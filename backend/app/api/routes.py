"""
API route handlers for DevDocs AI.

This module defines all FastAPI endpoints for document ingestion,
querying, and health checks.
"""

import logging
import time
from typing import Optional
from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from fastapi.responses import JSONResponse

from app.config import settings
from app.models import (
    QueryRequest,
    QueryResponse,
    IngestResponse,
    HealthResponse,
    ErrorResponse,
    SourceCitation,
)
from app.services.ingestion import get_ingestion_service
from app.services.retrieval import get_vector_store
from app.services.llm import get_ollama_service
from app.services.embeddings import get_embedding_service

logger = logging.getLogger(__name__)

# Create router
router = APIRouter()


# ============================================================================
# Health Check Endpoint
# ============================================================================

@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    description="Check the health status of the API and its dependencies",
)
async def health_check():
    """
    Health check endpoint.

    Verifies that all services (Ollama, ChromaDB, embeddings, cache) are operational.

    Returns:
        HealthResponse with status and service availability
    """
    try:
        # Check each service
        ollama_service = get_ollama_service()
        embedding_service = get_embedding_service()
        vector_store = get_vector_store()

        services_status = {
            "ollama": await ollama_service.check_health(),
            "chromadb": vector_store.check_health(),
            "embeddings": embedding_service.check_health(),
        }

        # Check cache if enabled
        stats = {}
        if settings.enable_caching:
            try:
                from app.services.cache import get_cache_service
                cache = get_cache_service()
                cache_healthy = await cache.check_health()
                services_status["cache"] = cache_healthy

                # Get cache statistics
                if cache_healthy:
                    cache_stats = cache.get_stats()
                    stats["cache"] = cache_stats
            except Exception as e:
                logger.warning(f"Cache health check failed: {e}")
                services_status["cache"] = False

        # Determine overall status
        all_healthy = all(services_status.values())
        any_healthy = any(services_status.values())

        if all_healthy:
            status = "healthy"
        elif any_healthy:
            status = "degraded"
        else:
            status = "unhealthy"

        return HealthResponse(
            status=status,
            services=services_status,
            stats=stats if stats else None,
        )

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthResponse(
            status="unhealthy",
            services={
                "ollama": False,
                "chromadb": False,
                "embeddings": False,
            }
        )


# ============================================================================
# Document Ingestion Endpoint
# ============================================================================

@router.post(
    "/ingest",
    response_model=IngestResponse,
    summary="Ingest documents",
    description="Upload and process code files or ZIP archives into the knowledge base",
)
async def ingest_documents(
    file: UploadFile = File(..., description="File or ZIP archive to upload"),
    collection_name: Optional[str] = Form(None, description="Target collection name"),
    overwrite: bool = Form(False, description="Overwrite existing documents"),
):
    """
    Ingest documents into the knowledge base.

    Accepts individual files or ZIP archives. Supported file types are
    configured in settings (default: .py, .js, .ts, .java, .go, .md, etc.).

    Args:
        file: Uploaded file (code file or ZIP archive)
        collection_name: Optional collection name (defaults to configured collection)
        overwrite: Whether to replace existing documents with same file paths

    Returns:
        IngestResponse with processing statistics

    Raises:
        HTTPException: If file processing fails
    """
    from app.services.metrics import files_ingested, chunks_created, ingestion_latency

    start_time = time.time()

    try:
        # Read file content
        content = await file.read()
        filename = file.filename or "unknown"

        logger.info(
            f"Received file upload: {filename} "
            f"({len(content)} bytes, collection: {collection_name or 'default'})"
        )

        # Get ingestion service
        ingestion_service = get_ingestion_service(collection_name)

        # Process the file
        files_processed, total_chunks, file_metadata = await ingestion_service.ingest_from_upload(
            file_content=content,
            filename=filename,
            overwrite=overwrite,
        )

        processing_time = time.time() - start_time

        # Track ingestion metrics
        for metadata in file_metadata:
            language = metadata.language or "unknown"
            files_ingested.labels(language=language, status="success").inc()
            chunks_created.labels(language=language, chunking_strategy="smart" if settings.enable_smart_chunking else "character").inc(metadata.num_chunks)
            ingestion_latency.labels(language=language).observe(processing_time / files_processed)

        response = IngestResponse(
            success=True,
            message=f"Successfully processed {files_processed} file(s)",
            files_processed=files_processed,
            total_chunks=total_chunks,
            collection_name=collection_name or settings.chroma_collection_name,
            processing_time_seconds=round(processing_time, 2),
            file_metadata=file_metadata,
        )

        logger.info(
            f"Ingestion complete: {files_processed} files, {total_chunks} chunks, "
            f"{processing_time:.2f}s"
        )

        return response

    except ValueError as e:
        # Validation errors (unsupported file type, etc.)
        logger.warning(f"Validation error during ingestion: {e}")
        files_ingested.labels(language="unknown", status="validation_error").inc()
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error during ingestion: {e}")
        files_ingested.labels(language="unknown", status="error").inc()
        raise HTTPException(
            status_code=500,
            detail=f"Internal error during document processing: {str(e)}"
        )


# ============================================================================
# Query Endpoint
# ============================================================================

@router.post(
    "/query",
    response_model=QueryResponse,
    summary="Query the knowledge base",
    description="Ask questions about the uploaded codebase and get AI-generated answers",
)
async def query_knowledge_base(request: QueryRequest):
    """
    Query the knowledge base and get an AI-generated answer.

    Uses RAG (Retrieval-Augmented Generation) to:
    1. Retrieve relevant code chunks using semantic search
    2. Generate an answer using the LLM with retrieved context

    Args:
        request: QueryRequest containing the question and options

    Returns:
        QueryResponse with answer and source citations

    Raises:
        HTTPException: If query processing fails
    """
    from app.services.metrics import query_counter, query_latency, retrieval_chunks

    start_time = time.time()

    try:
        logger.info(f"Received query: '{request.question}'")

        # Get services
        vector_store = get_vector_store(request.collection_name)
        ollama_service = get_ollama_service()

        # Determine top_k
        top_k = request.top_k or settings.retrieval_top_k

        # Retrieve relevant chunks
        logger.info(f"Retrieving top {top_k} relevant chunks")
        search_results = await vector_store.search(
            query=request.question,
            top_k=top_k,
        )

        # Track retrieval metrics
        retrieval_chunks.observe(len(search_results))

        if not search_results:
            logger.warning("No relevant documents found for query")
            query_counter.labels(endpoint="query", status="no_results").inc()
            return QueryResponse(
                success=True,
                question=request.question,
                answer="I couldn't find any relevant information in the codebase to answer your question. "
                       "Please try rephrasing or ensure documents have been ingested.",
                sources=[],
                processing_time_seconds=round(time.time() - start_time, 2),
                model_used=settings.ollama_model,
            )

        # Extract chunks for context
        chunks = [chunk for chunk, score in search_results]

        # Generate answer using LLM
        logger.info("Generating answer with LLM")
        answer = await ollama_service.generate_with_context(
            question=request.question,
            context_chunks=chunks,
        )

        # Format citations
        citations = []
        if request.include_sources:
            citations = vector_store.format_as_citations(search_results)

        processing_time = time.time() - start_time

        response = QueryResponse(
            success=True,
            question=request.question,
            answer=answer,
            sources=citations,
            processing_time_seconds=round(processing_time, 2),
            model_used=settings.ollama_model,
        )

        # Track success metrics
        query_counter.labels(endpoint="query", status="success").inc()
        query_latency.labels(endpoint="query").observe(processing_time)

        logger.info(
            f"Query complete: {len(citations)} sources, {processing_time:.2f}s"
        )

        return response

    except Exception as e:
        # Track error metrics
        query_counter.labels(endpoint="query", status="error").inc()
        query_latency.labels(endpoint="query").observe(time.time() - start_time)

        logger.error(f"Error processing query: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error processing query: {str(e)}"
        )


# ============================================================================
# Collection Stats Endpoint (Bonus - useful for debugging)
# ============================================================================

@router.get(
    "/stats",
    summary="Get collection statistics",
    description="Get statistics about the vector database collection",
)
async def get_stats(collection_name: Optional[str] = None):
    """
    Get statistics about the knowledge base.

    Args:
        collection_name: Optional collection name (defaults to configured collection)

    Returns:
        Dictionary with collection statistics
    """
    try:
        vector_store = get_vector_store(collection_name)
        stats = vector_store.get_collection_stats()

        logger.info(f"Retrieved stats for collection: {stats}")
        return stats

    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving statistics: {str(e)}"
        )


# ============================================================================
# Prometheus Metrics Endpoint (Phase 3)
# ============================================================================

@router.get(
    "/metrics",
    summary="Prometheus metrics",
    description="Get Prometheus metrics for monitoring (query latency, cache hit rate, etc.)",
)
async def metrics():
    """
    Prometheus metrics endpoint.

    Returns metrics in Prometheus text format for scraping by Prometheus server.

    Metrics include:
    - Query latency and throughput
    - Cache hit rates (embedding and response)
    - LLM usage (requests, tokens, latency)
    - Retrieval performance (chunks, latency)
    - Ingestion statistics (files, chunks)

    Example Prometheus scrape config:
        scrape_configs:
          - job_name: 'devdocs-ai'
            static_configs:
              - targets: ['localhost:8000']
            metrics_path: '/api/v1/metrics'
    """
    from app.services.metrics import export_metrics, get_content_type, update_chromadb_metrics
    from starlette.responses import Response

    # Update ChromaDB metrics before exporting
    try:
        vector_store = get_vector_store()
        update_chromadb_metrics(vector_store)
    except Exception:
        pass  # Metrics are optional, don't fail

    return Response(
        content=export_metrics(),
        media_type=get_content_type()
    )

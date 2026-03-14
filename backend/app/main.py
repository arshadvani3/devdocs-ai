"""
Main FastAPI application entry point.

This module sets up the FastAPI application with middleware, routes,
and configuration.
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.api.routes import router
from app.api.websocket import router as ws_router
from app.models import ErrorResponse

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.

    This runs on startup and shutdown to manage resources.
    """
    # Startup
    logger.info("=" * 60)
    logger.info(f"Starting {settings.app_name} v1.0.0")
    logger.info(f"Environment: {'DEBUG' if settings.debug else 'PRODUCTION'}")
    logger.info(f"LLM: Groq ({settings.groq_model})")
    logger.info(f"Vector DB: Qdrant Cloud ({settings.qdrant_url})")
    logger.info(f"Embedding: HuggingFace API ({settings.embedding_model})")
    logger.info(f"WebSocket streaming: ws://localhost:{settings.api_port}/api/v1/stream")
    logger.info("=" * 60)

    # Test cache connection
    if settings.enable_caching:
        try:
            from app.services.cache import get_cache_service
            cache = get_cache_service()
            is_healthy = await cache.check_health()
            if is_healthy:
                logger.info("✓ Redis cache is healthy")
            else:
                logger.warning("✗ Redis cache is not responding")
        except Exception as e:
            logger.warning(f"✗ Redis cache unavailable: {e}")
            logger.warning("  Continuing without caching...")
    else:
        logger.info("ℹ Caching disabled in settings")

    # Optionally pre-load models here for faster first request
    # (Uncomment if you want to load on startup)
    # try:
    #     from app.services.embeddings import get_embedding_service
    #     logger.info("Pre-loading embedding model...")
    #     embedding_service = get_embedding_service()
    #     embedding_service.model  # Trigger lazy loading
    #     logger.info("Embedding model loaded successfully")
    # except Exception as e:
    #     logger.warning(f"Could not pre-load embedding model: {e}")

    yield

    # Shutdown
    if settings.enable_caching:
        try:
            from app.services.cache import get_cache_service
            cache = get_cache_service()
            await cache.close()
            logger.info("Redis cache connection closed")
        except Exception:
            pass

    logger.info("Shutting down DevDocs AI")


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    description=(
        "A production-grade RAG-powered code documentation assistant. "
        "Upload codebases, ask questions, and get accurate answers with source citations."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)


# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include API routes
app.include_router(router, prefix="/api/v1", tags=["API"])

# Include WebSocket routes
app.include_router(ws_router, prefix="/api/v1", tags=["WebSocket"])


# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """
    Root endpoint with API information.

    Returns:
        Welcome message and API details
    """
    return {
        "name": settings.app_name,
        "version": "1.0.0",
        "description": "RAG-powered code documentation assistant",
        "docs": "/docs",
        "health": "/api/v1/health",
        "endpoints": {
            "ingest": "/api/v1/ingest",
            "query": "/api/v1/query",
            "stats": "/api/v1/stats",
        }
    }


# HTTP exception handler
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions and return standard error response."""
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=exc.detail,
            detail=None,
        ).model_dump(mode='json')  # Serialize datetime properly
    )


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Handle unexpected exceptions gracefully."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal server error",
            "detail": str(exc) if settings.debug else "An unexpected error occurred"
        }
    )


if __name__ == "__main__":
    import uvicorn

    # Run with uvicorn programmatically (useful for debugging)
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )

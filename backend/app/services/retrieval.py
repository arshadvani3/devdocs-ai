"""
Vector storage and retrieval service using Qdrant Cloud.

This module handles storing document chunks with embeddings in Qdrant
and retrieving relevant chunks based on similarity search.
"""

import logging
import uuid
import asyncio
from typing import List, Optional, Dict, Any, Tuple
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
    FilterSelector,
)

from app.config import settings
from app.models import DocumentChunk, SourceCitation
from app.services.embeddings import get_embedding_service

logger = logging.getLogger(__name__)

EMBEDDING_DIM = 384  # all-MiniLM-L6-v2 produces 384-dimensional embeddings


class VectorStore:
    """
    Vector database service using Qdrant Cloud.

    This class manages document storage and similarity search using
    Qdrant as the vector database backend.

    Attributes:
        collection_name: Name of the current collection
    """

    def __init__(self, collection_name: Optional[str] = None):
        """
        Initialize the vector store.

        Args:
            collection_name: Name of the collection to use.
                           Defaults to configured collection name.
        """
        self.collection_name = collection_name or settings.qdrant_collection_name
        self._client: Optional[QdrantClient] = None
        self.embedding_service = get_embedding_service()

    def _get_client(self) -> QdrantClient:
        """Get or create Qdrant client."""
        if self._client is None:
            logger.info(f"Initializing Qdrant client at {settings.qdrant_url}")
            self._client = QdrantClient(
                url=settings.qdrant_url,
                api_key=settings.qdrant_api_key,
            )
            logger.info("Qdrant client initialized successfully")
        return self._client

    def _ensure_collection(self) -> None:
        """Create collection if it doesn't exist."""
        client = self._get_client()
        try:
            client.get_collection(self.collection_name)
            logger.debug(f"Collection already exists: {self.collection_name}")
        except Exception:
            logger.info(f"Creating new collection: {self.collection_name}")
            client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=EMBEDDING_DIM,
                    distance=Distance.COSINE,
                ),
            )
            logger.info(f"Created collection: {self.collection_name}")

    def _chunk_id_to_uuid(self, chunk_id: str) -> str:
        """Convert string chunk ID to deterministic UUID for Qdrant."""
        return str(uuid.uuid5(uuid.NAMESPACE_DNS, chunk_id))

    async def add_documents(self, chunks: List[DocumentChunk]) -> int:
        """
        Add document chunks to the vector store.

        Args:
            chunks: List of DocumentChunk objects to store

        Returns:
            Number of documents successfully added

        Raises:
            Exception: If there's an error adding documents
        """
        if not chunks:
            logger.warning("No chunks to add")
            return 0

        try:
            self._ensure_collection()
            client = self._get_client()

            # Generate embeddings if not present
            documents = [chunk.text for chunk in chunks]
            if chunks[0].embedding is None:
                logger.info(f"Generating embeddings for {len(chunks)} chunks")
                embeddings = await self.embedding_service.embed_batch(
                    documents, show_progress=True
                )
            else:
                embeddings = [chunk.embedding for chunk in chunks]

            # Build Qdrant points with full payload
            points = [
                PointStruct(
                    id=self._chunk_id_to_uuid(chunk.id),
                    vector=embedding,
                    payload={
                        "chunk_id": chunk.id,
                        "code": chunk.text,
                        "file_path": chunk.file_path,
                        "start_line": chunk.start_line,
                        "end_line": chunk.end_line,
                        "language": chunk.language,
                        "chunk_type": "code",
                        "chunk_index": chunk.chunk_index,
                    },
                )
                for chunk, embedding in zip(chunks, embeddings)
            ]

            logger.info(
                f"Adding {len(points)} documents to collection {self.collection_name}"
            )

            def _upsert():
                client.upsert(
                    collection_name=self.collection_name,
                    points=points,
                )

            await asyncio.to_thread(_upsert)

            logger.info(f"Successfully added {len(chunks)} documents")
            return len(chunks)

        except Exception as e:
            logger.error(f"Error adding documents to vector store: {e}")
            raise

    async def search(
        self,
        query: str,
        top_k: int = 5,
        filter_dict: Optional[Dict[str, Any]] = None,
    ) -> List[Tuple[DocumentChunk, float]]:
        """
        Search for similar documents using semantic similarity.

        Args:
            query: Query text to search for
            top_k: Number of results to return
            filter_dict: Optional metadata filters (e.g., {"language": "python"})

        Returns:
            List of (DocumentChunk, similarity_score) tuples, sorted by relevance

        Example:
            >>> store = VectorStore()
            >>> results = await store.search("How does authentication work?", top_k=3)
            >>> for chunk, score in results:
            ...     print(f"{chunk.file_path}:{chunk.start_line} (score: {score})")
        """
        try:
            self._ensure_collection()
            client = self._get_client()

            logger.info(f"Searching for: '{query}' (top_k={top_k})")
            query_embedding = await self.embedding_service.embed_query(query)

            # Build optional filter
            qdrant_filter = None
            if filter_dict:
                conditions = [
                    FieldCondition(key=k, match=MatchValue(value=v))
                    for k, v in filter_dict.items()
                ]
                qdrant_filter = Filter(must=conditions)

            def _search():
                return client.search(
                    collection_name=self.collection_name,
                    query_vector=query_embedding,
                    limit=top_k,
                    query_filter=qdrant_filter,
                    with_payload=True,
                )

            results = await asyncio.to_thread(_search)

            chunks_with_scores: List[Tuple[DocumentChunk, float]] = []
            for hit in results:
                payload = hit.payload or {}
                chunk = DocumentChunk(
                    id=payload.get("chunk_id", str(hit.id)),
                    text=payload.get("code", ""),
                    file_path=payload.get("file_path", ""),
                    start_line=payload.get("start_line", 1),
                    end_line=payload.get("end_line", 1),
                    language=payload.get("language", "unknown"),
                    chunk_index=payload.get("chunk_index", 0),
                )
                # Qdrant cosine scores are already in [0, 1] range for normalized vectors
                similarity_score = float(hit.score)
                chunks_with_scores.append((chunk, similarity_score))

            logger.info(f"Found {len(chunks_with_scores)} results")
            return chunks_with_scores

        except Exception as e:
            logger.error(f"Error searching vector store: {e}")
            raise

    def delete_by_file_path(self, file_path: str) -> int:
        """
        Delete all chunks from a specific file.

        Useful for updating documents - delete old chunks before adding new ones.

        Args:
            file_path: Path of the file whose chunks should be deleted

        Returns:
            Number of chunks deleted
        """
        try:
            client = self._get_client()

            count_filter = Filter(
                must=[FieldCondition(key="file_path", match=MatchValue(value=file_path))]
            )

            # Count before deleting
            count_result = client.count(
                collection_name=self.collection_name,
                count_filter=count_filter,
            )
            count = count_result.count

            if count > 0:
                client.delete(
                    collection_name=self.collection_name,
                    points_selector=FilterSelector(
                        filter=Filter(
                            must=[
                                FieldCondition(
                                    key="file_path", match=MatchValue(value=file_path)
                                )
                            ]
                        )
                    ),
                )
                logger.info(f"Deleted {count} chunks from {file_path}")
            else:
                logger.info(f"No chunks found for {file_path}")

            return count

        except Exception as e:
            err = str(e)
            if "doesn't exist" in err or "Not found" in err:
                logger.debug(f"Collection doesn't exist yet, nothing to delete for {file_path}")
                return 0
            logger.error(f"Error deleting chunks for {file_path}: {e}")
            raise

    def get_collection_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the collection.

        Returns:
            Dictionary with collection statistics
        """
        try:
            client = self._get_client()
            info = client.get_collection(self.collection_name)
            count = info.points_count or 0

            return {
                "collection_name": self.collection_name,
                "total_chunks": count,
                "embedding_dimension": EMBEDDING_DIM,
            }
        except Exception as e:
            logger.error(f"Error getting collection stats: {e}")
            return {
                "collection_name": self.collection_name,
                "total_chunks": 0,
                "error": str(e),
            }

    def check_health(self) -> bool:
        """
        Check if the vector store is working.

        Returns:
            True if healthy, False otherwise
        """
        try:
            client = self._get_client()
            client.get_collections()
            return True
        except Exception as e:
            logger.error(f"Vector store health check failed: {e}")
            return False

    def format_as_citations(
        self,
        results: List[Tuple[DocumentChunk, float]]
    ) -> List[SourceCitation]:
        """
        Convert search results to SourceCitation objects for API responses.

        Args:
            results: List of (chunk, score) tuples from search

        Returns:
            List of SourceCitation objects
        """
        citations = []
        for chunk, score in results:
            snippet = chunk.text[:200] + "..." if len(chunk.text) > 200 else chunk.text

            citation = SourceCitation(
                file_path=chunk.file_path,
                start_line=chunk.start_line,
                end_line=chunk.end_line,
                text_snippet=snippet,
                relevance_score=round(score, 3),
            )
            citations.append(citation)

        return citations


def get_vector_store(collection_name: Optional[str] = None) -> VectorStore:
    """
    Factory function to get a VectorStore instance.

    Args:
        collection_name: Optional collection name

    Returns:
        VectorStore instance
    """
    return VectorStore(collection_name=collection_name)

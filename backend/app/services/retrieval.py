"""
Vector storage and retrieval service using ChromaDB.

This module handles storing document chunks with embeddings in ChromaDB
and retrieving relevant chunks based on similarity search.
"""

import logging
from typing import List, Optional, Dict, Any, Tuple
import chromadb
from chromadb.config import Settings as ChromaSettings

from app.config import settings
from app.models import DocumentChunk, SourceCitation
from app.services.embeddings import get_embedding_service

logger = logging.getLogger(__name__)


class VectorStore:
    """
    Vector database service using ChromaDB.

    This class manages document storage and similarity search using
    ChromaDB as the vector database backend.

    Attributes:
        client: ChromaDB client instance
        collection_name: Name of the current collection
    """

    def __init__(self, collection_name: Optional[str] = None):
        """
        Initialize the vector store.

        Args:
            collection_name: Name of the collection to use.
                           Defaults to configured collection name.
        """
        self.collection_name = collection_name or settings.chroma_collection_name
        self._client: Optional[chromadb.Client] = None
        self._collection: Optional[chromadb.Collection] = None
        self.embedding_service = get_embedding_service()

    def _get_client(self) -> chromadb.Client:
        """Get or create ChromaDB client."""
        if self._client is None:
            persist_dir = settings.get_chroma_path()
            logger.info(f"Initializing ChromaDB client at {persist_dir}")

            self._client = chromadb.Client(
                ChromaSettings(
                    persist_directory=str(persist_dir),
                    anonymized_telemetry=False,
                )
            )
            logger.info("ChromaDB client initialized successfully")

        return self._client

    def _get_collection(self) -> chromadb.Collection:
        """
        Get or create the collection.

        Returns:
            ChromaDB collection instance
        """
        if self._collection is None:
            client = self._get_client()

            try:
                # Try to get existing collection
                self._collection = client.get_collection(
                    name=self.collection_name
                )
                logger.info(f"Retrieved existing collection: {self.collection_name}")
            except Exception:
                # Create new collection if it doesn't exist
                self._collection = client.create_collection(
                    name=self.collection_name,
                    metadata={"description": "DevDocs AI code documentation"}
                )
                logger.info(f"Created new collection: {self.collection_name}")

        return self._collection

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
            collection = self._get_collection()

            # Prepare data for ChromaDB
            ids = [chunk.id for chunk in chunks]
            documents = [chunk.text for chunk in chunks]
            metadatas = [
                {
                    "file_path": chunk.file_path,
                    "start_line": chunk.start_line,
                    "end_line": chunk.end_line,
                    "language": chunk.language,
                    "chunk_index": chunk.chunk_index,
                }
                for chunk in chunks
            ]

            # Generate embeddings if not present
            if chunks[0].embedding is None:
                logger.info(f"Generating embeddings for {len(chunks)} chunks")
                embeddings = await self.embedding_service.embed_batch(
                    documents,
                    show_progress=True
                )
            else:
                embeddings = [chunk.embedding for chunk in chunks]

            # Add to ChromaDB
            logger.info(f"Adding {len(chunks)} documents to collection {self.collection_name}")
            collection.add(
                ids=ids,
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas,
            )

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
            collection = self._get_collection()

            # Generate query embedding
            logger.info(f"Searching for: '{query}' (top_k={top_k})")
            query_embedding = await self.embedding_service.embed_query(query)

            # Perform similarity search
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=filter_dict,  # Optional metadata filtering
            )

            # Parse results
            chunks_with_scores: List[Tuple[DocumentChunk, float]] = []

            if results["ids"] and len(results["ids"][0]) > 0:
                for i in range(len(results["ids"][0])):
                    chunk = DocumentChunk(
                        id=results["ids"][0][i],
                        text=results["documents"][0][i],
                        file_path=results["metadatas"][0][i]["file_path"],
                        start_line=results["metadatas"][0][i]["start_line"],
                        end_line=results["metadatas"][0][i]["end_line"],
                        language=results["metadatas"][0][i]["language"],
                        chunk_index=results["metadatas"][0][i]["chunk_index"],
                    )

                    # ChromaDB returns distances, convert to similarity score
                    # Lower distance = higher similarity
                    distance = results["distances"][0][i]
                    similarity_score = 1.0 / (1.0 + distance)

                    chunks_with_scores.append((chunk, similarity_score))

                logger.info(f"Found {len(chunks_with_scores)} results")
            else:
                logger.warning("No results found for query")

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
            collection = self._get_collection()

            # Query for all chunks with this file_path
            results = collection.get(
                where={"file_path": file_path}
            )

            if results["ids"]:
                collection.delete(ids=results["ids"])
                logger.info(f"Deleted {len(results['ids'])} chunks from {file_path}")
                return len(results["ids"])
            else:
                logger.info(f"No chunks found for {file_path}")
                return 0

        except Exception as e:
            logger.error(f"Error deleting chunks for {file_path}: {e}")
            raise

    def get_collection_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the collection.

        Returns:
            Dictionary with collection statistics
        """
        try:
            collection = self._get_collection()
            count = collection.count()

            return {
                "collection_name": self.collection_name,
                "total_chunks": count,
                "embedding_dimension": self.embedding_service.embedding_dim,
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
            collection = self._get_collection()
            # Try a simple operation
            collection.count()
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
            # Truncate text snippet to reasonable length
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

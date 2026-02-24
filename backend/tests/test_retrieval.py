"""
Tests for vector storage and retrieval functionality.

These tests verify that embeddings, storage, and search work correctly.
"""

import pytest

from app.models import DocumentChunk
from app.services.embeddings import get_embedding_service
from app.services.retrieval import get_vector_store


# ============================================================================
# Embedding Tests
# ============================================================================

def test_embedding_service_initialization():
    """Test that embedding service initializes correctly."""
    service = get_embedding_service()
    assert service is not None
    assert service.model_name is not None


def test_embed_single_text():
    """Test embedding a single text."""
    service = get_embedding_service()
    text = "def hello_world(): print('Hello')"

    embedding = service.embed_text(text)

    assert isinstance(embedding, list)
    assert len(embedding) == service.embedding_dim
    assert all(isinstance(x, float) for x in embedding)


def test_embed_batch():
    """Test embedding multiple texts."""
    service = get_embedding_service()
    texts = [
        "def foo(): pass",
        "def bar(): pass",
        "class Calculator: pass",
    ]

    embeddings = service.embed_batch(texts)

    assert len(embeddings) == len(texts)
    assert all(len(emb) == service.embedding_dim for emb in embeddings)


def test_embed_empty_batch():
    """Test embedding empty batch."""
    service = get_embedding_service()
    embeddings = service.embed_batch([])
    assert embeddings == []


def test_embedding_consistency():
    """Test that same text produces same embedding."""
    service = get_embedding_service()
    text = "def test(): return 42"

    emb1 = service.embed_text(text)
    emb2 = service.embed_text(text)

    # Embeddings should be identical for same text
    assert emb1 == emb2


def test_embedding_health_check():
    """Test embedding service health check."""
    service = get_embedding_service()
    assert service.check_health() is True


# ============================================================================
# Vector Store Tests
# ============================================================================

@pytest.fixture
def test_chunks():
    """Create sample chunks for testing."""
    return [
        DocumentChunk(
            id="test_1",
            text="def authenticate_user(username, password): return True",
            file_path="auth.py",
            start_line=1,
            end_line=1,
            language="python",
            chunk_index=0,
        ),
        DocumentChunk(
            id="test_2",
            text="def login(request): user = authenticate_user(request.username, request.password)",
            file_path="views.py",
            start_line=10,
            end_line=10,
            language="python",
            chunk_index=0,
        ),
        DocumentChunk(
            id="test_3",
            text="class Calculator: def add(self, a, b): return a + b",
            file_path="calc.py",
            start_line=1,
            end_line=2,
            language="python",
            chunk_index=0,
        ),
    ]


def test_vector_store_initialization():
    """Test vector store initialization."""
    store = get_vector_store(collection_name="test_init")
    assert store is not None
    assert store.collection_name == "test_init"


def test_add_and_search_documents(test_chunks):
    """Test adding documents and searching."""
    # Use a unique collection for this test
    store = get_vector_store(collection_name="test_search")

    # Add documents
    num_added = store.add_documents(test_chunks)
    assert num_added == len(test_chunks)

    # Search for authentication-related code
    results = store.search("user authentication login", top_k=2)

    assert len(results) > 0
    # Results should be (chunk, score) tuples
    assert all(isinstance(result, tuple) for result in results)
    assert all(len(result) == 2 for result in results)

    # First result should be most relevant
    best_chunk, best_score = results[0]
    assert isinstance(best_chunk, DocumentChunk)
    assert isinstance(best_score, float)
    assert 0.0 <= best_score <= 1.0


def test_search_no_results():
    """Test search when no relevant documents exist."""
    store = get_vector_store(collection_name="test_empty")

    # Search in empty collection
    results = store.search("nonexistent query", top_k=5)

    assert isinstance(results, list)
    assert len(results) == 0


def test_delete_by_file_path(test_chunks):
    """Test deleting documents by file path."""
    store = get_vector_store(collection_name="test_delete")

    # Add documents
    store.add_documents(test_chunks)

    # Delete one file's chunks
    num_deleted = store.delete_by_file_path("auth.py")
    assert num_deleted >= 1

    # Verify it's gone
    results = store.search("authenticate_user", top_k=5)
    # Should not find the deleted chunk
    file_paths = [chunk.file_path for chunk, score in results]
    assert "auth.py" not in file_paths or len(results) == 0


def test_get_collection_stats(test_chunks):
    """Test getting collection statistics."""
    store = get_vector_store(collection_name="test_stats")

    # Add some documents
    store.add_documents(test_chunks)

    stats = store.get_collection_stats()

    assert "collection_name" in stats
    assert "total_chunks" in stats
    assert stats["total_chunks"] >= len(test_chunks)


def test_vector_store_health_check():
    """Test vector store health check."""
    store = get_vector_store(collection_name="test_health")
    assert store.check_health() is True


def test_format_citations(test_chunks):
    """Test formatting search results as citations."""
    store = get_vector_store(collection_name="test_citations")

    # Add documents
    store.add_documents(test_chunks)

    # Search and format
    results = store.search("authentication", top_k=2)
    citations = store.format_as_citations(results)

    assert len(citations) > 0
    for citation in citations:
        assert hasattr(citation, 'file_path')
        assert hasattr(citation, 'start_line')
        assert hasattr(citation, 'end_line')
        assert hasattr(citation, 'text_snippet')
        assert hasattr(citation, 'relevance_score')
        assert 0.0 <= citation.relevance_score <= 1.0


# ============================================================================
# Integration Tests
# ============================================================================

@pytest.mark.asyncio
async def test_end_to_end_retrieval():
    """
    Test the complete retrieval pipeline: embed → store → search.
    """
    from app.services.ingestion import get_ingestion_service
    import tempfile
    from pathlib import Path

    # Sample code
    code = '''
def process_payment(amount, card_number):
    """Process a credit card payment."""
    if validate_card(card_number):
        return charge_card(card_number, amount)
    return False


def validate_card(card_number):
    """Validate credit card number."""
    return len(card_number) == 16
'''

    # Create temp file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(code)
        temp_file = f.name

    try:
        # Ingest
        service = get_ingestion_service(collection_name="test_e2e")
        chunks, metadata = await service.ingest_file(temp_file, overwrite=True)

        # Search
        store = get_vector_store(collection_name="test_e2e")
        results = store.search("how to process payment", top_k=3)

        # Verify we found relevant results
        assert len(results) > 0

        # The top result should contain payment-related code
        top_chunk, top_score = results[0]
        assert "payment" in top_chunk.text.lower() or "charge" in top_chunk.text.lower()

    finally:
        Path(temp_file).unlink()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

"""
Tests for document ingestion functionality.

These tests verify that file parsing, chunking, and ingestion
work correctly.
"""

import pytest
import tempfile
from pathlib import Path

from app.utils.parsing import parse_file, detect_language, count_lines
from app.utils.chunking import chunk_text
from app.models import DocumentChunk


# Sample Python code for testing
SAMPLE_PYTHON_CODE = '''
def hello_world():
    """Print hello world."""
    print("Hello, World!")


def add_numbers(a, b):
    """Add two numbers."""
    return a + b


class Calculator:
    """A simple calculator."""

    def __init__(self):
        self.result = 0

    def add(self, x):
        """Add to result."""
        self.result += x
        return self.result
'''


# ============================================================================
# Parsing Tests
# ============================================================================

def test_detect_language():
    """Test language detection from file extensions."""
    assert detect_language("test.py") == "python"
    assert detect_language("test.js") == "javascript"
    assert detect_language("test.ts") == "typescript"
    assert detect_language("test.java") == "java"
    assert detect_language("test.go") == "go"
    assert detect_language("test.md") == "markdown"
    assert detect_language("test.xyz") == "unknown"


def test_parse_python_file():
    """Test parsing a Python file."""
    # Create a temporary Python file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(SAMPLE_PYTHON_CODE)
        temp_file = f.name

    try:
        content, language = parse_file(temp_file)

        assert content is not None
        assert language == "python"
        assert "def hello_world" in content
        assert "class Calculator" in content
        assert len(content) > 0
    finally:
        Path(temp_file).unlink()


def test_parse_nonexistent_file():
    """Test parsing a file that doesn't exist."""
    content, language = parse_file("/nonexistent/file.py")
    assert content is None


def test_count_lines():
    """Test line counting."""
    text = "line1\nline2\nline3"
    assert count_lines(text) == 3

    text = "single line"
    assert count_lines(text) == 1


# ============================================================================
# Chunking Tests
# ============================================================================

def test_chunk_text_basic():
    """Test basic text chunking."""
    text = SAMPLE_PYTHON_CODE
    chunks = chunk_text(
        text=text,
        file_path="test.py",
        language="python",
        max_chunk_size=100,
        chunk_overlap=20,
    )

    assert len(chunks) > 0
    assert all(isinstance(chunk, DocumentChunk) for chunk in chunks)
    assert all(chunk.language == "python" for chunk in chunks)
    assert all(chunk.file_path == "test.py" for chunk in chunks)


def test_chunk_text_metadata():
    """Test that chunks have correct metadata."""
    text = "line1\nline2\nline3\nline4\nline5"
    chunks = chunk_text(
        text=text,
        file_path="test.txt",
        language="text",
        max_chunk_size=20,
        chunk_overlap=5,
    )

    # Verify metadata
    for i, chunk in enumerate(chunks):
        assert chunk.chunk_index == i
        assert chunk.start_line >= 1
        assert chunk.end_line >= chunk.start_line
        assert chunk.id == f"test.txt_chunk_{i}"


def test_chunk_empty_text():
    """Test chunking empty text."""
    chunks = chunk_text(
        text="",
        file_path="empty.py",
        language="python",
    )

    assert len(chunks) == 0


def test_chunk_text_small():
    """Test chunking text smaller than max_chunk_size."""
    text = "small text"
    chunks = chunk_text(
        text=text,
        file_path="small.py",
        language="python",
        max_chunk_size=1000,
    )

    assert len(chunks) == 1
    assert chunks[0].text == "small text"


# ============================================================================
# Integration Test
# ============================================================================

@pytest.mark.asyncio
async def test_full_ingestion_pipeline():
    """
    Test the complete ingestion pipeline.

    NOTE: This test requires ChromaDB to be available and will create
    a test collection. It may take a few seconds to run.
    """
    from app.services.ingestion import get_ingestion_service

    # Create a temporary Python file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(SAMPLE_PYTHON_CODE)
        temp_file = f.name

    try:
        # Use a test collection to avoid polluting the main collection
        service = get_ingestion_service(collection_name="test_collection")

        # Ingest the file
        chunks, metadata = await service.ingest_file(temp_file, overwrite=True)

        # Verify results
        assert len(chunks) > 0
        assert metadata.file_path == temp_file
        assert metadata.language == "python"
        assert metadata.num_chunks == len(chunks)

    finally:
        Path(temp_file).unlink()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

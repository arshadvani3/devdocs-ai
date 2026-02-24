"""
Text chunking utilities for splitting documents into manageable pieces.

This module implements chunking strategies for code and documentation,
optimized for semantic search and RAG applications.
"""

import logging
from typing import List
from app.models import DocumentChunk

logger = logging.getLogger(__name__)


def chunk_text(
    text: str,
    file_path: str,
    language: str,
    max_chunk_size: int = 500,
    chunk_overlap: int = 50,
) -> List[DocumentChunk]:
    """
    Split text into overlapping chunks for embedding and retrieval.

    This implements a simple character-based chunking strategy with overlap.
    Future improvements could include:
    - AST-based chunking for code (split by functions/classes)
    - Semantic chunking (split at natural boundaries)
    - Language-specific chunking strategies

    Args:
        text: The text content to chunk
        file_path: Original file path for metadata
        language: Programming language or file type
        max_chunk_size: Maximum characters per chunk
        chunk_overlap: Number of characters to overlap between chunks

    Returns:
        List of DocumentChunk objects with metadata

    Example:
        >>> text = "def foo():\\n    pass\\n\\ndef bar():\\n    pass"
        >>> chunks = chunk_text(text, "main.py", "python", max_chunk_size=20)
        >>> len(chunks)
        3
    """
    if not text or not text.strip():
        logger.warning(f"Empty text provided for chunking: {file_path}")
        return []

    # Split text into lines for better line number tracking
    lines = text.splitlines(keepends=True)
    total_lines = len(lines)

    chunks: List[DocumentChunk] = []
    chunk_index = 0

    # Current chunk being built
    current_chunk = ""
    current_start_line = 1
    current_line_num = 1

    for line_num, line in enumerate(lines, start=1):
        # Add line to current chunk
        current_chunk += line

        # Check if we've reached max size or end of file
        if len(current_chunk) >= max_chunk_size or line_num == total_lines:
            # Create chunk if we have content
            if current_chunk.strip():
                chunk = DocumentChunk(
                    id=f"{file_path}_chunk_{chunk_index}",
                    text=current_chunk.strip(),
                    file_path=file_path,
                    start_line=current_start_line,
                    end_line=line_num,
                    language=language,
                    chunk_index=chunk_index,
                )
                chunks.append(chunk)
                chunk_index += 1

                # Calculate overlap for next chunk
                # Go back by overlap characters
                overlap_text = current_chunk[-chunk_overlap:] if len(current_chunk) > chunk_overlap else ""

                # Find which line the overlap starts at
                overlap_lines = overlap_text.count("\n")
                current_start_line = max(1, line_num - overlap_lines)

                # Reset current chunk with overlap
                current_chunk = overlap_text
                current_line_num = line_num

    logger.info(
        f"Chunked {file_path} into {len(chunks)} chunks "
        f"(max_size={max_chunk_size}, overlap={chunk_overlap})"
    )

    return chunks


def chunk_by_lines(
    text: str,
    file_path: str,
    language: str,
    lines_per_chunk: int = 50,
    overlap_lines: int = 5,
) -> List[DocumentChunk]:
    """
    Split text into chunks by line count (alternative strategy).

    This can be useful for code where line-based chunking makes more sense
    than character-based chunking.

    Args:
        text: The text content to chunk
        file_path: Original file path for metadata
        language: Programming language or file type
        lines_per_chunk: Number of lines per chunk
        overlap_lines: Number of lines to overlap between chunks

    Returns:
        List of DocumentChunk objects with metadata
    """
    if not text or not text.strip():
        return []

    lines = text.splitlines()
    total_lines = len(lines)

    chunks: List[DocumentChunk] = []
    chunk_index = 0
    start_line = 0

    while start_line < total_lines:
        # Calculate end line for this chunk
        end_line = min(start_line + lines_per_chunk, total_lines)

        # Extract chunk lines
        chunk_lines = lines[start_line:end_line]
        chunk_text = "\n".join(chunk_lines)

        if chunk_text.strip():
            chunk = DocumentChunk(
                id=f"{file_path}_chunk_{chunk_index}",
                text=chunk_text,
                file_path=file_path,
                start_line=start_line + 1,  # 1-indexed
                end_line=end_line,  # 1-indexed
                language=language,
                chunk_index=chunk_index,
            )
            chunks.append(chunk)
            chunk_index += 1

        # Move to next chunk with overlap
        start_line = end_line - overlap_lines

        # Prevent infinite loop
        if start_line >= total_lines - overlap_lines:
            break

    logger.info(
        f"Chunked {file_path} by lines into {len(chunks)} chunks "
        f"(lines_per_chunk={lines_per_chunk}, overlap={overlap_lines})"
    )

    return chunks


def smart_chunk_code(
    text: str,
    file_path: str,
    language: str,
    max_chunk_size: int = 500,
) -> List[DocumentChunk]:
    """
    Intelligently chunk code based on language structure.

    Uses AST-based chunking for supported languages (Python, JavaScript, Markdown)
    to preserve function/class boundaries and semantic structure.
    Falls back to character-based chunking for unsupported languages.

    Args:
        text: The text content to chunk
        file_path: Original file path for metadata
        language: Programming language or file type
        max_chunk_size: Maximum characters per chunk (guidance, not strict limit)

    Returns:
        List of DocumentChunk objects with metadata
    """
    from app.config import settings

    # Check if smart chunking is enabled
    if not settings.enable_smart_chunking:
        logger.debug(f"Smart chunking disabled, using character-based for {file_path}")
        return chunk_text(text, file_path, language, max_chunk_size)

    # Route to language-specific chunkers
    try:
        if language == "python":
            from app.utils.ast_chunking import chunk_python_ast
            logger.debug(f"Using Python AST chunking for {file_path}")
            return chunk_python_ast(text, file_path, max_chunk_size)

        elif language in ("javascript", "typescript", "jsx", "tsx"):
            from app.utils.ast_chunking import chunk_javascript_simple
            logger.debug(f"Using JavaScript regex chunking for {file_path}")
            return chunk_javascript_simple(text, file_path, max_chunk_size)

        elif language == "markdown":
            from app.utils.ast_chunking import chunk_markdown_by_headers
            logger.debug(f"Using Markdown header chunking for {file_path}")
            return chunk_markdown_by_headers(text, file_path, max_chunk_size)

        else:
            # Unsupported language - fall back to character-based
            logger.debug(f"No smart chunker for '{language}', using character-based for {file_path}")
            return chunk_text(text, file_path, language, max_chunk_size)

    except Exception as e:
        logger.warning(f"Smart chunking failed for {file_path}: {e}, falling back to character-based")
        return chunk_text(text, file_path, language, max_chunk_size)


def merge_small_chunks(
    chunks: List[DocumentChunk],
    min_chunk_size: int = 100,
) -> List[DocumentChunk]:
    """
    Merge chunks that are too small to be useful.

    This is a post-processing step to avoid having tiny chunks
    that lack sufficient context for meaningful retrieval.

    Args:
        chunks: List of chunks to process
        min_chunk_size: Minimum acceptable chunk size

    Returns:
        List of chunks with small ones merged
    """
    if not chunks:
        return []

    merged: List[DocumentChunk] = []
    current_merge: List[DocumentChunk] = []

    for chunk in chunks:
        if len(chunk.text) < min_chunk_size:
            current_merge.append(chunk)
        else:
            # If we have chunks waiting to merge, merge them now
            if current_merge:
                merged_text = "\n\n".join(c.text for c in current_merge)
                merged_chunk = DocumentChunk(
                    id=current_merge[0].id,
                    text=merged_text,
                    file_path=current_merge[0].file_path,
                    start_line=current_merge[0].start_line,
                    end_line=current_merge[-1].end_line,
                    language=current_merge[0].language,
                    chunk_index=current_merge[0].chunk_index,
                )
                merged.append(merged_chunk)
                current_merge = []

            # Add the current chunk
            merged.append(chunk)

    # Handle remaining small chunks
    if current_merge:
        merged_text = "\n\n".join(c.text for c in current_merge)
        merged_chunk = DocumentChunk(
            id=current_merge[0].id,
            text=merged_text,
            file_path=current_merge[0].file_path,
            start_line=current_merge[0].start_line,
            end_line=current_merge[-1].end_line,
            language=current_merge[0].language,
            chunk_index=current_merge[0].chunk_index,
        )
        merged.append(merged_chunk)

    logger.info(f"Merged small chunks: {len(chunks)} -> {len(merged)}")
    return merged

"""
AST-based code chunking for better semantic preservation.

This module provides intelligent chunking strategies that respect code structure:
- Python: AST-based chunking by functions, classes, and methods
- JavaScript/TypeScript: Regex-based function and class detection
- Markdown: Header-based sectioning

These strategies preserve complete code blocks and logical units,
improving retrieval quality compared to character-based chunking.
"""

import ast
import logging
import re
from typing import List, Optional, Tuple
from app.models import DocumentChunk

logger = logging.getLogger(__name__)


def chunk_python_ast(
    code: str,
    file_path: str,
    max_chunk_size: int = 500
) -> List[DocumentChunk]:
    """
    Chunk Python code by AST nodes (functions, classes, methods).
    Preserves complete code blocks for better semantic understanding.

    Args:
        code: Python source code
        file_path: Original file path
        max_chunk_size: Maximum characters per chunk (guidance, not strict limit)

    Returns:
        List of DocumentChunk objects representing functions, classes, and module-level code

    Example:
        >>> code = '''
        ... def hello():
        ...     print("Hello")
        ...
        ... class MyClass:
        ...     def method(self):
        ...         pass
        ... '''
        >>> chunks = chunk_python_ast(code, "test.py")
        >>> len(chunks) >= 2  # At least function and class
        True
    """
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        logger.warning(f"Python syntax error in {file_path}: {e}")
        # Fall back to character-based chunking
        from app.utils.chunking import chunk_text
        return chunk_text(code, file_path, "python", max_chunk_size)

    lines = code.splitlines()
    chunks = []

    # Extract top-level nodes (functions, classes)
    for node in ast.iter_child_nodes(tree):
        chunk_text = None
        start_line = None
        end_line = None
        node_type = None
        node_name = None

        if isinstance(node, ast.FunctionDef):
            node_type = "function"
            node_name = node.name
            start_line = node.lineno
            end_line = node.end_lineno
        elif isinstance(node, ast.AsyncFunctionDef):
            node_type = "async_function"
            node_name = node.name
            start_line = node.lineno
            end_line = node.end_lineno
        elif isinstance(node, ast.ClassDef):
            node_type = "class"
            node_name = node.name
            start_line = node.lineno
            end_line = node.end_lineno
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            # Skip imports - will be captured as module-level code
            continue

        if start_line and end_line:
            # Extract source lines (convert to 0-indexed)
            chunk_lines = lines[start_line - 1:end_line]
            chunk_text = "\n".join(chunk_lines).strip()

            # If chunk is too large, split it further
            if len(chunk_text) > max_chunk_size * 2:
                logger.debug(f"Large {node_type} '{node_name}' ({len(chunk_text)} chars), splitting...")
                # For large functions/classes, use character-based sub-chunking
                from app.utils.chunking import chunk_text
                sub_chunks = chunk_text(chunk_text, file_path, "python", max_chunk_size)
                chunks.extend(sub_chunks)
            else:
                chunks.append(DocumentChunk(
                    id=f"{file_path}:{start_line}:{node_type}:{node_name}",
                    text=chunk_text,
                    file_path=file_path,
                    start_line=start_line,
                    end_line=end_line,
                    language="python",
                    chunk_index=len(chunks),
                ))

    # Handle module-level code (imports, constants, etc.)
    # Find gaps between extracted nodes
    extracted_lines = set()
    for chunk in chunks:
        for line_no in range(chunk.start_line, chunk.end_line + 1):
            extracted_lines.add(line_no)

    # Collect remaining lines (module-level code)
    module_level_lines = []
    for i, line in enumerate(lines, start=1):
        if i not in extracted_lines and line.strip():
            module_level_lines.append((i, line))

    # Group module-level code into chunks
    if module_level_lines:
        current_chunk_lines = []
        start_line_num = module_level_lines[0][0]
        last_line_num = start_line_num

        for line_num, line_content in module_level_lines:
            # Start new chunk if there's a gap in line numbers (non-contiguous)
            if current_chunk_lines and line_num > last_line_num + 1:
                # Save current chunk
                if current_chunk_lines:
                    chunks.append(DocumentChunk(
                        id=f"{file_path}:{start_line_num}:module",
                        text="\n".join(current_chunk_lines).strip(),
                        file_path=file_path,
                        start_line=start_line_num,
                        end_line=last_line_num,
                        language="python",
                        chunk_index=len(chunks),
                    ))
                # Start new chunk
                current_chunk_lines = [line_content]
                start_line_num = line_num
            else:
                current_chunk_lines.append(line_content)

            last_line_num = line_num

            # Check if chunk is getting too large
            chunk_size = sum(len(l) for l in current_chunk_lines)
            if chunk_size > max_chunk_size:
                chunks.append(DocumentChunk(
                    id=f"{file_path}:{start_line_num}:module",
                    text="\n".join(current_chunk_lines).strip(),
                    file_path=file_path,
                    start_line=start_line_num,
                    end_line=line_num,
                    language="python",
                    chunk_index=len(chunks),
                ))
                current_chunk_lines = []
                start_line_num = line_num + 1

        # Add remaining module-level code
        if current_chunk_lines:
            chunks.append(DocumentChunk(
                id=f"{file_path}:{start_line_num}:module",
                text="\n".join(current_chunk_lines).strip(),
                file_path=file_path,
                start_line=start_line_num,
                end_line=module_level_lines[-1][0],
                language="python",
                chunk_index=len(chunks),
            ))

    logger.info(f"AST chunking: {len(chunks)} chunks from {file_path}")
    return chunks


def chunk_javascript_simple(
    code: str,
    file_path: str,
    max_chunk_size: int = 500
) -> List[DocumentChunk]:
    """
    Simple regex-based chunking for JavaScript/TypeScript.
    Splits by function and class declarations.

    This is a simpler alternative to full AST parsing (which would require esprima).
    It identifies common patterns like function declarations, arrow functions, and classes.

    Args:
        code: JavaScript/TypeScript source code
        file_path: Original file path
        max_chunk_size: Maximum characters per chunk (guidance)

    Returns:
        List of DocumentChunk objects
    """
    chunks = []
    lines = code.splitlines()

    # Regex patterns for JS/TS functions and classes
    # Match: function foo(), const foo = (), export function, export const foo = async ()
    function_pattern = r"^\s*(export\s+)?(async\s+)?(function\s+\w+|const\s+\w+\s*=\s*(\([^)]*\)\s*=>|\(.*?\)\s*=>|async\s*\([^)]*\)\s*=>))"
    class_pattern = r"^\s*(export\s+)?(default\s+)?class\s+\w+"

    # Find all function/class starts
    markers: List[Tuple[int, str]] = []  # (line_number, type)
    for i, line in enumerate(lines, start=1):
        if re.search(function_pattern, line):
            markers.append((i, "function"))
        elif re.search(class_pattern, line):
            markers.append((i, "class"))

    # Split by markers
    for idx, (marker_line, marker_type) in enumerate(markers):
        # Determine end line (next marker or end of file)
        if idx + 1 < len(markers):
            end_line = markers[idx + 1][0] - 1
        else:
            end_line = len(lines)

        # Extract chunk
        chunk_lines = lines[marker_line - 1:end_line]
        chunk_text = "\n".join(chunk_lines).strip()

        # If chunk is too large, fall back to character chunking
        if len(chunk_text) > max_chunk_size * 2:
            from app.utils.chunking import chunk_text
            sub_chunks = chunk_text(chunk_text, file_path, "javascript", max_chunk_size)
            chunks.extend(sub_chunks)
        else:
            chunks.append(DocumentChunk(
                id=f"{file_path}:{marker_line}:{marker_type}",
                text=chunk_text,
                file_path=file_path,
                start_line=marker_line,
                end_line=end_line,
                language="javascript",
                chunk_index=len(chunks),
            ))

    # Fall back to character-based if no markers found
    if not chunks:
        logger.debug(f"No JS/TS functions/classes found in {file_path}, using character chunking")
        from app.utils.chunking import chunk_text
        return chunk_text(code, file_path, "javascript", max_chunk_size)

    logger.info(f"JS/TS chunking: {len(chunks)} chunks from {file_path}")
    return chunks


def chunk_markdown_by_headers(
    content: str,
    file_path: str,
    max_chunk_size: int = 500
) -> List[DocumentChunk]:
    """
    Chunk Markdown by headers (##, ###, etc.).
    Preserves document structure and semantic sections.

    Args:
        content: Markdown content
        file_path: Original file path
        max_chunk_size: Maximum characters per chunk (guidance)

    Returns:
        List of DocumentChunk objects representing sections
    """
    chunks = []
    lines = content.splitlines()

    # Find header lines (# Header, ## Header, etc.)
    header_indices: List[Tuple[int, int]] = []  # (line_number, header_level)
    for i, line in enumerate(lines, start=1):
        match = re.match(r"^(#{1,6})\s+", line)
        if match:
            header_level = len(match.group(1))
            header_indices.append((i, header_level))

    # Split by headers
    for idx, (start_line, level) in enumerate(header_indices):
        # Determine end line (next header of same or higher level, or end of file)
        end_line = len(lines)
        for next_line, next_level in header_indices[idx + 1:]:
            if next_level <= level:
                end_line = next_line - 1
                break

        # Extract section
        section_lines = lines[start_line - 1:end_line]
        section_text = "\n".join(section_lines).strip()

        # If section is too large, split it further
        if len(section_text) > max_chunk_size * 2:
            logger.debug(f"Large markdown section ({len(section_text)} chars), splitting...")
            from app.utils.chunking import chunk_text
            sub_chunks = chunk_text(section_text, file_path, "markdown", max_chunk_size)
            chunks.extend(sub_chunks)
        else:
            chunks.append(DocumentChunk(
                id=f"{file_path}:{start_line}:section",
                text=section_text,
                file_path=file_path,
                start_line=start_line,
                end_line=end_line,
                language="markdown",
                chunk_index=len(chunks),
            ))

    # Handle content before first header (if any)
    if header_indices and header_indices[0][0] > 1:
        preamble_lines = lines[:header_indices[0][0] - 1]
        preamble_text = "\n".join(preamble_lines).strip()
        if preamble_text:
            chunks.insert(0, DocumentChunk(
                id=f"{file_path}:1:preamble",
                text=preamble_text,
                file_path=file_path,
                start_line=1,
                end_line=header_indices[0][0] - 1,
                language="markdown",
                chunk_index=0,
            ))

    # Fall back if no headers found
    if not chunks:
        logger.debug(f"No markdown headers found in {file_path}, using character chunking")
        from app.utils.chunking import chunk_text
        return chunk_text(content, file_path, "markdown", max_chunk_size)

    # Re-index chunks
    for i, chunk in enumerate(chunks):
        chunk.chunk_index = i

    logger.info(f"Markdown chunking: {len(chunks)} chunks from {file_path}")
    return chunks

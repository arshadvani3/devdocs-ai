"""
File parsing utilities for extracting content from code files.

This module handles reading and parsing various file types,
extracting raw text content for further processing.
"""

import logging
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


# Language detection based on file extension
EXTENSION_TO_LANGUAGE = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".java": "java",
    ".go": "go",
    ".rs": "rust",
    ".cpp": "cpp",
    ".c": "c",
    ".h": "c",
    ".hpp": "cpp",
    ".md": "markdown",
    ".txt": "text",
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
}


def detect_language(file_path: str) -> str:
    """
    Detect programming language from file extension.

    Args:
        file_path: Path to the file

    Returns:
        Language identifier string (e.g., 'python', 'javascript')
    """
    extension = Path(file_path).suffix.lower()
    return EXTENSION_TO_LANGUAGE.get(extension, "unknown")


def is_binary_file(file_path: Path) -> bool:
    """
    Check if a file is binary (not text).

    Uses a simple heuristic: reads first 8192 bytes and checks for null bytes.

    Args:
        file_path: Path to the file to check

    Returns:
        True if file appears to be binary, False otherwise
    """
    try:
        with open(file_path, "rb") as f:
            chunk = f.read(8192)
            # Binary files typically contain null bytes
            return b"\x00" in chunk
    except Exception as e:
        logger.warning(f"Error checking if file is binary {file_path}: {e}")
        return True  # Assume binary if we can't read it


def read_file_content(file_path: str, max_size_mb: int = 10) -> Optional[str]:
    """
    Read text content from a file with safety checks.

    Args:
        file_path: Path to the file to read
        max_size_mb: Maximum file size in megabytes (default: 10MB)

    Returns:
        File content as string, or None if file cannot be read

    Raises:
        ValueError: If file is too large or is binary
    """
    path = Path(file_path)

    # Check if file exists
    if not path.exists():
        logger.error(f"File does not exist: {file_path}")
        return None

    # Check file size
    file_size_mb = path.stat().st_size / (1024 * 1024)
    if file_size_mb > max_size_mb:
        raise ValueError(
            f"File too large: {file_size_mb:.2f}MB (max: {max_size_mb}MB)"
        )

    # Check if binary
    if is_binary_file(path):
        raise ValueError(f"Cannot process binary file: {file_path}")

    # Try to read with different encodings
    encodings = ["utf-8", "latin-1", "cp1252"]

    for encoding in encodings:
        try:
            with open(path, "r", encoding=encoding) as f:
                content = f.read()
            logger.info(f"Successfully read {file_path} with {encoding} encoding")
            return content
        except UnicodeDecodeError:
            continue
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
            return None

    logger.error(f"Could not decode file {file_path} with any encoding")
    return None


def parse_file(file_path: str) -> Tuple[Optional[str], str]:
    """
    Parse a file and return its content and detected language.

    This is the main entry point for file parsing. It handles
    language detection, content extraction, and error handling.

    Args:
        file_path: Path to the file to parse

    Returns:
        Tuple of (content, language). Content is None if parsing failed.

    Example:
        >>> content, lang = parse_file("src/main.py")
        >>> if content:
        ...     print(f"Parsed {lang} file with {len(content)} characters")
    """
    try:
        # Detect language from extension
        language = detect_language(file_path)

        # Read file content
        content = read_file_content(file_path)

        if content is None:
            logger.warning(f"Failed to read file: {file_path}")
            return None, language

        # Basic validation
        if not content.strip():
            logger.warning(f"File is empty: {file_path}")
            return None, language

        logger.info(
            f"Successfully parsed {file_path} ({language}): "
            f"{len(content)} chars, {len(content.splitlines())} lines"
        )

        return content, language

    except ValueError as e:
        # Re-raise validation errors (file too large, binary, etc.)
        raise
    except Exception as e:
        logger.error(f"Unexpected error parsing {file_path}: {e}")
        return None, "unknown"


def count_lines(content: str) -> int:
    """
    Count the number of lines in content.

    Args:
        content: Text content

    Returns:
        Number of lines
    """
    return len(content.splitlines())


def validate_file_extension(file_path: str, allowed_extensions: list[str]) -> bool:
    """
    Check if file has an allowed extension.

    Args:
        file_path: Path to the file
        allowed_extensions: List of allowed extensions (e.g., ['.py', '.js'])

    Returns:
        True if extension is allowed, False otherwise
    """
    extension = Path(file_path).suffix.lower()
    return extension in allowed_extensions

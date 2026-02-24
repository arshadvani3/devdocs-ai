"""
Document ingestion service.

This module orchestrates the complete document ingestion pipeline:
file upload → parsing → chunking → embedding → storage.
"""

import logging
from pathlib import Path
from typing import List, Optional
import tempfile
import zipfile
import shutil
from datetime import datetime

from app.config import settings
from app.models import DocumentChunk, FileMetadata
from app.utils.parsing import parse_file, validate_file_extension, count_lines
from app.utils.chunking import smart_chunk_code
from app.services.retrieval import get_vector_store

logger = logging.getLogger(__name__)


class IngestionService:
    """
    Service for ingesting documents into the knowledge base.

    This class coordinates the entire pipeline from file upload
    to storage in the vector database.
    """

    def __init__(self, collection_name: Optional[str] = None):
        """
        Initialize ingestion service.

        Args:
            collection_name: Target collection name (defaults to config)
        """
        self.collection_name = collection_name
        self.vector_store = get_vector_store(collection_name)
        self.allowed_extensions = settings.supported_extensions_list

    async def ingest_file(
        self,
        file_path: str,
        overwrite: bool = False,
    ) -> tuple[List[DocumentChunk], FileMetadata]:
        """
        Ingest a single file into the knowledge base.

        Args:
            file_path: Path to the file to ingest
            overwrite: If True, delete existing chunks for this file first

        Returns:
            Tuple of (list of chunks created, file metadata)

        Raises:
            ValueError: If file type is not supported or file is invalid
        """
        # Validate file extension
        if not validate_file_extension(file_path, self.allowed_extensions):
            raise ValueError(
                f"Unsupported file type. Allowed: {', '.join(self.allowed_extensions)}"
            )

        logger.info(f"Starting ingestion for: {file_path}")

        # Parse file
        try:
            content, language = parse_file(file_path)
        except ValueError as e:
            # Re-raise validation errors (binary file, too large, etc.)
            logger.error(f"File validation failed for {file_path}: {e}")
            raise

        if content is None:
            raise ValueError(f"Could not read file: {file_path}")

        # Chunk the content using smart chunking
        chunks = smart_chunk_code(
            text=content,
            file_path=file_path,
            language=language,
            max_chunk_size=settings.max_chunk_size,
        )

        if not chunks:
            raise ValueError(f"No chunks generated from file: {file_path}")

        # Delete existing chunks if overwrite is True
        if overwrite:
            logger.info(f"Overwrite enabled, deleting existing chunks for {file_path}")
            self.vector_store.delete_by_file_path(file_path)

        # Add chunks to vector store
        num_added = await self.vector_store.add_documents(chunks)

        # Create file metadata
        file_size = Path(file_path).stat().st_size
        metadata = FileMetadata(
            file_path=file_path,
            file_size=file_size,
            language=language,
            num_chunks=len(chunks),
            processed_at=datetime.utcnow(),
        )

        logger.info(
            f"Successfully ingested {file_path}: "
            f"{num_added} chunks, {file_size} bytes, {language}"
        )

        return chunks, metadata

    async def ingest_multiple_files(
        self,
        file_paths: List[str],
        overwrite: bool = False,
    ) -> tuple[int, int, List[FileMetadata]]:
        """
        Ingest multiple files.

        Args:
            file_paths: List of file paths to ingest
            overwrite: If True, delete existing chunks for each file first

        Returns:
            Tuple of (files_processed, total_chunks, list of file metadata)
        """
        files_processed = 0
        total_chunks = 0
        all_metadata: List[FileMetadata] = []
        errors: List[str] = []

        for file_path in file_paths:
            try:
                chunks, metadata = await self.ingest_file(file_path, overwrite)
                files_processed += 1
                total_chunks += len(chunks)
                all_metadata.append(metadata)
            except Exception as e:
                logger.error(f"Error ingesting {file_path}: {e}")
                errors.append(f"{file_path}: {str(e)}")

        if errors:
            logger.warning(f"Encountered {len(errors)} errors during ingestion")
            for error in errors:
                logger.warning(f"  - {error}")

        logger.info(
            f"Batch ingestion complete: {files_processed}/{len(file_paths)} files, "
            f"{total_chunks} total chunks"
        )

        return files_processed, total_chunks, all_metadata

    async def ingest_directory(
        self,
        directory_path: str,
        recursive: bool = True,
        overwrite: bool = False,
    ) -> tuple[int, int, List[FileMetadata]]:
        """
        Ingest all supported files from a directory.

        Args:
            directory_path: Path to the directory
            recursive: If True, search subdirectories
            overwrite: If True, delete existing chunks for each file first

        Returns:
            Tuple of (files_processed, total_chunks, list of file metadata)
        """
        directory = Path(directory_path)

        if not directory.exists():
            raise ValueError(f"Directory does not exist: {directory_path}")

        if not directory.is_dir():
            raise ValueError(f"Not a directory: {directory_path}")

        # Find all supported files
        file_paths: List[str] = []

        if recursive:
            for ext in self.allowed_extensions:
                file_paths.extend(
                    str(p) for p in directory.rglob(f"*{ext}")
                )
        else:
            for ext in self.allowed_extensions:
                file_paths.extend(
                    str(p) for p in directory.glob(f"*{ext}")
                )

        logger.info(f"Found {len(file_paths)} files in {directory_path}")

        return await self.ingest_multiple_files(file_paths, overwrite)

    async def ingest_zip(
        self,
        zip_path: str,
        overwrite: bool = False,
    ) -> tuple[int, int, List[FileMetadata]]:
        """
        Ingest files from a ZIP archive.

        Args:
            zip_path: Path to the ZIP file
            overwrite: If True, delete existing chunks for each file first

        Returns:
            Tuple of (files_processed, total_chunks, list of file metadata)

        Raises:
            ValueError: If file is not a valid ZIP
        """
        if not zipfile.is_zipfile(zip_path):
            raise ValueError(f"Not a valid ZIP file: {zip_path}")

        # Create temporary directory to extract files
        temp_dir = tempfile.mkdtemp(prefix="devdocs_")

        try:
            logger.info(f"Extracting ZIP to temporary directory: {temp_dir}")

            # Extract ZIP
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)

            # Ingest all files from the extracted directory
            result = await self.ingest_directory(
                temp_dir,
                recursive=True,
                overwrite=overwrite,
            )

            logger.info(f"Successfully processed ZIP file: {zip_path}")
            return result

        finally:
            # Clean up temporary directory
            try:
                shutil.rmtree(temp_dir)
                logger.debug(f"Cleaned up temporary directory: {temp_dir}")
            except Exception as e:
                logger.warning(f"Could not clean up temp directory {temp_dir}: {e}")

    async def ingest_from_upload(
        self,
        file_content: bytes,
        filename: str,
        overwrite: bool = False,
    ) -> tuple[int, int, List[FileMetadata]]:
        """
        Ingest a file from an upload (FastAPI UploadFile).

        This method handles both single files and ZIP archives.

        Args:
            file_content: Raw file bytes
            filename: Original filename
            overwrite: If True, delete existing chunks for each file first

        Returns:
            Tuple of (files_processed, total_chunks, list of file metadata)
        """
        # Create temporary file
        temp_file = tempfile.NamedTemporaryFile(
            delete=False,
            suffix=Path(filename).suffix
        )

        try:
            # Write uploaded content to temp file
            temp_file.write(file_content)
            temp_file.close()

            logger.info(f"Processing uploaded file: {filename}")

            # Check if it's a ZIP file
            if filename.endswith('.zip') and zipfile.is_zipfile(temp_file.name):
                return await self.ingest_zip(temp_file.name, overwrite)
            else:
                # Ingest as single file
                chunks, metadata = await self.ingest_file(temp_file.name, overwrite)
                return 1, len(chunks), [metadata]

        finally:
            # Clean up temp file
            try:
                Path(temp_file.name).unlink()
            except Exception as e:
                logger.warning(f"Could not delete temp file {temp_file.name}: {e}")


def get_ingestion_service(collection_name: Optional[str] = None) -> IngestionService:
    """
    Factory function to get an IngestionService instance.

    Args:
        collection_name: Optional collection name

    Returns:
        IngestionService instance
    """
    return IngestionService(collection_name=collection_name)

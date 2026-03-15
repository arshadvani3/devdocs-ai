"""
GitHub repository ingestion service.

This module clones public GitHub repositories and feeds them through
the existing document ingestion pipeline (chunking, embedding, Qdrant storage).
"""

import logging
import re
import time
import tempfile
import shutil
from pathlib import Path
from typing import Optional

import httpx
import git

from app.services.ingestion import get_ingestion_service

logger = logging.getLogger(__name__)

# Repos larger than this (in KB) trigger a warning
_SIZE_WARN_KB = 200 * 1024   # 200 MB
# Repos larger than this are rejected outright
_SIZE_MAX_KB = 500 * 1024    # 500 MB

_GITHUB_URL_RE = re.compile(
    r'^https?://github\.com/([a-zA-Z0-9_.-]+)/([a-zA-Z0-9_.-]+?)(?:\.git)?/?$'
)


def validate_github_url(url: str) -> bool:
    """
    Check that a URL is a valid public GitHub repository URL.

    Args:
        url: URL string to validate

    Returns:
        True if it matches https://github.com/owner/repo pattern
    """
    return bool(_GITHUB_URL_RE.match(url))


def get_repo_name(url: str) -> str:
    """
    Extract the "owner/repo" slug from a GitHub URL.

    Args:
        url: GitHub repository URL

    Returns:
        Slug like "expressjs/express"

    Raises:
        ValueError: If the URL doesn't match the expected pattern
    """
    match = _GITHUB_URL_RE.match(url)
    if not match:
        raise ValueError(f"Cannot extract repo name from URL: {url}")
    owner, repo = match.group(1), match.group(2)
    return f"{owner}/{repo}"


def _collection_name_from_repo(repo_slug: str) -> str:
    """Convert 'owner/repo' slug to a Qdrant-safe collection name."""
    # Replace slashes and dots with hyphens, lowercase
    return re.sub(r'[^a-zA-Z0-9-]', '-', repo_slug).lower()


async def _check_repo_size(repo_slug: str) -> int:
    """
    Query the GitHub API to get the repository size in KB.

    Args:
        repo_slug: "owner/repo" string

    Returns:
        Repository size in KB (0 if API is unavailable)

    Raises:
        ValueError: If the repository is not found (may be private)
    """
    api_url = f"https://api.github.com/repos/{repo_slug}"
    headers = {"Accept": "application/vnd.github.v3+json"}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(api_url, headers=headers)

            if response.status_code == 404:
                raise ValueError(
                    f"Repository '{repo_slug}' not found. "
                    "It may be private or the URL may be incorrect."
                )
            if response.status_code == 403:
                logger.warning("GitHub API rate limited — skipping size check")
                return 0

            response.raise_for_status()
            data = response.json()
            return data.get("size", 0)  # size is in KB
    except httpx.TimeoutException:
        logger.warning("GitHub API timeout — skipping size check")
        return 0


def clone_repo(url: str, dest_path: Path) -> Path:
    """
    Shallow-clone a GitHub repository to dest_path.

    Uses depth=1 to fetch only the latest commit, keeping it fast.

    Args:
        url: GitHub repository URL
        dest_path: Local destination directory (must not already exist)

    Returns:
        Path to the cloned repository

    Raises:
        git.GitCommandError: If the clone fails (e.g., private repo, bad URL)
    """
    logger.info(f"Cloning {url} → {dest_path} (shallow, depth=1)")
    git.Repo.clone_from(
        url,
        str(dest_path),
        depth=1,
        no_checkout=False,
    )
    logger.info(f"Clone complete: {dest_path}")
    return dest_path


def cleanup(temp_path: Path) -> None:
    """
    Remove the temporary clone directory.

    Args:
        temp_path: Path to remove (must be a directory)
    """
    try:
        shutil.rmtree(str(temp_path))
        logger.debug(f"Cleaned up temp directory: {temp_path}")
    except Exception as e:
        logger.warning(f"Could not clean up {temp_path}: {e}")


async def ingest_github_repo(
    repo_url: str,
    collection_name: Optional[str] = None,
) -> dict:
    """
    Clone a public GitHub repository and ingest it into the knowledge base.

    Validates the URL, optionally checks repo size, clones with depth=1,
    passes the directory to the existing ingestion pipeline, then cleans up.

    Args:
        repo_url: Public GitHub repository URL
                  (e.g. "https://github.com/expressjs/express")
        collection_name: Qdrant collection to store into.
                         Defaults to a slug derived from the repo name.

    Returns:
        dict with keys:
            repo_url, repo_name, total_files, processed_files,
            total_chunks, collection_name, time_taken_seconds

    Raises:
        ValueError: On invalid URL, private repo, or repo too large (>500MB)
        Exception:  On network failures or ingestion errors
    """
    start_time = time.time()

    # ── Validate URL ──────────────────────────────────────────────────────────
    if not validate_github_url(repo_url):
        raise ValueError(
            f"Invalid GitHub URL: '{repo_url}'. "
            "Expected format: https://github.com/owner/repo"
        )

    repo_slug = get_repo_name(repo_url)
    logger.info(f"Starting GitHub ingestion for: {repo_slug}")

    # ── Determine collection name ─────────────────────────────────────────────
    if collection_name is None:
        collection_name = _collection_name_from_repo(repo_slug)

    # ── Pre-clone size check via GitHub API ───────────────────────────────────
    size_kb = await _check_repo_size(repo_slug)

    if size_kb > _SIZE_MAX_KB:
        raise ValueError(
            f"Repository '{repo_slug}' is too large to index "
            f"({size_kb // 1024} MB > 500 MB limit)."
        )

    if size_kb > _SIZE_WARN_KB:
        logger.warning(
            f"Repository '{repo_slug}' is large ({size_kb // 1024} MB). "
            "Ingestion may take a while."
        )

    # ── Clone to temp directory ───────────────────────────────────────────────
    temp_dir = Path(tempfile.mkdtemp(prefix="devdocs_gh_"))
    clone_dest = temp_dir / "repo"

    try:
        logger.info("Cloning repo...")
        try:
            clone_repo(repo_url, clone_dest)
        except git.GitCommandError as e:
            err_str = str(e)
            if "Repository not found" in err_str or "authentication" in err_str.lower():
                raise ValueError(
                    f"Could not clone '{repo_url}'. "
                    "The repository may be private or require authentication."
                ) from e
            raise

        # ── Ingest via existing pipeline ──────────────────────────────────────
        logger.info("Chunking files and generating embeddings...")
        ingestion_service = get_ingestion_service(collection_name)

        # Pre-create collection so every file can upsert without hitting 404
        ingestion_service.vector_store._ensure_collection()

        files_processed, total_chunks, _ = await ingestion_service.ingest_directory(
            directory_path=str(clone_dest),
            recursive=True,
            overwrite=True,
        )

        # Count total supported files found (before filtering)
        from app.config import settings
        total_files = sum(
            1
            for ext in settings.supported_extensions_list
            for _ in clone_dest.rglob(f"*{ext}")
        )

        time_taken = round(time.time() - start_time, 2)

        logger.info(
            f"GitHub ingestion complete: {repo_slug} → "
            f"{files_processed} files, {total_chunks} chunks, {time_taken}s"
        )

        return {
            "repo_url": repo_url,
            "repo_name": repo_slug,
            "total_files": total_files,
            "processed_files": files_processed,
            "total_chunks": total_chunks,
            "collection_name": collection_name,
            "time_taken_seconds": time_taken,
        }

    finally:
        cleanup(temp_dir)

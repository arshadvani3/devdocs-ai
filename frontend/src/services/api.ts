/**
 * API service for REST endpoints (file upload, health check).
 * WebSocket streaming is handled separately via useWebSocket hook.
 */

import type { UploadResponse, HealthResponse } from '../types';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

/**
 * Upload files to the backend for ingestion.
 * Accepts single files or ZIP archives.
 */
export async function uploadFiles(
  files: FileList,
  collectionName?: string,
  overwrite: boolean = false
): Promise<UploadResponse> {
  const formData = new FormData();

  // Add the first file (support for single file or ZIP)
  formData.append('file', files[0]);

  if (collectionName) {
    formData.append('collection_name', collectionName);
  }
  formData.append('overwrite', String(overwrite));

  const response = await fetch(`${API_BASE}/ingest`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: 'Upload failed' }));
    throw new Error(error.error || `Upload failed with status ${response.status}`);
  }

  return response.json();
}

/**
 * Check the health status of backend services.
 */
export async function getHealth(): Promise<HealthResponse> {
  const response = await fetch(`${API_BASE}/health`);

  if (!response.ok) {
    throw new Error(`Health check failed with status ${response.status}`);
  }

  return response.json();
}

// ─── GitHub ingestion types ───────────────────────────────────────────────────

export interface GitHubIngestResponse {
  success: boolean;
  repo_url: string;
  repo_name: string;
  total_files: number;
  processed_files: number;
  total_chunks: number;
  collection_name: string;
  time_taken_seconds: number;
}

export interface GitHubStatusResponse {
  indexed: boolean;
  collection_name: string;
  total_chunks: number;
}

// ─── GitHub ingestion API calls ───────────────────────────────────────────────

/**
 * Clone and index a public GitHub repository.
 */
export async function ingestGitHubRepo(repoUrl: string): Promise<GitHubIngestResponse> {
  const response = await fetch(`${API_BASE}/ingest/github`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ repo_url: repoUrl }),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Ingestion failed' }));
    throw new Error(error.detail || `Request failed with status ${response.status}`);
  }

  return response.json();
}

/**
 * Check whether a GitHub repo has already been indexed.
 * repo_name should use hyphens (e.g. "expressjs-express").
 */
export async function checkGitHubRepoStatus(repoName: string): Promise<GitHubStatusResponse> {
  const response = await fetch(`${API_BASE}/ingest/github/status/${encodeURIComponent(repoName)}`);

  if (!response.ok) {
    throw new Error(`Status check failed with status ${response.status}`);
  }

  return response.json();
}

/**
 * Get collection statistics.
 */
export async function getStats(collectionName?: string): Promise<any> {
  const url = new URL(`${API_BASE}/stats`);
  if (collectionName) {
    url.searchParams.append('collection_name', collectionName);
  }

  const response = await fetch(url.toString());

  if (!response.ok) {
    throw new Error(`Stats request failed with status ${response.status}`);
  }

  return response.json();
}

/**
 * UploadPanel component for ingesting code into the knowledge base.
 * Tab 1: Upload Files — drag-and-drop or file picker (unchanged)
 * Tab 2: GitHub Repo — clone & index a public GitHub repository
 */

import { useState, useRef } from 'react';
import type { DragEvent, ChangeEvent } from 'react';
import { uploadFiles, ingestGitHubRepo } from '../services/api';
import type { UploadResponse } from '../types';
import type { GitHubIngestResponse } from '../services/api';

type ActiveTab = 'upload' | 'github';

interface UploadPanelProps {
  onUploadSuccess?: (response: UploadResponse) => void;
  onGitHubSuccess?: (collectionName: string) => void;
}

// ─── GitHub status message steps ──────────────────────────────────────────────
type GitHubStatus =
  | 'idle'
  | 'cloning'
  | 'chunking'
  | 'embedding'
  | 'done'
  | 'error';

const STATUS_LABELS: Record<GitHubStatus, string> = {
  idle: '',
  cloning: 'Cloning repo...',
  chunking: 'Chunking files...',
  embedding: 'Generating embeddings...',
  done: 'Done!',
  error: '',
};

export function UploadPanel({ onUploadSuccess, onGitHubSuccess }: UploadPanelProps) {
  // ── Shared state ─────────────────────────────────────────────────────────────
  const [activeTab, setActiveTab] = useState<ActiveTab>('upload');

  // ── File upload state (Tab 1 — unchanged) ────────────────────────────────────
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadHistory, setUploadHistory] = useState<UploadResponse[]>([]);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // ── GitHub state (Tab 2) ─────────────────────────────────────────────────────
  const [githubUrl, setGithubUrl] = useState('');
  const [githubStatus, setGithubStatus] = useState<GitHubStatus>('idle');
  const [githubError, setGithubError] = useState<string | null>(null);
  const [githubResult, setGithubResult] = useState<GitHubIngestResponse | null>(null);

  // ── File upload handlers (unchanged from original) ───────────────────────────
  const handleDragOver = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = async (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
    const files = e.dataTransfer.files;
    if (files.length > 0) {
      await handleUpload(files);
    }
  };

  const handleFileSelect = async (e: ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      await handleUpload(files);
    }
  };

  const handleUpload = async (files: FileList) => {
    setIsUploading(true);
    setUploadError(null);

    try {
      const response = await uploadFiles(files);
      setUploadHistory((prev) => [response, ...prev]);
      if (onUploadSuccess) {
        onUploadSuccess(response);
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Upload failed';
      setUploadError(errorMessage);
      console.error('Upload error:', err);
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const openFilePicker = () => {
    fileInputRef.current?.click();
  };

  // ── GitHub clone handler ──────────────────────────────────────────────────────
  const handleGitHubIngest = async () => {
    if (!githubUrl.trim()) return;

    setGithubError(null);
    setGithubResult(null);
    setGithubStatus('cloning');

    try {
      // The backend handles all phases; we simulate progress steps on a timer
      // while the real request runs, then jump to 'done' on completion.
      const progressSteps: GitHubStatus[] = ['cloning', 'chunking', 'embedding'];
      let stepIdx = 0;

      const progressTimer = setInterval(() => {
        stepIdx++;
        if (stepIdx < progressSteps.length) {
          setGithubStatus(progressSteps[stepIdx]);
        }
      }, 4000); // advance every 4 s

      const result = await ingestGitHubRepo(githubUrl.trim());

      clearInterval(progressTimer);
      setGithubStatus('done');
      setGithubResult(result);

      // Notify parent so it can switch the active collection automatically
      if (onGitHubSuccess) {
        onGitHubSuccess(result.collection_name);
      }
    } catch (err) {
      setGithubStatus('error');
      setGithubError(err instanceof Error ? err.message : 'Ingestion failed');
      console.error('GitHub ingestion error:', err);
    }
  };

  const resetGitHub = () => {
    setGithubUrl('');
    setGithubStatus('idle');
    setGithubError(null);
    setGithubResult(null);
  };

  // ── Render ────────────────────────────────────────────────────────────────────
  return (
    <div className="h-full flex flex-col bg-gray-800 border-r border-gray-700">
      {/* Header */}
      <div className="p-4 border-b border-gray-700">
        <h2 className="text-lg font-semibold text-gray-100">Add Documents</h2>
        <p className="text-sm text-gray-400 mt-1">
          Upload files or index a GitHub repo to build your knowledge base
        </p>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-gray-700">
        <button
          onClick={() => setActiveTab('upload')}
          className={`flex-1 py-2 text-sm font-medium transition-colors ${
            activeTab === 'upload'
              ? 'text-blue-400 border-b-2 border-blue-400 bg-gray-800'
              : 'text-gray-400 hover:text-gray-200'
          }`}
        >
          Upload Files
        </button>
        <button
          onClick={() => setActiveTab('github')}
          className={`flex-1 py-2 text-sm font-medium transition-colors ${
            activeTab === 'github'
              ? 'text-blue-400 border-b-2 border-blue-400 bg-gray-800'
              : 'text-gray-400 hover:text-gray-200'
          }`}
        >
          GitHub Repo
        </button>
      </div>

      {/* ── Tab 1: Upload Files (original, unchanged) ─────────────────────── */}
      {activeTab === 'upload' && (
        <>
          <div className="p-4">
            <div
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors cursor-pointer ${
                isDragging
                  ? 'border-blue-500 bg-blue-500/10'
                  : 'border-gray-600 hover:border-gray-500 bg-gray-900/50'
              }`}
              onClick={openFilePicker}
            >
              <input
                ref={fileInputRef}
                type="file"
                onChange={handleFileSelect}
                accept=".py,.js,.ts,.java,.go,.md,.tsx,.jsx,.cpp,.c,.h,.rs,.zip"
                className="hidden"
              />

              {isUploading ? (
                <div className="flex flex-col items-center">
                  <svg className="animate-spin h-12 w-12 text-blue-500 mb-4" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  <p className="text-gray-300 font-medium">Uploading...</p>
                </div>
              ) : (
                <div className="flex flex-col items-center">
                  <svg className="w-12 h-12 text-gray-400 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                  </svg>
                  <p className="text-gray-300 font-medium mb-2">
                    Drop files here or click to browse
                  </p>
                  <p className="text-sm text-gray-500">
                    Supports: .py, .js, .ts, .java, .go, .md, .zip, etc.
                  </p>
                </div>
              )}
            </div>

            {uploadError && (
              <div className="mt-4 p-3 bg-red-500/10 border border-red-500/50 rounded-lg">
                <p className="text-sm text-red-400">{uploadError}</p>
              </div>
            )}
          </div>

          {/* Upload history */}
          <div className="flex-1 overflow-y-auto p-4 space-y-3 scrollbar-thin">
            <h3 className="text-sm font-semibold text-gray-400 mb-3">Upload History</h3>
            {uploadHistory.length === 0 ? (
              <p className="text-sm text-gray-500 text-center py-8">No uploads yet</p>
            ) : (
              uploadHistory.map((upload, idx) => (
                <div
                  key={idx}
                  className="p-3 bg-gray-900/50 rounded-lg border border-gray-700"
                >
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <svg className="w-5 h-5 text-green-500 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                      </svg>
                      <span className="text-sm font-medium text-gray-200">
                        {upload.message}
                      </span>
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-2 text-xs text-gray-400">
                    <div>
                      <span className="font-medium">Files:</span> {upload.files_processed}
                    </div>
                    <div>
                      <span className="font-medium">Chunks:</span> {upload.total_chunks}
                    </div>
                    <div className="col-span-2">
                      <span className="font-medium">Time:</span> {upload.processing_time_seconds}s
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </>
      )}

      {/* ── Tab 2: GitHub Repo ─────────────────────────────────────────────── */}
      {activeTab === 'github' && (
        <div className="flex-1 flex flex-col p-4 space-y-4">
          {/* URL input */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Repository URL
            </label>
            <input
              type="url"
              value={githubUrl}
              onChange={(e) => setGithubUrl(e.target.value)}
              placeholder="https://github.com/username/repo"
              disabled={githubStatus !== 'idle' && githubStatus !== 'error'}
              className="w-full px-3 py-2 bg-gray-900 border border-gray-600 rounded-lg
                         text-gray-100 placeholder-gray-500 text-sm
                         focus:outline-none focus:border-blue-500
                         disabled:opacity-50 disabled:cursor-not-allowed"
              onKeyDown={(e) => {
                if (e.key === 'Enter' && githubStatus === 'idle') {
                  handleGitHubIngest();
                }
              }}
            />
          </div>

          {/* Clone & Index button */}
          {(githubStatus === 'idle' || githubStatus === 'error') && (
            <button
              onClick={githubStatus === 'error' ? resetGitHub : handleGitHubIngest}
              disabled={!githubUrl.trim() && githubStatus === 'idle'}
              className="w-full py-2 px-4 bg-blue-600 hover:bg-blue-700
                         disabled:bg-gray-700 disabled:cursor-not-allowed
                         text-white text-sm font-medium rounded-lg transition-colors"
            >
              {githubStatus === 'error' ? 'Try Again' : 'Clone & Index'}
            </button>
          )}

          {/* Progress indicator */}
          {githubStatus !== 'idle' && githubStatus !== 'done' && githubStatus !== 'error' && (
            <div className="flex flex-col items-center py-6 space-y-3">
              <svg className="animate-spin h-10 w-10 text-blue-500" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
              <p className="text-sm text-gray-300 font-medium">
                {STATUS_LABELS[githubStatus]}
              </p>
              <p className="text-xs text-gray-500">This may take a minute for large repos</p>

              {/* Step progress pills */}
              <div className="flex gap-2 mt-2">
                {(['cloning', 'chunking', 'embedding'] as GitHubStatus[]).map((step) => {
                  const steps: GitHubStatus[] = ['cloning', 'chunking', 'embedding'];
                  const currentIdx = steps.indexOf(githubStatus);
                  const stepIdx = steps.indexOf(step);
                  const isDone = stepIdx < currentIdx;
                  const isActive = step === githubStatus;
                  return (
                    <span
                      key={step}
                      className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                        isDone
                          ? 'bg-green-500/20 text-green-400'
                          : isActive
                          ? 'bg-blue-500/20 text-blue-400'
                          : 'bg-gray-700 text-gray-500'
                      }`}
                    >
                      {STATUS_LABELS[step]}
                    </span>
                  );
                })}
              </div>
            </div>
          )}

          {/* Error state */}
          {githubStatus === 'error' && githubError && (
            <div className="p-3 bg-red-500/10 border border-red-500/50 rounded-lg">
              <p className="text-sm font-medium text-red-400 mb-1">Ingestion failed</p>
              <p className="text-xs text-red-300">{githubError}</p>
            </div>
          )}

          {/* Success state */}
          {githubStatus === 'done' && githubResult && (
            <div className="p-4 bg-green-500/10 border border-green-500/30 rounded-lg space-y-3">
              <div className="flex items-center gap-2">
                <svg className="w-5 h-5 text-green-500 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                </svg>
                <p className="text-sm font-semibold text-green-400">
                  {githubResult.repo_name} indexed!
                </p>
              </div>

              <div className="grid grid-cols-2 gap-2 text-xs text-gray-400">
                <div>
                  <span className="font-medium text-gray-300">Files processed:</span>{' '}
                  {githubResult.processed_files} / {githubResult.total_files}
                </div>
                <div>
                  <span className="font-medium text-gray-300">Chunks created:</span>{' '}
                  {githubResult.total_chunks}
                </div>
                <div>
                  <span className="font-medium text-gray-300">Collection:</span>{' '}
                  {githubResult.collection_name}
                </div>
                <div>
                  <span className="font-medium text-gray-300">Time:</span>{' '}
                  {githubResult.time_taken_seconds}s
                </div>
              </div>

              <p className="text-xs text-green-400/80">
                Collection activated — start asking questions!
              </p>

              <button
                onClick={resetGitHub}
                className="w-full py-1.5 text-xs text-gray-400 hover:text-gray-200
                           border border-gray-700 hover:border-gray-500 rounded-lg
                           transition-colors"
              >
                Index another repo
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

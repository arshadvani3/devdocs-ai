/**
 * UploadPanel component for ingesting code into the knowledge base.
 * Tab 1: Upload Files — drag-and-drop or file picker
 * Tab 2: GitHub Repo — clone & index a public GitHub repository
 */

import { useState, useRef } from 'react';
import type { DragEvent, ChangeEvent } from 'react';
import { uploadFiles, ingestGitHubRepo } from '../services/api';
import type { UploadResponse } from '../types';
import type { GitHubIngestResponse } from '../services/api';

type ActiveTab = 'upload' | 'github';
type GitHubStatus = 'idle' | 'cloning' | 'chunking' | 'embedding' | 'done' | 'error';

const STATUS_LABELS: Record<GitHubStatus, string> = {
  idle: '',
  cloning: 'Cloning repo…',
  chunking: 'Chunking files…',
  embedding: 'Generating embeddings…',
  done: 'Done!',
  error: '',
};

interface UploadPanelProps {
  onUploadSuccess?: (response: UploadResponse) => void;
  onGitHubSuccess?: (collectionName: string) => void;
}

export function UploadPanel({ onUploadSuccess, onGitHubSuccess }: UploadPanelProps) {
  const [activeTab, setActiveTab] = useState<ActiveTab>('github');

  // File upload state
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadHistory, setUploadHistory] = useState<UploadResponse[]>([]);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // GitHub state
  const [githubUrl, setGithubUrl] = useState('');
  const [githubStatus, setGithubStatus] = useState<GitHubStatus>('idle');
  const [githubError, setGithubError] = useState<string | null>(null);
  const [githubResult, setGithubResult] = useState<GitHubIngestResponse | null>(null);

  // File upload handlers
  const handleDragOver = (e: DragEvent<HTMLDivElement>) => { e.preventDefault(); setIsDragging(true); };
  const handleDragLeave = (e: DragEvent<HTMLDivElement>) => { e.preventDefault(); setIsDragging(false); };

  const handleDrop = async (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files.length > 0) await handleUpload(e.dataTransfer.files);
  };

  const handleFileSelect = async (e: ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) await handleUpload(e.target.files);
  };

  const handleUpload = async (files: FileList) => {
    setIsUploading(true);
    setUploadError(null);
    try {
      const response = await uploadFiles(files);
      setUploadHistory((prev) => [response, ...prev]);
      if (onUploadSuccess) onUploadSuccess(response);
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : 'Upload failed');
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  // GitHub handler
  const handleGitHubIngest = async () => {
    if (!githubUrl.trim()) return;
    setGithubError(null);
    setGithubResult(null);
    setGithubStatus('cloning');

    const steps: GitHubStatus[] = ['cloning', 'chunking', 'embedding'];
    let stepIdx = 0;
    const timer = setInterval(() => {
      stepIdx++;
      if (stepIdx < steps.length) setGithubStatus(steps[stepIdx]);
    }, 4000);

    try {
      const result = await ingestGitHubRepo(githubUrl.trim());
      clearInterval(timer);
      setGithubStatus('done');
      setGithubResult(result);
      if (onGitHubSuccess) onGitHubSuccess(result.collection_name);
    } catch (err) {
      clearInterval(timer);
      setGithubStatus('error');
      setGithubError(err instanceof Error ? err.message : 'Ingestion failed');
    }
  };

  const resetGitHub = () => {
    setGithubUrl('');
    setGithubStatus('idle');
    setGithubError(null);
    setGithubResult(null);
  };

  const isProcessing = githubStatus !== 'idle' && githubStatus !== 'done' && githubStatus !== 'error';

  return (
    <div className="h-full flex flex-col bg-slate-900 rounded-xl border border-slate-800/80 overflow-hidden">
      {/* Header */}
      <div className="px-4 pt-4 pb-3 border-b border-slate-800/60">
        <h2 className="text-sm font-semibold text-slate-200">Add Documents</h2>
        <p className="text-xs text-slate-500 mt-0.5">Upload files or index a GitHub repo</p>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-slate-800/60 px-1 pt-1">
        {(['github', 'upload'] as ActiveTab[]).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`flex-1 py-2 text-xs font-medium rounded-t-lg transition-colors relative ${
              activeTab === tab
                ? 'text-indigo-400 bg-slate-800/50'
                : 'text-slate-500 hover:text-slate-300 hover:bg-slate-800/30'
            }`}
          >
            {tab === 'github' ? (
              <span className="flex items-center justify-center gap-1.5">
                <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 24 24">
                  <path fillRule="evenodd" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" clipRule="evenodd" />
                </svg>
                GitHub Repo
              </span>
            ) : (
              <span className="flex items-center justify-center gap-1.5">
                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
                </svg>
                Upload Files
              </span>
            )}
            {activeTab === tab && (
              <div className="absolute bottom-0 left-2 right-2 h-0.5 bg-indigo-500 rounded-full" />
            )}
          </button>
        ))}
      </div>

      {/* ── GitHub Tab ── */}
      {activeTab === 'github' && (
        <div className="flex-1 flex flex-col p-4 space-y-3 overflow-y-auto">
          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1.5">
              Repository URL
            </label>
            <input
              type="url"
              value={githubUrl}
              onChange={(e) => setGithubUrl(e.target.value)}
              placeholder="https://github.com/username/repo"
              disabled={isProcessing}
              className="w-full px-3 py-2 bg-slate-800/60 border border-slate-700/50 rounded-lg text-sm text-slate-100 placeholder-slate-600 focus:outline-none focus:border-indigo-500/60 focus:ring-1 focus:ring-indigo-500/20 disabled:opacity-40 disabled:cursor-not-allowed transition-all"
              onKeyDown={(e) => { if (e.key === 'Enter' && githubStatus === 'idle') handleGitHubIngest(); }}
            />
          </div>

          {/* Action button */}
          {(githubStatus === 'idle' || githubStatus === 'error') && (
            <button
              onClick={githubStatus === 'error' ? resetGitHub : handleGitHubIngest}
              disabled={!githubUrl.trim() && githubStatus === 'idle'}
              className="w-full py-2 px-4 bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-800 disabled:text-slate-600 disabled:cursor-not-allowed text-white text-sm font-medium rounded-lg transition-all shadow-sm shadow-indigo-500/20 hover:shadow-indigo-500/30"
            >
              {githubStatus === 'error' ? 'Try Again' : 'Clone & Index'}
            </button>
          )}

          {/* Progress */}
          {isProcessing && (
            <div className="flex flex-col items-center py-6 space-y-4">
              <div className="relative">
                <div className="w-12 h-12 rounded-full border-2 border-indigo-500/20 border-t-indigo-500 animate-spin" />
                <div className="absolute inset-0 flex items-center justify-center">
                  <svg className="w-5 h-5 text-indigo-400" fill="currentColor" viewBox="0 0 24 24">
                    <path fillRule="evenodd" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" clipRule="evenodd" />
                  </svg>
                </div>
              </div>
              <div className="text-center">
                <p className="text-sm font-medium text-slate-300">{STATUS_LABELS[githubStatus]}</p>
                <p className="text-xs text-slate-600 mt-1">This may take a minute for large repos</p>
              </div>
              <div className="flex gap-1.5">
                {(['cloning', 'chunking', 'embedding'] as GitHubStatus[]).map((step) => {
                  const steps: GitHubStatus[] = ['cloning', 'chunking', 'embedding'];
                  const current = steps.indexOf(githubStatus);
                  const idx = steps.indexOf(step);
                  return (
                    <span key={step} className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                      idx < current ? 'bg-emerald-500/15 text-emerald-400' :
                      step === githubStatus ? 'bg-indigo-500/15 text-indigo-400' :
                      'bg-slate-800 text-slate-600'
                    }`}>
                      {STATUS_LABELS[step].replace('…', '')}
                    </span>
                  );
                })}
              </div>
            </div>
          )}

          {/* Error */}
          {githubStatus === 'error' && githubError && (
            <div className="p-3 bg-rose-500/8 border border-rose-500/20 rounded-lg">
              <p className="text-xs font-medium text-rose-400 mb-0.5">Ingestion failed</p>
              <p className="text-xs text-rose-300/70">{githubError}</p>
            </div>
          )}

          {/* Success */}
          {githubStatus === 'done' && githubResult && (
            <div className="p-4 bg-emerald-500/8 border border-emerald-500/20 rounded-xl space-y-3">
              <div className="flex items-center gap-2">
                <div className="w-5 h-5 rounded-full bg-emerald-500/20 flex items-center justify-center flex-shrink-0">
                  <svg className="w-3 h-3 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
                  </svg>
                </div>
                <p className="text-sm font-semibold text-emerald-400 truncate">
                  {githubResult.repo_name} indexed!
                </p>
              </div>

              <div className="grid grid-cols-2 gap-2">
                {[
                  { label: 'Files processed', value: `${githubResult.processed_files} / ${githubResult.total_files}` },
                  { label: 'Chunks created', value: githubResult.total_chunks },
                  { label: 'Collection', value: githubResult.collection_name },
                  { label: 'Time', value: `${githubResult.time_taken_seconds}s` },
                ].map(({ label, value }) => (
                  <div key={label} className="bg-slate-800/40 rounded-lg px-2.5 py-2">
                    <p className="text-xs text-slate-500 leading-none mb-1">{label}</p>
                    <p className="text-xs font-medium text-slate-200 truncate">{value}</p>
                  </div>
                ))}
              </div>

              <p className="text-xs text-emerald-400/70">
                Collection activated — start asking questions!
              </p>

              <button
                onClick={resetGitHub}
                className="w-full py-1.5 text-xs text-slate-500 hover:text-slate-300 border border-slate-700/50 hover:border-slate-600 rounded-lg transition-colors"
              >
                Index another repo
              </button>
            </div>
          )}
        </div>
      )}

      {/* ── Upload Files Tab ── */}
      {activeTab === 'upload' && (
        <>
          <div className="p-4">
            <div
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              className={`border-2 border-dashed rounded-xl p-8 text-center transition-all cursor-pointer ${
                isDragging
                  ? 'border-indigo-500/60 bg-indigo-500/5'
                  : 'border-slate-700/60 hover:border-slate-600/80 bg-slate-800/20 hover:bg-slate-800/40'
              }`}
            >
              <input
                ref={fileInputRef}
                type="file"
                onChange={handleFileSelect}
                accept=".py,.js,.ts,.java,.go,.md,.tsx,.jsx,.cpp,.c,.h,.rs,.cu,.cuh,.cs,.rb,.swift,.kt,.yaml,.yml,.json,.sql,.zip"
                className="hidden"
              />

              {isUploading ? (
                <div className="flex flex-col items-center gap-3">
                  <div className="w-10 h-10 rounded-full border-2 border-indigo-500/20 border-t-indigo-500 animate-spin" />
                  <p className="text-sm text-slate-400 font-medium">Uploading…</p>
                </div>
              ) : (
                <div className="flex flex-col items-center gap-2">
                  <div className="w-10 h-10 rounded-xl bg-slate-800 border border-slate-700/50 flex items-center justify-center mb-1">
                    <svg className="w-5 h-5 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                    </svg>
                  </div>
                  <p className="text-sm font-medium text-slate-300">Drop files or click to browse</p>
                  <p className="text-xs text-slate-600">Supports .py .js .ts .cpp .c .cu .md .zip and more</p>
                </div>
              )}
            </div>

            {uploadError && (
              <div className="mt-3 p-3 bg-rose-500/8 border border-rose-500/20 rounded-lg">
                <p className="text-xs text-rose-400">{uploadError}</p>
              </div>
            )}
          </div>

          {/* Upload history */}
          <div className="flex-1 overflow-y-auto px-4 pb-4">
            <p className="text-xs font-medium text-slate-600 mb-2">History</p>
            {uploadHistory.length === 0 ? (
              <p className="text-xs text-slate-600 text-center py-6">No uploads yet</p>
            ) : (
              <div className="space-y-2">
                {uploadHistory.map((upload, idx) => (
                  <div key={idx} className="p-3 bg-slate-800/40 rounded-lg border border-slate-700/30">
                    <div className="flex items-center gap-2 mb-2">
                      <div className="w-4 h-4 rounded-full bg-emerald-500/20 flex items-center justify-center flex-shrink-0">
                        <svg className="w-2.5 h-2.5 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
                        </svg>
                      </div>
                      <span className="text-xs font-medium text-slate-300 truncate">{upload.message}</span>
                    </div>
                    <div className="grid grid-cols-3 gap-1 text-xs text-slate-500">
                      <span>{upload.files_processed} files</span>
                      <span>{upload.total_chunks} chunks</span>
                      <span>{upload.processing_time_seconds}s</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}

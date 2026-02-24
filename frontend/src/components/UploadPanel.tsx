/**
 * UploadPanel component for file uploads.
 * Supports drag-and-drop and file selection.
 */

import { useState, useRef } from 'react';
import type { DragEvent, ChangeEvent } from 'react';
import { uploadFiles } from '../services/api';
import type { UploadResponse } from '../types';

interface UploadPanelProps {
  onUploadSuccess?: (response: UploadResponse) => void;
}

export function UploadPanel({ onUploadSuccess }: UploadPanelProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadHistory, setUploadHistory] = useState<UploadResponse[]>([]);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

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
    setError(null);

    try {
      const response = await uploadFiles(files);
      setUploadHistory((prev) => [response, ...prev]);
      if (onUploadSuccess) {
        onUploadSuccess(response);
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Upload failed';
      setError(errorMessage);
      console.error('Upload error:', err);
    } finally {
      setIsUploading(false);
      // Reset file input
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const openFilePicker = () => {
    fileInputRef.current?.click();
  };

  return (
    <div className="h-full flex flex-col bg-gray-800 border-r border-gray-700">
      {/* Header */}
      <div className="p-4 border-b border-gray-700">
        <h2 className="text-lg font-semibold text-gray-100">Upload Documents</h2>
        <p className="text-sm text-gray-400 mt-1">
          Upload code files or ZIP archives to build your knowledge base
        </p>
      </div>

      {/* Upload area */}
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

        {/* Error message */}
        {error && (
          <div className="mt-4 p-3 bg-red-500/10 border border-red-500/50 rounded-lg">
            <p className="text-sm text-red-400">{error}</p>
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
    </div>
  );
}

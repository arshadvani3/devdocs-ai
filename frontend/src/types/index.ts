/**
 * TypeScript type definitions for DevDocs AI frontend.
 * These interfaces match the backend Pydantic models.
 */

export interface Message {
  id: string;
  type: 'user' | 'assistant';
  content: string;
  sources?: SourceCitation[];
  timestamp: Date;
  streaming?: boolean;
}

export interface SourceCitation {
  file_path: string;
  start_line: number;
  end_line: number;
  text_snippet: string;
  relevance_score: number;
}

export interface UploadResponse {
  success: boolean;
  message: string;
  files_processed: number;
  total_chunks: number;
  collection_name: string;
  processing_time_seconds: number;
  file_metadata?: FileMetadata[];
}

export interface FileMetadata {
  file_path: string;
  file_size: number;
  language: string;
  num_chunks: number;
  processed_at: string;
}

export interface HealthResponse {
  status: string;
  timestamp: string;
  services: {
    ollama: boolean;
    chromadb: boolean;
    embeddings: boolean;
  };
  version: string;
}

export interface QueryRequest {
  question: string;
  collection_name?: string;
  top_k?: number;
}

export interface WebSocketMessage {
  type: 'token' | 'sources' | 'error';
  content?: string;
  message?: string;
  data?: SourceCitation[];
}

export type ConnectionStatus = 'connecting' | 'connected' | 'disconnected';

import { apiClient } from './client';

// ===== Types =====

export interface RAGSource {
  source: string;
  page: number;
  filename: string;
  snippet: string;
}

export interface RAGQueryRequest {
  question: string;
  k?: number;
  return_context?: boolean;
}

export interface RAGQueryResponse {
  success: boolean;
  answer: string;
  sources: RAGSource[];
  context?: string;
  error?: string;
}

export interface RAGIngestResponse {
  success: boolean;
  message: string;
  filename?: string;
  file_hash?: string;
  pages_loaded?: number;
  chunks_added?: number;
  already_indexed?: boolean;
  error?: string;
}

export interface RAGIndexStats {
  persist_directory: string;
  collection_name: string;
  embedding_model: string;
  device: string;
  indexed_file_hashes: number;
  total_documents: number;
}

export interface RAGStatsResponse {
  success: boolean;
  stats: RAGIndexStats;
}

export interface RAGUploadedFile {
  filename: string;
  size: number;
  modified: number;
}

export interface RAGFilesResponse {
  success: boolean;
  files: RAGUploadedFile[];
  count: number;
}

export interface OllamaStatus {
  connected: boolean;
  model?: string;
  base_url?: string;
  message: string;
  error?: string;
}

export interface RAGConfig {
  persist_directory: string;
  collection_name: string;
  ollama_model: string;
  ollama_base_url: string;
  chunk_size: number;
  chunk_overlap: number;
  embedding_model: string;
  retriever_k: number;
  search_type: string;
}

// Quiz Generation Types
export interface QuizQuestion {
  question_number: number;
  question: string;
  options: {
    A: string;
    B: string;
    C: string;
    D: string;
  };
  correct_answer: string;
  explanation?: string;
}

export interface GenerateQuizRequest {
  topic: string;
  num_questions: number;
  difficulty?: 'easy' | 'medium' | 'hard';
  language?: 'vi' | 'en';
}

export interface GenerateQuizResponse {
  success: boolean;
  questions: QuizQuestion[];
  topic: string;
  num_questions_requested: number;
  num_questions_generated: number;
  context_used?: string;
  raw_response?: string;
  error?: string;
}

// ===== API Functions =====

/**
 * Upload a PDF file for RAG
 */
export const uploadRAGDocument = async (file: File): Promise<RAGIngestResponse> => {
  const formData = new FormData();
  formData.append('file', file);

  const response = await apiClient.post<RAGIngestResponse>(
    '/api/document-rag/upload',
    formData,
    {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    }
  );
  return response.data;
};

/**
 * Build index for an uploaded document
 */
export const buildRAGIndex = async (filename: string): Promise<RAGIngestResponse> => {
  const formData = new FormData();
  formData.append('filename', filename);

  const response = await apiClient.post<RAGIngestResponse>(
    '/api/document-rag/build-index',
    formData
  );
  return response.data;
};

/**
 * Upload and immediately index a PDF document
 */
export const uploadAndIndexDocument = async (file: File): Promise<RAGIngestResponse> => {
  const formData = new FormData();
  formData.append('file', file);

  const response = await apiClient.post<RAGIngestResponse>(
    '/api/document-rag/upload-and-index',
    formData,
    {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    }
  );
  return response.data;
};

/**
 * Query the document knowledge base
 */
export const queryRAG = async (request: RAGQueryRequest): Promise<RAGQueryResponse> => {
  const response = await apiClient.post<RAGQueryResponse>(
    '/api/document-rag/query',
    request
  );
  return response.data;
};

/**
 * Get index statistics
 */
export const getRAGStats = async (): Promise<RAGStatsResponse> => {
  const response = await apiClient.get<RAGStatsResponse>('/api/document-rag/stats');
  return response.data;
};

/**
 * Reset the document index
 */
export const resetRAGIndex = async (): Promise<{ success: boolean; message?: string; error?: string }> => {
  const response = await apiClient.post('/api/document-rag/reset');
  return response.data;
};

/**
 * Check Ollama connection status
 */
export const checkOllamaStatus = async (): Promise<OllamaStatus> => {
  const response = await apiClient.get<OllamaStatus>('/api/document-rag/ollama-status');
  return response.data;
};

/**
 * Get RAG configuration
 */
export const getRAGConfig = async (): Promise<{ success: boolean; config: RAGConfig }> => {
  const response = await apiClient.get('/api/document-rag/config');
  return response.data;
};

/**
 * List uploaded files
 */
export const listUploadedFiles = async (): Promise<RAGFilesResponse> => {
  const response = await apiClient.get<RAGFilesResponse>('/api/document-rag/uploaded-files');
  return response.data;
};

/**
 * Delete an uploaded file
 */
export const deleteUploadedFile = async (filename: string): Promise<{ success: boolean; message: string }> => {
  const response = await apiClient.delete(`/api/document-rag/uploaded-files/${encodeURIComponent(filename)}`);
  return response.data;
};

/**
 * Generate quiz from indexed documents
 */
export const generateQuiz = async (request: GenerateQuizRequest): Promise<GenerateQuizResponse> => {
  const response = await apiClient.post<GenerateQuizResponse>(
    '/api/document-rag/generate-quiz',
    request
  );
  return response.data;
};

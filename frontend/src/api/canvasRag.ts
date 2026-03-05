/**
 * Canvas RAG API
 * API calls for Canvas-specific document RAG operations
 * Completely separate from uploaded document RAG
 */

import { apiClient } from './client';
import { getCanvasHeaders, clearCanvasTokenCache } from './canvas';

const API_BASE = '/api/canvas-rag';

// Re-export clearCanvasTokenCache for convenience
export { clearCanvasTokenCache as clearCanvasRagTokenCache };

// ===== Types =====

export interface CanvasDownloadRequest {
  url: string;
  filename: string;
  course_id: number;
  file_id: number;
}

export interface CanvasDownloadResponse {
  success: boolean;
  status: 'saved' | 'duplicate' | 'failed';
  md5_hash?: string;
  filename?: string;
  file_path?: string;
  existing_filename?: string;
  message?: string;
  error?: string;
}

export interface CanvasIndexRequest {
  filename: string;
  course_id?: number;  // Canvas course ID for collection naming
}

export interface CanvasIndexResponse {
  success: boolean;
  message?: string;
  file_hash?: string;
  filename?: string;
  pages_loaded?: number;
  chunks_added?: number;
  already_indexed?: boolean;
  topics_extracted?: number;
  topics?: Array<{ name: string; description: string }>;
  error?: string;
}

export interface CanvasExtractTopicsRequest {
  filename: string;
  num_topics?: number;
}

export interface CanvasTopicsResponse {
  success: boolean;
  topics: string[];
  filename: string;
  error?: string;
}

export interface CanvasUpdateTopicsRequest {
  filename: string;
  topics: string[];
}

export interface CanvasFile {
  filename: string;
  size: number;
  modified: number;
  is_indexed: boolean;
}

export interface CanvasIndexedDocument {
  filename: string;
  original_filename: string;
  file_hash: string;
  indexed_at: string;
  chunks_added: number;
  topic_count: number;
}

export interface CanvasStats {
  total_documents: number;
  total_chunks: number;
  collection_name: string;
  unique_files: number;
}

export interface CanvasQueryRequest {
  question: string;
  k?: number;
  return_context?: boolean;
}

export interface CanvasQueryResponse {
  success: boolean;
  answer?: string;
  sources?: Array<{
    content: string;
    source: string;
    page?: number;
    score?: number;
  }>;
  context?: string;
  error?: string;
}

export interface CanvasQuizRequest {
  topics: string[];
  num_questions?: number;
  difficulty?: 'easy' | 'medium' | 'hard';
  language?: 'vi' | 'en';
  k?: number;
  selected_documents?: string[];
}

export interface CanvasQuizQuestion {
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

export interface CanvasQuizResponse {
  success: boolean;
  questions: CanvasQuizQuestion[];
  topic?: string;
  error?: string;
}

// ===== API Functions =====

/**
 * Download a file from Canvas with MD5 deduplication
 */
export async function downloadCanvasFile(
  request: CanvasDownloadRequest
): Promise<CanvasDownloadResponse> {
  const headers = await getCanvasHeaders();
  const response = await apiClient.post<CanvasDownloadResponse>(
    `${API_BASE}/download`,
    request,
    { headers }
  );
  return response.data;
}

/**
 * Index a downloaded Canvas file
 */
export async function indexCanvasFile(
  filename: string,
  courseId?: number
): Promise<CanvasIndexResponse> {
  const response = await apiClient.post<CanvasIndexResponse>(
    `${API_BASE}/index`,
    { filename, course_id: courseId }
  );
  return response.data;
}

/**
 * Extract topics from a Canvas file
 */
export async function extractCanvasTopics(
  filename: string,
  numTopics: number = 8
): Promise<CanvasTopicsResponse> {
  const response = await apiClient.post<CanvasTopicsResponse>(
    `${API_BASE}/extract-topics`,
    { filename, num_topics: numTopics }
  );
  return response.data;
}

/**
 * Get topics for a Canvas document
 */
export async function getCanvasDocumentTopics(
  filename: string
): Promise<CanvasTopicsResponse> {
  const response = await apiClient.get<CanvasTopicsResponse>(
    `${API_BASE}/topics/${encodeURIComponent(filename)}`
  );
  return response.data;
}

/**
 * Update topics for a Canvas document
 */
export async function updateCanvasDocumentTopics(
  filename: string,
  topics: string[]
): Promise<{ success: boolean; message?: string }> {
  const response = await apiClient.put(`${API_BASE}/topics`, {
    filename,
    topics,
  });
  return response.data;
}

/**
 * List all indexed Canvas documents
 * Optionally filter by courseId
 */
export async function listIndexedCanvasDocuments(courseId?: number): Promise<{
  success: boolean;
  documents: CanvasIndexedDocument[];
  count: number;
}> {
  const params = courseId ? { course_id: courseId } : {};
  const response = await apiClient.get(`${API_BASE}/indexed`, { params });
  return response.data;
}

/**
 * Query Canvas documents
 */
export async function queryCanvasDocuments(
  request: CanvasQueryRequest
): Promise<CanvasQueryResponse> {
  const response = await apiClient.post<CanvasQueryResponse>(
    `${API_BASE}/query`,
    request
  );
  return response.data;
}

/**
 * Generate quiz from Canvas documents
 */
export async function generateCanvasQuiz(
  request: CanvasQuizRequest
): Promise<CanvasQuizResponse> {
  const response = await apiClient.post<CanvasQuizResponse>(
    `${API_BASE}/generate-quiz`,
    request
  );
  return response.data;
}

/**
 * Reset Canvas index
 */
export async function resetCanvasIndex(): Promise<{
  success: boolean;
  message?: string;
}> {
  const response = await apiClient.post(`${API_BASE}/reset`);
  return response.data;
}

/**
 * Remove index for a Canvas file (keep the file)
 */
export async function removeCanvasFileIndex(
  filename: string
): Promise<{ success: boolean; message?: string }> {
  const response = await apiClient.delete(
    `${API_BASE}/index/${encodeURIComponent(filename)}`
  );
  return response.data;
}

export const canvasRagApi = {
  downloadCanvasFile,
  indexCanvasFile,
  extractCanvasTopics,
  getCanvasDocumentTopics,
  updateCanvasDocumentTopics,
  listIndexedCanvasDocuments,
  queryCanvasDocuments,
  generateCanvasQuiz,
  resetCanvasIndex,
  removeCanvasFileIndex,
};

export default canvasRagApi;

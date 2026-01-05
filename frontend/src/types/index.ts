// API Types

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

export interface ToolUsage {
  tool: string;
  args: Record<string, unknown>;
}

export interface ChatRequest {
  message: string;
  history: ChatMessage[];
  model: string;
  max_iterations: number;
}

export interface ChatResponse {
  response: string;
  iterations: number;
  tools_used: ToolUsage[];
  success: boolean;
  error?: string;
}

export interface UploadResponse {
  success: boolean;
  message: string;
  files: string[];
  count: number;
}

export interface QuizQuestion {
  question: string;
  options: Record<string, string>;
  correct: Record<string, string>;
}

export interface QuizGenerateRequest {
  num_questions: number;
  source_pdf?: string;
}

export interface QuizGenerateResponse {
  success: boolean;
  quiz_id: string;
  num_questions: number;
  html_file: string;
  file_url: string;
  message: string;
}

export interface QuizListItem {
  id: string;
  timestamp: string;
  num_questions: number;
  source_pdf?: string;
}

export interface GradingRequest {
  exam_code?: string;
}

export interface GradingResult {
  student_id: string;
  full_name: string;
  email: string;
  exam_code: string;
  score: number;
  evaluation: string;
}

export interface GradingSummary {
  total_students: number;
  average_score: number;
  max_score: number;
  min_score: number;
}

export interface GradingResponse {
  success: boolean;
  exam_code: string;
  summary?: GradingSummary;
  overall_assessment?: string;
  results: GradingResult[];
  excel_file?: string;
  error?: string;
}

export interface ConfigResponse {
  role: string;
  available_models: string[];
  default_model: string;
  max_iterations: number;
}

export type Role = 'STUDENT' | 'TEACHER';

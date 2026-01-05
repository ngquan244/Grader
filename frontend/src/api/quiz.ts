import apiClient from './client';
import type { QuizGenerateRequest, QuizGenerateResponse, QuizListItem } from '../types';

export const quizApi = {
  extractQuestions: async (file: File): Promise<{
    success: boolean;
    message: string;
    questions: unknown[];
    count: number;
  }> => {
    const formData = new FormData();
    formData.append('file', file);

    const response = await apiClient.post('/api/quiz/extract', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  generateQuiz: async (request: QuizGenerateRequest): Promise<QuizGenerateResponse> => {
    const response = await apiClient.post<QuizGenerateResponse>('/api/quiz/generate', request);
    return response.data;
  },

  getQuizList: async (): Promise<{ quizzes: QuizListItem[]; total: number }> => {
    const response = await apiClient.get('/api/quiz/list');
    return response.data;
  },

  getQuiz: async (quizId: string): Promise<unknown> => {
    const response = await apiClient.get(`/api/quiz/${quizId}`);
    return response.data;
  },

  deleteQuiz: async (quizId: string): Promise<{ success: boolean; message: string }> => {
    const response = await apiClient.delete(`/api/quiz/${quizId}`);
    return response.data;
  },
};

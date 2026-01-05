import apiClient from './client';
import type { GradingRequest, GradingResponse } from '../types';

export const gradingApi = {
  executeGrading: async (): Promise<{
    success: boolean;
    result: unknown;
  }> => {
    const response = await apiClient.post('/api/grading/execute');
    return response.data;
  },

  getSummary: async (request: GradingRequest): Promise<GradingResponse> => {
    const response = await apiClient.post<GradingResponse>('/api/grading/summary', request);
    return response.data;
  },

  getExamCodes: async (): Promise<{ exam_codes: string[] }> => {
    const response = await apiClient.get('/api/grading/exam-codes');
    return response.data;
  },

  exportResults: async (examCode: string): Promise<{ success: boolean; file_url: string }> => {
    const response = await apiClient.post('/api/grading/export', { exam_code: examCode });
    return response.data;
  },
};

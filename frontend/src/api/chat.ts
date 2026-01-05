import apiClient from './client';
import type { ChatRequest, ChatResponse } from '../types';

export const chatApi = {
  sendMessage: async (request: ChatRequest): Promise<ChatResponse> => {
    const response = await apiClient.post<ChatResponse>('/api/chat/send', request);
    return response.data;
  },

  getModels: async (): Promise<{ models: string[]; default: string }> => {
    const response = await apiClient.get('/api/chat/models');
    return response.data;
  },

  clearHistory: async (): Promise<{ message: string; success: boolean }> => {
    const response = await apiClient.delete('/api/chat/history');
    return response.data;
  },
};

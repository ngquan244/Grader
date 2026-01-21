import apiClient from './client';
import type { ConfigResponse } from '../types';

export const configApi = {
  getConfig: async (): Promise<ConfigResponse> => {
    const response = await apiClient.get<ConfigResponse>('/api/config/');
    return response.data;
  },

  getModels: async (): Promise<{ models: string[]; default: string }> => {
    const response = await apiClient.get('/api/config/models');
    return response.data;
  },

  setModel: async (model: string, maxIterations: number = 10): Promise<{
    success: boolean;
    model: string;
    max_iterations: number;
    message: string;
  }> => {
    const response = await apiClient.post('/api/config/model', {
      model,
      max_iterations: maxIterations,
    });
    return response.data;
  },
};

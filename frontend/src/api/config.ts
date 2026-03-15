import apiClient from './client';
import type { ConfigResponse } from '../types';

export const configApi = {
  getConfig: async (): Promise<ConfigResponse> => {
    const response = await apiClient.get<ConfigResponse>('/api/config/');
    return response.data;
  },
};

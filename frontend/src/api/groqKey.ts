import { apiClient } from './client';

export interface GroqKeyStatus {
  has_key: boolean;
  source: 'db' | 'env' | 'none';
  masked_key: string | null;
  updated_at: string | null;
}

export const groqKeyApi = {
  getStatus: async (): Promise<GroqKeyStatus> => {
    const res = await apiClient.get('/api/admin/groq-key/status');
    return res.data;
  },

  updateKey: async (apiKey: string): Promise<{ success: boolean; message: string }> => {
    const res = await apiClient.put('/api/admin/groq-key', { api_key: apiKey });
    return res.data;
  },

  deleteKey: async (): Promise<{ success: boolean; message: string }> => {
    const res = await apiClient.delete('/api/admin/groq-key');
    return res.data;
  },
};

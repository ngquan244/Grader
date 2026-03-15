import React, { createContext, useContext, useState, useEffect, type ReactNode } from 'react';
import { configApi } from '../api/config';
import type { ConfigResponse } from '../types';

interface AppContextType {
  config: ConfigResponse | null;
  loading: boolean;
  model: string;
  setModel: (model: string) => void;
}

const AppContext = createContext<AppContextType | undefined>(undefined);

export const AppProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [config, setConfig] = useState<ConfigResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [model, setModel] = useState('llama-3.3-70b-versatile');

  useEffect(() => {
    loadConfig();
  }, []);

  const loadConfig = async () => {
    try {
      const data = await configApi.getConfig();
      setConfig(data);
      setModel(data.default_model);
    } catch (error) {
      console.error('Failed to load config:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <AppContext.Provider
      value={{
        config,
        loading,
        model,
        setModel,
      }}
    >
      {children}
    </AppContext.Provider>
  );
};

export const useApp = () => {
  const context = useContext(AppContext);
  if (context === undefined) {
    throw new Error('useApp must be used within an AppProvider');
  }
  return context;
};

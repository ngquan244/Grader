import React, { createContext, useContext, useState, useEffect, type ReactNode } from 'react';
import { configApi } from '../api/config';
import type { Role, ConfigResponse, ChatMessage, ToolUsage } from '../types';

interface AppContextType {
  role: Role;
  setRole: (role: Role) => Promise<void>;
  switchRole: () => Promise<void>;
  config: ConfigResponse | null;
  loading: boolean;
  model: string;
  setModel: (model: string) => void;
  maxIterations: number;
  setMaxIterations: (n: number) => void;
  // Chat state - persisted across tab switches
  chatMessages: ChatMessage[];
  setChatMessages: React.Dispatch<React.SetStateAction<ChatMessage[]>>;
  chatToolsUsed: ToolUsage[];
  setChatToolsUsed: React.Dispatch<React.SetStateAction<ToolUsage[]>>;
  clearChat: () => void;
}

const AppContext = createContext<AppContextType | undefined>(undefined);

export const AppProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [role, setRoleState] = useState<Role>('STUDENT');
  const [config, setConfig] = useState<ConfigResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [model, setModel] = useState('llama3.1:latest');
  const [maxIterations, setMaxIterations] = useState(10);
  
  // Chat state - persisted across tab switches
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [chatToolsUsed, setChatToolsUsed] = useState<ToolUsage[]>([]);

  const clearChat = () => {
    setChatMessages([]);
    setChatToolsUsed([]);
  };

  useEffect(() => {
    loadConfig();
  }, []);

  const loadConfig = async () => {
    try {
      const data = await configApi.getConfig();
      setConfig(data);
      setRoleState(data.role as Role);
      setModel(data.default_model);
      setMaxIterations(data.max_iterations);
    } catch (error) {
      console.error('Failed to load config:', error);
    } finally {
      setLoading(false);
    }
  };

  const setRole = async (newRole: Role) => {
    try {
      await configApi.setRole(newRole);
      setRoleState(newRole);
    } catch (error) {
      console.error('Failed to set role:', error);
      throw error;
    }
  };

  const switchRole = async () => {
    try {
      const result = await configApi.switchRole();
      setRoleState(result.current_role as Role);
    } catch (error) {
      console.error('Failed to switch role:', error);
      throw error;
    }
  };

  return (
    <AppContext.Provider
      value={{
        role,
        setRole,
        switchRole,
        config,
        loading,
        model,
        setModel,
        maxIterations,
        setMaxIterations,
        chatMessages,
        setChatMessages,
        chatToolsUsed,
        setChatToolsUsed,
        clearChat,
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

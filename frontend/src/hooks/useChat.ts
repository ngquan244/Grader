import { useState, useCallback } from 'react';
import { chatApi } from '../api';
import type { ChatMessage, ToolUsage, ChatResponse } from '../types';

interface UseChatOptions {
  model: string;
  maxIterations: number;
}

interface UseChatReturn {
  messages: ChatMessage[];
  toolsUsed: ToolUsage[];
  isLoading: boolean;
  error: string | null;
  sendMessage: (content: string) => Promise<ChatResponse | null>;
  clearChat: () => void;
  setMessages: React.Dispatch<React.SetStateAction<ChatMessage[]>>;
  setToolsUsed: React.Dispatch<React.SetStateAction<ToolUsage[]>>;
}

export function useChat(
  options: UseChatOptions,
  externalMessages?: ChatMessage[],
  externalSetMessages?: React.Dispatch<React.SetStateAction<ChatMessage[]>>,
  externalToolsUsed?: ToolUsage[],
  externalSetToolsUsed?: React.Dispatch<React.SetStateAction<ToolUsage[]>>,
  externalClearChat?: () => void
): UseChatReturn {
  const [internalMessages, setInternalMessages] = useState<ChatMessage[]>([]);
  const [internalToolsUsed, setInternalToolsUsed] = useState<ToolUsage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Use external state if provided, otherwise use internal
  const messages = externalMessages ?? internalMessages;
  const setMessages = externalSetMessages ?? setInternalMessages;
  const toolsUsed = externalToolsUsed ?? internalToolsUsed;
  const setToolsUsed = externalSetToolsUsed ?? setInternalToolsUsed;

  const clearChat = useCallback(() => {
    if (externalClearChat) {
      externalClearChat();
    } else {
      setInternalMessages([]);
      setInternalToolsUsed([]);
    }
    setError(null);
  }, [externalClearChat]);

  const sendMessage = useCallback(async (content: string): Promise<ChatResponse | null> => {
    if (!content.trim()) {
      setError('Vui lòng nhập tin nhắn');
      return null;
    }

    setIsLoading(true);
    setError(null);

    // Add user message
    const userMessage: ChatMessage = { role: 'user', content };
    setMessages(prev => [...prev, userMessage]);

    try {
      const response = await chatApi.sendMessage({
        message: content,
        history: messages,
        model: options.model,
        max_iterations: options.maxIterations,
      });

      if (response.success) {
        // Add assistant response
        const assistantMessage: ChatMessage = {
          role: 'assistant',
          content: response.response,
        };
        setMessages(prev => [...prev, assistantMessage]);

        // Update tools used
        if (response.tools_used?.length > 0) {
          setToolsUsed(prev => [...prev, ...response.tools_used]);
        }
      } else {
        setError(response.error || 'Đã xảy ra lỗi');
      }

      return response;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Đã xảy ra lỗi không xác định';
      setError(errorMessage);
      return null;
    } finally {
      setIsLoading(false);
    }
  }, [messages, options.model, options.maxIterations, setMessages, setToolsUsed]);

  return {
    messages,
    toolsUsed,
    isLoading,
    error,
    sendMessage,
    clearChat,
    setMessages,
    setToolsUsed,
  };
}

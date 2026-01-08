import React, { useState, useRef, useEffect } from 'react';
import { chatApi } from '../api/chat';
import { useApp } from '../context/AppContext';
import { Send, Loader2, Trash2, Bot, User } from 'lucide-react';
import type { ChatMessage } from '../types';

const ChatPanel: React.FC = () => {
  const { model, maxIterations, chatMessages, setChatMessages, chatToolsUsed, setChatToolsUsed, clearChat } = useApp();
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [chatMessages]);

  const handleSend = async () => {
    if (!input.trim() || loading) return;

    const userMessage: ChatMessage = { role: 'user', content: input };
    setChatMessages((prev) => [...prev, userMessage]);
    setInput('');
    setLoading(true);
    setChatToolsUsed([]);

    try {
      const response = await chatApi.sendMessage({
        message: input,
        history: chatMessages,
        model,
        max_iterations: maxIterations,
      });

      const assistantMessage: ChatMessage = {
        role: 'assistant',
        content: response.response,
      };
      setChatMessages((prev) => [...prev, assistantMessage]);
      setChatToolsUsed(response.tools_used || []);
    } catch (error) {
      console.error('Chat error:', error);
      const errorMessage: ChatMessage = {
        role: 'assistant',
        content: 'Xin lỗi, đã xảy ra lỗi khi xử lý tin nhắn của bạn.',
      };
      setChatMessages((prev) => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="chat-panel">
      <div className="chat-header">
        <h2>Chat với AI Assistant</h2>
        <button className="btn-secondary btn-sm" onClick={clearChat}>
          <Trash2 size={16} />
          <span>Xóa lịch sử</span>
        </button>
      </div>

      <div className="chat-messages">
        {chatMessages.length === 0 && (
          <div className="chat-welcome">
            <Bot size={48} />
            <h3>Xin chào! Tôi là Teaching Assistant</h3>
            <p>Tôi có thể giúp bạn chấm điểm bài thi, tạo quiz, và nhiều việc khác.</p>
            <div className="suggestions">
              <button onClick={() => setInput('Chấm điểm bài thi trong thư mục Filled-temp')}>
                Chấm điểm bài thi
              </button>
              <button onClick={() => setInput('Tổng hợp kết quả mã đề 132')}>
                Tổng hợp kết quả
              </button>
              <button onClick={() => setInput('Tạo quiz từ file PDF đề thi')}>
                Tạo quiz từ PDF
              </button>
            </div>
          </div>
        )}

        {chatMessages.map((msg, index) => (
          <div key={index} className={`message ${msg.role}`}>
            <div className="message-avatar">
              {msg.role === 'user' ? <User size={20} /> : <Bot size={20} />}
            </div>
            <div className="message-content">
              <pre>{msg.content}</pre>
            </div>
          </div>
        ))}

        {loading && (
          <div className="message assistant loading">
            <div className="message-avatar">
              <Bot size={20} />
            </div>
            <div className="message-content">
              <Loader2 className="spin" size={20} />
              <span>Đang xử lý...</span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {chatToolsUsed.length > 0 && (
        <div className="tools-used">
          <span>Tools đã sử dụng:</span>
          {chatToolsUsed.map((tool, index) => (
            <span key={index} className="tool-badge">
              {tool.tool}
            </span>
          ))}
        </div>
      )}

      <div className="chat-input">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder="Nhập tin nhắn..."
          rows={3}
          disabled={loading}
        />
        <button
          className="btn-send"
          onClick={handleSend}
          disabled={!input.trim() || loading}
        >
          {loading ? <Loader2 className="spin" size={20} /> : <Send size={20} />}
        </button>
      </div>
    </div>
  );
};

export default ChatPanel;

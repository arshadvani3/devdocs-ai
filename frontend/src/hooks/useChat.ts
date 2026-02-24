/**
 * Custom React hook for managing chat messages and state.
 * Handles message history, streaming updates, and localStorage persistence.
 */

import { useState, useEffect, useCallback } from 'react';
import type { Message, SourceCitation } from '../types';

interface UseChatReturn {
  messages: Message[];
  currentStreamingMessage: string;
  addUserMessage: (content: string) => void;
  startAssistantMessage: () => void;
  appendToAssistantMessage: (token: string) => void;
  completeAssistantMessage: (sources: SourceCitation[]) => void;
  clearMessages: () => void;
}

const STORAGE_KEY = 'devdocs-chat-history';

export function useChat(): UseChatReturn {
  const [messages, setMessages] = useState<Message[]>([]);
  const [currentStreamingMessage, setCurrentStreamingMessage] = useState('');

  // Load messages from localStorage on mount
  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        const parsed = JSON.parse(stored);
        // Convert timestamp strings back to Date objects
        const messagesWithDates = parsed.map((msg: any) => ({
          ...msg,
          timestamp: new Date(msg.timestamp),
        }));
        setMessages(messagesWithDates);
      }
    } catch (error) {
      console.error('Failed to load chat history:', error);
    }
  }, []);

  // Save messages to localStorage whenever they change
  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(messages));
    } catch (error) {
      console.error('Failed to save chat history:', error);
    }
  }, [messages]);

  const addUserMessage = useCallback((content: string) => {
    const newMessage: Message = {
      id: `user-${Date.now()}`,
      type: 'user',
      content,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, newMessage]);
  }, []);

  const startAssistantMessage = useCallback(() => {
    setCurrentStreamingMessage('');
    const newMessage: Message = {
      id: `assistant-${Date.now()}`,
      type: 'assistant',
      content: '',
      timestamp: new Date(),
      streaming: true,
    };
    setMessages((prev) => [...prev, newMessage]);
  }, []);

  const appendToAssistantMessage = useCallback((token: string) => {
    setCurrentStreamingMessage((prev) => prev + token);
    setMessages((prev) => {
      if (prev.length === 0) return prev;

      const lastMessage = prev[prev.length - 1];
      if (lastMessage && lastMessage.type === 'assistant' && lastMessage.streaming) {
        // Create a new message object instead of mutating
        const updatedMessage: Message = {
          ...lastMessage,
          content: lastMessage.content + token,
        };
        return [...prev.slice(0, -1), updatedMessage];
      }
      return prev;
    });
  }, []);

  const completeAssistantMessage = useCallback((sources: SourceCitation[]) => {
    setCurrentStreamingMessage('');
    setMessages((prev) => {
      if (prev.length === 0) return prev;

      const lastMessage = prev[prev.length - 1];
      if (lastMessage && lastMessage.type === 'assistant') {
        // Create a new message object instead of mutating
        const updatedMessage: Message = {
          ...lastMessage,
          streaming: false,
          sources,
        };
        return [...prev.slice(0, -1), updatedMessage];
      }
      return prev;
    });
  }, []);

  const clearMessages = useCallback(() => {
    setMessages([]);
    setCurrentStreamingMessage('');
    localStorage.removeItem(STORAGE_KEY);
  }, []);

  return {
    messages,
    currentStreamingMessage,
    addUserMessage,
    startAssistantMessage,
    appendToAssistantMessage,
    completeAssistantMessage,
    clearMessages,
  };
}

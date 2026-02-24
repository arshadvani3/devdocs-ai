/**
 * MessageList component for displaying chat messages.
 * Shows user questions and AI responses with sources.
 */

import { useEffect, useRef } from 'react';
import type { Message } from '../types';
import { SourceCitation } from './SourceCitation';

interface MessageListProps {
  messages: Message[];
}

export function MessageList({ messages }: MessageListProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const formatTimestamp = (date: Date): string => {
    return new Intl.DateTimeFormat('en-US', {
      hour: 'numeric',
      minute: 'numeric',
      hour12: true,
    }).format(date);
  };

  return (
    <div className="flex-1 overflow-y-auto p-4 space-y-4 scrollbar-thin">
      {messages.length === 0 ? (
        <div className="flex items-center justify-center h-full text-center">
          <div className="max-w-md">
            <svg className="w-16 h-16 mx-auto mb-4 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
            </svg>
            <h3 className="text-xl font-semibold text-gray-300 mb-2">No messages yet</h3>
            <p className="text-gray-500">
              Upload your codebase and start asking questions!
            </p>
          </div>
        </div>
      ) : (
        messages.map((message) => (
          <div
            key={message.id}
            className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-3xl ${
                message.type === 'user'
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-800 text-gray-100'
              } rounded-lg p-4 shadow-lg`}
            >
              {/* Message header */}
              <div className="flex items-center gap-2 mb-2">
                <div
                  className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
                    message.type === 'user' ? 'bg-blue-700' : 'bg-gray-700'
                  }`}
                >
                  {message.type === 'user' ? 'U' : 'AI'}
                </div>
                <span className="text-xs opacity-75">
                  {formatTimestamp(message.timestamp)}
                </span>
              </div>

              {/* Message content */}
              <div className="prose prose-invert max-w-none">
                <p className="whitespace-pre-wrap break-words">
                  {message.content}
                  {message.streaming && (
                    <span className="inline-block w-2 h-4 ml-1 bg-current streaming-cursor" />
                  )}
                </p>
              </div>

              {/* Sources */}
              {message.sources && message.sources.length > 0 && (
                <div className="mt-4 space-y-2">
                  <div className="text-sm font-semibold opacity-75 mb-2">
                    Sources ({message.sources.length}):
                  </div>
                  {message.sources.map((citation, idx) => (
                    <SourceCitation key={idx} citation={citation} />
                  ))}
                </div>
              )}
            </div>
          </div>
        ))
      )}
      <div ref={messagesEndRef} />
    </div>
  );
}

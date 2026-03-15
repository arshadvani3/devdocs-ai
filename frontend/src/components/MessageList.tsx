/**
 * MessageList component for displaying chat messages.
 */

import { useEffect, useRef } from 'react';
import type { Message } from '../types';
import { SourceCitation } from './SourceCitation';

interface MessageListProps {
  messages: Message[];
  hasCollection?: boolean;
}

export function MessageList({ messages, hasCollection }: MessageListProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null);

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

  if (messages.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center p-8">
        <div className="text-center max-w-sm">
          <div className="w-14 h-14 mx-auto mb-5 rounded-2xl bg-gradient-to-br from-indigo-500/20 to-violet-500/20 border border-indigo-500/20 flex items-center justify-center">
            <svg className="w-7 h-7 text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
            </svg>
          </div>
          <h3 className="text-base font-semibold text-slate-300 mb-2">
            {hasCollection ? 'Ask anything about your code' : 'No codebase loaded yet'}
          </h3>
          <p className="text-sm text-slate-500 leading-relaxed">
            {hasCollection
              ? 'Ask questions about functions, architecture, bugs, or anything in the indexed codebase.'
              : 'Upload files or index a GitHub repo on the left to get started.'}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto p-4 space-y-5">
      {messages.map((message) => (
        <div
          key={message.id}
          className={`flex gap-3 ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}
        >
          {/* AI avatar */}
          {message.type === 'assistant' && (
            <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center flex-shrink-0 mt-0.5 shadow-md shadow-indigo-500/20">
              <svg className="w-3.5 h-3.5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
              </svg>
            </div>
          )}

          <div className={`max-w-2xl ${message.type === 'user' ? 'order-first' : ''}`}>
            {/* Bubble */}
            <div className={`rounded-2xl px-4 py-3 shadow-sm ${
              message.type === 'user'
                ? 'bg-indigo-600 text-white rounded-tr-sm'
                : 'bg-slate-800 text-slate-100 rounded-tl-sm border border-slate-700/50'
            }`}>
              <p className="whitespace-pre-wrap break-words text-sm leading-relaxed">
                {message.content}
                {message.streaming && (
                  <span className="inline-block w-0.5 h-4 ml-0.5 bg-current align-middle animate-pulse" />
                )}
              </p>
            </div>

            {/* Timestamp */}
            <div className={`text-xs text-slate-600 mt-1 px-1 ${message.type === 'user' ? 'text-right' : 'text-left'}`}>
              {formatTimestamp(message.timestamp)}
            </div>

            {/* Sources */}
            {message.sources && message.sources.length > 0 && (
              <div className="mt-3 space-y-1.5">
                <div className="text-xs font-medium text-slate-500 px-1">
                  Sources ({message.sources.length})
                </div>
                {message.sources.map((citation, idx) => (
                  <SourceCitation key={idx} citation={citation} />
                ))}
              </div>
            )}
          </div>

          {/* User avatar */}
          {message.type === 'user' && (
            <div className="w-7 h-7 rounded-lg bg-slate-700 flex items-center justify-center flex-shrink-0 mt-0.5">
              <svg className="w-3.5 h-3.5 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
              </svg>
            </div>
          )}
        </div>
      ))}
      <div ref={messagesEndRef} />
    </div>
  );
}

/**
 * ChatInterface component - main container for the chat application.
 */

import { useEffect, useRef, useState } from 'react';
import { useWebSocket } from '../hooks/useWebSocket';
import { useChat } from '../hooks/useChat';
import { MessageList } from './MessageList';
import { MessageInput } from './MessageInput';
import { UploadPanel } from './UploadPanel';
import type { WebSocketMessage } from '../types';

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/api/v1/stream';

export function ChatInterface() {
  const { sendMessage, lastMessage, connectionStatus, isStreaming } = useWebSocket(WS_URL);
  const {
    messages,
    addUserMessage,
    startAssistantMessage,
    appendToAssistantMessage,
    completeAssistantMessage,
    clearMessages,
  } = useChat();
  const [activeCollection, setActiveCollection] = useState<string | undefined>(undefined);
  const lastProcessedMessageRef = useRef<WebSocketMessage | null>(null);

  useEffect(() => {
    if (!lastMessage || lastMessage === lastProcessedMessageRef.current) return;
    lastProcessedMessageRef.current = lastMessage;

    switch (lastMessage.type) {
      case 'token':
        if (!isStreaming || messages[messages.length - 1]?.type !== 'assistant') {
          startAssistantMessage();
        }
        if (lastMessage.content) appendToAssistantMessage(lastMessage.content);
        break;
      case 'sources':
        completeAssistantMessage(lastMessage.data || []);
        break;
      case 'error':
        if (messages[messages.length - 1]?.streaming) completeAssistantMessage([]);
        break;
    }
  }, [lastMessage, isStreaming, messages, startAssistantMessage, appendToAssistantMessage, completeAssistantMessage]);

  const handleSendMessage = (content: string) => {
    addUserMessage(content);
    sendMessage({
      question: content,
      top_k: 5,
      ...(activeCollection && { collection_name: activeCollection }),
    });
  };

  return (
    <div className="h-[calc(100vh-7rem)] flex gap-4">
      {/* Left panel */}
      <div className="w-96 flex-shrink-0">
        <UploadPanel
          onUploadSuccess={(response) => {
            if (response.collection_name) setActiveCollection(response.collection_name);
          }}
          onGitHubSuccess={(collectionName) => {
            setActiveCollection(collectionName);
          }}
        />
      </div>

      {/* Right panel — Chat */}
      <div className="flex-1 flex flex-col bg-slate-900 rounded-xl border border-slate-800/80 overflow-hidden">
        {/* Chat toolbar */}
        <div className="px-4 py-2.5 bg-slate-900/95 border-b border-slate-800/60 flex items-center justify-between gap-3 min-h-[44px]">
          <div className="flex items-center gap-2.5 min-w-0">
            {/* Connection dot */}
            <div className="flex items-center gap-1.5 flex-shrink-0">
              <div className={`w-1.5 h-1.5 rounded-full ${
                connectionStatus === 'connected'
                  ? 'bg-emerald-400 shadow-[0_0_6px_rgba(52,211,153,0.6)]'
                  : connectionStatus === 'connecting'
                  ? 'bg-amber-400 animate-pulse'
                  : 'bg-rose-500'
              }`} />
              <span className="text-xs text-slate-500">
                {connectionStatus === 'connected' ? 'Connected' :
                 connectionStatus === 'connecting' ? 'Connecting…' : 'Disconnected'}
              </span>
            </div>

            {/* Active collection badge */}
            {activeCollection ? (
              <div className="flex items-center gap-1.5 px-2 py-0.5 bg-indigo-500/10 border border-indigo-500/20 rounded-full min-w-0">
                <svg className="w-3 h-3 text-indigo-400 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 12h14M12 5l7 7-7 7" />
                </svg>
                <span className="text-xs text-indigo-300 font-mono truncate max-w-[200px]">
                  {activeCollection}
                </span>
              </div>
            ) : (
              <span className="text-xs text-slate-600 italic">no collection active</span>
            )}
          </div>

          {messages.length > 0 && (
            <button
              onClick={clearMessages}
              className="text-xs text-slate-600 hover:text-slate-300 transition-colors flex-shrink-0 px-2 py-1 rounded hover:bg-slate-800"
            >
              Clear
            </button>
          )}
        </div>

        {/* Messages */}
        <MessageList messages={messages} hasCollection={!!activeCollection} />

        {/* Input */}
        <MessageInput
          onSend={handleSendMessage}
          disabled={connectionStatus !== 'connected' || isStreaming}
        />
      </div>
    </div>
  );
}

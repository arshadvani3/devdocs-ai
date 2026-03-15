/**
 * ChatInterface component - main container for the chat application.
 * Integrates upload panel, message list, and input components.
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

  // Track last processed message to prevent duplicate processing
  const lastProcessedMessageRef = useRef<WebSocketMessage | null>(null);

  // Handle incoming WebSocket messages
  useEffect(() => {
    // Skip if no message or if we've already processed this exact message object
    if (!lastMessage || lastMessage === lastProcessedMessageRef.current) {
      return;
    }

    // Mark this message as processed
    lastProcessedMessageRef.current = lastMessage;

    console.log('Processing WebSocket message:', lastMessage.type, lastMessage.content?.substring(0, 20));

    switch (lastMessage.type) {
      case 'token':
        // First token - start new assistant message
        if (!isStreaming || messages[messages.length - 1]?.type !== 'assistant') {
          startAssistantMessage();
        }
        // Append token to current message
        if (lastMessage.content) {
          appendToAssistantMessage(lastMessage.content);
        }
        break;

      case 'sources':
        // Complete the message with sources
        completeAssistantMessage(lastMessage.data || []);
        break;

      case 'error':
        // Handle error
        console.error('WebSocket error:', lastMessage.message);
        if (messages[messages.length - 1]?.streaming) {
          completeAssistantMessage([]);
        }
        // Could also show error in UI
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
    <div className="h-[calc(100vh-8rem)] flex gap-4">
      {/* Left panel - Upload */}
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

      {/* Right panel - Chat */}
      <div className="flex-1 flex flex-col bg-gray-800 rounded-lg border border-gray-700 overflow-hidden">
        {/* Connection status indicator */}
        <div className="px-4 py-2 bg-gray-900 border-b border-gray-700 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div
              className={`w-2 h-2 rounded-full ${
                connectionStatus === 'connected'
                  ? 'bg-green-500'
                  : connectionStatus === 'connecting'
                  ? 'bg-yellow-500 animate-pulse'
                  : 'bg-red-500'
              }`}
            />
            <span className="text-sm text-gray-400">
              {connectionStatus === 'connected'
                ? 'Connected'
                : connectionStatus === 'connecting'
                ? 'Connecting...'
                : 'Disconnected'}
            </span>
          </div>

          {messages.length > 0 && (
            <button
              onClick={clearMessages}
              className="text-sm text-gray-400 hover:text-gray-200 transition-colors"
            >
              Clear chat
            </button>
          )}
        </div>

        {/* Messages */}
        <MessageList messages={messages} />

        {/* Input */}
        <MessageInput
          onSend={handleSendMessage}
          disabled={connectionStatus !== 'connected' || isStreaming}
        />
      </div>
    </div>
  );
}

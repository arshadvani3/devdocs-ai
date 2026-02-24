# DevDocs AI - Frontend

Modern React TypeScript frontend for the DevDocs AI RAG-powered code documentation assistant.

## Features

- **Real-time Streaming**: WebSocket-based streaming for live responses
- **File Upload**: Drag-and-drop interface for uploading code files and ZIP archives
- **Syntax Highlighting**: Prism.js integration for beautiful code display
- **Source Citations**: Expandable source references with relevance scores
- **Chat History**: Persistent chat history using localStorage
- **Dark Theme**: Professional dark mode design with TailwindCSS
- **Responsive**: Mobile-friendly responsive layout

## Tech Stack

- **React 19** with TypeScript 5.9
- **Vite 7** for fast development and building
- **TailwindCSS 3.4** for styling
- **Prism.js 1.30** for syntax highlighting
- **WebSocket** for real-time streaming

## Getting Started

### Prerequisites

- Node.js 18+ and npm
- Backend server running at `http://localhost:8000`

### Installation

```bash
# Install dependencies
npm install
```

### Development

```bash
# Start development server
npm run dev

# App will be available at http://localhost:5173
```

### Build for Production

```bash
# Build optimized production bundle
npm run build

# Preview production build
npm run preview
```

## Project Structure

```
src/
├── components/          # React components
│   ├── ChatInterface.tsx    # Main chat container
│   ├── MessageList.tsx      # Message display
│   ├── MessageInput.tsx     # Input field
│   ├── CodeBlock.tsx        # Syntax-highlighted code
│   ├── SourceCitation.tsx   # Source references
│   └── UploadPanel.tsx      # File upload UI
├── hooks/              # Custom React hooks
│   ├── useWebSocket.ts     # WebSocket connection
│   └── useChat.ts          # Chat state management
├── services/           # API services
│   └── api.ts             # REST API calls
├── types/              # TypeScript types
│   └── index.ts           # Type definitions
├── App.tsx             # Main app component
├── index.css           # Global styles
└── main.tsx            # Entry point
```

## Features Walkthrough

### Upload Documents

1. Drag and drop files or click to browse
2. Supports individual code files or ZIP archives
3. View upload history with stats (files processed, chunks created)

### Ask Questions

1. Type your question in the input box
2. Press Enter to send (Shift+Enter for newline)
3. Watch the AI response stream in real-time
4. View source citations below each answer
5. Click citations to expand and see code snippets

### Chat Management

- Chat history persists across page refreshes
- Use "Clear chat" button to reset conversation
- Connection status indicator shows WebSocket state

## Configuration

Create a `.env` file in the frontend directory:

```bash
VITE_API_BASE_URL=http://localhost:8000/api/v1
VITE_WS_URL=ws://localhost:8000/api/v1/stream
```

Update these variables if your backend runs on a different host/port.

## Technical Implementation

### Custom Hooks
- **`useWebSocket`** - Manages WebSocket lifecycle, reconnection, and message handling
- **`useChat`** - Encapsulates chat state, message history, and localStorage persistence

### Performance Optimizations
- Real-time token streaming with WebSocket for instant feedback
- Lazy loading of syntax highlighting languages
- LocalStorage for chat persistence across sessions
- Optimistic UI updates for better UX

### Component Architecture
- Separation of concerns (UI components vs business logic)
- TypeScript for type safety throughout
- Custom hooks for reusable stateful logic
- Responsive design with mobile-first approach

---

## Key Achievements

This frontend demonstrates:
- **Real-time streaming** with WebSocket for instant user feedback and token-by-token display
- **Custom React hooks** (useWebSocket, useChat) for clean separation of concerns
- **TypeScript** for complete type safety and improved developer experience
- **Modern UI patterns** with TailwindCSS and component composition
- **State management** with localStorage persistence across sessions
- **Performance optimization** through lazy loading and optimistic UI updates
- **Responsive design** with mobile-first approach using TailwindCSS utilities

Part of the **DevDocs AI** portfolio project showcasing full-stack development skills.

---

## License

MIT

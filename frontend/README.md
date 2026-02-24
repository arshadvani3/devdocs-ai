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

- **React 18** with TypeScript
- **Vite** for fast development and building
- **TailwindCSS** for styling
- **Prism.js** for syntax highlighting
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

Backend API URL is configured in:
- WebSocket: `src/components/ChatInterface.tsx` (WS_URL constant)
- REST API: `src/services/api.ts` (API_BASE constant)

Update these if your backend runs on a different host/port.

## Troubleshooting

### WebSocket connection fails
- Ensure backend is running at `http://localhost:8000`
- Check browser console for connection errors
- Verify CORS settings in backend

### Syntax highlighting not working
- Prism.js languages are imported in `CodeBlock.tsx`
- Add more languages by importing from `prismjs/components/`

### Upload fails
- Check file extension is supported (see backend config)
- Verify backend `/api/v1/ingest` endpoint is accessible
- Check browser network tab for errors

## Development Tips

- Hot reload is enabled - save files to see changes instantly
- Use React DevTools for debugging component state
- Check browser console for WebSocket message logs
- TailwindCSS IntelliSense extension recommended for VS Code

## License

MIT

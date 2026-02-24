# WebSocket Debugging Guide

## Changes Made

### Backend Enhancements ([backend/app/api/websocket.py](backend/app/api/websocket.py))

Added comprehensive debugging with emojis for easy log scanning:

1. **Connection Logging:**
   - ✓ WebSocket connection accepted
   - Client info and headers logged
   - Connection closure tracking

2. **Token Streaming Debug:**
   - 📤 Log each token sent (with truncation)
   - Count tokens streamed
   - Small 10ms delay between tokens to prevent overwhelming
   - Catch and log send errors

3. **Error Handling:**
   - ✗ All errors logged with context
   - JSON decode errors show raw data
   - Stream errors caught separately
   - Disconnect codes logged

4. **Progress Indicators:**
   - 🚀 Streaming start
   - 📨 Query received
   - 📚 Sources prepared
   - 🔌 Client disconnected
   - 🔚 Connection closed

### LLM Service Enhancements ([backend/app/services/llm.py](backend/app/services/llm.py))

1. **Ollama Connection Debug:**
   - 🤖 Streaming start logged
   - ✓ Connection established confirmation
   - Token counting and periodic logging
   - First 3 tokens + every 20th token logged

2. **Error Context:**
   - Connection errors with URL
   - JSON parse errors with line preview
   - Complete exception traces

## Testing WebSocket

### Option 1: Python Test Script

Run the included test script:

```bash
cd backend
source venv/bin/activate
python test_websocket.py
```

This will:
- Connect to WebSocket
- Send a test question
- Display streaming tokens in real-time
- Show sources when complete
- Report any errors

### Option 2: Browser Console

Open browser console and run:

```javascript
const ws = new WebSocket('ws://localhost:8000/api/v1/stream');

ws.onopen = () => {
    console.log('✓ Connected');
    ws.send(JSON.stringify({
        question: 'What is this codebase about?',
        top_k: 3
    }));
};

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log(data.type, data);

    if (data.type === 'token') {
        console.log(data.content, { end: '' });
    } else if (data.type === 'sources') {
        console.log('\n✓ Sources:', data.data.length);
    } else if (data.type === 'error') {
        console.error('✗ Error:', data.message);
    }
};

ws.onerror = (error) => {
    console.error('✗ WebSocket error:', error);
};

ws.onclose = () => {
    console.log('🔌 Disconnected');
};
```

### Option 3: Frontend App

1. Start backend:
```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --log-level debug
```

2. Start frontend:
```bash
cd frontend
npm run dev
```

3. Open http://localhost:5173
4. Check browser console (F12) for WebSocket logs
5. Check backend terminal for server logs

## Reading the Logs

### Backend Logs

Look for these indicators:

**Good:**
```
INFO:     ✓ WebSocket connection accepted successfully
INFO:     📨 Received WebSocket query: 'What is this about?'
INFO:     🤖 Starting streaming generation with llama3.1:8b
INFO:     ✓ Ollama streaming connection established (status 200)
DEBUG:    📤 Sending token #1: 'This'
DEBUG:    📤 Sending token #10: 'codebase'
INFO:     ✓ Streaming complete! Sent 150 tokens
INFO:     📚 Preparing sources...
INFO:     ✓ Query complete: 5 sources sent successfully
```

**Bad - Connection Issues:**
```
ERROR:    ✗ Failed to accept WebSocket connection: ...
ERROR:    ✗ Error sending token #45: ...
INFO:     🔌 WebSocket client disconnected (code: 1006)
```

**Bad - Ollama Issues:**
```
ERROR:    Could not connect to Ollama at http://localhost:11434
ERROR:    Model 'llama3.1:8b' not found
```

### Frontend Console

Look for WebSocket messages:
```
WebSocket connected
Received raw data: {"type":"token","content":"This"}
Received raw data: {"type":"sources","data":[...]}
```

If you see:
```
WebSocket error: ...
WebSocket disconnected
```

Check:
1. Backend is running
2. CORS is configured (should be by default)
3. No firewall blocking WebSocket

## Common Issues

### 1. "WebSocket keeps disconnecting"

**Cause:** Frontend might be reconnecting too aggressively

**Fix:** Check [frontend/src/hooks/useWebSocket.ts](frontend/src/hooks/useWebSocket.ts) - exponential backoff is implemented

### 2. "No tokens received"

**Check:**
- Backend logs show "📤 Sending token" messages
- If yes → frontend WebSocket hook issue
- If no → Ollama connection issue

**Fix:**
```bash
# Test Ollama directly
curl http://localhost:11434/api/generate -d '{
  "model": "llama3.1:8b",
  "prompt": "Hello",
  "stream": true
}'
```

### 3. "Tokens arrive but UI doesn't update"

**Cause:** Frontend message handler not processing tokens

**Check:** Browser console for errors in React components

**Fix:** Verify [ChatInterface.tsx](frontend/src/components/ChatInterface.tsx) `useEffect` handling

### 4. "Connection accepted but immediate disconnect"

**Cause:** Client sending invalid first message

**Check:** Backend logs for JSON parse errors

**Fix:** Verify frontend sends:
```json
{
  "question": "Your question here",
  "top_k": 5
}
```

## Debugging Checklist

Before reporting issues, verify:

- [ ] Backend running: `curl http://localhost:8000/api/v1/health`
- [ ] Ollama running: `curl http://localhost:11434/api/tags`
- [ ] WebSocket test passes: `python backend/test_websocket.py`
- [ ] Browser console shows WebSocket connection
- [ ] Backend logs show token sending
- [ ] No firewall/proxy blocking WebSocket

## Log Level Configuration

For more detailed debugging, set log level to DEBUG:

**.env:**
```bash
LOG_LEVEL=DEBUG
```

Or run uvicorn with:
```bash
uvicorn app.main:app --reload --log-level debug
```

This will show:
- Every token sent
- Raw WebSocket data
- Detailed HTTP requests
- ChromaDB queries

## Performance Notes

The 10ms delay between tokens (`asyncio.sleep(0.01)`) prevents:
- Overwhelming slow connections
- Browser buffering issues
- WebSocket frame fragmentation

If tokens arrive too slowly, reduce delay in [websocket.py](backend/app/api/websocket.py#L140):
```python
await asyncio.sleep(0.005)  # 5ms instead of 10ms
```

Or remove entirely for maximum speed (may cause issues on slow connections).

## Next Steps

If issues persist after debugging:
1. Share backend logs (with DEBUG level)
2. Share browser console output
3. Share result of `python test_websocket.py`
4. Note at which point it fails (connection/streaming/sources)

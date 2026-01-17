# Streaming Agent Visibility

## Transport Selection

| Transport | Best For | Bidirectional |
|-----------|----------|---------------|
| SSE (Server-Sent Events) | Simple streaming, wide browser support | No |
| WebSocket | Bidirectional, real-time interaction | Yes |
| HTTP Long-Polling | Fallback for restrictive networks | No |

## Server-Sent Events (SSE)

### FastAPI SSE Endpoint
```python
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
import asyncio
import json

app = FastAPI()

async def stream_agent_response(query: str):
    """Stream agent thinking and responses."""
    async for event in run_agent(query):
        if event["type"] == "thinking":
            yield f"event: thinking\ndata: {json.dumps(event)}\n\n"
        elif event["type"] == "tool_call":
            yield f"event: tool_call\ndata: {json.dumps(event)}\n\n"
        elif event["type"] == "response":
            yield f"event: response\ndata: {json.dumps(event)}\n\n"
        elif event["type"] == "done":
            yield f"event: done\ndata: {json.dumps(event)}\n\n"

@app.get("/agent/stream")
async def agent_stream(query: str):
    return StreamingResponse(
        stream_agent_response(query),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )
```

### React SSE Client
```typescript
function useAgentStream(query: string) {
  const [thinking, setThinking] = useState<string[]>([]);
  const [response, setResponse] = useState("");
  const [toolCalls, setToolCalls] = useState<ToolCall[]>([]);

  useEffect(() => {
    const eventSource = new EventSource(
      `/agent/stream?query=${encodeURIComponent(query)}`
    );

    eventSource.addEventListener("thinking", (e) => {
      const data = JSON.parse(e.data);
      setThinking((prev) => [...prev, data.content]);
    });

    eventSource.addEventListener("tool_call", (e) => {
      const data = JSON.parse(e.data);
      setToolCalls((prev) => [...prev, data]);
    });

    eventSource.addEventListener("response", (e) => {
      const data = JSON.parse(e.data);
      setResponse((prev) => prev + data.content);
    });

    eventSource.addEventListener("done", () => {
      eventSource.close();
    });

    eventSource.onerror = () => {
      eventSource.close();
    };

    return () => eventSource.close();
  }, [query]);

  return { thinking, response, toolCalls };
}
```

## WebSocket Implementation

### FastAPI WebSocket
```python
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import json

app = FastAPI()

class AgentSession:
    def __init__(self, websocket: WebSocket):
        self.websocket = websocket
        self.conversation_history = []
    
    async def send_event(self, event_type: str, data: dict):
        await self.websocket.send_json({
            "type": event_type,
            "data": data,
            "timestamp": time.time()
        })

@app.websocket("/agent/ws")
async def agent_websocket(websocket: WebSocket):
    await websocket.accept()
    session = AgentSession(websocket)
    
    try:
        while True:
            # Receive user message
            message = await websocket.receive_json()
            
            if message["type"] == "query":
                # Stream agent response
                async for event in run_agent(
                    message["content"],
                    session.conversation_history
                ):
                    await session.send_event(event["type"], event)
                
                # Update history
                session.conversation_history.append({
                    "role": "user",
                    "content": message["content"]
                })
                
            elif message["type"] == "interrupt":
                # Handle user interruption
                await cancel_current_task()
                
    except WebSocketDisconnect:
        pass
```

### React WebSocket Hook
```typescript
function useAgentWebSocket() {
  const [connected, setConnected] = useState(false);
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const ws = new WebSocket("ws://localhost:8000/agent/ws");
    wsRef.current = ws;

    ws.onopen = () => setConnected(true);
    ws.onclose = () => setConnected(false);
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setEvents((prev) => [...prev, data]);
    };

    return () => ws.close();
  }, []);

  const sendMessage = useCallback((content: string) => {
    wsRef.current?.send(JSON.stringify({
      type: "query",
      content
    }));
  }, []);

  const interrupt = useCallback(() => {
    wsRef.current?.send(JSON.stringify({ type: "interrupt" }));
  }, []);

  return { connected, events, sendMessage, interrupt };
}
```

## Streaming Anthropic to UI

### Full Pipeline
```python
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
import anthropic
import json

app = FastAPI()
client = anthropic.Anthropic()

async def stream_claude_response(messages: list):
    """Stream Claude response with thinking visibility."""
    
    with client.messages.stream(
        model="claude-sonnet-4-5",
        max_tokens=4096,
        thinking={"type": "enabled", "budget_tokens": 8000},
        messages=messages
    ) as stream:
        for event in stream:
            if event.type == "content_block_start":
                if event.content_block.type == "thinking":
                    yield f"event: thinking_start\ndata: {{}}\n\n"
                elif event.content_block.type == "text":
                    yield f"event: response_start\ndata: {{}}\n\n"
                    
            elif event.type == "content_block_delta":
                if hasattr(event.delta, "thinking"):
                    data = {"content": event.delta.thinking}
                    yield f"event: thinking\ndata: {json.dumps(data)}\n\n"
                elif hasattr(event.delta, "text"):
                    data = {"content": event.delta.text}
                    yield f"event: response\ndata: {json.dumps(data)}\n\n"
                    
            elif event.type == "message_stop":
                yield f"event: done\ndata: {{}}\n\n"

@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    messages = [{"role": "user", "content": request.content}]
    return StreamingResponse(
        stream_claude_response(messages),
        media_type="text/event-stream"
    )
```

## Framework-Agnostic Patterns

### Event Schema
```python
from pydantic import BaseModel
from typing import Literal
from datetime import datetime

class AgentEvent(BaseModel):
    type: Literal["thinking", "tool_call", "tool_result", "response", "error", "done"]
    content: str | dict | None = None
    timestamp: datetime
    metadata: dict = {}

# Consistent event emission
async def emit_event(event_type: str, content: any = None, **metadata):
    return AgentEvent(
        type=event_type,
        content=content,
        timestamp=datetime.utcnow(),
        metadata=metadata
    )
```

### Streamlit Integration
```python
import streamlit as st
import requests

st.title("Agent Chat")

if prompt := st.chat_input("Ask anything..."):
    with st.chat_message("user"):
        st.write(prompt)
    
    with st.chat_message("assistant"):
        thinking_placeholder = st.empty()
        response_placeholder = st.empty()
        
        thinking_text = ""
        response_text = ""
        
        # Stream from backend
        with requests.get(
            f"/agent/stream?query={prompt}",
            stream=True
        ) as r:
            for line in r.iter_lines():
                if line.startswith(b"event: "):
                    event_type = line[7:].decode()
                elif line.startswith(b"data: "):
                    data = json.loads(line[6:])
                    
                    if event_type == "thinking":
                        thinking_text += data.get("content", "")
                        with thinking_placeholder.expander("Thinking..."):
                            st.write(thinking_text)
                    elif event_type == "response":
                        response_text += data.get("content", "")
                        response_placeholder.write(response_text)
```

## Performance Considerations

1. **Buffering**: Disable proxy buffering (nginx, cloudflare)
2. **Heartbeats**: Send periodic pings to keep connection alive
3. **Reconnection**: Implement client-side reconnection with exponential backoff
4. **Compression**: Avoid for SSE (breaks streaming)

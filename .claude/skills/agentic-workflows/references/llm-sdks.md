# LLM SDK Integration

## Anthropic Claude SDK

### Basic Streaming
```python
import anthropic

client = anthropic.Anthropic()

with client.messages.stream(
    model="claude-sonnet-4-5",
    max_tokens=4096,
    messages=[{"role": "user", "content": "Hello"}]
) as stream:
    for text in stream.text_stream:
        print(text, end="", flush=True)
```

### Extended Thinking (Streaming)
```python
with client.messages.stream(
    model="claude-sonnet-4-5",
    max_tokens=16000,
    thinking={"type": "enabled", "budget_tokens": 10000},
    messages=[{"role": "user", "content": "Solve this complex problem..."}]
) as stream:
    for event in stream:
        if event.type == "content_block_delta":
            if hasattr(event.delta, "thinking_delta"):
                print(f"[Thinking] {event.delta.thinking}", end="")
            elif hasattr(event.delta, "text_delta"):
                print(event.delta.text, end="")
```

### Tool Use with Streaming
```python
tools = [{
    "name": "web_search",
    "description": "Search the web for information",
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query"}
        },
        "required": ["query"]
    }
}]

response = client.messages.create(
    model="claude-sonnet-4-5",
    max_tokens=4096,
    tools=tools,
    messages=[{"role": "user", "content": "Search for AI news"}]
)

# Handle tool use
for block in response.content:
    if block.type == "tool_use":
        tool_name = block.name
        tool_input = block.input
        # Execute tool and continue conversation
```

### Async Client
```python
from anthropic import AsyncAnthropic

client = AsyncAnthropic()

async def chat():
    async with client.messages.stream(
        model="claude-sonnet-4-5",
        max_tokens=1024,
        messages=[{"role": "user", "content": "Hello"}]
    ) as stream:
        async for text in stream.text_stream:
            print(text, end="", flush=True)
```

## OpenAI SDK

### Streaming with Function Calling
```python
from openai import OpenAI

client = OpenAI()

tools = [{
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "Get weather for a location",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {"type": "string"}
            },
            "required": ["location"]
        }
    }
}]

stream = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "What's the weather in SF?"}],
    tools=tools,
    stream=True
)

for chunk in stream:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="")
    if chunk.choices[0].delta.tool_calls:
        # Handle tool calls
        pass
```

### Structured Outputs (Native)
```python
from pydantic import BaseModel

class CalendarEvent(BaseModel):
    name: str
    date: str
    participants: list[str]

response = client.beta.chat.completions.parse(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Schedule a meeting..."}],
    response_format=CalendarEvent
)

event = response.choices[0].message.parsed
```

### Async Streaming
```python
from openai import AsyncOpenAI

client = AsyncOpenAI()

async def stream_response():
    stream = await client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": "Hello"}],
        stream=True
    )
    async for chunk in stream:
        if chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content
```

## vLLM Integration

### OpenAI-Compatible API
```python
from openai import OpenAI

# Point to vLLM server
client = OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="not-needed"
)

response = client.chat.completions.create(
    model="meta-llama/Llama-3.1-8B-Instruct",
    messages=[{"role": "user", "content": "Hello"}],
    stream=True
)

for chunk in response:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="")
```

### vLLM Server Launch
```bash
vllm serve meta-llama/Llama-3.1-8B-Instruct \
    --host 0.0.0.0 \
    --port 8000 \
    --tensor-parallel-size 2 \
    --gpu-memory-utilization 0.9
```

## Multi-Provider Routing

```python
from enum import Enum
from typing import Optional

class Provider(Enum):
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    VLLM = "vllm"

class ModelRouter:
    def __init__(self):
        self.anthropic = anthropic.Anthropic()
        self.openai = OpenAI()
        self.vllm = OpenAI(base_url="http://localhost:8000/v1", api_key="x")
    
    def route(self, task_type: str) -> Provider:
        """Route based on task requirements."""
        routing = {
            "complex_reasoning": Provider.ANTHROPIC,
            "code_generation": Provider.ANTHROPIC,
            "simple_chat": Provider.VLLM,
            "function_calling": Provider.OPENAI,
            "cost_sensitive": Provider.VLLM,
        }
        return routing.get(task_type, Provider.OPENAI)
    
    async def complete(self, messages: list, task_type: str):
        provider = self.route(task_type)
        
        if provider == Provider.ANTHROPIC:
            return await self._anthropic_complete(messages)
        elif provider == Provider.OPENAI:
            return await self._openai_complete(messages)
        else:
            return await self._vllm_complete(messages)
```

## Error Handling & Retries

```python
from tenacity import retry, stop_after_attempt, wait_exponential
import anthropic

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=60)
)
async def robust_completion(messages: list):
    try:
        response = await client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=4096,
            messages=messages
        )
        return response
    except anthropic.RateLimitError:
        raise  # Let tenacity retry
    except anthropic.APIError as e:
        logger.error(f"API error: {e}")
        raise
```

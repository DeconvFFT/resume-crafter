---
name: agentic-workflows
description: Build production-grade agentic AI systems with real-time streaming visibility, structured outputs, and multi-agent collaboration. Covers Anthropic/OpenAI/vLLM SDKs, A2A protocol for agent interoperability, Pydantic validation, LangGraph checkpointing for workflow resumption, vector DB memory (Pinecone/Chroma/FAISS), and guardrails for anti-hallucination. Use when building AI agents, multi-agent systems, tool-calling workflows, or applications requiring streaming agent reasoning to UI.
---

# Agentic Workflows Skill

Build intelligent, observable, and resilient AI agent systems.

## Architecture Decision Flow

```
New Agent System Request
           │
           ▼
┌──────────────────────────┐
│ Single task or multi-step?│
│ Single → Simple LLM call │
│ Multi-step → Agent loop  │
└──────────────────────────┘
           │
           ▼
┌──────────────────────────┐
│ Need multiple specialists?│
│ Yes → Multi-agent (A2A)  │
│ No → Single agent        │
└──────────────────────────┘
           │
           ▼
┌──────────────────────────┐
│ Long-running/resumable?   │
│ Yes → LangGraph + checkpoint│
│ No → Simple agent loop   │
└──────────────────────────┘
           │
           ▼
┌──────────────────────────┐
│ Need memory across sessions?│
│ Yes → Vector DB          │
│ No → In-session state    │
└──────────────────────────┘
```

## Provider Selection

| Provider | Best For | Streaming | Tools |
|----------|----------|-----------|-------|
| Anthropic Claude | Complex reasoning, extended thinking | SSE | Native |
| OpenAI GPT-4 | General purpose, function calling | SSE | Native |
| vLLM | Self-hosted, cost control | OpenAI-compatible | Via prompts |

## Quick Start Patterns

### Anthropic Streaming with Tools
```python
import anthropic

client = anthropic.Anthropic()

with client.messages.stream(
    model="claude-sonnet-4-5",
    max_tokens=4096,
    tools=[{"name": "search", "description": "Search the web", "input_schema": {...}}],
    messages=[{"role": "user", "content": "Research AI trends"}]
) as stream:
    for event in stream:
        if event.type == "content_block_delta":
            if hasattr(event.delta, "text"):
                print(event.delta.text, end="", flush=True)
            elif hasattr(event.delta, "thinking"):
                print(f"[Thinking] {event.delta.thinking}")
```

### Structured Output with Pydantic
```python
import instructor
from pydantic import BaseModel

class Analysis(BaseModel):
    summary: str
    confidence: float
    sources: list[str]

client = instructor.from_provider("anthropic/claude-sonnet-4-5")
result = client.create(
    response_model=Analysis,
    messages=[{"role": "user", "content": "Analyze market trends"}],
    max_retries=3
)
```

## Reference Documentation

| Task | Reference File |
|------|----------------|
| Anthropic/OpenAI/vLLM SDK patterns | [references/llm-sdks.md](references/llm-sdks.md) |
| Multi-agent with A2A protocol | [references/multi-agent.md](references/multi-agent.md) |
| Streaming to UI (SSE/WebSocket) | [references/streaming.md](references/streaming.md) |
| Pydantic structured outputs | [references/structured-outputs.md](references/structured-outputs.md) |
| Memory with vector DBs | [references/memory.md](references/memory.md) |
| Checkpointing & resumption | [references/checkpointing.md](references/checkpointing.md) |
| Guardrails & anti-hallucination | [references/guardrails.md](references/guardrails.md) |

## When to Use Multi-Agent

| Scenario | Approach |
|----------|----------|
| Different expertise needed | Multi-agent with specialists |
| Verification required | Debate pattern (critic agent) |
| Complex workflow orchestration | Supervisor + workers |
| Simple tool use | Single agent with tools |
| Independent subtasks | Parallel agents |

## Production Checklist

- [ ] Structured outputs with Pydantic validation
- [ ] Retry logic with exponential backoff
- [ ] Streaming to UI for visibility
- [ ] Checkpointing for long-running workflows
- [ ] Guardrails for input/output validation
- [ ] Memory persistence (vector DB or KV store)
- [ ] Error handling with graceful degradation
- [ ] Observability (logging, tracing)

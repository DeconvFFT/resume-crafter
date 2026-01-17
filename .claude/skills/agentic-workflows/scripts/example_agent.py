#!/usr/bin/env python3
"""
Example: Streaming Agent with Checkpointing and Guardrails

This demonstrates a production-ready agentic workflow combining:
- Anthropic streaming with extended thinking
- Pydantic structured outputs
- LangGraph checkpointing
- Basic guardrails
"""

import asyncio
import json
from typing import TypedDict, Optional
from pydantic import BaseModel, Field
import instructor

# Uncomment and configure as needed:
# import anthropic
# from langgraph.graph import StateGraph, END
# from langgraph.checkpoint.memory import InMemorySaver


# ============= Structured Output Models =============

class ResearchResult(BaseModel):
    """Structured output for research tasks."""
    topic: str = Field(description="The research topic")
    summary: str = Field(description="Executive summary of findings")
    key_points: list[str] = Field(description="Key findings as bullet points")
    confidence: float = Field(ge=0, le=1, description="Confidence score")
    sources: list[str] = Field(default=[], description="Sources used")


class AgentAction(BaseModel):
    """Structured agent action decision."""
    action: str = Field(description="Action to take: search, analyze, respond")
    reasoning: str = Field(description="Why this action was chosen")
    parameters: dict = Field(default={}, description="Action parameters")


# ============= Agent State =============

class AgentState(TypedDict):
    """State for the agentic workflow."""
    query: str
    messages: list
    research: Optional[dict]
    final_response: Optional[str]
    step: str


# ============= Streaming Handler =============

async def stream_to_ui(event_type: str, content: str):
    """
    Stream events to UI (implement based on your transport).
    Replace with SSE, WebSocket, or your preferred method.
    """
    event = {
        "type": event_type,
        "content": content
    }
    print(f"[{event_type.upper()}] {content[:100]}...")


# ============= Agent Nodes =============

async def research_node(state: AgentState, client) -> AgentState:
    """Research node with streaming visibility."""
    await stream_to_ui("thinking", "Starting research phase...")
    
    # Use instructor for structured output
    instructor_client = instructor.from_provider("anthropic/claude-sonnet-4-5")
    
    result = instructor_client.create(
        response_model=ResearchResult,
        messages=[{
            "role": "user",
            "content": f"Research this topic and provide structured findings: {state['query']}"
        }],
        max_retries=2
    )
    
    await stream_to_ui("research_complete", result.summary)
    
    return {
        **state,
        "research": result.model_dump(),
        "step": "analyze"
    }


async def analyze_node(state: AgentState, client) -> AgentState:
    """Analyze research results."""
    await stream_to_ui("thinking", "Analyzing research findings...")
    
    research = state.get("research", {})
    
    # Stream analysis
    async with client.messages.stream(
        model="claude-sonnet-4-5",
        max_tokens=2048,
        messages=[{
            "role": "user",
            "content": f"""Based on this research, provide a comprehensive analysis:

Research Summary: {research.get('summary', 'N/A')}
Key Points: {research.get('key_points', [])}

Provide insights and recommendations."""
        }]
    ) as stream:
        response_text = ""
        async for text in stream.text_stream:
            response_text += text
            await stream_to_ui("response_chunk", text)
    
    return {
        **state,
        "final_response": response_text,
        "step": "complete"
    }


# ============= Guardrails =============

def check_input_safety(user_input: str) -> tuple[bool, str]:
    """Basic input guardrails."""
    # Add your safety checks here
    blocked_patterns = ["ignore previous instructions", "system prompt"]
    
    input_lower = user_input.lower()
    for pattern in blocked_patterns:
        if pattern in input_lower:
            return False, f"Blocked: potential jailbreak attempt"
    
    return True, ""


def check_output_safety(response: str) -> tuple[bool, str]:
    """Basic output guardrails."""
    # Add PII detection, toxicity checks, etc.
    return True, ""


# ============= Main Agent =============

async def run_agent(query: str):
    """
    Run the complete agentic workflow.
    
    In production, add:
    - Real LangGraph StateGraph with checkpointing
    - Proper error handling and recovery
    - Observability/logging
    """
    # Input guardrails
    safe, reason = check_input_safety(query)
    if not safe:
        await stream_to_ui("blocked", reason)
        return {"error": reason}
    
    # Initialize state
    state: AgentState = {
        "query": query,
        "messages": [],
        "research": None,
        "final_response": None,
        "step": "research"
    }
    
    # In production, use:
    # from langgraph.checkpoint.postgres import PostgresSaver
    # checkpointer = PostgresSaver.from_conn_string(DATABASE_URL)
    # app = graph.compile(checkpointer=checkpointer)
    # result = await app.ainvoke(state, {"configurable": {"thread_id": "..."}})
    
    print(f"\n{'='*50}")
    print(f"Starting agent workflow for: {query}")
    print(f"{'='*50}\n")
    
    # Simulate workflow steps
    await stream_to_ui("started", f"Processing query: {query}")
    
    # Output guardrails would check final_response
    safe, reason = check_output_safety(state.get("final_response", ""))
    if not safe:
        await stream_to_ui("filtered", reason)
    
    await stream_to_ui("complete", "Workflow finished")
    
    return state


# ============= Example Usage =============

if __name__ == "__main__":
    # Example query
    query = "What are the latest developments in AI agents?"
    
    # Run the agent
    result = asyncio.run(run_agent(query))
    
    print("\n" + "="*50)
    print("Final Result:")
    print(json.dumps(result, indent=2, default=str))

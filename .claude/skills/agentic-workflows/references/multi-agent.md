# Multi-Agent Systems & A2A Protocol

## Google A2A Protocol Overview

A2A (Agent-to-Agent) is an open protocol for secure agent interoperability, now under Linux Foundation governance.

### Core Concepts

| Component | Description |
|-----------|-------------|
| Agent Card | JSON metadata at `/.well-known/agent.json` describing capabilities |
| Client Agent | Initiates tasks, interfaces with users |
| Remote Agent | Executes tasks, returns results |
| Task | Unit of work with lifecycle states |

### Agent Card Schema
```json
{
  "name": "research-agent",
  "description": "Performs deep research on topics",
  "url": "https://agent.example.com",
  "version": "1.0.0",
  "capabilities": {
    "streaming": true,
    "pushNotifications": true
  },
  "skills": [
    {
      "id": "web-research",
      "name": "Web Research",
      "description": "Search and synthesize information from the web"
    }
  ],
  "authentication": {
    "schemes": ["bearer", "oauth2"]
  }
}
```

### A2A Communication Flow

```
1. Discovery: Client fetches /.well-known/agent.json
2. Task Creation: Client POSTs task to remote agent
3. Status Updates: Remote sends progress via SSE/webhook
4. Completion: Remote returns artifacts
```

### Python A2A Client
```python
from a2a import A2AClient, Task

# Discover agent
client = A2AClient()
agent_card = await client.discover("https://research-agent.example.com")

# Create task
task = Task(
    skill_id="web-research",
    input={"query": "Latest AI developments"},
    callback_url="https://my-app.com/webhook"
)

# Send task and stream results
async for update in client.execute_streaming(agent_card, task):
    if update.type == "progress":
        print(f"Progress: {update.message}")
    elif update.type == "artifact":
        print(f"Result: {update.content}")
```

### A2A Server Implementation
```python
from fastapi import FastAPI
from a2a.server import A2AServer, AgentCard, Skill

app = FastAPI()
a2a = A2AServer(app)

# Define agent capabilities
card = AgentCard(
    name="analysis-agent",
    description="Analyzes data and provides insights",
    skills=[
        Skill(id="analyze", name="Data Analysis", description="...")
    ]
)

@a2a.skill("analyze")
async def analyze_data(input: dict, context: A2AContext):
    # Stream progress
    await context.send_progress("Starting analysis...")
    
    # Do work
    result = await perform_analysis(input["data"])
    
    # Return artifact
    return {"analysis": result, "confidence": 0.95}

a2a.register(card)
```

## Multi-Agent Patterns

### Supervisor-Worker Pattern
```python
from langgraph.graph import StateGraph, END
from typing import TypedDict, Literal

class AgentState(TypedDict):
    task: str
    plan: list[str]
    results: dict
    final_answer: str

def supervisor(state: AgentState) -> AgentState:
    """Supervisor plans and delegates."""
    plan = plan_task(state["task"])
    return {"plan": plan}

def researcher(state: AgentState) -> AgentState:
    """Research agent gathers information."""
    results = research(state["plan"][0])
    return {"results": {"research": results}}

def writer(state: AgentState) -> AgentState:
    """Writer agent synthesizes results."""
    answer = synthesize(state["results"])
    return {"final_answer": answer}

def router(state: AgentState) -> Literal["researcher", "writer", "end"]:
    if not state.get("results"):
        return "researcher"
    elif not state.get("final_answer"):
        return "writer"
    return "end"

# Build graph
graph = StateGraph(AgentState)
graph.add_node("supervisor", supervisor)
graph.add_node("researcher", researcher)
graph.add_node("writer", writer)
graph.add_conditional_edges("supervisor", router)
graph.add_edge("researcher", "supervisor")
graph.add_edge("writer", END)
graph.set_entry_point("supervisor")
```

### Debate Pattern (Critic Agent)
```python
class DebateState(TypedDict):
    question: str
    proposal: str
    critique: str
    revision: str
    rounds: int
    consensus: bool

def proposer(state: DebateState) -> DebateState:
    """Generate initial proposal or revision."""
    if state.get("critique"):
        proposal = revise_based_on_feedback(
            state["proposal"], 
            state["critique"]
        )
    else:
        proposal = generate_proposal(state["question"])
    return {"proposal": proposal, "rounds": state.get("rounds", 0) + 1}

def critic(state: DebateState) -> DebateState:
    """Critically evaluate the proposal."""
    critique = evaluate_proposal(state["proposal"])
    consensus = critique["score"] > 0.8
    return {"critique": critique["feedback"], "consensus": consensus}

def should_continue(state: DebateState) -> Literal["proposer", "end"]:
    if state["consensus"] or state["rounds"] >= 3:
        return "end"
    return "proposer"

# Build debate graph
graph = StateGraph(DebateState)
graph.add_node("proposer", proposer)
graph.add_node("critic", critic)
graph.add_edge("proposer", "critic")
graph.add_conditional_edges("critic", should_continue)
graph.set_entry_point("proposer")
```

### Parallel Agents
```python
from langgraph.graph import StateGraph
import asyncio

class ParallelState(TypedDict):
    query: str
    web_results: str
    db_results: str
    combined: str

async def web_search(state: ParallelState) -> dict:
    results = await search_web(state["query"])
    return {"web_results": results}

async def db_search(state: ParallelState) -> dict:
    results = await search_database(state["query"])
    return {"db_results": results}

def combine_results(state: ParallelState) -> ParallelState:
    combined = merge(state["web_results"], state["db_results"])
    return {"combined": combined}

# Parallel execution
graph = StateGraph(ParallelState)
graph.add_node("web_search", web_search)
graph.add_node("db_search", db_search)
graph.add_node("combine", combine_results)

# Both search nodes run in parallel from start
graph.set_entry_point("web_search")
graph.set_entry_point("db_search")
graph.add_edge("web_search", "combine")
graph.add_edge("db_search", "combine")
```

## When to Use Each Pattern

| Pattern | Use Case |
|---------|----------|
| Single Agent | Simple tasks, direct tool use |
| Supervisor-Worker | Complex workflows needing coordination |
| Debate/Critic | Quality-critical outputs, verification |
| Parallel | Independent subtasks, speed optimization |
| A2A Federation | Cross-organization, different frameworks |

## A2A vs MCP

| Protocol | Purpose |
|----------|---------|
| A2A | Agent-to-agent communication |
| MCP | Agent-to-tool/data communication |

Use MCP for tools and data sources, A2A for agent collaboration.

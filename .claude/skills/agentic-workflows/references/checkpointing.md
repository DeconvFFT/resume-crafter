# Checkpointing & Workflow Resumption

## LangGraph Checkpointing

LangGraph provides persistence for stateful workflows with automatic checkpointing.

### Core Concepts

| Concept | Description |
|---------|-------------|
| Checkpoint | Snapshot of graph state at a super-step |
| Thread | Unique ID for a conversation/workflow |
| Checkpointer | Persistence backend (memory, SQLite, Postgres) |

### Basic Setup
```python
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import InMemorySaver
from typing import TypedDict

class AgentState(TypedDict):
    messages: list
    current_step: str
    results: dict

# Build graph
graph = StateGraph(AgentState)
graph.add_node("research", research_node)
graph.add_node("analyze", analyze_node)
graph.add_node("write", write_node)
graph.add_edge("research", "analyze")
graph.add_edge("analyze", "write")
graph.add_edge("write", END)
graph.set_entry_point("research")

# Compile with checkpointer
checkpointer = InMemorySaver()
app = graph.compile(checkpointer=checkpointer)

# Run with thread_id
config = {"configurable": {"thread_id": "workflow-123"}}
result = app.invoke({"messages": ["Start research"]}, config)
```

### Production Checkpointers

#### SQLite (Local/Development)
```python
from langgraph.checkpoint.sqlite import SqliteSaver

# Sync
checkpointer = SqliteSaver.from_conn_string("checkpoints.db")

# Async
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
checkpointer = AsyncSqliteSaver.from_conn_string("checkpoints.db")
```

#### PostgreSQL (Production)
```python
from langgraph.checkpoint.postgres import PostgresSaver

checkpointer = PostgresSaver.from_conn_string(
    "postgresql://user:pass@localhost/db"
)

# With connection pooling
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
import asyncpg

pool = await asyncpg.create_pool(
    "postgresql://user:pass@localhost/db",
    min_size=5,
    max_size=20
)
checkpointer = AsyncPostgresSaver(pool)
```

#### DynamoDB (AWS)
```python
from langgraph_checkpoint_aws import DynamoDBSaver

checkpointer = DynamoDBSaver(
    table_name="langgraph-checkpoints",
    s3_bucket="langgraph-large-payloads",  # For checkpoints > 350KB
    enable_checkpoint_compression=True
)
```

### Resume from Failure
```python
async def run_with_recovery(
    app, 
    initial_state: dict, 
    thread_id: str
):
    config = {"configurable": {"thread_id": thread_id}}
    
    try:
        # Check for existing checkpoint
        checkpoint = await app.checkpointer.get(config)
        
        if checkpoint:
            print(f"Resuming from checkpoint: {checkpoint['id']}")
            # Resume from last checkpoint
            result = await app.ainvoke(None, config)
        else:
            # Start fresh
            result = await app.ainvoke(initial_state, config)
        
        return result
        
    except Exception as e:
        # State is saved at last successful step
        print(f"Failed at step, can resume: {e}")
        raise
```

### Time Travel (Debug)
```python
# List all checkpoints for a thread
checkpoints = list(app.checkpointer.list(config))

for cp in checkpoints:
    print(f"Checkpoint {cp.checkpoint_id}: {cp.metadata}")

# Resume from specific checkpoint
specific_config = {
    "configurable": {
        "thread_id": "workflow-123",
        "checkpoint_id": "checkpoint-abc"
    }
}
result = app.invoke(None, specific_config)
```

### Human-in-the-Loop
```python
from langgraph.graph import StateGraph, END

def approval_node(state: AgentState) -> AgentState:
    """Node that requires human approval."""
    return {"pending_approval": True}

def process_approval(state: AgentState) -> AgentState:
    """Process after approval received."""
    return {"approved": True, "pending_approval": False}

graph = StateGraph(AgentState)
graph.add_node("generate", generate_node)
graph.add_node("await_approval", approval_node)
graph.add_node("process", process_approval)

# Interrupt before approval
graph.add_edge("generate", "await_approval")
graph.add_conditional_edges(
    "await_approval",
    lambda s: "wait" if s.get("pending_approval") else "process",
    {"wait": END, "process": "process"}
)

app = graph.compile(
    checkpointer=checkpointer,
    interrupt_before=["await_approval"]  # Pause here
)

# First run - stops at approval
result = app.invoke(initial_state, config)
# Returns with pending_approval=True

# Later - resume after human approves
app.update_state(config, {"pending_approval": False, "approved": True})
final_result = app.invoke(None, config)
```

## Custom Checkpointing

### Database-Backed State
```python
from abc import ABC, abstractmethod
from typing import Optional
import json

class WorkflowState:
    def __init__(self, workflow_id: str, db):
        self.workflow_id = workflow_id
        self.db = db
    
    async def save(self, step: str, data: dict):
        """Save checkpoint."""
        await self.db.execute(
            """
            INSERT INTO checkpoints (workflow_id, step, data, created_at)
            VALUES ($1, $2, $3, NOW())
            ON CONFLICT (workflow_id, step) 
            DO UPDATE SET data = $3, created_at = NOW()
            """,
            self.workflow_id, step, json.dumps(data)
        )
    
    async def load(self, step: Optional[str] = None) -> Optional[dict]:
        """Load latest or specific checkpoint."""
        if step:
            row = await self.db.fetchrow(
                "SELECT data FROM checkpoints WHERE workflow_id = $1 AND step = $2",
                self.workflow_id, step
            )
        else:
            row = await self.db.fetchrow(
                """
                SELECT data FROM checkpoints 
                WHERE workflow_id = $1 
                ORDER BY created_at DESC LIMIT 1
                """,
                self.workflow_id
            )
        
        return json.loads(row["data"]) if row else None
    
    async def get_last_step(self) -> Optional[str]:
        """Get the last completed step."""
        row = await self.db.fetchrow(
            """
            SELECT step FROM checkpoints 
            WHERE workflow_id = $1 
            ORDER BY created_at DESC LIMIT 1
            """,
            self.workflow_id
        )
        return row["step"] if row else None
```

### Resumable Agent Loop
```python
class ResumableAgent:
    def __init__(self, llm_client, state: WorkflowState):
        self.client = llm_client
        self.state = state
        
    async def run(self, task: str):
        # Check for existing progress
        last_step = await self.state.get_last_step()
        checkpoint = await self.state.load() if last_step else None
        
        if checkpoint:
            print(f"Resuming from step: {last_step}")
            messages = checkpoint.get("messages", [])
            step_index = checkpoint.get("step_index", 0)
        else:
            messages = [{"role": "user", "content": task}]
            step_index = 0
        
        steps = ["plan", "research", "draft", "review", "finalize"]
        
        for i, step in enumerate(steps[step_index:], start=step_index):
            try:
                result = await self._execute_step(step, messages)
                messages.append({"role": "assistant", "content": result})
                
                # Checkpoint after each step
                await self.state.save(step, {
                    "messages": messages,
                    "step_index": i + 1,
                    "step_result": result
                })
                
            except Exception as e:
                print(f"Failed at {step}, checkpoint saved")
                raise
        
        return messages[-1]["content"]
```

## Best Practices

1. **Choose the right backend**:
   - InMemorySaver: Testing only
   - SQLite: Local dev, single instance
   - PostgreSQL: Production, multi-instance
   - DynamoDB: Serverless, AWS-native

2. **Checkpoint granularity**: Save after expensive operations, not every micro-step

3. **State serialization**: Ensure all state is JSON-serializable

4. **Thread management**: Use meaningful thread IDs (user_id + session_id)

5. **Cleanup**: Implement TTL or manual cleanup for old checkpoints

6. **Compression**: Enable for large states (DynamoDB/Postgres)

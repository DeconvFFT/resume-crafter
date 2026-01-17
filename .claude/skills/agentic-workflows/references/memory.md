# Memory & Vector Databases

## Vector DB Selection

| Database | Best For | Hosting |
|----------|----------|---------|
| Pinecone | Production, managed, low-ops | Cloud only |
| Chroma | Local dev, prototyping, embedded | Self-hosted |
| FAISS | High-performance, on-prem, large-scale | Self-hosted |

## Pinecone (Production)

### Setup
```python
from pinecone import Pinecone, ServerlessSpec

pc = Pinecone(api_key="your-api-key")

# Create index
pc.create_index(
    name="agent-memory",
    dimension=1536,  # OpenAI embedding dimension
    metric="cosine",
    spec=ServerlessSpec(cloud="aws", region="us-east-1")
)

index = pc.Index("agent-memory")
```

### Store & Retrieve
```python
from openai import OpenAI

openai_client = OpenAI()

def get_embedding(text: str) -> list[float]:
    response = openai_client.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )
    return response.data[0].embedding

# Store memory
def store_memory(user_id: str, content: str, metadata: dict = {}):
    embedding = get_embedding(content)
    index.upsert(
        vectors=[{
            "id": f"{user_id}_{uuid.uuid4()}",
            "values": embedding,
            "metadata": {
                "user_id": user_id,
                "content": content,
                "timestamp": datetime.utcnow().isoformat(),
                **metadata
            }
        }],
        namespace=user_id
    )

# Retrieve relevant memories
def recall_memories(user_id: str, query: str, top_k: int = 5) -> list[dict]:
    query_embedding = get_embedding(query)
    results = index.query(
        namespace=user_id,
        vector=query_embedding,
        top_k=top_k,
        include_metadata=True
    )
    return [
        {
            "content": match.metadata["content"],
            "score": match.score,
            "timestamp": match.metadata["timestamp"]
        }
        for match in results.matches
    ]
```

## Chroma (Development)

### Setup
```python
import chromadb
from chromadb.config import Settings

# Persistent storage
client = chromadb.PersistentClient(path="./chroma_db")

# Or in-memory for testing
# client = chromadb.Client()

collection = client.get_or_create_collection(
    name="agent_memory",
    metadata={"hnsw:space": "cosine"}
)
```

### Store & Retrieve
```python
# Store with auto-embedding
collection.add(
    documents=["User prefers concise responses", "User is working on ML project"],
    metadatas=[
        {"user_id": "user123", "type": "preference"},
        {"user_id": "user123", "type": "context"}
    ],
    ids=["mem1", "mem2"]
)

# Query
results = collection.query(
    query_texts=["What does the user like?"],
    n_results=5,
    where={"user_id": "user123"}
)

for doc, metadata, distance in zip(
    results["documents"][0],
    results["metadatas"][0],
    results["distances"][0]
):
    print(f"[{1 - distance:.2f}] {doc}")
```

## FAISS (High Performance)

### Setup
```python
import faiss
import numpy as np
from dataclasses import dataclass

@dataclass
class MemoryStore:
    index: faiss.Index
    id_to_content: dict[int, dict]
    current_id: int = 0

def create_faiss_store(dimension: int = 1536) -> MemoryStore:
    # IVF index for large-scale
    quantizer = faiss.IndexFlatL2(dimension)
    index = faiss.IndexIVFFlat(quantizer, dimension, 100)
    
    # Or simple flat index for smaller datasets
    # index = faiss.IndexFlatL2(dimension)
    
    return MemoryStore(index=index, id_to_content={})
```

### Store & Retrieve
```python
def add_memory(store: MemoryStore, embedding: np.ndarray, content: dict):
    if not store.index.is_trained:
        # Train IVF index (need enough vectors)
        store.index.train(embedding.reshape(1, -1))
    
    store.index.add(embedding.reshape(1, -1))
    store.id_to_content[store.current_id] = content
    store.current_id += 1

def search_memories(
    store: MemoryStore, 
    query_embedding: np.ndarray, 
    k: int = 5
) -> list[dict]:
    distances, indices = store.index.search(
        query_embedding.reshape(1, -1), k
    )
    
    results = []
    for dist, idx in zip(distances[0], indices[0]):
        if idx != -1:  # Valid result
            results.append({
                **store.id_to_content[idx],
                "distance": float(dist)
            })
    return results

# Save/Load
def save_store(store: MemoryStore, path: str):
    faiss.write_index(store.index, f"{path}/index.faiss")
    with open(f"{path}/content.json", "w") as f:
        json.dump(store.id_to_content, f)
```

## Memory Patterns

### Short-Term vs Long-Term
```python
class AgentMemory:
    def __init__(self, vector_db):
        self.short_term: list[dict] = []  # Current session
        self.vector_db = vector_db  # Long-term
        self.max_short_term = 20
    
    def add(self, content: str, importance: float = 0.5):
        memory = {
            "content": content,
            "timestamp": datetime.utcnow(),
            "importance": importance
        }
        
        # Always add to short-term
        self.short_term.append(memory)
        if len(self.short_term) > self.max_short_term:
            self._consolidate()
        
        # High importance goes to long-term immediately
        if importance > 0.7:
            self._store_long_term(memory)
    
    def _consolidate(self):
        """Move important short-term to long-term, summarize rest."""
        important = [m for m in self.short_term if m["importance"] > 0.5]
        for memory in important:
            self._store_long_term(memory)
        
        # Summarize and store less important
        if len(self.short_term) > len(important):
            summary = self._summarize(self.short_term)
            self._store_long_term({"content": summary, "type": "summary"})
        
        self.short_term = []
    
    def recall(self, query: str, k: int = 5) -> list[dict]:
        """Combine short-term and long-term recall."""
        long_term = self.vector_db.search(query, k=k)
        
        # Add relevant short-term
        relevant_short = self._filter_relevant(self.short_term, query)
        
        return self._merge_and_rank(long_term, relevant_short)
```

### Memory Summarization
```python
async def summarize_memories(memories: list[dict], client) -> str:
    """Compress multiple memories into a summary."""
    content = "\n".join([m["content"] for m in memories])
    
    response = await client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=500,
        messages=[{
            "role": "user",
            "content": f"""Summarize these conversation memories into key points:

{content}

Provide a concise summary that preserves important information."""
        }]
    )
    return response.content[0].text
```

## Integration with Agents

```python
class MemoryAugmentedAgent:
    def __init__(self, llm_client, memory: AgentMemory):
        self.client = llm_client
        self.memory = memory
    
    async def respond(self, user_message: str) -> str:
        # Recall relevant memories
        memories = self.memory.recall(user_message, k=5)
        
        # Build context
        memory_context = "\n".join([
            f"- {m['content']}" for m in memories
        ])
        
        # Generate response with memory context
        response = await self.client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=2048,
            system=f"""You have access to these memories about the user:
{memory_context}

Use this context to provide personalized, contextual responses.""",
            messages=[{"role": "user", "content": user_message}]
        )
        
        # Store new memory
        self.memory.add(
            f"User: {user_message}\nAssistant: {response.content[0].text}",
            importance=0.5
        )
        
        return response.content[0].text
```

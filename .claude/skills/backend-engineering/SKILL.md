---
name: backend-engineering
description: Build production-grade, scalable backends with Rust (Axum) for high-performance services and FastAPI for Python APIs. Includes ML inference serving (ONNX, vLLM, TensorRT), event-driven architecture (Kafka, RabbitMQ, Redis), Docker/Kubernetes orchestration, and AWS deployment (ECS, EKS, Lambda). Use when building APIs, microservices, real-time systems, ML serving infrastructure, or deploying containerized applications to AWS.
---

# Backend Engineering Skill

Build scalable, high-performance backends using the right tool for each layer.

## Language Selection Framework

| Use Case | Choose | Rationale |
|----------|--------|-----------|
| High-throughput streaming | Rust/Axum | Memory efficiency, no GC pauses |
| ML inference orchestration | FastAPI | Library ecosystem, model compatibility |
| CRUD APIs, rapid prototyping | FastAPI | Development velocity |
| Sub-millisecond latency | Rust/Axum | Predictable performance |
| Data pipelines | Hybrid | Rust for hot paths, Python for orchestration |

## Quick Start Patterns

### FastAPI Service
```python
from fastapi import FastAPI, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: initialize pools, connections
    yield
    # Shutdown: cleanup

app = FastAPI(lifespan=lifespan)

@app.get("/health")
async def health(): return {"status": "ok"}
```

### Rust/Axum Service
```rust
use axum::{routing::get, Router, Json};
use std::sync::Arc;

#[derive(Clone)]
struct AppState { /* db pools, config */ }

async fn health() -> Json<serde_json::Value> {
    Json(serde_json::json!({"status": "ok"}))
}

#[tokio::main]
async fn main() {
    let app = Router::new()
        .route("/health", get(health))
        .with_state(Arc::new(AppState {}));
    
    let listener = tokio::net::TcpListener::bind("0.0.0.0:3000").await.unwrap();
    axum::serve(listener, app).await.unwrap();
}
```

## Reference Documentation

Consult these references based on task requirements:

| Task | Reference File |
|------|----------------|
| FastAPI patterns, async DB, testing | [references/fastapi.md](references/fastapi.md) |
| Rust/Axum services, SQLx, error handling | [references/rust.md](references/rust.md) |
| ML inference, quantization, vLLM | [references/ml-serving.md](references/ml-serving.md) |
| Kafka, RabbitMQ, Redis, event patterns | [references/event-driven.md](references/event-driven.md) |
| Docker multi-stage builds, security | [references/docker.md](references/docker.md) |
| Kubernetes production patterns | [references/kubernetes.md](references/kubernetes.md) |
| AWS ECS, EKS, Lambda, CDK | [references/aws.md](references/aws.md) |

## Architecture Decision Flow

```
New Backend Service Request
           │
           ▼
┌──────────────────────────┐
│ Latency requirement?      │
│ < 10ms → Rust            │
│ > 10ms → FastAPI ok      │
└──────────────────────────┘
           │
           ▼
┌──────────────────────────┐
│ ML model serving?         │
│ LLM → vLLM               │
│ Vision/NLP → ONNX/TensorRT│
│ None → skip              │
└──────────────────────────┘
           │
           ▼
┌──────────────────────────┐
│ Event-driven?             │
│ High throughput → Kafka  │
│ Complex routing → RabbitMQ│
│ Real-time → Redis Streams│
└──────────────────────────┘
           │
           ▼
┌──────────────────────────┐
│ Deployment target?        │
│ Simple → ECS Fargate     │
│ Complex/Multi-cloud → EKS│
│ Event handlers → Lambda  │
└──────────────────────────┘
```

## Production Checklist

Before deploying any service:

- [ ] Health checks (liveness + readiness)
- [ ] Graceful shutdown handling
- [ ] Resource limits configured (CPU, memory)
- [ ] Connection pooling tuned
- [ ] Circuit breakers on external calls
- [ ] Structured logging (JSON)
- [ ] Distributed tracing enabled
- [ ] Secrets in Secrets Manager
- [ ] Multi-stage Docker build
- [ ] Auto-scaling configured

# Docker Best Practices

## Multi-Stage Builds

Separate build dependencies from runtime for smaller, secure images.

### Python/FastAPI
```dockerfile
# Build stage
FROM python:3.12-slim AS builder
WORKDIR /app

RUN pip install --no-cache-dir poetry
COPY pyproject.toml poetry.lock ./
RUN poetry export -f requirements.txt --output requirements.txt --without-hashes
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /wheels -r requirements.txt

# Runtime stage
FROM python:3.12-slim
WORKDIR /app

RUN useradd -r -s /bin/false appuser
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/* && rm -rf /wheels

COPY --chown=appuser:appuser ./src ./src
USER appuser

EXPOSE 8000
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Rust with cargo-chef
```dockerfile
FROM rust:1.82-bookworm AS chef
RUN cargo install cargo-chef
WORKDIR /app

FROM chef AS planner
COPY . .
RUN cargo chef prepare --recipe-path recipe.json

FROM chef AS builder
COPY --from=planner /app/recipe.json recipe.json
RUN cargo chef cook --release --recipe-path recipe.json
COPY . .
RUN cargo build --release

FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y ca-certificates && rm -rf /var/lib/apt/lists/*
RUN useradd -r -s /bin/false appuser
USER appuser
COPY --from=builder /app/target/release/my-app /usr/local/bin/
EXPOSE 3000
ENTRYPOINT ["/usr/local/bin/my-app"]
```

### Node.js
```dockerfile
FROM node:22 AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:22-slim
WORKDIR /app
RUN useradd -r -s /bin/false appuser

COPY --from=builder /app/dist ./dist
COPY --from=builder /app/package*.json ./
RUN npm ci --only=production && npm cache clean --force

USER appuser
EXPOSE 3000
CMD ["node", "dist/index.js"]
```

## Security Best Practices

### Run as Non-Root
```dockerfile
# Create non-root user
RUN useradd -r -s /bin/false -u 1001 appuser

# Change ownership of app files
COPY --chown=appuser:appuser ./app ./app

# Switch to non-root user
USER appuser
```

### Pin Image Versions
```dockerfile
# Bad: uses floating tag
FROM python:3.12-slim

# Good: pin to digest for reproducibility
FROM python:3.12-slim@sha256:abc123...
```

### Minimal Base Images
| Base Image | Size | Use Case |
|------------|------|----------|
| `scratch` | 0MB | Static binaries (Go, Rust) |
| `alpine` | ~5MB | Small footprint, musl libc |
| `distroless` | ~20MB | Google-maintained, no shell |
| `*-slim` | ~50-150MB | Debian-based, glibc compatible |

### Scan for Vulnerabilities
```bash
# Scan with Trivy
trivy image myapp:latest

# Scan with Docker Scout
docker scout cves myapp:latest
```

## Build Optimization

### Layer Caching
```dockerfile
# Copy dependency files first (changes less often)
COPY package*.json ./
RUN npm ci

# Copy source code last (changes frequently)
COPY . .
RUN npm run build
```

### Use .dockerignore
```
# .dockerignore
.git
.gitignore
node_modules
__pycache__
*.pyc
.env
.env.*
Dockerfile*
docker-compose*
README.md
tests/
.pytest_cache/
.coverage
*.log
```

### BuildKit Features
```dockerfile
# syntax=docker/dockerfile:1

# Cache mount for package managers
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

# Secret mount (not stored in image)
RUN --mount=type=secret,id=aws_credentials \
    aws s3 cp s3://bucket/file ./file
```

## Health Checks

```dockerfile
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1
```

## Docker Compose for Development

```yaml
version: '3.8'

services:
  api:
    build:
      context: .
      dockerfile: Dockerfile
      target: builder  # Use build stage for dev
    volumes:
      - .:/app
      - /app/node_modules  # Prevent overwrite
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/app
    depends_on:
      db:
        condition: service_healthy
    command: ["uvicorn", "src.main:app", "--reload", "--host", "0.0.0.0"]

  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
      POSTGRES_DB: app
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U user -d app"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
```

## Production Checklist

- [ ] Multi-stage build implemented
- [ ] Running as non-root user
- [ ] Base image pinned to digest
- [ ] No secrets in image layers
- [ ] .dockerignore configured
- [ ] Health check defined
- [ ] Resource limits set (in orchestrator)
- [ ] Vulnerability scan passed
- [ ] Labels for metadata
- [ ] Logging to stdout/stderr

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy backend code from repo root context
# Note: Railway builds from repo root, so we copy from backend/
COPY backend/pyproject.toml backend/alembic.ini ./
COPY backend/alembic ./alembic
COPY backend/src ./src

# Install Python dependencies
RUN pip install --no-cache-dir -e .

# Expose port
EXPOSE 8000

# Run migrations, start ARQ worker in background, and start API server
CMD ["sh", "-c", "alembic upgrade head && arq src.tasks.worker.WorkerSettings & uvicorn src.main:app --host 0.0.0.0 --port ${PORT:-8000}"]

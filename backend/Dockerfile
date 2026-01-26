FROM python:3.11-slim

# Force rebuild - version 2
ARG CACHE_BUST=2

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy all application code (needed for editable install)
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -e .

# Expose port
EXPOSE 8000

# Run migrations and start server with verbose output
CMD ["sh", "-c", "echo 'Starting migrations...' && alembic upgrade head && echo 'Migrations complete, starting server...' && uvicorn src.main:app --host 0.0.0.0 --port ${PORT:-8000}"]

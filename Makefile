.PHONY: help setup start stop restart logs backend frontend install-backend install-frontend db-migrate pull-model clean

# Default target
help:
	@echo "Resume Crafter - Available Commands:"
	@echo ""
	@echo "  make setup       - First-time setup (install deps, create .env, pull model)"
	@echo "  make start       - Start all services (Docker + Backend + Frontend)"
	@echo "  make stop        - Stop all services"
	@echo "  make restart     - Restart all services"
	@echo "  make logs        - View Docker container logs"
	@echo ""
	@echo "Individual services:"
	@echo "  make docker      - Start Docker services only"
	@echo "  make backend     - Start backend server only"
	@echo "  make frontend    - Start frontend server only"
	@echo "  make pull-model  - Pull Ollama Gemma model"
	@echo "  make db-migrate  - Run database migrations"
	@echo ""

# First-time setup
setup: install-backend install-frontend
	@echo "Creating backend .env file..."
	@cp -n backend/.env.example backend/.env 2>/dev/null || true
	@echo "Creating frontend .env.local file..."
	@cp -n frontend/.env.local.example frontend/.env.local 2>/dev/null || true
	@echo "Starting Docker services..."
	@docker-compose up -d
	@echo "Waiting for services to be ready..."
	@sleep 5
	@echo "Pulling Ollama model (this may take a few minutes)..."
	@docker exec resume-crafter-ollama ollama pull gemma3:4b || echo "Note: Run 'make pull-model' after Ollama container is ready"
	@echo "Running database migrations..."
	@cd backend && python -m alembic upgrade head
	@echo ""
	@echo "Setup complete! Run 'make start' to start the application."

# Install backend dependencies
install-backend:
	@echo "Installing backend dependencies..."
	@cd backend && pip install -e ".[dev]"

# Install frontend dependencies
install-frontend:
	@echo "Installing frontend dependencies..."
	@cd frontend && npm install

# Start Docker services
docker:
	@docker-compose up -d
	@echo "Docker services started. Waiting for health checks..."
	@sleep 3
	@docker-compose ps

# Pull Ollama model
pull-model:
	@echo "Pulling Gemma 3 4B model..."
	@docker exec resume-crafter-ollama ollama pull gemma3:4b

# Run database migrations
db-migrate:
	@cd backend && python -m alembic upgrade head

# Start backend only
backend:
	@cd backend && uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# Start frontend only
frontend:
	@cd frontend && npm run dev

# Start all services (run in foreground with all logs)
start: docker
	@echo ""
	@echo "Starting backend and frontend..."
	@echo "Backend: http://localhost:8000"
	@echo "Frontend: http://localhost:3000"
	@echo "API Docs: http://localhost:8000/docs"
	@echo ""
	@echo "Press Ctrl+C to stop"
	@trap 'make stop' INT; \
	(cd backend && uvicorn src.main:app --reload --host 0.0.0.0 --port 8000 &); \
	(cd frontend && npm run dev)

# Stop all services
stop:
	@echo "Stopping all services..."
	@-pkill -f "uvicorn src.main:app" 2>/dev/null || true
	@-pkill -f "next dev" 2>/dev/null || true
	@docker-compose down
	@echo "All services stopped."

# Restart all services
restart: stop start

# View Docker logs
logs:
	@docker-compose logs -f

# Clean up everything
clean: stop
	@echo "Cleaning up..."
	@docker-compose down -v
	@rm -rf backend/.venv frontend/node_modules frontend/.next
	@echo "Cleaned up all volumes and dependencies."

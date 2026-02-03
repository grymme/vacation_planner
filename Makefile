.PHONY: help install dev build test migrate run lint down logs frontend-install frontend-build frontend-dev

help:
	@echo "Available commands:"
	@echo ""
	@echo "  install          - Install all dependencies (backend + frontend)"
	@echo "  dev              - Start development servers"
	@echo "  build            - Build backend and frontend"
	@echo "  test             - Run backend tests"
	@echo "  migrate          - Run database migrations"
	@echo "  run              - Start production containers"
	@echo "  lint             - Lint backend and frontend"
	@echo "  down             - Stop containers"
	@echo "  logs             - Follow container logs"
	@echo "  frontend-install - Install frontend dependencies"
	@echo "  frontend-build   - Build frontend for production"
	@echo "  frontend-dev     - Start frontend dev server"

install:
	@echo "Installing backend dependencies..."
	cd backend && pip install -r requirements.txt
	@echo "Installing frontend dependencies..."
	cd frontend && npm install

dev:
	@echo "Starting development servers..."
	docker-compose up -d
	@echo ""
	@echo "Development servers started:"
	@echo "  - Frontend: http://localhost:3000"
	@echo "  - Backend:  http://localhost:8000/docs"
	@echo "  - Health:   http://localhost:8000/health"

build:
	@echo "Building backend..."
	cd backend && python -m build
	@echo "Building frontend..."
	cd frontend && npm run build

test:
	@echo "Running backend tests..."
	cd backend && python -m pytest tests/ -v --tb=short

test-coverage:
	@echo "Running tests with coverage..."
	cd backend && python -m pytest tests/ --cov=app --cov-report=html --cov-report=term-missing -v

test-ci:
	@echo "Running CI tests..."
	cd backend && python -m pytest tests/ --cov=app --cov-report=xml --cov-report=term -v

test-unit:
	@echo "Running unit tests..."
	cd backend && python -m pytest tests/ -v --tb=short -k "not integration"

migrate:
	@echo "Running database migrations..."
	cd backend && alembic upgrade head

run:
	@echo "Starting application..."
	docker-compose up -d --build

lint:
	@echo "Linting backend..."
	cd backend && ruff check .
	@echo "Linting frontend..."
	cd frontend && npx eslint src/ --ext ts,tsx

down:
	@echo "Stopping containers..."
	docker-compose down

logs:
	@echo "Following logs..."
	docker-compose logs -f

frontend-install:
	@echo "Installing frontend dependencies..."
	cd frontend && npm install

frontend-build:
	@echo "Building frontend..."
	cd frontend && npm run build

frontend-dev:
	@echo "Starting frontend dev server..."
	cd frontend && npm run dev

# Database commands
db-backup:
	@echo "Backing up database..."
	docker-compose exec db pg_dump -U vacation_user vacation_planner > backup_$$(date +%Y%m%d_%H%M%S).sql

db-restore:
	@echo "Restoring database..."
	@read -p "Enter backup file: " FILE; \
	docker-compose exec -T db psql -U vacation_user -d vacation_planner < $$FILE

# Health check
health:
	@echo "Checking service health..."
	curl -s http://localhost:8000/health | jq .
	@echo ""
	@echo "Container status:"
	docker-compose ps

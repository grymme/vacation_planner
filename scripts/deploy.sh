#!/bin/bash
set -e

DOMAIN=${1:-"semester.local"}
PROFILE=${2:-"lan"}

# Detect project root (either current dir or parent of scripts/)
if [ -f "docker-compose.yml" ]; then
    PROJECT_ROOT=$(pwd)
    COMPOSE_FILE="docker-compose.yml"
elif [ -f "infra/docker-compose.yml" ]; then
    PROJECT_ROOT=$(pwd)
    COMPOSE_FILE="infra/docker-compose.yml"
else
    # Try parent of scripts directory
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    if [ -f "$SCRIPT_DIR/../infra/docker-compose.yml" ]; then
        PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
        COMPOSE_FILE="infra/docker-compose.yml"
    else
        echo "Error: docker-compose.yml not found"
        exit 1
    fi
fi

cd "$PROJECT_ROOT"

echo "=========================================="
echo "Vacation Planner Deployment"
echo "Domain: $DOMAIN | Profile: $PROFILE"
echo "Project root: $PROJECT_ROOT"
echo "Compose file: $COMPOSE_FILE"
echo "=========================================="

# Step 1: Build containers
echo "[1/4] Building Docker containers..."
docker-compose -f "$COMPOSE_FILE" build

# Step 2: Start services
echo "[2/4] Starting services..."
docker-compose -f "$COMPOSE_FILE" --profile "$PROFILE" up -d

# Step 3: Wait for backend
echo "[3/4] Waiting for backend to be ready..."
sleep 5
for i in {1..30}; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo "Backend is ready!"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "Warning: Backend health check timed out"
    fi
    sleep 1
done

# Step 4: Initialize database
echo "[4/4] Initializing database..."
docker-compose -f "$COMPOSE_FILE" exec -T backend alembic upgrade head 2>/dev/null || echo "Migrations may already be applied"
docker-compose -f "$COMPOSE_FILE" exec -T backend python scripts/seed_admin.py 2>/dev/null || echo "Admin user may already exist"

echo ""
echo "=========================================="
echo "Deployment Complete!"
echo "=========================================="
echo ""
echo "Access your application at:"
echo "  - Frontend: http://$DOMAIN"
echo "  - API:      http://$DOMAIN:8000"
echo "  - Docs:     http://$DOMAIN:8000/docs"
echo ""
echo "Default admin credentials:"
echo "  Email:    admin@vacation.local"
echo "  Password: Admin123!@#"
echo ""
echo "IMPORTANT: Change the admin password after first login!"
echo ""
echo "Useful commands:"
echo "  View logs:  docker-compose -f $COMPOSE_FILE logs -f"
echo "  Restart:    docker-compose -f $COMPOSE_FILE restart"
echo "  Stop:       docker-compose -f $COMPOSE_FILE down"
echo "=========================================="

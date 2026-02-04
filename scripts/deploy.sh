#!/bin/bash
set -e

# Configuration
DOMAIN=${1:-"semester.local"}
PROFILE=${2:-"lan"}

echo "=========================================="
echo "Vacation Planner Deployment"
echo "Domain: $DOMAIN | Profile: $PROFILE"
echo "=========================================="

# Detect project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

echo "Project root: $PROJECT_ROOT"

# Check Docker is running and accessible
if ! docker info > /dev/null 2>&1; then
    echo "Error: Docker is not running or you don't have permission to access it."
    echo ""
    echo "Solutions:"
    echo "  1. Run with sudo: sudo $0 $DOMAIN $PROFILE"
    echo "  2. Or add your user to the docker group:"
    echo "     sudo usermod -aG docker \$USER"
    echo "     Then log out and back in."
    exit 1
fi

# Check compose files
BASE_COMPOSE="infra/docker-compose.yml"
LAN_COMPOSE="infra/docker-compose.lan.yml"
PUBLIC_COMPOSE="infra/docker-compose.public.yml"

if [ ! -f "$BASE_COMPOSE" ]; then
    echo "Error: $BASE_COMPOSE not found"
    exit 1
fi

# Step 1: Create data directory
echo "[1/5] Creating data directory..."
mkdir -p infra/data
chmod 755 infra/data

# Step 2: Generate .env if not exists
echo "[2/5] Configuring environment..."
if [ ! -f ".env" ]; then
    echo "Creating .env from example..."
    cp .env.example .env
    
    # Generate secure secrets
    JWT_SECRET=$(openssl rand -base64 32 2>/dev/null || openssl rand -base64 32)
    
    # Update .env with deployment settings
    sed -i "s|JWT_SECRET=.*|JWT_SECRET=$JWT_SECRET|" .env 2>/dev/null || sed -i '' "s|JWT_SECRET=.*|JWT_SECRET=$JWT_SECRET|" .env
    sed -i "s|DATABASE_URL=.*|DATABASE_URL=sqlite+aiosqlite:///./data/vacation.db|" .env 2>/dev/null || sed -i '' "s|DATABASE_URL=.*|DATABASE_URL=sqlite+aiosqlite:///./data/vacation.db|" .env
    sed -i "s|CORS_ORIGINS=.*|CORS_ORIGINS=http://$DOMAIN,http://localhost,http://127.0.0.1|" .env 2>/dev/null || sed -i '' "s|CORS_ORIGINS=.*|CORS_ORIGINS=http://$DOMAIN,http://localhost,http://127.0.0.1|" .env
    sed -i "s|HTTPS_MODE=.*|HTTPS_MODE=$PROFILE|" .env 2>/dev/null || sed -i '' "s|HTTPS_MODE=.*|HTTPS_MODE=$PROFILE|" .env
    sed -i "s|CADDY_DOMAIN=.*|CADDY_DOMAIN=$DOMAIN|" .env 2>/dev/null || sed -i '' "s|CADDY_DOMAIN=.*|CADDY_DOMAIN=$DOMAIN|" .env
    
    echo ".env created with secure defaults"
else
    echo ".env already exists, skipping..."
fi

# Step 3: Build and run based on profile
echo "[3/5] Starting services..."

if [ "$PROFILE" = "lan" ]; then
    # LAN mode: Use base + LAN compose (backend + frontend only, expose ports)
    echo "Starting in LAN mode..."
    docker-compose -f "$BASE_COMPOSE" -f "$LAN_COMPOSE" build
    docker-compose -f "$BASE_COMPOSE" -f "$LAN_COMPOSE" up -d
else
    # Public mode: Use base compose only (includes Caddy for TLS)
    echo "Starting in Public mode..."
    docker-compose -f "$BASE_COMPOSE" build
    docker-compose -f "$BASE_COMPOSE" up -d
fi

# Step 4: Wait for backend
echo "[4/5] Waiting for backend to be ready..."
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

# Step 5: Initialize database
echo "[5/5] Initializing database..."
docker-compose -f "$BASE_COMPOSE" exec -T backend alembic upgrade head 2>/dev/null || echo "Migrations may already be applied"
docker-compose -f "$BASE_COMPOSE" exec -T backend python scripts/seed_admin.py 2>/dev/null || echo "Admin user may already exist"

echo ""
echo "=========================================="
echo "Deployment Complete!"
echo "=========================================="
echo ""
echo "Access your application at:"
if [ "$PROFILE" = "lan" ]; then
    echo "  - Frontend: http://$DOMAIN:3000"
    echo "  - API:      http://$DOMAIN:8000"
    echo "  - Docs:     http://$DOMAIN:8000/docs"
else
    echo "  - Frontend: https://$DOMAIN"
    echo "  - API:      https://$DOMAIN/api/v1"
    echo "  - Docs:     https://$DOMAIN/docs"
fi
echo ""
echo "Default admin credentials:"
echo "  Email:    admin@vacation.local"
echo "  Password: Admin123!@#"
echo ""
echo "IMPORTANT: Change the admin password after first login!"
echo ""
echo "Useful commands:"
echo "  View logs:  docker-compose -f $BASE_COMPOSE logs -f"
echo "  Restart:    docker-compose -f $BASE_COMPOSE restart"
echo "  Stop:       docker-compose -f $BASE_COMPOSE down"
echo "=========================================="

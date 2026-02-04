#!/bin/bash
set -e

# Configuration
DOMAIN=${1:-"semester.local"}
PROFILE=${2:-"lan"}

echo "=========================================="
echo "Vacation Planner Deployment"
echo "Domain: $DOMAIN | Profile: $PROFILE"
echo "=========================================="

# Check if in project root
if [ ! -f "docker-compose.yml" ]; then
    echo "Error: docker-compose.yml not found. Run this from the project root."
    exit 1
fi

# Step 1: Create data directory
echo "[1/6] Creating data directory..."
mkdir -p backend/data
chmod 755 backend/data

# Step 2: Generate .env if not exists
echo "[2/6] Configuring environment..."
if [ ! -f ".env" ]; then
    echo "Creating .env from example..."
    cp .env.example .env
    
    # Generate secure secrets
    JWT_SECRET=$(openssl rand -base64 32)
    
    # Update .env with deployment settings
    sed -i "s|JWT_SECRET_KEY=.*|JWT_SECRET_KEY=$JWT_SECRET|" .env
    sed -i "s|DATABASE_URL=.*|DATABASE_URL=sqlite+aiosqlite:///./data/vacation.db|" .env
    sed -i "s|CORS_ORIGINS=.*|CORS_ORIGINS=http://$DOMAIN,http://localhost,http://127.0.0.1|" .env
    sed -i "s|HTTPS_MODE=.*|HTTPS_MODE=$PROFILE|" .env
    sed -i "s|CADDY_DOMAIN=.*|CADDY_DOMAIN=$DOMAIN|" .env
    
    echo ".env created with secure defaults"
else
    echo ".env already exists, skipping..."
fi

# Step 3: Build containers
echo "[3/6] Building Docker containers..."
docker compose build

# Step 4: Start services
echo "[4/6] Starting services..."
docker compose --profile "$PROFILE" up -d

# Step 5: Wait for backend
echo "[5/6] Waiting for backend to be ready..."
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

# Step 6: Initialize database
echo "[6/6] Initializing database..."
docker compose exec -T backend alembic upgrade head 2>/dev/null || echo "Migrations may already be applied"
docker compose exec -T backend python scripts/seed_admin.py 2>/dev/null || echo "Admin user may already exist"

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
echo "  View logs:  docker compose logs -f"
echo "  Restart:    docker compose restart"
echo "  Stop:       docker compose down"
echo "=========================================="

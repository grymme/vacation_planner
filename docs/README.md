# Vacation Planner - Setup Guide

A production-grade vacation planning application deployed on Raspberry Pi 5 with PostgreSQL, FastAPI, React, and Caddy reverse proxy with automatic TLS.

## Table of Contents

1. [Hardware Requirements](#hardware-requirements)
2. [Software Prerequisites](#software-prerequisites)
3. [Installation](#installation)
4. [Configuration](#configuration)
5. [First Run](#first-run)
6. [Public DNS Setup](#public-dns-setup)
7. [Let’s Encrypt Configuration](#lets-encrypt-configuration)
8. [LAN Mode (Internal Certificates)](#lan-mode-internal-certificates)
9. [First-Time Admin User](#first-time-admin-user)
10. [Troubleshooting](#troubleshooting)
11. [Backup and Restore](#backup-and-restore)

## Hardware Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| Raspberry Pi 5 | 4GB RAM | 8GB RAM |
| Storage | 32GB SD Card | 64GB+ SSD via USB |
| Network | Ethernet | Ethernet (stable connection) |

## Software Prerequisites

### Raspberry Pi OS (64-bit)

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -sSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo apt install -y docker-compose

# Verify installation
docker --version
docker-compose --version
```

## Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd vacation_planner
```

### 2. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit with your settings
nano .env
```

### 3. Start Services

```bash
# Build and start containers
make run

# Or manually
docker-compose up -d --build
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql+asyncpg://vacation_user:password@db:5432/vacation_planner` |
| `JWT_SECRET` | Secret key for JWT tokens | Change in production! |
| `DOMAIN` | Your domain name | `vacation.example.com` |
| `HTTPS_MODE` | `public` or `lan` | `lan` |
| `ADMIN_EMAIL` | Initial admin email | `admin@example.com` |
| `ADMIN_PASSWORD` | Initial admin password | Change immediately! |

### Database Tuning (Raspberry Pi 5)

The PostgreSQL container is configured with Raspberry Pi 5 optimized settings:

```yaml
# docker-compose.yml (already configured)
command: >
  postgres
  -c shared_buffers=256MB
  -c max_connections=100
  -c effective_cache_size=512MB
  -c work_mem=16MB
  -c maintenance_work_mem=128MB
```

## First Run

### 1. Verify Services are Running

```bash
# Check container status
docker-compose ps

# Check health
make health
```

### 2. Access the Application

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| API Docs | http://localhost:8000/docs |
| Health Check | http://localhost:8000/health |

## Public DNS Setup

For Let’s Encrypt TLS certificates, you need a public domain:

### Option 1: Dynamic DNS

1. Register a domain with a DNS provider
2. Configure Dynamic DNS to point to your home IP
3. Open port 80 and 443 on your router

### Option 2: Static IP

1. Obtain a static IP from your ISP
2. Point your domain A records to that IP
3. Open ports 80 and 443

### Port Forwarding

Configure your router to forward:
- TCP 80 → Raspberry Pi
- TCP 443 → Raspberry Pi

## Let’s Encrypt Configuration

### Enable Public Mode

```bash
# Edit .env
HTTPS_MODE=public
DOMAIN=your-domain.com
EMAIL=your-email@example.com

# Restart services
docker-compose down
docker-compose up -d
```

Caddy will automatically:
1. Obtain TLS certificates from Let’s Encrypt
2. Configure HTTP to HTTPS redirect
3. Set up security headers

### Verify TLS

```bash
# Check certificate
openssl s_client -connect your-domain.com:443 -servername your-domain.com
```

## LAN Mode (Internal Certificates)

For internal use without public access:

```bash
# Edit .env
HTTPS_MODE=lan
DOMAIN=vacation.local

# Restart services
docker-compose down
docker-compose up -d
```

Caddy will generate self-signed certificates automatically.

### Trust Self-Signed Certificate (Optional)

```bash
# Copy certificate to trusted store
docker-compose exec caddy cat /data/caddy/pki/authorities/local/root.crt | \
    sudo tee /usr/local/share/ca-certificates/vacation.crt

# Update CA store
sudo update-ca-certificates
```

## First-Time Admin User

The admin user is automatically created on first run using environment variables:

```env
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=changeme-in-production!
```

### Change Admin Password

1. Log in to the application
2. Navigate to Profile → Change Password
3. Or use API:

```bash
curl -X PUT http://localhost:8000/users/me \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"password": "new-secure-password"}'
```

## Troubleshooting

### Containers Not Starting

```bash
# Check logs
docker-compose logs

# Common issues:
# 1. Port already in use
# 2. Insufficient memory
# 3. Docker daemon not running
```

### Database Connection Failed

```bash
# Check database container
docker-compose logs db

# Verify connection
docker-compose exec db pg_isready -U vacation_user
```

### Certificate Issues (Let’s Encrypt)

```bash
# Check Caddy logs
docker-compose logs caddy

# Common issues:
# 1. Domain not resolving
# 2. Ports not forwarded
# 3. Rate limiting (5 certs per hour)
```

### Performance Issues

```bash
# Check resource usage
docker stats

# Increase memory for PostgreSQL
# Edit docker-compose.yml environment variables
```

### Reset Everything

```bash
# Stop and remove containers
docker-compose down -v

# Remove volumes
docker volume rm vacation_planner_postgres_data
docker volume rm vacation_planner_caddy_data

# Rebuild and restart
docker-compose up -d --build
```

## Backup and Restore

### Backup Database

```bash
# Using make
make db-backup

# Manual
docker-compose exec -T db pg_dump -U vacation_user vacation_planner > backup.sql
```

### Restore Database

```bash
# Using make
make db-restore

# Manual
docker-compose exec -T db psql -U vacation_user -d vacation_planner < backup.sql
```

### Automated Backups (Cron)

```bash
# Add to crontab
crontab -e

# Daily backup at 2 AM
0 2 * * * cd /path/to/vacation_planner && make db-backup > /dev/null 2>&1
```

### Backup Files

```bash
# Backup .env file
cp .env .env.backup

# Backup uploaded files (if any)
docker cp vacation_planner-backend:/app/uploads ./backups/
```

## Security Considerations

1. **Change all default passwords immediately**
2. **Use strong JWT secrets**
3. **Keep Docker images updated**
4. **Enable firewall**: `sudo ufw allow 80,443/tcp`
5. **Monitor logs regularly**
6. **Use HTTPS in production**

## Additional Resources

- [API Documentation](http://localhost:8000/docs)
- [Architecture Overview](ARCHITECTURE.md)
- [Security Policy](SECURITY.md)

# Vacation Planner

A production-grade vacation planning application with role-based access control (RBAC), built for deployment on Raspberry Pi 5. Features JWT authentication, Argon2id password hashing, and automatic TLS via Caddy.

## Features

- **Authentication**: JWT-based auth with HTTP-only cookies and Argon2id password hashing
- **Role-Based Access Control**: Admin, Manager, and User roles with company isolation
- **Vacation Management**: Submit, approve with workflow, reject vacation requests
- **Calendar View**: Interactive calendar for vacation visualization (FullCalendar)
- **Export Capabilities**: Export vacation data to CSV/Excel
- **Automatic TLS**: Caddy reverse proxy with Let's Encrypt integration
- **PostgreSQL**: Production-ready database with async support
- **Security**: Rate limiting, security headers, comprehensive audit logging

## Tech Stack

### Backend

| Technology | Purpose |
|------------|---------|
| FastAPI | Modern Python web framework with async support |
| SQLAlchemy 2.0 | Async database ORM with migrations (Alembic) |
| PostgreSQL 15 | Robust relational database |
| JWT | Token-based authentication |
| Argon2id | Memory-hard password hashing (Pi 5 optimized) |
| Pydantic | Data validation and serialization |

### Frontend

| Technology | Purpose |
|------------|---------|
| React 18 | UI library with hooks |
| Vite | Fast build tool |
| TypeScript | Type-safe code |
| FullCalendar | Interactive calendar component |
| Axios | HTTP client |

### Infrastructure

| Technology | Purpose |
|------------|---------|
| Docker | Containerization |
| Docker Compose | Multi-container orchestration |
| Caddy 2.7 | Reverse proxy with automatic TLS |
| Raspberry Pi 5 | ARM64 deployment target |

## Quick Start

### Prerequisites

- Raspberry Pi 5 (4GB+ RAM recommended)
- Docker & Docker Compose v2
- 32GB+ storage (industrial-grade SD card recommended)
- Domain name (for public deployment with TLS)

### Installation

```bash
# Clone repository
git clone <repository-url>
cd vacation_planner

# Install dependencies
make install

# Configure environment
cp .env.example .env
# Edit .env with your settings

# Start services
make run

# Access application
# Frontend: http://localhost:3000
# API Docs: http://localhost:8000/docs
```

### Production Deployment

```bash
# Build and start with all services
docker-compose --profile public up -d

# Or for LAN-only (no TLS)
docker-compose --profile lan up -d
```

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `POSTGRES_USER` | Yes | `vacation` | Database username |
| `POSTGRES_PASSWORD` | Yes | - | Database password (strong!) |
| `POSTGRES_DB` | Yes | `vacation_planner` | Database name |
| `JWT_SECRET` | Yes | - | Secret for JWT signing (32+ chars) |
| `JWT_ALGORITHM` | No | `HS256` | JWT algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | `15` | Access token lifetime |
| `REFRESH_TOKEN_EXPIRE_DAYS` | No | `7` | Refresh token lifetime |
| `ADMIN_EMAIL` | No | `admin@example.com` | Initial admin email |
| `ADMIN_PASSWORD` | Yes | - | Initial admin password |
| `ADMIN_FIRST_NAME` | No | `Admin` | Admin first name |
| `ADMIN_LAST_NAME` | No | `User` | Admin last name |
| `CORS_ORIGINS` | No | See `.env.example` | Allowed CORS origins |
| `ENVIRONMENT` | No | `production` | `development` or `production` |
| `CADDY_DOMAIN` | Public | `localhost` | Domain for TLS |
| `CADDY_TLS_EMAIL` | Public | - | Email for Let's Encrypt |
| `HTTPS_MODE` | No | `lan` | `lan` or `public` |

### Security Hardening

Before production deployment:

1. **Change all default passwords**
2. **Set strong JWT_SECRET** (minimum 32 random characters)
3. **Configure CORS_ORIGINS** with your domain
4. **Enable HTTPS** (set `HTTPS_MODE=public`)
5. **Set up automated backups** (see [Backup Procedures](docs/BACKUP.md))

## Project Structure

```
vacation_planner/
├── infra/                     # Docker infrastructure
│   ├── docker-compose.yml     # Container orchestration
│   ├── Caddyfile             # Reverse proxy config
│   └── Dockerfile.*          # Container builds
├── backend/                   # FastAPI application
│   ├── app/
│   │   ├── main.py          # Application entry point
│   │   ├── config.py        # Settings management
│   │   ├── database.py      # DB connection & async utilities
│   │   ├── models.py        # SQLAlchemy ORM models
│   │   ├── schemas.py       # Pydantic schemas
│   │   ├── auth.py          # JWT & password handling
│   │   ├── audit.py         # Audit logging
│   │   ├── middleware/       # Custom middleware
│   │   │   └── rate_limit.py # Rate limiting
│   │   └── routers/         # API endpoints
│   │       ├── auth.py      # Authentication
│   │       ├── users.py     # User management
│   │       ├── vacation_requests.py
│   │       ├── admin.py     # Admin operations
│   │       ├── manager.py   # Manager operations
│   │       └── exports.py   # Data export
│   ├── requirements.txt
│   ├── alembic.ini
│   └── tests/
├── frontend/                 # React application
│   ├── src/
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   ├── components/
│   │   ├── pages/
│   │   ├── context/         # Auth context
│   │   └── api/            # API client
│   ├── package.json
│   └── vite.config.ts
├── docs/                     # Documentation
│   ├── README.md
│   ├── SECURITY.md          # Security hardening guide
│   └── BACKUP.md            # Backup procedures
├── scripts/                  # Utility scripts
├── .env.example
├── .gitignore
├── Makefile
└── README.md
```

## API Documentation

### Authentication Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/auth/register` | Register new user |
| POST | `/api/v1/auth/login` | Login (sets HTTP-only cookies) |
| POST | `/api/v1/auth/refresh` | Refresh access token |
| POST | `/api/v1/auth/logout` | Logout (clears cookies) |
| GET | `/api/v1/auth/me` | Get current user |

### Vacation Request Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/vacation/` | List user's requests |
| POST | `/api/v1/vacation/` | Submit new request |
| GET | `/api/v1/vacation/{id}` | Get request details |
| DELETE | `/api/v1/vacation/{id}` | Cancel own request |

### Manager Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/manager/team` | List team members |
| GET | `/api/v1/manager/requests` | Pending approvals |
| POST | `/api/v1/manager/requests/{id}/approve` | Approve request |
| POST | `/api/v1/manager/requests/{id}/reject` | Reject request |

### Admin Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/admin/users` | List all users |
| POST | `/api/v1/admin/users` | Create user |
| PUT | `/api/v1/admin/users/{id}` | Update user |
| DELETE | `/api/v1/admin/users/{id}` | Delete user |
| GET | `/api/v1/admin/audit` | View audit logs |

## Security

See [Security Documentation](docs/SECURITY.md) for:

- Threat model and assets protected
- Security controls implemented
- Hardening checklist for production
- Incident response procedures

### Authentication Security

- **Password Hashing**: Argon2id with Pi 5 optimized parameters
  - `time_cost`: 2
  - `memory_cost`: 65536 KB (64 MB)
  - `parallelism`: 4
- **Token Security**:
  - Access tokens: 15-minute expiry (stored in memory)
  - Refresh tokens: 7-day expiry (HTTP-only secure cookies)

### Rate Limiting

| Endpoint Type | Limit | Window |
|---------------|-------|--------|
| Auth endpoints | 5 requests | per minute |
| API endpoints | 100 requests | per minute |
| Export endpoints | 10 requests | per minute |

### Security Headers

All responses include:

- `Strict-Transport-Security` (HSTS)
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: SAMEORIGIN`
- `Content-Security-Policy`
- `Referrer-Policy`
- `Permissions-Policy`

## Backup & Recovery

See [Backup Documentation](docs/BACKUP.md) for:

- Backup components and strategy
- Automated backup scripts
- Restore procedures
- Retention policies
- Disaster recovery checklist

### Quick Backup

```bash
# Run backup script
./scripts/backup.sh

# Backups stored in /home/pi/backups/vacation-planner/
```

### Quick Restore

```bash
# Restore from backup
./scripts/restore.sh vacation_planner_20250115_020000.sql.gz.enc
```

## Monitoring & Maintenance

### Health Checks

The application exposes health check endpoints:

- `GET /health` - Backend health (includes database status)
- `GET http://localhost/health` - Caddy proxy status

### Logs

```bash
# View all logs
docker-compose logs -f

# View specific service
docker-compose logs -f backend

# View with timestamps
docker-compose logs -f -t
```

### Resource Monitoring

```bash
# Docker stats
docker stats --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}"

# Disk usage
df -h /home/pi

# SD card health
sudo smartctl -a /dev/mmcblk0
```

### Updates

```bash
# Pull latest images
docker-compose pull

# Restart with new images
docker-compose up -d

# Prune old images
docker image prune -f
```

## Troubleshooting

### Common Issues

#### Database Connection Failed

```bash
# Check database status
docker-compose logs db

# Restart database
docker-compose restart db
```

#### JWT Token Errors

```bash
# Verify JWT_SECRET is set
cat .env | grep JWT_SECRET

# Restart backend after setting
docker-compose restart backend
```

#### Caddy TLS Errors

```bash
# Check Caddy logs
docker-compose logs caddy

# Verify domain DNS
dig your-domain.com

# Check port 443 is open
sudo ufw status
```

### Performance Tuning

#### PostgreSQL Optimization

The default configuration is tuned for Raspberry Pi 5:

- `shared_buffers`: 256MB
- `max_connections`: 100
- `effective_cache_size`: 512MB
- `work_mem`: 16MB

Adjust based on available RAM.

#### Database Maintenance

```bash
# Analyze tables (update statistics)
docker exec vacation-planner-db psql -U vacation -d vacation_planner -c "ANALYZE;"

# Vacuum analyze (reclaim space)
docker exec vacation-planner-db psql -U vacation -d vacation_planner -c "VACUUM ANALYZE;"
```

## Available Commands

| Command | Description |
|---------|-------------|
| `make install` | Install all dependencies |
| `make dev` | Start development servers |
| `make build` | Build for production |
| `make test` | Run tests |
| `make migrate` | Run database migrations |
| `make run` | Start production containers |
| `make down` | Stop containers |
| `make logs` | View logs |
| `make restart` | Restart containers |
| `make backup` | Create backup |
| `make restore` | Restore from backup |

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed system design documentation.

## License

MIT

## Support

For issues and feature requests, please open a GitHub issue.

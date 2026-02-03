# Vacation Planner

A production-grade vacation planning application with role-based access control (RBAC), built for deployment on Raspberry Pi 5.

## Features

- **Authentication**: JWT-based auth with HTTP-only cookies and Argon2id password hashing
- **Role-Based Access Control**: Admin, Manager, and User roles
- **Vacation Management**: Submit, approve, reject vacation requests
- **Calendar View**: Interactive calendar for vacation visualization
- **Automatic TLS**: Caddy reverse proxy with Let’s Encrypt integration
- **PostgreSQL**: Production-ready database configuration

## Tech Stack

### Backend
- **FastAPI**: Modern Python web framework with async support
- **SQLAlchemy 2.0**: Async database ORM with migrations (Alembic)
- **PostgreSQL**: Robust relational database
- **JWT**: Token-based authentication
- **Argon2id**: Memory-hard password hashing

### Frontend
- **React 18**: UI library with hooks
- **Vite**: Fast build tool
- **TypeScript**: Type-safe code
- **FullCalendar**: Interactive calendar component
- **Axios**: HTTP client

### Infrastructure
- **Docker**: Containerization
- **Docker Compose**: Multi-container orchestration
- **Caddy**: Reverse proxy with automatic TLS
- **arm64**: Optimized for Raspberry Pi 5

## Quick Start

### Prerequisites

- Raspberry Pi 5 (4GB+ RAM)
- Docker & Docker Compose
- 32GB+ storage

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

## Documentation

- [Setup Guide](docs/README.md) - Complete installation and configuration
- [Architecture](ARCHITECTURE.md) - System design overview
- [Security](docs/SECURITY.md) - Security considerations

## Project Structure

```
vacation_planner/
├── infra/                 # Docker infrastructure
│   ├── docker-compose.yml
│   ├── Caddyfile
│   └── Dockerfile.backend
├── backend/               # FastAPI application
│   ├── app/
│   │   ├── main.py       # Application entry point
│   │   ├── config.py     # Settings
│   │   ├── database.py   # DB connection
│   │   ├── models.py     # SQLAlchemy models
│   │   ├── auth.py       # Auth utilities
│   │   ├── schemas.py    # Pydantic schemas
│   │   └── routers/      # API endpoints
│   ├── requirements.txt
│   ├── alembic.ini
│   └── tests/
├── frontend/              # React application
│   ├── src/
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   └── components/
│   ├── package.json
│   └── vite.config.ts
├── docs/                  # Documentation
│   ├── README.md
│   └── SECURITY.md
├── .env.example
├── .gitignore
├── Makefile
└── README.md
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

## License

MIT

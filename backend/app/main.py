"""FastAPI application entry point."""
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import init_db, close_db
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.csrf import CSRFMiddleware
from app.routers import auth, users, vacation_requests, admin, manager, exports, vacation_periods

# Configure logging
logging.basicConfig(
    level=logging.INFO if settings.environment == "production" else logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan events (startup/shutdown)."""
    # Startup
    logger.info("Starting Vacation Planner application...")
    await init_db()
    logger.info("Database initialized")
    yield
    # Shutdown
    logger.info("Shutting down Vacation Planner application...")
    await close_db()
    logger.info("Database connections closed")


# Create FastAPI application
app = FastAPI(
    title="Vacation Planner API",
    description="A production-grade vacation planning system with RBAC",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.environment == "development" else None,
    redoc_url="/redoc" if settings.environment == "development" else None,
)

# Rate limiting middleware (applied before other middleware)
app.add_middleware(RateLimitMiddleware)

# CSRF protection middleware
app.add_middleware(CSRFMiddleware)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Handle uncaught exceptions."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal error occurred"}
    )


# Include routers with proper prefixes
app.include_router(auth.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(vacation_requests.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")
app.include_router(manager.router, prefix="/api/v1")
app.include_router(exports.router, prefix="/api/v1")
app.include_router(vacation_periods.router, prefix="/api/v1")
app.include_router(vacation_periods.router_allocations, prefix="/api/v1")
app.include_router(vacation_periods.router_balance, prefix="/api/v1")


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint for load balancers and monitoring."""
    from app.database import check_db_connection
    
    db_healthy = await check_db_connection()
    
    return {
        "status": "healthy" if db_healthy else "degraded",
        "database": "connected" if db_healthy else "disconnected",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint."""
    return {
        "name": "Vacation Planner API",
        "version": "1.0.0",
        "docs": "/docs" if settings.environment == "development" else None,
    }


# API v2 endpoint - returns deprecation notice for v2
@app.get("/api/v2", tags=["API v2"])
async def api_v2():
    """API v2 endpoint - returns deprecation notice."""
    return {
        "message": "API v2 is deprecated",
        "detail": "The v2 API endpoints are no longer supported. Please migrate to /api/v1 for all API requests.",
        "deprecated_since": "2024-01-01",
        "migration_guide": "Update your API client to use /api/v1 prefix instead of /api/v2",
    }

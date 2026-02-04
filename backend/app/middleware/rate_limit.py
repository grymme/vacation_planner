"""Rate limiting and account lockout middleware."""
import asyncio
import time
from collections import defaultdict
from typing import Optional

from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


# =============================================================================
# Account Lockout Store (In-Memory)
# =============================================================================
class AccountLockoutStore:
    """In-memory account lockout tracking.
    
    Locks accounts after 5 failed login attempts within 15 minutes.
    Auto-unlocks after 15 minutes.
    """
    
    def __init__(self):
        self._attempts: dict[str, list[float]] = defaultdict(list)
        self._locked: dict[str, bool] = defaultdict(bool)
        self._lockout_duration = 900  # 15 minutes in seconds
        self._max_attempts = 5
        self._window_seconds = 900  # 15 minutes window
    
    async def check_login(self, email: str) -> tuple[bool, str]:
        """Check if login is allowed for the email.
        
        Args:
            email: The user's email address.
            
        Returns:
            Tuple of (is_allowed, error_message).
        """
        now = time.time()
        window_start = now - self._window_seconds
        
        # Clean old attempts outside the window
        self._attempts[email] = [t for t in self._attempts[email] if t > window_start]
        
        # Check if account is locked
        if self._locked[email]:
            remaining = self._lockout_duration - (now - self._attempts[email][-1]) if self._attempts[email] else self._lockout_duration
            return False, f"Account locked due to too many failed attempts. Try again in {int(remaining)} seconds."
        
        # Check if we've reached max attempts
        if len(self._attempts[email]) >= self._max_attempts:
            self._locked[email] = True
            # Schedule unlock after lockout duration
            asyncio.get_event_loop().call_later(
                self._lockout_duration, 
                lambda: self._locked.__setitem__(email, False)
            )
            return False, "Account locked due to too many failed attempts. Try again in 15 minutes."
        
        return True, ""
    
    def record_failure(self, email: str) -> None:
        """Record a failed login attempt.
        
        Args:
            email: The user's email address.
        """
        self._attempts[email].append(time.time())
    
    def record_success(self, email: str) -> None:
        """Clear failed attempts on successful login.
        
        Args:
            email: The user's email address.
        """
        self._attempts[email] = []
    
    def is_locked(self, email: str) -> bool:
        """Check if an account is currently locked.
        
        Args:
            email: The user's email address.
            
        Returns:
            True if the account is locked.
        """
        return self._locked[email]


# Global account lockout store instance
account_lockout_store = AccountLockoutStore()


# =============================================================================
# Rate Limit Middleware
# =============================================================================
class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware for API endpoints."""
    
    # Default rate limits by endpoint type
    DEFAULT_LIMITS = {
        "/api/v1/auth/login": 10,  # 10 login attempts per minute
        "/api/v1/auth/refresh": 20,
        "/api/v1/auth/password-reset-request": 5,
    }
    
    def __init__(self, app):
        super().__init__(app)
        self._request_counts: dict[str, list[float]] = defaultdict(list)
    
    async def dispatch(self, request: Request, call_next):
        """Process the request through rate limiting."""
        # Skip rate limiting for health checks and docs
        if request.url.path in ["/health", "/docs", "/redoc"]:
            return await call_next(request)
        
        # Get rate limit for this endpoint
        limit = self.DEFAULT_LIMITS.get(request.url.path, 60)  # Default 60/minute
        
        # Check rate limit
        now = time.time()
        window = 60  # 1 minute window
        
        # Clean old requests
        self._request_counts[request.client.host] = [
            t for t in self._request_counts[request.client.host] if t > now - window
        ]
        
        # Check if over limit
        if len(self._request_counts[request.client.host]) >= limit:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": "Too many requests. Please try again later."}
            )
        
        # Record this request
        self._request_counts[request.client.host].append(now)
        
        return await call_next(request)

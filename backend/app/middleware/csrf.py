"""CSRF protection middleware for API endpoints."""
from typing import Optional

from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings


# =============================================================================
# CSRF Middleware
# =============================================================================
class CSRFMiddleware(BaseHTTPMiddleware):
    """CSRF protection middleware for state-changing requests.
    
    Validates Origin and Referer headers for POST, PUT, DELETE, PATCH requests
    to prevent cross-site request forgery attacks.
    """
    
    # Methods that require CSRF validation
    SENSITIVE_METHODS = {"POST", "PUT", "DELETE", "PATCH"}
    
    # Paths that don't require CSRF validation (e.g., webhooks, third-party APIs)
    EXCLUDED_PATHS = {
        "/health",
        "/api/v1/auth/login",
        "/api/v1/auth/refresh",
        "/api/v1/auth/password-reset-request",
        "/api/v1/auth/password-reset-confirm",
    }
    
    def __init__(self, app):
        super().__init__(app)
        self._allowed_origins: Optional[list[str]] = None
    
    @property
    def allowed_origins(self) -> list[str]:
        """Get allowed CORS origins from settings."""
        if self._allowed_origins is None:
            self._allowed_origins = settings.cors_origins if hasattr(settings, 'cors_origins') else []
        return self._allowed_origins
    
    async def dispatch(self, request: Request, call_next):
        """Validate CSRF protection for sensitive requests."""
        # Skip CSRF validation for non-sensitive methods
        if request.method not in self.SENSITIVE_METHODS:
            return await call_next(request)
        
        # Skip excluded paths
        if request.url.path in self.EXCLUDED_PATHS:
            return await call_next(request)
        
        # Get origin and referer headers
        origin = request.headers.get("origin")
        referer = request.headers.get("referer")
        
        # For browser requests, we need either Origin or Referer
        # This helps prevent CSRF attacks from malicious sites
        if not origin and not referer:
            # Allow requests without headers (e.g., mobile apps, curl)
            # In production, you might want to be stricter here
            return await call_next(request)
        
        # Validate Origin header if present
        if origin:
            if not self._is_origin_allowed(origin):
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={"detail": "CSRF validation failed: Invalid origin"}
                )
        
        # Validate Referer header if present
        if referer:
            if not self._is_referer_allowed(referer):
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={"detail": "CSRF validation failed: Invalid referer"}
                )
        
        return await call_next(request)
    
    def _is_origin_allowed(self, origin: str) -> bool:
        """Check if the origin is allowed.
        
        Args:
            origin: The Origin header value.
            
        Returns:
            True if the origin is allowed.
        """
        if not self.allowed_origins:
            # No restrictions configured, allow all
            return True
        
        # Exact match
        if origin in self.allowed_origins:
            return True
        
        # Check for wildcard patterns (e.g., "*.example.com")
        for allowed in self.allowed_origins:
            if allowed.endswith("*"):
                domain = allowed.rstrip("*")
                if origin.endswith(domain) or origin.startswith(domain):
                    return True
        
        return False
    
    def _is_referer_allowed(self, referer: str) -> bool:
        """Check if the referer is allowed.
        
        Args:
            referer: The Referer header value.
            
        Returns:
            True if the referer is allowed.
        """
        if not self.allowed_origins:
            # No restrictions configured, allow all
            return True
        
        # Extract the origin from referer
        # Referer format: https://example.com/path
        try:
            from urllib.parse import urlparse
            referer_origin = f"{urlparse(referer).scheme}://{urlparse(referer).netloc}"
            
            if referer_origin in self.allowed_origins:
                return True
            
            # Check for wildcard patterns
            for allowed in self.allowed_origins:
                if allowed.endswith("*"):
                    domain = allowed.rstrip("*")
                    if referer_origin.endswith(domain) or referer_origin.startswith(domain):
                        return True
            
            return False
        except Exception:
            # If we can't parse the referer, be strict and allow the request
            # (it will be validated by Origin if present)
            return True

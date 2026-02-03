"""Authentication utilities with JWT and Argon2id password hashing."""
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID
import logging

from jose import jwt, JWTError
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, InvalidHash
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.models import User, UserRole
from app.database import get_db

logger = logging.getLogger(__name__)

# =============================================================================
# Argon2id Password Hashing (Pi 5 optimized)
# =============================================================================
argon2_hasher = PasswordHasher(
    time_cost=int(os.getenv("ARGON2_TIME_COST", settings.argon2_time_cost)),
    memory_cost=int(os.getenv("ARGON2_MEMORY_COST", settings.argon2_memory_cost)),
    parallelism=int(os.getenv("ARGON2_PARALLELISM", settings.argon2_parallelism)),
    hash_len=32,
    salt_len=16,
)


def hash_password(password: str) -> str:
    """Hash a password using Argon2id.
    
    Args:
        password: The plain text password.
        
    Returns:
        The hashed password.
    """
    return argon2_hasher.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against a hash.
    
    Args:
        password: The plain text password.
        hashed: The hashed password to compare against.
        
    Returns:
        True if the password matches, False otherwise.
    """
    try:
        return argon2_hasher.verify(hashed, password)
    except (VerifyMismatchError, InvalidHash, Exception) as e:
        logger.warning(f"Password verification failed: {e}")
        return False


# =============================================================================
# JWT Token Management
# =============================================================================
def create_access_token(user_id: UUID, email: str, role: UserRole, company_id: UUID) -> str:
    """Create a JWT access token.
    
    Args:
        user_id: The user's UUID.
        email: The user's email.
        role: The user's role.
        company_id: The user's company UUID.
        
    Returns:
        The encoded JWT access token.
    """
    expires = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {
        "sub": str(user_id),
        "email": email,
        "role": role.value,
        "company_id": str(company_id),
        "exp": expires,
        "iat": datetime.now(timezone.utc),
        "type": "access"
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_refresh_token(user_id: UUID) -> str:
    """Create a JWT refresh token.
    
    Args:
        user_id: The user's UUID.
        
    Returns:
        The encoded JWT refresh token.
    """
    expires = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
    payload = {
        "sub": str(user_id),
        "exp": expires,
        "iat": datetime.now(timezone.utc),
        "type": "refresh"
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict:
    """Decode and validate a JWT token.
    
    Args:
        token: The JWT token to decode.
        
    Returns:
        The decoded token payload.
        
    Raises:
        HTTPException: If the token is invalid.
    """
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm]
        )
        return payload
    except JWTError as e:
        logger.warning(f"JWT decode error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )


def verify_refresh_token(refresh_token: str) -> UUID:
    """Verify a refresh token and return the user ID.
    
    Args:
        refresh_token: The refresh token to verify.
        
    Returns:
        The user's UUID.
        
    Raises:
        HTTPException: If the token is invalid.
    """
    payload = decode_token(refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type"
        )
    return UUID(payload["sub"])


# =============================================================================
# Invite Token Management
# =============================================================================
def generate_invite_token() -> str:
    """Generate a secure invite token.
    
    Returns:
        A URL-safe random token.
    """
    return secrets.token_urlsafe(32)


def create_invite_token(db: AsyncSession, user_id: UUID, created_by: Optional[UUID] = None) -> "InviteToken":
    """Create an invite token for a user.
    
    Args:
        db: The database session.
        user_id: The user's UUID.
        created_by: The creator's UUID.
        
    Returns:
        The created InviteToken object.
    """
    from app.models import InviteToken
    
    token_str = generate_invite_token()
    expires = datetime.now(timezone.utc) + timedelta(days=7)  # 7 day expiry
    
    invite = InviteToken(
        token=token_str,
        user_id=user_id,
        expires_at=expires,
        created_by=created_by
    )
    db.add(invite)
    return invite


# =============================================================================
# Password Reset Token Management
# =============================================================================
def generate_password_reset_token() -> str:
    """Generate a secure password reset token.
    
    Returns:
        A URL-safe random token.
    """
    return secrets.token_urlsafe(32)


def create_password_reset_token(db: AsyncSession, user_id: UUID) -> "PasswordResetToken":
    """Create a password reset token for a user.
    
    Args:
        db: The database session.
        user_id: The user's UUID.
        
    Returns:
        The created PasswordResetToken object.
    """
    from app.models import PasswordResetToken
    
    token_str = generate_password_reset_token()
    expires = datetime.now(timezone.utc) + timedelta(hours=1)  # 1 hour expiry
    
    reset = PasswordResetToken(
        token=token_str,
        user_id=user_id,
        expires_at=expires
    )
    db.add(reset)
    return reset


# =============================================================================
# Current User Dependencies
# =============================================================================
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Get the current authenticated user.
    
    Args:
        token: The JWT access token.
        db: The database session.
        
    Returns:
        The authenticated User.
        
    Raises:
        HTTPException: If not authenticated.
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    payload = decode_token(token)
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type"
        )
    
    user_id = UUID(payload["sub"])
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account inactive"
        )
    
    return user


def require_role(*allowed_roles: UserRole):
    """Create a dependency that requires specific roles.
    
    Args:
        allowed_roles: The roles that are allowed.
        
    Returns:
        A dependency function.
    """
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        return current_user
    return role_checker


async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Require admin role.
    
    Args:
        current_user: The current user.
        
    Returns:
        The user if admin.
        
    Raises:
        HTTPException: If not admin.
    """
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


async def require_manager_or_admin(current_user: User = Depends(get_current_user)) -> User:
    """Require manager or admin role.
    
    Args:
        current_user: The current user.
        
    Returns:
        The user if manager or admin.
        
    Raises:
        HTTPException: If not manager or admin.
    """
    if current_user.role not in (UserRole.ADMIN, UserRole.MANAGER):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Manager or admin access required"
        )
    return current_user


# =============================================================================
# Token Creation Helper
# =============================================================================
def create_tokens(user: User) -> tuple[str, str]:
    """Create access and refresh tokens for a user.
    
    Args:
        user: The User model instance.
        
    Returns:
        Tuple of (access_token, refresh_token).
    """
    access_token = create_access_token(
        user_id=user.id,
        email=user.email,
        role=user.role,
        company_id=user.company_id
    )
    refresh_token = create_refresh_token(user_id=user.id)
    return access_token, refresh_token


# =============================================================================
# Error Classes
# =============================================================================
class AuthError(Exception):
    """Authentication error exception."""
    def __init__(self, message: str, status_code: int = 401):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


# Re-export for convenience
from app.models import InviteToken, PasswordResetToken

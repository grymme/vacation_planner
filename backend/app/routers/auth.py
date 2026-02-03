"""Authentication router."""
import os
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import User, InviteToken, PasswordResetToken
from app.auth import (
    create_access_token,
    create_refresh_token,
    create_tokens,
    decode_token,
    verify_password,
    hash_password,
    get_current_user,
    require_admin,
)
from app.schemas import (
    Token,
    LoginRequest,
    RefreshTokenRequest,
    SetPasswordRequest,
    PasswordResetRequest,
    PasswordResetConfirmRequest,
    UserResponse,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=Token)
async def login(
    login_data: LoginRequest,
    response: Response,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Login with email and password. Returns access + refresh token (refresh in HTTP-only cookie)."""
    # Find user
    result = await db.execute(select(User).where(User.email == login_data.email))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    if not user.hashed_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account not activated. Please set password via invite link."
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is deactivated"
        )
    
    # Verify password
    if not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    # Create tokens
    access_token = create_access_token(user.id, user.email, user.role, user.company_id)
    refresh_token = create_refresh_token(user.id)
    
    # Set refresh token in HTTP-only secure cookie
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=settings.refresh_token_expire_days * 24 * 60 * 60,
        domain=request.url.hostname if request.url.hostname != "localhost" else None
    )
    
    return Token(access_token=access_token, refresh_token=refresh_token)


@router.post("/logout")
async def logout(response: Response):
    """Logout by clearing refresh token cookie."""
    response.delete_cookie(
        key="refresh_token",
        httponly=True,
        secure=True,
        samesite="lax"
    )
    return {"message": "Logged out successfully"}


@router.post("/refresh", response_model=Token)
async def refresh_token(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    """Refresh access token using HTTP-only refresh cookie."""
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No refresh token"
        )
    
    # Verify refresh token
    from app.auth import verify_refresh_token
    user_id = verify_refresh_token(refresh_token)
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user"
        )
    
    # Create new tokens
    access_token = create_access_token(user.id, user.email, user.role, user.company_id)
    new_refresh_token = create_refresh_token(user.id)
    
    # Update cookie
    response.set_cookie(
        key="refresh_token",
        value=new_refresh_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=settings.refresh_token_expire_days * 24 * 60 * 60,
        domain=request.url.hostname if request.url.hostname != "localhost" else None
    )
    
    return Token(access_token=access_token, refresh_token=new_refresh_token)


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Get current authenticated user."""
    return current_user


@router.post("/set-password", response_model=UserResponse)
async def set_password(
    request: SetPasswordRequest,
    db: AsyncSession = Depends(get_db)
):
    """Set password via invite token. Activates account."""
    # Find invite token
    result = await db.execute(
        select(InviteToken).where(
            InviteToken.token == request.token,
            InviteToken.used_at.is_(None),
            InviteToken.expires_at > datetime.now(timezone.utc)
        )
    )
    invite = result.scalar_one_or_none()
    
    if not invite:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired invite token"
        )
    
    # Validate password
    if len(request.password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters"
        )
    
    if request.password != request.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passwords do not match"
        )
    
    # Hash password and update user
    hashed = hash_password(request.password)
    invite.user.hashed_password = hashed
    invite.user.is_active = True
    invite.used_at = datetime.now(timezone.utc)
    
    await db.commit()
    await db.refresh(invite.user)
    
    return invite.user


@router.post("/password-reset-request")
async def password_reset_request(
    request: PasswordResetRequest,
    db: AsyncSession = Depends(get_db)
):
    """Request password reset. Sends email with reset link (dev mode: logs link)."""
    result = await db.execute(select(User).where(User.email == request.email))
    user = result.scalar_one_or_none()
    
    if user:
        from app.auth import create_password_reset_token
        # Create reset token
        reset = create_password_reset_token(db, user.id)
        await db.commit()
        
        # In dev mode, log the reset link
        if settings.mail_mode == "dev":
            print(f"🔧 [DEV] Password reset link: http://localhost:5173/reset-password?token={reset.token}")
    
    # Always return success to prevent email enumeration
    return {"message": "If the email exists, a reset link has been sent"}


@router.post("/password-reset-confirm")
async def password_reset_confirm(
    request: PasswordResetConfirmRequest,
    db: AsyncSession = Depends(get_db)
):
    """Confirm password reset with token."""
    result = await db.execute(
        select(PasswordResetToken).where(
            PasswordResetToken.token == request.token,
            PasswordResetToken.used_at.is_(None),
            PasswordResetToken.expires_at > datetime.now(timezone.utc)
        )
    )
    reset = result.scalar_one_or_none()
    
    if not reset:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )
    
    if len(request.password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters"
        )
    
    if request.password != request.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passwords do not match"
        )
    
    # Update password
    reset.user.hashed_password = hash_password(request.password)
    reset.used_at = datetime.now(timezone.utc)
    
    await db.commit()
    
    return {"message": "Password reset successful"}


# Import settings at the bottom to avoid circular imports
from app.config import settings

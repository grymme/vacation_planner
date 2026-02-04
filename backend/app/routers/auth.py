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
    create_and_store_refresh_token,
    decode_token,
    verify_password,
    hash_password,
    get_current_user,
    require_admin,
    validate_refresh_token,
    revoke_all_user_refresh_tokens,
)
from app.middleware.rate_limit import account_lockout_store
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
    # Check account lockout
    is_allowed, error_message = await account_lockout_store.check_login(login_data.email)
    if not is_allowed:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=error_message
        )
    
    # Find user
    result = await db.execute(select(User).where(User.email == login_data.email))
    user = result.scalar_one_or_none()
    
    if not user:
        # Record failure for non-existent user (prevent user enumeration)
        await account_lockout_store.record_failure(login_data.email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    if not user.hashed_password:
        await account_lockout_store.record_failure(login_data.email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account not activated. Please set password via invite link."
        )
    
    if not user.is_active:
        await account_lockout_store.record_failure(login_data.email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is deactivated"
        )
    
    # Verify password
    if not verify_password(login_data.password, user.hashed_password):
        await account_lockout_store.record_failure(login_data.email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    # Clear failed attempts on successful login
    account_lockout_store.record_success(login_data.email)
    
    # Create tokens with token rotation
    access_token = create_access_token(user.id, user.email, user.role, user.company_id)
    refresh_token, token_jti = await create_and_store_refresh_token(db, user.id)
    
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
    """Refresh access token using HTTP-only refresh cookie with token rotation."""
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No refresh token"
        )
    
    # Validate refresh token against database
    user_id = await validate_refresh_token(db, refresh_token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or revoked refresh token"
        )
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user"
        )
    
    # Create new tokens (this will revoke the old refresh token)
    access_token = create_access_token(user.id, user.email, user.role, user.company_id)
    new_refresh_token, new_token_jti = await create_and_store_refresh_token(db, user.id)
    
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
    
    # Password validation is now handled by the schema validator
    # which enforces minimum 12 chars with complexity requirements
    
    # Hash password and update user
    hashed = hash_password(request.password)
    invite.user.hashed_password = hashed
    invite.user.is_active = True
    invite.used_at = datetime.now(timezone.utc)
    
    # Revoke all existing refresh tokens for security
    await revoke_all_user_refresh_tokens(db, invite.user.id)
    
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
    
    # Password validation is now handled by the schema validator
    # which enforces minimum 12 chars with complexity requirements
    
    # Update password
    reset.user.hashed_password = hash_password(request.password)
    reset.used_at = datetime.now(timezone.utc)
    
    # Revoke all existing refresh tokens for security
    await revoke_all_user_refresh_tokens(db, reset.user.id)
    
    await db.commit()
    
    return {"message": "Password reset successful"}


# Import settings at the bottom to avoid circular imports
from app.config import settings

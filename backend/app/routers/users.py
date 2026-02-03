"""Users router with RBAC and company isolation."""
from typing import Annotated, Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import User, UserRole
from app.auth import get_current_user
from app.schemas import UserResponse, UserUpdate

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current user's profile with teams and function."""
    await db.refresh(current_user, ["teams", "function"])
    return current_user


@router.put("/me", response_model=UserResponse)
async def update_current_user(
    update_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update current user's profile."""
    update_dict = update_data.model_dump(exclude_unset=True)
    
    # Users can only update their own profile
    for field, value in update_dict.items():
        setattr(current_user, field, value)
    
    await db.commit()
    await db.refresh(current_user, ["teams", "function"])
    
    return current_user


@router.get("/", response_model=List[UserResponse])
async def list_users(
    company_id: Optional[UUID] = None,
    function_id: Optional[UUID] = None,
    role: Optional[UserRole] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List users. Admins see all, Managers see company users, Users see only themselves."""
    if current_user.role == UserRole.ADMIN:
        # Admin can see all or filter
        query = select(User)
        if company_id:
            query = query.where(User.company_id == company_id)
    elif current_user.role in (UserRole.MANAGER, UserRole.ADMIN):
        # Manager sees only their company
        query = select(User).where(User.company_id == current_user.company_id)
        if function_id:
            query = query.where(User.function_id == function_id)
        if role:
            query = query.where(User.role == role)
    else:
        # Regular user can only see themselves
        return [current_user]
    
    result = await db.execute(query)
    users = result.scalars().all()
    
    return users


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific user. Authorization depends on role and company."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Authorization
    if current_user.role == UserRole.ADMIN:
        pass  # Admin can see all
    elif user.company_id != current_user.company_id:
        raise HTTPException(status_code=403, detail="Cannot access users from other companies")
    elif user.id != current_user.id and current_user.role == UserRole.USER:
        raise HTTPException(status_code=403, detail="Cannot view other users")
    
    await db.refresh(user, ["teams", "function"])
    return user


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: UUID,
    update_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update a user. Admins and managers can update users in their company."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Authorization checks
    if current_user.role != UserRole.ADMIN:
        # Must be in same company
        if user.company_id != current_user.company_id:
            raise HTTPException(status_code=403, detail="Cannot update users from other companies")
        
        # Regular users can only update themselves
        if user.id != current_user.id:
            raise HTTPException(status_code=403, detail="Cannot update other users")
    
    update_dict = update_data.model_dump(exclude_unset=True)
    
    for field, value in update_dict.items():
        setattr(user, field, value)
    
    await db.commit()
    await db.refresh(user, ["teams", "function"])
    
    return user

"""Admin router for management operations with company/function/team management."""
from typing import Annotated, Optional, List
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import (
    User, Team, TeamMembership, TeamManagerAssignment, 
    Function, Company, AuditAction, UserRole
)
from app.auth import get_current_user, require_role, create_invite_token, hash_password
from app.audit import log_audit
from app.schemas import (
    UserResponse,
    UserUpdate,
    InviteUserRequest,
    InviteResponse,
    AuditLogResponse,
    CompanyCreate,
    CompanyResponse,
    FunctionCreate,
    FunctionResponse,
    TeamCreate,
    TeamResponse,
    MessageResponse,
)

router = APIRouter(prefix="/admin", tags=["Admin"])


# =============================================================================
# Company Management
# =============================================================================

@router.post("/companies", response_model=CompanyResponse)
async def create_company(
    request: CompanyCreate,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    """Admin: Create a new company."""
    company = Company(name=request.name)
    db.add(company)
    await db.commit()
    await db.refresh(company)
    
    await log_audit(
        db, current_user, AuditAction.TEAM_CREATED, "company", company.id, 
        {"name": company.name}
    )
    
    return company


@router.get("/companies", response_model=List[CompanyResponse])
async def list_companies(
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    """Admin: List all companies."""
    result = await db.execute(select(Company))
    return result.scalars().all()


@router.get("/companies/{company_id}", response_model=CompanyResponse)
async def get_company(
    company_id: UUID,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    """Admin: Get company by ID."""
    result = await db.execute(select(Company).where(Company.id == company_id))
    company = result.scalar_one_or_none()
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    return company


# =============================================================================
# Function Management
# =============================================================================

@router.post("/functions", response_model=FunctionResponse)
async def create_function(
    request: FunctionCreate,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    """Admin: Create a new function/department."""
    # Verify company exists
    company_result = await db.execute(select(Company).where(Company.id == request.company_id))
    if not company_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Company not found")
    
    function = Function(
        company_id=request.company_id,
        name=request.name
    )
    db.add(function)
    await db.commit()
    await db.refresh(function)
    
    await log_audit(
        db, current_user, AuditAction.TEAM_CREATED, "function", function.id, 
        {"name": function.name, "company_id": str(function.company_id)}
    )
    
    return function


@router.get("/functions", response_model=List[FunctionResponse])
async def list_functions(
    company_id: Optional[UUID] = None,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    """Admin: List functions, optionally filtered by company."""
    query = select(Function)
    if company_id:
        query = query.where(Function.company_id == company_id)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/functions/{function_id}", response_model=FunctionResponse)
async def get_function(
    function_id: UUID,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    """Admin: Get function by ID."""
    result = await db.execute(select(Function).where(Function.id == function_id))
    function = result.scalar_one_or_none()
    
    if not function:
        raise HTTPException(status_code=404, detail="Function not found")
    
    return function


# =============================================================================
# Team Management
# =============================================================================

@router.post("/teams", response_model=TeamResponse)
async def create_team(
    request: TeamCreate,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    """Admin: Create a new team."""
    # Verify company exists
    company_result = await db.execute(select(Company).where(Company.id == request.company_id))
    if not company_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Company not found")
    
    team = Team(
        company_id=request.company_id,
        name=request.name
    )
    db.add(team)
    await db.commit()
    await db.refresh(team)
    
    await log_audit(
        db, current_user, AuditAction.TEAM_CREATED, "team", team.id, 
        {"name": team.name, "company_id": str(team.company_id)}
    )
    
    return team


@router.get("/teams", response_model=List[TeamResponse])
async def list_teams(
    company_id: Optional[UUID] = None,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    """Admin: List teams, optionally filtered by company."""
    query = select(Team)
    if company_id:
        query = query.where(Team.company_id == company_id)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/teams/{team_id}", response_model=TeamResponse)
async def get_team(
    team_id: UUID,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    """Admin: Get team by ID."""
    result = await db.execute(select(Team).where(Team.id == team_id))
    team = result.scalar_one_or_none()
    
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    return team


@router.post("/teams/{team_id}/members/{user_id}", response_model=MessageResponse)
async def add_team_member(
    team_id: UUID,
    user_id: UUID,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    """Admin: Add a user to a team."""
    # Verify team exists
    team_result = await db.execute(select(Team).where(Team.id == team_id))
    team = team_result.scalar_one_or_none()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    # Verify user exists
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if already a member
    existing = await db.execute(
        select(TeamMembership).where(
            and_(
                TeamMembership.user_id == user_id,
                TeamMembership.team_id == team_id
            )
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="User is already a team member")
    
    membership = TeamMembership(user_id=user_id, team_id=team_id)
    db.add(membership)
    await db.commit()
    
    await log_audit(
        db, current_user, AuditAction.USER_UPDATED, "team", team_id, 
        {"action": "add_member", "user_id": str(user_id)}
    )
    
    return {"message": "User added to team"}


@router.delete("/teams/{team_id}/members/{user_id}", response_model=MessageResponse)
async def remove_team_member(
    team_id: UUID,
    user_id: UUID,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    """Admin: Remove a user from a team."""
    result = await db.execute(
        select(TeamMembership).where(
            and_(
                TeamMembership.user_id == user_id,
                TeamMembership.team_id == team_id
            )
        )
    )
    membership = result.scalar_one_or_none()
    
    if not membership:
        raise HTTPException(status_code=404, detail="Team membership not found")
    
    await db.delete(membership)
    await db.commit()
    
    await log_audit(
        db, current_user, AuditAction.USER_UPDATED, "team", team_id, 
        {"action": "remove_member", "user_id": str(user_id)}
    )
    
    return {"message": "User removed from team"}


@router.post("/teams/{team_id}/managers/{user_id}", response_model=MessageResponse)
async def assign_team_manager(
    team_id: UUID,
    user_id: UUID,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    """Admin: Assign a user as manager of a team."""
    # Verify team exists
    team_result = await db.execute(select(Team).where(Team.id == team_id))
    team = team_result.scalar_one_or_none()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    # Verify user exists and is in the company
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.company_id != team.company_id:
        raise HTTPException(status_code=400, detail="User must be in the same company as the team")
    
    # Check if already a manager
    existing = await db.execute(
        select(TeamManagerAssignment).where(
            and_(
                TeamManagerAssignment.user_id == user_id,
                TeamManagerAssignment.team_id == team_id
            )
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="User is already a team manager")
    
    # Update user role if not already manager
    if user.role == UserRole.USER:
        user.role = UserRole.MANAGER
    
    assignment = TeamManagerAssignment(user_id=user_id, team_id=team_id)
    db.add(assignment)
    await db.commit()
    
    await log_audit(
        db, current_user, AuditAction.MANAGER_ASSIGNED, "team", team_id, 
        {"manager_id": str(user_id)}
    )
    
    return {"message": "Team manager assigned"}


@router.delete("/teams/{team_id}/managers/{user_id}", response_model=MessageResponse)
async def remove_team_manager(
    team_id: UUID,
    user_id: UUID,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    """Admin: Remove a user's manager assignment from a team."""
    result = await db.execute(
        select(TeamManagerAssignment).where(
            and_(
                TeamManagerAssignment.user_id == user_id,
                TeamManagerAssignment.team_id == team_id
            )
        )
    )
    assignment = result.scalar_one_or_none()
    
    if not assignment:
        raise HTTPException(status_code=404, detail="Manager assignment not found")
    
    await db.delete(assignment)
    await db.commit()
    
    # Check if user is still manager of any teams
    remaining = await db.execute(
        select(TeamManagerAssignment).where(TeamManagerAssignment.user_id == user_id)
    )
    if not remaining.scalar_one_or_none():
        # Demote to user if no longer managing any teams
        user_result = await db.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()
        if user and user.role == UserRole.MANAGER:
            user.role = UserRole.USER
            await db.commit()
    
    await log_audit(
        db, current_user, AuditAction.MANAGER_REMOVED, "team", team_id, 
        {"manager_id": str(user_id)}
    )
    
    return {"message": "Team manager removed"}


# =============================================================================
# User Management (Existing)
# =============================================================================

@router.post("/invite", response_model=InviteResponse)
async def invite_user(
    request: InviteUserRequest,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    """Admin: Invite a new user. Creates inactive user + invite token."""
    # Verify company access
    if current_user.role != UserRole.ADMIN and current_user.company_id != request.company_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot invite to other company"
        )
    
    # Check if user already exists
    result = await db.execute(select(User).where(User.email == request.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists"
        )
    
    # Create user (inactive, no password yet)
    user = User(
        email=request.email,
        first_name=request.first_name,
        last_name=request.last_name,
        role=request.role,
        company_id=request.company_id,
        function_id=request.function_id,
        is_active=False,
        hashed_password=None
    )
    db.add(user)
    await db.flush()
    
    # Add to teams
    for team_id in request.team_ids:
        membership = TeamMembership(user_id=user.id, team_id=team_id)
        db.add(membership)
    
    # Create invite token
    invite = create_invite_token(db, user.id, created_by=current_user.id)
    await db.commit()
    
    return {
        "message": "User invited successfully",
        "user_id": user.id,
        "invite_token": invite.token,
        "invite_link": f"http://localhost:5173/set-password?token={invite.token}"
    }


@router.post("/users/{user_id}/deactivate", response_model=UserResponse)
async def deactivate_user(
    user_id: UUID,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    """Admin: Deactivate a user."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user.is_active = False
    await db.commit()
    await db.refresh(user)
    
    return user


@router.post("/users/{user_id}/reset-password")
async def admin_reset_password(
    user_id: UUID,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    """Admin: Reset user's password (invalidate current sessions, send new invite)."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Invalidate password (sets to None, requires password reset flow)
    user.hashed_password = None
    user.is_active = False
    
    await db.commit()
    
    return {"message": "Password reset. User will need to use password reset flow."}


@router.get("/users", response_model=list[UserResponse])
async def list_users(
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
):
    """Admin: List all users."""
    result = await db.execute(
        select(User).offset(skip).limit(limit).order_by(User.created_at.desc())
    )
    return result.scalars().all()


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: UUID,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    """Admin: Get user by ID."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: UUID,
    update_data: UserUpdate,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    """Admin: Update user."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    update_dict = update_data.model_dump(exclude_unset=True)
    
    for field, value in update_dict.items():
        setattr(user, field, value)
    
    await db.commit()
    await db.refresh(user)
    
    return user


# =============================================================================
# Audit Logs
# =============================================================================

@router.get("/audit-logs", response_model=list[AuditLogResponse])
async def list_audit_logs(
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
):
    """Admin: List audit logs."""
    from app.models import AuditLog
    
    result = await db.execute(
        select(AuditLog).offset(skip).limit(limit).order_by(AuditLog.created_at.desc())
    )
    return result.scalars().all()

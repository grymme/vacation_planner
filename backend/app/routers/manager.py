"""Manager router for manager-specific operations."""
from typing import Annotated, Optional, List
from uuid import UUID
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import (
    User, Team, TeamMembership, TeamManagerAssignment, 
    VacationRequest, VacationStatus, UserRole
)
from app.auth import get_current_user, require_role
from app.schemas import (
    UserResponse,
    TeamResponse,
    VacationRequestResponse,
    MessageResponse,
)

router = APIRouter(prefix="/manager", tags=["Manager"])


@router.get("/teams", response_model=List[TeamResponse])
async def get_managed_teams(
    current_user: User = Depends(require_role(UserRole.MANAGER, UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    """Manager: Get teams this user manages."""
    if current_user.role == UserRole.ADMIN:
        # Admin manages all teams in their company
        result = await db.execute(
            select(Team).where(Team.company_id == current_user.company_id)
        )
    else:
        result = await db.execute(
            select(Team).join(
                TeamManagerAssignment,
                TeamManagerAssignment.team_id == Team.id
            ).where(
                TeamManagerAssignment.user_id == current_user.id
            )
        )
    
    return result.scalars().all()


@router.get("/team-members/{team_id}", response_model=List[UserResponse])
async def get_team_members(
    team_id: UUID,
    current_user: User = Depends(require_role(UserRole.MANAGER, UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    """Manager: Get members of a team they manage."""
    # Verify manager access
    if current_user.role != UserRole.ADMIN:
        manager_check = await db.execute(
            select(TeamManagerAssignment).where(
                and_(
                    TeamManagerAssignment.user_id == current_user.id,
                    TeamManagerAssignment.team_id == team_id
                )
            )
        )
        if not manager_check.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="Not authorized to view this team")
    
    # Verify team exists and is in same company
    team_result = await db.execute(select(Team).where(Team.id == team_id))
    team = team_result.scalar_one_or_none()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    if team.company_id != current_user.company_id:
        raise HTTPException(status_code=403, detail="Cannot access teams from other companies")
    
    result = await db.execute(
        select(User)
        .join(TeamMembership, TeamMembership.user_id == User.id)
        .where(TeamMembership.team_id == team_id)
    )
    
    return result.scalars().all()


@router.get("/team-vacation-requests/{team_id}", response_model=List[VacationRequestResponse])
async def get_team_vacation_requests(
    team_id: UUID,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    status: Optional[VacationStatus] = None,
    current_user: User = Depends(require_role(UserRole.MANAGER, UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    """Manager: Get vacation requests for a team they manage."""
    # Verify manager access
    if current_user.role != UserRole.ADMIN:
        manager_check = await db.execute(
            select(TeamManagerAssignment).where(
                and_(
                    TeamManagerAssignment.user_id == current_user.id,
                    TeamManagerAssignment.team_id == team_id
                )
            )
        )
        if not manager_check.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="Not authorized to view this team")
    
    # Verify team exists and is in same company
    team_result = await db.execute(select(Team).where(Team.id == team_id))
    team = team_result.scalar_one_or_none()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    if team.company_id != current_user.company_id:
        raise HTTPException(status_code=403, detail="Cannot access teams from other companies")
    
    query = select(VacationRequest).where(VacationRequest.team_id == team_id)
    
    if start_date:
        query = query.where(VacationRequest.end_date >= start_date)
    if end_date:
        query = query.where(VacationRequest.start_date <= end_date)
    if status:
        query = query.where(VacationRequest.status == status)
    
    query = query.order_by(VacationRequest.start_date)
    result = await db.execute(query)
    requests = result.scalars().all()
    
    # Load user relationships
    for vr in requests:
        await db.refresh(vr, ["user"])
    
    return requests


@router.get("/pending-requests", response_model=List[VacationRequestResponse])
async def get_pending_requests(
    current_user: User = Depends(require_role(UserRole.MANAGER, UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    """Manager: Get all pending vacation requests for managed teams."""
    if current_user.role == UserRole.ADMIN:
        # Admin sees all pending
        query = select(VacationRequest).where(
            and_(
                VacationRequest.status == VacationStatus.PENDING,
                VacationRequest.team_id.isnot(None)
            )
        ).options(selectinload(VacationRequest.user))
    else:
        # Manager sees only their teams
        managed_teams = await db.execute(
            select(TeamManagerAssignment.team_id).where(
                TeamManagerAssignment.user_id == current_user.id
            )
        )
        team_ids = [t[0] for t in managed_teams.fetchall()]
        
        if not team_ids:
            return []
        
        query = select(VacationRequest).where(
            and_(
                VacationRequest.status == VacationStatus.PENDING,
                VacationRequest.team_id.in_(team_ids)
            )
        ).options(selectinload(VacationRequest.user))
    
    query = query.order_by(VacationRequest.created_at)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/teams/{team_id}/members/{user_id}/remove", response_model=MessageResponse)
async def remove_team_member(
    team_id: UUID,
    user_id: UUID,
    current_user: User = Depends(require_role(UserRole.MANAGER, UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    """Manager: Remove a user from a team they manage."""
    # Verify manager access
    if current_user.role != UserRole.ADMIN:
        manager_check = await db.execute(
            select(TeamManagerAssignment).where(
                and_(
                    TeamManagerAssignment.user_id == current_user.id,
                    TeamManagerAssignment.team_id == team_id
                )
            )
        )
        if not manager_check.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="Not authorized to manage this team")
    
    # Verify team exists and is in same company
    team_result = await db.execute(select(Team).where(Team.id == team_id))
    team = team_result.scalar_one_or_none()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    if team.company_id != current_user.company_id:
        raise HTTPException(status_code=403, detail="Cannot access teams from other companies")
    
    # Find and remove membership
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
    
    return {"message": "User removed from team"}

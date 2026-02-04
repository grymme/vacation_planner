"""Vacation requests router with RBAC enforcement."""
from datetime import date, datetime, timezone
from typing import Annotated, Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import (
    User, VacationRequest, VacationStatus, TeamMembership, 
    TeamManagerAssignment, AuditAction, Team, UserRole,
    VacationPeriod, VacationAllocation
)
from app.auth import get_current_user, require_role
from app.audit import log_audit
from app.schemas import (
    VacationRequestCreate,
    VacationRequestResponse,
    VacationRequestUpdate,
    VacationRequestAction,
)
from app.utils import calculate_business_days, get_vacation_period_for_date

router = APIRouter(prefix="/vacation-requests", tags=["Vacation Requests"])


@router.get("/", response_model=List[VacationRequestResponse])
async def get_my_vacation_requests(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    status: Optional[VacationStatus] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current user's vacation requests with optional filters."""
    query = select(VacationRequest).where(
        VacationRequest.user_id == current_user.id
    )
    
    if start_date:
        query = query.where(VacationRequest.end_date >= start_date)
    if end_date:
        query = query.where(VacationRequest.start_date <= end_date)
    if status:
        query = query.where(VacationRequest.status == status)
    
    query = query.order_by(VacationRequest.start_date.desc())
    
    result = await db.execute(query)
    requests = result.scalars().all()
    
    # Load user relationship
    for vr in requests:
        await db.refresh(vr, ["user"])
    
    return requests


@router.post("/", response_model=VacationRequestResponse, status_code=201)
async def create_vacation_request(
    request: VacationRequestCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new vacation request with auto-calculated days and period assignment."""
    # Validate dates
    if request.end_date < request.start_date:
        raise HTTPException(status_code=400, detail="End date must be after start date")
    
    # Calculate business days
    days_count = calculate_business_days(request.start_date, request.end_date)
    
    # Find vacation period for start_date
    periods_result = await db.execute(
        select(VacationPeriod).where(
            VacationPeriod.company_id == current_user.company_id
        )
    )
    periods = periods_result.scalars().all()
    period = get_vacation_period_for_date(request.start_date, periods)
    
    if not period:
        raise HTTPException(
            status_code=400, 
            detail="No vacation period found for the requested date"
        )
    
    # Check remaining balance (if allocation exists)
    allocation_result = await db.execute(
        select(VacationAllocation).where(
            VacationAllocation.user_id == current_user.id,
            VacationAllocation.vacation_period_id == period.id
        )
    )
    allocation = allocation_result.scalar_one_or_none()
    
    if allocation:
        # Get approved days for this period
        approved_result = await db.execute(
            select(func.coalesce(func.sum(VacationRequest.days_count), 0.0)).where(
                VacationRequest.user_id == current_user.id,
                VacationRequest.vacation_period_id == period.id,
                VacationRequest.status == VacationStatus.APPROVED
            )
        )
        approved_days = approved_result.scalar() or 0.0
        
        total_available = allocation.total_days + allocation.carried_over_days
        remaining = total_available - approved_days
        
        if days_count > remaining:
            raise HTTPException(
                status_code=400, 
                detail=f"Insufficient vacation balance. Requested: {days_count}, Remaining: {remaining}"
            )
    
    # Check for overlapping requests
    overlap = await db.execute(
        select(VacationRequest).where(
            and_(
                VacationRequest.user_id == current_user.id,
                VacationRequest.status != VacationStatus.CANCELLED,
                or_(
                    and_(
                        VacationRequest.start_date <= request.start_date,
                        VacationRequest.end_date >= request.start_date
                    ),
                    and_(
                        VacationRequest.start_date <= request.end_date,
                        VacationRequest.end_date >= request.end_date
                    ),
                    and_(
                        VacationRequest.start_date >= request.start_date,
                        VacationRequest.end_date <= request.end_date
                    )
                )
            )
        )
    )
    if overlap.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Overlapping vacation request exists")
    
    # If team_id provided, verify user belongs to team
    if request.team_id:
        team_check = await db.execute(
            select(TeamMembership).where(
                and_(
                    TeamMembership.user_id == current_user.id,
                    TeamMembership.team_id == request.team_id
                )
            )
        )
        if not team_check.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="User does not belong to specified team")
    
    # Create request
    vr = VacationRequest(
        user_id=current_user.id,
        team_id=request.team_id,
        vacation_period_id=period.id,
        start_date=request.start_date,
        end_date=request.end_date,
        vacation_type=request.vacation_type,
        days_count=days_count,
        reason=request.reason,
        status=VacationStatus.PENDING
    )
    db.add(vr)
    await db.commit()
    await db.refresh(vr)
    await db.refresh(vr, ["user"])
    
    return vr


@router.get("/{request_id}", response_model=VacationRequestResponse)
async def get_vacation_request(
    request_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific vacation request. Users can only see their own requests or requests from their teams (if manager)."""
    result = await db.execute(
        select(VacationRequest)
        .options(selectinload(VacationRequest.user))
        .where(VacationRequest.id == request_id)
    )
    vr = result.scalar_one_or_none()
    
    if not vr:
        raise HTTPException(status_code=404, detail="Vacation request not found")
    
    # Authorization: user can see own request, manager can see team requests
    if vr.user_id != current_user.id:
        if current_user.role == UserRole.ADMIN:
            pass  # Admin can see all
        elif current_user.role == UserRole.MANAGER:
            # Check if manager of any team the user belongs to
            manager_check = await db.execute(
                select(TeamManagerAssignment).where(
                    and_(
                        TeamManagerAssignment.user_id == current_user.id,
                        TeamManagerAssignment.team_id == vr.team_id
                    )
                )
            )
            if not manager_check.scalar_one_or_none():
                raise HTTPException(status_code=403, detail="Not authorized to view this request")
        else:
            raise HTTPException(status_code=403, detail="Not authorized to view this request")
    
    await db.refresh(vr, ["user"])
    return vr


@router.delete("/{request_id}")
async def cancel_vacation_request(
    request_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Cancel a pending vacation request. Only the owner can cancel."""
    result = await db.execute(
        select(VacationRequest).where(VacationRequest.id == request_id)
    )
    vr = result.scalar_one_or_none()
    
    if not vr:
        raise HTTPException(status_code=404, detail="Vacation request not found")
    
    if vr.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the owner can cancel this request")
    
    if vr.status != VacationStatus.PENDING:
        raise HTTPException(status_code=400, detail="Can only cancel pending requests")
    
    vr.status = VacationStatus.CANCELLED
    await db.commit()
    
    await log_audit(
        db, current_user, AuditAction.VACATION_REQUEST_CANCELLED, 
        "vacation_request", vr.id, {"dates": f"{vr.start_date} - {vr.end_date}"}
    )
    
    return {"message": "Vacation request cancelled"}


# =============================================================================
# Manager/Admin Endpoints
# =============================================================================

@router.get("/pending", response_model=List[VacationRequestResponse])
async def get_pending_requests_for_approval(
    team_id: Optional[UUID] = None,
    current_user: User = Depends(require_role(UserRole.MANAGER, UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    """Get pending vacation requests for teams managed by current manager."""
    if current_user.role == UserRole.ADMIN:
        # Admin sees all pending
        query = select(VacationRequest).where(
            and_(
                VacationRequest.status == VacationStatus.PENDING,
                VacationRequest.team_id.isnot(None)
            )
        )
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
        
        if team_id and team_id in team_ids:
            team_ids = [team_id]
        
        query = select(VacationRequest).where(
            and_(
                VacationRequest.status == VacationStatus.PENDING,
                VacationRequest.team_id.in_(team_ids)
            )
        ).options(selectinload(VacationRequest.user))
    
    query = query.order_by(VacationRequest.created_at)
    result = await db.execute(query)
    requests = result.scalars().all()
    
    return requests


@router.post("/{request_id}/approve", response_model=VacationRequestResponse)
async def approve_vacation_request(
    request_id: UUID,
    action: VacationRequestAction,
    current_user: User = Depends(require_role(UserRole.MANAGER, UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    """Approve or reject a vacation request. Managers can only act on their team's requests."""
    result = await db.execute(
        select(VacationRequest).where(VacationRequest.id == request_id)
    )
    vr = result.scalar_one_or_none()
    
    if not vr:
        raise HTTPException(status_code=404, detail="Vacation request not found")
    
    if vr.status != VacationStatus.PENDING:
        raise HTTPException(status_code=400, detail="Can only act on pending requests")
    
    # Authorization: manager must be assigned to the team
    if current_user.role != UserRole.ADMIN:
        manager_check = await db.execute(
            select(TeamManagerAssignment).where(
                and_(
                    TeamManagerAssignment.user_id == current_user.id,
                    TeamManagerAssignment.team_id == vr.team_id
                )
            )
        )
        if not manager_check.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="Not authorized to approve requests for this team")
    
    # Approve or reject
    if action.action == "approve":
        vr.status = VacationStatus.APPROVED
        vr.approver_id = current_user.id
        vr.approved_at = datetime.now(timezone.utc)
        audit_action = AuditAction.VACATION_REQUEST_APPROVED
    else:
        vr.status = VacationStatus.REJECTED
        vr.approver_id = current_user.id
        vr.approved_at = datetime.now(timezone.utc)
        audit_action = AuditAction.VACATION_REQUEST_REJECTED
    
    await db.commit()
    await db.refresh(vr, ["user"])
    
    await log_audit(db, current_user, audit_action, "vacation_request", vr.id, {
        "user_id": str(vr.user_id),
        "dates": f"{vr.start_date} - {vr.end_date}",
        "comment": action.comment
    })
    
    return vr


@router.put("/{request_id}/modify", response_model=VacationRequestResponse)
async def modify_vacation_request(
    request_id: UUID,
    update: VacationRequestUpdate,
    current_user: User = Depends(require_role(UserRole.MANAGER, UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    """Modify a vacation request's dates/type/reason. Managers can modify their team's requests."""
    result = await db.execute(
        select(VacationRequest).where(VacationRequest.id == request_id)
    )
    vr = result.scalar_one_or_none()
    
    if not vr:
        raise HTTPException(status_code=404, detail="Vacation request not found")
    
    # Authorization
    if current_user.role != UserRole.ADMIN:
        manager_check = await db.execute(
            select(TeamManagerAssignment).where(
                and_(
                    TeamManagerAssignment.user_id == current_user.id,
                    TeamManagerAssignment.team_id == vr.team_id
                )
            )
        )
        if not manager_check.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="Not authorized to modify requests for this team")
    
    # Track changes for audit
    changes = {}
    if update.start_date and update.start_date != vr.start_date:
        changes["start_date"] = {"from": str(vr.start_date), "to": str(update.start_date)}
        vr.start_date = update.start_date
    if update.end_date and update.end_date != vr.end_date:
        changes["end_date"] = {"from": str(vr.end_date), "to": str(update.end_date)}
        vr.end_date = update.end_date
    if update.vacation_type and update.vacation_type != vr.vacation_type:
        changes["vacation_type"] = {"from": vr.vacation_type, "to": update.vacation_type}
        vr.vacation_type = update.vacation_type
    if update.reason and update.reason != vr.reason:
        changes["reason"] = {"from": vr.reason, "to": update.reason}
        vr.reason = update.reason
    
    await db.commit()
    await db.refresh(vr, ["user"])
    
    await log_audit(db, current_user, AuditAction.VACATION_REQUEST_MODIFIED, 
                    "vacation_request", vr.id, {"changes": changes})
    
    return vr

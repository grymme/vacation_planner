"""Vacation periods and allocations router with admin endpoints."""
from datetime import date
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import (
    User, VacationPeriod, VacationAllocation, VacationRequest,
    VacationStatus, UserRole
)
from app.auth import get_current_user, require_role
from app.schemas import (
    VacationPeriodCreate,
    VacationPeriodUpdate,
    VacationPeriodResponse,
    VacationAllocationCreate,
    VacationAllocationUpdate,
    VacationAllocationResponse,
    VacationBalanceResponse,
)

# =============================================================================
# Admin Vacation Periods Router
# =============================================================================
router = APIRouter(prefix="/admin/vacation-periods", tags=["Vacation Periods"])


@router.get("/", response_model=List[VacationPeriodResponse])
async def get_vacation_periods(
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    """Get all vacation periods for the company."""
    result = await db.execute(
        select(VacationPeriod).where(
            VacationPeriod.company_id == current_user.company_id
        ).order_by(VacationPeriod.start_date.desc())
    )
    return result.scalars().all()


@router.get("/{period_id}", response_model=VacationPeriodResponse)
async def get_vacation_period(
    period_id: UUID,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific vacation period."""
    result = await db.execute(
        select(VacationPeriod).where(
            VacationPeriod.id == period_id,
            VacationPeriod.company_id == current_user.company_id
        )
    )
    period = result.scalar_one_or_none()
    
    if not period:
        raise HTTPException(status_code=404, detail="Vacation period not found")
    
    return period


@router.post("/", response_model=VacationPeriodResponse, status_code=201)
async def create_vacation_period(
    period: VacationPeriodCreate,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    """Create a new vacation period."""
    # Verify company access
    if period.company_id != current_user.company_id:
        raise HTTPException(status_code=403, detail="Not authorized to create periods for this company")
    
    # Check for overlapping periods
    overlap_result = await db.execute(
        select(VacationPeriod).where(
            VacationPeriod.company_id == period.company_id,
            VacationPeriod.start_date <= period.end_date,
            VacationPeriod.end_date >= period.start_date
        )
    )
    if overlap_result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Overlapping vacation period exists")
    
    # If this is set as default, unset other defaults
    if period.is_default:
        existing_defaults = await db.execute(
            select(VacationPeriod).where(
                VacationPeriod.company_id == period.company_id,
                VacationPeriod.is_default == True
            )
        )
        for existing in existing_defaults.scalars().all():
            existing.is_default = False
    
    db_period = VacationPeriod(**period.model_dump())
    db.add(db_period)
    await db.commit()
    await db.refresh(db_period)
    return db_period


@router.put("/{period_id}", response_model=VacationPeriodResponse)
async def update_vacation_period(
    period_id: UUID,
    update: VacationPeriodUpdate,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    """Update a vacation period."""
    result = await db.execute(
        select(VacationPeriod).where(
            VacationPeriod.id == period_id,
            VacationPeriod.company_id == current_user.company_id
        )
    )
    period = result.scalar_one_or_none()
    
    if not period:
        raise HTTPException(status_code=404, detail="Vacation period not found")
    
    # If setting as default, unset other defaults
    if update.is_default:
        existing_defaults = await db.execute(
            select(VacationPeriod).where(
                VacationPeriod.company_id == current_user.company_id,
                VacationPeriod.is_default == True,
                VacationPeriod.id != period_id
            )
        )
        for existing in existing_defaults.scalars().all():
            existing.is_default = False
    
    # Update fields
    update_data = update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(period, field, value)
    
    await db.commit()
    await db.refresh(period)
    return period


@router.delete("/{period_id}")
async def delete_vacation_period(
    period_id: UUID,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    """Delete a vacation period."""
    result = await db.execute(
        select(VacationPeriod).where(
            VacationPeriod.id == period_id,
            VacationPeriod.company_id == current_user.company_id
        )
    )
    period = result.scalar_one_or_none()
    
    if not period:
        raise HTTPException(status_code=404, detail="Vacation period not found")
    
    # Check if there are any vacation requests linked to this period
    requests_result = await db.execute(
        select(VacationRequest).where(
            VacationRequest.vacation_period_id == period_id
        ).limit(1)
    )
    if requests_result.scalar_one_or_none():
        raise HTTPException(
            status_code=400, 
            detail="Cannot delete vacation period with existing vacation requests"
        )
    
    await db.delete(period)
    await db.commit()
    return {"message": "Vacation period deleted"}


# =============================================================================
# Admin Allocations Router
# =============================================================================
router_allocations = APIRouter(prefix="/admin/allocations", tags=["Vacation Allocations"])


@router_allocations.get("/", response_model=List[VacationAllocationResponse])
async def get_allocations(
    vacation_period_id: Optional[UUID] = None,
    user_id: Optional[UUID] = None,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    """Get vacation allocations with optional filters."""
    query = select(VacationAllocation).join(
        VacationPeriod, VacationAllocation.vacation_period_id == VacationPeriod.id
    ).where(
        VacationPeriod.company_id == current_user.company_id
    )
    
    if vacation_period_id:
        query = query.where(VacationAllocation.vacation_period_id == vacation_period_id)
    if user_id:
        query = query.where(VacationAllocation.user_id == user_id)
    
    result = await db.execute(query)
    return result.scalars().all()


@router_allocations.get("/{allocation_id}", response_model=VacationAllocationResponse)
async def get_allocation(
    allocation_id: UUID,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific vacation allocation."""
    result = await db.execute(
        select(VacationAllocation).join(
            VacationPeriod, VacationAllocation.vacation_period_id == VacationPeriod.id
        ).where(
            VacationAllocation.id == allocation_id,
            VacationPeriod.company_id == current_user.company_id
        )
    )
    allocation = result.scalar_one_or_none()
    
    if not allocation:
        raise HTTPException(status_code=404, detail="Vacation allocation not found")
    
    return allocation


@router_allocations.post("/", response_model=VacationAllocationResponse, status_code=201)
async def create_allocation(
    allocation: VacationAllocationCreate,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    """Create a new vacation allocation."""
    # Verify user belongs to same company
    user_result = await db.execute(
        select(User).where(User.id == allocation.user_id)
    )
    user = user_result.scalar_one_or_none()
    if not user or user.company_id != current_user.company_id:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Verify vacation period belongs to same company
    period_result = await db.execute(
        select(VacationPeriod).where(
            VacationPeriod.id == allocation.vacation_period_id,
            VacationPeriod.company_id == current_user.company_id
        )
    )
    if not period_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Vacation period not found")
    
    # Check for existing allocation
    existing_result = await db.execute(
        select(VacationAllocation).where(
            VacationAllocation.user_id == allocation.user_id,
            VacationAllocation.vacation_period_id == allocation.vacation_period_id
        )
    )
    if existing_result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Allocation already exists for this user and period")
    
    db_allocation = VacationAllocation(**allocation.model_dump())
    db.add(db_allocation)
    await db.commit()
    await db.refresh(db_allocation)
    return db_allocation


@router_allocations.put("/{allocation_id}", response_model=VacationAllocationResponse)
async def update_allocation(
    allocation_id: UUID,
    update: VacationAllocationUpdate,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    """Update a vacation allocation."""
    result = await db.execute(
        select(VacationAllocation).join(
            VacationPeriod, VacationAllocation.vacation_period_id == VacationPeriod.id
        ).where(
            VacationAllocation.id == allocation_id,
            VacationPeriod.company_id == current_user.company_id
        )
    )
    allocation = result.scalar_one_or_none()
    
    if not allocation:
        raise HTTPException(status_code=404, detail="Vacation allocation not found")
    
    # Update fields
    update_data = update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(allocation, field, value)
    
    await db.commit()
    await db.refresh(allocation)
    return allocation


@router_allocations.delete("/{allocation_id}")
async def delete_allocation(
    allocation_id: UUID,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    """Delete a vacation allocation."""
    result = await db.execute(
        select(VacationAllocation).join(
            VacationPeriod, VacationAllocation.vacation_period_id == VacationPeriod.id
        ).where(
            VacationAllocation.id == allocation_id,
            VacationPeriod.company_id == current_user.company_id
        )
    )
    allocation = result.scalar_one_or_none()
    
    if not allocation:
        raise HTTPException(status_code=404, detail="Vacation allocation not found")
    
    await db.delete(allocation)
    await db.commit()
    return {"message": "Vacation allocation deleted"}


# =============================================================================
# User Vacation Balance Router
# =============================================================================
router_balance = APIRouter(prefix="/me", tags=["User Vacation Balance"])


@router_balance.get("/vacation-balance", response_model=VacationBalanceResponse)
async def get_my_vacation_balance(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get the current user's vacation balance for the active period."""
    today = date.today()
    
    # Get current vacation period
    period_result = await db.execute(
        select(VacationPeriod).where(
            VacationPeriod.company_id == current_user.company_id,
            VacationPeriod.start_date <= today,
            VacationPeriod.end_date >= today
        )
    )
    period = period_result.scalar_one_or_none()
    
    if not period:
        raise HTTPException(status_code=404, detail="No active vacation period found")
    
    # Get allocation
    allocation_result = await db.execute(
        select(VacationAllocation).where(
            VacationAllocation.user_id == current_user.id,
            VacationAllocation.vacation_period_id == period.id
        )
    )
    allocation = allocation_result.scalar_one_or_none()
    
    # Get approved days
    approved_result = await db.execute(
        select(func.coalesce(func.sum(VacationRequest.days_count), 0.0)).where(
            VacationRequest.user_id == current_user.id,
            VacationRequest.vacation_period_id == period.id,
            VacationRequest.status == VacationStatus.APPROVED
        )
    )
    approved_days = approved_result.scalar() or 0.0
    
    # Get pending days
    pending_result = await db.execute(
        select(func.coalesce(func.sum(VacationRequest.days_count), 0.0)).where(
            VacationRequest.user_id == current_user.id,
            VacationRequest.vacation_period_id == period.id,
            VacationRequest.status == VacationStatus.PENDING
        )
    )
    pending_days = pending_result.scalar() or 0.0
    
    # Calculate totals
    if allocation:
        total_available = allocation.total_days + allocation.carried_over_days
    else:
        total_available = 25.0  # Default allocation
    
    remaining_days = total_available - approved_days
    
    return VacationBalanceResponse(
        vacation_period=period,
        allocation=allocation,
        total_available=total_available,
        approved_days=approved_days,
        pending_days=pending_days,
        remaining_days=remaining_days
    )


@router_balance.get("/vacation-balance/all", response_model=List[VacationBalanceResponse])
async def get_all_vacation_balances(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get the current user's vacation balance for all periods."""
    # Get all vacation periods for the company
    periods_result = await db.execute(
        select(VacationPeriod).where(
            VacationPeriod.company_id == current_user.company_id
        ).order_by(VacationPeriod.start_date.desc())
    )
    periods = periods_result.scalars().all()
    
    balances = []
    for period in periods:
        # Get allocation
        allocation_result = await db.execute(
            select(VacationAllocation).where(
                VacationAllocation.user_id == current_user.id,
                VacationAllocation.vacation_period_id == period.id
            )
        )
        allocation = allocation_result.scalar_one_or_none()
        
        # Get approved days
        approved_result = await db.execute(
            select(func.coalesce(func.sum(VacationRequest.days_count), 0.0)).where(
                VacationRequest.user_id == current_user.id,
                VacationRequest.vacation_period_id == period.id,
                VacationRequest.status == VacationStatus.APPROVED
            )
        )
        approved_days = approved_result.scalar() or 0.0
        
        # Get pending days
        pending_result = await db.execute(
            select(func.coalesce(func.sum(VacationRequest.days_count), 0.0)).where(
                VacationRequest.user_id == current_user.id,
                VacationRequest.vacation_period_id == period.id,
                VacationRequest.status == VacationStatus.PENDING
            )
        )
        pending_days = pending_result.scalar() or 0.0
        
        # Calculate totals
        if allocation:
            total_available = allocation.total_days + allocation.carried_over_days
        else:
            total_available = 25.0  # Default allocation
        
        remaining_days = total_available - approved_days
        
        balances.append(VacationBalanceResponse(
            vacation_period=period,
            allocation=allocation,
            total_available=total_available,
            approved_days=approved_days,
            pending_days=pending_days,
            remaining_days=remaining_days
        ))
    
    return balances

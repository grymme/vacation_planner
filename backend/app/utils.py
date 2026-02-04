"""Utility functions for the Vacation Planner application."""
from datetime import date, timedelta
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


def calculate_business_days(start_date: date, end_date: date) -> int:
    """Calculate the number of business days between two dates (inclusive).
    
    Args:
        start_date: The start date.
        end_date: The end date.
        
    Returns:
        The number of business days (weekdays) between the dates.
    """
    if start_date > end_date:
        return 0
    
    total_days = 0
    current_date = start_date
    while current_date <= end_date:
        # Skip weekends (Monday=0, Sunday=6)
        if current_date.weekday() < 5:  # 0-4 are weekdays
            total_days += 1
        current_date += timedelta(days=1)
    
    return total_days


def get_vacation_period_for_date(
    target_date: date, 
    periods: List["VacationPeriod"]
) -> Optional["VacationPeriod"]:
    """Find the vacation period that contains the given date.
    
    Args:
        target_date: The date to find a period for.
        periods: List of vacation periods to search.
        
    Returns:
        The VacationPeriod containing the date, or None if not found.
    """
    for period in periods:
        if period.start_date <= target_date <= period.end_date:
            return period
    return None


async def get_current_vacation_period(
    company_id: UUID, 
    db: AsyncSession
) -> Optional["VacationPeriod"]:
    """Get the current active vacation period for a company.
    
    Args:
        company_id: The company's UUID.
        db: The database session.
        
    Returns:
        The current VacationPeriod, or None if not found.
    """
    from app.models import VacationPeriod
    
    today = date.today()
    result = await db.execute(
        select(VacationPeriod).where(
            VacationPeriod.company_id == company_id,
            VacationPeriod.start_date <= today,
            VacationPeriod.end_date >= today
        )
    )
    return result.scalar_one_or_none()


async def get_default_vacation_period(
    company_id: UUID,
    db: AsyncSession
) -> Optional["VacationPeriod"]:
    """Get the default vacation period for a company.
    
    Args:
        company_id: The company's UUID.
        db: The database session.
        
    Returns:
        The default VacationPeriod, or None if not found.
    """
    from app.models import VacationPeriod
    
    result = await db.execute(
        select(VacationPeriod).where(
            VacationPeriod.company_id == company_id,
            VacationPeriod.is_default == True
        )
    )
    return result.scalar_one_or_none()

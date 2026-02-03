"""Audit logging utility."""
from typing import Optional
from uuid import UUID
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models import AuditLog, AuditAction, User


async def log_audit(
    db: AsyncSession,
    actor: Optional[User],
    action: AuditAction,
    resource_type: str,
    resource_id: Optional[UUID] = None,
    details: Optional[dict] = None,
    ip_address: Optional[str] = None
) -> AuditLog:
    """Log an audit action.
    
    Args:
        db: The database session.
        actor: The user performing the action (can be None for system actions).
        action: The action being performed.
        resource_type: The type of resource being acted upon (e.g., "user", "team", "vacation_request").
        resource_id: The ID of the resource being acted upon.
        details: Additional context about the action.
        ip_address: The IP address of the client.
        
    Returns:
        The created AuditLog object.
    """
    log = AuditLog(
        actor_id=actor.id if actor else None,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details,
        ip_address=ip_address
    )
    db.add(log)
    await db.commit()
    await db.refresh(log)
    return log


async def get_audit_logs(
    db: AsyncSession,
    actor_id: Optional[UUID] = None,
    action: Optional[AuditAction] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[UUID] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    skip: int = 0,
    limit: int = 100
) -> list[AuditLog]:
    """Get audit logs with optional filters.
    
    Args:
        db: The database session.
        actor_id: Filter by actor ID.
        action: Filter by action type.
        resource_type: Filter by resource type.
        resource_id: Filter by resource ID.
        start_date: Filter by start date.
        end_date: Filter by end date.
        skip: Number of records to skip.
        limit: Maximum number of records to return.
        
    Returns:
        List of AuditLog objects.
    """
    query = select(AuditLog)
    
    if actor_id:
        query = query.where(AuditLog.actor_id == actor_id)
    if action:
        query = query.where(AuditLog.action == action)
    if resource_type:
        query = query.where(AuditLog.resource_type == resource_type)
    if resource_id:
        query = query.where(AuditLog.resource_id == resource_id)
    if start_date:
        query = query.where(AuditLog.created_at >= start_date)
    if end_date:
        query = query.where(AuditLog.created_at <= end_date)
    
    query = query.offset(skip).limit(limit).order_by(AuditLog.created_at.desc())
    
    result = await db.execute(query)
    return result.scalars().all()

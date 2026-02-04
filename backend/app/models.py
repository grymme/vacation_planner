"""SQLAlchemy models for the Vacation Planner application."""
import uuid
from datetime import datetime, date
from enum import Enum
from typing import Optional

from sqlalchemy import (
    String, Text, DateTime, Date, ForeignKey, Integer, Enum as SQLEnum, 
    Boolean, Index, UniqueConstraint, JSON, func, TypeDecorator
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class UserRole(str, Enum):
    """User roles for RBAC."""
    ADMIN = "admin"
    MANAGER = "manager"
    USER = "user"


class VacationStatus(str, Enum):
    """Vacation request status."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class AuditAction(str, Enum):
    """Audit log actions."""
    USER_CREATED = "user_created"
    USER_UPDATED = "user_updated"
    USER_DEACTIVATED = "user_deactivated"
    USER_PASSWORD_RESET = "user_password_reset"
    TEAM_CREATED = "team_created"
    TEAM_UPDATED = "team_updated"
    TEAM_DELETED = "team_deleted"
    MANAGER_ASSIGNED = "manager_assigned"
    MANAGER_REMOVED = "manager_removed"
    VACATION_REQUEST_APPROVED = "vacation_request_approved"
    VACATION_REQUEST_REJECTED = "vacation_request_rejected"
    VACATION_REQUEST_MODIFIED = "vacation_request_modified"
    VACATION_REQUEST_CANCELLED = "vacation_request_cancelled"


# Custom UUID type that stores as string for SQLite compatibility
class StringUUID(TypeDecorator):
    """Custom type for storing UUIDs as strings (SQLite compatible)."""
    impl = String(36)
    cache_ok = True
    
    def process_bind_param(self, value, dialect):
        """Convert UUID to string for storage."""
        if value is None:
            return None
        return str(value)
    
    def process_result_value(self, value, dialect):
        """Convert string back to UUID."""
        if value is None:
            return None
        return uuid.UUID(value)


# =============================================================================
# Company Model - multi-tenant isolation
# =============================================================================
class Company(Base):
    """Company model for multi-tenant isolation."""
    __tablename__ = "companies"
    
    id: Mapped[uuid.UUID] = mapped_column(StringUUID, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    functions: Mapped[list["Function"]] = relationship("Function", back_populates="company", cascade="all, delete-orphan")
    teams: Mapped[list["Team"]] = relationship("Team", back_populates="company", cascade="all, delete-orphan")
    users: Mapped[list["User"]] = relationship("User", back_populates="company")
    
    # Indexes
    __table_args__ = (Index("idx_companies_name", "name"),)


# =============================================================================
# Function Model - department/functional area
# =============================================================================
class Function(Base):
    """Function/department model."""
    __tablename__ = "functions"
    
    id: Mapped[uuid.UUID] = mapped_column(StringUUID, primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(StringUUID, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    company: Mapped["Company"] = relationship("Company", back_populates="functions")
    users: Mapped[list["User"]] = relationship("User", back_populates="function")
    
    # Indexes
    __table_args__ = (Index("idx_functions_company_name", "company_id", "name"),)


# =============================================================================
# Team Model - grouping within company
# =============================================================================
class Team(Base):
    """Team model for grouping users within a company."""
    __tablename__ = "teams"
    
    id: Mapped[uuid.UUID] = mapped_column(StringUUID, primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(StringUUID, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    company: Mapped["Company"] = relationship("Company", back_populates="teams")
    memberships: Mapped[list["TeamMembership"]] = relationship("TeamMembership", back_populates="team", cascade="all, delete-orphan")
    manager_assignments: Mapped[list["TeamManagerAssignment"]] = relationship("TeamManagerAssignment", back_populates="team", cascade="all, delete-orphan")
    vacation_requests: Mapped[list["VacationRequest"]] = relationship("VacationRequest", back_populates="team")
    
    # Indexes
    __table_args__ = (Index("idx_teams_company_name", "company_id", "name"),)


# =============================================================================
# User Model - with role enum
# =============================================================================
class User(Base):
    """User model for authentication and authorization."""
    __tablename__ = "users"
    
    id: Mapped[uuid.UUID] = mapped_column(StringUUID, primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # Nullable until password set via invite
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    role: Mapped[UserRole] = mapped_column(SQLEnum(UserRole), default=UserRole.USER, nullable=False)
    company_id: Mapped[uuid.UUID] = mapped_column(StringUUID, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    function_id: Mapped[Optional[uuid.UUID]] = mapped_column(StringUUID, ForeignKey("functions.id", ondelete="SET NULL"), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)  # False until password set
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    company: Mapped["Company"] = relationship("Company", back_populates="users")
    function: Mapped[Optional["Function"]] = relationship("Function", back_populates="users")
    memberships: Mapped[list["TeamMembership"]] = relationship("TeamMembership", back_populates="user", cascade="all, delete-orphan")
    manager_assignments: Mapped[list["TeamManagerAssignment"]] = relationship("TeamManagerAssignment", back_populates="user", cascade="all, delete-orphan")
    vacation_requests: Mapped[list["VacationRequest"]] = relationship("VacationRequest", back_populates="user", foreign_keys="VacationRequest.user_id")
    approved_requests: Mapped[list["VacationRequest"]] = relationship("VacationRequest", back_populates="approver", foreign_keys="VacationRequest.approver_id")
    audit_logs: Mapped[list["AuditLog"]] = relationship("AuditLog", back_populates="actor")
    invite_tokens: Mapped[list["InviteToken"]] = relationship("InviteToken", back_populates="user", cascade="all, delete-orphan", foreign_keys="InviteToken.user_id")
    password_reset_tokens: Mapped[list["PasswordResetToken"]] = relationship("PasswordResetToken", back_populates="user", cascade="all, delete-orphan")
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index("idx_users_email", "email", unique=True),
        Index("idx_users_company", "company_id"),
        Index("idx_users_role", "role"),
    )
    
    @property
    def full_name(self) -> str:
        """Return user's full name."""
        return f"{self.first_name} {self.last_name}"
    
    def is_admin(self) -> bool:
        """Check if user is an admin."""
        return self.role == UserRole.ADMIN
    
    def is_manager(self) -> bool:
        """Check if user is a manager."""
        return self.role in (UserRole.ADMIN, UserRole.MANAGER)


# =============================================================================
# Team Membership - many-to-many between User and Team
# =============================================================================
class TeamMembership(Base):
    """Team membership junction table."""
    __tablename__ = "team_memberships"
    
    id: Mapped[uuid.UUID] = mapped_column(StringUUID, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(StringUUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    team_id: Mapped[uuid.UUID] = mapped_column(StringUUID, ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="memberships")
    team: Mapped["Team"] = relationship("Team", back_populates="memberships")
    
    # Unique constraint
    __table_args__ = (UniqueConstraint("user_id", "team_id", name="uq_user_team"),)


# =============================================================================
# Team Manager Assignment - manager to team scope
# =============================================================================
class TeamManagerAssignment(Base):
    """Team manager assignment junction table."""
    __tablename__ = "team_manager_assignments"
    
    id: Mapped[uuid.UUID] = mapped_column(StringUUID, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(StringUUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    team_id: Mapped[uuid.UUID] = mapped_column(StringUUID, ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="manager_assignments")
    team: Mapped["Team"] = relationship("Team", back_populates="manager_assignments")
    
    # Unique constraint
    __table_args__ = (UniqueConstraint("user_id", "team_id", name="uq_manager_team"),)


# =============================================================================
# Vacation Request Model
# =============================================================================
class VacationRequest(Base):
    """Vacation request model."""
    __tablename__ = "vacation_requests"
    
    id: Mapped[uuid.UUID] = mapped_column(StringUUID, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(StringUUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    team_id: Mapped[Optional[uuid.UUID]] = mapped_column(StringUUID, ForeignKey("teams.id", ondelete="SET NULL"), nullable=True)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    vacation_type: Mapped[str] = mapped_column(String(50), default="annual")  # annual, sick, personal, etc.
    status: Mapped[VacationStatus] = mapped_column(SQLEnum(VacationStatus), default=VacationStatus.PENDING, nullable=False)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    approver_id: Mapped[Optional[uuid.UUID]] = mapped_column(StringUUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="vacation_requests", foreign_keys=[user_id])
    approver: Mapped[Optional["User"]] = relationship("User", back_populates="approved_requests", foreign_keys=[approver_id])
    team: Mapped[Optional["Team"]] = relationship("Team", back_populates="vacation_requests")
    
    # Indexes
    __table_args__ = (
        Index("idx_vr_user_dates", "user_id", "start_date", "end_date"),
        Index("idx_vr_status", "status"),
        Index("idx_vr_team_dates", "team_id", "start_date", "end_date"),
        Index("idx_vr_approver", "approver_id"),
    )
    
    @property
    def is_pending(self) -> bool:
        """Check if request is pending."""
        return self.status == VacationStatus.PENDING
    
    @property
    def is_approved(self) -> bool:
        """Check if request is approved."""
        return self.status == VacationStatus.APPROVED
    
    @property
    def is_rejected(self) -> bool:
        """Check if request is rejected."""
        return self.status == VacationStatus.REJECTED


# =============================================================================
# Audit Log Model
# =============================================================================
class AuditLog(Base):
    """Audit log model for tracking admin/manager actions."""
    __tablename__ = "audit_logs"
    
    id: Mapped[uuid.UUID] = mapped_column(StringUUID, primary_key=True, default=uuid.uuid4)
    actor_id: Mapped[Optional[uuid.UUID]] = mapped_column(StringUUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action: Mapped[AuditAction] = mapped_column(SQLEnum(AuditAction), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g., "user", "team", "vacation_request"
    resource_id: Mapped[Optional[uuid.UUID]] = mapped_column(StringUUID, nullable=True)
    details: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # Additional context
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)  # IPv4 or IPv6
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    actor: Mapped[Optional["User"]] = relationship("User", back_populates="audit_logs")
    
    # Indexes
    __table_args__ = (
        Index("idx_audit_actor", "actor_id"),
        Index("idx_audit_action", "action"),
        Index("idx_audit_resource", "resource_type", "resource_id"),
        Index("idx_audit_created", "created_at"),
    )


# =============================================================================
# Invite Token Model - for invite/set-password flow
# =============================================================================
class InviteToken(Base):
    """Invite token model for invite/set-password flow."""
    __tablename__ = "invite_tokens"
    
    id: Mapped[uuid.UUID] = mapped_column(StringUUID, primary_key=True, default=uuid.uuid4)
    token: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(StringUUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(StringUUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="invite_tokens", foreign_keys=[user_id])
    creator: Mapped[Optional["User"]] = relationship("User", foreign_keys=[created_by])
    
    # Indexes
    __table_args__ = (Index("idx_invite_token", "token", unique=True),)


# =============================================================================
# Password Reset Token Model
# =============================================================================
class PasswordResetToken(Base):
    """Password reset token model."""
    __tablename__ = "password_reset_tokens"
    
    id: Mapped[uuid.UUID] = mapped_column(StringUUID, primary_key=True, default=uuid.uuid4)
    token: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(StringUUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="password_reset_tokens")
    
    # Indexes
    __table_args__ = (Index("idx_pw_reset_token", "token", unique=True),)


# =============================================================================
# Refresh Token Model - for token rotation
# =============================================================================
class RefreshToken(Base):
    """Refresh token model for secure session management with token rotation.
    
    Tracks all issued refresh tokens to enable revocation and rotation.
    When a new refresh token is issued, the old one is revoked.
    """
    __tablename__ = "refresh_tokens"
    
    id: Mapped[uuid.UUID] = mapped_column(StringUUID, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(StringUUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_jti: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)  # JWT ID for rotation tracking
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="refresh_tokens")
    
    # Indexes
    __table_args__ = (
        Index("idx_refresh_tokens_user", "user_id"),
        Index("idx_refresh_tokens_jti", "token_jti", unique=True),
        Index("idx_refresh_tokens_expires", "expires_at"),
    )
    
    @property
    def is_revoked(self) -> bool:
        """Check if the token has been revoked."""
        return self.revoked_at is not None
    
    @property
    def is_expired(self) -> bool:
        """Check if the token has expired."""
        return datetime.now(timezone.utc) > self.expires_at

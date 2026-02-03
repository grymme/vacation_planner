"""Pydantic schemas for API request/response validation."""
from datetime import date, datetime
from typing import Optional, Literal
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, ConfigDict, model_validator


# =============================================================================
# Enums (shared with models)
# =============================================================================
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


# =============================================================================
# Auth Schemas
# =============================================================================
class Token(BaseModel):
    """Token response schema."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    """Login request schema."""
    email: EmailStr
    password: str


class RefreshTokenRequest(BaseModel):
    """Token refresh request schema."""
    refresh_token: str


class SetPasswordRequest(BaseModel):
    """Set password from invite schema."""
    token: str
    password: str = Field(..., min_length=8)
    confirm_password: str


class PasswordResetRequest(BaseModel):
    """Password reset request schema (initiated by user)."""
    email: EmailStr


class PasswordResetConfirmRequest(BaseModel):
    """Password reset with token schema."""
    token: str
    password: str = Field(..., min_length=8)
    confirm_password: str


class InviteUserRequest(BaseModel):
    """Invite user schema (admin)."""
    email: EmailStr
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    role: UserRole
    company_id: UUID
    function_id: Optional[UUID] = None
    team_ids: list[UUID] = []


class InviteResponse(BaseModel):
    """Invite response schema."""
    message: str
    user_id: UUID
    invite_token: str
    invite_link: str


# =============================================================================
# User Schemas
# =============================================================================
class UserBase(BaseModel):
    """Base user schema."""
    email: EmailStr
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)


class UserResponse(BaseModel):
    """User response schema."""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    email: str
    first_name: str
    last_name: str
    role: UserRole
    company_id: UUID
    function_id: Optional[UUID]
    is_active: bool
    created_at: datetime


class UserCreate(BaseModel):
    """User create schema (for seed script)."""
    email: EmailStr
    password: str = Field(..., min_length=8)
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    role: UserRole
    company_id: UUID
    function_id: Optional[UUID] = None


class UserUpdate(BaseModel):
    """User update schema."""
    email: Optional[EmailStr] = None
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None


# =============================================================================
# Company Schemas
# =============================================================================
class CompanyCreate(BaseModel):
    """Company create schema."""
    name: str = Field(..., min_length=1, max_length=255)


class CompanyResponse(BaseModel):
    """Company response schema."""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    name: str
    created_at: datetime


# =============================================================================
# Function Schemas
# =============================================================================
class FunctionCreate(BaseModel):
    """Function create schema."""
    company_id: UUID
    name: str = Field(..., min_length=1, max_length=255)


class FunctionResponse(BaseModel):
    """Function response schema."""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    company_id: UUID
    name: str
    created_at: datetime


# =============================================================================
# Team Schemas
# =============================================================================
class TeamCreate(BaseModel):
    """Team create schema."""
    company_id: UUID
    name: str = Field(..., min_length=1, max_length=255)


class TeamResponse(BaseModel):
    """Team response schema."""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    company_id: UUID
    name: str
    created_at: datetime


class TeamWithMembersResponse(BaseModel):
    """Team with members response schema."""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    company_id: UUID
    name: str
    members: list["UserResponse"]
    created_at: datetime


# =============================================================================
# Vacation Request Schemas
# =============================================================================
class VacationRequestCreate(BaseModel):
    """Vacation request create schema."""
    start_date: date
    end_date: date
    vacation_type: str = "annual"
    reason: Optional[str] = None
    team_id: Optional[UUID] = None
    
    @model_validator(mode='before')
    @classmethod
    def validate_dates(cls, data):
        if isinstance(data, dict):
            return data
        if data.end_date < data.start_date:
            raise ValueError("end_date must be after or equal to start_date")
        return data


class VacationRequestUpdate(BaseModel):
    """Vacation request update schema (user can only cancel/update draft)."""
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    vacation_type: Optional[str] = None
    reason: Optional[str] = None


class VacationRequestAction(BaseModel):
    """Vacation request approve/reject schema."""
    action: Literal["approve", "reject"]
    comment: Optional[str] = None


class VacationRequestResponse(BaseModel):
    """Vacation request response schema."""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    user_id: UUID
    team_id: Optional[UUID]
    start_date: date
    end_date: date
    vacation_type: str
    status: VacationStatus
    reason: Optional[str]
    approver_id: Optional[UUID]
    approved_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    user: Optional[UserResponse] = None


# =============================================================================
# Audit Log Schemas
# =============================================================================
class AuditLogResponse(BaseModel):
    """Audit log response schema."""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    actor_id: Optional[UUID]
    action: str
    resource_type: str
    resource_id: Optional[UUID]
    details: Optional[dict]
    ip_address: Optional[str]
    created_at: datetime


# =============================================================================
# Health Check Schemas
# =============================================================================
class HealthCheck(BaseModel):
    """Health check response schema."""
    status: str
    database: str
    timestamp: datetime


# =============================================================================
# Error Schemas
# =============================================================================
class ErrorResponse(BaseModel):
    """Error response schema."""
    detail: str
    error_code: Optional[str] = None


class ValidationErrorResponse(BaseModel):
    """Validation error response schema."""
    detail: list[dict]


# =============================================================================
# Message Schemas
# =============================================================================
class MessageResponse(BaseModel):
    """Message response schema."""
    message: str

"""Pydantic schemas for API request/response validation."""
import re
from datetime import date, datetime
from typing import Optional, Literal
from enum import Enum
from uuid import UUID

import bleach
from pydantic import BaseModel, EmailStr, Field, ConfigDict, model_validator, field_validator


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


# Password complexity validation
def validate_password_complexity(password: str) -> str:
    """Validate password meets complexity requirements.
    
    Requirements:
    - Minimum 12 characters
    - At least 1 uppercase letter
    - At least 1 lowercase letter
    - At least 1 number
    - At least 1 special character
    """
    if len(password) < 12:
        raise ValueError('Password must be at least 12 characters')
    if not re.search(r'[A-Z]', password):
        raise ValueError('Password must contain at least one uppercase letter')
    if not re.search(r'[a-z]', password):
        raise ValueError('Password must contain at least one lowercase letter')
    if not re.search(r'[0-9]', password):
        raise ValueError('Password must contain at least one number')
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        raise ValueError('Password must contain at least one special character')
    return password


class SetPasswordRequest(BaseModel):
    """Set password from invite schema."""
    token: str
    password: str = Field(..., min_length=12)
    confirm_password: str
    
    @field_validator('password')
    @classmethod
    def password_complexity(cls, v: str) -> str:
        return validate_password_complexity(v)
    
    @model_validator(mode='after')
    def passwords_match(self):
        if self.password != self.confirm_password:
            raise ValueError('Passwords do not match')
        return self


class PasswordResetRequest(BaseModel):
    """Password reset request schema (initiated by user)."""
    email: EmailStr


class PasswordResetConfirmRequest(BaseModel):
    """Password reset with token schema."""
    token: str
    password: str = Field(..., min_length=12)
    confirm_password: str
    
    @field_validator('password')
    @classmethod
    def password_complexity(cls, v: str) -> str:
        return validate_password_complexity(v)
    
    @model_validator(mode='after')
    def passwords_match(self):
        if self.password != self.confirm_password:
            raise ValueError('Passwords do not match')
        return self


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
    password: str = Field(..., min_length=12)
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    role: UserRole
    company_id: UUID
    function_id: Optional[UUID] = None
    
    @field_validator('password')
    @classmethod
    def password_complexity(cls, v: str) -> str:
        return validate_password_complexity(v)


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
# VacationPeriod Schemas
# =============================================================================
class VacationPeriodCreate(BaseModel):
    """Vacation period create schema."""
    company_id: UUID
    name: str = Field(..., min_length=1, max_length=100)
    start_date: date
    end_date: date
    is_default: bool = False
    
    @model_validator(mode='after')
    def validate_dates(self):
        if self.end_date <= self.start_date:
            raise ValueError('end_date must be after start_date')
        return self


class VacationPeriodUpdate(BaseModel):
    """Vacation period update schema."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_default: Optional[bool] = None


class VacationPeriodResponse(BaseModel):
    """Vacation period response schema."""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    company_id: UUID
    name: str
    start_date: date
    end_date: date
    is_default: bool
    created_at: datetime
    updated_at: datetime


# =============================================================================
# VacationAllocation Schemas
# =============================================================================
class VacationAllocationCreate(BaseModel):
    """Vacation allocation create schema."""
    user_id: UUID
    vacation_period_id: UUID
    total_days: float = 25.0
    carried_over_days: float = 0.0


class VacationAllocationUpdate(BaseModel):
    """Vacation allocation update schema."""
    total_days: Optional[float] = None
    carried_over_days: Optional[float] = None


class VacationAllocationResponse(BaseModel):
    """Vacation allocation response schema."""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    user_id: UUID
    vacation_period_id: UUID
    total_days: float
    carried_over_days: float
    days_used: float
    remaining_days: float  # Computed property from model
    created_at: datetime
    updated_at: datetime


class VacationBalanceResponse(BaseModel):
    """Vacation balance response for users."""
    vacation_period: VacationPeriodResponse
    allocation: Optional[VacationAllocationResponse] = None
    total_available: float
    approved_days: float
    pending_days: float
    remaining_days: float


# =============================================================================
# Input Sanitization Utilities
# =============================================================================
def sanitize_input(text: str) -> str:
    """Sanitize user input to prevent XSS attacks.
    
    Args:
        text: The input text to sanitize.
        
    Returns:
        Sanitized text with all HTML tags stripped.
    """
    if not text:
        return text
    return bleach.clean(
        text,
        tags=[],  # No HTML tags allowed
        attributes={},
        strip=True
    )


def sanitize_optional_input(text: Optional[str]) -> Optional[str]:
    """Sanitize optional input text.
    
    Args:
        text: The optional input text to sanitize.
        
    Returns:
        Sanitized text or None.
    """
    if text is None:
        return None
    return sanitize_input(text)


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
    
    @field_validator('vacation_type', 'reason')
    @classmethod
    def sanitize_text_fields(cls, v: Optional[str]) -> Optional[str]:
        return sanitize_optional_input(v)
    
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
    
    @field_validator('vacation_type', 'reason')
    @classmethod
    def sanitize_text_fields(cls, v: Optional[str]) -> Optional[str]:
        return sanitize_optional_input(v)


class VacationRequestAction(BaseModel):
    """Vacation request approve/reject schema."""
    action: Literal["approve", "reject"]
    comment: Optional[str] = None
    
    @field_validator('comment')
    @classmethod
    def sanitize_comment(cls, v: Optional[str]) -> Optional[str]:
        return sanitize_optional_input(v)


class VacationRequestResponse(BaseModel):
    """Vacation request response schema."""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    user_id: UUID
    team_id: Optional[UUID]
    vacation_period_id: Optional[UUID]
    start_date: date
    end_date: date
    vacation_type: str
    days_count: Optional[float]
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

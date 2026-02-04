"""Pytest configuration and fixtures for vacation planner tests."""
import asyncio
import os
from datetime import datetime, timedelta, timezone
from typing import AsyncGenerator
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import (
    Company, Function, Team, User, UserRole, TeamMembership, 
    TeamManagerAssignment, VacationRequest, VacationStatus, InviteToken,
    VacationPeriod, VacationAllocation
)
from app.auth import hash_password, create_access_token

# Set test environment
os.environ["JWT_SECRET"] = "test-secret-key-for-testing-only"
os.environ["ENVIRONMENT"] = "testing"

# Module-level storage
_engine = None
_session_factory = None


@pytest_asyncio.fixture
async def db_session():
    """Create database engine, tables, and session for tests."""
    global _engine, _session_factory
    
    # Create engine if not exists
    if _engine is None:
        _engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        # Create tables immediately
        async with _engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        # Create session factory
        _session_factory = async_sessionmaker(
            _engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
    
    # Use the session factory to create a session
    async with _session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def client(db_session: AsyncSession):
    """Create a test client using the database session."""
    async def override_get_db():
        async with _session_factory() as session:
            yield session
    
    app.dependency_overrides[get_db] = override_get_db
    
    # Create a test app without middleware for proper testing
    from fastapi import FastAPI
    from app.routers import auth, users, vacation_requests, admin, manager, exports, vacation_periods
    
    test_app = FastAPI(
        title="Vacation Planner API (Test)",
        version="1.0.0",
    )
    
    # Include all routers
    test_app.include_router(auth.router, prefix="/api/v1")
    test_app.include_router(users.router, prefix="/api/v1")
    test_app.include_router(vacation_requests.router, prefix="/api/v1")
    test_app.include_router(admin.router, prefix="/api/v1")
    test_app.include_router(manager.router, prefix="/api/v1")
    test_app.include_router(exports.router, prefix="/api/v1")
    # Include vacation periods router (has prefix built-in)
    test_app.include_router(vacation_periods.router, prefix="/api/v1")
    test_app.include_router(vacation_periods.router_allocations, prefix="/api/v1")
    test_app.include_router(vacation_periods.router_balance, prefix="/api/v1")
    
    # Add health check
    @test_app.get("/health")
    async def health_check():
        return {"status": "healthy"}
    
    @test_app.get("/")
    async def root():
        return {"name": "Vacation Planner API (Test)"}
    
    test_app.dependency_overrides[get_db] = override_get_db
    
    async with AsyncClient(
        transport=ASGITransport(app=test_app),
        base_url="http://test"
    ) as ac:
        yield ac
    
    app.dependency_overrides.clear()


# =============================================================================
# Company Fixtures
# =============================================================================
@pytest_asyncio.fixture
async def test_company(db_session: AsyncSession) -> Company:
    """Create a test company."""
    company = Company(name=f"Test Company {uuid4()}")
    db_session.add(company)
    await db_session.commit()
    await db_session.refresh(company)
    return company


@pytest_asyncio.fixture
async def test_company2(db_session: AsyncSession) -> Company:
    """Create a second test company for isolation testing."""
    company = Company(name=f"Test Company 2 {uuid4()}")
    db_session.add(company)
    await db_session.commit()
    await db_session.refresh(company)
    return company


# =============================================================================
# Function Fixtures
# =============================================================================
@pytest_asyncio.fixture
async def test_function(db_session: AsyncSession, test_company: Company) -> Function:
    """Create a test function/department."""
    func = Function(name="Test Function", company_id=test_company.id)
    db_session.add(func)
    await db_session.commit()
    await db_session.refresh(func)
    return func


@pytest_asyncio.fixture
async def test_function2(db_session: AsyncSession, test_company: Company) -> Function:
    """Create a second test function/department."""
    func = Function(name="Test Function 2", company_id=test_company.id)
    db_session.add(func)
    await db_session.commit()
    await db_session.refresh(func)
    return func


# =============================================================================
# Team Fixtures
# =============================================================================
@pytest_asyncio.fixture
async def test_team(db_session: AsyncSession, test_company: Company) -> Team:
    """Create a test team."""
    team = Team(name="Test Team", company_id=test_company.id)
    db_session.add(team)
    await db_session.commit()
    await db_session.refresh(team)
    return team


@pytest_asyncio.fixture
async def test_team2(db_session: AsyncSession, test_company: Company) -> Team:
    """Create a second test team."""
    team = Team(name="Test Team 2", company_id=test_company.id)
    db_session.add(team)
    await db_session.commit()
    await db_session.refresh(team)
    return team


# =============================================================================
# User Fixtures
# =============================================================================
@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession, test_company: Company) -> User:
    """Create an admin user."""
    user = User(
        email=f"admin_{uuid4().hex[:8]}@test.com",
        hashed_password=hash_password("adminpassword123"),
        first_name="Admin",
        last_name="User",
        role=UserRole.ADMIN,
        company_id=test_company.id,
        is_active=True
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def manager_user(db_session: AsyncSession, test_company: Company, test_team: Team) -> User:
    """Create a manager user."""
    user = User(
        email=f"manager_{uuid4().hex[:8]}@test.com",
        hashed_password=hash_password("managerpassword123"),
        first_name="Manager",
        last_name="User",
        role=UserRole.MANAGER,
        company_id=test_company.id,
        is_active=True
    )
    db_session.add(user)
    await db_session.flush()
    
    # Assign as team manager
    assignment = TeamManagerAssignment(user_id=user.id, team_id=test_team.id)
    db_session.add(assignment)
    
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def manager_user2(db_session: AsyncSession, test_company: Company, test_team2: Team) -> User:
    """Create a second manager user for different team."""
    user = User(
        email=f"manager2_{uuid4().hex[:8]}@test.com",
        hashed_password=hash_password("managerpassword123"),
        first_name="Manager2",
        last_name="User",
        role=UserRole.MANAGER,
        company_id=test_company.id,
        is_active=True
    )
    db_session.add(user)
    await db_session.flush()
    
    # Assign as team manager
    assignment = TeamManagerAssignment(user_id=user.id, team_id=test_team2.id)
    db_session.add(assignment)
    
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def regular_user(db_session: AsyncSession, test_company: Company, test_team: Team) -> User:
    """Create a regular user."""
    user = User(
        email=f"user_{uuid4().hex[:8]}@test.com",
        hashed_password=hash_password("userpassword123"),
        first_name="Regular",
        last_name="User",
        role=UserRole.USER,
        company_id=test_company.id,
        is_active=True
    )
    db_session.add(user)
    await db_session.flush()
    
    # Add to team
    membership = TeamMembership(user_id=user.id, team_id=test_team.id)
    db_session.add(membership)
    
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def regular_user2(db_session: AsyncSession, test_company: Company, test_team2: Team) -> User:
    """Create a second regular user in different team."""
    user = User(
        email=f"user2_{uuid4().hex[:8]}@test.com",
        hashed_password=hash_password("userpassword123"),
        first_name="Regular2",
        last_name="User",
        role=UserRole.USER,
        company_id=test_company.id,
        is_active=True
    )
    db_session.add(user)
    await db_session.flush()
    
    # Add to team
    membership = TeamMembership(user_id=user.id, team_id=test_team2.id)
    db_session.add(membership)
    
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def user_from_other_company(db_session: AsyncSession, test_company2: Company) -> User:
    """Create a user from a different company for isolation testing."""
    user = User(
        email=f"other_company_{uuid4().hex[:8]}@test.com",
        hashed_password=hash_password("otherpassword123"),
        first_name="Other",
        last_name="Company",
        role=UserRole.USER,
        company_id=test_company2.id,
        is_active=True
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def inactive_user(db_session: AsyncSession, test_company: Company) -> User:
    """Create an inactive user."""
    user = User(
        email=f"inactive_{uuid4().hex[:8]}@test.com",
        hashed_password=hash_password("inactivepassword123"),
        first_name="Inactive",
        last_name="User",
        role=UserRole.USER,
        company_id=test_company.id,
        is_active=False
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def invited_user(db_session: AsyncSession, test_company: Company, admin_user: User) -> User:
    """Create a user invited but not yet activated."""
    # Use unique token for each test
    unique_token = f"test-invite-token-{uuid4().hex[:8]}"
    user = User(
        email=f"invited_{uuid4().hex[:8]}@test.com",
        hashed_password=None,
        first_name="Invited",
        last_name="User",
        role=UserRole.USER,
        company_id=test_company.id,
        is_active=False
    )
    db_session.add(user)
    await db_session.flush()
    
    # Create invite token
    invite_token = InviteToken(
        token=unique_token,
        user_id=user.id,
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        created_by=admin_user.id
    )
    db_session.add(invite_token)
    
    await db_session.commit()
    await db_session.refresh(user)
    return user


# =============================================================================
# Vacation Request Fixtures
# =============================================================================
@pytest_asyncio.fixture
async def vacation_request_pending(
    db_session: AsyncSession, 
    regular_user: User, 
    test_team: Team
) -> VacationRequest:
    """Create a pending vacation request."""
    vr = VacationRequest(
        user_id=regular_user.id,
        team_id=test_team.id,
        start_date=datetime(2024, 6, 1, tzinfo=timezone.utc).date(),
        end_date=datetime(2024, 6, 5, tzinfo=timezone.utc).date(),
        vacation_type="annual",
        status=VacationStatus.PENDING,
        reason="Summer vacation"
    )
    db_session.add(vr)
    await db_session.commit()
    await db_session.refresh(vr)
    return vr


@pytest_asyncio.fixture
async def vacation_request_approved(
    db_session: AsyncSession, 
    regular_user: User, 
    test_team: Team,
    manager_user: User
) -> VacationRequest:
    """Create an approved vacation request."""
    vr = VacationRequest(
        user_id=regular_user.id,
        team_id=test_team.id,
        start_date=datetime(2024, 7, 1, tzinfo=timezone.utc).date(),
        end_date=datetime(2024, 7, 10, tzinfo=timezone.utc).date(),
        vacation_type="annual",
        status=VacationStatus.APPROVED,
        reason="Holiday trip",
        approver_id=manager_user.id,
        approved_at=datetime.now(timezone.utc)
    )
    db_session.add(vr)
    await db_session.commit()
    await db_session.refresh(vr)
    return vr


@pytest_asyncio.fixture
async def vacation_request_rejected(
    db_session: AsyncSession, 
    regular_user: User, 
    test_team: Team,
    manager_user: User
) -> VacationRequest:
    """Create a rejected vacation request."""
    vr = VacationRequest(
        user_id=regular_user.id,
        team_id=test_team.id,
        start_date=datetime(2024, 8, 1, tzinfo=timezone.utc).date(),
        end_date=datetime(2024, 8, 5, tzinfo=timezone.utc).date(),
        vacation_type="sick",
        status=VacationStatus.REJECTED,
        reason="Not enough notice",
        approver_id=manager_user.id,
        approved_at=datetime.now(timezone.utc)
    )
    db_session.add(vr)
    await db_session.commit()
    await db_session.refresh(vr)
    return vr


@pytest_asyncio.fixture
async def vacation_request_cancelled(
    db_session: AsyncSession, 
    regular_user: User, 
    test_team: Team
) -> VacationRequest:
    """Create a cancelled vacation request."""
    vr = VacationRequest(
        user_id=regular_user.id,
        team_id=test_team.id,
        start_date=datetime(2024, 9, 1, tzinfo=timezone.utc).date(),
        end_date=datetime(2024, 9, 3, tzinfo=timezone.utc).date(),
        vacation_type="personal",
        status=VacationStatus.CANCELLED,
        reason="Plans changed"
    )
    db_session.add(vr)
    await db_session.commit()
    await db_session.refresh(vr)
    return vr


# =============================================================================
# Authentication Header Fixtures
# =============================================================================
@pytest_asyncio.fixture
async def admin_auth_headers(admin_user: User) -> dict:
    """Create authorization headers for admin user."""
    token = create_access_token(
        user_id=admin_user.id,
        email=admin_user.email,
        role=admin_user.role,
        company_id=admin_user.company_id
    )
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def manager_auth_headers(manager_user: User) -> dict:
    """Create authorization headers for manager user."""
    token = create_access_token(
        user_id=manager_user.id,
        email=manager_user.email,
        role=manager_user.role,
        company_id=manager_user.company_id
    )
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def user_auth_headers(regular_user: User) -> dict:
    """Create authorization headers for regular user."""
    token = create_access_token(
        user_id=regular_user.id,
        email=regular_user.email,
        role=regular_user.role,
        company_id=regular_user.company_id
    )
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def user2_auth_headers(regular_user2: User) -> dict:
    """Create authorization headers for second regular user."""
    token = create_access_token(
        user_id=regular_user2.id,
        email=regular_user2.email,
        role=regular_user2.role,
        company_id=regular_user2.company_id
    )
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def other_company_auth_headers(user_from_other_company: User) -> dict:
    """Create authorization headers for user from other company."""
    token = create_access_token(
        user_id=user_from_other_company.id,
        email=user_from_other_company.email,
        role=user_from_other_company.role,
        company_id=user_from_other_company.company_id
    )
    return {"Authorization": f"Bearer {token}"}


# =============================================================================
# Vacation Period Fixtures
# =============================================================================
@pytest_asyncio.fixture
async def test_vacation_period(db_session: AsyncSession, test_company: Company) -> VacationPeriod:
    """Create a test vacation period."""
    from datetime import date
    period = VacationPeriod(
        company_id=test_company.id,
        name="2024-2025",
        start_date=date(2024, 4, 1),
        end_date=date(2025, 3, 31),
        is_default=True
    )
    db_session.add(period)
    await db_session.commit()
    await db_session.refresh(period)
    return period


@pytest_asyncio.fixture
async def test_vacation_period2(db_session: AsyncSession, test_company: Company) -> VacationPeriod:
    """Create a second test vacation period."""
    from datetime import date
    period = VacationPeriod(
        company_id=test_company.id,
        name="2025-2026",
        start_date=date(2025, 4, 1),
        end_date=date(2026, 3, 31),
        is_default=False
    )
    db_session.add(period)
    await db_session.commit()
    await db_session.refresh(period)
    return period


@pytest_asyncio.fixture
async def test_vacation_period_other_company(db_session: AsyncSession, test_company2: Company) -> VacationPeriod:
    """Create a vacation period for another company."""
    from datetime import date
    period = VacationPeriod(
        company_id=test_company2.id,
        name="2024-2025",
        start_date=date(2024, 4, 1),
        end_date=date(2025, 3, 31),
        is_default=True
    )
    db_session.add(period)
    await db_session.commit()
    await db_session.refresh(period)
    return period


# =============================================================================
# Vacation Allocation Fixtures
# =============================================================================
@pytest_asyncio.fixture
async def test_allocation(db_session: AsyncSession, regular_user: User, test_vacation_period: VacationPeriod) -> VacationAllocation:
    """Create a test vacation allocation."""
    allocation = VacationAllocation(
        user_id=regular_user.id,
        vacation_period_id=test_vacation_period.id,
        total_days=25.0,
        carried_over_days=5.0,
        days_used=0.0
    )
    db_session.add(allocation)
    await db_session.commit()
    await db_session.refresh(allocation)
    return allocation


@pytest_asyncio.fixture
async def test_allocation_with_used_days(db_session: AsyncSession, regular_user: User, test_vacation_period: VacationPeriod) -> VacationAllocation:
    """Create a test vacation allocation with some days already used."""
    allocation = VacationAllocation(
        user_id=regular_user.id,
        vacation_period_id=test_vacation_period.id,
        total_days=25.0,
        carried_over_days=5.0,
        days_used=10.0
    )
    db_session.add(allocation)
    await db_session.commit()
    await db_session.refresh(allocation)
    return allocation


@pytest_asyncio.fixture
async def test_allocation_for_user2(db_session: AsyncSession, regular_user2: User, test_vacation_period: VacationPeriod) -> VacationAllocation:
    """Create a test vacation allocation for user2."""
    allocation = VacationAllocation(
        user_id=regular_user2.id,
        vacation_period_id=test_vacation_period.id,
        total_days=25.0,
        carried_over_days=0.0,
        days_used=0.0
    )
    db_session.add(allocation)
    await db_session.commit()
    await db_session.refresh(allocation)
    return allocation

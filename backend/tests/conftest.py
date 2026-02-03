"""Pytest configuration and fixtures for vacation planner tests."""
import asyncio
import os
from datetime import datetime, timezone
from typing import AsyncGenerator, Generator
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy import event

from app.database import Base, get_db
from app.main import app
from app.models import (
    Company, Function, Team, User, UserRole, TeamMembership, 
    TeamManagerAssignment, VacationRequest, VacationStatus, InviteToken
)
from app.auth import hash_password, create_access_token

# Set test environment
os.environ["JWT_SECRET"] = "test-secret-key-for-testing-only"
os.environ["ENVIRONMENT"] = "testing"


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# SQLite UUID handler
@event.listens_for(Base.metadata, "before_create")
def receive_before_create(target, connection, **kw):
    """Handle UUID types for SQLite."""
    pass


@pytest_asyncio.fixture
async def async_engine():
    """Create async SQLite engine for testing with UUID support."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool
    from app.database import Base
    
    # Create async engine with proper UUID handling
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(async_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    async_session_maker = async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    async with async_session_maker() as session:
        yield session


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create a test client with database session override."""
    async_session_maker = async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    async def override_get_db():
        async with async_session_maker() as session:
            yield session
    
    app.dependency_overrides[get_db] = override_get_db
    
    async with AsyncClient(
        transport=ASGITransport(app=app),
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
        email="admin@test.com",
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
        email="manager@test.com",
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
        email="manager2@test.com",
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
        email="user@test.com",
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
        email="user2@test.com",
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
async def inactive_user(db_session: AsyncSession, test_company: Company) -> User:
    """Create an inactive user."""
    user = User(
        email="inactive@test.com",
        hashed_password=None,
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
    user = User(
        email="invited@test.com",
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
        token="test-invite-token",
        user_id=user.id,
        expires_at=datetime.now(timezone.utc) + timezone.timedelta(days=7),
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

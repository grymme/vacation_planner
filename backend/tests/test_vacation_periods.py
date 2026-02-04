"""Comprehensive API tests for vacation periods and allocations functionality."""
import pytest
from datetime import date, timedelta
from uuid import uuid4

from app.models import VacationStatus


# =============================================================================
# Helper function to add trailing slashes to URLs
# =============================================================================
def ensure_trailing_slash(url: str) -> str:
    """Ensure URL has a trailing slash."""
    if not url.endswith("/"):
        url += "/"
    return url


# =============================================================================
# Vacation Period CRUD Tests (Admin Only)
# =============================================================================
class TestVacationPeriodCRUD:
    """Tests for vacation period CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_vacation_period_as_admin(
        self, client, admin_user, admin_auth_headers, test_company
    ):
        """Test that admins can create vacation periods."""
        response = await client.post(
            ensure_trailing_slash("/api/v1/admin/vacation-periods"),
            json={
                "company_id": str(test_company.id),
                "name": "2024-2025",
                "start_date": "2024-04-01",
                "end_date": "2025-03-31",
                "is_default": True
            },
            headers=admin_auth_headers
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "2024-2025"
        assert data["is_default"] == True
        assert data["company_id"] == str(test_company.id)

    @pytest.mark.asyncio
    async def test_create_vacation_period_non_admin_forbidden(
        self, client, regular_user, user_auth_headers, test_company
    ):
        """Test that non-admins cannot create periods."""
        response = await client.post(
            ensure_trailing_slash("/api/v1/admin/vacation-periods"),
            json={
                "company_id": str(test_company.id),
                "name": "2024-2025",
                "start_date": "2024-04-01",
                "end_date": "2025-03-31"
            },
            headers=user_auth_headers
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_create_vacation_period_manager_forbidden(
        self, client, manager_user, manager_auth_headers, test_company
    ):
        """Test that managers cannot create periods."""
        response = await client.post(
            ensure_trailing_slash("/api/v1/admin/vacation-periods"),
            json={
                "company_id": str(test_company.id),
                "name": "2024-2025",
                "start_date": "2024-04-01",
                "end_date": "2025-03-31"
            },
            headers=manager_auth_headers
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_create_vacation_period_invalid_dates(
        self, client, admin_user, admin_auth_headers, test_company
    ):
        """Test that creating period with invalid dates fails."""
        response = await client.post(
            ensure_trailing_slash("/api/v1/admin/vacation-periods"),
            json={
                "company_id": str(test_company.id),
                "name": "2024-2025",
                "start_date": "2025-04-01",
                "end_date": "2024-03-31"
            },
            headers=admin_auth_headers
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_vacation_period_overlapping_fails(
        self, client, admin_user, admin_auth_headers, test_company, test_vacation_period
    ):
        """Test that overlapping periods are rejected."""
        response = await client.post(
            ensure_trailing_slash("/api/v1/admin/vacation-periods"),
            json={
                "company_id": str(test_company.id),
                "name": "2024-2025-overlap",
                "start_date": "2024-10-01",
                "end_date": "2025-09-30"
            },
            headers=admin_auth_headers
        )
        assert response.status_code == 400
        assert "overlapping" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_get_vacation_periods(
        self, client, admin_user, admin_auth_headers, test_company, test_vacation_period
    ):
        """Test listing vacation periods."""
        response = await client.get(
            ensure_trailing_slash("/api/v1/admin/vacation-periods"),
            headers=admin_auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    @pytest.mark.asyncio
    async def test_get_vacation_periods_non_admin_forbidden(
        self, client, regular_user, user_auth_headers
    ):
        """Test that non-admins cannot list periods."""
        response = await client.get(
            ensure_trailing_slash("/api/v1/admin/vacation-periods"),
            headers=user_auth_headers
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_get_vacation_period_by_id(
        self, client, admin_user, admin_auth_headers, test_vacation_period
    ):
        """Test getting a specific vacation period."""
        response = await client.get(
            f"/api/v1/admin/vacation-periods/{test_vacation_period.id}",
            headers=admin_auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_vacation_period.id)

    @pytest.mark.asyncio
    async def test_get_vacation_period_not_found(
        self, client, admin_user, admin_auth_headers
    ):
        """Test getting nonexistent vacation period."""
        fake_id = str(uuid4())
        response = await client.get(
            f"/api/v1/admin/vacation-periods/{fake_id}",
            headers=admin_auth_headers
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_vacation_period(
        self, client, admin_user, admin_auth_headers, test_vacation_period
    ):
        """Test updating a vacation period."""
        response = await client.put(
            f"/api/v1/admin/vacation-periods/{test_vacation_period.id}",
            json={"name": "2025-2026"},
            headers=admin_auth_headers
        )
        assert response.status_code == 200
        assert response.json()["name"] == "2025-2026"

    @pytest.mark.asyncio
    async def test_update_vacation_period_set_default(
        self, client, admin_user, admin_auth_headers, test_vacation_period, test_vacation_period2
    ):
        """Test setting a period as default unsets other defaults."""
        response = await client.put(
            f"/api/v1/admin/vacation-periods/{test_vacation_period2.id}",
            json={"is_default": True},
            headers=admin_auth_headers
        )
        assert response.status_code == 200
        assert response.json()["is_default"] == True

    @pytest.mark.asyncio
    async def test_delete_vacation_period(
        self, client, admin_user, admin_auth_headers, test_vacation_period2
    ):
        """Test deleting a vacation period."""
        response = await client.delete(
            f"/api/v1/admin/vacation-periods/{test_vacation_period2.id}",
            headers=admin_auth_headers
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_delete_vacation_period_with_requests_fails(
        self, client, admin_user, admin_auth_headers, test_vacation_period, db_session, regular_user, test_team
    ):
        """Test that deleting period with requests fails."""
        from app.models import VacationRequest
        
        vr = VacationRequest(
            user_id=regular_user.id,
            team_id=test_team.id,
            start_date=date(2024, 6, 1),
            end_date=date(2024, 6, 5),
            vacation_type="annual",
            status=VacationStatus.PENDING,
            vacation_period_id=test_vacation_period.id
        )
        db_session.add(vr)
        await db_session.commit()
        
        response = await client.delete(
            f"/api/v1/admin/vacation-periods/{test_vacation_period.id}",
            headers=admin_auth_headers
        )
        assert response.status_code == 400
        assert "requests" in response.json()["detail"].lower()


# =============================================================================
# Vacation Allocation CRUD Tests
# =============================================================================
class TestVacationAllocationCRUD:
    """Tests for vacation allocation CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_allocation(
        self, client, admin_user, admin_auth_headers, regular_user, test_vacation_period
    ):
        """Test creating a vacation allocation."""
        response = await client.post(
            ensure_trailing_slash("/api/v1/admin/allocations"),
            json={
                "user_id": str(regular_user.id),
                "vacation_period_id": str(test_vacation_period.id),
                "total_days": 25.0,
                "carried_over_days": 5.0
            },
            headers=admin_auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total_days"] == 25.0
        assert data["carried_over_days"] == 5.0

    @pytest.mark.asyncio
    async def test_create_duplicate_allocation_fails(
        self, client, admin_user, admin_auth_headers, regular_user, test_vacation_period, test_allocation
    ):
        """Test that duplicate allocations are rejected."""
        response = await client.post(
            ensure_trailing_slash("/api/v1/admin/allocations"),
            json={
                "user_id": str(regular_user.id),
                "vacation_period_id": str(test_vacation_period.id),
                "total_days": 30.0
            },
            headers=admin_auth_headers
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_get_allocations(
        self, client, admin_user, admin_auth_headers, test_allocation
    ):
        """Test listing allocations."""
        response = await client.get(
            ensure_trailing_slash("/api/v1/admin/allocations"),
            headers=admin_auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_get_allocation_by_id(
        self, client, admin_user, admin_auth_headers, test_allocation
    ):
        """Test getting a specific allocation."""
        response = await client.get(
            f"/api/v1/admin/allocations/{test_allocation.id}",
            headers=admin_auth_headers
        )
        assert response.status_code == 200
        assert response.json()["id"] == str(test_allocation.id)

    @pytest.mark.asyncio
    async def test_update_allocation(
        self, client, admin_user, admin_auth_headers, test_allocation
    ):
        """Test updating an allocation."""
        response = await client.put(
            f"/api/v1/admin/allocations/{test_allocation.id}",
            json={"total_days": 30.0},
            headers=admin_auth_headers
        )
        assert response.status_code == 200
        assert response.json()["total_days"] == 30.0

    @pytest.mark.asyncio
    async def test_delete_allocation(
        self, client, admin_user, admin_auth_headers, test_allocation
    ):
        """Test deleting an allocation."""
        response = await client.delete(
            f"/api/v1/admin/allocations/{test_allocation.id}",
            headers=admin_auth_headers
        )
        assert response.status_code == 200


# =============================================================================
# Vacation Balance Tests (User Endpoints)
# =============================================================================
class TestVacationBalance:
    """Tests for user vacation balance endpoints."""

    @pytest.mark.asyncio
    async def test_get_my_vacation_balance(
        self, client, regular_user, user_auth_headers, test_vacation_period, test_allocation
    ):
        """Test getting current user's vacation balance."""
        response = await client.get(
            "/api/v1/me/vacation-balance",
            headers=user_auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "total_available" in data
        assert "approved_days" in data
        assert "pending_days" in data
        assert "remaining_days" in data

    @pytest.mark.asyncio
    async def test_get_vacation_balance_requires_auth(self, client):
        """Test that balance endpoint requires authentication."""
        response = await client.get("/api/v1/me/vacation-balance")
        assert response.status_code == 401


# =============================================================================
# Vacation Request with Balance Integration Tests
# =============================================================================
class TestVacationRequestWithBalance:
    """Tests for vacation requests with balance integration."""

    @pytest.mark.asyncio
    async def test_create_vacation_request_with_balance(
        self, client, regular_user, user_auth_headers, test_team, test_vacation_period, test_allocation
    ):
        """Test creating a vacation request with balance validation."""
        response = await client.post(
            "/api/v1/vacation-requests/",
            json={
                "start_date": "2024-04-02",
                "end_date": "2024-04-04",
                "vacation_type": "annual",
                "team_id": str(test_team.id)
            },
            headers=user_auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["days_count"] == 3

    @pytest.mark.asyncio
    async def test_create_vacation_request_exceeds_balance(
        self, client, regular_user, user_auth_headers, test_team, test_vacation_period, test_allocation
    ):
        """Test that requests exceeding balance are rejected."""
        response = await client.post(
            "/api/v1/vacation-requests/",
            json={
                "start_date": "2024-04-01",
                "end_date": "2024-05-15",
                "vacation_type": "annual",
                "team_id": str(test_team.id)
            },
            headers=user_auth_headers
        )
        assert response.status_code == 400


# =============================================================================
# Company Isolation Tests
# =============================================================================
class TestVacationPeriodCompanyIsolation:
    """Tests for company data isolation."""

    @pytest.mark.asyncio
    async def test_cannot_access_other_company_period(
        self, client, admin_user, admin_auth_headers, test_vacation_period_other_company
    ):
        """Test that admin cannot access other company's periods."""
        response = await client.get(
            f"/api/v1/admin/vacation-periods/{test_vacation_period_other_company.id}",
            headers=admin_auth_headers
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_cannot_create_period_for_other_company(
        self, client, admin_user, admin_auth_headers, test_company2
    ):
        """Test that admin cannot create periods for other company."""
        response = await client.post(
            ensure_trailing_slash("/api/v1/admin/vacation-periods"),
            json={
                "company_id": str(test_company2.id),
                "name": "2024-2025",
                "start_date": "2024-04-01",
                "end_date": "2025-03-31"
            },
            headers=admin_auth_headers
        )
        assert response.status_code == 403


# =============================================================================
# Edge Cases and Validation Tests
# =============================================================================
class TestVacationPeriodEdgeCases:
    """Tests for edge cases and validation."""

    @pytest.mark.asyncio
    async def test_create_period_same_start_end_dates(
        self, client, admin_user, admin_auth_headers, test_company
    ):
        """Test creating period with same start and end date."""
        # Use unique dates to avoid conflicts
        response = await client.post(
            ensure_trailing_slash("/api/v1/admin/vacation-periods"),
            json={
                "company_id": str(test_company.id),
                "name": f"single-day-{uuid4().hex[:8]}",
                "start_date": "2030-04-01",
                "end_date": "2030-04-01"
            },
            headers=admin_auth_headers
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_allocations_requires_admin(
        self, client, regular_user, user_auth_headers
    ):
        """Test that allocations endpoint requires admin role."""
        response = await client.get(
            ensure_trailing_slash("/api/v1/admin/allocations"),
            headers=user_auth_headers
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_create_allocation_requires_admin(
        self, client, regular_user, user_auth_headers, test_vacation_period
    ):
        """Test that creating allocations requires admin role."""
        response = await client.post(
            ensure_trailing_slash("/api/v1/admin/allocations"),
            json={
                "user_id": str(regular_user.id),
                "vacation_period_id": str(test_vacation_period.id),
                "total_days": 25.0
            },
            headers=user_auth_headers
        )
        assert response.status_code == 403

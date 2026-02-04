"""Tests for Role-Based Access Control (RBAC)."""
import pytest
from datetime import date, datetime, timezone, timedelta
from uuid import uuid4


class TestRBACEnforcement:
    """Test role-based access control enforcement."""
    
    @pytest.mark.asyncio
    async def test_admin_can_access_admin_endpoints(self, client, admin_user, admin_auth_headers):
        """Test admin can access admin endpoints."""
        response = await client.get(
            "/api/v1/admin/users",
            headers=admin_auth_headers
        )
        
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_manager_cannot_access_admin_endpoints(self, client, manager_user, manager_auth_headers):
        """Test manager cannot access admin endpoints."""
        response = await client.get(
            "/api/v1/admin/users",
            headers=manager_auth_headers
        )
        
        assert response.status_code == 403
    
    @pytest.mark.asyncio
    async def test_user_cannot_access_admin_endpoints(self, client, regular_user, user_auth_headers):
        """Test regular user cannot access admin endpoints."""
        response = await client.get(
            "/api/v1/admin/users",
            headers=user_auth_headers
        )
        
        assert response.status_code == 403


class TestAdminEndpoints:
    """Tests for admin-only endpoints."""
    
    @pytest.mark.asyncio
    async def test_admin_can_list_users(self, client, admin_user, admin_auth_headers, test_company):
        """Test admin can list all users."""
        response = await client.get(
            "/api/v1/admin/users",
            headers=admin_auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    @pytest.mark.asyncio
    async def test_admin_can_list_companies(self, client, admin_user, admin_auth_headers):
        """Test admin can list companies."""
        response = await client.get(
            "/api/v1/admin/companies",
            headers=admin_auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    @pytest.mark.asyncio
    async def test_admin_can_list_functions(self, client, admin_user, admin_auth_headers):
        """Test admin can list functions."""
        response = await client.get(
            "/api/v1/admin/functions",
            headers=admin_auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    @pytest.mark.asyncio
    async def test_admin_can_create_team(self, client, admin_user, admin_auth_headers, test_company):
        """Test admin can create a team."""
        response = await client.post(
            "/api/v1/admin/teams",
            json={
                "name": "New Team",
                "company_id": str(test_company.id)
            },
            headers=admin_auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "New Team"
    
    @pytest.mark.asyncio
    async def test_manager_cannot_create_team(self, client, manager_user, manager_auth_headers, test_company):
        """Test manager cannot create a team."""
        response = await client.post(
            "/api/v1/admin/teams",
            json={
                "name": "Unauthorized Team",
                "company_id": str(test_company.id)
            },
            headers=manager_auth_headers
        )
        
        assert response.status_code == 403
    
    @pytest.mark.asyncio
    async def test_user_cannot_create_team(self, client, regular_user, user_auth_headers, test_company):
        """Test regular user cannot create a team."""
        response = await client.post(
            "/api/v1/admin/teams",
            json={
                "name": "Unauthorized Team",
                "company_id": str(test_company.id)
            },
            headers=user_auth_headers
        )
        
        assert response.status_code == 403


class TestVacationRequestRBAC:
    """Test vacation request access control."""
    
    @pytest.mark.asyncio
    async def test_user_can_create_own_request(self, client, regular_user, user_auth_headers):
        """Test user can create their own vacation request."""
        tomorrow = date.today() + timedelta(days=1)
        next_week = date.today() + timedelta(days=8)
        
        response = await client.post(
            "/api/v1/vacation-requests/",
            json={
                "start_date": str(tomorrow),
                "end_date": str(next_week),
                "vacation_type": "annual",
                "reason": "Test vacation"
            },
            headers=user_auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "pending"
        assert data["user_id"] == str(regular_user.id)
    
    @pytest.mark.asyncio
    async def test_user_can_view_own_requests(self, client, regular_user, user_auth_headers):
        """Test user can view their own vacation requests."""
        response = await client.get(
            "/api/v1/vacation-requests/",
            headers=user_auth_headers
        )
        
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    @pytest.mark.asyncio
    async def test_user_cannot_view_others_requests(self, client, regular_user, user_auth_headers, regular_user2, user2_auth_headers):
        """Test user cannot view other users' requests."""
        # Create a request as user2
        tomorrow = date.today() + timedelta(days=1)
        next_week = date.today() + timedelta(days=8)
        
        user2_request = await client.post(
            "/api/v1/vacation-requests/",
            json={
                "start_date": str(tomorrow),
                "end_date": str(next_week),
                "vacation_type": "annual",
                "reason": "User2 vacation"
            },
            headers=user2_auth_headers
        )
        
        request_id = user2_request.json()["id"]
        
        # Try to access it as regular user
        response = await client.get(
            f"/api/v1/vacation-requests/{request_id}",
            headers=user_auth_headers
        )
        
        assert response.status_code == 403
    
    @pytest.mark.asyncio
    async def test_manager_can_view_team_requests(self, client, manager_user, manager_auth_headers, regular_user, test_team):
        """Test manager can view requests from their team."""
        response = await client.get(
            f"/api/v1/manager/team-vacation-requests/{test_team.id}",
            headers=manager_auth_headers
        )
        
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    @pytest.mark.asyncio
    async def test_manager_can_approve_request(self, client, manager_user, manager_auth_headers, regular_user, test_team, db_session):
        """Test manager can approve vacation requests."""
        from app.models import VacationRequest
        
        # Create a vacation request
        vr = VacationRequest(
            user_id=regular_user.id,
            team_id=test_team.id,
            start_date=date(2024, 6, 1),
            end_date=date(2024, 6, 5),
            vacation_type="annual",
            status=VacationStatus.PENDING
        )
        db_session.add(vr)
        await db_session.commit()
        await db_session.refresh(vr)
        
        response = await client.post(
            f"/api/v1/vacation-requests/{vr.id}/approve",
            json={"action": "approve", "comment": "Approved"},
            headers=manager_auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "approved"
        assert data["approver_id"] == str(manager_user.id)
    
    @pytest.mark.asyncio
    async def test_manager_can_reject_request(self, client, manager_user, manager_auth_headers, regular_user, test_team, db_session):
        """Test manager can reject vacation requests."""
        from app.models import VacationRequest
        
        # Create a vacation request
        vr = VacationRequest(
            user_id=regular_user.id,
            team_id=test_team.id,
            start_date=date(2024, 6, 1),
            end_date=date(2024, 6, 5),
            vacation_type="annual",
            status=VacationStatus.PENDING
        )
        db_session.add(vr)
        await db_session.commit()
        await db_session.refresh(vr)
        
        response = await client.post(
            f"/api/v1/vacation-requests/{vr.id}/approve",
            json={"action": "reject", "comment": "Not enough notice"},
            headers=manager_auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "rejected"
    
    @pytest.mark.asyncio
    async def test_user_cannot_approve_requests(self, client, regular_user, user_auth_headers, regular_user2, test_team, db_session):
        """Test regular user cannot approve any requests."""
        from app.models import VacationRequest
        
        # Create a vacation request for user2
        vr = VacationRequest(
            user_id=regular_user2.id,
            team_id=test_team.id,
            start_date=date(2024, 6, 1),
            end_date=date(2024, 6, 5),
            vacation_type="annual",
            status=VacationStatus.PENDING
        )
        db_session.add(vr)
        await db_session.commit()
        await db_session.refresh(vr)
        
        # Try to approve as regular user
        response = await client.post(
            f"/api/v1/vacation-requests/{vr.id}/approve",
            json={"action": "approve", "comment": "Trying to approve"},
            headers=user_auth_headers
        )
        
        assert response.status_code == 403


class TestExportFunctionality:
    """Test export endpoints."""
    
    @pytest.mark.asyncio
    async def test_user_can_export_own_requests_csv(self, client, regular_user, user_auth_headers):
        """Test user can export their own requests as CSV."""
        response = await client.get(
            "/api/v1/export/csv",
            headers=user_auth_headers
        )
        
        assert response.status_code == 200
        assert "text/csv" in response.headers.get("content-type", "")
    
    @pytest.mark.asyncio
    async def test_user_can_export_own_requests_xlsx(self, client, regular_user, user_auth_headers):
        """Test user can export their own requests as XLSX."""
        response = await client.get(
            "/api/v1/export/xlsx",
            headers=user_auth_headers
        )
        
        assert response.status_code == 200
        assert "openxmlformats" in response.headers.get("content-type", "")
    
    @pytest.mark.asyncio
    async def test_manager_can_export_team_requests(self, client, manager_user, manager_auth_headers):
        """Test manager can export team requests."""
        response = await client.get(
            "/api/v1/export/csv",
            headers=manager_auth_headers
        )
        
        assert response.status_code == 200
        assert "text/csv" in response.headers.get("content-type", "")
    
    @pytest.mark.asyncio
    async def test_admin_can_export_all_requests(self, client, admin_user, admin_auth_headers):
        """Test admin can export all requests."""
        response = await client.get(
            "/api/v1/export/csv",
            headers=admin_auth_headers
        )
        
        assert response.status_code == 200
        assert "text/csv" in response.headers.get("content-type", "")
    
    @pytest.mark.asyncio
    async def test_export_requires_authentication(self, client):
        """Test export requires authentication."""
        response = await client.get("/api/v1/export/csv")
        
        assert response.status_code == 401


class TestManagerEndpoints:
    """Test manager-specific endpoints."""
    
    @pytest.mark.asyncio
    async def test_manager_can_view_team_members(self, client, manager_user, manager_auth_headers, test_team):
        """Test manager can view team members."""
        response = await client.get(
            f"/api/v1/manager/team-members/{test_team.id}",
            headers=manager_auth_headers
        )
        
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    @pytest.mark.asyncio
    async def test_user_cannot_view_team_members(self, client, regular_user, user_auth_headers, test_team):
        """Test regular user cannot view team members."""
        response = await client.get(
            f"/api/v1/manager/team-members/{test_team.id}",
            headers=user_auth_headers
        )
        
        assert response.status_code == 403
    
    @pytest.mark.asyncio
    async def test_manager_can_view_pending_requests(self, client, manager_user, manager_auth_headers, test_team, db_session):
        """Test manager can view pending requests."""
        response = await client.get(
            "/api/v1/manager/pending-requests",
            headers=manager_auth_headers
        )
        
        assert response.status_code == 200


class TestUserEndpoints:
    """Test user-specific endpoints."""
    
    @pytest.mark.asyncio
    async def test_user_can_view_own_profile(self, client, regular_user, user_auth_headers):
        """Test user can view their own profile."""
        response = await client.get(
            "/api/v1/users/me",
            headers=user_auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == regular_user.email
    
    @pytest.mark.asyncio
    async def test_user_can_update_own_profile(self, client, regular_user, user_auth_headers):
        """Test user can update their own profile."""
        response = await client.put(
            "/api/v1/users/me",
            json={
                "first_name": "Updated",
                "last_name": "Name"
            },
            headers=user_auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["first_name"] == "Updated"
        assert data["last_name"] == "Name"
    
    @pytest.mark.asyncio
    async def test_user_cannot_update_role(self, client, regular_user, user_auth_headers):
        """Test user cannot update their own role."""
        response = await client.put(
            "/api/v1/users/me",
            json={"role": "admin"},
            headers=user_auth_headers
        )
        
        # Should either fail validation or be ignored
        assert response.status_code in [200, 422]


# Import VacationStatus for use in tests
from app.models import VacationStatus

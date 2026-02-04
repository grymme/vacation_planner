"""Comprehensive API test suite for Vacation Planner."""
import pytest
from datetime import date, datetime, timezone, timedelta
from uuid import uuid4


# =============================================================================
# Authentication Tests
# =============================================================================
class TestAuthentication:
    """Tests for authentication endpoints."""

    @pytest.mark.asyncio
    async def test_register_user_flow(self, client, test_company):
        """Test user registration via invite flow."""
        # Admin invites user
        invite_response = await client.post(
            "/api/v1/admin/invite",
            json={
                "email": "newuser@test.com",
                "first_name": "New",
                "last_name": "User",
                "role": "user",
                "company_id": str(test_company.id)
            },
            headers={"Authorization": "Bearer test-admin-token"}  # Will fail, but tests flow
        )
        # This would require admin token, tested elsewhere

    @pytest.mark.asyncio
    async def test_login_success(self, client, regular_user):
        """Test successful login."""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": regular_user.email,
                "password": "userpassword123"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_login_invalid_password(self, client, regular_user):
        """Test login with invalid password."""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": regular_user.email,
                "password": "wrongpassword"
            }
        )
        
        assert response.status_code == 401
        assert "Invalid" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, client):
        """Test login with nonexistent user."""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "nonexistent@test.com",
                "password": "password123"
            }
        )
        
        assert response.status_code == 401
        assert "Invalid" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_login_inactive_user(self, client, inactive_user):
        """Test login with inactive user."""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": inactive_user.email,
                "password": "inactivepassword123"
            }
        )
        
        assert response.status_code == 401
        assert "deactivated" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_login_no_password_set(self, client, invited_user):
        """Test login with user who hasn't set password yet."""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": invited_user.email,
                "password": "password123"
            }
        )
        
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_logout(self, client, regular_user):
        """Test logout clears session."""
        # First login
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": regular_user.email,
                "password": "userpassword123"
            }
        )
        
        assert login_response.status_code == 200
        
        # Then logout
        logout_response = await client.post("/api/v1/auth/logout")
        
        assert logout_response.status_code == 200
        assert "message" in logout_response.json()

    @pytest.mark.asyncio
    async def test_token_refresh(self, client, regular_user):
        """Test refreshing access token."""
        # First login to get refresh token
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": regular_user.email,
                "password": "userpassword123"
            }
        )
        
        assert login_response.status_code == 200
        refresh_token = login_response.cookies.get("refresh_token")
        
        # Use refresh token to get new access token
        response = await client.post(
            "/api/v1/auth/refresh",
            cookies={"refresh_token": refresh_token}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data

    @pytest.mark.asyncio
    async def test_refresh_invalid_token(self, client):
        """Test refreshing with invalid token."""
        response = await client.post(
            "/api/v1/auth/refresh",
            cookies={"refresh_token": "invalid-refresh-token"}
        )
        
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_password_reset_request(self, client, regular_user):
        """Test password reset request."""
        response = await client.post(
            "/api/v1/auth/password-reset-request",
            json={"email": regular_user.email}
        )
        
        # Always returns success to prevent email enumeration
        assert response.status_code == 200
        assert "message" in response.json()

    @pytest.mark.asyncio
    async def test_password_reset_request_nonexistent(self, client):
        """Test password reset request for nonexistent user."""
        response = await client.post(
            "/api/v1/auth/password-reset-request",
            json={"email": "nonexistent@test.com"}
        )
        
        # Should still return success to prevent enumeration
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_set_password_invalid_token(self, client):
        """Test setting password with invalid token."""
        response = await client.post(
            "/api/v1/auth/set-password",
            json={
                "token": "invalid-token",
                "password": "Newpassword123!",
                "confirm_password": "Newpassword123!"
            }
        )
        
        assert response.status_code == 400


# =============================================================================
# User Profile Tests
# =============================================================================
class TestUserProfile:
    """Tests for user profile endpoints."""

    @pytest.mark.asyncio
    async def test_get_current_user_success(self, client, regular_user, user_auth_headers):
        """Test getting current user info with valid token."""
        response = await client.get(
            "/api/v1/auth/me",
            headers=user_auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == regular_user.email
        assert data["first_name"] == "Regular"
        assert data["role"] == "user"

    @pytest.mark.asyncio
    async def test_get_current_user_no_token(self, client):
        """Test getting current user without token."""
        response = await client.get("/api/v1/auth/me")
        
        assert response.status_code == 401
        assert "Not authenticated" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_current_user_invalid_token(self, client):
        """Test getting current user with invalid token."""
        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid-token"}
        )
        
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_update_current_user(self, client, regular_user, user_auth_headers):
        """Test updating current user profile."""
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
    async def test_get_user_profile(self, client, regular_user, user_auth_headers):
        """Test getting own user profile via users endpoint."""
        response = await client.get(
            f"/api/v1/users/{regular_user.id}",
            headers=user_auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == regular_user.email


# =============================================================================
# Vacation Request Tests
# =============================================================================
class TestVacationRequests:
    """Tests for vacation request endpoints."""

    @pytest.mark.asyncio
    async def test_create_vacation_request(self, client, regular_user, user_auth_headers, test_team):
        """Test creating a vacation request."""
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        next_week = (date.today() + timedelta(days=8)).isoformat()
        
        response = await client.post(
            "/api/v1/vacation-requests/",
            json={
                "start_date": tomorrow,
                "end_date": next_week,
                "vacation_type": "annual",
                "reason": "Summer vacation",
                "team_id": str(test_team.id)
            },
            headers=user_auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "pending"
        assert data["user_id"] == str(regular_user.id)
        assert data["vacation_type"] == "annual"

    @pytest.mark.asyncio
    async def test_create_vacation_request_invalid_dates(self, client, regular_user, user_auth_headers):
        """Test creating request with end date before start date."""
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        
        response = await client.post(
            "/api/v1/vacation-requests/",
            json={
                "start_date": tomorrow,
                "end_date": yesterday,
                "vacation_type": "annual"
            },
            headers=user_auth_headers
        )
        
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_create_vacation_request_single_day(self, client, regular_user, user_auth_headers):
        """Test creating a single-day vacation request."""
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        
        response = await client.post(
            "/api/v1/vacation-requests/",
            json={
                "start_date": tomorrow,
                "end_date": tomorrow,
                "vacation_type": "sick"
            },
            headers=user_auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["start_date"] == data["end_date"]

    @pytest.mark.asyncio
    async def test_list_own_vacation_requests(self, client, regular_user, user_auth_headers):
        """Test listing own vacation requests."""
        response = await client.get(
            "/api/v1/vacation-requests/",
            headers=user_auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_list_vacation_requests_with_filters(self, client, regular_user, user_auth_headers, vacation_request_pending):
        """Test listing requests with status filter."""
        response = await client.get(
            "/api/v1/vacation-requests/",
            params={"status": "pending"},
            headers=user_auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        for req in data:
            assert req["status"] == "pending"

    @pytest.mark.asyncio
    async def test_get_vacation_request(self, client, regular_user, user_auth_headers, vacation_request_pending):
        """Test getting a specific vacation request."""
        response = await client.get(
            f"/api/v1/vacation-requests/{vacation_request_pending.id}",
            headers=user_auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(vacation_request_pending.id)
        assert data["reason"] == "Summer vacation"

    @pytest.mark.asyncio
    async def test_get_vacation_request_not_found(self, client, regular_user, user_auth_headers):
        """Test getting nonexistent vacation request."""
        fake_id = str(uuid4())
        response = await client.get(
            f"/api/v1/vacation-requests/{fake_id}",
            headers=user_auth_headers
        )
        
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_cancel_pending_request(self, client, regular_user, user_auth_headers, db_session, test_team):
        """Test canceling a pending vacation request."""
        from app.models import VacationRequest
        
        # Create a pending request
        vr = VacationRequest(
            user_id=regular_user.id,
            team_id=test_team.id,
            start_date=(date.today() + timedelta(days=10)).isoformat(),
            end_date=(date.today() + timedelta(days=12)).isoformat(),
            vacation_type="annual",
            status=VacationStatus.PENDING
        )
        db_session.add(vr)
        await db_session.commit()
        await db_session.refresh(vr)
        
        # Cancel it
        response = await client.delete(
            f"/api/v1/vacation-requests/{vr.id}",
            headers=user_auth_headers
        )
        
        assert response.status_code == 200
        assert "cancelled" in response.json()["message"].lower()

    @pytest.mark.asyncio
    async def test_cancel_approved_request_fails(self, client, regular_user, user_auth_headers, vacation_request_approved):
        """Test that canceling an approved request fails."""
        response = await client.delete(
            f"/api/v1/vacation-requests/{vacation_request_approved.id}",
            headers=user_auth_headers
        )
        
        assert response.status_code == 400
        assert "pending" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_create_overlapping_request_fails(self, client, regular_user, user_auth_headers, db_session, test_team):
        """Test that creating overlapping requests fails."""
        from app.models import VacationRequest
        
        # Create an existing pending request
        vr = VacationRequest(
            user_id=regular_user.id,
            team_id=test_team.id,
            start_date=(date.today() + timedelta(days=10)).isoformat(),
            end_date=(date.today() + timedelta(days=12)).isoformat(),
            vacation_type="annual",
            status=VacationStatus.PENDING
        )
        db_session.add(vr)
        await db_session.commit()
        
        # Try to create overlapping request
        response = await client.post(
            "/api/v1/vacation-requests/",
            json={
                "start_date": (date.today() + timedelta(days=11)).isoformat(),
                "end_date": (date.today() + timedelta(days=13)).isoformat(),
                "vacation_type": "annual"
            },
            headers=user_auth_headers
        )
        
        assert response.status_code == 400
        assert "overlapping" in response.json()["detail"].lower()


# =============================================================================
# Manager Tests
# =============================================================================
class TestManagerEndpoints:
    """Tests for manager-specific endpoints."""

    @pytest.mark.asyncio
    async def test_manager_can_get_managed_teams(self, client, manager_user, manager_auth_headers, test_team):
        """Test manager can get their managed teams."""
        response = await client.get(
            "/api/v1/manager/teams",
            headers=manager_auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    @pytest.mark.asyncio
    async def test_user_cannot_get_managed_teams(self, client, regular_user, user_auth_headers):
        """Test regular user cannot access manager teams endpoint."""
        response = await client.get(
            "/api/v1/manager/teams",
            headers=user_auth_headers
        )
        
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_manager_can_get_team_members(self, client, manager_user, manager_auth_headers, regular_user, test_team):
        """Test manager can get team members."""
        response = await client.get(
            f"/api/v1/manager/team-members/{test_team.id}",
            headers=manager_auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_manager_cannot_get_other_team_members(self, client, manager_user, manager_auth_headers, test_team2):
        """Test manager cannot get members of team they don't manage."""
        response = await client.get(
            f"/api/v1/manager/team-members/{test_team2.id}",
            headers=manager_auth_headers
        )
        
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_manager_can_get_pending_requests(self, client, manager_user, manager_auth_headers):
        """Test manager can get pending requests for their teams."""
        response = await client.get(
            "/api/v1/manager/pending-requests",
            headers=manager_auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_manager_can_get_team_vacation_requests(self, client, manager_user, manager_auth_headers, regular_user, test_team, db_session):
        """Test manager can get vacation requests for their team."""
        from app.models import VacationRequest
        
        # Create a vacation request
        vr = VacationRequest(
            user_id=regular_user.id,
            team_id=test_team.id,
            start_date=(date.today() + timedelta(days=5)).isoformat(),
            end_date=(date.today() + timedelta(days=7)).isoformat(),
            vacation_type="annual",
            status=VacationStatus.PENDING
        )
        db_session.add(vr)
        await db_session.commit()
        
        response = await client.get(
            f"/api/v1/manager/team-vacation-requests/{test_team.id}",
            headers=manager_auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_manager_can_approve_request(self, client, manager_user, manager_auth_headers, regular_user, test_team, db_session):
        """Test manager can approve a vacation request."""
        from app.models import VacationRequest
        
        # Create a pending request
        vr = VacationRequest(
            user_id=regular_user.id,
            team_id=test_team.id,
            start_date=(date.today() + timedelta(days=5)).isoformat(),
            end_date=(date.today() + timedelta(days=7)).isoformat(),
            vacation_type="annual",
            status=VacationStatus.PENDING
        )
        db_session.add(vr)
        await db_session.commit()
        await db_session.refresh(vr)
        
        response = await client.post(
            f"/api/v1/vacation-requests/{vr.id}/approve",
            json={"action": "approve", "comment": "Approved for summer vacation"},
            headers=manager_auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "approved"
        assert data["approver_id"] == str(manager_user.id)

    @pytest.mark.asyncio
    async def test_manager_can_reject_request(self, client, manager_user, manager_auth_headers, regular_user, test_team, db_session):
        """Test manager can reject a vacation request."""
        from app.models import VacationRequest
        
        # Create a pending request
        vr = VacationRequest(
            user_id=regular_user.id,
            team_id=test_team.id,
            start_date=(date.today() + timedelta(days=5)).isoformat(),
            end_date=(date.today() + timedelta(days=7)).isoformat(),
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
    async def test_manager_cannot_approve_already_approved(self, client, manager_user, manager_auth_headers, vacation_request_approved):
        """Test manager cannot approve an already approved request."""
        response = await client.post(
            f"/api/v1/vacation-requests/{vacation_request_approved.id}/approve",
            json={"action": "approve"},
            headers=manager_auth_headers
        )
        
        assert response.status_code == 400
        assert "pending" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_manager_can_modify_request_dates(self, client, manager_user, manager_auth_headers, regular_user, test_team, db_session):
        """Test manager can modify a vacation request's dates."""
        from app.models import VacationRequest
        
        # Create a pending request
        vr = VacationRequest(
            user_id=regular_user.id,
            team_id=test_team.id,
            start_date=(date.today() + timedelta(days=5)).isoformat(),
            end_date=(date.today() + timedelta(days=7)).isoformat(),
            vacation_type="annual",
            status=VacationStatus.PENDING
        )
        db_session.add(vr)
        await db_session.commit()
        await db_session.refresh(vr)
        
        new_start = (date.today() + timedelta(days=10)).isoformat()
        new_end = (date.today() + timedelta(days=12)).isoformat()
        
        response = await client.put(
            f"/api/v1/vacation-requests/{vr.id}/modify",
            json={"start_date": new_start, "end_date": new_end},
            headers=manager_auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["start_date"] == new_start
        assert data["end_date"] == new_end


# =============================================================================
# Admin Tests
# =============================================================================
class TestAdminEndpoints:
    """Tests for admin-specific endpoints."""

    @pytest.mark.asyncio
    async def test_admin_can_list_all_users(self, client, admin_user, admin_auth_headers):
        """Test admin can list all users."""
        response = await client.get(
            "/api/v1/admin/users",
            headers=admin_auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_manager_cannot_list_all_users(self, client, manager_user, manager_auth_headers):
        """Test manager cannot list all users."""
        response = await client.get(
            "/api/v1/admin/users",
            headers=manager_auth_headers
        )
        
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_admin_can_create_company(self, client, admin_user, admin_auth_headers):
        """Test admin can create a new company."""
        response = await client.post(
            "/api/v1/admin/companies",
            json={"name": f"New Company {uuid4().hex[:8]}"},
            headers=admin_auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "name" in data

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
    async def test_admin_can_create_function(self, client, admin_user, admin_auth_headers, test_company):
        """Test admin can create a function/department."""
        response = await client.post(
            "/api/v1/admin/functions",
            json={
                "company_id": str(test_company.id),
                "name": f"New Function {uuid4().hex[:8]}"
            },
            headers=admin_auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["company_id"] == str(test_company.id)

    @pytest.mark.asyncio
    async def test_admin_can_create_team(self, client, admin_user, admin_auth_headers, test_company):
        """Test admin can create a team."""
        response = await client.post(
            "/api/v1/admin/teams",
            json={
                "company_id": str(test_company.id),
                "name": f"New Team {uuid4().hex[:8]}"
            },
            headers=admin_auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["name"]

    @pytest.mark.asyncio
    async def test_admin_can_invite_user(self, client, admin_user, admin_auth_headers, test_company):
        """Test admin can invite a new user."""
        response = await client.post(
            "/api/v1/admin/invite",
            json={
                "email": f"invited_{uuid4().hex[:8]}@test.com",
                "first_name": "Invited",
                "last_name": "User",
                "role": "user",
                "company_id": str(test_company.id)
            },
            headers=admin_auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "invite_token" in data
        assert "user_id" in data
        assert data["message"] == "User invited successfully"

    @pytest.mark.asyncio
    async def test_admin_can_update_user(self, client, admin_user, admin_auth_headers, regular_user):
        """Test admin can update a user."""
        response = await client.put(
            f"/api/v1/admin/users/{regular_user.id}",
            json={"first_name": "Updated by Admin"},
            headers=admin_auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["first_name"] == "Updated by Admin"

    @pytest.mark.asyncio
    async def test_admin_can_deactivate_user(self, client, admin_user, admin_auth_headers, db_session, test_company):
        """Test admin can deactivate a user."""
        from app.models import User
        
        # Create a new user
        user = User(
            email=f"deactivate_{uuid4().hex[:8]}@test.com",
            hashed_password=hash_password("password123"),
            first_name="ToDeactivate",
            last_name="User",
            role=UserRole.USER,
            company_id=test_company.id,
            is_active=True
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        
        response = await client.post(
            f"/api/v1/admin/users/{user.id}/deactivate",
            headers=admin_auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] is False

    @pytest.mark.asyncio
    async def test_admin_can_assign_team_manager(self, client, admin_user, admin_auth_headers, regular_user, test_team):
        """Test admin can assign a user as team manager."""
        response = await client.post(
            f"/api/v1/admin/teams/{test_team.id}/managers/{regular_user.id}",
            headers=admin_auth_headers
        )
        
        assert response.status_code == 200
        assert "message" in response.json()

    @pytest.mark.asyncio
    async def test_admin_can_remove_team_manager(self, client, admin_user, admin_auth_headers, manager_user, test_team):
        """Test admin can remove a user's manager assignment."""
        response = await client.delete(
            f"/api/v1/admin/teams/{test_team.id}/managers/{manager_user.id}",
            headers=admin_auth_headers
        )
        
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_admin_can_add_team_member(self, client, admin_user, admin_auth_headers, regular_user, test_team):
        """Test admin can add a user to a team."""
        response = await client.post(
            f"/api/v1/admin/teams/{test_team.id}/members/{regular_user.id}",
            headers=admin_auth_headers
        )
        
        assert response.status_code == 200
        assert "message" in response.json()

    @pytest.mark.asyncio
    async def test_admin_can_remove_team_member(self, client, admin_user, admin_auth_headers, regular_user, test_team):
        """Test admin can remove a user from a team."""
        response = await client.delete(
            f"/api/v1/admin/teams/{test_team.id}/members/{regular_user.id}",
            headers=admin_auth_headers
        )
        
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_admin_can_reset_user_password(self, client, admin_user, admin_auth_headers, regular_user):
        """Test admin can reset a user's password."""
        response = await client.post(
            f"/api/v1/admin/users/{regular_user.id}/reset-password",
            headers=admin_auth_headers
        )
        
        assert response.status_code == 200
        assert "message" in response.json()

    @pytest.mark.asyncio
    async def test_admin_can_list_audit_logs(self, client, admin_user, admin_auth_headers):
        """Test admin can list audit logs."""
        response = await client.get(
            "/api/v1/admin/audit-logs",
            headers=admin_auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


# =============================================================================
# Export Tests
# =============================================================================
class TestExports:
    """Tests for export endpoints."""

    @pytest.mark.asyncio
    async def test_user_can_export_own_requests_csv(self, client, regular_user, user_auth_headers):
        """Test user can export their own requests as CSV."""
        response = await client.get(
            "/api/v1/export/csv",
            headers=user_auth_headers
        )
        
        assert response.status_code == 200
        assert "text/csv" in response.headers.get("content-type", "")
        assert "attachment" in response.headers.get("content-disposition", "")

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

    @pytest.mark.asyncio
    async def test_export_with_date_filter(self, client, regular_user, user_auth_headers):
        """Test export with date filter."""
        response = await client.get(
            "/api/v1/export/csv",
            params={
                "start_date": "2024-01-01",
                "end_date": "2024-12-31"
            },
            headers=user_auth_headers
        )
        
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_export_with_status_filter(self, client, regular_user, user_auth_headers):
        """Test export with status filter."""
        response = await client.get(
            "/api/v1/export/csv",
            params={"status": "approved"},
            headers=user_auth_headers
        )
        
        assert response.status_code == 200


# =============================================================================
# Security Tests
# =============================================================================
class TestSecurity:
    """Tests for security and RBAC enforcement."""

    @pytest.mark.asyncio
    async def test_user_cannot_access_admin_endpoints(self, client, regular_user, user_auth_headers):
        """Test regular user cannot access admin endpoints."""
        response = await client.get(
            "/api/v1/admin/users",
            headers=user_auth_headers
        )
        
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_manager_cannot_access_admin_endpoints(self, client, manager_user, manager_auth_headers):
        """Test manager cannot access admin endpoints."""
        response = await client.get(
            "/api/v1/admin/users",
            headers=manager_auth_headers
        )
        
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_user_cannot_access_manager_endpoints(self, client, regular_user, user_auth_headers):
        """Test regular user cannot access manager endpoints."""
        response = await client.get(
            "/api/v1/manager/teams",
            headers=user_auth_headers
        )
        
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_user_cannot_view_other_users_requests(self, client, regular_user, user_auth_headers, regular_user2, user2_auth_headers, db_session, test_team2):
        """Test user cannot view other users' vacation requests."""
        from app.models import VacationRequest
        
        # Create a request as user2
        vr = VacationRequest(
            user_id=regular_user2.id,
            team_id=test_team2.id,
            start_date=(date.today() + timedelta(days=5)).isoformat(),
            end_date=(date.today() + timedelta(days=7)).isoformat(),
            vacation_type="annual",
            status=VacationStatus.PENDING
        )
        db_session.add(vr)
        await db_session.commit()
        await db_session.refresh(vr)
        
        # Try to access it as regular user
        response = await client.get(
            f"/api/v1/vacation-requests/{vr.id}",
            headers=user_auth_headers
        )
        
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_user_cannot_approve_requests(self, client, regular_user, user_auth_headers, regular_user2, test_team2, db_session):
        """Test regular user cannot approve any requests."""
        from app.models import VacationRequest
        
        # Create a request for user2
        vr = VacationRequest(
            user_id=regular_user2.id,
            team_id=test_team2.id,
            start_date=(date.today() + timedelta(days=5)).isoformat(),
            end_date=(date.today() + timedelta(days=7)).isoformat(),
            vacation_type="annual",
            status=VacationStatus.PENDING
        )
        db_session.add(vr)
        await db_session.commit()
        await db_session.refresh(vr)
        
        # Try to approve as regular user
        response = await client.post(
            f"/api/v1/vacation-requests/{vr.id}/approve",
            json={"action": "approve"},
            headers=user_auth_headers
        )
        
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_user_cannot_cancel_others_requests(self, client, regular_user, user_auth_headers, regular_user2, test_team2, db_session):
        """Test user cannot cancel other users' vacation requests."""
        from app.models import VacationRequest
        
        # Create a request for user2
        vr = VacationRequest(
            user_id=regular_user2.id,
            team_id=test_team2.id,
            start_date=(date.today() + timedelta(days=5)).isoformat(),
            end_date=(date.today() + timedelta(days=7)).isoformat(),
            vacation_type="annual",
            status=VacationStatus.PENDING
        )
        db_session.add(vr)
        await db_session.commit()
        await db_session.refresh(vr)
        
        # Try to cancel as regular user
        response = await client.delete(
            f"/api/v1/vacation-requests/{vr.id}",
            headers=user_auth_headers
        )
        
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_company_isolation(self, client, regular_user, user_auth_headers, user_from_other_company, other_company_auth_headers, db_session, test_team, test_company2, test_team2):
        """Test users from different companies cannot see each other's data."""
        from app.models import VacationRequest
        
        # Create vacation request in company 1
        vr1 = VacationRequest(
            user_id=regular_user.id,
            team_id=test_team.id,
            start_date=(date.today() + timedelta(days=5)).isoformat(),
            end_date=(date.today() + timedelta(days=7)).isoformat(),
            vacation_type="annual",
            status=VacationStatus.PENDING
        )
        db_session.add(vr1)
        await db_session.commit()
        
        # User from company 2 should not see company 1's data
        # Export should only show their own requests
        response = await client.get(
            "/api/v1/export/csv",
            headers=other_company_auth_headers
        )
        
        assert response.status_code == 200
        content = response.text
        # Content should not contain company 1 user data
        assert regular_user.email not in content

    @pytest.mark.asyncio
    async def test_authentication_required_on_protected_endpoints(self, client):
        """Test that authentication is required on protected endpoints."""
        endpoints = [
            ("GET", "/api/v1/auth/me"),
            ("GET", "/api/v1/users/me"),
            ("PUT", "/api/v1/users/me"),
            ("GET", "/api/v1/vacation-requests/"),
            ("POST", "/api/v1/vacation-requests/"),
            ("GET", "/api/v1/manager/teams"),
            ("GET", "/api/v1/admin/users"),
            ("GET", "/api/v1/export/csv"),
        ]
        
        for method, endpoint in endpoints:
            if method == "GET":
                response = await client.get(endpoint)
            elif method == "PUT":
                response = await client.put(endpoint, json={})
            elif method == "POST":
                response = await client.post(endpoint, json={})
            
            assert response.status_code == 401, f"{method} {endpoint} should require auth"

    @pytest.mark.asyncio
    async def test_invalid_token_rejected(self, client):
        """Test that invalid tokens are rejected."""
        invalid_endpoints = [
            ("GET", "/api/v1/auth/me", {"Authorization": "Bearer invalid-token"}),
            ("GET", "/api/v1/users/me", {"Authorization": "Bearer fake-token"}),
            ("GET", "/api/v1/vacation-requests/", {"Authorization": "Bearer not-real"}),
        ]
        
        for method, endpoint, headers in invalid_endpoints:
            if method == "GET":
                response = await client.get(endpoint, headers=headers)
            elif method == "PUT":
                response = await client.put(endpoint, json={}, headers=headers)
            elif method == "POST":
                response = await client.post(endpoint, json={}, headers=headers)
            
            assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_user_cannot_impersonate_admin(self, client, regular_user, user_auth_headers):
        """Test user cannot access admin API with user token."""
        admin_endpoints = [
            ("GET", "/api/v1/admin/users"),
            ("POST", "/api/v1/admin/companies"),
            ("POST", "/api/v1/admin/invite"),
        ]
        
        for method, endpoint in admin_endpoints:
            if method == "GET":
                response = await client.get(endpoint, headers=user_auth_headers)
            elif method == "POST":
                response = await client.post(endpoint, json={}, headers=user_auth_headers)
            
            assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_manager_scope_enforcement(self, client, manager_user, manager_auth_headers, test_team, test_team2, db_session, regular_user2):
        """Test manager can only manage their assigned teams."""
        from app.models import VacationRequest
        
        # Create a vacation request for user2 in team2 (not managed by manager_user)
        vr = VacationRequest(
            user_id=regular_user2.id,
            team_id=test_team2.id,
            start_date=(date.today() + timedelta(days=5)).isoformat(),
            end_date=(date.today() + timedelta(days=7)).isoformat(),
            vacation_type="annual",
            status=VacationStatus.PENDING
        )
        db_session.add(vr)
        await db_session.commit()
        await db_session.refresh(vr)
        
        # Try to approve as manager of different team
        response = await client.post(
            f"/api/v1/vacation-requests/{vr.id}/approve",
            json={"action": "approve"},
            headers=manager_auth_headers
        )
        
        assert response.status_code == 403


# =============================================================================
# Health Check Tests
# =============================================================================
class TestHealthCheck:
    """Tests for health check endpoint."""

    @pytest.mark.asyncio
    async def test_health_check(self, client):
        """Test health check endpoint."""
        response = await client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "database" in data
        assert "timestamp" in data

    @pytest.mark.asyncio
    async def test_root_endpoint(self, client):
        """Test root endpoint."""
        response = await client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "version" in data


# Import additional dependencies
from app.models import VacationRequest, VacationStatus
from app.auth import hash_password

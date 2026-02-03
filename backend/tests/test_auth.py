"""Tests for authentication functionality."""
import pytest
from datetime import datetime, timedelta, timezone


class TestPasswordHashing:
    """Tests for password hashing functions."""
    
    def test_password_hash_is_different_from_plain(self):
        """Test that hashed password is different from plain password."""
        from app.auth import hash_password, verify_password
        
        password = "testpassword123"
        hashed = hash_password(password)
        
        assert hashed != password
        assert len(hashed) > len(password)
    
    def test_verify_correct_password(self):
        """Test that correct password is verified."""
        from app.auth import hash_password, verify_password
        
        password = "testpassword123"
        hashed = hash_password(password)
        
        assert verify_password(password, hashed) is True
    
    def test_verify_incorrect_password(self):
        """Test that incorrect password is not verified."""
        from app.auth import hash_password, verify_password
        
        password = "testpassword123"
        wrong_password = "wrongpassword"
        hashed = hash_password(password)
        
        assert verify_password(wrong_password, hashed) is False
    
    def test_argon2id_prefix(self):
        """Test that Argon2id prefix is present in hash."""
        from app.auth import hash_password
        
        password = "testpassword"
        hashed = hash_password(password)
        
        # Argon2id hashes start with $argon2id$
        assert "$argon2id$" in hashed
    
    def test_hash_uniqueness(self):
        """Test that same password produces different hashes (salt)."""
        from app.auth import hash_password, verify_password
        
        password = "samepassword"
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        
        # Different hashes due to different salts
        assert hash1 != hash2
        
        # But both should verify correctly
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True


class TestJWT:
    """Tests for JWT token functionality."""
    
    def test_create_access_token(self):
        """Test access token creation."""
        from app.auth import create_access_token
        from app.models import UserRole
        
        token = create_access_token(
            user_id=__import__("uuid").uuid4(),
            email="test@example.com",
            role=UserRole.USER,
            company_id=__import__("uuid").uuid4()
        )
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0
    
    def test_create_refresh_token(self):
        """Test refresh token creation."""
        from app.auth import create_refresh_token
        
        token = create_refresh_token(user_id=__import__("uuid").uuid4())
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0
    
    def test_decode_valid_token(self):
        """Test decoding a valid token."""
        from app.auth import create_access_token, decode_token
        from app.models import UserRole
        
        user_id = __import__("uuid").uuid4()
        email = "test@example.com"
        
        token = create_access_token(
            user_id=user_id,
            email=email,
            role=UserRole.USER,
            company_id=__import__("uuid").uuid4()
        )
        
        payload = decode_token(token)
        
        assert payload is not None
        assert payload.get("sub") == str(user_id)
        assert payload.get("email") == email
        assert payload.get("type") == "access"
    
    def test_decode_invalid_token(self):
        """Test decoding an invalid token raises exception."""
        from fastapi import HTTPException
        
        # Invalid token should raise HTTPException
        with pytest.raises(HTTPException) as exc_info:
            from app.auth import decode_token
            decode_token("invalid_token")
        
        assert exc_info.value.status_code == 401
    
    def test_decode_expired_token(self):
        """Test decoding an expired token raises exception."""
        from fastapi import HTTPException
        from jose import jwt
        from app.config import settings
        
        # Create an expired token
        expired_payload = {
            "sub": str(__import__("uuid").uuid4()),
            "email": "test@example.com",
            "role": "user",
            "company_id": str(__import__("uuid").uuid4()),
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
            "iat": datetime.now(timezone.utc) - timedelta(hours=2),
            "type": "access"
        }
        expired_token = jwt.encode(
            expired_payload, 
            settings.jwt_secret, 
            algorithm=settings.jwt_algorithm
        )
        
        from app.auth import decode_token
        # Expired token should raise HTTPException
        with pytest.raises(HTTPException) as exc_info:
            decode_token(expired_token)
        
        assert exc_info.value.status_code == 401


class TestLogin:
    """Tests for user login."""
    
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
    async def test_login_wrong_password(self, client, regular_user):
        """Test login with wrong password."""
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


class TestGetCurrentUser:
    """Tests for getting current user info."""
    
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
    async def test_get_current_user_admin(self, client, admin_user, admin_auth_headers):
        """Test getting admin user info."""
        response = await client.get(
            "/api/v1/auth/me",
            headers=admin_auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == admin_user.email
        assert data["role"] == "admin"
    
    @pytest.mark.asyncio
    async def test_get_current_user_manager(self, client, manager_user, manager_auth_headers):
        """Test getting manager user info."""
        response = await client.get(
            "/api/v1/auth/me",
            headers=manager_auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == manager_user.email
        assert data["role"] == "manager"


class TestTokenRefresh:
    """Tests for token refresh functionality."""
    
    @pytest.mark.asyncio
    async def test_refresh_token(self, client, regular_user):
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


class TestInviteFlow:
    """Tests for invite/set-password flow."""
    
    @pytest.mark.asyncio
    async def test_invite_requires_admin(self, client, manager_user, manager_auth_headers):
        """Test that non-admin cannot invite users."""
        response = await client.post(
            "/api/v1/admin/invite",
            json={
                "email": "newuser@test.com",
                "first_name": "New",
                "last_name": "User",
                "role": "user",
                "company_id": str(manager_user.company_id)
            },
            headers=manager_auth_headers
        )
        
        # Manager should not have admin access
        assert response.status_code == 403
    
    @pytest.mark.asyncio
    async def test_admin_can_invite_user(self, client, admin_user, admin_auth_headers, test_company):
        """Test that admin can invite new user."""
        response = await client.post(
            "/api/v1/admin/invite",
            json={
                "email": "newuser@test.com",
                "first_name": "New",
                "last_name": "User",
                "role": "user",
                "company_id": str(test_company.id)
            },
            headers=admin_auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "invite_token" in data
        assert data["message"] == "User invited successfully"
    
    @pytest.mark.asyncio
    async def test_invite_creates_inactive_user(self, client, admin_user, admin_auth_headers, test_company):
        """Test that invite creates inactive user."""
        response = await client.post(
            "/api/v1/admin/invite",
            json={
                "email": "inviteduser@test.com",
                "first_name": "Invited",
                "last_name": "User",
                "role": "user",
                "company_id": str(test_company.id)
            },
            headers=admin_auth_headers
        )
        
        assert response.status_code == 200
        
        # Login should fail since password not set
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "inviteduser@test.com",
                "password": "password123"
            }
        )
        
        assert login_response.status_code == 401


class TestLogout:
    """Tests for logout functionality."""
    
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
        
        # Logout should succeed (token blacklisting would be implemented in production)
        assert logout_response.status_code == 200

"""Integration tests for authentication API."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestAuthRegistration:
    """Test user registration."""

    async def test_register_success(self, unauthenticated_client: AsyncClient, db_session):
        """Test successful user registration."""
        response = await unauthenticated_client.post(
            "/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "securepassword123",
                "full_name": "New User",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert data["full_name"] == "New User"
        assert "id" in data
        assert "password" not in data
        assert "password_hash" not in data

    async def test_register_duplicate_email(
        self, unauthenticated_client: AsyncClient, test_user
    ):
        """Test registration with existing email."""
        response = await unauthenticated_client.post(
            "/auth/register",
            json={
                "email": test_user.email,  # Already exists
                "password": "somepassword123",
            },
        )

        assert response.status_code == 400
        assert "already registered" in response.json()["detail"].lower()

    async def test_register_invalid_email(self, unauthenticated_client: AsyncClient):
        """Test registration with invalid email format."""
        response = await unauthenticated_client.post(
            "/auth/register",
            json={
                "email": "not-an-email",
                "password": "securepassword123",
            },
        )

        assert response.status_code == 422  # Validation error

    async def test_register_weak_password(self, unauthenticated_client: AsyncClient):
        """Test registration with weak password."""
        response = await unauthenticated_client.post(
            "/auth/register",
            json={
                "email": "test@example.com",
                "password": "123",  # Too short
            },
        )

        assert response.status_code == 422


@pytest.mark.asyncio
class TestAuthLogin:
    """Test user login."""

    async def test_login_success(self, unauthenticated_client: AsyncClient, test_user):
        """Test successful login."""
        response = await unauthenticated_client.post(
            "/auth/login",
            json={
                "email": test_user.email,
                "password": "testpassword123",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert "expires_in" in data

    async def test_login_wrong_password(
        self, unauthenticated_client: AsyncClient, test_user
    ):
        """Test login with wrong password."""
        response = await unauthenticated_client.post(
            "/auth/login",
            json={
                "email": test_user.email,
                "password": "wrongpassword",
            },
        )

        assert response.status_code == 401
        assert "invalid" in response.json()["detail"].lower()

    async def test_login_nonexistent_user(self, unauthenticated_client: AsyncClient):
        """Test login with non-existent user."""
        response = await unauthenticated_client.post(
            "/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "somepassword123",
            },
        )

        assert response.status_code == 401


@pytest.mark.asyncio
class TestTokenRefresh:
    """Test token refresh."""

    async def test_refresh_token_success(
        self, unauthenticated_client: AsyncClient, test_user
    ):
        """Test successful token refresh."""
        # First login to get tokens
        login_response = await unauthenticated_client.post(
            "/auth/login",
            json={
                "email": test_user.email,
                "password": "testpassword123",
            },
        )
        tokens = login_response.json()

        # Refresh the token
        response = await unauthenticated_client.post(
            "/auth/refresh",
            json={"refresh_token": tokens["refresh_token"]},
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        # New tokens should be different
        assert data["access_token"] != tokens["access_token"]

    async def test_refresh_invalid_token(self, unauthenticated_client: AsyncClient):
        """Test refresh with invalid token."""
        response = await unauthenticated_client.post(
            "/auth/refresh",
            json={"refresh_token": "invalid-token"},
        )

        assert response.status_code == 401


@pytest.mark.asyncio
class TestAuthenticatedEndpoints:
    """Test authenticated endpoint access."""

    async def test_get_current_user(self, client: AsyncClient, test_user):
        """Test getting current user info."""
        response = await client.get("/auth/me")

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == test_user.email
        assert data["id"] == str(test_user.id)

    async def test_access_without_token(self, unauthenticated_client: AsyncClient):
        """Test accessing protected endpoint without token."""
        response = await unauthenticated_client.get("/auth/me")

        assert response.status_code == 401

    async def test_access_with_invalid_token(self, unauthenticated_client: AsyncClient):
        """Test accessing protected endpoint with invalid token."""
        response = await unauthenticated_client.get(
            "/auth/me",
            headers={"Authorization": "Bearer invalid-token"},
        )

        assert response.status_code == 401

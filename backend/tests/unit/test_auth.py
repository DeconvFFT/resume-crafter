"""Unit tests for authentication."""

import pytest
from jose import jwt

from src.auth.jwt import (
    create_access_token,
    create_refresh_token,
    verify_password,
    get_password_hash,
)
from src.config import get_settings


settings = get_settings()


class TestPasswordHashing:
    """Test password hashing functions."""

    def test_hash_password(self):
        """Test password hashing."""
        password = "testpassword123"
        hashed = get_password_hash(password)

        assert hashed != password
        assert len(hashed) > 0
        assert hashed.startswith("$2b$")  # bcrypt prefix

    def test_verify_correct_password(self):
        """Test verifying correct password."""
        password = "testpassword123"
        hashed = get_password_hash(password)

        assert verify_password(password, hashed) is True

    def test_verify_incorrect_password(self):
        """Test verifying incorrect password."""
        password = "testpassword123"
        hashed = get_password_hash(password)

        assert verify_password("wrongpassword", hashed) is False

    def test_different_hashes_for_same_password(self):
        """Test that hashing same password produces different hashes."""
        password = "testpassword123"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)

        # Hashes should be different (due to salt)
        assert hash1 != hash2

        # But both should verify correctly
        assert verify_password(password, hash1)
        assert verify_password(password, hash2)


class TestTokenCreation:
    """Test JWT token creation."""

    def test_create_access_token(self):
        """Test access token creation."""
        data = {"sub": "user-123", "email": "test@example.com"}
        token = create_access_token(data)

        assert token is not None
        assert len(token) > 0

        # Decode and verify
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        assert payload["sub"] == "user-123"
        assert payload["email"] == "test@example.com"
        assert "exp" in payload
        assert payload["type"] == "access"

    def test_create_refresh_token(self):
        """Test refresh token creation."""
        data = {"sub": "user-123"}
        token = create_refresh_token(data)

        assert token is not None
        assert len(token) > 0

        # Decode and verify
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        assert payload["sub"] == "user-123"
        assert "exp" in payload
        assert payload["type"] == "refresh"

    def test_access_token_expiry(self):
        """Test that access token has correct expiry."""
        from datetime import datetime, timezone

        data = {"sub": "user-123"}
        token = create_access_token(data)

        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )

        exp_time = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        now = datetime.now(timezone.utc)

        # Should expire in approximately 15 minutes (with some tolerance)
        time_diff = (exp_time - now).total_seconds()
        expected_seconds = settings.jwt_access_token_expire_minutes * 60

        assert abs(time_diff - expected_seconds) < 10  # 10 second tolerance


class TestTokenValidation:
    """Test JWT token validation."""

    def test_decode_valid_token(self):
        """Test decoding a valid token."""
        data = {"sub": "user-123", "email": "test@example.com"}
        token = create_access_token(data)

        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )

        assert payload["sub"] == "user-123"
        assert payload["email"] == "test@example.com"

    def test_decode_invalid_token(self):
        """Test decoding an invalid token."""
        from jose.exceptions import JWTError

        invalid_token = "invalid.token.here"

        with pytest.raises(JWTError):
            jwt.decode(
                invalid_token,
                settings.jwt_secret_key,
                algorithms=[settings.jwt_algorithm],
            )

    def test_decode_with_wrong_secret(self):
        """Test decoding with wrong secret."""
        from jose.exceptions import JWTError

        data = {"sub": "user-123"}
        token = create_access_token(data)

        with pytest.raises(JWTError):
            jwt.decode(
                token,
                "wrong-secret-key",
                algorithms=[settings.jwt_algorithm],
            )

    def test_expired_token(self):
        """Test expired token handling."""
        from datetime import timedelta
        from jose.exceptions import ExpiredSignatureError

        # Create token that expires immediately
        data = {"sub": "user-123"}
        token = create_access_token(data, expires_delta=timedelta(seconds=-1))

        with pytest.raises(ExpiredSignatureError):
            jwt.decode(
                token,
                settings.jwt_secret_key,
                algorithms=[settings.jwt_algorithm],
            )

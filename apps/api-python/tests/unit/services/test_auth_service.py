"""Tests for AuthService"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime

from infrastructure.services.auth_service import AuthService


class TestAuthService:
    """Test cases for AuthService"""

    @pytest.fixture
    def auth_service(self):
        """AuthService instance"""
        return AuthService()

    def test_hash_password(self, auth_service):
        """Test password hashing"""
        password = "test_password123"
        hashed = auth_service.hash_password(password)

        assert hashed != password
        assert len(hashed) > 20
        assert hashed.startswith("$2b$")

    def test_verify_password_correct(self, auth_service):
        """Test password verification with correct password"""
        password = "test_password123"
        hashed = auth_service.hash_password(password)

        assert auth_service.verify_password(password, hashed) is True

    def test_verify_password_incorrect(self, auth_service):
        """Test password verification with incorrect password"""
        password = "test_password123"
        wrong_password = "wrong_password"
        hashed = auth_service.hash_password(password)

        assert auth_service.verify_password(wrong_password, hashed) is False

    def test_verify_password_invalid_hash(self, auth_service):
        """Test password verification with invalid hash"""
        password = "test_password123"
        invalid_hash = "invalid_hash"

        assert auth_service.verify_password(password, invalid_hash) is False

    def test_generate_totp_secret(self, auth_service):
        """Test TOTP secret generation"""
        secret = auth_service.generate_totp_secret()

        assert isinstance(secret, str)
        assert len(secret) == 32
        # Base32 characters
        assert all(c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567" for c in secret)

    def test_get_totp_provisioning_uri(self, auth_service):
        """Test TOTP provisioning URI generation"""
        secret = "JBSWY3DPEHPK3PXP"
        email = "test@example.com"

        uri = auth_service.get_totp_provisioning_uri(secret, email)

        assert uri.startswith("otpauth://totp/")
        assert (
            "test%40example.com" in uri or "test@example.com" in uri
        )  # URL encoded or not
        assert "TradingView%20Gateway" in uri or "TradingView Gateway" in uri
        assert secret in uri

    @patch("pyotp.TOTP")
    def test_verify_totp_token_valid(self, mock_totp_class, auth_service):
        """Test TOTP token verification with valid token"""
        secret = "JBSWY3DPEHPK3PXP"
        token = "123456"

        mock_totp = MagicMock()
        mock_totp.verify.return_value = True
        mock_totp_class.return_value = mock_totp

        result = auth_service.verify_totp_token(secret, token)

        assert result is True
        mock_totp_class.assert_called_once_with(secret)
        mock_totp.verify.assert_called_once_with(token, valid_window=1)

    @patch("pyotp.TOTP")
    def test_verify_totp_token_invalid(self, mock_totp_class, auth_service):
        """Test TOTP token verification with invalid token"""
        secret = "JBSWY3DPEHPK3PXP"
        token = "wrong_token"

        mock_totp = MagicMock()
        mock_totp.verify.return_value = False
        mock_totp_class.return_value = mock_totp

        result = auth_service.verify_totp_token(secret, token)

        assert result is False

    @patch("pyotp.TOTP")
    def test_verify_totp_token_exception(self, mock_totp_class, auth_service):
        """Test TOTP token verification with exception"""
        secret = "INVALID_SECRET"
        token = "123456"

        mock_totp_class.side_effect = ValueError("Invalid secret")

        result = auth_service.verify_totp_token(secret, token)

        assert result is False

    @patch("infrastructure.services.auth_service.datetime")
    @patch("infrastructure.services.auth_service.jwt")
    def test_create_access_token(self, mock_jwt, mock_datetime, auth_service):
        """Test JWT access token creation"""
        user_id = "123e4567-e89b-12d3-a456-426614174000"
        email = "test@example.com"

        # Mock datetime
        now = datetime(2023, 1, 1, 12, 0, 0)
        mock_datetime.utcnow.return_value = now

        # Mock JWT encode
        mock_jwt.encode.return_value = "mock_token"

        token = auth_service.create_access_token(user_id, email)

        assert token == "mock_token"

        # Verify JWT payload
        call_args = mock_jwt.encode.call_args[0][0]
        assert call_args["sub"] == user_id
        assert call_args["email"] == email
        assert call_args["type"] == "access"
        assert call_args["iat"] == now

    @patch("infrastructure.services.auth_service.datetime")
    @patch("infrastructure.services.auth_service.jwt")
    def test_create_refresh_token(self, mock_jwt, mock_datetime, auth_service):
        """Test JWT refresh token creation"""
        user_id = "123e4567-e89b-12d3-a456-426614174000"

        # Mock datetime
        now = datetime(2023, 1, 1, 12, 0, 0)
        mock_datetime.utcnow.return_value = now

        # Mock JWT encode
        mock_jwt.encode.return_value = "mock_refresh_token"

        token = auth_service.create_refresh_token(user_id)

        assert token == "mock_refresh_token"

        # Verify JWT payload
        call_args = mock_jwt.encode.call_args[0][0]
        assert call_args["sub"] == user_id
        assert call_args["type"] == "refresh"
        assert call_args["iat"] == now

    @patch("infrastructure.services.auth_service.jwt")
    def test_verify_token_valid(self, mock_jwt, auth_service):
        """Test JWT token verification with valid token"""
        token = "valid_token"
        payload = {"sub": "user_123", "exp": 1234567890}

        mock_jwt.decode.return_value = payload

        result = auth_service.verify_token(token)

        assert result == payload
        mock_jwt.decode.assert_called_once_with(
            token,
            auth_service.settings.secret_key,
            algorithms=[auth_service.settings.algorithm],
        )

    @patch("infrastructure.services.auth_service.jwt")
    def test_verify_token_expired(self, mock_jwt, auth_service):
        """Test JWT token verification with expired token"""
        token = "expired_token"

        import jwt as jwt_module

        mock_jwt.ExpiredSignatureError = jwt_module.ExpiredSignatureError
        mock_jwt.decode.side_effect = jwt_module.ExpiredSignatureError()

        result = auth_service.verify_token(token)

        assert result is None

    @patch("infrastructure.services.auth_service.jwt")
    def test_verify_token_invalid(self, mock_jwt, auth_service):
        """Test JWT token verification with invalid token"""
        token = "invalid_token"

        import jwt as jwt_module

        mock_jwt.InvalidTokenError = jwt_module.InvalidTokenError
        mock_jwt.decode.side_effect = jwt_module.InvalidTokenError()

        result = auth_service.verify_token(token)

        assert result is None

    def test_create_token_pair(self, auth_service):
        """Test creating access and refresh token pair"""
        user_id = "123e4567-e89b-12d3-a456-426614174000"
        email = "test@example.com"

        with (
            patch.object(auth_service, "create_access_token") as mock_access,
            patch.object(auth_service, "create_refresh_token") as mock_refresh,
        ):
            mock_access.return_value = "access_token"
            mock_refresh.return_value = "refresh_token"

            access_token, refresh_token = auth_service.create_token_pair(user_id, email)

            assert access_token == "access_token"
            assert refresh_token == "refresh_token"

            mock_access.assert_called_once_with(user_id, email)
            mock_refresh.assert_called_once_with(user_id)

    def test_refresh_access_token_valid(self, auth_service):
        """Test refreshing access token with valid refresh token"""
        refresh_token = "valid_refresh_token"

        with (
            patch.object(auth_service, "verify_token") as mock_verify,
            patch.object(auth_service, "create_access_token") as mock_create,
        ):
            mock_verify.return_value = {"sub": "user_123", "type": "refresh"}
            mock_create.return_value = "new_access_token"

            result = auth_service.refresh_access_token(refresh_token)

            assert result == "new_access_token"
            mock_verify.assert_called_once_with(refresh_token)
            mock_create.assert_called_once_with("user_123", "")

    def test_refresh_access_token_invalid_type(self, auth_service):
        """Test refreshing access token with wrong token type"""
        refresh_token = "access_token_not_refresh"

        with patch.object(auth_service, "verify_token") as mock_verify:
            mock_verify.return_value = {"sub": "user_123", "type": "access"}

            result = auth_service.refresh_access_token(refresh_token)

            assert result is None

    def test_refresh_access_token_invalid_token(self, auth_service):
        """Test refreshing access token with invalid token"""
        refresh_token = "invalid_token"

        with patch.object(auth_service, "verify_token") as mock_verify:
            mock_verify.return_value = None

            result = auth_service.refresh_access_token(refresh_token)

            assert result is None

    def test_extract_user_id_from_token_valid(self, auth_service):
        """Test extracting user ID from valid access token"""
        token = "valid_access_token"

        with patch.object(auth_service, "verify_token") as mock_verify:
            mock_verify.return_value = {"sub": "user_123", "type": "access"}

            result = auth_service.extract_user_id_from_token(token)

            assert result == "user_123"

    def test_extract_user_id_from_token_wrong_type(self, auth_service):
        """Test extracting user ID from refresh token"""
        token = "refresh_token"

        with patch.object(auth_service, "verify_token") as mock_verify:
            mock_verify.return_value = {"sub": "user_123", "type": "refresh"}

            result = auth_service.extract_user_id_from_token(token)

            assert result is None

    def test_is_token_valid_true(self, auth_service):
        """Test token validity check with valid token"""
        token = "valid_token"

        with patch.object(auth_service, "verify_token") as mock_verify:
            mock_verify.return_value = {"sub": "user_123"}

            result = auth_service.is_token_valid(token)

            assert result is True

    def test_is_token_valid_false(self, auth_service):
        """Test token validity check with invalid token"""
        token = "invalid_token"

        with patch.object(auth_service, "verify_token") as mock_verify:
            mock_verify.return_value = None

            result = auth_service.is_token_valid(token)

            assert result is False

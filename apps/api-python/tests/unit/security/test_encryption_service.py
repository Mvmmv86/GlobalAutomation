"""Unit tests for EncryptionService"""

import pytest
import base64
import os
import secrets
from unittest.mock import patch
from datetime import datetime, timedelta

from infrastructure.security.encryption_service import (
    EncryptionService,
    EncryptionError,
)


class TestEncryptionService:
    """Test cases for EncryptionService"""

    @pytest.fixture
    def test_master_key(self):
        """Generate test master key"""
        return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()

    @pytest.fixture
    def encryption_service(self, test_master_key):
        """Create EncryptionService instance for testing"""
        return EncryptionService(test_master_key)

    @pytest.fixture
    def encryption_service_no_key(self):
        """Create EncryptionService without master key (will generate one)"""
        with patch.dict(os.environ, {}, clear=True):
            with patch(
                "infrastructure.security.encryption_service.logger"
            ) as mock_logger:
                service = EncryptionService()
                mock_logger.warning.assert_called_once()
                return service

    def test_initialization_with_master_key(self, test_master_key):
        """Test EncryptionService initialization with provided master key"""
        service = EncryptionService(test_master_key)

        assert service._master_key == test_master_key
        assert service._fernet is not None
        assert service._cache == {}
        assert service._cache_expiry == 300

    def test_initialization_without_master_key(self):
        """Test EncryptionService initialization without master key"""
        with patch.dict(os.environ, {}, clear=True):
            with patch(
                "infrastructure.security.encryption_service.logger"
            ) as mock_logger:
                service = EncryptionService()

                mock_logger.warning.assert_called_once()
                assert service._master_key is not None
                assert len(service._master_key) > 0

    def test_initialization_with_env_key(self):
        """Test EncryptionService initialization with environment variable"""
        test_key = "test_key_from_env"
        with patch.dict(os.environ, {"ENCRYPTION_MASTER_KEY": test_key}):
            service = EncryptionService()

            assert service._master_key == test_key

    def test_encrypt_string_basic(self, encryption_service):
        """Test basic string encryption"""
        plaintext = "sensitive_api_key_123"

        encrypted = encryption_service.encrypt_string(plaintext)

        assert encrypted != plaintext
        assert len(encrypted) > 0
        assert isinstance(encrypted, str)

    def test_encrypt_string_with_context(self, encryption_service):
        """Test string encryption with context"""
        plaintext = "api_key_with_context"
        context = "binance:user123"

        encrypted = encryption_service.encrypt_string(plaintext, context)

        assert encrypted != plaintext
        assert len(encrypted) > 0

    def test_encrypt_empty_string(self, encryption_service):
        """Test encrypting empty string"""
        encrypted = encryption_service.encrypt_string("")

        assert encrypted == ""

    def test_decrypt_string_basic(self, encryption_service):
        """Test basic string decryption"""
        plaintext = "test_decryption_data"

        encrypted = encryption_service.encrypt_string(plaintext)
        decrypted = encryption_service.decrypt_string(encrypted)

        assert decrypted == plaintext

    def test_decrypt_string_with_context(self, encryption_service):
        """Test string decryption with context"""
        plaintext = "context_test_data"
        context = "exchange:user456"

        encrypted = encryption_service.encrypt_string(plaintext, context)
        decrypted = encryption_service.decrypt_string(encrypted, context)

        assert decrypted == plaintext

    def test_decrypt_empty_string(self, encryption_service):
        """Test decrypting empty string"""
        decrypted = encryption_service.decrypt_string("")

        assert decrypted == ""

    def test_decrypt_with_wrong_context(self, encryption_service):
        """Test decryption with wrong context fails"""
        plaintext = "context_sensitive_data"
        correct_context = "binance:user123"
        wrong_context = "bybit:user456"

        encrypted = encryption_service.encrypt_string(plaintext, correct_context)

        with pytest.raises(EncryptionError, match="Invalid context"):
            encryption_service.decrypt_string(encrypted, wrong_context)

    def test_encrypt_api_key(self, encryption_service):
        """Test API key encryption with context"""
        api_key = "test_api_key_12345"
        exchange = "binance"
        user_id = "user789"

        encrypted = encryption_service.encrypt_api_key(api_key, exchange, user_id)
        decrypted = encryption_service.decrypt_api_key(encrypted, exchange, user_id)

        assert decrypted == api_key

    def test_encrypt_api_secret(self, encryption_service):
        """Test API secret encryption with context"""
        api_secret = "super_secret_key_67890"
        exchange = "bybit"
        user_id = "user456"

        encrypted = encryption_service.encrypt_api_secret(api_secret, exchange, user_id)
        decrypted = encryption_service.decrypt_api_secret(encrypted, exchange, user_id)

        assert decrypted == api_secret

    def test_decrypt_api_key_wrong_context(self, encryption_service):
        """Test API key decryption with wrong context"""
        api_key = "test_api_key"
        exchange = "binance"
        user_id = "user123"
        wrong_user_id = "user456"

        encrypted = encryption_service.encrypt_api_key(api_key, exchange, user_id)

        with pytest.raises(EncryptionError):
            encryption_service.decrypt_api_key(encrypted, exchange, wrong_user_id)

    def test_encrypt_decrypt_dict(self, encryption_service):
        """Test dictionary encryption and decryption"""
        test_dict = {
            "api_key": "test_key",
            "api_secret": "test_secret",
            "permissions": ["trade", "read"],
        }
        context = "user_config"

        encrypted = encryption_service.encrypt_dict(test_dict, context)
        decrypted = encryption_service.decrypt_dict(encrypted, context)

        assert decrypted == test_dict

    def test_generate_secure_token(self, encryption_service):
        """Test secure token generation"""
        token1 = encryption_service.generate_secure_token()
        token2 = encryption_service.generate_secure_token()

        assert token1 != token2
        assert len(token1) > 0
        assert len(token2) > 0
        assert isinstance(token1, str)
        assert isinstance(token2, str)

    def test_generate_secure_token_custom_length(self, encryption_service):
        """Test secure token generation with custom length"""
        length = 16
        token = encryption_service.generate_secure_token(length)

        # Base64 encoded token will be longer than the byte length
        assert len(token) > length
        assert isinstance(token, str)

    def test_encrypt_with_aes_gcm(self, encryption_service):
        """Test AES-GCM encryption"""
        plaintext = "AES-GCM test data"
        associated_data = "additional_authenticated_data"

        result = encryption_service.encrypt_with_aes_gcm(plaintext, associated_data)

        assert "ciphertext" in result
        assert "key" in result
        assert "nonce" in result
        assert "associated_data" in result
        assert result["associated_data"] == associated_data

    def test_decrypt_with_aes_gcm(self, encryption_service):
        """Test AES-GCM decryption"""
        plaintext = "AES-GCM round trip test"
        associated_data = "auth_data"

        encrypted_data = encryption_service.encrypt_with_aes_gcm(
            plaintext, associated_data
        )
        decrypted = encryption_service.decrypt_with_aes_gcm(encrypted_data)

        assert decrypted == plaintext

    def test_aes_gcm_without_associated_data(self, encryption_service):
        """Test AES-GCM without associated data"""
        plaintext = "AES-GCM without associated data"

        encrypted_data = encryption_service.encrypt_with_aes_gcm(plaintext)
        decrypted = encryption_service.decrypt_with_aes_gcm(encrypted_data)

        assert decrypted == plaintext
        assert encrypted_data["associated_data"] == ""

    def test_cache_functionality(self, encryption_service):
        """Test decryption caching"""
        plaintext = "cached_data_test"

        encrypted = encryption_service.encrypt_string(plaintext)

        # First decryption should cache the result
        decrypted1 = encryption_service.decrypt_string(encrypted)
        assert decrypted1 == plaintext

        # Second decryption should use cache
        decrypted2 = encryption_service.decrypt_string(encrypted)
        assert decrypted2 == plaintext

        # Verify cache contains the data
        cache_key = f"{encrypted}:"
        assert cache_key in encryption_service._cache

    def test_cache_expiry(self, encryption_service):
        """Test cache expiry functionality"""
        plaintext = "cache_expiry_test"

        # Set short cache expiry for testing
        encryption_service._cache_expiry = 0  # Immediate expiry

        encrypted = encryption_service.encrypt_string(plaintext)

        # First decryption
        decrypted1 = encryption_service.decrypt_string(encrypted)
        assert decrypted1 == plaintext

        # Wait for cache to expire (simulate with manual expiry)
        cache_key = f"{encrypted}:"
        if cache_key in encryption_service._cache:
            encryption_service._cache[cache_key]["expiry"] = datetime.now() - timedelta(
                seconds=1
            )

        # Second decryption should re-decrypt (not use expired cache)
        decrypted2 = encryption_service.decrypt_string(encrypted)
        assert decrypted2 == plaintext

    def test_clear_cache(self, encryption_service):
        """Test cache clearing"""
        plaintext = "cache_clear_test"

        encrypted = encryption_service.encrypt_string(plaintext)
        encryption_service.decrypt_string(encrypted)  # Cache the result

        assert len(encryption_service._cache) > 0

        encryption_service.clear_cache()

        assert len(encryption_service._cache) == 0

    def test_rotate_master_key(self, encryption_service, test_master_key):
        """Test master key rotation"""
        new_key = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()

        new_service = encryption_service.rotate_master_key(new_key)

        assert new_service._master_key == new_key
        assert new_service._master_key != encryption_service._master_key
        assert isinstance(new_service, EncryptionService)

    def test_verify_integrity_success(self, encryption_service):
        """Test integrity verification success"""
        plaintext = "integrity_test_data"
        context = "test_context"

        encrypted = encryption_service.encrypt_string(plaintext, context)

        is_valid = encryption_service.verify_integrity(plaintext, encrypted, context)

        assert is_valid is True

    def test_verify_integrity_failure(self, encryption_service):
        """Test integrity verification failure"""
        plaintext = "original_data"
        wrong_plaintext = "tampered_data"

        encrypted = encryption_service.encrypt_string(plaintext)

        is_valid = encryption_service.verify_integrity(wrong_plaintext, encrypted)

        assert is_valid is False

    def test_verify_integrity_invalid_encrypted_data(self, encryption_service):
        """Test integrity verification with invalid encrypted data"""
        plaintext = "test_data"
        invalid_encrypted = "invalid_encrypted_data"

        is_valid = encryption_service.verify_integrity(plaintext, invalid_encrypted)

        assert is_valid is False

    def test_encryption_error_on_invalid_data(self, encryption_service):
        """Test encryption error handling"""
        with patch.object(
            encryption_service._fernet,
            "encrypt",
            side_effect=Exception("Encryption failed"),
        ):
            with pytest.raises(EncryptionError, match="Failed to encrypt data"):
                encryption_service.encrypt_string("test")

    def test_decryption_error_on_invalid_data(self, encryption_service):
        """Test decryption error handling"""
        invalid_encrypted = "invalid_base64_data"

        with pytest.raises(EncryptionError, match="Failed to decrypt data"):
            encryption_service.decrypt_string(invalid_encrypted)

    def test_create_fernet_cipher_error(self):
        """Test Fernet cipher creation error"""
        with patch(
            "infrastructure.security.encryption_service.Fernet",
            side_effect=Exception("Cipher error"),
        ):
            with pytest.raises(EncryptionError, match="Failed to create cipher"):
                EncryptionService("invalid_key")

    def test_aes_gcm_encryption_error(self, encryption_service):
        """Test AES-GCM encryption error handling"""
        with patch("infrastructure.security.encryption_service.AESGCM") as mock_aesgcm:
            mock_aesgcm.return_value.encrypt.side_effect = Exception("AES-GCM failed")

            with pytest.raises(EncryptionError, match="AES-GCM encryption failed"):
                encryption_service.encrypt_with_aes_gcm("test")

    def test_aes_gcm_decryption_error(self, encryption_service):
        """Test AES-GCM decryption error handling"""
        # Create valid encrypted data first
        encrypted_data = encryption_service.encrypt_with_aes_gcm("test")

        # Then mock the decryption to fail
        with patch("infrastructure.security.encryption_service.AESGCM") as mock_aesgcm:
            mock_aesgcm.return_value.decrypt.side_effect = Exception(
                "AES-GCM decrypt failed"
            )

            with pytest.raises(EncryptionError, match="AES-GCM decryption failed"):
                encryption_service.decrypt_with_aes_gcm(encrypted_data)

    def test_fernet_key_derivation(self):
        """Test Fernet key derivation from non-standard master key"""
        master_key = "custom_master_key_not_base64"

        service = EncryptionService(master_key)

        # Should successfully create service with derived key
        assert service._fernet is not None

        # Test encryption/decryption works
        plaintext = "derivation_test"
        encrypted = service.encrypt_string(plaintext)
        decrypted = service.decrypt_string(encrypted)

        assert decrypted == plaintext

    def test_different_services_different_keys(self):
        """Test that different services with different keys produce different results"""
        key1 = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()
        key2 = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()

        service1 = EncryptionService(key1)
        service2 = EncryptionService(key2)

        plaintext = "cross_service_test"

        encrypted1 = service1.encrypt_string(plaintext)
        encrypted2 = service2.encrypt_string(plaintext)

        # Different keys should produce different encrypted data
        assert encrypted1 != encrypted2

        # Each service should decrypt its own data correctly
        assert service1.decrypt_string(encrypted1) == plaintext
        assert service2.decrypt_string(encrypted2) == plaintext

        # Cross-decryption should fail
        with pytest.raises(EncryptionError):
            service1.decrypt_string(encrypted2)

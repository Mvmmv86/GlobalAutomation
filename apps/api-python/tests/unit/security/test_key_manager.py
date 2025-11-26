"""Unit tests for KeyManager"""

import pytest
import os
import base64
import secrets
from unittest.mock import patch
from datetime import datetime, timedelta

from infrastructure.security.key_manager import KeyManager, KeyManagerError


class TestKeyManager:
    """Test cases for KeyManager"""

    @pytest.fixture
    def key_manager(self):
        """Create KeyManager instance for testing"""
        return KeyManager()

    @pytest.fixture
    def test_key(self):
        """Generate test key"""
        return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()

    def test_initialization(self, key_manager):
        """Test KeyManager initialization"""
        assert key_manager._keys_cache == {}
        assert key_manager._cache_expiry == 300

    def test_get_master_key_from_env(self, key_manager):
        """Test getting master key from environment"""
        test_key = "test_master_key_from_env"

        with patch.dict(os.environ, {"ENCRYPTION_MASTER_KEY": test_key}):
            key = key_manager.get_master_key()

            assert key == test_key

    def test_get_master_key_generate_when_missing(self, key_manager):
        """Test generating master key when not in environment"""
        with patch.dict(os.environ, {}, clear=True):
            with patch("infrastructure.security.key_manager.logger") as mock_logger:
                key = key_manager.get_master_key()

                mock_logger.warning.assert_called_once()
                assert key is not None
                assert len(key) > 0
                assert os.environ["ENCRYPTION_MASTER_KEY"] == key

    def test_get_master_key_custom_name(self, key_manager):
        """Test getting master key with custom environment variable name"""
        custom_key_name = "CUSTOM_ENCRYPTION_KEY"
        test_key = "custom_test_key"

        with patch.dict(os.environ, {custom_key_name: test_key}):
            key = key_manager.get_master_key(custom_key_name)

            assert key == test_key

    def test_generate_key_default_length(self, key_manager):
        """Test generating key with default length"""
        key = key_manager.generate_key()

        assert isinstance(key, str)
        assert len(key) > 0

        # Verify it's valid base64
        decoded = base64.urlsafe_b64decode(key)
        assert len(decoded) == 32  # Default length

    def test_generate_key_custom_length(self, key_manager):
        """Test generating key with custom length"""
        length = 16
        key = key_manager.generate_key(length)

        decoded = base64.urlsafe_b64decode(key)
        assert len(decoded) == length

    def test_rotate_key_success(self, key_manager, test_key):
        """Test successful key rotation"""
        old_key_name = "TEST_OLD_KEY"

        with patch.dict(os.environ, {old_key_name: test_key}):
            with patch("infrastructure.security.key_manager.logger") as mock_logger:
                new_key = key_manager.rotate_key(old_key_name)

                assert new_key != test_key
                assert os.environ[old_key_name] == new_key
                mock_logger.info.assert_called()

                # Check that backup was created
                backup_keys = [
                    k
                    for k in os.environ.keys()
                    if k.startswith(f"{old_key_name}_BACKUP_")
                ]
                assert len(backup_keys) == 1
                assert os.environ[backup_keys[0]] == test_key

    def test_rotate_key_different_target(self, key_manager, test_key):
        """Test key rotation with different target key name"""
        old_key_name = "TEST_OLD_KEY"
        new_key_name = "TEST_NEW_KEY"

        with patch.dict(os.environ, {old_key_name: test_key}):
            new_key = key_manager.rotate_key(old_key_name, new_key_name)

            assert new_key != test_key
            assert os.environ[new_key_name] == new_key
            assert os.environ[old_key_name] == test_key  # Original unchanged

    def test_rotate_key_error(self, key_manager):
        """Test key rotation error handling"""
        with patch.object(
            key_manager, "generate_key", side_effect=Exception("Generate failed")
        ):
            with pytest.raises(KeyManagerError, match="Failed to rotate key"):
                key_manager.rotate_key("TEST_KEY")

    def test_validate_key_valid_base64(self, key_manager, test_key):
        """Test validating valid base64 key"""
        assert key_manager.validate_key(test_key) is True

    def test_validate_key_valid_string(self, key_manager):
        """Test validating valid string key"""
        string_key = "valid_string_key_with_good_length"

        assert key_manager.validate_key(string_key) is True

    def test_validate_key_invalid_empty(self, key_manager):
        """Test validating empty key"""
        assert key_manager.validate_key("") is False
        assert key_manager.validate_key(None) is False

    def test_validate_key_invalid_too_short(self, key_manager):
        """Test validating too short key"""
        short_key = "short"

        assert key_manager.validate_key(short_key) is False

    def test_validate_key_invalid_too_long(self, key_manager):
        """Test validating too long key"""
        long_key = "x" * 300

        assert key_manager.validate_key(long_key) is False

    def test_get_key_info_existing_key(self, key_manager, test_key):
        """Test getting information about existing key"""
        key_name = "TEST_INFO_KEY"

        with patch.dict(os.environ, {key_name: test_key}):
            info = key_manager.get_key_info(key_name)

            assert info["key_name"] == key_name
            assert info["exists"] is True
            assert info["valid"] is True
            assert info["length"] == len(test_key)
            assert info["is_base64"] is True

    def test_get_key_info_nonexistent_key(self, key_manager):
        """Test getting information about non-existent key"""
        key_name = "NONEXISTENT_KEY"

        with patch.dict(os.environ, {}, clear=True):
            info = key_manager.get_key_info(key_name)

            assert info["key_name"] == key_name
            assert info["exists"] is False
            assert info["valid"] is False
            assert info["length"] == 0
            assert info["is_base64"] is False

    def test_get_key_info_string_key(self, key_manager):
        """Test getting information about string key"""
        key_name = "STRING_KEY"
        string_key = "valid_string_key_with_good_length"  # 32 characters

        with patch.dict(os.environ, {key_name: string_key}):
            info = key_manager.get_key_info(key_name)

            assert info["exists"] is True
            assert info["valid"] is True
            assert info["is_base64"] is False

    def test_list_keys_with_prefix(self, key_manager, test_key):
        """Test listing keys with specific prefix"""
        env_vars = {
            "ENCRYPTION_KEY1": test_key,
            "ENCRYPTION_KEY2": "another_key",
            "OTHER_KEY": "should_not_appear",
            "ENCRYPTION_BACKUP": "backup_key",
        }

        with patch.dict(os.environ, env_vars):
            keys = key_manager.list_keys("ENCRYPTION_")

            assert len(keys) == 3
            assert "ENCRYPTION_KEY1" in keys
            assert "ENCRYPTION_KEY2" in keys
            assert "ENCRYPTION_BACKUP" in keys
            assert "OTHER_KEY" not in keys

    def test_cache_key(self, key_manager, test_key):
        """Test caching a key"""
        key_name = "cache_test_key"
        ttl = 10

        key_manager.cache_key(key_name, test_key, ttl)

        assert key_name in key_manager._keys_cache
        cached_data = key_manager._keys_cache[key_name]
        assert cached_data["value"] == test_key
        assert isinstance(cached_data["expiry"], datetime)

    def test_get_cached_key_valid(self, key_manager, test_key):
        """Test getting valid cached key"""
        key_name = "cached_key_test"

        key_manager.cache_key(key_name, test_key, 300)  # 5 minutes TTL

        retrieved_key = key_manager.get_cached_key(key_name)

        assert retrieved_key == test_key

    def test_get_cached_key_expired(self, key_manager, test_key):
        """Test getting expired cached key"""
        key_name = "expired_key_test"

        # Cache with immediate expiry
        key_manager.cache_key(key_name, test_key, 0)

        # Manually expire the key
        if key_name in key_manager._keys_cache:
            key_manager._keys_cache[key_name]["expiry"] = datetime.now() - timedelta(
                seconds=1
            )

        retrieved_key = key_manager.get_cached_key(key_name)

        assert retrieved_key is None
        assert key_name not in key_manager._keys_cache

    def test_get_cached_key_nonexistent(self, key_manager):
        """Test getting non-existent cached key"""
        retrieved_key = key_manager.get_cached_key("nonexistent_key")

        assert retrieved_key is None

    def test_clear_cache(self, key_manager, test_key):
        """Test clearing key cache"""
        key_manager.cache_key("key1", test_key, 300)
        key_manager.cache_key("key2", "another_key", 300)

        assert len(key_manager._keys_cache) == 2

        key_manager.clear_cache()

        assert len(key_manager._keys_cache) == 0

    def test_backup_keys(self, key_manager):
        """Test backing up keys"""
        keys_to_backup = ["KEY1", "KEY2", "KEY3"]
        env_vars = {
            "KEY1": "value1",
            "KEY2": "value2",
            "KEY3": "value3",
            "KEY4": "value4",  # Should not be backed up
        }

        with patch.dict(os.environ, env_vars):
            with patch("infrastructure.security.key_manager.logger") as mock_logger:
                backup_mapping = key_manager.backup_keys(keys_to_backup)

                assert len(backup_mapping) == 3
                assert "KEY1" in backup_mapping
                assert "KEY2" in backup_mapping
                assert "KEY3" in backup_mapping

                # Verify backup keys were created
                for original_key, backup_key in backup_mapping.items():
                    assert backup_key in os.environ
                    assert os.environ[backup_key] == env_vars[original_key]

                mock_logger.info.assert_called()

    def test_restore_keys(self, key_manager):
        """Test restoring keys from backup"""
        backup_mapping = {
            "ORIGINAL_KEY1": "BACKUP_KEY1",
            "ORIGINAL_KEY2": "BACKUP_KEY2",
        }

        env_vars = {"BACKUP_KEY1": "restored_value1", "BACKUP_KEY2": "restored_value2"}

        with patch.dict(os.environ, env_vars):
            with patch("infrastructure.security.key_manager.logger") as mock_logger:
                key_manager.restore_keys(backup_mapping)

                assert os.environ["ORIGINAL_KEY1"] == "restored_value1"
                assert os.environ["ORIGINAL_KEY2"] == "restored_value2"
                mock_logger.info.assert_called()

    def test_restore_keys_missing_backup(self, key_manager):
        """Test restoring keys when backup is missing"""
        backup_mapping = {"ORIGINAL_KEY": "MISSING_BACKUP_KEY"}

        with patch.dict(os.environ, {}, clear=True):
            with patch("infrastructure.security.key_manager.logger") as mock_logger:
                key_manager.restore_keys(backup_mapping)

                mock_logger.warning.assert_called_with(
                    "Backup MISSING_BACKUP_KEY not found for ORIGINAL_KEY"
                )

    def test_cleanup_backups(self, key_manager):
        """Test cleaning up old backup keys"""
        current_timestamp = int(datetime.now().timestamp())
        old_timestamp = current_timestamp - (25 * 3600)  # 25 hours ago
        recent_timestamp = current_timestamp - (1 * 3600)  # 1 hour ago

        env_vars = {
            f"KEY1_BACKUP_{old_timestamp}": "old_backup1",
            f"KEY2_BACKUP_{old_timestamp}": "old_backup2",
            f"KEY3_BACKUP_{recent_timestamp}": "recent_backup",
            "REGULAR_KEY": "not_a_backup",
            "INVALID_BACKUP_FORMAT": "invalid",
        }

        with patch.dict(os.environ, env_vars):
            with patch("infrastructure.security.key_manager.logger") as mock_logger:
                cleaned_count = key_manager.cleanup_backups(max_age_hours=24)

                assert cleaned_count == 2
                assert f"KEY1_BACKUP_{old_timestamp}" not in os.environ
                assert f"KEY2_BACKUP_{old_timestamp}" not in os.environ
                assert f"KEY3_BACKUP_{recent_timestamp}" in os.environ
                assert "REGULAR_KEY" in os.environ

                mock_logger.info.assert_called()

    def test_cleanup_backups_no_old_keys(self, key_manager):
        """Test cleanup when no old backup keys exist"""
        current_timestamp = int(datetime.now().timestamp())
        recent_timestamp = current_timestamp - (1 * 3600)  # 1 hour ago

        env_vars = {
            f"KEY1_BACKUP_{recent_timestamp}": "recent_backup",
            "REGULAR_KEY": "not_a_backup",
        }

        with patch.dict(os.environ, env_vars):
            cleaned_count = key_manager.cleanup_backups(max_age_hours=24)

            assert cleaned_count == 0
            assert f"KEY1_BACKUP_{recent_timestamp}" in os.environ
            assert "REGULAR_KEY" in os.environ

    def test_cleanup_backups_invalid_format(self, key_manager):
        """Test cleanup with invalid backup key format"""
        env_vars = {
            "INVALID_BACKUP_abc": "invalid_timestamp",
            "KEY_BACKUP_": "empty_timestamp",
            "REGULAR_KEY": "not_a_backup",
        }

        with patch.dict(os.environ, env_vars):
            cleaned_count = key_manager.cleanup_backups()

            assert cleaned_count == 0  # No valid backup keys to clean
            assert all(key in os.environ for key in env_vars.keys())

    def test_validate_key_exception_handling(self, key_manager):
        """Test validate_key exception handling"""
        # Test with a mock that raises an exception
        with patch("base64.urlsafe_b64decode", side_effect=Exception("Decode error")):
            result = key_manager.validate_key("test_key_causes_exception")

            # Should fall back to string validation
            assert result is True  # "test_key_causes_exception" is valid length

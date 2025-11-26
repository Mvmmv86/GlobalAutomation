"""Key management service for handling encryption keys"""

import os
import base64
import secrets
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class KeyManagerError(Exception):
    """Base exception for key management errors"""

    pass


class KeyManager:
    """Service for managing encryption keys and key rotation"""

    def __init__(self):
        """Initialize key manager"""
        self._keys_cache: Dict[str, Any] = {}
        self._cache_expiry = 300  # 5 minutes

    def get_master_key(self, key_name: str = "ENCRYPTION_MASTER_KEY") -> str:
        """
        Get master encryption key from environment or generate one

        Args:
            key_name: Environment variable name for the key

        Returns:
            Master encryption key
        """
        key = os.getenv(key_name)

        if not key:
            # In production, this should be loaded from a secure key management service
            # For development, generate a key and warn
            logger.warning(f"No {key_name} found, generating temporary key")
            key = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()
            os.environ[key_name] = key

        return key

    def generate_key(self, length: int = 32) -> str:
        """
        Generate a new secure key

        Args:
            length: Key length in bytes

        Returns:
            Base64 encoded key
        """
        key_bytes = secrets.token_bytes(length)
        return base64.urlsafe_b64encode(key_bytes).decode()

    def rotate_key(self, old_key_name: str, new_key_name: Optional[str] = None) -> str:
        """
        Rotate an encryption key

        Args:
            old_key_name: Current key environment variable name
            new_key_name: New key environment variable name (if different)

        Returns:
            New key value
        """
        try:
            new_key = self.generate_key()
            target_key_name = new_key_name or old_key_name

            # Store old key for potential rollback
            old_key = os.getenv(old_key_name)
            if old_key:
                backup_key_name = (
                    f"{old_key_name}_BACKUP_{int(datetime.now().timestamp())}"
                )
                os.environ[backup_key_name] = old_key
                logger.info(f"Backed up old key as {backup_key_name}")

            # Set new key
            os.environ[target_key_name] = new_key
            logger.info(f"Rotated key {target_key_name}")

            return new_key

        except Exception as e:
            raise KeyManagerError(f"Failed to rotate key: {str(e)}")

    def validate_key(self, key: str) -> bool:
        """
        Validate that a key is properly formatted

        Args:
            key: Key to validate

        Returns:
            True if key is valid, False otherwise
        """
        try:
            if not key:
                return False

            # Check if it's base64 encoded
            try:
                decoded = base64.urlsafe_b64decode(key)
                # Check reasonable key length (16-64 bytes)
                return 16 <= len(decoded) <= 64
            except:
                # If not base64, check if it's a reasonable string
                return 8 <= len(key) <= 256

        except Exception:
            return False

    def get_key_info(self, key_name: str) -> Dict[str, Any]:
        """
        Get information about a key

        Args:
            key_name: Environment variable name

        Returns:
            Dictionary with key information
        """
        key = os.getenv(key_name)

        info = {
            "key_name": key_name,
            "exists": key is not None,
            "valid": False,
            "length": 0,
            "is_base64": False,
        }

        if key:
            info["valid"] = self.validate_key(key)
            info["length"] = len(key)

            try:
                base64.urlsafe_b64decode(key)
                info["is_base64"] = True
            except:
                info["is_base64"] = False

        return info

    def list_keys(self, prefix: str = "ENCRYPTION_") -> Dict[str, Dict[str, Any]]:
        """
        List all encryption keys in environment

        Args:
            prefix: Key name prefix to filter by

        Returns:
            Dictionary of key information
        """
        keys = {}

        for env_name, env_value in os.environ.items():
            if env_name.startswith(prefix):
                keys[env_name] = self.get_key_info(env_name)

        return keys

    def cache_key(self, key_name: str, key_value: str, ttl_seconds: int = 300):
        """
        Cache a key value temporarily

        Args:
            key_name: Key identifier
            key_value: Key value to cache
            ttl_seconds: Time to live in seconds
        """
        expiry = datetime.now() + timedelta(seconds=ttl_seconds)

        self._keys_cache[key_name] = {"value": key_value, "expiry": expiry}

    def get_cached_key(self, key_name: str) -> Optional[str]:
        """
        Get a cached key value

        Args:
            key_name: Key identifier

        Returns:
            Cached key value or None if not found/expired
        """
        if key_name not in self._keys_cache:
            return None

        cached_data = self._keys_cache[key_name]

        if datetime.now() > cached_data["expiry"]:
            del self._keys_cache[key_name]
            return None

        return cached_data["value"]

    def clear_cache(self):
        """Clear the key cache"""
        self._keys_cache.clear()

    def backup_keys(self, keys: list[str]) -> Dict[str, str]:
        """
        Create backup of specified keys

        Args:
            keys: List of key names to backup

        Returns:
            Dictionary of backed up keys
        """
        backup = {}
        timestamp = int(datetime.now().timestamp())

        for key_name in keys:
            key_value = os.getenv(key_name)
            if key_value:
                backup_name = f"{key_name}_BACKUP_{timestamp}"
                os.environ[backup_name] = key_value
                backup[key_name] = backup_name
                logger.info(f"Backed up {key_name} as {backup_name}")

        return backup

    def restore_keys(self, backup_mapping: Dict[str, str]):
        """
        Restore keys from backup

        Args:
            backup_mapping: Dictionary mapping original key names to backup names
        """
        for original_name, backup_name in backup_mapping.items():
            backup_value = os.getenv(backup_name)
            if backup_value:
                os.environ[original_name] = backup_value
                logger.info(f"Restored {original_name} from {backup_name}")
            else:
                logger.warning(f"Backup {backup_name} not found for {original_name}")

    def cleanup_backups(self, max_age_hours: int = 24):
        """
        Clean up old backup keys

        Args:
            max_age_hours: Maximum age of backups to keep
        """
        current_time = datetime.now().timestamp()
        cutoff_time = current_time - (max_age_hours * 3600)

        keys_to_remove = []

        for env_name in os.environ:
            if "_BACKUP_" in env_name:
                try:
                    # Extract timestamp from backup key name
                    parts = env_name.split("_BACKUP_")
                    if len(parts) == 2:
                        backup_timestamp = int(parts[1])
                        if backup_timestamp < cutoff_time:
                            keys_to_remove.append(env_name)
                except (ValueError, IndexError):
                    # Invalid backup key format, skip
                    continue

        for key_name in keys_to_remove:
            del os.environ[key_name]
            logger.info(f"Cleaned up old backup key: {key_name}")

        return len(keys_to_remove)

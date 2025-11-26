"""Encryption service for sensitive data"""

import base64
import os
import secrets
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import logging

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

logger = logging.getLogger(__name__)


class EncryptionError(Exception):
    """Base exception for encryption errors"""

    pass


class EncryptionService:
    """Service for encrypting/decrypting sensitive data like API keys"""

    def __init__(self, master_key: Optional[str] = None):
        """
        Initialize encryption service

        Args:
            master_key: Master encryption key (if None, will use environment variable)
        """
        self._master_key = master_key or self._get_master_key()
        self._fernet = self._create_fernet_cipher()
        self._cache: Dict[str, Any] = {}
        self._cache_expiry = 300  # 5 minutes

    def _get_master_key(self) -> str:
        """Get master key from environment or generate one"""
        key = os.getenv("ENCRYPTION_MASTER_KEY")

        if not key:
            # In production, this should be loaded from a secure key management service
            # For development, generate a key and warn
            logger.warning("No ENCRYPTION_MASTER_KEY found, generating temporary key")
            key = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()
            os.environ["ENCRYPTION_MASTER_KEY"] = key

        return key

    def _create_fernet_cipher(self) -> Fernet:
        """Create Fernet cipher from master key"""
        try:
            # If master key is already base64 encoded Fernet key, use directly
            if len(self._master_key) == 44:  # Fernet key length
                key = self._master_key.encode()
            else:
                # Derive key from master key using PBKDF2
                salt = b"stable_salt_for_api_keys"  # In production, use random salt per encryption
                kdf = PBKDF2HMAC(
                    algorithm=hashes.SHA256(),
                    length=32,
                    salt=salt,
                    iterations=100000,
                )
                key = base64.urlsafe_b64encode(kdf.derive(self._master_key.encode()))

            return Fernet(key)

        except Exception as e:
            raise EncryptionError(f"Failed to create cipher: {str(e)}")

    def encrypt_string(self, plaintext: str, context: Optional[str] = None) -> str:
        """
        Encrypt a string value

        Args:
            plaintext: The string to encrypt
            context: Optional context for additional security

        Returns:
            Base64 encoded encrypted string
        """
        try:
            if not plaintext:
                return ""

            # Add context if provided
            if context:
                data = f"{context}:{plaintext}".encode()
            else:
                data = plaintext.encode()

            # Encrypt the data
            encrypted = self._fernet.encrypt(data)

            # Return base64 encoded result
            return base64.urlsafe_b64encode(encrypted).decode()

        except Exception as e:
            logger.error(f"Encryption failed: {str(e)}")
            raise EncryptionError(f"Failed to encrypt data: {str(e)}")

    def decrypt_string(self, encrypted_data: str, context: Optional[str] = None) -> str:
        """
        Decrypt a string value

        Args:
            encrypted_data: Base64 encoded encrypted string
            context: Optional context used during encryption

        Returns:
            Decrypted plaintext string
        """
        try:
            if not encrypted_data:
                return ""

            # Check cache first
            cache_key = f"{encrypted_data}:{context or ''}"
            if cache_key in self._cache:
                cached_data = self._cache[cache_key]
                if datetime.now() < cached_data["expiry"]:
                    return cached_data["value"]
                else:
                    del self._cache[cache_key]

            # Decode base64
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode())

            # Decrypt the data
            decrypted = self._fernet.decrypt(encrypted_bytes)

            # Remove context if it was added
            decrypted_str = decrypted.decode()
            if context:
                if decrypted_str.startswith(f"{context}:"):
                    result = decrypted_str[len(context) + 1 :]
                else:
                    raise EncryptionError("Invalid context for decryption")
            else:
                result = decrypted_str

            # Cache the result
            self._cache[cache_key] = {
                "value": result,
                "expiry": datetime.now() + timedelta(seconds=self._cache_expiry),
            }

            return result

        except Exception as e:
            logger.error(f"Decryption failed: {str(e)}")
            raise EncryptionError(f"Failed to decrypt data: {str(e)}")

    def encrypt_api_key(self, api_key: str, exchange: str, user_id: str) -> str:
        """
        Encrypt API key with exchange and user context

        Args:
            api_key: The API key to encrypt
            exchange: Exchange name (binance, bybit, etc.)
            user_id: User ID for additional context

        Returns:
            Encrypted API key
        """
        context = f"{exchange}:{user_id}"
        return self.encrypt_string(api_key, context)

    def decrypt_api_key(self, encrypted_key: str, exchange: str, user_id: str) -> str:
        """
        Decrypt API key with exchange and user context

        Args:
            encrypted_key: The encrypted API key
            exchange: Exchange name (binance, bybit, etc.)
            user_id: User ID for context validation

        Returns:
            Decrypted API key
        """
        context = f"{exchange}:{user_id}"
        return self.decrypt_string(encrypted_key, context)

    def encrypt_api_secret(self, api_secret: str, exchange: str, user_id: str) -> str:
        """
        Encrypt API secret with exchange and user context

        Args:
            api_secret: The API secret to encrypt
            exchange: Exchange name (binance, bybit, etc.)
            user_id: User ID for additional context

        Returns:
            Encrypted API secret
        """
        context = f"{exchange}:{user_id}:secret"
        return self.encrypt_string(api_secret, context)

    def decrypt_api_secret(
        self, encrypted_secret: str, exchange: str, user_id: str
    ) -> str:
        """
        Decrypt API secret with exchange and user context

        Args:
            encrypted_secret: The encrypted API secret
            exchange: Exchange name (binance, bybit, etc.)
            user_id: User ID for context validation

        Returns:
            Decrypted API secret
        """
        context = f"{exchange}:{user_id}:secret"
        return self.decrypt_string(encrypted_secret, context)

    def encrypt_dict(self, data: Dict[str, Any], context: Optional[str] = None) -> str:
        """
        Encrypt a dictionary as JSON

        Args:
            data: Dictionary to encrypt
            context: Optional context

        Returns:
            Encrypted JSON string
        """
        import json

        json_str = json.dumps(data, sort_keys=True)
        return self.encrypt_string(json_str, context)

    def decrypt_dict(
        self, encrypted_data: str, context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Decrypt a dictionary from encrypted JSON

        Args:
            encrypted_data: Encrypted JSON string
            context: Optional context

        Returns:
            Decrypted dictionary
        """
        import json

        json_str = self.decrypt_string(encrypted_data, context)
        return json.loads(json_str)

    def generate_secure_token(self, length: int = 32) -> str:
        """
        Generate a secure random token

        Args:
            length: Token length in bytes

        Returns:
            Base64 encoded secure token
        """
        token_bytes = secrets.token_bytes(length)
        return base64.urlsafe_b64encode(token_bytes).decode()

    def encrypt_with_aes_gcm(
        self, plaintext: str, associated_data: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Encrypt using AES-GCM for authenticated encryption

        Args:
            plaintext: Data to encrypt
            associated_data: Additional authenticated data

        Returns:
            Dictionary with encrypted data, nonce, and tag
        """
        try:
            # Generate random key and nonce
            key = secrets.token_bytes(32)  # 256-bit key
            nonce = secrets.token_bytes(12)  # 96-bit nonce for GCM

            # Create cipher
            aesgcm = AESGCM(key)

            # Encrypt
            ciphertext = aesgcm.encrypt(
                nonce,
                plaintext.encode(),
                associated_data.encode() if associated_data else None,
            )

            return {
                "ciphertext": base64.urlsafe_b64encode(ciphertext).decode(),
                "key": base64.urlsafe_b64encode(key).decode(),
                "nonce": base64.urlsafe_b64encode(nonce).decode(),
                "associated_data": associated_data or "",
            }

        except Exception as e:
            raise EncryptionError(f"AES-GCM encryption failed: {str(e)}")

    def decrypt_with_aes_gcm(self, encrypted_data: Dict[str, str]) -> str:
        """
        Decrypt using AES-GCM

        Args:
            encrypted_data: Dictionary with ciphertext, key, nonce, and associated_data

        Returns:
            Decrypted plaintext
        """
        try:
            # Decode components
            ciphertext = base64.urlsafe_b64decode(encrypted_data["ciphertext"])
            key = base64.urlsafe_b64decode(encrypted_data["key"])
            nonce = base64.urlsafe_b64decode(encrypted_data["nonce"])
            associated_data = encrypted_data.get("associated_data")

            # Create cipher
            aesgcm = AESGCM(key)

            # Decrypt
            plaintext = aesgcm.decrypt(
                nonce, ciphertext, associated_data.encode() if associated_data else None
            )

            return plaintext.decode()

        except Exception as e:
            raise EncryptionError(f"AES-GCM decryption failed: {str(e)}")

    def clear_cache(self):
        """Clear the decryption cache"""
        self._cache.clear()

    def rotate_master_key(self, new_master_key: str) -> "EncryptionService":
        """
        Create new encryption service with rotated master key

        Args:
            new_master_key: New master key

        Returns:
            New EncryptionService instance with new key
        """
        return EncryptionService(new_master_key)

    def verify_integrity(
        self, plaintext: str, encrypted_data: str, context: Optional[str] = None
    ) -> bool:
        """
        Verify that encrypted data matches plaintext

        Args:
            plaintext: Original plaintext
            encrypted_data: Encrypted version
            context: Optional context

        Returns:
            True if they match, False otherwise
        """
        try:
            decrypted = self.decrypt_string(encrypted_data, context)
            return decrypted == plaintext
        except:
            return False

"""Exchange Credentials Service - Secure API key management"""

from typing import Optional, Dict, Any
from uuid import UUID

from infrastructure.database.repositories.exchange_account import (
    ExchangeAccountRepository,
)
from infrastructure.database.models.exchange_account import (
    ExchangeAccount,
    ExchangeType,
    ExchangeEnvironment,
)
from infrastructure.security.encryption_service import EncryptionService
from infrastructure.security.key_manager import KeyManager


class ExchangeCredentialsService:
    """Service for secure management of exchange API credentials"""

    def __init__(
        self,
        exchange_account_repository: ExchangeAccountRepository,
        encryption_service: EncryptionService,
        key_manager: KeyManager,
    ):
        self.exchange_account_repository = exchange_account_repository
        self.encryption_service = encryption_service
        self.key_manager = key_manager

    async def create_exchange_account(
        self,
        user_id: UUID,
        name: str,
        exchange_type: ExchangeType,
        api_key: str,
        api_secret: str,
        environment: ExchangeEnvironment = ExchangeEnvironment.TESTNET,
        passphrase: Optional[str] = None,
        **kwargs,
    ) -> ExchangeAccount:
        """
        Create a new exchange account with encrypted credentials

        Args:
            user_id: User ID who owns the account
            name: User-friendly account name
            exchange_type: Exchange platform (binance, bybit, etc.)
            api_key: Exchange API key (will be encrypted)
            api_secret: Exchange API secret (will be encrypted)
            environment: testnet or mainnet
            passphrase: Optional passphrase for some exchanges
            **kwargs: Additional account configuration

        Returns:
            Created ExchangeAccount instance
        """
        # Validate API credentials format (basic check)
        if not api_key or not api_secret:
            raise ValueError("API key and secret are required")

        if len(api_key) < 10 or len(api_secret) < 20:
            raise ValueError("API credentials appear to be invalid (too short)")

        # Encrypt credentials using context for additional security
        user_str = str(user_id)
        exchange_str = exchange_type.value

        encrypted_api_key = self.encryption_service.encrypt_api_key(
            api_key, exchange_str, user_str
        )
        encrypted_api_secret = self.encryption_service.encrypt_api_secret(
            api_secret, exchange_str, user_str
        )

        # Encrypt passphrase if provided
        encrypted_passphrase = None
        if passphrase:
            encrypted_passphrase = self.encryption_service.encrypt_string(
                passphrase, f"{exchange_str}:{user_str}:passphrase"
            )

        # Prepare account data
        account_data = {
            "user_id": user_str,
            "name": name,
            "exchange_type": exchange_type,
            "environment": environment,
            "api_key_encrypted": encrypted_api_key,
            "api_secret_encrypted": encrypted_api_secret,
            "passphrase_encrypted": encrypted_passphrase,
            "is_active": True,
            "health_status": "unknown",  # Will be updated on first successful connection
            **kwargs,
        }

        # Create account
        account = await self.exchange_account_repository.create(account_data)

        # Log account creation (without sensitive data)
        import structlog

        logger = structlog.get_logger()
        logger.info(
            "Exchange account created",
            user_id=user_str,
            account_id=str(account.id),
            exchange_type=exchange_type.value,
            environment=environment.value,
        )

        return account

    async def get_decrypted_credentials(
        self, account_id: UUID, user_id: UUID
    ) -> Dict[str, str]:
        """
        Get decrypted credentials for an exchange account

        Args:
            account_id: Exchange account ID
            user_id: User ID (for security validation)

        Returns:
            Dictionary with decrypted credentials

        Raises:
            ValueError: If account not found or user doesn't own it
        """
        # Get account and verify ownership
        account = await self.exchange_account_repository.get(account_id)
        if not account:
            raise ValueError("Exchange account not found")

        if account.user_id != str(user_id):
            raise ValueError("User does not own this exchange account")

        if not account.is_active:
            raise ValueError("Exchange account is inactive")

        # Prepare context for decryption
        user_str = str(user_id)
        exchange_str = account.exchange_type.value

        try:
            # Decrypt credentials
            api_key = self.encryption_service.decrypt_api_key(
                account.api_key_encrypted, exchange_str, user_str
            )
            api_secret = self.encryption_service.decrypt_api_secret(
                account.api_secret_encrypted, exchange_str, user_str
            )

            result = {
                "api_key": api_key,
                "api_secret": api_secret,
                "exchange_type": exchange_str,
                "environment": account.environment.value,
            }

            # Decrypt passphrase if present
            if account.passphrase_encrypted:
                passphrase = self.encryption_service.decrypt_string(
                    account.passphrase_encrypted,
                    f"{exchange_str}:{user_str}:passphrase",
                )
                result["passphrase"] = passphrase

            return result

        except Exception as e:
            import structlog

            logger = structlog.get_logger()
            logger.error(
                "Failed to decrypt exchange credentials",
                account_id=str(account_id),
                user_id=user_str,
                error=str(e),
            )
            raise ValueError("Failed to decrypt credentials")

    async def update_credentials(
        self,
        account_id: UUID,
        user_id: UUID,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        passphrase: Optional[str] = None,
    ) -> bool:
        """
        Update encrypted credentials for an exchange account

        Args:
            account_id: Exchange account ID
            user_id: User ID (for security validation)
            api_key: New API key (optional)
            api_secret: New API secret (optional)
            passphrase: New passphrase (optional)

        Returns:
            True if update successful
        """
        # Get account and verify ownership
        account = await self.exchange_account_repository.get(account_id)
        if not account or account.user_id != str(user_id):
            return False

        # Prepare update data
        update_data = {}
        user_str = str(user_id)
        exchange_str = account.exchange_type.value

        # Encrypt new credentials if provided
        if api_key:
            update_data["api_key_encrypted"] = self.encryption_service.encrypt_api_key(
                api_key, exchange_str, user_str
            )

        if api_secret:
            update_data[
                "api_secret_encrypted"
            ] = self.encryption_service.encrypt_api_secret(
                api_secret, exchange_str, user_str
            )

        if passphrase:
            update_data[
                "passphrase_encrypted"
            ] = self.encryption_service.encrypt_string(
                passphrase, f"{exchange_str}:{user_str}:passphrase"
            )

        # Mark as unknown health since credentials changed
        if update_data:
            update_data["health_status"] = "unknown"

            # Update account
            updated_account = await self.exchange_account_repository.update(
                account_id, update_data
            )

            return updated_account is not None

        return True

    async def verify_credentials(self, account_id: UUID, user_id: UUID) -> bool:
        """
        Verify exchange credentials by testing connection

        Args:
            account_id: Exchange account ID
            user_id: User ID (for security validation)

        Returns:
            True if credentials are valid
        """
        try:
            # Get decrypted credentials
            credentials = await self.get_decrypted_credentials(account_id, user_id)

            # Test connection using appropriate exchange adapter
            from application.services.exchange_adapter_factory import (
                ExchangeAdapterFactory,
            )

            exchange_type = credentials["exchange_type"]
            is_testnet = credentials["environment"] == "testnet"

            adapter = ExchangeAdapterFactory.create_adapter(
                exchange_type=exchange_type,
                api_key=credentials["api_key"],
                api_secret=credentials["api_secret"],
                testnet=is_testnet,
                passphrase=credentials.get("passphrase"),
            )

            # Test connection
            is_valid = await adapter.test_connection()

            if is_valid:
                # Mark account as healthy
                await self.exchange_account_repository.update(
                    account_id,
                    {"health_status": "healthy", "last_health_check": "NOW()"},
                )

            return is_valid

        except Exception as e:
            import structlog

            logger = structlog.get_logger()
            logger.warning(
                "Credential verification failed",
                account_id=str(account_id),
                user_id=str(user_id),
                error=str(e),
            )
            return False

    async def rotate_credentials(
        self, account_id: UUID, user_id: UUID, new_api_key: str, new_api_secret: str
    ) -> bool:
        """
        Rotate API credentials with verification

        Args:
            account_id: Exchange account ID
            user_id: User ID (for security validation)
            new_api_key: New API key
            new_api_secret: New API secret

        Returns:
            True if rotation successful
        """
        # Update credentials
        updated = await self.update_credentials(
            account_id, user_id, new_api_key, new_api_secret
        )

        if updated:
            # Verify new credentials
            verified = await self.verify_credentials(account_id, user_id)

            if verified:
                import structlog

                logger = structlog.get_logger()
                logger.info(
                    "Credentials rotated successfully",
                    account_id=str(account_id),
                    user_id=str(user_id),
                )
                return True
            else:
                # Verification failed, log warning
                import structlog

                logger = structlog.get_logger()
                logger.warning(
                    "Credential rotation completed but verification failed",
                    account_id=str(account_id),
                    user_id=str(user_id),
                )

        return False

    async def get_account_status(
        self, account_id: UUID, user_id: UUID
    ) -> Dict[str, Any]:
        """
        Get comprehensive status of an exchange account

        Args:
            account_id: Exchange account ID
            user_id: User ID (for security validation)

        Returns:
            Account status information
        """
        account = await self.exchange_account_repository.get(account_id)
        if not account or account.user_id != str(user_id):
            raise ValueError("Account not found or access denied")

        return {
            "id": str(account.id),
            "name": account.name,
            "exchange_type": account.exchange_type.value,
            "environment": account.environment.value,
            "is_active": account.is_active,
            "health_status": account.health_status,
            "last_health_check": account.last_health_check,
            "created_at": account.created_at,
            "updated_at": account.updated_at,
            "has_credentials": bool(
                account.api_key_encrypted and account.api_secret_encrypted
            ),
            "has_passphrase": bool(account.passphrase_encrypted),
        }

    async def delete_account(
        self, account_id: UUID, user_id: UUID, permanent: bool = False
    ) -> bool:
        """
        Delete or deactivate an exchange account

        Args:
            account_id: Exchange account ID
            user_id: User ID (for security validation)
            permanent: Whether to permanently delete (vs soft delete)

        Returns:
            True if deletion successful
        """
        account = await self.exchange_account_repository.get(account_id)
        if not account or account.user_id != str(user_id):
            return False

        if permanent:
            # Permanent deletion
            success = await self.exchange_account_repository.delete(account_id)
        else:
            # Soft delete (deactivate)
            updated_account = await self.exchange_account_repository.update(
                account_id, {"is_active": False}
            )
            success = updated_account is not None

        if success:
            import structlog

            logger = structlog.get_logger()
            logger.info(
                "Exchange account deleted",
                account_id=str(account_id),
                user_id=str(user_id),
                permanent=permanent,
            )

        return success

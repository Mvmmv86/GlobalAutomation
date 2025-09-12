"""Service interfaces - Abstract contracts for external services"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from uuid import UUID

from ..models.webhook import TradingViewWebhook


class QueueService(ABC):
    """Abstract queue service for job processing"""

    @abstractmethod
    async def add_execution_job(
        self, alert_id: str, account_id: UUID, webhook: TradingViewWebhook
    ) -> str:
        """Add execution job to queue"""
        pass

    @abstractmethod
    async def add_reconciliation_job(
        self, account_id: UUID, job_data: Dict[str, Any]
    ) -> str:
        """Add reconciliation job to queue"""
        pass


class CryptoService(ABC):
    """Abstract crypto service for encryption/decryption"""

    @abstractmethod
    def encrypt(self, data: str) -> str:
        """Encrypt sensitive data"""
        pass

    @abstractmethod
    def decrypt(self, encrypted_data: str) -> str:
        """Decrypt sensitive data"""
        pass


class AuthService(ABC):
    """Abstract authentication service"""

    @abstractmethod
    async def create_access_token(self, user_id: UUID) -> str:
        """Create JWT access token"""
        pass

    @abstractmethod
    async def verify_token(self, token: str) -> Optional[UUID]:
        """Verify JWT token and return user ID"""
        pass

    @abstractmethod
    async def hash_password(self, password: str) -> str:
        """Hash password"""
        pass

    @abstractmethod
    async def verify_password(self, password: str, hashed: str) -> bool:
        """Verify password against hash"""
        pass


class AccountSelectionService(ABC):
    """Abstract account selection service"""

    @abstractmethod
    async def select_account(
        self, webhook: TradingViewWebhook, user_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """Select best account for webhook execution"""
        pass


class WebhookValidationService(ABC):
    """Abstract webhook validation service"""

    @abstractmethod
    def verify_hmac_signature(self, payload: str, signature: str, secret: str) -> bool:
        """Verify HMAC signature"""
        pass

    @abstractmethod
    def validate_webhook_payload(self, payload: Dict[str, Any]) -> TradingViewWebhook:
        """Validate and parse webhook payload"""
        pass

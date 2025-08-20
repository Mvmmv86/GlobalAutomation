"""Repository interfaces - Abstract contracts for data access"""

from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID

from ..models.user import User
from ..models.exchange_account import ExchangeAccount
from ..models.webhook import WebhookJob


class UserRepository(ABC):
    """Abstract user repository"""

    @abstractmethod
    async def create(self, user: User) -> User:
        """Create a new user"""
        pass

    @abstractmethod
    async def get_by_id(self, user_id: UUID) -> Optional[User]:
        """Get user by ID"""
        pass

    @abstractmethod
    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        pass

    @abstractmethod
    async def update(self, user: User) -> User:
        """Update user"""
        pass

    @abstractmethod
    async def delete(self, user_id: UUID) -> bool:
        """Delete user"""
        pass


class ExchangeAccountRepository(ABC):
    """Abstract exchange account repository"""

    @abstractmethod
    async def create(self, account: ExchangeAccount) -> ExchangeAccount:
        """Create a new exchange account"""
        pass

    @abstractmethod
    async def get_by_id(self, account_id: UUID) -> Optional[ExchangeAccount]:
        """Get account by ID"""
        pass

    @abstractmethod
    async def get_by_user_id(self, user_id: UUID) -> List[ExchangeAccount]:
        """Get all accounts for a user"""
        pass

    @abstractmethod
    async def get_active_by_user_id(self, user_id: UUID) -> List[ExchangeAccount]:
        """Get active accounts for a user"""
        pass

    @abstractmethod
    async def update(self, account: ExchangeAccount) -> ExchangeAccount:
        """Update account"""
        pass

    @abstractmethod
    async def delete(self, account_id: UUID) -> bool:
        """Delete account"""
        pass


class WebhookJobRepository(ABC):
    """Abstract webhook job repository"""

    @abstractmethod
    async def create(self, job: WebhookJob) -> WebhookJob:
        """Create a new webhook job"""
        pass

    @abstractmethod
    async def get_by_id(self, job_id: UUID) -> Optional[WebhookJob]:
        """Get job by ID"""
        pass

    @abstractmethod
    async def get_by_alert_id(self, alert_id: str) -> Optional[WebhookJob]:
        """Get job by alert ID (for idempotency)"""
        pass

    @abstractmethod
    async def get_pending_jobs(self, limit: int = 100) -> List[WebhookJob]:
        """Get pending jobs for processing"""
        pass

    @abstractmethod
    async def update(self, job: WebhookJob) -> WebhookJob:
        """Update job"""
        pass

    @abstractmethod
    async def get_failed_jobs(self, limit: int = 100) -> List[WebhookJob]:
        """Get failed jobs for retry"""
        pass

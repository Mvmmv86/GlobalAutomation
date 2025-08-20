"""FastAPI dependency providers"""

from typing import AsyncGenerator, Tuple
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.di.container import get_container
from infrastructure.database.repositories import (
    UserRepository,
    APIKeyRepository,
    ExchangeAccountRepository,
    WebhookRepository,
    WebhookDeliveryRepository,
    OrderRepository,
    PositionRepository,
)
from infrastructure.security.encryption_service import EncryptionService
from infrastructure.security.key_manager import KeyManager


async def get_database_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for database session"""
    container = await get_container()
    async with container.session_scope() as session:
        yield session


async def get_user_repository(
    session: AsyncSession = Depends(get_database_session),
) -> UserRepository:
    """FastAPI dependency for UserRepository"""
    return UserRepository(session)


async def get_api_key_repository(
    session: AsyncSession = Depends(get_database_session),
) -> APIKeyRepository:
    """FastAPI dependency for APIKeyRepository"""
    return APIKeyRepository(session)


async def get_exchange_account_repository(
    session: AsyncSession = Depends(get_database_session),
) -> ExchangeAccountRepository:
    """FastAPI dependency for ExchangeAccountRepository"""
    return ExchangeAccountRepository(session)


async def get_webhook_repository(
    session: AsyncSession = Depends(get_database_session),
) -> WebhookRepository:
    """FastAPI dependency for WebhookRepository"""
    return WebhookRepository(session)


async def get_webhook_delivery_repository(
    session: AsyncSession = Depends(get_database_session),
) -> WebhookDeliveryRepository:
    """FastAPI dependency for WebhookDeliveryRepository"""
    return WebhookDeliveryRepository(session)


async def get_order_repository(
    session: AsyncSession = Depends(get_database_session),
) -> OrderRepository:
    """FastAPI dependency for OrderRepository"""
    return OrderRepository(session)


async def get_position_repository(
    session: AsyncSession = Depends(get_database_session),
) -> PositionRepository:
    """FastAPI dependency for PositionRepository"""
    return PositionRepository(session)


async def get_repositories(
    session: AsyncSession = Depends(get_database_session),
) -> Tuple[
    UserRepository,
    APIKeyRepository,
    ExchangeAccountRepository,
    WebhookRepository,
    WebhookDeliveryRepository,
    OrderRepository,
    PositionRepository,
]:
    """FastAPI dependency for all repositories"""
    return (
        UserRepository(session),
        APIKeyRepository(session),
        ExchangeAccountRepository(session),
        WebhookRepository(session),
        WebhookDeliveryRepository(session),
        OrderRepository(session),
        PositionRepository(session),
    )


# Import services
from application.services import UserService, WebhookService, ExchangeService
from infrastructure.services.auth_service import AuthService


async def get_user_service(
    user_repo: UserRepository = Depends(get_user_repository),
    api_key_repo: APIKeyRepository = Depends(get_api_key_repository),
) -> UserService:
    """FastAPI dependency for UserService"""
    return UserService(user_repo, api_key_repo)


async def get_webhook_service(
    webhook_repo: WebhookRepository = Depends(get_webhook_repository),
    webhook_delivery_repo: WebhookDeliveryRepository = Depends(
        get_webhook_delivery_repository
    ),
    user_repo: UserRepository = Depends(get_user_repository),
) -> WebhookService:
    """FastAPI dependency for WebhookService"""
    return WebhookService(webhook_repo, webhook_delivery_repo, user_repo)


async def get_exchange_service(
    exchange_account_repo: ExchangeAccountRepository = Depends(
        get_exchange_account_repository
    ),
    order_repo: OrderRepository = Depends(get_order_repository),
    position_repo: PositionRepository = Depends(get_position_repository),
    user_repo: UserRepository = Depends(get_user_repository),
) -> ExchangeService:
    """FastAPI dependency for ExchangeService"""
    return ExchangeService(exchange_account_repo, order_repo, position_repo, user_repo)


async def get_auth_service() -> AuthService:
    """FastAPI dependency for AuthService"""
    return AuthService()


# Repository dependency shortcuts
UserRepo = Depends(get_user_repository)
APIKeyRepo = Depends(get_api_key_repository)
ExchangeAccountRepo = Depends(get_exchange_account_repository)
WebhookRepo = Depends(get_webhook_repository)
WebhookDeliveryRepo = Depends(get_webhook_delivery_repository)
OrderRepo = Depends(get_order_repository)
PositionRepo = Depends(get_position_repository)

# Service dependency shortcuts
UserSvc = Depends(get_user_service)
WebhookSvc = Depends(get_webhook_service)
ExchangeSvc = Depends(get_exchange_service)
AuthSvc = Depends(get_auth_service)


# Security services
async def get_encryption_service() -> EncryptionService:
    """FastAPI dependency for EncryptionService"""
    container = await get_container()
    return container.get("encryption_service")


async def get_key_manager() -> KeyManager:
    """FastAPI dependency for KeyManager"""
    container = await get_container()
    return container.get("key_manager")


# Security dependency shortcuts
EncryptionSvc = Depends(get_encryption_service)
KeyMgr = Depends(get_key_manager)

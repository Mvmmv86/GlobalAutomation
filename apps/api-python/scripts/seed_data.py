#!/usr/bin/env python3
"""Seed data script for trading platform development environment"""

import asyncio
import os
import sys
from decimal import Decimal
from datetime import datetime, timezone
from uuid import uuid4

# Add parent directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from infrastructure.database.models import (
    User,
    ExchangeAccount,
    Webhook,
    Order,
    Position,
)
from infrastructure.database.models.user import APIKey
from infrastructure.database.models.exchange_account import ExchangeType
from infrastructure.database.models.webhook import WebhookStatus
from infrastructure.database.models.order import OrderType, OrderSide, OrderStatus
from infrastructure.database.models.position import PositionSide, PositionStatus
from infrastructure.security.encryption_service import EncryptionService


async def get_database_session() -> AsyncSession:
    """Create database session"""
    # Use development database URL
    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres@localhost:5432/trading_platform_dev",
    )

    engine = create_async_engine(database_url, echo=True)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    return async_session()


async def create_demo_users(session: AsyncSession) -> list[User]:
    """Create demo users"""
    from passlib.context import CryptContext

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    users = [
        User(
            id=str(uuid4()),
            email="demo@tradingplatform.com",
            name="Demo User",
            password_hash=pwd_context.hash("demo123"),
            is_active=True,
            is_verified=True,
            totp_enabled=False,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        ),
        User(
            id=str(uuid4()),
            email="trader@tradingplatform.com",
            name="Pro Trader",
            password_hash=pwd_context.hash("trader123"),
            is_active=True,
            is_verified=True,
            totp_enabled=True,
            totp_secret="DEMO_SECRET_KEY_12345678",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        ),
        User(
            id=str(uuid4()),
            email="admin@tradingplatform.com",
            name="Platform Admin",
            password_hash=pwd_context.hash("admin123"),
            is_active=True,
            is_verified=True,
            totp_enabled=True,
            totp_secret="ADMIN_SECRET_KEY_87654321",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        ),
    ]

    for user in users:
        session.add(user)

    await session.flush()
    print(f"✅ Created {len(users)} demo users")
    return users


async def create_api_keys(session: AsyncSession, users: list[User]) -> list[APIKey]:
    """Create API keys for demo users"""
    import hashlib
    import secrets

    api_keys = []

    for i, user in enumerate(users):
        # Generate API key
        key = f"tp_{''.join(secrets.choice('abcdefghijklmnopqrstuvwxyz0123456789') for _ in range(32))}"
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        prefix = key[:8]

        api_key = APIKey(
            id=str(uuid4()),
            name=f"Demo API Key {i + 1}",
            key_hash=key_hash,
            prefix=prefix,
            is_active=True,
            permissions={"trading": True, "read_only": False},
            rate_limit_per_minute=100,
            rate_limit_per_hour=5000,
            user_id=user.id,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        api_keys.append(api_key)
        session.add(api_key)

        # Print the actual key for development use
        print(f"🔑 API Key for {user.email}: {key}")

    await session.flush()
    print(f"✅ Created {len(api_keys)} API keys")
    return api_keys


async def create_exchange_accounts(
    session: AsyncSession, users: list[User]
) -> list[ExchangeAccount]:
    """Create demo exchange accounts"""
    encryption_service = EncryptionService()

    accounts = []

    for user in users:
        # Binance testnet account
        binance_account = ExchangeAccount(
            id=str(uuid4()),
            name="Binance Testnet",
            exchange=ExchangeType.BINANCE,
            api_key=encryption_service.encrypt("demo_binance_api_key_123"),
            secret_key=encryption_service.encrypt("demo_binance_secret_key_456"),
            testnet=True,
            is_active=True,
            user_id=user.id,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        # Bybit testnet account
        bybit_account = ExchangeAccount(
            id=str(uuid4()),
            name="Bybit Testnet",
            exchange=ExchangeType.BYBIT,
            api_key=encryption_service.encrypt("demo_bybit_api_key_789"),
            secret_key=encryption_service.encrypt("demo_bybit_secret_key_012"),
            testnet=True,
            is_active=True,
            user_id=user.id,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        accounts.extend([binance_account, bybit_account])
        session.add(binance_account)
        session.add(bybit_account)

    await session.flush()
    print(f"✅ Created {len(accounts)} exchange accounts")
    return accounts


async def create_webhooks(session: AsyncSession, users: list[User]) -> list[Webhook]:
    """Create demo webhooks"""
    import secrets

    webhooks = []

    for i, user in enumerate(users):
        webhook = Webhook(
            id=str(uuid4()),
            name=f"TradingView Strategy {i + 1}",
            url_path=f"webhook/{secrets.token_urlsafe(16)}",
            secret=secrets.token_urlsafe(32),
            status=WebhookStatus.ACTIVE,
            is_public=False,
            rate_limit_per_minute=60,
            rate_limit_per_hour=1000,
            max_retries=3,
            retry_delay_seconds=60,
            user_id=user.id,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        webhooks.append(webhook)
        session.add(webhook)

        print(f"🔗 Webhook for {user.email}: /webhook/{webhook.url_path}")

    await session.flush()
    print(f"✅ Created {len(webhooks)} webhooks")
    return webhooks


async def create_sample_orders(
    session: AsyncSession, accounts: list[ExchangeAccount]
) -> list[Order]:
    """Create sample orders for demonstration"""
    orders = []

    symbols = ["BTCUSDT", "ETHUSDT", "ADAUSDT"]

    for account in accounts[:2]:  # Only first 2 accounts
        for i, symbol in enumerate(symbols):
            order = Order(
                id=str(uuid4()),
                client_order_id=f"demo_order_{account.exchange}_{i}_{int(datetime.now().timestamp())}",
                symbol=symbol,
                side=OrderSide.BUY if i % 2 == 0 else OrderSide.SELL,
                type=OrderType.LIMIT,
                status=OrderStatus.FILLED if i == 0 else OrderStatus.OPEN,
                quantity=Decimal("0.1"),
                price=Decimal(
                    "45000"
                    if symbol == "BTCUSDT"
                    else "2800"
                    if symbol == "ETHUSDT"
                    else "0.45"
                ),
                filled_quantity=Decimal("0.1") if i == 0 else Decimal("0"),
                average_fill_price=Decimal(
                    "45000"
                    if symbol == "BTCUSDT"
                    else "2800"
                    if symbol == "ETHUSDT"
                    else "0.45"
                )
                if i == 0
                else None,
                fees_paid=Decimal("0.05") if i == 0 else Decimal("0"),
                fee_currency="USDT" if i == 0 else None,
                source="demo",
                exchange_account_id=account.id,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )

            orders.append(order)
            session.add(order)

    await session.flush()
    print(f"✅ Created {len(orders)} sample orders")
    return orders


async def create_sample_positions(
    session: AsyncSession, accounts: list[ExchangeAccount]
) -> list[Position]:
    """Create sample positions for demonstration"""
    positions = []

    symbols = ["BTCUSDT", "ETHUSDT"]

    for account in accounts[:2]:  # Only first 2 accounts
        for i, symbol in enumerate(symbols):
            position = Position(
                id=str(uuid4()),
                symbol=symbol,
                side=PositionSide.LONG,
                status=PositionStatus.OPEN,
                size=Decimal("0.1"),
                entry_price=Decimal("45000" if symbol == "BTCUSDT" else "2800"),
                mark_price=Decimal("46000" if symbol == "BTCUSDT" else "2850"),
                unrealized_pnl=Decimal("100" if symbol == "BTCUSDT" else "5"),
                realized_pnl=Decimal("0"),
                initial_margin=Decimal("450" if symbol == "BTCUSDT" else "28"),
                maintenance_margin=Decimal("225" if symbol == "BTCUSDT" else "14"),
                leverage=Decimal("10.00"),
                liquidation_price=Decimal("40500" if symbol == "BTCUSDT" else "2520"),
                opened_at=datetime.now(timezone.utc),
                last_update_at=datetime.now(timezone.utc),
                total_fees=Decimal("2.25"),
                funding_fees=Decimal("0.50"),
                exchange_account_id=account.id,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )

            positions.append(position)
            session.add(position)

    await session.flush()
    print(f"✅ Created {len(positions)} sample positions")
    return positions


async def main():
    """Main seed function"""
    print("🌱 Starting database seeding...")

    try:
        session = await get_database_session()

        # Create all seed data
        users = await create_demo_users(session)
        api_keys = await create_api_keys(session, users)
        accounts = await create_exchange_accounts(session, users)
        webhooks = await create_webhooks(session, users)
        orders = await create_sample_orders(session, accounts)
        positions = await create_sample_positions(session, accounts)

        # Commit all changes
        await session.commit()
        await session.close()

        print("\n🎉 Database seeding completed successfully!")
        print("\n📊 Summary:")
        print(f"   - Users: {len(users)}")
        print(f"   - API Keys: {len(api_keys)}")
        print(f"   - Exchange Accounts: {len(accounts)}")
        print(f"   - Webhooks: {len(webhooks)}")
        print(f"   - Orders: {len(orders)}")
        print(f"   - Positions: {len(positions)}")

        print("\n🔐 Demo Credentials:")
        print("   - demo@tradingplatform.com / demo123")
        print("   - trader@tradingplatform.com / trader123")
        print("   - admin@tradingplatform.com / admin123")

    except Exception as e:
        print(f"❌ Error during seeding: {e}")
        if "session" in locals():
            await session.rollback()
            await session.close()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

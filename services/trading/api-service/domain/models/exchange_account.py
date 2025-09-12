"""Exchange Account domain model - Core business logic for trading accounts"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID


class ExchangeType(str, Enum):
    """Supported exchanges"""

    BINANCE = "binance"
    BYBIT = "bybit"


@dataclass
class ExchangeAccount:
    """Exchange account entity for trading"""

    id: UUID
    name: str
    exchange: ExchangeType
    testnet: bool
    is_active: bool
    user_id: UUID
    created_at: datetime
    updated_at: datetime

    # Encrypted credentials (handled by infrastructure layer)
    encrypted_api_key: str
    encrypted_secret_key: str
    encrypted_passphrase: Optional[str] = None

    def __post_init__(self):
        """Validate account data"""
        if not self.name or len(self.name.strip()) == 0:
            raise ValueError("Account name cannot be empty")

        if len(self.name) > 100:
            raise ValueError("Account name too long (max 100 characters)")

        if not self.encrypted_api_key:
            raise ValueError("API key is required")

        if not self.encrypted_secret_key:
            raise ValueError("Secret key is required")

    def activate(self) -> None:
        """Activate trading account"""
        self.is_active = True

    def deactivate(self) -> None:
        """Deactivate trading account"""
        self.is_active = False

    def switch_to_live(self) -> None:
        """Switch to live trading (production)"""
        if not self.testnet:
            raise ValueError("Account is already in live mode")
        self.testnet = False

    def switch_to_testnet(self) -> None:
        """Switch to testnet (paper trading)"""
        if self.testnet:
            raise ValueError("Account is already in testnet mode")
        self.testnet = True

    def update_name(self, new_name: str) -> None:
        """Update account name"""
        if not new_name or len(new_name.strip()) == 0:
            raise ValueError("Account name cannot be empty")
        if len(new_name) > 100:
            raise ValueError("Account name too long (max 100 characters)")
        self.name = new_name.strip()

    def is_production_ready(self) -> bool:
        """Check if account is ready for production trading"""
        return (
            self.is_active
            and not self.testnet
            and self.encrypted_api_key
            and self.encrypted_secret_key
        )

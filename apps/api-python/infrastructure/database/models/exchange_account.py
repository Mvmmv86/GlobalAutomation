"""Exchange Account model for trading connections"""

from datetime import datetime
from enum import Enum
from typing import List, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from .base import Base


class ExchangeType(str, Enum):
    """Supported exchange types"""

    BINANCE = "binance"
    BYBIT = "bybit"
    # Future exchanges can be added here


class ExchangeEnvironment(str, Enum):
    """Exchange environment types"""

    TESTNET = "testnet"
    MAINNET = "mainnet"


class ExchangeAccount(Base):
    """Exchange account model for storing API credentials and trading configuration"""

    __tablename__ = "exchange_accounts"

    # Basic info
    name: Mapped[str] = mapped_column(String(255), comment="User-friendly account name")

    # ✅ FIX: Map to correct column name 'exchange' (not 'exchange_type')
    exchange_type: Mapped[str] = mapped_column(
        "exchange", String(50), comment="Exchange platform type"
    )

    testnet: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        comment="Whether this is a testnet account"
    )

    # API credentials (encrypted)
    api_key_encrypted: Mapped[str] = mapped_column(
        "api_key", Text, comment="Encrypted exchange API key"
    )

    # ✅ FIX: Map to correct column name 'secret_key' (not 'secret_key_encrypted')
    api_secret_encrypted: Mapped[str] = mapped_column(
        "secret_key", Text, comment="Exchange API secret"
    )

    passphrase_encrypted: Mapped[Optional[str]] = mapped_column(
        "passphrase", Text, comment="Encrypted passphrase (for exchanges that require it)"
    )

    # Status and configuration
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, comment="Account active status"
    )

    # ✅ FIX: Map to correct column name 'is_main' (not 'is_default')
    is_default: Mapped[bool] = mapped_column(
        "is_main", Boolean, default=False, comment="Main account for dashboard"
    )

    # ⚠️ CAMPOS NÃO EXISTEM NO BANCO - Mantidos como @property para compatibilidade
    # Estes campos são usados pelo código mas não existem na tabela real
    # Retornam valores default para não quebrar código existente

    # Relationships
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        comment="User owner ID",
    )

    user: Mapped["User"] = relationship("User", back_populates="exchange_accounts")

    orders: Mapped[List["Order"]] = relationship(
        "Order", back_populates="exchange_account", cascade="all, delete-orphan"
    )

    positions: Mapped[List["Position"]] = relationship(
        "Position", back_populates="exchange_account", cascade="all, delete-orphan"
    )

    # ==================== COMPUTED PROPERTIES ====================
    # Campos que não existem no banco mas são usados pelo código

    @property
    def environment(self) -> ExchangeEnvironment:
        """Get environment as enum"""
        return ExchangeEnvironment.TESTNET if self.testnet else ExchangeEnvironment.MAINNET

    @property
    def health_status(self) -> str:
        """Health status - default 'healthy' se conta ativa"""
        return "healthy" if self.is_active else "unknown"

    @property
    def last_health_check(self) -> Optional[datetime]:
        """Last health check - sempre None (campo não existe)"""
        return None

    @property
    def total_orders(self) -> int:
        """Total orders - sempre 0 (campo não existe)"""
        return 0

    @property
    def successful_orders(self) -> int:
        """Successful orders - sempre 0 (campo não existe)"""
        return 0

    @property
    def failed_orders(self) -> int:
        """Failed orders - sempre 0 (campo não existe)"""
        return 0

    @property
    def last_trade_at(self) -> Optional[datetime]:
        """Last trade timestamp - sempre None (campo não existe)"""
        return None

    @property
    def max_position_size(self) -> Optional[str]:
        """Max position size - sempre None (campo não existe)"""
        return None

    @property
    def max_daily_volume(self) -> Optional[str]:
        """Max daily volume - sempre None (campo não existe)"""
        return None

    @property
    def risk_level(self) -> str:
        """Risk level - sempre 'medium' (campo não existe)"""
        return "medium"

    @property
    def rate_limit_window(self) -> int:
        """Rate limit window - sempre 60s (campo não existe)"""
        return 60

    @property
    def rate_limit_requests(self) -> int:
        """Rate limit requests - sempre 1200 (campo não existe)"""
        return 1200

    def __init__(self, **kwargs):
        """Initialize ExchangeAccount with default values"""
        # ✅ Apenas defaults para campos REAIS no banco
        kwargs.setdefault("testnet", True)
        kwargs.setdefault("is_active", True)
        # Remover defaults de campos que não existem no banco
        super().__init__(**kwargs)

    def activate(self) -> None:
        """Activate exchange account"""
        self.is_active = True

    def deactivate(self) -> None:
        """Deactivate exchange account"""
        self.is_active = False

    def set_as_default(self) -> None:
        """Mark as default account for this exchange"""
        self.is_default = True

    def unset_as_default(self) -> None:
        """Unmark as default account"""
        self.is_default = False

    def update_health_status(self, status: str, error: Optional[str] = None) -> None:
        """Update account health status - NO-OP (campos não existem no banco)"""
        # ⚠️ Método mantido para compatibilidade mas não faz nada
        # Campos health_status, last_health_check, last_error não existem no banco
        pass

    def increment_order_stats(self, success: bool) -> None:
        """Update order statistics - NO-OP (campos não existem no banco)"""
        # ⚠️ Método mantido para compatibilidade mas não faz nada
        # Campos total_orders, successful_orders, failed_orders não existem no banco
        pass

    def get_success_rate(self) -> float:
        """Calculate order success rate - sempre 0 (campos não existem)"""
        return 0.0

    def is_healthy(self) -> bool:
        """Check if account is healthy"""
        return self.is_active and self.health_status in ["healthy", "warning"]

    def can_trade(self) -> bool:
        """Check if account can execute trades"""
        return self.is_active and self.health_status == "healthy"

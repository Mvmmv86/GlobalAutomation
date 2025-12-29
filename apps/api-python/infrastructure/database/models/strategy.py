"""Strategy models for automated trading system"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import List, Optional, Any

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, Integer, Numeric
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB

from .base import Base


class ConfigType(str, Enum):
    """Strategy configuration type"""
    VISUAL = "visual"
    YAML = "yaml"
    PINESCRIPT = "pinescript"


class IndicatorType(str, Enum):
    """Supported indicator types"""
    # Indicadores existentes
    NADARAYA_WATSON = "nadaraya_watson"
    TPO = "tpo"
    RSI = "rsi"
    MACD = "macd"
    EMA = "ema"
    EMA_CROSS = "ema_cross"
    BOLLINGER = "bollinger"
    ATR = "atr"
    VOLUME_PROFILE = "volume_profile"

    # Novos indicadores - Fase 1 (Dez/2025)
    STOCHASTIC = "stochastic"
    STOCHASTIC_RSI = "stochastic_rsi"
    SUPERTREND = "supertrend"

    # Novos indicadores - Fase 2 (Dez/2025)
    ADX = "adx"
    VWAP = "vwap"
    ICHIMOKU = "ichimoku"
    OBV = "obv"


class ConditionType(str, Enum):
    """Condition types for entry/exit"""
    ENTRY_LONG = "entry_long"
    ENTRY_SHORT = "entry_short"
    EXIT_LONG = "exit_long"
    EXIT_SHORT = "exit_short"


class LogicOperator(str, Enum):
    """Logic operators for combining conditions"""
    AND = "AND"
    OR = "OR"


class SignalType(str, Enum):
    """Signal types"""
    LONG = "long"
    SHORT = "short"


class SignalStatus(str, Enum):
    """Signal status"""
    PENDING = "pending"
    EXECUTED = "executed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Strategy(Base):
    """Automated trading strategy configuration"""

    __tablename__ = "strategies"

    # Basic info
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="Strategy name")
    description: Mapped[Optional[str]] = mapped_column(Text, comment="Strategy description")

    # Configuration type
    config_type: Mapped[ConfigType] = mapped_column(
        SQLEnum(ConfigType, native_enum=False, values_callable=lambda x: [e.value for e in x]),
        default=ConfigType.VISUAL,
        comment="Configuration type: visual, yaml, or pinescript"
    )
    config_yaml: Mapped[Optional[str]] = mapped_column(Text, comment="YAML configuration")
    pinescript_source: Mapped[Optional[str]] = mapped_column(Text, comment="Original PineScript source")

    # Documentation for admins
    documentation: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        default=dict,
        comment="Detailed documentation for strategy selection"
    )

    # Trading configuration
    symbols: Mapped[dict] = mapped_column(JSONB, default=list, comment="Array of trading symbols")
    timeframe: Mapped[str] = mapped_column(String(10), default="5m", comment="Timeframe: 1m, 5m, 15m, etc.")

    # State
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, comment="Whether strategy is active")
    is_backtesting: Mapped[bool] = mapped_column(Boolean, default=False, comment="Whether backtesting is running")

    # Bot reference (not a FK - bots table managed separately)
    bot_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False),
        nullable=True,
        comment="Linked bot for signal execution"
    )

    created_by: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False),
        nullable=True,
        comment="User who created the strategy"
    )

    # Relationships
    indicators: Mapped[List["StrategyIndicator"]] = relationship(
        "StrategyIndicator",
        back_populates="strategy",
        cascade="all, delete-orphan",
        order_by="StrategyIndicator.order_index"
    )

    conditions: Mapped[List["StrategyCondition"]] = relationship(
        "StrategyCondition",
        back_populates="strategy",
        cascade="all, delete-orphan",
        order_by="StrategyCondition.order_index"
    )

    signals: Mapped[List["StrategySignal"]] = relationship(
        "StrategySignal",
        back_populates="strategy",
        cascade="all, delete-orphan",
        order_by="StrategySignal.created_at.desc()"
    )

    backtest_results: Mapped[List["StrategyBacktestResult"]] = relationship(
        "StrategyBacktestResult",
        back_populates="strategy",
        cascade="all, delete-orphan",
        order_by="StrategyBacktestResult.created_at.desc()"
    )

    def __init__(self, **kwargs):
        kwargs.setdefault("config_type", ConfigType.VISUAL)
        kwargs.setdefault("symbols", [])
        kwargs.setdefault("timeframe", "5m")
        kwargs.setdefault("is_active", False)
        kwargs.setdefault("is_backtesting", False)
        super().__init__(**kwargs)

    def activate(self) -> None:
        """Activate strategy"""
        self.is_active = True

    def deactivate(self) -> None:
        """Deactivate strategy"""
        self.is_active = False

    def get_symbols_list(self) -> List[str]:
        """Get symbols as Python list"""
        if isinstance(self.symbols, list):
            return self.symbols
        return []


class StrategyIndicator(Base):
    """Indicator configuration for a strategy"""

    __tablename__ = "strategy_indicators"

    # Parent relationship
    strategy_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("strategies.id", ondelete="CASCADE"),
        nullable=False,
        comment="Parent strategy ID"
    )

    # Indicator config
    indicator_type: Mapped[IndicatorType] = mapped_column(
        SQLEnum(IndicatorType, native_enum=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        comment="Indicator type"
    )

    parameters: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        comment="Indicator parameters as JSON"
    )

    order_index: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="Order for evaluation"
    )

    # Relationship
    strategy: Mapped["Strategy"] = relationship("Strategy", back_populates="indicators")

    def __init__(self, **kwargs):
        kwargs.setdefault("parameters", {})
        kwargs.setdefault("order_index", 0)
        super().__init__(**kwargs)

    def get_parameter(self, key: str, default: Any = None) -> Any:
        """Get a specific parameter value"""
        return self.parameters.get(key, default)


class StrategyCondition(Base):
    """Entry/exit condition for a strategy"""

    __tablename__ = "strategy_conditions"

    # Parent relationship
    strategy_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("strategies.id", ondelete="CASCADE"),
        nullable=False,
        comment="Parent strategy ID"
    )

    # Condition config
    condition_type: Mapped[ConditionType] = mapped_column(
        SQLEnum(ConditionType, native_enum=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        comment="Condition type: entry_long, entry_short, exit_long, exit_short"
    )

    conditions: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        comment="Conditions as JSON array"
    )

    logic_operator: Mapped[LogicOperator] = mapped_column(
        SQLEnum(LogicOperator, native_enum=False, values_callable=lambda x: [e.value for e in x]),
        default=LogicOperator.AND,
        comment="Logic operator: AND or OR"
    )

    order_index: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="Order for evaluation"
    )

    # Relationship
    strategy: Mapped["Strategy"] = relationship("Strategy", back_populates="conditions")

    def __init__(self, **kwargs):
        kwargs.setdefault("logic_operator", LogicOperator.AND)
        kwargs.setdefault("order_index", 0)
        super().__init__(**kwargs)

    def get_conditions_list(self) -> List[dict]:
        """Get conditions as Python list"""
        if isinstance(self.conditions, list):
            return self.conditions
        return []


class StrategySignal(Base):
    """Trading signal generated by a strategy"""

    __tablename__ = "strategy_signals"

    # Parent relationship
    strategy_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("strategies.id", ondelete="CASCADE"),
        nullable=False,
        comment="Parent strategy ID"
    )

    # Signal data
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, comment="Trading symbol")

    signal_type: Mapped[SignalType] = mapped_column(
        SQLEnum(SignalType, native_enum=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        comment="Signal type: long or short"
    )

    entry_price: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(20, 8),
        comment="Price at signal generation"
    )

    indicator_values: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        comment="Indicator values at signal time"
    )

    # Status
    status: Mapped[SignalStatus] = mapped_column(
        SQLEnum(SignalStatus, native_enum=False, values_callable=lambda x: [e.value for e in x]),
        default=SignalStatus.PENDING,
        comment="Signal status"
    )

    # Link to bot execution
    bot_signal_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("bot_signals.id", ondelete="SET NULL"),
        comment="Reference to bot_signals table"
    )

    # Relationship
    strategy: Mapped["Strategy"] = relationship("Strategy", back_populates="signals")

    def __init__(self, **kwargs):
        kwargs.setdefault("status", SignalStatus.PENDING)
        super().__init__(**kwargs)

    def mark_executed(self, bot_signal_id: str) -> None:
        """Mark signal as executed"""
        self.status = SignalStatus.EXECUTED
        self.bot_signal_id = bot_signal_id

    def mark_failed(self) -> None:
        """Mark signal as failed"""
        self.status = SignalStatus.FAILED

    def mark_cancelled(self) -> None:
        """Mark signal as cancelled"""
        self.status = SignalStatus.CANCELLED


class StrategyBacktestResult(Base):
    """Backtest result for a strategy"""

    __tablename__ = "strategy_backtest_results"

    # Parent relationship
    strategy_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("strategies.id", ondelete="CASCADE"),
        nullable=False,
        comment="Parent strategy ID"
    )

    # Period
    start_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Backtest start date"
    )

    end_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Backtest end date"
    )

    symbol: Mapped[str] = mapped_column(String(20), nullable=False, comment="Tested symbol")

    # Configuration
    initial_capital: Mapped[Decimal] = mapped_column(
        Numeric(20, 8),
        default=10000,
        comment="Initial capital for backtest"
    )

    leverage: Mapped[int] = mapped_column(Integer, default=10, comment="Leverage used")

    margin_percent: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        default=5.00,
        comment="Margin percentage per trade"
    )

    stop_loss_percent: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        default=2.00,
        comment="Stop loss percentage"
    )

    take_profit_percent: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        default=4.00,
        comment="Take profit percentage"
    )

    include_fees: Mapped[bool] = mapped_column(Boolean, default=True, comment="Include trading fees")
    include_slippage: Mapped[bool] = mapped_column(Boolean, default=True, comment="Include slippage")

    # Metrics
    total_trades: Mapped[int] = mapped_column(Integer, default=0, comment="Total number of trades")
    winning_trades: Mapped[int] = mapped_column(Integer, default=0, comment="Winning trades count")
    losing_trades: Mapped[int] = mapped_column(Integer, default=0, comment="Losing trades count")

    win_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), comment="Win rate percentage")
    profit_factor: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4), comment="Profit factor")

    total_pnl: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 8), comment="Total P&L in USD")
    total_pnl_percent: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4), comment="Total P&L percentage")

    max_drawdown: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4), comment="Maximum drawdown percentage")
    sharpe_ratio: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4), comment="Sharpe ratio")

    # Detailed data
    trades: Mapped[Optional[dict]] = mapped_column(JSONB, comment="List of simulated trades")
    equity_curve: Mapped[Optional[dict]] = mapped_column(JSONB, comment="Equity curve data for charts")

    # Relationship
    strategy: Mapped["Strategy"] = relationship("Strategy", back_populates="backtest_results")

    def __init__(self, **kwargs):
        kwargs.setdefault("initial_capital", Decimal("10000"))
        kwargs.setdefault("leverage", 10)
        kwargs.setdefault("margin_percent", Decimal("5.00"))
        kwargs.setdefault("stop_loss_percent", Decimal("2.00"))
        kwargs.setdefault("take_profit_percent", Decimal("4.00"))
        kwargs.setdefault("include_fees", True)
        kwargs.setdefault("include_slippage", True)
        kwargs.setdefault("total_trades", 0)
        kwargs.setdefault("winning_trades", 0)
        kwargs.setdefault("losing_trades", 0)
        super().__init__(**kwargs)

    def calculate_metrics(self) -> None:
        """Calculate derived metrics from trades"""
        if self.total_trades > 0:
            self.win_rate = Decimal(str((self.winning_trades / self.total_trades) * 100))

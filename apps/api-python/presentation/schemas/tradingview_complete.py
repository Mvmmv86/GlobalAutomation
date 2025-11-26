"""
Schema completo para TradingView baseado nas configurações do frontend
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from enum import Enum


class MarginMode(str, Enum):
    CROSS = "cross"
    ISOLATED = "isolated"


class PositionMode(str, Enum):
    HEDGE = "hedge"
    ONE_WAY = "one-way"


class OrderSizeType(str, Enum):
    PERCENTAGE = "percentage"
    FIXED = "fixed"
    RISK_BASED = "risk_based"


class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP_MARKET = "stop_market"
    STOP_LIMIT = "stop_limit"


class OrderExecutionMode(str, Enum):
    MARKET = "market"
    LIMIT = "limit"
    AUTO = "auto"


class ActionType(str, Enum):
    BUY = "buy"
    SELL = "sell"
    CLOSE = "close"
    CLOSE_LONG = "close_long"
    CLOSE_SHORT = "close_short"


class StrategyType(str, Enum):
    SCALPING = "scalping"
    SWING = "swing"
    POSITION = "position"
    ARBITRAGE = "arbitrage"
    GRID = "grid"
    DCA = "dca"
    MARTINGALE = "martingale"
    CUSTOM = "custom"


# ============== CONFIGURAÇÕES DE CONTA ==============


class AccountTradingSettings(BaseModel):
    """Configurações de Trading da Conta"""

    defaultLeverage: int = Field(10, ge=1, le=125)
    marginMode: MarginMode = MarginMode.CROSS
    positionMode: PositionMode = PositionMode.ONE_WAY
    defaultOrderSize: float = Field(1.0, gt=0)
    orderSizeType: OrderSizeType = OrderSizeType.PERCENTAGE
    orderExecutionMode: OrderExecutionMode = OrderExecutionMode.AUTO


class AccountRiskSettings(BaseModel):
    """Configurações de Risk Management da Conta"""

    maxLossPerTrade: float = Field(2.0, ge=0, le=100)  # percentage
    maxDailyExposure: float = Field(10.0, ge=0, le=100)  # percentage
    maxSimultaneousPositions: int = Field(5, ge=1, le=50)
    maxLeverageLimit: int = Field(20, ge=1, le=125)
    enableStopLoss: bool = True
    enableTakeProfit: bool = True
    enableSlippage: bool = True
    maxSlippage: float = Field(0.1, ge=0, le=10)  # percentage


class AccountApiSettings(BaseModel):
    """Configurações de API da Conta"""

    apiTimeout: int = Field(5000, ge=1000, le=30000)  # ms
    enableApiRetry: bool = True
    maxRetryAttempts: int = Field(3, ge=0, le=10)
    apiRateLimit: int = Field(10, ge=1, le=100)  # requests per second


class AccountWebhookSettings(BaseModel):
    """Configurações de Webhook da Conta"""

    webhookDelay: int = Field(0, ge=0, le=5000)  # ms
    enableWebhookRetry: bool = True
    webhookTimeout: int = Field(10000, ge=1000, le=60000)  # ms
    enableSignalValidation: bool = True
    minVolumeFilter: float = Field(0.0, ge=0)


class ExchangeSpecificSettings(BaseModel):
    """Configurações Específicas da Exchange"""

    favoriteSymbols: List[str] = ["BTCUSDT", "ETHUSDT", "BNBUSDT"]
    preferredTimeframes: List[str] = ["5m", "15m", "1h", "4h"]
    customFees: Dict[str, float] = {"maker": 0.1, "taker": 0.1}


class AccountConfiguration(BaseModel):
    """Configuração Completa da Conta (do frontend)"""

    trading: AccountTradingSettings
    risk: AccountRiskSettings
    api: AccountApiSettings
    webhook: AccountWebhookSettings
    exchange: ExchangeSpecificSettings


# ============== CONFIGURAÇÕES DE WEBHOOK ==============


class WebhookSecuritySettings(BaseModel):
    """Configurações de Segurança do Webhook"""

    enableAuth: bool = True
    secretKey: str = Field(..., min_length=10)
    enableIPWhitelist: bool = False
    allowedIPs: List[str] = []


class WebhookSignalProcessing(BaseModel):
    """Configurações de Processamento de Sinais"""

    enableSignalValidation: bool = True
    requiredFields: List[str] = ["symbol", "side", "quantity"]
    enableDuplicateFilter: bool = True
    duplicateWindowMs: int = Field(5000, ge=1000, le=300000)


class WebhookRiskLimits(BaseModel):
    """Limites de Risk Management do Webhook"""

    enableRiskLimits: bool = True
    maxOrdersPerMinute: int = Field(10, ge=1, le=1000)
    maxDailyOrders: int = Field(100, ge=1, le=10000)
    minOrderSize: float = Field(0.01, gt=0)
    maxOrderSize: float = Field(1000.0, gt=0)


class WebhookExecutionSettings(BaseModel):
    """Configurações de Execução do Webhook"""

    executionDelay: int = Field(0, ge=0, le=10000)  # ms
    enableRetry: bool = True
    maxRetries: int = Field(3, ge=0, le=10)
    retryDelayMs: int = Field(1000, ge=100, le=30000)


class WebhookConfiguration(BaseModel):
    """Configuração Completa do Webhook (do frontend)"""

    name: str = Field(..., min_length=1, max_length=255)
    description: str = Field("", max_length=500)
    exchangeAccountId: str = Field(..., min_length=1)
    strategy: StrategyType = StrategyType.SCALPING
    symbols: List[str] = ["BTCUSDT"]
    status: str = "active"

    security: WebhookSecuritySettings
    signalProcessing: WebhookSignalProcessing
    riskLimits: WebhookRiskLimits
    execution: WebhookExecutionSettings

    # Configurações avançadas
    timeoutMs: int = Field(30000, ge=1000, le=300000)
    enableRateLimit: bool = True
    rateLimit: int = Field(60, ge=1, le=10000)  # per minute


# ============== PAYLOAD TRADINGVIEW COMPLETO ==============


class StopLossConfig(BaseModel):
    """Configuração de Stop Loss"""

    enabled: bool = True
    price: Optional[float] = Field(None, gt=0)
    percentage: Optional[float] = Field(None, gt=0, le=100)
    type: OrderType = OrderType.MARKET
    trigger_type: str = Field(
        "last_price", pattern="^(last_price|mark_price|index_price)$"
    )


class TakeProfitConfig(BaseModel):
    """Configuração de Take Profit"""

    enabled: bool = True
    price: Optional[float] = Field(None, gt=0)
    percentage: Optional[float] = Field(None, gt=0, le=100)
    type: OrderType = OrderType.LIMIT
    trigger_type: str = Field(
        "last_price", pattern="^(last_price|mark_price|index_price)$"
    )


class TradingSignalData(BaseModel):
    """Indicadores e Sinais Técnicos"""

    rsi: Optional[float] = Field(None, ge=0, le=100)
    macd: Optional[float] = None
    volume: Optional[float] = Field(None, ge=0)
    volatility: Optional[float] = Field(None, ge=0, le=100)
    support: Optional[float] = Field(None, gt=0)
    resistance: Optional[float] = Field(None, gt=0)
    signal_strength: str = Field("medium", pattern="^(weak|medium|strong)$")
    confidence: Optional[float] = Field(None, ge=0, le=100)


class StrategyMetadata(BaseModel):
    """Metadados da Estratégia"""

    name: str = Field(..., min_length=1)
    version: str = "1.0"
    timeframe: str = Field(
        "15m", pattern="^(1m|3m|5m|15m|30m|1h|2h|4h|6h|8h|12h|1d|3d|1w|1M)$"
    )
    strategy_type: StrategyType = StrategyType.SCALPING
    description: Optional[str] = None


class RiskManagementConfig(BaseModel):
    """Configuração de Risk Management"""

    position_size_type: OrderSizeType = OrderSizeType.PERCENTAGE
    position_size_value: float = Field(1.0, gt=0)
    max_position_size: float = Field(10.0, gt=0, le=100)  # percentage of portfolio
    max_daily_loss: float = Field(5.0, gt=0, le=100)  # percentage
    max_drawdown: float = Field(10.0, gt=0, le=100)  # percentage
    portfolio_heat: float = Field(2.0, gt=0, le=100)  # percentage
    correlation_limit: float = Field(0.7, ge=-1, le=1)


class PositionConfig(BaseModel):
    """Configuração de Posição"""

    leverage: int = Field(10, ge=1, le=125)
    margin_mode: MarginMode = MarginMode.CROSS
    position_mode: PositionMode = PositionMode.ONE_WAY
    position_side: Optional[str] = Field(None, pattern="^(long|short|both)$")
    reduce_only: bool = False
    close_position: bool = False
    time_in_force: str = Field("GTC", pattern="^(GTC|IOC|FOK)$")
    post_only: bool = False


class ExchangeConfig(BaseModel):
    """Configuração de Exchange"""

    exchange: str = Field(..., min_length=1)
    account_id: str = Field(..., min_length=1)
    symbol_mapping: Dict[str, str] = {}
    api_timeout: int = Field(5000, ge=1000, le=30000)
    enable_retry: bool = True
    max_retry_attempts: int = Field(3, ge=0, le=10)


class WebhookMetadata(BaseModel):
    """Metadados do Webhook"""

    webhook_id: str = Field(..., min_length=1)
    user_id: str = Field(..., min_length=1)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    source: str = "tradingview"
    webhook_version: str = "2.0"
    request_id: Optional[str] = None


class CompleteTradingViewWebhook(BaseModel):
    """
    Payload COMPLETO do TradingView
    Baseado nas configurações do frontend (ConfigureAccountModal + CreateWebhookModal)
    """

    # ============== DADOS BÁSICOS (obrigatórios) ==============
    ticker: str = Field(
        ..., min_length=1, max_length=20, description="Símbolo do ativo (ex: BTCUSDT)"
    )
    action: ActionType = Field(..., description="Ação a ser executada")
    price: Optional[float] = Field(None, gt=0, description="Preço atual do ativo")
    quantity: float = Field(..., gt=0, description="Quantidade base da ordem")
    order_type: OrderType = OrderType.MARKET

    # ============== CONFIGURAÇÕES DE POSIÇÃO ==============
    position: PositionConfig

    # ============== STOP LOSS & TAKE PROFIT ==============
    stop_loss: Optional[StopLossConfig] = None
    take_profit: Optional[TakeProfitConfig] = None

    # ============== RISK MANAGEMENT ==============
    risk_management: RiskManagementConfig

    # ============== CONFIGURAÇÕES DE EXCHANGE ==============
    exchange_config: ExchangeConfig

    # ============== DADOS DA ESTRATÉGIA ==============
    strategy: StrategyMetadata

    # ============== SINAIS TÉCNICOS ==============
    signals: Optional[TradingSignalData] = None

    # ============== CONFIGURAÇÕES DE WEBHOOK ==============
    webhook_config: Dict[str, Any] = Field(
        default_factory=dict, description="Configurações específicas do webhook"
    )

    # ============== CONFIGURAÇÕES DE CONTA ==============
    account_config: Dict[str, Any] = Field(
        default_factory=dict, description="Configurações específicas da conta"
    )

    # ============== METADADOS ==============
    metadata: WebhookMetadata

    @validator("ticker")
    def validate_ticker(cls, v):
        """Validar formato do ticker"""
        if not v.isupper():
            raise ValueError("Ticker deve estar em maiúsculo")
        return v

    @validator("quantity")
    def validate_quantity(cls, v, values):
        """Validar quantidade baseada no risk management"""
        if "risk_management" in values:
            risk = values["risk_management"]
            if risk.position_size_type == OrderSizeType.PERCENTAGE:
                if v > risk.max_position_size:
                    raise ValueError(
                        f"Quantidade excede o limite máximo de {risk.max_position_size}%"
                    )
        return v

    class Config:
        use_enum_values = True
        validate_assignment = True
        extra = "forbid"  # Não permitir campos extras


# ============== RESPONSE SCHEMAS ==============


class WebhookProcessingResult(BaseModel):
    """Resultado do processamento do webhook"""

    success: bool
    message: str
    delivery_id: str
    webhook_id: str
    processing_time_ms: int

    # Estatísticas de execução
    orders_created: int = 0
    orders_executed: int = 0
    orders_failed: int = 0

    # Configurações aplicadas
    leverage_applied: Optional[int] = None
    stop_loss_set: Optional[float] = None
    take_profit_set: Optional[float] = None

    # Detalhes de risk management
    position_size_calculated: Optional[float] = None
    risk_percentage: Optional[float] = None
    portfolio_impact: Optional[float] = None

    # Validações
    validation_passed: bool = True
    validation_warnings: List[str] = []
    validation_errors: List[str] = []

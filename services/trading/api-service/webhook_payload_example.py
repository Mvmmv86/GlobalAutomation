#!/usr/bin/env python3
"""
Exemplo prático de payload TradingView completo
Baseado nas configurações do frontend (ConfigureAccountModal + CreateWebhookModal)
"""

import json
from datetime import datetime
from presentation.schemas.tradingview_complete import (
    CompleteTradingViewWebhook,
    AccountConfiguration,
    WebhookConfiguration,
    PositionConfig,
    StopLossConfig,
    TakeProfitConfig,
    RiskManagementConfig,
    ExchangeConfig,
    StrategyMetadata,
    TradingSignalData,
    WebhookMetadata,
    ActionType,
    OrderType,
    MarginMode,
    PositionMode,
    OrderSizeType,
    StrategyType,
    AccountTradingSettings,
    AccountRiskSettings,
    AccountApiSettings,
    AccountWebhookSettings,
    ExchangeSpecificSettings,
    WebhookSecuritySettings,
    WebhookSignalProcessing,
    WebhookRiskLimits,
    WebhookExecutionSettings
)


def create_complete_payload_example():
    """
    Cria um exemplo completo de payload baseado nas configurações do frontend
    """
    
    # ============== CONFIGURAÇÕES DE CONTA (do ConfigureAccountModal) ==============
    
    account_config = AccountConfiguration(
        trading=AccountTradingSettings(
            defaultLeverage=10,
            marginMode=MarginMode.CROSS,
            positionMode=PositionMode.ONE_WAY,
            defaultOrderSize=1.0,
            orderSizeType=OrderSizeType.PERCENTAGE,
            orderExecutionMode="auto"
        ),
        risk=AccountRiskSettings(
            maxLossPerTrade=2.0,  # 2%
            maxDailyExposure=10.0,  # 10%
            maxSimultaneousPositions=5,
            maxLeverageLimit=20,
            enableStopLoss=True,
            enableTakeProfit=True,
            enableSlippage=True,
            maxSlippage=0.1  # 0.1%
        ),
        api=AccountApiSettings(
            apiTimeout=5000,
            enableApiRetry=True,
            maxRetryAttempts=3,
            apiRateLimit=10
        ),
        webhook=AccountWebhookSettings(
            webhookDelay=0,
            enableWebhookRetry=True,
            webhookTimeout=10000,
            enableSignalValidation=True,
            minVolumeFilter=1000000.0
        ),
        exchange=ExchangeSpecificSettings(
            favoriteSymbols=["BTCUSDT", "ETHUSDT", "BNBUSDT"],
            preferredTimeframes=["5m", "15m", "1h", "4h"],
            customFees={"maker": 0.1, "taker": 0.1}
        )
    )
    
    # ============== CONFIGURAÇÕES DE WEBHOOK (do CreateWebhookModal) ==============
    
    webhook_config = WebhookConfiguration(
        name="RSI Scalping Strategy",
        description="Estratégia de scalping baseada em RSI com stop loss e take profit automático",
        exchangeAccountId="binance_main_account",
        strategy=StrategyType.SCALPING,
        symbols=["BTCUSDT", "ETHUSDT"],
        status="active",
        
        security=WebhookSecuritySettings(
            enableAuth=True,
            secretKey="minha_secret_key_super_secreta_123",
            enableIPWhitelist=False,
            allowedIPs=[]
        ),
        signalProcessing=WebhookSignalProcessing(
            enableSignalValidation=True,
            requiredFields=["symbol", "side", "quantity", "price"],
            enableDuplicateFilter=True,
            duplicateWindowMs=5000
        ),
        riskLimits=WebhookRiskLimits(
            enableRiskLimits=True,
            maxOrdersPerMinute=10,
            maxDailyOrders=100,
            minOrderSize=0.001,
            maxOrderSize=1.0
        ),
        execution=WebhookExecutionSettings(
            executionDelay=100,  # 100ms delay
            enableRetry=True,
            maxRetries=3,
            retryDelayMs=1000
        ),
        timeoutMs=30000,
        enableRateLimit=True,
        rateLimit=60
    )
    
    # ============== PAYLOAD TRADINGVIEW COMPLETO ==============
    
    complete_payload = CompleteTradingViewWebhook(
        # Dados básicos
        ticker="BTCUSDT",
        action=ActionType.BUY,
        price=45123.50,
        quantity=0.1,
        order_type=OrderType.MARKET,
        
        # Configurações de posição (baseado nas configs da conta)
        position=PositionConfig(
            leverage=account_config.trading.defaultLeverage,
            margin_mode=account_config.trading.marginMode,
            position_mode=account_config.trading.positionMode,
            position_side="long",
            reduce_only=False,
            close_position=False,
            time_in_force="GTC",
            post_only=False
        ),
        
        # Stop Loss (baseado nas configs de risk)
        stop_loss=StopLossConfig(
            enabled=account_config.risk.enableStopLoss,
            percentage=2.0,  # 2% de stop loss
            type=OrderType.MARKET,
            trigger_type="last_price"
        ) if account_config.risk.enableStopLoss else None,
        
        # Take Profit (baseado nas configs de risk)
        take_profit=TakeProfitConfig(
            enabled=account_config.risk.enableTakeProfit,
            percentage=4.0,  # 4% de take profit (2:1 risk/reward)
            type=OrderType.LIMIT,
            trigger_type="last_price"
        ) if account_config.risk.enableTakeProfit else None,
        
        # Risk Management (baseado nas configs da conta)
        risk_management=RiskManagementConfig(
            position_size_type=account_config.trading.orderSizeType,
            position_size_value=account_config.trading.defaultOrderSize,
            max_position_size=account_config.risk.maxDailyExposure,
            max_daily_loss=account_config.risk.maxLossPerTrade,
            max_drawdown=5.0,
            portfolio_heat=2.0,
            correlation_limit=0.7
        ),
        
        # Configurações de exchange
        exchange_config=ExchangeConfig(
            exchange="binance",
            account_id=webhook_config.exchangeAccountId,
            symbol_mapping={"binance": "BTCUSDT", "bybit": "BTCUSDT", "okx": "BTC-USDT-SWAP"},
            api_timeout=account_config.api.apiTimeout,
            enable_retry=account_config.api.enableApiRetry,
            max_retry_attempts=account_config.api.maxRetryAttempts
        ),
        
        # Metadados da estratégia
        strategy=StrategyMetadata(
            name=webhook_config.name,
            version="1.0",
            timeframe="15m",
            strategy_type=webhook_config.strategy,
            description=webhook_config.description
        ),
        
        # Sinais técnicos
        signals=TradingSignalData(
            rsi=30.5,
            macd=0.25,
            volume=1234567.89,
            volatility=15.2,
            support=44500.00,
            resistance=45800.00,
            signal_strength="strong",
            confidence=85.5
        ),
        
        # Configurações específicas do webhook
        webhook_config={
            "webhook_id": "webhook_demo_123",
            "enable_notifications": True,
            "notification_email": "trader@example.com",
            "enable_logging": True,
            "custom_headers": {
                "User-Agent": "TradingView-Webhook/2.0",
                "X-Strategy": webhook_config.strategy.value
            }
        },
        
        # Configurações específicas da conta
        account_config={
            "favorite_symbols": account_config.exchange.favoriteSymbols,
            "preferred_timeframes": account_config.exchange.preferredTimeframes,
            "custom_fees": account_config.exchange.customFees,
            "enable_slippage": account_config.risk.enableSlippage,
            "max_slippage": account_config.risk.maxSlippage
        },
        
        # Metadados
        metadata=WebhookMetadata(
            webhook_id="webhook_demo_123",
            user_id="user_demo_456",
            timestamp=datetime.utcnow(),
            source="tradingview",
            webhook_version="2.0",
            request_id="req_789"
        )
    )
    
    return complete_payload


def demo_exchange_adapters(complete_payload: CompleteTradingViewWebhook):
    """
    Demonstra como converter o payload completo para cada exchange
    """
    
    print("🔄 ADAPTANDO PAYLOAD PARA EXCHANGES...")
    print("="*60)
    
    # ============== BINANCE ADAPTER ==============
    def adapt_to_binance(payload):
        # Calcular preços de stop loss e take profit
        entry_price = payload.price
        leverage = payload.position.leverage
        
        stop_loss_price = None
        take_profit_price = None
        
        if payload.stop_loss and payload.stop_loss.enabled:
            if payload.action == ActionType.BUY:
                stop_loss_price = entry_price * (1 - payload.stop_loss.percentage / 100)
            else:
                stop_loss_price = entry_price * (1 + payload.stop_loss.percentage / 100)
        
        if payload.take_profit and payload.take_profit.enabled:
            if payload.action == ActionType.BUY:
                take_profit_price = entry_price * (1 + payload.take_profit.percentage / 100)
            else:
                take_profit_price = entry_price * (1 - payload.take_profit.percentage / 100)
        
        binance_payload = {
            # Dados básicos
            "symbol": payload.ticker,
            "side": payload.action.upper(),
            "type": payload.order_type.upper(),
            "quantity": str(payload.quantity),
            "timeInForce": payload.position.time_in_force,
            
            # Configurações de posição
            "positionSide": payload.position.position_side.upper() if payload.position.position_side else "BOTH",
            "reduceOnly": payload.position.reduce_only,
            "closePosition": payload.position.close_position,
            
            # Risk management
            "stopPrice": str(stop_loss_price) if stop_loss_price else None,
            "workingType": "CONTRACT_PRICE",
            
            # Configurações específicas
            "leverage": payload.position.leverage,
            "marginType": payload.position.margin_mode.upper(),
            
            # Metadados
            "newClientOrderId": f"tv_{payload.metadata.request_id}",
            "timestamp": int(payload.metadata.timestamp.timestamp() * 1000),
        }
        
        # Remover campos None
        return {k: v for k, v in binance_payload.items() if v is not None}
    
    # ============== BYBIT ADAPTER ==============
    def adapt_to_bybit(payload):
        entry_price = payload.price
        
        stop_loss_price = None
        take_profit_price = None
        
        if payload.stop_loss and payload.stop_loss.enabled:
            if payload.action == ActionType.BUY:
                stop_loss_price = entry_price * (1 - payload.stop_loss.percentage / 100)
            else:
                stop_loss_price = entry_price * (1 + payload.stop_loss.percentage / 100)
        
        if payload.take_profit and payload.take_profit.enabled:
            if payload.action == ActionType.BUY:
                take_profit_price = entry_price * (1 + payload.take_profit.percentage / 100)
            else:
                take_profit_price = entry_price * (1 - payload.take_profit.percentage / 100)
        
        bybit_payload = {
            # Identificação
            "category": "linear",
            "symbol": payload.ticker,
            "side": payload.action.capitalize(),
            "orderType": payload.order_type.capitalize(),
            "qty": str(payload.quantity),
            
            # Configurações de posição
            "positionIdx": 1 if payload.position.position_side == "long" else 2 if payload.position.position_side == "short" else 0,
            "reduceOnly": payload.position.reduce_only,
            "closeOnTrigger": payload.position.close_position,
            
            # Stop Loss / Take Profit
            "stopLoss": str(stop_loss_price) if stop_loss_price else None,
            "takeProfit": str(take_profit_price) if take_profit_price else None,
            "slTriggerBy": "LastPrice" if stop_loss_price else None,
            "tpTriggerBy": "LastPrice" if take_profit_price else None,
            
            # Configurações específicas
            "leverage": str(payload.position.leverage),
            "marginMode": 1 if payload.position.margin_mode == MarginMode.ISOLATED else 0,
            
            # Metadados
            "orderLinkId": f"tv_{payload.metadata.request_id}",
        }
        
        # Remover campos None
        return {k: v for k, v in bybit_payload.items() if v is not None}
    
    # ============== DEMONSTRAÇÃO ==============
    
    binance_adapted = adapt_to_binance(complete_payload)
    bybit_adapted = adapt_to_bybit(complete_payload)
    
    print("🟡 BINANCE Payload:")
    print(json.dumps(binance_adapted, indent=2))
    print("\n" + "="*60)
    
    print("🔵 BYBIT Payload:")
    print(json.dumps(bybit_adapted, indent=2))
    print("\n" + "="*60)
    
    return binance_adapted, bybit_adapted


if __name__ == "__main__":
    print("🚀 EXEMPLO DE PAYLOAD TRADINGVIEW COMPLETO")
    print("Baseado nas configurações do frontend (ConfigureAccountModal + CreateWebhookModal)")
    print("="*80)
    
    # Criar payload completo
    payload = create_complete_payload_example()
    
    # Mostrar payload como JSON
    print("\n📦 PAYLOAD COMPLETO:")
    payload_dict = payload.dict()
    print(json.dumps(payload_dict, indent=2, default=str))
    
    print("\n" + "="*80)
    
    # Demonstrar adaptação para exchanges
    demo_exchange_adapters(payload)
    
    print("\n✅ PAYLOAD COMPLETO CRIADO COM SUCESSO!")
    print("🎯 Este payload contém TODAS as configurações do frontend:")
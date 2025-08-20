# 📊 Mapeamento de Payload: TradingView → Exchanges

## 🚨 **Problema Atual**
O payload atual é muito simples para exchanges reais:
```json
{
  "ticker": "BTCUSDT",
  "action": "buy", 
  "price": 45123.50,
  "quantity": 0.1
}
```

## 💰 **O Que As Exchanges Realmente Precisam**

### 1. **Binance Futures API**
```json
{
  // Dados obrigatórios
  "symbol": "BTCUSDT",           // ✅ Temos (ticker)
  "side": "BUY",                 // ✅ Temos (action)
  "type": "MARKET",              // ✅ Temos (order_type)
  "quantity": "0.1",             // ✅ Temos
  "timeInForce": "GTC",          // ❌ FALTA
  
  // Dados de risk management
  "leverage": 10,                // ❌ FALTA - CRÍTICO
  "marginType": "ISOLATED",      // ❌ FALTA - CRÍTICO
  "positionSide": "LONG",        // ❌ FALTA - CRÍTICO
  
  // Stop Loss / Take Profit
  "stopPrice": "44000.00",       // ❌ FALTA
  "workingType": "CONTRACT_PRICE", // ❌ FALTA
  
  // Configurações avançadas
  "reduceOnly": false,           // ❌ FALTA
  "closePosition": false,        // ❌ FALTA
  "activationPrice": "45200.00", // ❌ FALTA
  "callbackRate": "0.1",         // ❌ FALTA
  
  // Timestamps e IDs
  "timestamp": 1642680000000,    // ❌ FALTA
  "recvWindow": 5000,            // ❌ FALTA
  "newClientOrderId": "tv_001"   // ❌ FALTA
}
```

### 2. **Bybit V5 API**
```json
{
  // Identificação
  "category": "linear",          // ❌ FALTA - spot/linear/option
  "symbol": "BTCUSDT",          // ✅ Temos
  "side": "Buy",                // ✅ Temos
  "orderType": "Market",        // ✅ Temos
  "qty": "0.1",                 // ✅ Temos
  
  // Configurações de posição
  "positionIdx": 0,             // ❌ FALTA - hedge mode
  "leverage": "10",             // ❌ FALTA - CRÍTICO
  "marginMode": 1,              // ❌ FALTA - cross/isolated
  
  // Stop Loss / Take Profit
  "stopLoss": "44000",          // ❌ FALTA
  "takeProfit": "46000",        // ❌ FALTA
  "tpTriggerBy": "LastPrice",   // ❌ FALTA
  "slTriggerBy": "LastPrice",   // ❌ FALTA
  
  // Configurações avançadas
  "reduceOnly": false,          // ❌ FALTA
  "closeOnTrigger": false,      // ❌ FALTA
  "orderLinkId": "tv_002"       // ❌ FALTA
}
```

### 3. **OKX API**
```json
{
  // Básico
  "instId": "BTC-USDT-SWAP",    // ❌ FALTA - formato específico
  "side": "buy",                // ✅ Temos
  "ordType": "market",          // ✅ Temos
  "sz": "1",                    // ✅ Temos (contracts, não quantidade)
  
  // Configurações específicas
  "tdMode": "isolated",         // ❌ FALTA - trade mode
  "ccy": "USDT",               // ❌ FALTA - currency
  "posSide": "long",           // ❌ FALTA - position side
  "lever": "10",               // ❌ FALTA - leverage
  
  // Stop Loss / Take Profit  
  "slTriggerPx": "44000",      // ❌ FALTA
  "slOrdPx": "-1",             // ❌ FALTA
  "tpTriggerPx": "46000",      // ❌ FALTA
  "tpOrdPx": "-1",             // ❌ FALTA
  
  // IDs e configurações
  "clOrdId": "tv_003",         // ❌ FALTA
  "tag": "tradingview"         // ❌ FALTA
}
```

## 📝 **Payload TradingView Expandido (Necessário)**

```json
{
  // Dados básicos (que já temos)
  "ticker": "BTCUSDT",
  "action": "buy",              // buy/sell/close
  "price": 45123.50,
  "quantity": 0.1,
  "order_type": "market",       // market/limit/stop
  
  // NOVOS: Configurações de Risk Management
  "leverage": 10,
  "margin_mode": "isolated",    // cross/isolated
  "position_side": "long",      // long/short/both
  "position_size_type": "fixed", // fixed/percentage/risk_based
  
  // NOVOS: Stop Loss / Take Profit
  "stop_loss": {
    "enabled": true,
    "price": 44000.00,
    "type": "market",           // market/limit
    "trigger_type": "last_price" // last_price/mark_price
  },
  "take_profit": {
    "enabled": true,
    "price": 46000.00,
    "type": "limit",
    "trigger_type": "last_price"
  },
  
  // NOVOS: Configurações de Exchange
  "exchange_config": {
    "exchange": "binance",      // binance/bybit/okx
    "account_id": "main_account",
    "symbol_mapping": {
      "binance": "BTCUSDT",
      "bybit": "BTCUSDT", 
      "okx": "BTC-USDT-SWAP"
    }
  },
  
  // NOVOS: Configurações de Posição
  "position_config": {
    "reduce_only": false,
    "close_position": false,
    "time_in_force": "GTC",     // GTC/IOC/FOK
    "post_only": false
  },
  
  // NOVOS: Risk Management Avançado
  "risk_management": {
    "max_position_size": 1.0,
    "max_daily_loss": 1000.00,
    "max_drawdown": 5.0,        // percentage
    "portfolio_heat": 2.0       // percentage of portfolio
  },
  
  // Dados existentes expandidos
  "strategy": {
    "name": "RSI Breakout",
    "version": "1.2",
    "timeframe": "15m",
    "signal_strength": "strong", // weak/medium/strong
    "confidence": 85.5           // percentage
  },
  
  // Indicadores técnicos
  "indicators": {
    "rsi": 30.5,
    "macd": 0.25,
    "volume": 1234567.89,
    "volatility": 0.15,
    "support": 44500.00,
    "resistance": 45800.00
  },
  
  // Metadados
  "metadata": {
    "timestamp": "2025-01-20T15:30:00Z",
    "source": "tradingview",
    "webhook_version": "2.0",
    "user_id": "user_123",
    "strategy_id": "strategy_456"
  }
}
```

## 🔧 **Como Implementar o Mapeamento**

### 1. **Adapter Pattern por Exchange**
```python
class BinanceAdapter:
    def convert_payload(self, tv_payload):
        return {
            "symbol": tv_payload["ticker"],
            "side": tv_payload["action"].upper(),
            "type": tv_payload["order_type"].upper(),
            "quantity": str(tv_payload["quantity"]),
            "leverage": tv_payload["leverage"],
            # ... mais mapeamentos
        }

class BybitAdapter:
    def convert_payload(self, tv_payload):
        return {
            "category": "linear",
            "symbol": tv_payload["ticker"],
            "side": tv_payload["action"].capitalize(),
            # ... mapeamentos específicos do Bybit
        }
```

### 2. **Validação Específica por Exchange**
```python
class ExchangeValidator:
    def validate_binance_payload(self, payload):
        required_fields = ["symbol", "side", "type", "quantity"]
        # Validações específicas da Binance
        
    def validate_bybit_payload(self, payload):
        required_fields = ["category", "symbol", "side", "orderType"]
        # Validações específicas do Bybit
```

## ❓ **Pergunta Crítica**

**Você quer que eu implemente:**
1. ✅ **Payload expandido** com todos os campos necessários?
2. ✅ **Adapters específicos** para cada exchange?
3. ✅ **Validação robusta** por exchange?
4. ✅ **Configuração flexível** de risk management?

**Sem isso, o webhook não funcionará com exchanges reais!**
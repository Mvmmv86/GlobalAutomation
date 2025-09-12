# 🚀 Guia de Teste de Webhooks TradingView

## 📍 URLs Disponíveis

- **Backend**: http://localhost:8000  
- **Webhook Simples**: `POST http://localhost:8000/api/v1/webhooks/tv/test-simple`
- **Webhook Completo**: `POST http://localhost:8000/api/v1/webhooks/tv/webhook_demo_123`

---

## 🧪 TESTE 1: Webhook Simples (Mais Fácil)

### Via cURL:
```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{
    "ticker": "BTCUSDT",
    "action": "buy",
    "price": 45123.50,
    "quantity": 0.1,
    "order_type": "market",
    "message": "Sinal de compra detectado"
  }' \
  http://localhost:8000/api/v1/webhooks/tv/test-simple
```

### Via Postman:
- **Method**: POST
- **URL**: `http://localhost:8000/api/v1/webhooks/tv/test-simple`
- **Headers**: `Content-Type: application/json`
- **Body** (raw JSON):
```json
{
  "ticker": "BTCUSDT",
  "action": "buy",
  "price": 45123.50,
  "quantity": 0.1,
  "order_type": "market",
  "message": "Sinal de compra detectado"
}
```

### ✅ Resultado Esperado:
```json
{
  "success": true,
  "message": "TradingView webhook received successfully",
  "payload": { ... },
  "processing_result": {
    "orders_created": 1,
    "orders_executed": 1,
    "orders_failed": 0
  },
  "test_mode": true
}
```

---

## 🧪 TESTE 2: Webhook com HMAC (Avançado)

### Via Python (script já funcionando):
```bash
python test_webhook_hmac.py
```

### Via cURL (manual):
```bash
# Payload
PAYLOAD='{"action":"buy","message":"Sinal de compra","order_type":"market","price":45123.5,"quantity":0.1,"ticker":"BTCUSDT"}'

# Calcular HMAC (Linux/Mac)
SIGNATURE=$(echo -n "$PAYLOAD" | openssl dgst -sha256 -hmac "minha_secret_key_super_secreta_123" | awk '{print $2}')

# Enviar webhook
curl -X POST \
  -H "Content-Type: application/json" \
  -H "x-tradingview-signature: sha256=$SIGNATURE" \
  -d "$PAYLOAD" \
  http://localhost:8000/api/v1/webhooks/tv/webhook_demo_123
```

---

## 🧪 TESTE 3: Simular TradingView Real

### Para testar como se fosse o TradingView de verdade:

1. **Abra o Postman ou Insomnia**
2. **Configure**:
   - Method: `POST`
   - URL: `http://localhost:8000/api/v1/webhooks/tv/webhook_demo_123`
   - Headers:
     - `Content-Type: application/json`
     - `User-Agent: TradingView-Webhook/1.0`
   - Body (JSON):

```json
{
  "ticker": "{{ticker}}",
  "action": "{{strategy.order.action}}",
  "price": {{close}},
  "quantity": 0.1,
  "order_type": "market",
  "message": "TradingView Alert: {{strategy.order.action}} {{ticker}}",
  "signal_strength": "strong",
  "rsi": 45.2,
  "volume": 1234567.89,
  "timestamp": "2025-01-20T15:30:00Z",
  "strategy": {
    "name": "RSI Strategy",
    "version": "1.0"
  }
}
```

### ✅ Resultado Esperado:
```json
{
  "success": true,
  "message": "Webhook processed successfully",
  "delivery_id": "demo-delivery-12345",
  "webhook_id": "webhook_demo_123",
  "orders_created": 1,
  "orders_executed": 1,
  "processing_time_ms": 50,
  "hmac_verified": false,
  "payload_processed": { ... }
}
```

---

## 📊 Como Monitorar os Testes

### 1. **Logs do Servidor** (Terminal onde roda o servidor):
```bash
✅ TradingView webhook processed: webhook_demo_123
📦 Payload: {'ticker': 'BTCUSDT', 'action': 'buy', ...}
🔐 HMAC verified: True/False
```

### 2. **Health Check**:
```bash
curl http://localhost:8000/api/v1/health
```

### 3. **Teste de Conectividade**:
```bash
curl http://localhost:8000
```

---

## 🛠️ Resolução de Problemas

### Erro "Connection Refused":
- ✅ Verificar se o servidor está rodando: `ps aux | grep python`
- ✅ Verificar porta 8000: `lsof -i :8000`

### Erro 404 "Webhook not found":
- ✅ Usar URL correta: `/webhook_demo_123` (não outros nomes)
- ✅ Verificar método POST (não GET)

### Erro 401 "Invalid signature":
- ✅ Usar script Python: `python test_webhook_hmac.py`
- ✅ Para teste manual, omitir header `x-tradingview-signature`

### Erro 400 "Missing fields":
- ✅ Incluir campos obrigatórios: `ticker` e `action`
- ✅ Verificar formato JSON válido

---

## 🎯 URLs Para Diferentes Cenários

| Cenário | URL | HMAC Obrigatório |
|---------|-----|------------------|
| Teste simples | `/api/v1/webhooks/tv/test-simple` | ❌ Não |
| Webhook demo | `/api/v1/webhooks/tv/webhook_demo_123` | ⚠️ Opcional |
| Webhook real* | `/api/v1/webhooks/tv/{seu-webhook-id}` | ✅ Sim |

*Para webhook real, precisa do banco PostgreSQL funcionando
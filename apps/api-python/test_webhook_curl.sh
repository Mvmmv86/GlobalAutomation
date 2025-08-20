#!/bin/bash

echo "🚀 Testando webhook TradingView via cURL..."
echo ""

# Payload de teste (formato TradingView)
PAYLOAD='{
  "ticker": "BTCUSDT",
  "action": "buy",
  "price": 45123.50,
  "quantity": 0.1,
  "order_type": "market",
  "message": "Sinal de compra detectado",
  "signal_strength": "strong",
  "rsi": 30.5,
  "volume": 1234567.89,
  "timestamp": "2025-01-20T10:30:00Z"
}'

echo "📦 Payload:"
echo "$PAYLOAD" | jq .
echo ""

# Teste 1: Webhook simples (sem HMAC)
echo "🧪 TESTE 1: Webhook simples (sem validação HMAC)"
echo "URL: http://localhost:8000/api/v1/webhooks/tv/test-simple"
echo ""

curl -X POST \
  -H "Content-Type: application/json" \
  -H "User-Agent: TradingView-Webhook/1.0" \
  -d "$PAYLOAD" \
  http://localhost:8000/api/v1/webhooks/tv/test-simple | jq .

echo ""
echo "=" * 60

# Teste 2: Webhook com HMAC válido
echo ""
echo "🧪 TESTE 2: Webhook com HMAC válido"
echo "URL: http://localhost:8000/api/v1/webhooks/tv/webhook_demo_123"
echo ""

# Calcular HMAC SHA256
SECRET="minha_secret_key_super_secreta_123"
SIGNATURE=$(echo -n "$PAYLOAD" | openssl dgst -sha256 -hmac "$SECRET" | awk '{print $2}')

curl -X POST \
  -H "Content-Type: application/json" \
  -H "User-Agent: TradingView-Webhook/1.0" \
  -H "x-tradingview-signature: sha256=$SIGNATURE" \
  -d "$PAYLOAD" \
  http://localhost:8000/api/v1/webhooks/tv/webhook_demo_123 | jq .

echo ""
echo "=" * 60

# Teste 3: Webhook com HMAC inválido (deve falhar)
echo ""
echo "🧪 TESTE 3: Webhook com HMAC inválido (deve retornar erro 401)"
echo ""

curl -X POST \
  -H "Content-Type: application/json" \
  -H "User-Agent: TradingView-Webhook/1.0" \
  -H "x-tradingview-signature: sha256=signature_errada_123" \
  -d "$PAYLOAD" \
  http://localhost:8000/api/v1/webhooks/tv/webhook_demo_123 | jq .

echo ""
echo "=" * 60

# Teste 4: Webhook inexistente (deve falhar)
echo ""
echo "🧪 TESTE 4: Webhook inexistente (deve retornar erro 404)"
echo ""

curl -X POST \
  -H "Content-Type: application/json" \
  -H "User-Agent: TradingView-Webhook/1.0" \
  -d "$PAYLOAD" \
  http://localhost:8000/api/v1/webhooks/tv/webhook_inexistente | jq .

echo ""
echo "✅ Testes concluídos!"
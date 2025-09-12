#!/usr/bin/env python3
"""Script para testar webhook com validação HMAC"""

import requests
import json
import hmac
import hashlib

# Configurações do webhook criado
WEBHOOK_URL = "http://localhost:8000/api/v1/webhooks/tv/webhook_demo_123"
WEBHOOK_SECRET = "minha_secret_key_super_secreta_123"

# Payload de teste (formato TradingView)
payload = {
    "ticker": "BTCUSDT",
    "action": "buy",
    "price": 45123.50,
    "quantity": 0.1,
    "order_type": "market",
    "message": "Sinal de compra detectado",
    "signal_strength": "strong",
    "rsi": 30.5,
    "volume": 1234567.89,
    "timestamp": "2025-01-20T10:30:00Z",
}

# Converter payload para JSON
payload_json = json.dumps(payload, separators=(",", ":"), sort_keys=True)

# Calcular HMAC signature
signature = hmac.new(
    WEBHOOK_SECRET.encode("utf-8"), payload_json.encode("utf-8"), hashlib.sha256
).hexdigest()

print("🚀 Testando webhook com HMAC...")
print(f"📝 URL: {WEBHOOK_URL}")
print(f"🔑 Secret: {WEBHOOK_SECRET}")
print(f"📦 Payload: {payload}")
print(f"🔐 Signature SHA256: {signature}")
print("-" * 50)

# Headers com signature
headers = {
    "Content-Type": "application/json",
    "x-tradingview-signature": f"sha256={signature}",
    "User-Agent": "TradingView-Webhook/1.0",
}

try:
    # Enviar webhook
    response = requests.post(
        WEBHOOK_URL, data=payload_json, headers=headers, timeout=10
    )

    print(f"📨 Status Code: {response.status_code}")
    print(f"📄 Response Headers: {dict(response.headers)}")

    if response.status_code == 200:
        print("✅ Webhook processado com sucesso!")
        result = response.json()
        print(f"📊 Resultado: {json.dumps(result, indent=2)}")
    else:
        print(f"❌ Erro ao processar webhook: {response.status_code}")
        print(f"💬 Resposta: {response.text}")

except requests.exceptions.ConnectionError:
    print("❌ Erro de conexão - verifique se o servidor está rodando na porta 8000")
except Exception as e:
    print(f"❌ Erro: {e}")

print("\n" + "=" * 50)
print("🧪 Testando com signature inválida...")

# Testar com signature errada
headers_wrong = headers.copy()
headers_wrong["x-tradingview-signature"] = "sha256=signature_errada_123"

try:
    response = requests.post(
        WEBHOOK_URL, data=payload_json, headers=headers_wrong, timeout=10
    )

    print(f"📨 Status Code: {response.status_code}")

    if response.status_code == 401:
        print("✅ Validação funcionando! Webhook rejeitou signature inválida.")
    else:
        print(f"⚠️ Resposta inesperada: {response.text}")

except Exception as e:
    print(f"❌ Erro: {e}")

print("\n" + "=" * 50)
print("🧪 Testando sem signature...")

# Testar sem signature
headers_no_sig = {"Content-Type": "application/json"}

try:
    response = requests.post(
        WEBHOOK_URL, data=payload_json, headers=headers_no_sig, timeout=10
    )

    print(f"📨 Status Code: {response.status_code}")
    print(f"💬 Resposta: {response.text}")

except Exception as e:
    print(f"❌ Erro: {e}")

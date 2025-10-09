#!/usr/bin/env python3
"""
Script para testar criação de ordem com SL/TP
Simula o que o frontend deveria enviar
"""
import requests
import json

# Endpoint
url = "http://localhost:8000/api/v1/orders/create"

# Dados da ordem COM SL/TP
order_data = {
    "exchange_account_id": "0bad440b-f800-46ff-812f-5c359969885e",
    "symbol": "AVAXUSDT",
    "side": "buy",
    "type": "market",
    "quantity": 1.0,
    "is_futures": True,
    "leverage": 10,
    "stop_loss": 30.0,    # SL em $30
    "take_profit": 33.0   # TP em $33
}

print("=" * 70)
print("🧪 Teste: Criação de ordem com SL/TP")
print("=" * 70)
print(f"\n📊 Dados da ordem:")
print(json.dumps(order_data, indent=2))
print("\n⚠️  ATENÇÃO: Este teste NÃO executará a ordem!")
print("⚠️  Apenas mostraria como deveria ser enviado")
print("\n💡 Para testar de verdade, você precisaria:")
print("   1. Criar ordem no frontend com SL/TP preenchidos")
print("   2. Verificar logs do backend para confirmar salvamento")
print("   3. Verificar banco de dados para ver as 3 ordens (main + SL + TP)")
print("=" * 70)

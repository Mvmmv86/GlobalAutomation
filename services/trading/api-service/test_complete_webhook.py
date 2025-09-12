#!/usr/bin/env python3
"""
Teste do webhook com payload completo
"""

import json
import requests
import hmac
import hashlib
from webhook_payload_example import create_complete_payload_example


def test_complete_webhook():
    """
    Testa webhook com payload completo baseado no frontend
    """

    print("🚀 TESTANDO WEBHOOK COM PAYLOAD COMPLETO")
    print("=" * 60)

    # Criar payload completo
    payload_obj = create_complete_payload_example()
    payload_dict = payload_obj.model_dump()

    # Preparar para envio (remover campos não serializáveis)
    webhook_payload = {
        "ticker": payload_dict["ticker"],
        "action": payload_dict["action"],
        "price": payload_dict["price"],
        "quantity": payload_dict["quantity"],
        "order_type": payload_dict["order_type"],
        # Configurações de posição
        "position": payload_dict["position"],
        # Stop Loss e Take Profit
        "stop_loss": payload_dict["stop_loss"],
        "take_profit": payload_dict["take_profit"],
        # Risk Management
        "risk_management": payload_dict["risk_management"],
        # Exchange Config
        "exchange_config": payload_dict["exchange_config"],
        # Strategy
        "strategy": payload_dict["strategy"],
        # Signals
        "signals": payload_dict["signals"],
        # Configs adicionais
        "webhook_config": payload_dict["webhook_config"],
        "account_config": payload_dict["account_config"],
    }

    print(f"📦 Payload completo criado:")
    print(f"   • Ticker: {webhook_payload['ticker']}")
    print(f"   • Action: {webhook_payload['action']}")
    print(f"   • Leverage: {webhook_payload['position']['leverage']}")
    print(f"   • Stop Loss: {webhook_payload['stop_loss']['enabled']}")
    print(f"   • Exchange: {webhook_payload['exchange_config']['exchange']}")
    print(f"   • Strategy: {webhook_payload['strategy']['name']}")

    # Configurações do teste (usar endpoint do main.py)
    webhook_url = "http://localhost:8000/api/v1/webhooks/tv/test-webhook"
    secret = "minha_secret_key_super_secreta_123"

    # Converter para JSON
    payload_json = json.dumps(
        webhook_payload, separators=(",", ":"), sort_keys=True, default=str
    )

    # Calcular HMAC
    signature = hmac.new(
        secret.encode("utf-8"), payload_json.encode("utf-8"), hashlib.sha256
    ).hexdigest()

    # Headers
    headers = {
        "Content-Type": "application/json",
        "x-tradingview-signature": f"sha256={signature}",
        "User-Agent": "TradingView-Webhook/2.0",
    }

    print(f"\n🔗 Enviando para: {webhook_url}")
    print(f"🔐 HMAC Signature: sha256={signature[:16]}...")
    print(f"📊 Payload size: {len(payload_json):,} bytes")

    try:
        # Enviar webhook
        response = requests.post(
            webhook_url, data=payload_json, headers=headers, timeout=10
        )

        print(f"\n📨 Response Status: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print("✅ Webhook processado com sucesso!")
            print(f"\n📊 RESULTADO:")
            print(f"   • Delivery ID: {result.get('delivery_id')}")
            print(f"   • Payload Type: {result.get('payload_type')}")
            print(f"   • Orders Created: {result.get('orders_created')}")
            print(f"   • Orders Executed: {result.get('orders_executed')}")
            print(f"   • Processing Time: {result.get('processing_time_ms')}ms")
            print(f"   • HMAC Verified: {result.get('hmac_verified')}")

            # Mostrar configurações aplicadas
            config_applied = result.get("config_applied", {})
            if config_applied:
                print(f"\n⚙️ CONFIGURAÇÕES APLICADAS:")
                print(f"   • Leverage: {config_applied.get('leverage')}x")
                print(f"   • Margin Mode: {config_applied.get('margin_mode')}")
                print(f"   • Position Mode: {config_applied.get('position_mode')}")
                print(f"   • Stop Loss: {config_applied.get('stop_loss_enabled')}")
                print(f"   • Take Profit: {config_applied.get('take_profit_enabled')}")
                print(f"   • Exchange: {config_applied.get('exchange')}")
                print(f"   • Strategy: {config_applied.get('strategy')}")

            # Mostrar adapters de exchange
            exchange_adapters = result.get("exchange_adapters", [])
            if exchange_adapters:
                print(f"\n🏭 EXCHANGE ADAPTERS:")
                for adapter in exchange_adapters:
                    print(f"   • {adapter['exchange'].upper()}: {adapter['status']}")
                    order = adapter.get("order", {})
                    if order:
                        print(f"     - Symbol: {order.get('symbol')}")
                        print(f"     - Side: {order.get('side')}")
                        print(f"     - Type: {order.get('type')}")
                        print(f"     - Quantity: {order.get('quantity')}")
                        print(f"     - Leverage: {order.get('leverage')}")

            return True

        else:
            print(f"❌ Erro: {response.status_code}")
            try:
                error_data = response.json()
                print(f"💬 Resposta: {json.dumps(error_data, indent=2)}")
            except:
                print(f"💬 Resposta: {response.text}")
            return False

    except requests.exceptions.ConnectionError:
        print("❌ Erro de conexão - verifique se o servidor está rodando")
        return False
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False


def test_simple_payload():
    """
    Teste comparativo com payload simples
    """
    print(f"\n🔄 TESTANDO PAYLOAD SIMPLES (comparação)")
    print("=" * 60)

    simple_payload = {
        "ticker": "BTCUSDT",
        "action": "buy",
        "price": 45123.50,
        "quantity": 0.1,
        "order_type": "market",
    }

    webhook_url = "http://localhost:8000/api/v1/webhooks/tv/webhook_demo_123"

    try:
        response = requests.post(
            webhook_url,
            json=simple_payload,
            headers={"Content-Type": "application/json"},
            timeout=10,
        )

        if response.status_code == 200:
            result = response.json()
            print("✅ Payload simples processado!")
            print(f"   • Payload Type: {result.get('payload_type')}")
            print(f"   • Orders Created: {result.get('orders_created')}")
            print(f"   • Processing Time: {result.get('processing_time_ms')}ms")
            return True
        else:
            print(f"❌ Erro: {response.status_code}")
            return False

    except Exception as e:
        print(f"❌ Erro: {e}")
        return False


if __name__ == "__main__":
    print("🧪 TESTE COMPLETO DE WEBHOOK")
    print("Baseado nas configurações do frontend")
    print("=" * 80)

    # Teste 1: Payload completo
    complete_success = test_complete_webhook()

    # Teste 2: Payload simples
    simple_success = test_simple_payload()

    print("\n" + "=" * 80)
    print("📊 RESUMO DOS TESTES:")
    print(f"   ✅ Payload Completo: {'SUCESSO' if complete_success else 'FALHOU'}")
    print(f"   ✅ Payload Simples: {'SUCESSO' if simple_success else 'FALHOU'}")

    if complete_success and simple_success:
        print("\n🎉 TODOS OS TESTES PASSARAM!")
        print("🚀 Webhook está pronto para produção!")
    else:
        print("\n⚠️ Alguns testes falharam")
        print("🔧 Verifique se o servidor está rodando na porta 8000")

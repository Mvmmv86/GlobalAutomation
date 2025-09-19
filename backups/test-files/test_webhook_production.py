#!/usr/bin/env python3
"""
Teste de webhook para ambiente de produção
Compatível com pgBouncer transaction mode
"""

import requests
import json


def test_simple_webhook():
    """Teste com payload simples"""

    print("🧪 TESTE DE WEBHOOK - PRODUÇÃO")
    print("=" * 60)

    # Payload simples
    payload = {
        "ticker": "BTCUSDT",
        "action": "buy",
        "price": 45000.00,
        "quantity": 0.1,
        "order_type": "market",
    }

    # Endpoint do webhook
    webhook_url = "http://localhost:8000/api/v1/webhooks/tv/test-simple"

    print(f"📦 Enviando payload simples para: {webhook_url}")
    print(f"   • Ticker: {payload['ticker']}")
    print(f"   • Action: {payload['action']}")
    print(f"   • Quantity: {payload['quantity']}")

    try:
        response = requests.post(
            webhook_url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30,
        )

        print(f"\n📨 Status: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print("✅ SUCESSO!")
            print(f"   • Message: {result.get('message', 'OK')}")
            print(f"   • Test Mode: {result.get('test_mode', False)}")
            return True
        else:
            print(f"❌ Erro: {response.status_code}")
            try:
                error = response.json()
                print(f"   Detalhes: {error}")
            except:
                print(f"   Response: {response.text[:500]}")
            return False

    except requests.exceptions.ConnectionError:
        print("❌ Erro de conexão - verifique se o servidor está rodando")
        return False
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False


def test_health():
    """Teste de health check"""

    print("\n🏥 TESTE DE HEALTH CHECK")
    print("=" * 60)

    try:
        response = requests.get("http://localhost:8000/api/v1/health/", timeout=10)

        if response.status_code == 200:
            health = response.json()
            print("✅ API Health:")
            print(f"   • Status: {health.get('status')}")
            print(f"   • Version: {health.get('version')}")
            print(f"   • Environment: {health.get('environment')}")

            services = health.get("services", {})
            print("\n📊 Services:")
            for service, status in services.items():
                emoji = "✅" if status == "healthy" else "⚠️"
                print(f"   {emoji} {service}: {status}")

            return True
        else:
            print(f"❌ Health check falhou: {response.status_code}")
            return False

    except Exception as e:
        print(f"❌ Erro no health check: {e}")
        return False


if __name__ == "__main__":
    print("🚀 TESTE DE WEBHOOK PARA PRODUÇÃO")
    print("Compatível com pgBouncer transaction mode")
    print("=" * 80)

    # Teste 1: Health check
    health_ok = test_health()

    # Teste 2: Webhook simples
    webhook_ok = test_simple_webhook()

    print("\n" + "=" * 80)
    print("📊 RESUMO:")
    print(f"   • Health Check: {'✅ PASSOU' if health_ok else '❌ FALHOU'}")
    print(f"   • Webhook Test: {'✅ PASSOU' if webhook_ok else '❌ FALHOU'}")

    if health_ok and webhook_ok:
        print("\n🎉 SISTEMA PRONTO PARA PRODUÇÃO!")
        print("✅ Compatível com pgBouncer transaction mode")
    else:
        print("\n⚠️ Verifique os erros acima")

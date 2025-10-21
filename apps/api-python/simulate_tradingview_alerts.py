#!/usr/bin/env python3
"""
Simula alertas do TradingView enviando requisições HTTP para os webhooks
Permite testar o sistema completo sem esperar alertas reais
"""

import requests
import json
import time
from datetime import datetime

# Configuração
BASE_URL = "http://localhost:8000"  # Mudar para URL do ngrok se quiser testar via internet

# Webhooks disponíveis
WEBHOOKS = {
    "BTC": {
        "path": "/webhooks/tv/btctpo",
        "name": "BTC_TPO_12min",
        "ticker": "BTCUSDT",
    },
    "ETH": {
        "path": "/webhooks/tv/ethtpo",
        "name": "ETH_TPO_12min",
        "ticker": "ETHUSDT",
    },
    "SOL": {
        "path": "/webhooks/tv/soltpo",
        "name": "SOL_TPO_12min",
        "ticker": "SOLUSDT",
    },
    "BNB": {
        "path": "/webhooks/tv/bnbtpo",
        "name": "BNB_TPO_5min",
        "ticker": "BNBUSDT",
    },
}

def print_header(title):
    """Print formatted header"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)

def send_webhook_alert(webhook_key, action="buy", price=None):
    """
    Envia um alerta simulado para o webhook

    Args:
        webhook_key: Chave do webhook (BTC, ETH, SOL, BNB)
        action: Ação do trade (buy, sell, close)
        price: Preço (opcional, usa preço fictício se não fornecido)
    """
    if webhook_key not in WEBHOOKS:
        print(f"❌ Webhook '{webhook_key}' não encontrado!")
        return False

    webhook = WEBHOOKS[webhook_key]

    # Preços fictícios se não fornecido
    default_prices = {
        "BTCUSDT": 67500.0,
        "ETHUSDT": 3200.0,
        "SOLUSDT": 145.0,
        "BNBUSDT": 620.5,
    }

    if price is None:
        price = default_prices.get(webhook["ticker"], 1000.0)

    # Payload que simula o TradingView
    payload = {
        "ticker": webhook["ticker"],
        "action": action,
        "price": price,
        "timestamp": datetime.now().isoformat(),
        "source": "simulation_script"  # Identificar que é um teste
    }

    url = f"{BASE_URL}{webhook['path']}"

    print(f"\n📤 Enviando alerta para {webhook['name']}...")
    print(f"   URL: {url}")
    print(f"   Payload: {json.dumps(payload, indent=6)}")

    try:
        start_time = time.time()
        response = requests.post(
            url,
            json=payload,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "TradingView-Webhook-Simulator/1.0"
            },
            timeout=30
        )
        elapsed_ms = int((time.time() - start_time) * 1000)

        print(f"\n📥 RESPOSTA:")
        print(f"   Status Code: {response.status_code}")
        print(f"   Tempo: {elapsed_ms}ms")

        try:
            response_data = response.json()
            print(f"   Resposta JSON:")
            print(f"   {json.dumps(response_data, indent=6)}")

            if response_data.get("success"):
                print(f"\n   ✅ Alerta processado com SUCESSO!")
                if "orders_created" in response_data:
                    print(f"   📊 Ordens criadas: {response_data['orders_created']}")
                    print(f"   🚀 Ordens executadas: {response_data.get('orders_executed', 0)}")
                return True
            else:
                print(f"\n   ⚠️  Alerta recebido mas houve erro no processamento:")
                print(f"   ❌ Erro: {response_data.get('error', 'Desconhecido')}")
                return False

        except json.JSONDecodeError:
            print(f"   Resposta (não é JSON): {response.text}")
            return response.status_code == 200

    except requests.exceptions.ConnectionError:
        print(f"\n   ❌ ERRO: Não conseguiu conectar ao backend!")
        print(f"   ⚠️  Certifique-se que o backend está rodando em {BASE_URL}")
        return False
    except requests.exceptions.Timeout:
        print(f"\n   ❌ ERRO: Timeout após 30 segundos")
        return False
    except Exception as e:
        print(f"\n   ❌ ERRO: {e}")
        return False

def test_all_webhooks():
    """Testa todos os webhooks com alertas de compra"""
    print_header("🧪 TESTE COMPLETO - TODOS OS WEBHOOKS")

    results = {}

    for key, webhook in WEBHOOKS.items():
        success = send_webhook_alert(key, action="buy")
        results[webhook["name"]] = "✅ SUCESSO" if success else "❌ FALHOU"
        time.sleep(2)  # Aguardar 2s entre cada teste

    print_header("📊 RESUMO DOS TESTES")
    for name, result in results.items():
        print(f"   {result} - {name}")

    total = len(results)
    passed = sum(1 for r in results.values() if "SUCESSO" in r)
    print(f"\n   Total: {passed}/{total} webhooks funcionando")

def interactive_mode():
    """Modo interativo para testar webhooks individualmente"""
    print_header("🎮 MODO INTERATIVO - SIMULADOR DE ALERTAS")

    while True:
        print("\n" + "-" * 80)
        print("Escolha uma opção:")
        print("  1. Testar BTC (buy)")
        print("  2. Testar ETH (buy)")
        print("  3. Testar SOL (buy)")
        print("  4. Testar BNB (buy)")
        print("  5. Testar TODOS os webhooks")
        print("  6. Teste customizado")
        print("  0. Sair")
        print("-" * 80)

        choice = input("\n👉 Escolha: ").strip()

        if choice == "0":
            print("\n👋 Saindo...")
            break
        elif choice == "1":
            send_webhook_alert("BTC", "buy")
        elif choice == "2":
            send_webhook_alert("ETH", "buy")
        elif choice == "3":
            send_webhook_alert("SOL", "buy")
        elif choice == "4":
            send_webhook_alert("BNB", "buy")
        elif choice == "5":
            test_all_webhooks()
        elif choice == "6":
            print("\n📝 Teste Customizado:")
            webhook_key = input("  Webhook (BTC/ETH/SOL/BNB): ").strip().upper()
            action = input("  Ação (buy/sell/close): ").strip().lower()
            price_str = input("  Preço (Enter para usar default): ").strip()

            price = float(price_str) if price_str else None
            send_webhook_alert(webhook_key, action, price)
        else:
            print("❌ Opção inválida!")

if __name__ == "__main__":
    import sys

    print("=" * 80)
    print("🚀 SIMULADOR DE ALERTAS DO TRADINGVIEW")
    print("=" * 80)
    print(f"\nBackend: {BASE_URL}")
    print("\nEste script simula alertas do TradingView enviando requisições HTTP")
    print("para os webhooks configurados, permitindo testar o sistema completo.")

    # Verificar se backend está acessível
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print("\n✅ Backend está acessível e respondendo!")
        else:
            print(f"\n⚠️  Backend respondeu com status {response.status_code}")
    except:
        print(f"\n❌ ATENÇÃO: Backend não está acessível em {BASE_URL}")
        print("   Execute 'python3 main.py' antes de usar este script")
        sys.exit(1)

    # Menu
    print("\n" + "-" * 80)
    print("Modos de operação:")
    print("  1. Modo Interativo (escolher webhook individualmente)")
    print("  2. Teste Rápido (testar todos os webhooks de uma vez)")
    print("-" * 80)

    mode = input("\n👉 Escolha o modo (1 ou 2): ").strip()

    if mode == "1":
        interactive_mode()
    elif mode == "2":
        test_all_webhooks()
    else:
        print("❌ Modo inválido! Use 1 ou 2")

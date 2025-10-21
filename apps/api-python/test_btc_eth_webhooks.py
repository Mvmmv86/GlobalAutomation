#!/usr/bin/env python3
"""
Teste dos webhooks BTC e ETH
"""

import asyncio
import json
import sys
from uuid import UUID

sys.path.insert(0, '/home/globalauto/global/apps/api-python')

from infrastructure.di.container import get_container


async def test_webhook(webhook_name, payload):
    """Test a specific webhook"""

    print("\n" + "=" * 80)
    print(f"TESTANDO: {webhook_name}")
    print("=" * 80)

    try:
        # Get container
        container = await get_container()
        webhook_repo = container.get("webhook_repository")
        tv_service = container.get("tradingview_webhook_service")

        # Find webhook by name
        from infrastructure.database.models.webhook import Webhook
        from sqlalchemy import select

        session = container.get("database_session")
        stmt = select(Webhook).where(Webhook.name == webhook_name)
        result = await session.execute(stmt)
        webhook = result.scalar_one_or_none()

        if not webhook:
            print(f"❌ Webhook '{webhook_name}' não encontrado!")
            return False

        print(f"\n✅ Webhook encontrado:")
        print(f"   ID: {webhook.id}")
        print(f"   URL: /webhooks/tv/{webhook.url_path}")
        print(f"   Margem: ${webhook.default_margin_usd}")
        print(f"   Alavancagem: {webhook.default_leverage}x")
        print(f"   SL: {webhook.default_stop_loss_pct}%")
        print(f"   TP: {webhook.default_take_profit_pct}%")

        print(f"\n📦 Payload:")
        print(json.dumps(payload, indent=2))

        # Process webhook
        print(f"\n🚀 Processando webhook...")

        result = await tv_service.process_tradingview_webhook(
            webhook_id=UUID(webhook.id),
            payload=payload,
            headers={"Content-Type": "application/json"},
            user_ip="127.0.0.1"
        )

        print(f"\n📊 RESULTADO:")
        print(json.dumps(result, indent=2, default=str))

        if result.get("success"):
            print(f"\n✅ SUCESSO!")
            print(f"   Ordens criadas: {result.get('orders_created', 0)}")
            print(f"   Ordens executadas: {result.get('orders_executed', 0)}")
            print(f"   Tempo: {result.get('processing_time_ms', 0)}ms")
            return True
        else:
            print(f"\n❌ FALHOU!")
            print(f"   Erro: {result.get('error')}")
            return False

    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    print("=" * 80)
    print("TESTE DOS WEBHOOKS BTC E ETH")
    print("=" * 80)

    # Payloads de teste
    btc_payload = {
        "ticker": "BTCUSDT",
        "action": "buy",
        "price": 67500.0
    }

    eth_payload = {
        "ticker": "ETHUSDT",
        "action": "buy",
        "price": 3200.0
    }

    results = {}

    # Testar BTC
    print("\n\n" + "#" * 80)
    print("# TESTE 1: BTC_TPO_12min")
    print("#" * 80)
    results["BTC"] = await test_webhook("BTC_TPO_12min", btc_payload)

    await asyncio.sleep(2)  # Wait 2s between tests

    # Testar ETH
    print("\n\n" + "#" * 80)
    print("# TESTE 2: ETH_TPO_12min")
    print("#" * 80)
    results["ETH"] = await test_webhook("ETH_TPO_12min", eth_payload)

    # Resumo
    print("\n\n" + "=" * 80)
    print("RESUMO DOS TESTES")
    print("=" * 80)

    for name, success in results.items():
        status = "✅ PASSOU" if success else "❌ FALHOU"
        print(f"   {status} - {name}_TPO_12min")

    total = len(results)
    passed = sum(1 for r in results.values() if r)

    print(f"\n   Total: {passed}/{total} testes passaram")

    return all(results.values())


if __name__ == "__main__":
    print("\n🧪 Iniciando testes dos webhooks BTC e ETH\n")

    success = asyncio.run(main())

    print("\n" + "=" * 80)
    if success:
        print("✅ TODOS OS TESTES PASSARAM!")
    else:
        print("❌ ALGUNS TESTES FALHARAM")
    print("=" * 80 + "\n")

    sys.exit(0 if success else 1)

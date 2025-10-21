#!/usr/bin/env python3
"""
Debug script para identificar onde o fluxo de webhooks está quebrando
Este script simula um webhook do TradingView e rastreia cada etapa
"""

import asyncio
import json
import sys
from uuid import UUID
from decimal import Decimal

# Add app to path
sys.path.insert(0, '/home/globalauto/global/apps/api-python')

from infrastructure.di.container import get_container
from application.services.tradingview_webhook_service import TradingViewWebhookService
from infrastructure.database.repositories import WebhookRepository
import structlog

logger = structlog.get_logger()


async def test_webhook_flow():
    """Test complete webhook flow with detailed logging"""

    print("=" * 80)
    print("TESTE DE FLUXO DE WEBHOOK - DEBUG DETALHADO")
    print("=" * 80)

    # Payload simulando TradingView (formato complexo real)
    test_payload = {
        "trade_id": "DEBUG_TEST_001",
        "action": "Venda",  # Será normalizado para "sell"
        "symbol": "SOLUSDT",
        "timestamp": "2025-10-15 12:00:00",
        "source": "DEBUG_Test",
        "position": {
            "side": "SELL",
            "quantity": "0.146",
            "entry_price": "205.50",
            "size_usdt": "30"
        },
        "risk_management": {
            "stop_loss": {
                "price": "210.00",
                "method": "ATR"
            },
            "take_profit_1": {
                "price": "201.00",
                "quantity": "0.097",
                "size_usdt": "20",
                "method": "Percentage"
            }
        }
    }

    print(f"\n1. PAYLOAD DE TESTE:")
    print(json.dumps(test_payload, indent=2))

    try:
        # Initialize container
        print("\n2. INICIALIZANDO CONTAINER DI...")
        container = await get_container()
        print("   ✅ Container inicializado")

        # Get webhook repository
        print("\n3. BUSCANDO WEBHOOK NO BANCO...")
        webhook_repo = container.get("webhook_repository")

        # List all webhooks
        # Assuming there's a method to get all webhooks or get by user_id
        # For now, we'll try to get by url_path

        # First, let's see what webhooks exist
        print("   Tentando listar webhooks existentes...")

        # Since we don't have a list_all method, let's check the database directly
        from sqlalchemy import select
        from infrastructure.database.models.webhook import Webhook

        session = container.get("database_session")

        from infrastructure.database.models.webhook import WebhookStatus
        stmt = select(Webhook).where(Webhook.status == WebhookStatus.ACTIVE).limit(5)
        result = await session.execute(stmt)
        webhooks = result.scalars().all()

        if not webhooks:
            print("   ❌ NENHUM WEBHOOK ATIVO ENCONTRADO NO BANCO!")
            print("   Por favor, crie um webhook primeiro via dashboard")
            return False

        print(f"   ✅ Encontrados {len(webhooks)} webhooks ativos:")
        for wh in webhooks:
            print(f"      - ID: {wh.id}, Path: {wh.url_path}, User: {wh.user_id}")
            print(f"        Margin: ${wh.default_margin_usd}, Leverage: {wh.default_leverage}x")
            print(f"        SL: {wh.default_stop_loss_pct}%, TP: {wh.default_take_profit_pct}%")

        # Use the first active webhook for testing
        webhook = webhooks[0]
        print(f"\n   📌 USANDO WEBHOOK: {webhook.id} (path: {webhook.url_path})")

        # Get TradingView webhook service
        print("\n4. OBTENDO TRADINGVIEW WEBHOOK SERVICE...")
        tv_service = container.get("tradingview_webhook_service")
        print(f"   ✅ Service obtido: {type(tv_service).__name__}")

        # Test payload normalization
        print("\n5. TESTANDO NORMALIZAÇÃO DE PAYLOAD...")
        normalized = tv_service._normalize_payload(test_payload)
        print(f"   Original action: '{test_payload['action']}'")
        print(f"   Normalized action: '{normalized.get('action')}'")
        print(f"   Normalized ticker: '{normalized.get('ticker')}'")
        print(f"   Normalized price: {normalized.get('price')}")

        # Test payload validation
        print("\n6. TESTANDO VALIDAÇÃO DE PAYLOAD...")
        try:
            trading_signal = await tv_service._validate_tradingview_payload(test_payload)
            print(f"   ✅ Payload validado com sucesso")
            print(f"   Signal: {trading_signal.ticker} {trading_signal.action} @ {trading_signal.price}")
        except Exception as e:
            print(f"   ❌ ERRO NA VALIDAÇÃO: {e}")
            return False

        # Test exchange account retrieval
        print("\n7. VERIFICANDO EXCHANGE ACCOUNTS DO USUÁRIO...")
        exchange_account_repo = container.get("exchange_account_repository")
        user_id = UUID(webhook.user_id)

        exchange_accounts = await exchange_account_repo.get_user_active_accounts(user_id)

        if not exchange_accounts:
            print(f"   ❌ NENHUMA EXCHANGE ACCOUNT ATIVA PARA USER {user_id}")
            return False

        print(f"   ✅ Encontradas {len(exchange_accounts)} exchange accounts:")
        for acc in exchange_accounts:
            print(f"      - ID: {acc.id}, Type: {acc.exchange_type.value}, Testnet: {acc.environment.value}")

        # Test secure exchange service
        print("\n8. TESTANDO SECURE EXCHANGE SERVICE...")
        secure_exchange_service = container.get("secure_exchange_service")
        print(f"   ✅ Service obtido: {type(secure_exchange_service).__name__}")

        # Test adapter creation (without actually creating order yet)
        print("\n9. TESTANDO CRIAÇÃO DE ADAPTER...")
        try:
            test_account = exchange_accounts[0]
            adapter = await secure_exchange_service.get_exchange_adapter(
                test_account.id,
                user_id
            )
            print(f"   ✅ Adapter criado: {adapter.name}")

            # Test connection
            print("\n10. TESTANDO CONEXÃO COM EXCHANGE...")
            is_connected = await adapter.test_connection()
            if is_connected:
                print(f"   ✅ Conexão com {adapter.name} bem-sucedida")
            else:
                print(f"   ❌ FALHA NA CONEXÃO COM {adapter.name}")
                return False

        except Exception as e:
            print(f"   ❌ ERRO AO CRIAR ADAPTER: {e}")
            import traceback
            traceback.print_exc()
            return False

        # Now test the FULL webhook processing (THIS IS THE CRITICAL TEST)
        print("\n" + "=" * 80)
        print("11. TESTE COMPLETO DO PROCESSO DE WEBHOOK")
        print("=" * 80)
        print("\n⚠️  ATENÇÃO: Isso vai tentar criar uma ordem REAL na Binance!")
        print("   Payload:", json.dumps(test_payload, indent=2))

        response = input("\n   Deseja continuar e criar ordem REAL? (sim/NAO): ")

        if response.lower() != 'sim':
            print("\n   ⏭️  Teste de ordem cancelado pelo usuário")
            print("\n✅ TODOS OS TESTES PRÉ-ORDEM PASSARAM COM SUCESSO!")
            print("\nCONCLUSÃO:")
            print("  - Webhook encontrado e ativo")
            print("  - Payload normalizado corretamente")
            print("  - Exchange account encontrada")
            print("  - Adapter criado e conectado")
            print("  - Service pipeline funcionando")
            print("\n⚠️  O PROBLEMA pode estar em:")
            print("  1. Cálculo de quantity (linha 531-560 do service)")
            print("  2. Chamada do create_order (linha 563-571)")
            print("  3. Configuração de market_type no webhook")
            return True

        # Execute full webhook processing
        print("\n   🚀 INICIANDO PROCESSAMENTO COMPLETO...")

        result = await tv_service.process_tradingview_webhook(
            webhook_id=UUID(webhook.id),
            payload=test_payload,
            headers={"Content-Type": "application/json"},
            user_ip="127.0.0.1"
        )

        print("\n12. RESULTADO DO PROCESSAMENTO:")
        print(json.dumps(result, indent=2, default=str))

        if result.get("success"):
            print("\n✅ ✅ ✅ WEBHOOK PROCESSADO COM SUCESSO! ✅ ✅ ✅")
            print(f"   Ordens criadas: {result.get('orders_created', 0)}")
            print(f"   Ordens executadas: {result.get('orders_executed', 0)}")
            return True
        else:
            print("\n❌ WEBHOOK FALHOU!")
            print(f"   Erro: {result.get('error')}")
            return False

    except Exception as e:
        print(f"\n❌ ERRO DURANTE O TESTE: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Cleanup
        if 'session' in locals():
            await session.close()


if __name__ == "__main__":
    print("\n🔍 INICIANDO DEBUG DO FLUXO DE WEBHOOKS\n")

    result = asyncio.run(test_webhook_flow())

    print("\n" + "=" * 80)
    if result:
        print("✅ TESTE CONCLUÍDO COM SUCESSO")
    else:
        print("❌ TESTE FALHOU - VER LOGS ACIMA")
    print("=" * 80 + "\n")

    sys.exit(0 if result else 1)

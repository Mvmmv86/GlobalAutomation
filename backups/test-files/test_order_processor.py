#!/usr/bin/env python3
"""
Teste do Order Processor
"""

import asyncio
import json
from infrastructure.services.order_processor import order_processor
from infrastructure.database.connection_transaction_mode import transaction_db


async def test_order_processor():
    """Teste completo do processador de ordens"""

    print("🧪 TESTANDO ORDER PROCESSOR")
    print("=" * 60)

    try:
        # Conectar ao banco
        await transaction_db.connect()
        print("✅ Conectado ao banco")

        # Teste 1: Payload simples do TradingView
        print("\n📊 Teste 1: Processando ordem simples...")
        simple_payload = {
            "ticker": "BTCUSDT",
            "action": "buy",
            "price": 45000.00,
            "quantity": 0.001,
        }

        result1 = await order_processor.process_tradingview_webhook(simple_payload)

        if result1["success"]:
            print(f"   ✅ Ordem processada: ID {result1['order_id']}")
            print(f"   Exchange Order: {result1.get('exchange_order_id', 'N/A')}")
            print(f"   Status: {result1.get('status', 'unknown')}")
        else:
            print(f"   ❌ Erro: {result1.get('error', 'Unknown')}")

        # Teste 2: Payload completo
        print("\n📊 Teste 2: Processando ordem completa...")
        complex_payload = {
            "ticker": "ETHUSDT",
            "action": "sell",
            "price": 2500.00,
            "quantity": 0.1,
            "order_type": "market",
            "position": {"size": 0.1, "leverage": 10},
            "risk_management": {"stop_loss": 2400.00, "take_profit": 2600.00},
        }

        result2 = await order_processor.process_tradingview_webhook(complex_payload)

        if result2["success"]:
            print(f"   ✅ Ordem processada: ID {result2['order_id']}")
            print(f"   Exchange Order: {result2.get('exchange_order_id', 'N/A')}")
        else:
            print(f"   ❌ Erro: {result2.get('error', 'Unknown')}")

        # Teste 3: Verificar ordens criadas
        print("\n📈 Teste 3: Verificando ordens no banco...")
        recent_orders = await order_processor.get_recent_orders(5)

        print(f"   Total de ordens recentes: {len(recent_orders)}")
        for order in recent_orders:
            print(
                f"   • ID {order['id']}: {order['symbol']} {order['side']} - {order['status']}"
            )

        # Teste 4: Buscar ordem específica
        if result1["success"]:
            print(f"\n🔍 Teste 4: Buscando ordem {result1['order_id']}...")
            order_details = await order_processor.get_order_status(result1["order_id"])

            if order_details:
                print(f"   Symbol: {order_details['symbol']}")
                print(f"   Side: {order_details['side']}")
                print(f"   Quantity: {order_details['quantity']}")
                print(f"   Status: {order_details['status']}")
                print(f"   Exchange: {order_details['exchange']}")
                print(f"   Created: {order_details['created_at']}")
            else:
                print("   ❌ Ordem não encontrada")

        # Teste 5: Erro de validação
        print("\n❌ Teste 5: Testando erro de validação...")
        invalid_payload = {"ticker": "INVALID", "action": "invalid_action"}

        result3 = await order_processor.process_tradingview_webhook(invalid_payload)

        if not result3["success"]:
            print(f"   ✅ Erro capturado corretamente: {result3['error']}")
        else:
            print("   ❌ Deveria ter falhado na validação")

        print("\n🎉 TODOS OS TESTES CONCLUÍDOS!")
        return True

    except Exception as e:
        print(f"\n❌ ERRO NO TESTE: {e}")
        import traceback

        traceback.print_exc()
        return False

    finally:
        await transaction_db.disconnect()


async def show_orders_table():
    """Mostra todas as ordens na tabela"""

    try:
        await transaction_db.connect()

        orders = await transaction_db.fetch(
            """
            SELECT 
                id, symbol, side, quantity, status, exchange_order_id, created_at
            FROM trading_orders 
            ORDER BY created_at DESC
        """
        )

        print("\n📊 TODAS AS ORDENS NO BANCO:")
        print("-" * 80)

        if not orders:
            print("   Nenhuma ordem encontrada")
        else:
            for order in orders:
                print(
                    f"ID {order['id']}: {order['symbol']} {order['side']} {order['quantity']} - {order['status']} ({order['created_at']})"
                )

    finally:
        await transaction_db.disconnect()


if __name__ == "__main__":
    print("🚀 Iniciando teste do Order Processor...")

    success = asyncio.run(test_order_processor())

    if success:
        print("\n✅ Order Processor funcionando!")
        print("Próximo: Integrar com webhook do TradingView")

        # Mostrar tabela
        asyncio.run(show_orders_table())
    else:
        print("\n⚠️ Testes falharam")

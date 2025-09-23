#!/usr/bin/env python3
"""
Verificar ordens criadas pelo sistema completo
"""

import asyncio
from infrastructure.database.connection_transaction_mode import transaction_db


async def check_orders():
    """Verificar ordens no banco"""

    try:
        await transaction_db.connect()

        # Buscar todas as ordens
        orders = await transaction_db.fetch(
            """
            SELECT 
                id, symbol, side, quantity, price, status, 
                exchange, exchange_order_id, filled_quantity, 
                average_price, created_at, updated_at
            FROM trading_orders 
            ORDER BY created_at DESC
        """
        )

        print("📊 TODAS AS ORDENS NO SISTEMA:")
        print("=" * 100)

        if not orders:
            print("   Nenhuma ordem encontrada")
        else:
            for order in orders:
                print(f"🆔 ID: {order['id']}")
                print(
                    f"   📈 {order['symbol']} {order['side'].upper()} {order['quantity']}"
                )
                print(f"   💰 Price: ${order['price'] or 'Market'}")
                print(f"   📊 Status: {order['status']}")
                print(f"   🏭 Exchange: {order['exchange']}")
                print(f"   🆔 Exchange Order: {order['exchange_order_id'] or 'N/A'}")
                print(f"   ✅ Filled: {order['filled_quantity'] or 'N/A'}")
                print(f"   💵 Avg Price: ${order['average_price'] or 'N/A'}")
                print(f"   📅 Created: {order['created_at']}")
                print(f"   🔄 Updated: {order['updated_at'] or 'N/A'}")
                print("-" * 80)

        # Estatísticas
        total_orders = len(orders)
        filled_orders = len([o for o in orders if o["status"] in ["FILLED", "filled"]])
        pending_orders = len([o for o in orders if o["status"] == "pending"])
        failed_orders = len([o for o in orders if o["status"] == "failed"])

        print(f"\n📊 ESTATÍSTICAS:")
        print(f"   • Total de ordens: {total_orders}")
        print(f"   • ✅ Executadas (FILLED): {filled_orders}")
        print(f"   • ⏳ Pendentes: {pending_orders}")
        print(f"   • ❌ Falhas: {failed_orders}")

        if total_orders > 0:
            success_rate = (filled_orders / total_orders) * 100
            print(f"   • 🎯 Taxa de sucesso: {success_rate:.1f}%")

        return True

    except Exception as e:
        print(f"❌ Erro: {e}")
        return False

    finally:
        await transaction_db.disconnect()


if __name__ == "__main__":
    print("🔍 Verificando ordens no sistema...")
    asyncio.run(check_orders())

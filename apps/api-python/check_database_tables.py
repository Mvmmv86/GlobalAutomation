#!/usr/bin/env python3
"""Check all tables in the database"""

import asyncio
import os
from dotenv import load_dotenv
from infrastructure.database.connection_transaction_mode import transaction_db

load_dotenv()

async def check_database_tables():
    """Check all tables and their data counts"""

    print("🔍 Verificando TODAS as tabelas do banco de dados...")
    print("=" * 60)

    # Initialize database
    await transaction_db.connect()

    try:
        # 1. List all tables
        tables = await transaction_db.fetch("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)

        print(f"\n📊 Total de tabelas encontradas: {len(tables)}")
        print("\n📋 Lista de tabelas:")

        for table in tables:
            table_name = table['table_name']

            # Get row count for each table
            count_result = await transaction_db.fetchval(f"SELECT COUNT(*) FROM {table_name}")

            print(f"\n   📁 {table_name}: {count_result} registros")

            # For tables that might contain trade/order history
            if 'trade' in table_name.lower() or 'order' in table_name.lower() or 'history' in table_name.lower():
                print(f"      ⚠️ POSSÍVEL TABELA DE HISTÓRICO!")

                # Get sample data
                sample = await transaction_db.fetch(f"""
                    SELECT * FROM {table_name}
                    ORDER BY
                        CASE
                            WHEN column_name = 'created_at' THEN created_at
                            WHEN column_name = 'updated_at' THEN updated_at
                            ELSE NULL
                        END DESC NULLS LAST
                    LIMIT 3
                """)

                if sample:
                    print(f"      Sample columns: {list(sample[0].keys())[:5]}...")

        # 2. Check trading_orders table specifically
        print("\n\n🎯 Análise detalhada da tabela 'trading_orders':")
        orders_stats = await transaction_db.fetchrow("""
            SELECT
                COUNT(*) as total,
                COUNT(CASE WHEN status = 'NEW' THEN 1 END) as new_orders,
                COUNT(CASE WHEN status = 'FILLED' THEN 1 END) as filled_orders,
                COUNT(CASE WHEN status = 'CANCELED' THEN 1 END) as canceled_orders,
                MIN(created_at) as oldest,
                MAX(created_at) as newest
            FROM trading_orders
        """)

        if orders_stats:
            print(f"   Total: {orders_stats['total']}")
            print(f"   NEW: {orders_stats['new_orders']}")
            print(f"   FILLED: {orders_stats['filled_orders']}")
            print(f"   CANCELED: {orders_stats['canceled_orders']}")
            print(f"   Mais antiga: {orders_stats['oldest']}")
            print(f"   Mais recente: {orders_stats['newest']}")

        # 3. Check for account-specific orders
        account_id = "0bad440b-f800-46ff-812f-5c359969885e"
        account_orders = await transaction_db.fetchval("""
            SELECT COUNT(*)
            FROM trading_orders
            WHERE exchange_account_id = $1
        """, account_id)

        print(f"\n   Ordens da conta principal: {account_orders}")

        # Sample filled orders
        filled_sample = await transaction_db.fetch("""
            SELECT
                symbol, side, order_type, quantity, price, status,
                created_at, updated_at
            FROM trading_orders
            WHERE status = 'FILLED'
                AND exchange_account_id = $1
            ORDER BY created_at DESC
            LIMIT 10
        """, account_id)

        if filled_sample:
            print(f"\n   📋 Últimas 10 ordens FILLED da conta:")
            for i, order in enumerate(filled_sample, 1):
                print(f"\n   {i}. {order['symbol']} - {order['side']}")
                print(f"      Qtd: {order['quantity']}, Price: {order['price']}")
                print(f"      Created: {order['created_at']}")

    except Exception as e:
        print(f"\n❌ Erro: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await transaction_db.disconnect()

    print("\n" + "=" * 60)
    print("✅ Verificação completa!")

if __name__ == "__main__":
    asyncio.run(check_database_tables())
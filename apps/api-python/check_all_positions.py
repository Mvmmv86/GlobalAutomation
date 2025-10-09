#!/usr/bin/env python3
"""Script to check all positions in the database"""

import asyncio
import os
from dotenv import load_dotenv
from infrastructure.database.connection import init_database, close_database
from infrastructure.database.connection_transaction_mode import transaction_db

load_dotenv()

async def check_all_positions():
    """Check all positions in database"""

    # Initialize database
    await init_database()

    try:
        print("🔍 Verificando TODAS as posições no banco de dados")
        print("=" * 60)

        # 1. Total de posições
        total = await transaction_db.fetchval("SELECT COUNT(*) FROM positions")
        print(f"\n📊 Total de posições no banco: {total}")

        # 2. Por status
        by_status = await transaction_db.fetch("""
            SELECT status, COUNT(*) as count
            FROM positions
            GROUP BY status
            ORDER BY count DESC
        """)
        print("\n📈 Distribuição por status:")
        for row in by_status:
            print(f"   {row['status']}: {row['count']} posições")

        # 3. Por conta de exchange
        by_account = await transaction_db.fetch("""
            SELECT
                ea.name as account_name,
                ea.id as account_id,
                COUNT(p.*) as total,
                COUNT(CASE WHEN p.status = 'closed' THEN 1 END) as closed,
                COUNT(CASE WHEN p.status = 'open' THEN 1 END) as open
            FROM exchange_accounts ea
            LEFT JOIN positions p ON p.exchange_account_id = ea.id
            WHERE ea.is_active = true
            GROUP BY ea.id, ea.name
            ORDER BY total DESC
        """)
        print("\n🏦 Por conta de exchange:")
        for row in by_account:
            print(f"\n   {row['account_name']} ({row['account_id'][:8]}...):")
            print(f"      Total: {row['total']}")
            print(f"      Fechadas: {row['closed']}")
            print(f"      Abertas: {row['open']}")

        # 4. Conta específica
        account_id = "0bad440b-f800-46ff-812f-5c359969885e"
        print(f"\n🎯 Detalhes da conta principal ({account_id[:8]}...):")

        # Posições fechadas sem filtro de data
        all_closed = await transaction_db.fetch("""
            SELECT
                id, symbol, side, entry_price,
                unrealized_pnl, realized_pnl,
                created_at, closed_at, status
            FROM positions
            WHERE exchange_account_id = $1
                AND status = 'closed'
            ORDER BY created_at DESC
        """, account_id)

        print(f"\n   Total de posições fechadas (sem filtro de data): {len(all_closed)}")

        if all_closed:
            print("\n   📋 Lista completa de posições fechadas:")
            for i, pos in enumerate(all_closed, 1):
                print(f"\n   {i}. {pos['symbol']} ({pos['side']})")
                print(f"      ID: {pos['id'][:8]}...")
                print(f"      Entry: ${pos['entry_price']:.2f}")
                pnl = pos['realized_pnl'] or pos['unrealized_pnl'] or 0
                print(f"      P&L: ${pnl:.2f}")
                print(f"      Created: {pos['created_at']}")
                print(f"      Closed: {pos['closed_at'] or 'N/A'}")

        # 5. Verificar se existem posições órfãs
        orphan = await transaction_db.fetchval("""
            SELECT COUNT(*)
            FROM positions p
            LEFT JOIN exchange_accounts ea ON p.exchange_account_id = ea.id
            WHERE ea.id IS NULL OR ea.is_active = false
        """)
        if orphan > 0:
            print(f"\n⚠️  ATENÇÃO: {orphan} posições órfãs ou de contas inativas!")

        # 6. Verificar range de datas
        date_range = await transaction_db.fetchrow("""
            SELECT
                MIN(created_at) as oldest,
                MAX(created_at) as newest,
                MIN(closed_at) as oldest_closed,
                MAX(closed_at) as newest_closed
            FROM positions
            WHERE status = 'closed'
        """)

        if date_range:
            print("\n📅 Range de datas das posições fechadas:")
            print(f"   Criação mais antiga: {date_range['oldest']}")
            print(f"   Criação mais recente: {date_range['newest']}")
            print(f"   Fechamento mais antigo: {date_range['oldest_closed'] or 'N/A'}")
            print(f"   Fechamento mais recente: {date_range['newest_closed'] or 'N/A'}")

    except Exception as e:
        print(f"\n❌ Erro: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await close_database()

    print("\n" + "=" * 60)
    print("✅ Verificação completa!")

if __name__ == "__main__":
    asyncio.run(check_all_positions())
#!/usr/bin/env python3
"""
Script simplificado de debug para SL/TP
"""
import asyncio
from infrastructure.database.connection_transaction_mode import transaction_db

async def debug_simple():
    await transaction_db.connect()

    print("="*70)
    print("🔍 DEBUG SIMPLIFICADO: Ordens SL/TP")
    print("="*70)

    # 1. Ver todos os tipos de ordem que existem
    print("\n1️⃣ Tipos de ordem existentes no banco:")
    types = await transaction_db.fetch("""
        SELECT DISTINCT type, COUNT(*) as count
        FROM orders
        GROUP BY type
        ORDER BY count DESC
    """)

    for row in types:
        print(f"   {row['type']}: {row['count']} ordens")

    # 2. Ver status das ordens
    print("\n2️⃣ Status das ordens:")
    statuses = await transaction_db.fetch("""
        SELECT DISTINCT status, COUNT(*) as count
        FROM orders
        GROUP BY status
        ORDER BY count DESC
    """)

    for row in statuses:
        print(f"   {row['status']}: {row['count']} ordens")

    # 3. Últimas 5 ordens criadas
    print("\n3️⃣ Últimas 5 ordens (qualquer tipo):")
    recent = await transaction_db.fetch("""
        SELECT
            id,
            symbol,
            side,
            type,
            status,
            price,
            created_at
        FROM orders
        ORDER BY created_at DESC
        LIMIT 5
    """)

    for row in recent:
        print(f"\n   {row['symbol']} - {row['type']} ({row['status']})")
        print(f"   Price: ${row['price']}")
        print(f"   Created: {row['created_at']}")

    # 4. Posições abertas
    print("\n4️⃣ Posições abertas:")
    positions = await transaction_db.fetch("""
        SELECT
            id,
            symbol,
            side,
            size,
            entry_price,
            status
        FROM positions
        WHERE status = 'open'
        ORDER BY created_at DESC
        LIMIT 5
    """)

    if not positions:
        print("   ⚠️ Nenhuma posição aberta!")
    else:
        for row in positions:
            print(f"   {row['symbol']} {row['side']} {row['size']} @ ${row['entry_price']}")

    print("\n" + "="*70)

if __name__ == "__main__":
    asyncio.run(debug_simple())

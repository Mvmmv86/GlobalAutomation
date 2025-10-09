#!/usr/bin/env python3
"""
Script de debug para verificar ordens SL/TP no banco
"""
import asyncio
import os
from infrastructure.database.connection_transaction_mode import transaction_db

async def debug_sltp_orders():
    # Inicializar pool de conexão
    await transaction_db.connect()
    """Verificar ordens SL/TP no banco"""

    print("=" * 70)
    print("🔍 DEBUG: Ordens Stop Loss / Take Profit")
    print("=" * 70)

    # 1. Total de ordens SL/TP
    print("\n1️⃣ Total de ordens SL/TP:")
    total = await transaction_db.fetchval("""
        SELECT COUNT(*)
        FROM orders
        WHERE type IN ('stop_loss', 'take_profit', 'stop_market', 'take_profit_market')
    """)
    print(f"   Total: {total} ordens")

    # 2. Ordens por status
    print("\n2️⃣ Ordens por status:")
    by_status = await transaction_db.fetch("""
        SELECT status, COUNT(*) as count
        FROM orders
        WHERE type IN ('stop_loss', 'take_profit', 'stop_market', 'take_profit_market')
        GROUP BY status
        ORDER BY count DESC
    """)
    for row in by_status:
        print(f"   {row['status']}: {row['count']} ordens")

    # 3. Ordens por tipo
    print("\n3️⃣ Ordens por tipo:")
    by_type = await transaction_db.fetch("""
        SELECT type, COUNT(*) as count
        FROM orders
        WHERE type IN ('stop_loss', 'take_profit', 'stop_market', 'take_profit_market')
        GROUP BY type
        ORDER BY count DESC
    """)
    for row in by_type:
        print(f"   {row['type']}: {row['count']} ordens")

    # 4. Últimas 5 ordens SL/TP criadas
    print("\n4️⃣ Últimas 5 ordens SL/TP criadas:")
    recent = await transaction_db.fetch("""
        SELECT
            id,
            symbol,
            side,
            type,
            status,
            price,
            stop_price,
            created_at
        FROM orders
        WHERE type IN ('stop_loss', 'take_profit', 'stop_market', 'take_profit_market')
        ORDER BY created_at DESC
        LIMIT 5
    """)

    if not recent:
        print("   ⚠️  Nenhuma ordem encontrada!")
    else:
        for row in recent:
            print(f"\n   📊 {row['symbol']} - {row['type']}")
            print(f"      Status: {row['status']}")
            print(f"      Side: {row['side']}")
            print(f"      Price: ${row['price']}")
            print(f"      Stop Price: ${row['stop_price']}")
            print(f"      Created: {row['created_at']}")

    # 5. Ordens "ativas" (possíveis status)
    print("\n5️⃣ Ordens 'ativas' por diferentes critérios:")

    statuses_to_check = [
        ('new', "status = 'new'"),
        ('open', "status = 'open'"),
        ('submitted', "status = 'submitted'"),
        ('pending', "status = 'pending'"),
        ('filled', "status = 'filled'"),
        ('new OR open', "status IN ('new', 'open')"),
        ('new OR open OR submitted', "status IN ('new', 'open', 'submitted')"),
    ]

    for label, condition in statuses_to_check:
        count = await transaction_db.fetchval(f"""
            SELECT COUNT(*)
            FROM orders
            WHERE type IN ('stop_loss', 'take_profit', 'STOP_LOSS', 'TAKE_PROFIT',
                           'stop_market', 'take_profit_market', 'STOP_MARKET', 'TAKE_PROFIT_MARKET')
              AND {condition}
        """)
        print(f"   {label}: {count} ordens")

    # 6. Exemplo de query atual do usePositionOrders
    print("\n6️⃣ Simulando filtro atual do usePositionOrders:")
    print("   (status = 'new' apenas)")

    current_filter = await transaction_db.fetch("""
        SELECT
            symbol,
            type,
            status,
            price
        FROM orders
        WHERE type IN ('stop_loss', 'take_profit', 'stop_market', 'take_profit_market')
          AND status = 'new'
        ORDER BY created_at DESC
        LIMIT 10
    """)

    if not current_filter:
        print("   ❌ Nenhuma ordem com status='new' encontrada!")
        print("   💡 PROBLEMA IDENTIFICADO: Filtro muito restritivo!")
    else:
        print(f"   ✅ {len(current_filter)} ordens encontradas com status='new'")
        for row in current_filter:
            print(f"      - {row['symbol']} {row['type']} @ ${row['price']}")

    # 7. Verificar posições abertas
    print("\n7️⃣ Posições abertas (para comparação):")
    positions = await transaction_db.fetch("""
        SELECT
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
        print("   ⚠️  Nenhuma posição aberta!")
    else:
        print(f"   ✅ {len(positions)} posições abertas:")
        for row in positions:
            print(f"      - {row['symbol']} {row['side']} {row['size']} @ ${row['entry_price']}")

    print("\n" + "=" * 70)
    print("✅ Debug completo!")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(debug_sltp_orders())

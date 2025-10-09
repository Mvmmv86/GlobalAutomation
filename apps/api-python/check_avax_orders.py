#!/usr/bin/env python3
import asyncio
from infrastructure.database.connection_transaction_mode import transaction_db

async def check_avax():
    await transaction_db.connect()
    
    print("=" * 70)
    print("🔍 Todas as ordens AVAXUSDT:")
    print("=" * 70)
    
    orders = await transaction_db.fetch("""
        SELECT 
            id,
            external_id,
            client_order_id,
            symbol,
            side,
            type,
            status,
            price,
            stop_price,
            quantity,
            reduce_only,
            created_at
        FROM orders
        WHERE symbol = 'AVAXUSDT'
        ORDER BY created_at DESC
    """)
    
    for i, order in enumerate(orders, 1):
        print(f"\n{i}. Ordem ID: {order['id']}")
        print(f"   External ID: {order['external_id']}")
        print(f"   Client Order ID: {order['client_order_id']}")
        print(f"   Side: {order['side']}")
        print(f"   Type: {order['type']}")
        print(f"   Status: {order['status']}")
        print(f"   Price: ${order['price']}")
        print(f"   Stop Price: ${order['stop_price']}")
        print(f"   Quantity: {order['quantity']}")
        print(f"   Reduce Only: {order['reduce_only']}")
        print(f"   Created: {order['created_at']}")
    
    print("\n" + "=" * 70)
    print(f"✅ Total: {len(orders)} ordens AVAX")
    print("=" * 70)

asyncio.run(check_avax())

#!/usr/bin/env python3
import asyncio
from infrastructure.database.connection_transaction_mode import transaction_db

async def check():
    await transaction_db.connect()
    
    print("=" * 70)
    print("🔍 TODAS as ordens do banco (últimas 10):")
    print("=" * 70)
    
    orders = await transaction_db.fetch("""
        SELECT 
            id,
            symbol,
            side,
            type,
            status,
            price,
            stop_price,
            client_order_id,
            created_at
        FROM orders
        ORDER BY created_at DESC
        LIMIT 10
    """)
    
    for i, order in enumerate(orders, 1):
        is_sltp = order['client_order_id'] and (
            order['client_order_id'].startswith('sl_') or 
            order['client_order_id'].startswith('tp_')
        )
        
        emoji = "🎯" if is_sltp else "📊"
        
        print(f"\n{i}. {emoji} {order['symbol']} - {order['side']} {order['type']}")
        print(f"   Client ID: {order['client_order_id']}")
        print(f"   Status: {order['status']}")
        print(f"   Price: ${order['price']}")
        print(f"   Stop Price: ${order['stop_price']}")
        print(f"   Created: {order['created_at']}")
        
        if is_sltp:
            print(f"   ⚠️ ESTA É UMA ORDEM SL/TP!")
    
    print("\n" + "=" * 70)

asyncio.run(check())

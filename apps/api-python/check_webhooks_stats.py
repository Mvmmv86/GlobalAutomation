#!/usr/bin/env python3
"""Check webhook statistics in database"""

import asyncio
import sys
sys.path.insert(0, '/home/globalauto/global/apps/api-python')

from infrastructure.database.connection_transaction_mode import transaction_db

async def check_stats():
    """Check webhook statistics"""

    # Initialize database connection
    await transaction_db.connect()

    print("\n🔍 Checking webhook statistics...\n")

    # Check webhooks
    webhooks = await transaction_db.fetch("""
        SELECT
            id, name, url_path,
            total_deliveries, successful_deliveries, failed_deliveries,
            last_delivery_at
        FROM webhooks
        ORDER BY last_delivery_at DESC NULLS LAST
        LIMIT 5
    """)

    print("📊 Webhooks:")
    for w in webhooks:
        print(f"  - {w['name']}")
        print(f"    ID: {w['id']}")
        print(f"    Total: {w['total_deliveries']}, Success: {w['successful_deliveries']}, Failed: {w['failed_deliveries']}")
        print(f"    Last delivery: {w['last_delivery_at']}")
        print()

    # Check recent deliveries
    deliveries = await transaction_db.fetch("""
        SELECT
            d.id, d.webhook_id, d.status, d.created_at,
            d.orders_created, d.orders_executed, d.orders_failed,
            w.name as webhook_name
        FROM webhook_deliveries d
        JOIN webhooks w ON w.id = d.webhook_id
        ORDER BY d.created_at DESC
        LIMIT 5
    """)

    print("📦 Recent Deliveries:")
    for d in deliveries:
        print(f"  - {d['webhook_name']} ({d['created_at']})")
        print(f"    Status: {d['status']}")
        print(f"    Orders: created={d['orders_created']}, executed={d['orders_executed']}, failed={d['orders_failed']}")
        print()

    await transaction_db.close()

if __name__ == "__main__":
    asyncio.run(check_stats())

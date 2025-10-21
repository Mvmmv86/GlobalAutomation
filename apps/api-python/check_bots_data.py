#!/usr/bin/env python3
import asyncio
import asyncpg
import os
from dotenv import load_dotenv
import json

load_dotenv()

async def check_bots():
    """Check what data is being returned from bots table"""
    database_url = os.getenv("DATABASE_URL")

    if database_url.startswith("postgresql+asyncpg://"):
        database_url = database_url.replace("postgresql+asyncpg://", "postgresql://")

    conn = await asyncpg.connect(database_url)

    try:
        # Get all bots with the same query used in admin controller
        bots = await conn.fetch("""
            SELECT
                id, name, description, market_type, status,
                master_webhook_path,
                default_leverage, default_margin_usd,
                default_stop_loss_pct, default_take_profit_pct,
                total_subscribers, total_signals_sent,
                avg_win_rate, avg_pnl_pct,
                created_at, updated_at
            FROM bots
            ORDER BY created_at DESC
        """)

        print(f"\n✅ Found {len(bots)} bots\n")

        for bot in bots:
            bot_dict = dict(bot)
            print(f"📦 Bot ID: {bot_dict['id']}")
            print(f"   Name: {bot_dict.get('name', 'NULL')}")
            print(f"   Description: {bot_dict.get('description', 'NULL')[:50]}...")
            print(f"   Status: {bot_dict.get('status', 'NULL')}")
            print(f"   Market Type: {bot_dict.get('market_type', 'NULL')}")
            print(f"   Webhook Path: {bot_dict.get('master_webhook_path', 'NULL')}")
            print(f"   Subscribers: {bot_dict.get('total_subscribers', 'NULL')}")
            print(f"   Signals Sent: {bot_dict.get('total_signals_sent', 'NULL')}")
            print(f"   Win Rate: {bot_dict.get('avg_win_rate', 'NULL')}")
            print(f"   P&L: {bot_dict.get('avg_pnl_pct', 'NULL')}")
            print(f"   Created: {bot_dict.get('created_at', 'NULL')}")
            print()

            # Show full JSON
            print(f"📋 Full JSON:\n{json.dumps(bot_dict, default=str, indent=2)}\n")
            print("-" * 80)

    except Exception as e:
        print(f"❌ Error: {e}")
        raise
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(check_bots())

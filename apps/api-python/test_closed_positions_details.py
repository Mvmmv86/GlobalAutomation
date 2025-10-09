#!/usr/bin/env python3
"""Test script to verify closed positions details and dates"""

import asyncio
import aiohttp
import json
from datetime import datetime, timedelta

async def test_closed_positions():
    """Test closed positions with date information"""

    base_url = "http://localhost:8000"

    # Calculate date range for last 30 days
    date_to = datetime.now().strftime("%Y-%m-%d")
    date_from = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

    print("🔍 Testing Closed Positions Details")
    print("=" * 60)
    print(f"📅 Date range: {date_from} to {date_to}")

    async with aiohttp.ClientSession() as session:

        # Get closed positions
        print("\n📊 Fetching CLOSED positions...")
        async with session.get(
            f"{base_url}/api/v1/positions",
            params={
                "status": "closed",
                "exchange_account_id": "0bad440b-f800-46ff-812f-5c359969885e",
                "date_from": date_from,
                "date_to": date_to
            }
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                positions = data.get("data", [])
                print(f"✅ Found {len(positions)} closed positions\n")

                # Analyze each position
                positions_with_date = 0
                positions_without_date = 0

                print("📋 Position Details:")
                print("-" * 60)

                for i, pos in enumerate(positions, 1):
                    symbol = pos['symbol']
                    side = pos['side']
                    entry_price = pos['entry_price']
                    realized_pnl = pos.get('realized_pnl', 0) or pos.get('unrealized_pnl', 0)
                    closed_at = pos.get('closed_at')
                    created_at = pos.get('created_at')

                    print(f"\n{i}. {symbol} ({side})")
                    print(f"   Entry: ${entry_price:.2f}")
                    print(f"   P&L: ${realized_pnl:.2f}")

                    if closed_at:
                        positions_with_date += 1
                        try:
                            # Parse and format date
                            date_obj = datetime.fromisoformat(closed_at.replace('Z', '+00:00'))
                            formatted_date = date_obj.strftime("%d/%m/%Y %H:%M")
                            print(f"   Closed: {formatted_date}")
                        except:
                            print(f"   Closed: {closed_at}")
                    else:
                        positions_without_date += 1
                        print(f"   Closed: NOT AVAILABLE")
                        if created_at:
                            print(f"   Created: {created_at[:10]} (fallback)")

                print("\n" + "-" * 60)
                print(f"\n📈 Summary:")
                print(f"   Total positions: {len(positions)}")
                print(f"   With close date: {positions_with_date}")
                print(f"   Without close date: {positions_without_date}")

                # Calculate total P&L
                total_pnl = sum(
                    pos.get('realized_pnl', 0) or pos.get('unrealized_pnl', 0)
                    for pos in positions
                )
                print(f"   Total P&L: ${total_pnl:.2f}")

            else:
                print(f"❌ Error: {resp.status}")
                error_text = await resp.text()
                print(f"Error details: {error_text}")

    print("\n" + "=" * 60)
    print("✅ Test completed!")

if __name__ == "__main__":
    asyncio.run(test_closed_positions())
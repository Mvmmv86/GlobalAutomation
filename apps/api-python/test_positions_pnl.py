#!/usr/bin/env python3
"""Test script to verify P&L calculations for positions"""

import asyncio
import aiohttp
import json
from datetime import datetime, timedelta

async def test_positions_pnl():
    """Test P&L calculations for open and closed positions"""

    base_url = "http://localhost:8000"

    # Calculate date range for last 30 days
    date_to = datetime.now().strftime("%Y-%m-%d")
    date_from = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

    print("🔍 Testing Positions P&L Calculations")
    print("=" * 50)

    async with aiohttp.ClientSession() as session:

        # Test 1: Get open positions
        print("\n1. Fetching OPEN positions...")
        async with session.get(
            f"{base_url}/api/v1/positions",
            params={
                "status": "open",
                "exchange_account_id": "0bad440b-f800-46ff-812f-5c359969885e"
            }
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                positions = data.get("data", [])
                print(f"   ✅ Found {len(positions)} open positions")

                for pos in positions[:3]:  # Show first 3
                    print(f"\n   📊 {pos['symbol']} ({pos['side']})")
                    print(f"      Entry: ${pos['entry_price']:.2f}")
                    print(f"      Mark: ${pos.get('mark_price', 0):.2f}")
                    print(f"      Unrealized P&L: ${pos.get('unrealized_pnl', 0):.2f}")
                    print(f"      Size: {pos['size']}")
            else:
                print(f"   ❌ Error: {resp.status}")

        # Test 2: Get closed positions
        print("\n2. Fetching CLOSED positions (last 30 days)...")
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
                print(f"   ✅ Found {len(positions)} closed positions")

                total_realized_pnl = 0
                for pos in positions[:5]:  # Show first 5
                    realized_pnl = pos.get('realized_pnl', 0) or pos.get('unrealized_pnl', 0)
                    total_realized_pnl += realized_pnl

                    print(f"\n   📊 {pos['symbol']} ({pos['side']})")
                    print(f"      Entry: ${pos['entry_price']:.2f}")
                    print(f"      Exit: ${pos.get('exit_price', 'N/A')}")
                    print(f"      Realized P&L: ${realized_pnl:.2f}")
                    print(f"      Size: {pos['size']}")
                    if pos.get('closed_at'):
                        print(f"      Closed: {pos['closed_at'][:10]}")

                if positions:
                    print(f"\n   💰 Total Realized P&L (sample): ${total_realized_pnl:.2f}")
            else:
                print(f"   ❌ Error: {resp.status}")
                error_text = await resp.text()
                print(f"   Error details: {error_text}")

        # Test 3: Get all positions
        print("\n3. Fetching ALL positions...")
        async with session.get(
            f"{base_url}/api/v1/positions",
            params={
                "exchange_account_id": "0bad440b-f800-46ff-812f-5c359969885e",
                "date_from": date_from,
                "date_to": date_to,
                "limit": 50
            }
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                positions = data.get("data", [])

                open_count = sum(1 for p in positions if p['status'] == 'open')
                closed_count = sum(1 for p in positions if p['status'] == 'closed')

                print(f"   ✅ Total positions: {len(positions)}")
                print(f"      Open: {open_count}")
                print(f"      Closed: {closed_count}")

                # Calculate totals
                total_unrealized = sum(p.get('unrealized_pnl', 0) for p in positions if p['status'] == 'open')
                total_realized = sum(
                    p.get('realized_pnl', 0) or p.get('unrealized_pnl', 0)
                    for p in positions if p['status'] == 'closed'
                )

                print(f"\n   💰 P&L Summary:")
                print(f"      Total Unrealized (Open): ${total_unrealized:.2f}")
                print(f"      Total Realized (Closed): ${total_realized:.2f}")
                print(f"      Total P&L: ${(total_unrealized + total_realized):.2f}")
            else:
                print(f"   ❌ Error: {resp.status}")

    print("\n" + "=" * 50)
    print("✅ Test completed!")

if __name__ == "__main__":
    asyncio.run(test_positions_pnl())
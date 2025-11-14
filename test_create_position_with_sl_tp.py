#!/usr/bin/env python3
"""
Script to create a test position with SL/TP orders on BingX
"""

import asyncio
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'apps', 'api-python'))

from infrastructure.external.exchange_adapters.bingx_adapter import BingXAdapter

async def create_test_position():
    # BingX credentials
    API_KEY = "eav5kOI91l0I0fVRXEaUUaV17hLi9lHVbpxK8dzcULVdN4sGdGk4g5kMKfCQhrEQhkQ35EilMngr0PQCRJqA"
    API_SECRET = "Fq74sZdGbLsuQzmn1kyTlTzhfGRfEjvQhlzvA50pbGNaUm9DBVGQctUksblscKfJGzqFWRGQJXLCQfGUg"

    adapter = BingXAdapter()
    await adapter.initialize(API_KEY, API_SECRET, testnet=False)

    print("="*60)
    print("🚀 CREATING TEST POSITION WITH SL/TP ON BINGX")
    print("="*60)

    try:
        # 1. Get current BTC price
        print("\n📊 Getting current BTC price...")
        ticker_response = await adapter.connector.api_request(
            method="GET",
            path="/openApi/swap/v2/quote/ticker",
            params={"symbol": "BTC-USDT"}
        )

        if ticker_response and 'data' in ticker_response:
            current_price = float(ticker_response['data'][0]['lastPrice'])
            print(f"   Current BTC price: ${current_price:,.2f}")
        else:
            print("❌ Failed to get BTC price")
            return

        # 2. Open a small test position (minimum size)
        print(f"\n🎯 Opening LONG position on BTC...")

        # Calculate position size (0.001 BTC minimum)
        position_size = 0.001
        leverage = 10

        # Create market order to open position
        order_params = {
            "symbol": "BTC-USDT",
            "side": "BUY",
            "type": "MARKET",
            "quantity": position_size,
            "leverage": leverage
        }

        print(f"   Size: {position_size} BTC")
        print(f"   Leverage: {leverage}x")
        print(f"   Value: ${position_size * current_price:,.2f}")

        order_response = await adapter.connector.api_request(
            method="POST",
            path="/openApi/swap/v2/trade/order",
            params=order_params
        )

        if order_response and 'data' in order_response:
            order_id = order_response['data'].get('order', {}).get('orderId')
            print(f"✅ Position opened! Order ID: {order_id}")
        else:
            print(f"❌ Failed to open position: {order_response}")
            return

        # 3. Set Stop Loss (2% below entry)
        sl_price = current_price * 0.98
        print(f"\n🔴 Setting Stop Loss at ${sl_price:,.2f} (-2%)")

        sl_params = {
            "symbol": "BTC-USDT",
            "side": "SELL",  # Opposite side for closing
            "type": "STOP_MARKET",
            "stopPrice": sl_price,
            "quantity": position_size,
            "workingType": "MARK_PRICE"
        }

        sl_response = await adapter.connector.api_request(
            method="POST",
            path="/openApi/swap/v2/trade/order",
            params=sl_params
        )

        if sl_response and 'data' in sl_response:
            sl_order_id = sl_response['data'].get('order', {}).get('orderId')
            print(f"✅ Stop Loss set! Order ID: {sl_order_id}")
        else:
            print(f"❌ Failed to set Stop Loss: {sl_response}")

        # 4. Set Take Profit (3% above entry)
        tp_price = current_price * 1.03
        print(f"\n🟢 Setting Take Profit at ${tp_price:,.2f} (+3%)")

        tp_params = {
            "symbol": "BTC-USDT",
            "side": "SELL",  # Opposite side for closing
            "type": "TAKE_PROFIT_MARKET",
            "stopPrice": tp_price,
            "quantity": position_size,
            "workingType": "MARK_PRICE"
        }

        tp_response = await adapter.connector.api_request(
            method="POST",
            path="/openApi/swap/v2/trade/order",
            params=tp_params
        )

        if tp_response and 'data' in tp_response:
            tp_order_id = tp_response['data'].get('order', {}).get('orderId')
            print(f"✅ Take Profit set! Order ID: {tp_order_id}")
        else:
            print(f"❌ Failed to set Take Profit: {tp_response}")

        # 5. Verify pending orders
        print("\n📋 Verifying pending orders...")
        pending_orders = await adapter.connector.api_request(
            method="GET",
            path="/openApi/swap/v2/trade/openOrders",
            params={"symbol": "BTC-USDT"}
        )

        if pending_orders and 'data' in pending_orders:
            orders = pending_orders['data'].get('orders', [])
            print(f"   Found {len(orders)} pending orders:")
            for order in orders:
                order_type = order.get('type', '')
                stop_price = order.get('stopPrice', 0)
                print(f"   - {order_type}: ${stop_price:,.2f}")

        print("\n✅ Test position created successfully!")
        print("   Please check your trading platform to see SL/TP lines on the chart")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(create_test_position())
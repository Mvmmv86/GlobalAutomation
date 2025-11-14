#!/usr/bin/env python3
"""
Test script to debug orders API
"""

import requests
import json

def test_orders_api():
    """Test the orders API endpoint"""

    # BingX account ID
    account_id = "8a42489d-8b66-405d-ab04-a9bbaa091e31"

    # API endpoint
    url = f"http://localhost:8001/api/v1/orders"

    # Query parameters
    params = {
        "exchange_account_id": account_id
    }

    print("="*60)
    print("🔍 TESTING ORDERS API")
    print("="*60)
    print(f"URL: {url}")
    print(f"Account ID: {account_id}")

    try:
        # Make the request
        response = requests.get(url, params=params)

        print(f"\nStatus Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"\nResponse: {json.dumps(data, indent=2)}")

            if data.get('success'):
                orders = data.get('data', [])
                print(f"\n✅ Found {len(orders)} orders")

                for order in orders:
                    print(f"\nOrder Details:")
                    print(f"  Symbol: {order.get('symbol')}")
                    print(f"  Type: {order.get('order_type')}")
                    print(f"  Status: {order.get('status')}")
                    print(f"  Price: {order.get('price')}")
                    print(f"  Stop Price: {order.get('stop_price')}")
            else:
                print(f"❌ Request failed: {data.get('error')}")
        else:
            print(f"❌ HTTP Error: {response.text}")

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_orders_api()
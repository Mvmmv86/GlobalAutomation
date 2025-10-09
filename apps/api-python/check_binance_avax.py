#!/usr/bin/env python3
"""
Verificar ordens AVAX diretamente na Binance
"""
import asyncio
import os
from infrastructure.exchanges.binance_connector import BinanceConnector

async def check():
    api_key = os.getenv('BINANCE_API_KEY')
    api_secret = os.getenv('BINANCE_API_SECRET')
    
    connector = BinanceConnector(api_key, api_secret, testnet=False)
    
    print("=" * 70)
    print("🔍 Ordens AVAXUSDT na Binance (FUTURES):")
    print("=" * 70)
    
    try:
        result = await connector.get_futures_orders('AVAXUSDT')
        
        if result['success']:
            orders = result['data']
            print(f"\n✅ Total: {len(orders)} ordens encontradas\n")
            
            for i, order in enumerate(orders, 1):
                print(f"{i}. Order ID: {order['orderId']}")
                print(f"   Symbol: {order['symbol']}")
                print(f"   Side: {order['side']}")
                print(f"   Type: {order['type']}")
                print(f"   Status: {order['status']}")
                print(f"   Price: ${order.get('price', order.get('stopPrice', 'N/A'))}")
                print(f"   Stop Price: ${order.get('stopPrice', 'N/A')}")
                print(f"   Quantity: {order['origQty']}")
                print(f"   Reduce Only: {order.get('reduceOnly', False)}")
                print()
        else:
            print(f"❌ Erro: {result.get('error')}")
    
    except Exception as e:
        print(f"❌ Exceção: {e}")
        import traceback
        traceback.print_exc()
    
    print("=" * 70)

asyncio.run(check())

#!/usr/bin/env python3
"""
Script para verificar ordens pendentes (SL/TP) diretamente na BingX
"""

import asyncio
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'apps', 'api-python'))

from infrastructure.external.exchange_adapters.bingx_adapter import BingXAdapter

async def check_orders():
    # Suas credenciais BingX
    API_KEY = "eav5kOI91l0I0fVRXEaUUaV17hLi9lHVbpxK8dzcULVdN4sGdGk4g5kMKfCQhrEQhkQ35EilMngr0PQCRJqA"
    API_SECRET = "Fq74sZdGbLsuQzmn1kyTlTzhfGRfEjvQhlzvA50pbGNaUm9DBVGQctUksblscKfJGzqFWRGQJXLCQfGUg"

    adapter = BingXAdapter()
    await adapter.initialize(API_KEY, API_SECRET, testnet=False)

    print("="*60)
    print("🔍 VERIFICANDO ORDENS PENDENTES NA BINGX")
    print("="*60)

    try:
        # 1. Buscar posições abertas
        print("\n📊 Buscando posições abertas...")
        positions = await adapter.get_futures_positions()

        if positions and positions['data']:
            for pos in positions['data']:
                if float(pos.get('positionAmt', 0)) != 0:
                    symbol = pos.get('symbol')
                    side = "LONG" if float(pos['positionAmt']) > 0 else "SHORT"
                    print(f"\n✅ Posição encontrada: {symbol} {side}")
                    print(f"   Quantidade: {pos['positionAmt']}")
                    print(f"   Preço entrada: ${pos.get('avgPrice', 0)}")

        # 2. Buscar ordens pendentes (SL/TP)
        print("\n🔍 Buscando ordens pendentes (Stop Loss e Take Profit)...")

        # Método 1: Buscar todas as ordens pendentes
        pending_orders = await adapter.connector.api_request(
            method="GET",
            path="/openApi/swap/v2/trade/openOrders",
            params={}
        )

        if pending_orders and 'data' in pending_orders:
            orders = pending_orders['data'].get('orders', [])
            print(f"\n📋 Total de ordens pendentes: {len(orders)}")

            for order in orders:
                order_type = order.get('type', '')
                symbol = order.get('symbol', '')
                price = order.get('price', 0)
                stop_price = order.get('stopPrice', 0)

                if 'STOP' in order_type.upper() or 'TAKE_PROFIT' in order_type.upper():
                    print(f"\n🎯 Ordem {order_type} encontrada:")
                    print(f"   Symbol: {symbol}")
                    print(f"   Tipo: {order_type}")
                    print(f"   Preço: ${price}")
                    print(f"   Stop Price: ${stop_price}")
                    print(f"   Side: {order.get('side')}")
                    print(f"   Quantidade: {order.get('origQty')}")
                    print(f"   Order ID: {order.get('orderId')}")

        # Método 2: Buscar ordens de trigger específicas
        print("\n🔍 Buscando ordens de trigger (método alternativo)...")
        trigger_orders = await adapter.connector.api_request(
            method="GET",
            path="/openApi/swap/v1/trade/triggerOrders",
            params={}
        )

        if trigger_orders and 'data' in trigger_orders:
            orders = trigger_orders.get('data', [])
            print(f"\n📋 Ordens de trigger encontradas: {len(orders)}")

            for order in orders:
                print(f"\n🎯 Ordem trigger:")
                print(f"   Symbol: {order.get('symbol')}")
                print(f"   Tipo: {order.get('type')}")
                print(f"   Trigger Price: ${order.get('triggerPrice')}")
                print(f"   Order Price: ${order.get('price')}")
                print(f"   Side: {order.get('side')}")

    except Exception as e:
        print(f"\n❌ Erro: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(check_orders())
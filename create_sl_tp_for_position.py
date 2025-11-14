#!/usr/bin/env python3
"""
Script para criar ordens de Stop Loss e Take Profit para posição existente
"""

import asyncio
import aiohttp
import json
from decimal import Decimal

async def create_sl_tp_orders():
    # Configurações
    API_URL = "http://localhost:8001/api/v1"
    POSITION_ID = "8d64790b-cbfd-4f53-9658-3d8893a37e2d"
    SYMBOL = "SOLUSDT"
    ENTRY_PRICE = 151.821

    # Calcular preços de SL e TP
    sl_price = round(ENTRY_PRICE * 0.97, 2)  # -3% do preço de entrada
    tp_price = round(ENTRY_PRICE * 1.05, 2)  # +5% do preço de entrada

    print(f"📊 Criando ordens SL/TP para posição SOLUSDT")
    print(f"   Entrada: ${ENTRY_PRICE}")
    print(f"   🔴 Stop Loss: ${sl_price} (-3%)")
    print(f"   🟢 Take Profit: ${tp_price} (+5%)")

    async with aiohttp.ClientSession() as session:
        # Criar ordem de Stop Loss
        sl_order = {
            "symbol": SYMBOL,
            "side": "SELL",  # Para posição LONG, SL é SELL
            "order_type": "STOP_MARKET",
            "quantity": 1.0,
            "price": sl_price,
            "status": "open",
            "exchange": "bingx",
            "exchange_account_id": "8a42489d-8b66-405d-ab04-a9bbaa091e31",
            "operation_type": "futures",
            "position_id": POSITION_ID
        }

        # Criar ordem de Take Profit
        tp_order = {
            "symbol": SYMBOL,
            "side": "SELL",  # Para posição LONG, TP é SELL
            "order_type": "TAKE_PROFIT_MARKET",
            "quantity": 1.0,
            "price": tp_price,
            "status": "open",
            "exchange": "bingx",
            "exchange_account_id": "8a42489d-8b66-405d-ab04-a9bbaa091e31",
            "operation_type": "futures",
            "position_id": POSITION_ID
        }

        try:
            # Criar Stop Loss
            print("\n🔴 Criando ordem de Stop Loss...")
            async with session.post(f"{API_URL}/orders", json=sl_order) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    print(f"✅ Stop Loss criado: {result}")
                else:
                    print(f"❌ Erro ao criar Stop Loss: {resp.status}")
                    text = await resp.text()
                    print(f"   Resposta: {text}")

            # Criar Take Profit
            print("\n🟢 Criando ordem de Take Profit...")
            async with session.post(f"{API_URL}/orders", json=tp_order) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    print(f"✅ Take Profit criado: {result}")
                else:
                    print(f"❌ Erro ao criar Take Profit: {resp.status}")
                    text = await resp.text()
                    print(f"   Resposta: {text}")

            # Verificar ordens criadas
            print("\n📋 Verificando ordens criadas...")
            async with session.get(f"{API_URL}/orders?symbol={SYMBOL}&exchange_account_id=8a42489d-8b66-405d-ab04-a9bbaa091e31") as resp:
                if resp.status == 200:
                    result = await resp.json()
                    orders = result.get('data', [])
                    print(f"✅ Total de ordens: {len(orders)}")
                    for order in orders:
                        print(f"   - {order['order_type']}: ${order['price']} ({order['status']})")

        except Exception as e:
            print(f"❌ Erro: {e}")

if __name__ == "__main__":
    print("="*60)
    print("CRIANDO ORDENS SL/TP PARA TESTE DO GRÁFICO")
    print("="*60)
    asyncio.run(create_sl_tp_orders())
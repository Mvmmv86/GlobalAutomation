#!/usr/bin/env python3
"""
Script para buscar o histórico de trades da Binance via API HTTP
e identificar posições fechadas
"""

import asyncio
import aiohttp
from datetime import datetime, timedelta

async def sync_closed_positions_via_api():
    """Sync closed positions through API endpoint"""

    account_id = "0bad440b-f800-46ff-812f-5c359969885e"
    base_url = "http://localhost:8000"

    print("🔍 Buscando histórico de trades da Binance...")
    print("=" * 60)

    async with aiohttp.ClientSession() as session:

        # 1. Primeiro buscar trades dos últimos 90 dias
        print("\n📊 Buscando trades...")
        async with session.post(
            f"{base_url}/api/v1/sync/trades/{account_id}",
            params={
                "days_back": 90,
                "limit": 500
            }
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                print(f"✅ Resposta: {data.get('message')}")

                trades = data.get('trades_preview', [])
                total_trades = data.get('total_trades', 0)

                print(f"\n📈 Total de trades encontrados: {total_trades}")

                if trades:
                    print("\n📋 Preview dos primeiros trades:")
                    for i, trade in enumerate(trades[:5], 1):
                        print(f"\n   {i}. {trade.get('symbol', 'N/A')}")
                        print(f"      Side: {trade.get('side', 'N/A')}")
                        print(f"      Quantity: {trade.get('qty', 0)}")
                        print(f"      Price: ${trade.get('price', 0)}")
                        print(f"      Time: {trade.get('time', 'N/A')}")
            else:
                print(f"❌ Erro: {resp.status}")
                text = await resp.text()
                print(f"   {text}")

        # 2. Buscar ordens executadas (FILLED)
        print("\n\n📦 Buscando ordens executadas...")
        async with session.post(
            f"{base_url}/api/v1/sync/orders/{account_id}",
            params={
                "days_back": 90,
                "limit": 500
            }
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                synced = data.get('synced_count', 0)
                total = data.get('total_orders', 0)

                print(f"✅ Ordens sincronizadas: {synced}/{total}")
            else:
                print(f"❌ Erro: {resp.status}")

        # 3. Verificar posições no banco após sincronização
        print("\n\n🔍 Verificando posições após sincronização...")

        # Buscar todas as posições (sem filtro de data)
        async with session.get(
            f"{base_url}/api/v1/positions",
            params={
                "exchange_account_id": account_id
            }
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                positions = data.get('data', [])

                open_count = sum(1 for p in positions if p.get('status') == 'open')
                closed_count = sum(1 for p in positions if p.get('status') == 'closed')

                print(f"\n📊 Total de posições no banco:")
                print(f"   Abertas: {open_count}")
                print(f"   Fechadas: {closed_count}")
                print(f"   Total: {len(positions)}")

    print("\n" + "=" * 60)
    print("✅ Análise concluída!")
    print("\n⚠️  NOTA: O sistema atual NÃO converte trades em posições fechadas.")
    print("    Isso precisa ser implementado para mostrar seu histórico completo.")

if __name__ == "__main__":
    asyncio.run(sync_closed_positions_via_api())
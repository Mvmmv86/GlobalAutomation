#!/usr/bin/env python3
"""
Teste dos endpoints de ordens da API
"""

import asyncio
import aiohttp
import json


async def test_orders_api():
    """Testa os endpoints de ordens"""

    base_url = "http://localhost:8000/api/v1"

    async with aiohttp.ClientSession() as session:
        # Teste 1: Listar ordens
        print("🧪 Teste 1: GET /api/v1/orders")
        try:
            async with session.get(f"{base_url}/orders") as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"   ✅ Status: {response.status}")
                    print(f"   📊 Total orders: {data.get('total', 0)}")
                    print(f"   📋 Structure: {list(data.keys())}")
                else:
                    text = await response.text()
                    print(f"   ❌ Status: {response.status}")
                    print(f"   Error: {text}")
        except Exception as e:
            print(f"   ❌ Exception: {e}")

        print()

        # Teste 2: Estatísticas
        print("🧪 Teste 2: GET /api/v1/orders/stats")
        try:
            async with session.get(f"{base_url}/orders/stats") as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"   ✅ Status: {response.status}")
                    print(f"   📊 Stats: {json.dumps(data, indent=2)}")
                else:
                    text = await response.text()
                    print(f"   ❌ Status: {response.status}")
                    print(f"   Error: {text}")
        except Exception as e:
            print(f"   ❌ Exception: {e}")

        print()

        # Teste 3: Ordem específica
        print("🧪 Teste 3: GET /api/v1/orders/1")
        try:
            async with session.get(f"{base_url}/orders/1") as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"   ✅ Status: {response.status}")
                    print(
                        f"   📋 Order details: {data.get('data', {}).get('symbol', 'N/A')}"
                    )
                else:
                    text = await response.text()
                    print(f"   ❌ Status: {response.status}")
                    print(f"   Error: {text}")
        except Exception as e:
            print(f"   ❌ Exception: {e}")

        print()

        # Teste 4: Criar ordem de teste
        print("🧪 Teste 4: POST /api/v1/orders/test")
        try:
            async with session.post(f"{base_url}/orders/test") as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"   ✅ Status: {response.status}")
                    print(f"   💼 Test order created: {data.get('success', False)}")
                else:
                    text = await response.text()
                    print(f"   ❌ Status: {response.status}")
                    print(f"   Error: {text}")
        except Exception as e:
            print(f"   ❌ Exception: {e}")


if __name__ == "__main__":
    print("🔍 Testando endpoints de ordens...")
    asyncio.run(test_orders_api())
    print("\n✅ Testes concluídos!")

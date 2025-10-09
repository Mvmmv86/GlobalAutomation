#!/usr/bin/env python3
"""
Test script para diagnosticar problema com ordens AVAX
"""
import asyncio
import os
from infrastructure.exchanges.binance_connector import BinanceConnector
from binance.client import Client

async def test_symbol_info():
    """Verifica informações do símbolo AVAX na Binance"""

    # Carregar credenciais
    api_key = os.getenv('BINANCE_API_KEY')
    api_secret = os.getenv('BINANCE_API_SECRET')

    if not api_key or not api_secret:
        print("❌ Credenciais não encontradas!")
        return

    connector = BinanceConnector(api_key, api_secret, testnet=False)

    # Teste 1: Buscar info do símbolo AVAXUSDT
    print("=" * 60)
    print("🔍 TESTE 1: Informações do símbolo AVAXUSDT")
    print("=" * 60)

    try:
        client = Client(api_key, api_secret)
        exchange_info = client.futures_exchange_info()

        # Encontrar AVAXUSDT
        avax_info = next(
            (s for s in exchange_info['symbols'] if s['symbol'] == 'AVAXUSDT'),
            None
        )

        if avax_info:
            print(f"\n✅ Símbolo encontrado: {avax_info['symbol']}")
            print(f"   Status: {avax_info['status']}")
            print(f"   Base Asset: {avax_info['baseAsset']}")
            print(f"   Quote Asset: {avax_info['quoteAsset']}")

            # Filtros importantes
            print("\n📊 FILTROS:")
            for filter_info in avax_info['filters']:
                if filter_info['filterType'] == 'LOT_SIZE':
                    print(f"\n   LOT_SIZE:")
                    print(f"      minQty: {filter_info['minQty']}")
                    print(f"      maxQty: {filter_info['maxQty']}")
                    print(f"      stepSize: {filter_info['stepSize']}")

                elif filter_info['filterType'] == 'PRICE_FILTER':
                    print(f"\n   PRICE_FILTER:")
                    print(f"      minPrice: {filter_info['minPrice']}")
                    print(f"      maxPrice: {filter_info['maxPrice']}")
                    print(f"      tickSize: {filter_info['tickSize']}")

                elif filter_info['filterType'] == 'MIN_NOTIONAL':
                    print(f"\n   MIN_NOTIONAL:")
                    print(f"      notional: {filter_info['notional']}")
        else:
            print("❌ Símbolo AVAXUSDT não encontrado!")

    except Exception as e:
        print(f"❌ Erro ao buscar info do símbolo: {e}")

    # Teste 2: Comparar com BTCUSDT
    print("\n" + "=" * 60)
    print("🔍 TESTE 2: Comparação BTCUSDT vs AVAXUSDT")
    print("=" * 60)

    try:
        btc_info = next(
            (s for s in exchange_info['symbols'] if s['symbol'] == 'BTCUSDT'),
            None
        )

        if btc_info:
            print("\n✅ BTCUSDT:")
            for filter_info in btc_info['filters']:
                if filter_info['filterType'] == 'LOT_SIZE':
                    print(f"   LOT_SIZE stepSize: {filter_info['stepSize']}")
                    print(f"   LOT_SIZE minQty: {filter_info['minQty']}")

    except Exception as e:
        print(f"❌ Erro: {e}")

    # Teste 3: Simular arredondamento
    print("\n" + "=" * 60)
    print("🔍 TESTE 3: Simulação de arredondamento ERRADO")
    print("=" * 60)

    test_quantities = [1.0, 0.5, 0.1, 10.0, 100.0]

    for qty in test_quantities:
        rounded = round(qty, 3)  # Código atual (ERRADO)
        print(f"   Quantidade original: {qty} → Arredondada: {rounded}")

    print("\n⚠️  PROBLEMA IDENTIFICADO:")
    print("   O código atual SEMPRE arredonda para 3 decimais,")
    print("   mas cada símbolo tem seu próprio stepSize!")

if __name__ == "__main__":
    asyncio.run(test_symbol_info())

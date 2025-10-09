#!/usr/bin/env python3
"""
Test script simplificado - apenas verifica precisão na Binance (sem credenciais)
"""
import requests

def test_symbol_precision():
    """Verifica precisão dos símbolos na Binance (API pública)"""

    print("=" * 60)
    print("🔍 Verificando precisão de símbolos na Binance")
    print("=" * 60)

    try:
        # API pública da Binance - não precisa de credenciais
        response = requests.get('https://fapi.binance.com/fapi/v1/exchangeInfo')
        data = response.json()

        symbols_to_check = ['BTCUSDT', 'AVAXUSDT', 'ETHUSDT']

        for symbol_name in symbols_to_check:
            symbol_info = next(
                (s for s in data['symbols'] if s['symbol'] == symbol_name),
                None
            )

            if symbol_info:
                print(f"\n{'='*60}")
                print(f"✅ {symbol_name}")
                print(f"{'='*60}")
                print(f"Status: {symbol_info['status']}")
                print(f"Quantity Precision: {symbol_info.get('quantityPrecision', 'N/A')}")
                print(f"Price Precision: {symbol_info.get('pricePrecision', 'N/A')}")

                # Buscar filtros
                for filter_info in symbol_info['filters']:
                    if filter_info['filterType'] == 'LOT_SIZE':
                        step_size = float(filter_info['stepSize'])
                        min_qty = float(filter_info['minQty'])
                        max_qty = float(filter_info['maxQty'])

                        print(f"\n📊 LOT_SIZE Filter:")
                        print(f"   minQty: {min_qty}")
                        print(f"   maxQty: {max_qty}")
                        print(f"   stepSize: {step_size}")

                        # Descobrir quantas casas decimais
                        step_str = filter_info['stepSize']
                        if '.' in step_str:
                            decimals = len(step_str.split('.')[1].rstrip('0'))
                        else:
                            decimals = 0

                        print(f"   ⚠️  DECIMAIS CORRETOS: {decimals}")

                    elif filter_info['filterType'] == 'PRICE_FILTER':
                        tick_size = float(filter_info['tickSize'])
                        print(f"\n💰 PRICE_FILTER:")
                        print(f"   tickSize: {tick_size}")

                    elif filter_info['filterType'] == 'MIN_NOTIONAL':
                        notional = float(filter_info['notional'])
                        print(f"\n💵 MIN_NOTIONAL:")
                        print(f"   notional: ${notional}")

            else:
                print(f"\n❌ {symbol_name} não encontrado!")

        # Mostrar o PROBLEMA
        print("\n" + "=" * 60)
        print("⚠️  PROBLEMA IDENTIFICADO NO CÓDIGO")
        print("=" * 60)
        print("\nCódigo atual (binance_connector.py linha 727-730):")
        print("```python")
        print("if 'BTC' in symbol.upper():")
        print("    quantity = round(quantity, 3)")
        print("else:")
        print("    quantity = round(quantity, 3)  # Default")
        print("```")
        print("\n❌ Isso está ERRADO! Cada símbolo tem precisão diferente!")
        print("\n✅ SOLUÇÃO: Buscar stepSize dinamicamente para cada símbolo")

    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_symbol_precision()

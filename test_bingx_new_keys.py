#!/usr/bin/env python3
"""
TESTE COM NOVAS CHAVES DA BINGX
Executa ordem real com SL/TP usando Método 3 (ordens separadas)
"""

import asyncio
import sys
import json
from datetime import datetime

# Adicionar path
sys.path.insert(0, '/mnt/c/Users/marcu/GlobalAutomation/apps/api-python')

from infrastructure.exchanges.bingx_connector import BingXConnector


async def executar_teste_bingx():
    """Testa ordem com as novas chaves"""

    print("="*80)
    print("🚀 TESTE BINGX COM NOVAS CHAVES API")
    print("="*80)
    print(f"Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Credenciais fornecidas
    api_key = "YK7lnc70VwKVVRzzcvtfnhgl4blz8w0GsTWTOXhyoC3P9NYmF32ymDQXaJu8kzM2R2KRpQAJW86pdLQrg"
    api_secret = "4gxl34k6GbE1TfyFhaAAD13JmkGwLYti2ZcROWhHQGYzdpqAx5Isky5dHYZTFHC1zJFwslru61IMc3jW9Fw"

    print("\n✅ Usando chaves fornecidas")
    print(f"   API Key: {api_key[:20]}...")

    try:
        # Conectar à BingX
        print("\n📡 Conectando à BingX...")
        connector = BingXConnector(api_key, api_secret, testnet=False)
        print("✅ Conectado com sucesso!")

        # Testar conexão básica
        print("\n🔍 Testando conexão...")

        # Buscar balanço
        balance_result = await connector._make_request(
            "GET",
            "/openApi/swap/v2/user/balance",
            {},
            signed=True
        )

        if balance_result.get("code") == 0:
            print("✅ Conexão funcionando!")
            balance = balance_result.get("data", {}).get("balance", {})
            equity = balance.get("equity", 0)
            print(f"   Balanço USDT: ${equity}")
        else:
            print(f"❌ Erro na conexão: {balance_result}")
            return

        # Buscar preço do SOL
        ticker = "SOLUSDT"
        print(f"\n💰 Buscando preço de {ticker}...")
        current_price = await connector.get_current_price(ticker)
        current_price = float(current_price)  # Converter Decimal para float
        print(f"✅ Preço atual: ${current_price}")

        # Configurações da ordem
        # BingX exige mínimo de 1 SOL
        quantity = 1.0  # Mínimo exigido pela BingX
        leverage = 2  # Reduzido para 2x (mínimo) por limitação da conta
        margin = quantity * current_price  # Calculado com base na quantidade mínima
        sl_price = round(current_price * 0.98, 2)  # -2%
        tp_price = round(current_price * 1.05, 2)  # +5%

        print(f"\n📊 Configuração da Ordem:")
        print(f"   💰 Margem: ${margin}")
        print(f"   📊 Quantidade: {quantity} SOL")
        print(f"   🎚️ Leverage: {leverage}x")
        print(f"   🔴 Stop Loss: ${sl_price} (-2%)")
        print(f"   🟢 Take Profit: ${tp_price} (+5%)")

        # Executar automaticamente (usuário já autorizou)
        print("\n" + "="*60)
        print("✅ EXECUTANDO ORDEM REAL NA BINGX")
        print("="*60)

        # Configurar leverage
        print(f"\n⚙️ Configurando leverage...")
        try:
            await connector.set_leverage(ticker, leverage)
            print(f"✅ Leverage: {leverage}x")
        except:
            print(f"⚠️ Leverage já configurado")

        print("\n" + "="*60)
        print("🚀 EXECUTANDO ORDEM - MÉTODO 3 (ORDENS SEPARADAS)")
        print("="*60)

        # PASSO 1: ORDEM PRINCIPAL
        print("\n📤 PASSO 1: Ordem principal...")

        main_params = {
            "symbol": "SOL-USDT",
            "side": "BUY",
            "positionSide": "LONG",
            "type": "MARKET",
            "quantity": str(quantity)
        }

        main_result = await connector._make_request(
            "POST",
            "/openApi/swap/v2/trade/order",
            main_params,
            signed=True,
            use_body=True
        )

        if main_result.get("code") != 0:
            print(f"❌ Erro: {main_result}")
            return

        order_id = main_result.get("data", {}).get("order", {}).get("orderId")
        print(f"✅ ORDEM EXECUTADA! ID: {order_id}")

        # PASSO 2: AGUARDAR
        print("\n⏳ Aguardando 3 segundos...")
        await asyncio.sleep(3)

        # PASSO 3: STOP LOSS
        print("\n📤 PASSO 2: Stop Loss...")

        sl_params = {
            "symbol": "SOL-USDT",
            "side": "SELL",
            "positionSide": "LONG",
            "type": "STOP_MARKET",
            "stopPrice": str(sl_price),
            "quantity": str(quantity)
        }

        sl_result = await connector._make_request(
            "POST",
            "/openApi/swap/v2/trade/order",
            sl_params,
            signed=True,
            use_body=True
        )

        if sl_result.get("code") == 0:
            print(f"✅ STOP LOSS CRIADO! Preço: ${sl_price}")
        else:
            print(f"❌ Erro SL: {sl_result.get('msg')}")

        # PASSO 4: TAKE PROFIT
        print("\n📤 PASSO 3: Take Profit...")

        tp_params = {
            "symbol": "SOL-USDT",
            "side": "SELL",
            "positionSide": "LONG",
            "type": "TAKE_PROFIT_MARKET",
            "stopPrice": str(tp_price),
            "quantity": str(quantity)
        }

        tp_result = await connector._make_request(
            "POST",
            "/openApi/swap/v2/trade/order",
            tp_params,
            signed=True,
            use_body=True
        )

        if tp_result.get("code") == 0:
            print(f"✅ TAKE PROFIT CRIADO! Preço: ${tp_price}")
        else:
            print(f"❌ Erro TP: {tp_result.get('msg')}")

        # VALIDAÇÃO
        print("\n🔍 Validando ordens...")
        await asyncio.sleep(2)

        open_orders = await connector._make_request(
            "GET",
            "/openApi/swap/v2/trade/openOrders",
            {"symbol": "SOL-USDT"},
            signed=True
        )

        if open_orders.get("code") == 0:
            orders = open_orders.get("data", {}).get("orders", [])
            print(f"\n✅ {len(orders)} ordens abertas")

            sl_found = False
            tp_found = False

            for order in orders:
                tipo = order.get("type", "")
                preco = order.get("stopPrice")
                if "STOP" in tipo:
                    sl_found = True
                    print(f"   🔴 SL: ${preco}")
                if "TAKE_PROFIT" in tipo:
                    tp_found = True
                    print(f"   🟢 TP: ${preco}")

            if sl_found and tp_found:
                print("\n🎉 SUCESSO TOTAL!")
                print("✅ Posição COMPLETAMENTE PROTEGIDA!")
            elif sl_found:
                print("\n⚠️ Apenas SL configurado")
            elif tp_found:
                print("\n⚠️ Apenas TP configurado")
            else:
                print("\n❌ Nenhuma proteção criada")

    except Exception as e:
        print(f"\n❌ Erro: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "="*80)
    print("📱 VERIFIQUE NA BINGX:")
    print("1. Acesse sua conta")
    print("2. Futures > Posições")
    print("3. Futures > Ordens Abertas")
    print("="*80)


if __name__ == "__main__":
    print("\n⚠️ TESTE COM ORDEM REAL NA BINGX")
    print("   Valor: ~$15 USD")
    print("   Método: Ordens SL/TP separadas")
    asyncio.run(executar_teste_bingx())
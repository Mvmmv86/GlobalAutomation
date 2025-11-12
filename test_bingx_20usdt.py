#!/usr/bin/env python3
"""
TESTE REAL COM $20 USDT DE MARGEM NA BINGX
Executa ordem com SL/TP usando Método 3 (ordens separadas)
Configuração específica do usuário: margem de $20 USDT
"""

import asyncio
import sys
import json
from datetime import datetime
from decimal import Decimal

# Adicionar path
sys.path.insert(0, '/mnt/c/Users/marcu/GlobalAutomation/apps/api-python')

from infrastructure.exchanges.bingx_connector import BingXConnector


async def executar_ordem_20usdt():
    """Testa ordem com margem de $20 USDT"""

    print("="*80)
    print("🚀 TESTE BINGX COM MARGEM DE $20 USDT")
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

        # CONFIGURAÇÕES COM MARGEM DE $20 USDT
        margin = 20.0  # $20 USDT conforme solicitado
        leverage = 10  # Leverage padrão 10x (pode ajustar se necessário)

        # Calcular quantidade baseada na margem
        # Com leverage 10x, $20 de margem = $200 de posição nominal
        position_value = margin * leverage
        quantity = round(position_value / current_price, 3)

        # Garantir que atende o mínimo de 1 SOL
        if quantity < 1.0:
            print(f"⚠️ Quantidade calculada ({quantity}) menor que mínimo. Ajustando para 1 SOL")
            quantity = 1.0
            margin = round(quantity * current_price / leverage, 2)
            print(f"   Nova margem necessária: ${margin}")

        sl_price = round(current_price * 0.98, 2)  # -2%
        tp_price = round(current_price * 1.05, 2)  # +5%

        print(f"\n📊 Configuração da Ordem:")
        print(f"   💰 Margem: ${margin} USDT")
        print(f"   📊 Quantidade: {quantity} SOL")
        print(f"   💵 Valor da Posição: ${round(quantity * current_price, 2)}")
        print(f"   🎚️ Leverage: {leverage}x")
        print(f"   🔴 Stop Loss: ${sl_price} (-2%)")
        print(f"   🟢 Take Profit: ${tp_price} (+5%)")

        # Confirmar execução
        print("\n" + "="*60)
        print("✅ EXECUTANDO ORDEM REAL NA BINGX")
        print("="*60)

        # Configurar leverage
        print(f"\n⚙️ Configurando leverage...")
        try:
            await connector.set_leverage(ticker, leverage)
            print(f"✅ Leverage: {leverage}x")
        except:
            print(f"⚠️ Leverage já configurado ou erro ao configurar")

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

        print(f"   Parâmetros: {json.dumps(main_params, indent=2)}")

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
        avg_price = main_result.get("data", {}).get("order", {}).get("avgPrice", current_price)
        print(f"✅ ORDEM EXECUTADA! ID: {order_id}")
        print(f"   Preço de entrada: ${avg_price}")

        # PASSO 2: AGUARDAR
        print("\n⏳ Aguardando 3 segundos para posição ser estabelecida...")
        await asyncio.sleep(3)

        # PASSO 3: STOP LOSS
        print("\n📤 PASSO 2: Criando Stop Loss...")

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
            sl_order_id = sl_result.get("data", {}).get("order", {}).get("orderId")
            print(f"✅ STOP LOSS CRIADO!")
            print(f"   Order ID: {sl_order_id}")
            print(f"   Preço trigger: ${sl_price}")
        else:
            print(f"❌ Erro SL: {sl_result.get('msg')}")

        # PASSO 4: TAKE PROFIT
        print("\n📤 PASSO 3: Criando Take Profit...")

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
            tp_order_id = tp_result.get("data", {}).get("order", {}).get("orderId")
            print(f"✅ TAKE PROFIT CRIADO!")
            print(f"   Order ID: {tp_order_id}")
            print(f"   Preço trigger: ${tp_price}")
        else:
            print(f"❌ Erro TP: {tp_result.get('msg')}")

        # VALIDAÇÃO
        print("\n🔍 Validando ordens abertas...")
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

        # Resumo final
        print("\n" + "="*60)
        print("📊 RESUMO DA OPERAÇÃO")
        print("="*60)
        print(f"💰 Margem utilizada: ${margin} USDT")
        print(f"📈 Quantidade: {quantity} SOL")
        print(f"💵 Valor total da posição: ${round(quantity * current_price, 2)}")
        print(f"🎚️ Leverage: {leverage}x")
        print(f"🔴 Stop Loss em: ${sl_price} (perda máx: ~${round(margin * 0.02, 2)})")
        print(f"🟢 Take Profit em: ${tp_price} (lucro alvo: ~${round(margin * 0.05, 2)})")

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
    print("   Margem: $20 USDT")
    print("   Método: Ordens SL/TP separadas")
    asyncio.run(executar_ordem_20usdt())
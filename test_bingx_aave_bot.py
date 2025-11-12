#!/usr/bin/env python3
"""
TESTE REAL COM BOT AAVE NA BINGX
Executa ordem com AAVEUSDT usando Método 3 (ordens separadas)
Busca configurações específicas do bot AAVE do banco de dados
"""

import asyncio
import sys
import json
from datetime import datetime
from decimal import Decimal

# Adicionar path
sys.path.insert(0, '/mnt/c/Users/marcu/GlobalAutomation/apps/api-python')

from infrastructure.exchanges.bingx_connector import BingXConnector
from infrastructure.security.encryption_service import EncryptionService
import asyncpg


async def executar_ordem_aave():
    """Testa ordem com bot AAVE"""

    print("="*80)
    print("🚀 TESTE BINGX COM BOT AAVE")
    print("="*80)
    print(f"Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Conectar ao banco
    conn = await asyncpg.connect(
        "postgresql://postgres.zmdqmrugotfftxvrwdsd:Wzg0kBvtrSbclQ9V@aws-1-us-east-2.pooler.supabase.com:5432/postgres?sslmode=require"
    )

    try:
        # 1. Buscar bot AAVE com configurações
        print("\n1️⃣ Buscando bot AAVE no banco de dados...")

        bot_data = await conn.fetchrow("""
            SELECT
                b.id, b.name, b.market_type, b.symbol,
                bs.custom_margin_usd,
                bs.custom_leverage,
                bs.custom_stop_loss_pct,
                bs.custom_take_profit_pct,
                ea.api_key, ea.secret_key, ea.name as account_name
            FROM bots b
            JOIN bot_subscriptions bs ON b.id = bs.bot_id
            JOIN exchange_accounts ea ON ea.id = bs.exchange_account_id
            WHERE b.symbol = 'AAVEUSDT'
            AND b.market_type = 'futures'
            AND ea.exchange = 'bingx'
            AND ea.is_active = true
            AND bs.status = 'active'
            LIMIT 1
        """)

        if not bot_data:
            print("⚠️ Bot AAVE não encontrado, buscando configurações padrão...")

            # Buscar qualquer conta BingX ativa
            account = await conn.fetchrow("""
                SELECT api_key, secret_key, name
                FROM exchange_accounts
                WHERE exchange = 'bingx'
                AND is_active = true
                AND testnet = false
                LIMIT 1
            """)

            if not account:
                print("❌ Nenhuma conta BingX encontrada!")
                return

            bot_data = {
                'name': 'AAVE Manual Test',
                'symbol': 'AAVEUSDT',
                'account_name': account['name'],
                'api_key': account['api_key'],
                'secret_key': account['secret_key'],
                'custom_margin_usd': 20.0,  # $20 USDT padrão
                'custom_leverage': 10,
                'custom_stop_loss_pct': 2.0,
                'custom_take_profit_pct': 5.0
            }

        print(f"✅ Bot: {bot_data['name']}")
        print(f"✅ Símbolo: {bot_data['symbol']}")
        print(f"✅ Conta: {bot_data['account_name']}")

        # 2. Descriptografar credenciais
        print("\n2️⃣ Conectando à BingX...")
        encryption_service = EncryptionService()
        api_key = encryption_service.decrypt_value(bot_data['api_key'])
        api_secret = encryption_service.decrypt_value(bot_data['secret_key'])

        connector = BingXConnector(api_key, api_secret, testnet=False)
        print("✅ Conectado à BingX (Produção)")

        # 3. Buscar preço atual do AAVE
        ticker = bot_data['symbol']
        print(f"\n3️⃣ Buscando preço de {ticker}...")
        current_price = await connector.get_current_price(ticker)
        current_price = float(current_price)
        print(f"✅ Preço atual: ${current_price}")

        # 4. Configurações (usar custom ou padrão)
        margin = bot_data['custom_margin_usd'] or 20.0  # $20 USDT padrão
        leverage = bot_data['custom_leverage'] or 10
        stop_loss_pct = bot_data['custom_stop_loss_pct'] or 2.0
        take_profit_pct = bot_data['custom_take_profit_pct'] or 5.0

        # 5. Calcular parâmetros
        position_value = margin * leverage
        quantity = round(position_value / current_price, 3)

        # Verificar quantidade mínima para AAVE
        # BingX geralmente requer mínimo de 0.1 AAVE
        min_quantity = 0.1
        if quantity < min_quantity:
            print(f"⚠️ Quantidade calculada ({quantity}) menor que mínimo. Ajustando para {min_quantity} AAVE")
            quantity = min_quantity
            margin = round(quantity * current_price / leverage, 2)
            print(f"   Nova margem necessária: ${margin}")

        sl_price = round(current_price * (1 - stop_loss_pct / 100), 2)
        tp_price = round(current_price * (1 + take_profit_pct / 100), 2)

        print(f"\n4️⃣ Configuração da Ordem:")
        print(f"   💰 Margem: ${margin} USDT")
        print(f"   📊 Quantidade: {quantity} AAVE")
        print(f"   💵 Valor da Posição: ${round(quantity * current_price, 2)}")
        print(f"   🎚️ Leverage: {leverage}x")
        print(f"   🔴 Stop Loss: ${sl_price} (-{stop_loss_pct}%)")
        print(f"   🟢 Take Profit: ${tp_price} (+{take_profit_pct}%)")

        # Confirmar execução
        print("\n" + "="*60)
        print("✅ EXECUTANDO ORDEM REAL NA BINGX - AAVE")
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

        # Formatar símbolo para BingX (AAVE-USDT)
        bingx_symbol = ticker.replace("USDT", "-USDT")

        main_params = {
            "symbol": bingx_symbol,
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
        executed_qty = main_result.get("data", {}).get("order", {}).get("executedQty", quantity)
        print(f"✅ ORDEM EXECUTADA! ID: {order_id}")
        print(f"   Preço de entrada: ${avg_price}")
        print(f"   Quantidade executada: {executed_qty} AAVE")

        # Usar a quantidade real executada para SL/TP
        actual_quantity = float(executed_qty)

        # PASSO 2: AGUARDAR
        print("\n⏳ Aguardando 3 segundos para posição ser estabelecida...")
        await asyncio.sleep(3)

        # PASSO 3: STOP LOSS
        print("\n📤 PASSO 2: Criando Stop Loss...")

        sl_params = {
            "symbol": bingx_symbol,
            "side": "SELL",
            "positionSide": "LONG",
            "type": "STOP_MARKET",
            "stopPrice": str(sl_price),
            "quantity": str(actual_quantity)
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
            "symbol": bingx_symbol,
            "side": "SELL",
            "positionSide": "LONG",
            "type": "TAKE_PROFIT_MARKET",
            "stopPrice": str(tp_price),
            "quantity": str(actual_quantity)
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
            {"symbol": bingx_symbol},
            signed=True
        )

        if open_orders.get("code") == 0:
            orders = open_orders.get("data", {}).get("orders", [])

            # Filtrar apenas ordens de AAVE
            aave_orders = [o for o in orders if o.get("symbol") == bingx_symbol]
            print(f"\n✅ {len(aave_orders)} ordens de AAVE abertas")

            sl_found = False
            tp_found = False

            for order in aave_orders:
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
                print("✅ Posição AAVE COMPLETAMENTE PROTEGIDA!")
            elif sl_found:
                print("\n⚠️ Apenas SL configurado")
            elif tp_found:
                print("\n⚠️ Apenas TP configurado")
            else:
                print("\n❌ Nenhuma proteção criada")

        # Resumo final
        print("\n" + "="*60)
        print("📊 RESUMO DA OPERAÇÃO - AAVE")
        print("="*60)
        print(f"🪙 Ativo: AAVE")
        print(f"💰 Margem utilizada: ${margin} USDT")
        print(f"📈 Quantidade: {actual_quantity} AAVE")
        print(f"💵 Valor total da posição: ${round(actual_quantity * float(avg_price), 2)}")
        print(f"🎚️ Leverage: {leverage}x")
        print(f"🔴 Stop Loss em: ${sl_price} (perda máx: ~${round(margin * (stop_loss_pct / 100), 2)})")
        print(f"🟢 Take Profit em: ${tp_price} (lucro alvo: ~${round(margin * (take_profit_pct / 100), 2)})")

    except Exception as e:
        print(f"\n❌ Erro: {e}")
        import traceback
        traceback.print_exc()

    finally:
        await conn.close()

    print("\n" + "="*80)
    print("📱 VERIFIQUE NA BINGX:")
    print("1. Acesse sua conta")
    print("2. Futures > Posições")
    print("3. Confirme a posição de AAVE")
    print("4. Futures > Ordens Abertas")
    print("5. Confirme SL e TP de AAVE")
    print("="*80)


if __name__ == "__main__":
    print("\n⚠️ TESTE COM ORDEM REAL NA BINGX - AAVE")
    print("   Bot: AAVE")
    print("   Método: Ordens SL/TP separadas")
    asyncio.run(executar_ordem_aave())
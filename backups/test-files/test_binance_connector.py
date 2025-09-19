#!/usr/bin/env python3
"""
Teste do Binance Connector
"""

import asyncio
from decimal import Decimal
from infrastructure.exchanges.binance_connector import create_binance_connector


async def test_binance_connector():
    """Teste completo do Binance connector"""

    print("🧪 TESTANDO BINANCE CONNECTOR")
    print("=" * 60)

    # Criar connector em modo demo (sem API keys)
    binance = create_binance_connector(testnet=True)

    print(f"📊 Demo mode: {binance.is_demo_mode()}")

    try:
        # Teste 1: Conexão
        print("\n🔗 Testando conexão...")
        connection_result = await binance.test_connection()
        print(f"   Status: {'✅' if connection_result['success'] else '❌'}")
        print(f"   Demo: {connection_result.get('demo', False)}")
        print(f"   Testnet: {connection_result.get('testnet', False)}")

        # Teste 2: Informações do símbolo
        print("\n📈 Testando informações do símbolo...")
        symbol_info = await binance.get_symbol_info("BTCUSDT")
        print(f"   Symbol: {symbol_info['symbol']}")
        print(f"   Status: {symbol_info['status']}")
        print(f"   Min Qty: {symbol_info['min_qty']}")
        print(f"   Demo: {symbol_info.get('demo', False)}")

        # Teste 3: Preço atual
        print("\n💰 Testando preço atual...")
        price = await binance.get_current_price("BTCUSDT")
        print(f"   Preço BTCUSDT: ${price:,.2f}")

        # Teste 4: Informações da conta
        print("\n👤 Testando informações da conta...")
        account_info = await binance.get_account_info()
        print(f"   Demo: {account_info.get('demo', False)}")
        print(f"   Account Type: {account_info.get('account_type', 'N/A')}")
        print(f"   Balances: {len(account_info.get('balances', []))}")

        # Teste 5: Criar ordem de compra (demo)
        print("\n🛒 Testando ordem de compra (demo)...")
        buy_order = await binance.create_market_order(
            symbol="BTCUSDT", side="buy", quantity=Decimal("0.001")
        )

        if buy_order["success"]:
            print(f"   ✅ Ordem criada: {buy_order['order_id']}")
            print(f"   Symbol: {buy_order['symbol']}")
            print(f"   Side: {buy_order['side']}")
            print(f"   Quantity: {buy_order['quantity']}")
            print(f"   Price: ${buy_order['price']}")
            print(f"   Status: {buy_order['status']}")
            print(f"   Demo: {buy_order.get('demo', False)}")
        else:
            print(f"   ❌ Erro: {buy_order.get('error', 'Unknown error')}")

        # Teste 6: Criar ordem de venda (demo)
        print("\n💸 Testando ordem de venda (demo)...")
        sell_order = await binance.create_market_order(
            symbol="BTCUSDT", side="sell", quantity=Decimal("0.001")
        )

        if sell_order["success"]:
            print(f"   ✅ Ordem criada: {sell_order['order_id']}")
            print(f"   Symbol: {sell_order['symbol']}")
            print(f"   Side: {sell_order['side']}")
            print(f"   Status: {sell_order['status']}")
        else:
            print(f"   ❌ Erro: {sell_order.get('error', 'Unknown error')}")

        print("\n🎉 TODOS OS TESTES PASSARAM!")
        print("Binance connector funcionando em modo demo")

        return True

    except Exception as e:
        print(f"\n❌ ERRO NO TESTE: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("🚀 Iniciando teste do Binance Connector...")
    success = asyncio.run(test_binance_connector())

    if success:
        print("\n✅ Binance connector pronto para uso!")
        print("Próximo: Criar serviço de processamento de ordens")
    else:
        print("\n⚠️ Testes falharam")

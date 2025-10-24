"""
Script para mostrar saldos USDT em SPOT e FUTURES
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from infrastructure.database.connection_transaction_mode import transaction_db
from infrastructure.exchanges.binance_connector import BinanceConnector

async def get_usdt_balances():
    """Busca saldos USDT em SPOT e FUTURES"""

    account_id = "9b9cbe41-a6a1-46ff-a72d-76c74119582d"

    print("\n" + "="*80)
    print("💰 SALDOS EM USDT - SPOT E FUTURES")
    print("="*80 + "\n")

    await transaction_db.connect()

    try:
        # 1. BUSCAR CREDENCIAIS
        account = await transaction_db.fetchrow("""
            SELECT api_key, secret_key, COALESCE(testnet, false) as testnet
            FROM exchange_accounts
            WHERE id = $1
        """, account_id)

        if not account:
            print("❌ Conta não encontrada!")
            return

        # 2. CRIAR CONNECTOR
        connector = BinanceConnector(
            api_key=account['api_key'],
            api_secret=account['secret_key'],
            testnet=account['testnet']
        )

        # 3. BUSCAR SALDO SPOT (USDT)
        print("📊 SPOT:")
        print("-" * 80)

        spot_result = await connector.get_account_info()

        if spot_result.get('success'):
            balances = spot_result.get('balances', [])
            usdt_spot = None

            for bal in balances:
                if bal.get('asset') == 'USDT':
                    usdt_spot = bal
                    break

            if usdt_spot:
                free = float(usdt_spot.get('free', 0))
                locked = float(usdt_spot.get('locked', 0))
                total = free + locked

                print(f"  Asset: USDT")
                print(f"  Free:   ${free:.8f}")
                print(f"  Locked: ${locked:.8f}")
                print(f"  Total:  ${total:.8f}")
            else:
                print("  ⚠️  Nenhum saldo USDT encontrado")
        else:
            print(f"  ❌ ERRO: {spot_result.get('error')}")

        # 4. BUSCAR SALDO FUTURES (USDT)
        print("\n🚀 FUTURES:")
        print("-" * 80)

        futures_result = await connector.get_futures_account()

        if futures_result.get('success'):
            assets = futures_result.get('assets', [])
            usdt_futures = None

            for asset in assets:
                if asset.get('asset') == 'USDT':
                    usdt_futures = asset
                    break

            if usdt_futures:
                wallet = float(usdt_futures.get('walletBalance', 0))
                unrealized = float(usdt_futures.get('unrealizedProfit', 0))
                available = float(usdt_futures.get('availableBalance', 0))
                cross_wallet = float(usdt_futures.get('crossWalletBalance', 0))
                margin = float(usdt_futures.get('marginBalance', 0))

                print(f"  Asset: USDT")
                print(f"  Wallet Balance:        ${wallet:.8f}")
                print(f"  Available Balance:     ${available:.8f}")
                print(f"  Cross Wallet Balance:  ${cross_wallet:.8f}")
                print(f"  Margin Balance:        ${margin:.8f}")
                print(f"  Unrealized Profit:     ${unrealized:.8f}")
                print(f"  Total (with PnL):      ${wallet + unrealized:.8f}")
            else:
                print("  ⚠️  Nenhum saldo USDT encontrado em FUTURES")
        else:
            print(f"  ❌ ERRO: {futures_result.get('error')}")

        # 5. RESUMO TOTAL
        print("\n" + "="*80)
        print("📈 RESUMO TOTAL:")
        print("-" * 80)

        # Calcular totais
        spot_total = 0
        futures_total = 0

        if spot_result.get('success') and usdt_spot:
            spot_total = float(usdt_spot.get('free', 0)) + float(usdt_spot.get('locked', 0))

        if futures_result.get('success') and usdt_futures:
            futures_total = float(usdt_futures.get('walletBalance', 0))

        grand_total = spot_total + futures_total

        print(f"  SPOT USDT:     ${spot_total:.8f}")
        print(f"  FUTURES USDT:  ${futures_total:.8f}")
        print(f"  {'=' * 50}")
        print(f"  TOTAL GERAL:   ${grand_total:.8f}")

        print("\n" + "="*80 + "\n")

    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if transaction_db._pool:
            await transaction_db._pool.close()

if __name__ == "__main__":
    asyncio.run(get_usdt_balances())

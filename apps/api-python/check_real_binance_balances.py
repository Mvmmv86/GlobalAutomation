"""
Verifica saldos REAIS da Binance API AGORA (sem usar banco de dados)
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from infrastructure.database.connection_transaction_mode import transaction_db
from infrastructure.exchanges.binance_connector import BinanceConnector

async def check_real_balances():
    """Busca saldos REAIS da Binance agora"""

    account_id = "9b9cbe41-a6a1-46ff-a72d-76c74119582d"

    print("\n" + "="*80)
    print("🔍 VERIFICAÇÃO DE SALDOS REAIS DA BINANCE (AGORA)")
    print("="*80 + "\n")

    await transaction_db.connect()

    try:
        # 1. BUSCAR CREDENCIAIS DA CONTA
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

        # 3. BUSCAR SALDOS SPOT
        print("📊 SALDOS SPOT (Binance API - TEMPO REAL):")
        print("="*80)

        spot_result = await connector.get_account_info()

        if not spot_result.get('success'):
            print(f"❌ ERRO: {spot_result.get('error')}")
        else:
            balances = spot_result.get('balances', [])
            balances_with_balance = [b for b in balances if float(b.get('free', 0)) > 0 or float(b.get('locked', 0)) > 0]

            print(f"\n✅ Total: {len(balances_with_balance)} ativos com saldo\n")

            for bal in balances_with_balance:
                asset = bal.get('asset')
                free = float(bal.get('free', 0))
                locked = float(bal.get('locked', 0))
                total = free + locked
                print(f"  {asset:<10} | Free: {free:>15.8f} | Locked: {locked:>15.8f} | Total: {total:>15.8f}")

        # 4. BUSCAR SALDOS FUTURES
        print("\n" + "="*80)
        print("🚀 SALDOS FUTURES (Binance API - TEMPO REAL):")
        print("="*80)

        futures_result = await connector.get_futures_account()

        if not futures_result.get('success'):
            print(f"❌ ERRO: {futures_result.get('error')}")
        else:
            assets = futures_result.get('assets', [])
            assets_with_balance = [a for a in assets if float(a.get('walletBalance', 0)) != 0]

            if assets_with_balance:
                print(f"\n✅ Total: {len(assets_with_balance)} ativos com saldo\n")

                for asset_data in assets_with_balance:
                    asset = asset_data.get('asset')
                    wallet = float(asset_data.get('walletBalance', 0))
                    unrealized = float(asset_data.get('unrealizedProfit', 0))
                    available = float(asset_data.get('availableBalance', 0))
                    print(f"  {asset:<10} | Wallet: {wallet:>15.8f} | Available: {available:>15.8f} | Unrealized PnL: {unrealized:>15.8f}")
            else:
                print("\n⚠️  Nenhum saldo em FUTURES")

        # 5. BUSCAR POSIÇÕES FUTURES
        print("\n" + "="*80)
        print("📈 POSIÇÕES ABERTAS FUTURES (Binance API - TEMPO REAL):")
        print("="*80)

        positions_result = await connector.get_futures_positions()

        if not positions_result.get('success'):
            print(f"❌ ERRO: {positions_result.get('error')}")
        else:
            positions = positions_result.get('positions', [])
            open_positions = [p for p in positions if float(p.get('positionAmt', 0)) != 0]

            if open_positions:
                print(f"\n✅ Total: {len(open_positions)} posições abertas\n")

                for pos in open_positions:
                    symbol = pos.get('symbol')
                    side = 'LONG' if float(pos.get('positionAmt', 0)) > 0 else 'SHORT'
                    amt = abs(float(pos.get('positionAmt', 0)))
                    entry = float(pos.get('entryPrice', 0))
                    mark = float(pos.get('markPrice', 0))
                    pnl = float(pos.get('unRealizedProfit', 0))

                    print(f"  {symbol:<15} | {side:<6} | Amount: {amt:>12.4f} | Entry: {entry:>12.4f} | Mark: {mark:>12.4f} | PnL: {pnl:>12.4f}")
            else:
                print("\n⚠️  Nenhuma posição aberta em FUTURES")

        print("\n" + "="*80)
        print("✅ VERIFICAÇÃO CONCLUÍDA")
        print("="*80 + "\n")

    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if transaction_db._pool:
            await transaction_db._pool.close()

if __name__ == "__main__":
    asyncio.run(check_real_balances())

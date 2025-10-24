"""
Debug completo da resposta FUTURES da Binance
"""

import asyncio
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from infrastructure.database.connection_transaction_mode import transaction_db
from infrastructure.exchanges.binance_connector import BinanceConnector

async def debug_futures():
    account_id = "9b9cbe41-a6a1-46ff-a72d-76c74119582d"

    await transaction_db.connect()

    try:
        account = await transaction_db.fetchrow("""
            SELECT api_key, secret_key, COALESCE(testnet, false) as testnet
            FROM exchange_accounts
            WHERE id = $1
        """, account_id)

        connector = BinanceConnector(
            api_key=account['api_key'],
            api_secret=account['secret_key'],
            testnet=account['testnet']
        )

        print("\n" + "="*80)
        print("🔍 DEBUG COMPLETO - FUTURES ACCOUNT")
        print("="*80 + "\n")

        futures_result = await connector.get_futures_account()

        print("📦 RESPOSTA COMPLETA DA API:")
        print("-"*80)
        print(json.dumps(futures_result, indent=2))

        if futures_result.get('success'):
            print("\n✅ SUCESSO - Analisando dados...")

            # Total Account Info
            print("\n💰 INFORMAÇÕES DA CONTA:")
            print("-"*80)
            account_data = futures_result.get('account', {})
            print(f"Total Wallet Balance: ${account_data.get('totalWalletBalance', 0)}")
            print(f"Total Unrealized Profit: ${account_data.get('totalUnrealizedProfit', 0)}")
            print(f"Total Margin Balance: ${account_data.get('totalMarginBalance', 0)}")
            print(f"Total Available Balance: ${account_data.get('availableBalance', 0)}")
            print(f"Max Withdraw Amount: ${account_data.get('maxWithdrawAmount', 0)}")

            # Assets
            print("\n📊 ASSETS (TODOS):")
            print("-"*80)
            assets = futures_result.get('assets', [])

            if assets:
                for asset in assets:
                    asset_name = asset.get('asset')
                    wallet = float(asset.get('walletBalance', 0))
                    unrealized = float(asset.get('unrealizedProfit', 0))
                    available = float(asset.get('availableBalance', 0))

                    print(f"\n{asset_name}:")
                    print(f"  Wallet Balance:    ${wallet:.8f}")
                    print(f"  Available:         ${available:.8f}")
                    print(f"  Unrealized Profit: ${unrealized:.8f}")
            else:
                print("⚠️  Lista de assets vazia!")

        else:
            print(f"\n❌ ERRO: {futures_result.get('error')}")

        print("\n" + "="*80 + "\n")

    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if transaction_db._pool:
            await transaction_db._pool.close()

if __name__ == "__main__":
    asyncio.run(debug_futures())

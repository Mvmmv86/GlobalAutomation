"""
SCRIPT PARA SINCRONIZAR PRODUÇÃO DIRETAMENTE
- Conecta direto no banco Supabase
- Busca dados da Binance
- Insere no banco
- NÃO depende do backend da Digital Ocean
"""

import asyncio
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from infrastructure.database.connection_transaction_mode import transaction_db
from infrastructure.exchanges.binance_connector import BinanceConnector

async def sync_production():
    """Sincroniza PRODUÇÃO diretamente"""

    account_id = "9b9cbe41-a6a1-46ff-a72d-76c74119582d"

    print("\n" + "="*80)
    print("🚀 SINCRONIZAÇÃO DIRETA EM PRODUÇÃO")
    print("="*80 + "\n")

    await transaction_db.connect()

    try:
        # 1. BUSCAR CONTA
        print("1️⃣ Buscando conta da produção...")
        account = await transaction_db.fetchrow("""
            SELECT id, name, exchange, api_key, secret_key,
                   COALESCE(testnet, false) as testnet
            FROM exchange_accounts
            WHERE id = $1
        """, account_id)

        if not account:
            print(f"   ❌ Conta não encontrada!")
            return

        print(f"   ✅ Conta: {account['name']} ({account['exchange']})")
        print(f"      Testnet: {account['testnet']}")

        # 2. CRIAR CONNECTOR (PLAIN TEXT - SEM DESCRIPTOGRAFIA)
        print("\n2️⃣ Criando connector Binance...")
        connector = BinanceConnector(
            api_key=account['api_key'],
            api_secret=account['secret_key'],
            testnet=account['testnet']
        )
        print(f"   ✅ Connector criado!")

        # 3. BUSCAR SALDOS SPOT
        print("\n3️⃣ Buscando saldos SPOT da Binance...")
        spot_result = await connector.get_account_info()

        if not spot_result.get('success'):
            print(f"   ❌ ERRO: {spot_result.get('error')}")
            return

        balances = spot_result.get('balances', [])
        balances_with_balance = [b for b in balances if float(b.get('free', 0)) > 0 or float(b.get('locked', 0)) > 0]
        print(f"   ✅ {len(balances_with_balance)} ativos com saldo")

        # 4. BUSCAR FUTURES ACCOUNT
        print("\n4️⃣ Buscando dados FUTURES da Binance...")
        futures_result = await connector.get_futures_account()

        if futures_result.get('success'):
            futures_assets = futures_result.get('assets', [])
            futures_with_balance = [a for a in futures_assets if float(a.get('walletBalance', 0)) > 0]
            print(f"   ✅ {len(futures_with_balance)} ativos FUTURES com saldo")
        else:
            print(f"   ⚠️ Sem acesso a FUTURES: {futures_result.get('error')}")
            futures_with_balance = []

        # 5. LIMPAR SALDOS ANTIGOS
        print("\n5️⃣ Limpando saldos antigos da conta...")
        await transaction_db.execute("""
            DELETE FROM exchange_account_balances
            WHERE exchange_account_id = $1
        """, account_id)
        print(f"   ✅ Saldos antigos removidos")

        # 6. INSERIR SALDOS SPOT
        print("\n6️⃣ Inserindo saldos SPOT...")
        spot_count = 0
        for balance in balances_with_balance:
            try:
                asset = balance.get('asset', '').upper()
                free = float(balance.get('free', 0))
                locked = float(balance.get('locked', 0))
                total = free + locked

                await transaction_db.execute("""
                    INSERT INTO exchange_account_balances (
                        exchange_account_id, asset, free_balance, locked_balance,
                        total_balance, account_type, last_updated
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                """, account_id, asset, free, locked, total, 'spot', datetime.now())

                spot_count += 1
            except Exception as e:
                print(f"      ❌ Erro ao inserir {asset}: {e}")

        print(f"   ✅ {spot_count} saldos SPOT inseridos")

        # 7. INSERIR SALDOS FUTURES
        print("\n7️⃣ Inserindo saldos FUTURES...")
        futures_count = 0
        for asset_data in futures_with_balance:
            try:
                asset = asset_data.get('asset', '').upper()
                wallet_balance = float(asset_data.get('walletBalance', 0))
                unrealized_profit = float(asset_data.get('unrealizedProfit', 0))
                available_balance = float(asset_data.get('availableBalance', 0))

                await transaction_db.execute("""
                    INSERT INTO exchange_account_balances (
                        exchange_account_id, asset, free_balance, locked_balance,
                        total_balance, account_type, last_updated
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                """, account_id, asset, available_balance,
                wallet_balance - available_balance, wallet_balance, 'futures', datetime.now())

                futures_count += 1
            except Exception as e:
                print(f"      ❌ Erro ao inserir {asset}: {e}")

        print(f"   ✅ {futures_count} saldos FUTURES inseridos")

        # 8. VERIFICAR RESULTADO FINAL
        print("\n8️⃣ Verificando dados inseridos...")
        saved = await transaction_db.fetch("""
            SELECT asset, total_balance, account_type
            FROM exchange_account_balances
            WHERE exchange_account_id = $1
            ORDER BY total_balance DESC
            LIMIT 10
        """, account_id)

        if saved:
            print(f"   ✅ {len(saved)} registros (mostrando top 10):")
            for row in saved:
                print(f"      - {row['asset']}: {row['total_balance']} ({row['account_type']})")
        else:
            print("   ❌ Nenhum registro encontrado!")

        # 9. TOTAL GERAL
        total_result = await transaction_db.fetchrow("""
            SELECT COUNT(*) as total,
                   COUNT(CASE WHEN account_type = 'spot' THEN 1 END) as spot_count,
                   COUNT(CASE WHEN account_type = 'futures' THEN 1 END) as futures_count
            FROM exchange_account_balances
            WHERE exchange_account_id = $1
        """, account_id)

        print("\n" + "="*80)
        print("✅ SINCRONIZAÇÃO CONCLUÍDA!")
        print(f"   Total: {total_result['total']} registros")
        print(f"   SPOT: {total_result['spot_count']} ativos")
        print(f"   FUTURES: {total_result['futures_count']} ativos")
        print("="*80 + "\n")

    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if transaction_db._pool:
            await transaction_db._pool.close()

if __name__ == "__main__":
    asyncio.run(sync_production())

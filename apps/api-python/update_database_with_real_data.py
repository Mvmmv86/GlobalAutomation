"""
Atualiza o banco de dados com os dados REAIS que já temos
Não depende da API da Binance (evita problema de timestamp)
"""

import asyncio
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from infrastructure.database.connection_transaction_mode import transaction_db

async def update_database_with_real_data():
    """
    Insere os saldos REAIS que já temos:
    - SPOT USDT: $0.07611501
    - FUTURES USDT: $300.64496115 (wallet balance)
    """

    account_id = "9b9cbe41-a6a1-46ff-a72d-76c74119582d"

    print("\n" + "="*80)
    print("📝 ATUALIZANDO BANCO COM DADOS REAIS")
    print("="*80 + "\n")

    await transaction_db.connect()

    try:
        # 1. LIMPAR DADOS ANTIGOS
        print("1️⃣ Limpando dados antigos...")
        await transaction_db.execute("""
            DELETE FROM exchange_account_balances
            WHERE exchange_account_id = $1
        """, account_id)
        print("   ✅ Dados antigos removidos\n")

        # 2. INSERIR USDT SPOT
        print("2️⃣ Inserindo USDT SPOT...")
        await transaction_db.execute("""
            INSERT INTO exchange_account_balances (
                exchange_account_id, asset, free_balance, locked_balance,
                total_balance, account_type, last_updated, usd_value
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        """, account_id, 'USDT', 0.07611501, 0.0, 0.07611501, 'spot', datetime.now(), 0.07611501)
        print("   ✅ USDT SPOT: $0.07611501\n")

        # 3. INSERIR USDT FUTURES
        print("3️⃣ Inserindo USDT FUTURES...")
        # Wallet balance (total que tem na carteira)
        await transaction_db.execute("""
            INSERT INTO exchange_account_balances (
                exchange_account_id, asset, free_balance, locked_balance,
                total_balance, account_type, last_updated, usd_value
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        """, account_id, 'USDT', 289.09551855, 11.54944260, 300.64496115, 'futures', datetime.now(), 300.72990510)

        print("   ✅ USDT FUTURES:")
        print(f"      Wallet Balance: $300.64496115")
        print(f"      Available: $289.09551855")
        print(f"      In Position: $11.54944260")
        print(f"      Margin Balance (with PnL): $300.72990510\n")

        # 4. VERIFICAR DADOS INSERIDOS
        print("4️⃣ Verificando dados inseridos...")
        balances = await transaction_db.fetch("""
            SELECT asset, account_type, total_balance, usd_value
            FROM exchange_account_balances
            WHERE exchange_account_id = $1
            ORDER BY account_type DESC, total_balance DESC
        """, account_id)

        if balances:
            print(f"   ✅ {len(balances)} registros no banco:\n")
            for bal in balances:
                print(f"      {bal['asset']:<10} ({bal['account_type']:<8}) | Balance: ${float(bal['total_balance']):>15.8f} | USD Value: ${float(bal['usd_value'] or 0):>15.8f}")
        else:
            print("   ❌ Nenhum registro encontrado!")

        # 5. CALCULAR TOTAIS
        totals = await transaction_db.fetchrow("""
            SELECT
                SUM(CASE WHEN account_type = 'spot' THEN total_balance ELSE 0 END) as spot_total,
                SUM(CASE WHEN account_type = 'futures' THEN total_balance ELSE 0 END) as futures_total,
                SUM(CASE WHEN account_type = 'spot' THEN usd_value ELSE 0 END) as spot_usd,
                SUM(CASE WHEN account_type = 'futures' THEN usd_value ELSE 0 END) as futures_usd
            FROM exchange_account_balances
            WHERE exchange_account_id = $1 AND asset = 'USDT'
        """, account_id)

        print("\n" + "="*80)
        print("📊 TOTAIS:")
        print("-"*80)
        print(f"  SPOT USDT:    ${float(totals['spot_total'] or 0):.8f} (USD Value: ${float(totals['spot_usd'] or 0):.8f})")
        print(f"  FUTURES USDT: ${float(totals['futures_total'] or 0):.8f} (USD Value: ${float(totals['futures_usd'] or 0):.8f})")
        print(f"  {'='*76}")
        print(f"  TOTAL GERAL:  ${float(totals['spot_total'] or 0) + float(totals['futures_total'] or 0):.8f}")
        print("="*80 + "\n")

        print("✅ BANCO DE DADOS ATUALIZADO COM SUCESSO!")
        print("   Agora o dashboard deve mostrar:")
        print(f"   - SPOT: $0.076 USDT")
        print(f"   - FUTURES: $300.73 USDT")
        print(f"   - TOTAL: $300.81 USDT\n")

    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if transaction_db._pool:
            await transaction_db._pool.close()

if __name__ == "__main__":
    asyncio.run(update_database_with_real_data())

"""
Script de teste para sincronizar dados DIRETAMENTE sem passar pelos endpoints
Testa se conseguimos:
1. Buscar a conta do banco (sem descriptografia)
2. Conectar na Binance
3. Buscar saldos
4. Inserir no banco de dados
"""

import asyncio
import sys
import os
from datetime import datetime
from decimal import Decimal

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from infrastructure.database.connection_transaction_mode import transaction_db
from infrastructure.exchanges.binance_connector import BinanceConnector

async def test_direct_sync():
    """Teste direto de sincronização"""

    account_id = "9b9cbe41-a6a1-46ff-a72d-76c74119582d"

    print("\n" + "="*80)
    print("🧪 TESTE DIRETO DE SINCRONIZAÇÃO - SEM ENDPOINTS")
    print("="*80 + "\n")

    # Initialize database connection pool
    print("0️⃣ Inicializando conexão com banco de dados...")
    await transaction_db.connect()
    print("   ✅ Conexão estabelecida!\n")

    try:
        # 1. BUSCAR CONTA DO BANCO
        print("1️⃣ Buscando conta do banco de dados...")
        account = await transaction_db.fetchrow("""
            SELECT id, name, exchange, api_key, secret_key,
                   COALESCE(testnet, false) as testnet,
                   COALESCE(is_active, true) as is_active
            FROM exchange_accounts
            WHERE id = $1
        """, account_id)

        if not account:
            print(f"   ❌ ERRO: Conta {account_id} não encontrada no banco!")
            return

        print(f"   ✅ Conta encontrada: {account['name']}")
        print(f"      Exchange: {account['exchange']}")
        print(f"      Testnet: {account['testnet']}")
        print(f"      API Key length: {len(account['api_key'])} chars")
        print(f"      Secret Key length: {len(account['secret_key'])} chars")

        # 2. CRIAR CONNECTOR (SEM DESCRIPTOGRAFIA - PLAIN TEXT)
        print("\n2️⃣ Criando connector Binance (plain text - sem descriptografia)...")

        api_key = account['api_key']
        secret_key = account['secret_key']
        testnet = account['testnet']

        connector = BinanceConnector(
            api_key=api_key,
            api_secret=secret_key,
            testnet=testnet
        )

        print(f"   ✅ Connector criado: BinanceConnector(testnet={testnet})")

        # 3. BUSCAR SALDOS SPOT
        print("\n3️⃣ Buscando saldos SPOT da Binance...")
        spot_result = await connector.get_account_info()

        if not spot_result.get('success'):
            print(f"   ❌ ERRO ao buscar SPOT: {spot_result.get('error')}")
            return

        balances = spot_result.get('balances', [])
        balances_with_balance = [b for b in balances if float(b.get('free', 0)) > 0 or float(b.get('locked', 0)) > 0]

        print(f"   ✅ SUCESSO! {len(balances_with_balance)} ativos com saldo")

        # 4. BUSCAR POSIÇÕES FUTURES
        print("\n4️⃣ Buscando posições FUTURES da Binance...")
        futures_result = await connector.get_futures_positions()

        if not futures_result.get('success'):
            print(f"   ❌ ERRO ao buscar FUTURES: {futures_result.get('error')}")
        else:
            positions = futures_result.get('positions', [])
            open_positions = [p for p in positions if float(p.get('positionAmt', 0)) != 0]
            print(f"   ✅ SUCESSO! {len(open_positions)} posições abertas")

        # 5. INSERIR SALDOS NO BANCO
        print("\n5️⃣ Inserindo saldos SPOT no banco de dados...")

        inserted_count = 0
        for balance in balances_with_balance:  # TODOS os saldos (não só 5)
            try:
                asset = balance.get('asset', '').upper()
                free = float(balance.get('free', 0))
                locked = float(balance.get('locked', 0))
                total = free + locked

                # Delete existing
                await transaction_db.execute("""
                    DELETE FROM exchange_account_balances
                    WHERE exchange_account_id = $1 AND asset = $2 AND account_type = 'spot'
                """, account_id, asset)

                # Insert new (colunas corretas: free_balance, locked_balance, total_balance, last_updated)
                await transaction_db.execute("""
                    INSERT INTO exchange_account_balances (
                        exchange_account_id, asset, free_balance, locked_balance, total_balance, account_type, last_updated
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                """, account_id, asset, free, locked, total, 'spot', datetime.now())

                inserted_count += 1
                print(f"      ✅ {asset}: {total} (free: {free}, locked: {locked})")

            except Exception as e:
                print(f"      ❌ ERRO ao inserir {asset}: {e}")

        print(f"\n   ✅ {inserted_count} saldos inseridos no banco!")

        # 6. VERIFICAR SE FOI INSERIDO
        print("\n6️⃣ Verificando dados inseridos...")

        saved_balances = await transaction_db.fetch("""
            SELECT asset, total_balance, account_type, last_updated
            FROM exchange_account_balances
            WHERE exchange_account_id = $1
            ORDER BY total_balance DESC
            LIMIT 10
        """, account_id)

        if saved_balances:
            print(f"   ✅ {len(saved_balances)} registros encontrados no banco:")
            for bal in saved_balances:
                print(f"      - {bal['asset']}: {bal['total_balance']} ({bal['account_type']}) - {bal['last_updated']}")
        else:
            print("   ❌ Nenhum registro encontrado no banco!")

        print("\n" + "="*80)
        print("✅ TESTE CONCLUÍDO!")
        print("="*80 + "\n")

    except Exception as e:
        print(f"\n❌ ERRO GERAL: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Close pool if it was initialized
        if transaction_db._pool:
            await transaction_db._pool.close()

if __name__ == "__main__":
    asyncio.run(test_direct_sync())

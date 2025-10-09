#!/usr/bin/env python3
"""
Script para aplicar índices de performance no banco de dados
"""
import asyncio
import sys
from infrastructure.database.connection_transaction_mode import transaction_db

# Lista de índices a criar
INDEXES = [
    # 1. Orders - Busca por conta + data
    """
    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_orders_account_created
      ON orders(exchange_account_id, created_at DESC)
      WHERE is_active = true
    """,

    # 2. Orders - Busca por símbolo + status
    """
    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_orders_symbol_status
      ON orders(symbol, status)
      WHERE status IN ('filled', 'pending', 'new')
    """,

    # 3. Orders - Índice composto para histórico
    """
    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_orders_created_status_account
      ON orders(created_at DESC, status, exchange_account_id)
    """,

    # 4. Trading Orders - Índice para stats
    """
    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_trading_orders_stats
      ON trading_orders(status, created_at, filled_quantity, average_price)
      WHERE created_at >= NOW() - INTERVAL '7 days'
    """,

    # 5. Positions - Busca por conta + símbolo
    """
    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_positions_account_symbol
      ON positions(exchange_account_id, symbol)
      WHERE status IN ('open', 'active')
    """,

    # 6. Positions - Busca de posições abertas
    """
    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_positions_open
      ON positions(status, created_at DESC)
      WHERE status IN ('open', 'active')
    """,

    # 7. Positions - P&L queries
    """
    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_positions_pnl
      ON positions(exchange_account_id, status, unrealized_pnl, realized_pnl)
      WHERE status IN ('open', 'active', 'closed')
    """,

    # 8. Exchange Accounts - Contas ativas
    """
    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_exchange_accounts_active
      ON exchange_accounts(testnet, is_active, created_at ASC)
      WHERE is_active = true
    """,

    # 9. Users - Login
    """
    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_email_active
      ON users(email, is_active)
      WHERE is_active = true
    """,

    # 10. Orders - Ordens FILLED recentes
    """
    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_orders_filled_recent
      ON orders(created_at DESC, exchange_account_id, symbol)
      WHERE status = 'filled' AND created_at >= NOW() - INTERVAL '30 days'
    """,
]

async def apply_indexes():
    """Aplicar todos os índices"""
    try:
        print("🔗 Conectando ao banco de dados...")
        await transaction_db.connect()
        print("✅ Conectado!\n")

        print(f"📊 Aplicando {len(INDEXES)} índices de performance...\n")

        success_count = 0
        skip_count = 0
        error_count = 0

        for i, index_sql in enumerate(INDEXES, 1):
            # Extrair nome do índice do SQL
            index_name = "unknown"
            if "idx_" in index_sql:
                start = index_sql.index("idx_")
                end = index_sql.index("\n", start) if "\n" in index_sql[start:] else len(index_sql)
                index_name = index_sql[start:end].split()[0]

            try:
                print(f"[{i}/{len(INDEXES)}] Criando {index_name}...", end=" ")

                # CREATE INDEX CONCURRENTLY não pode ser executado dentro de transação
                # Então vamos executar diretamente
                async with transaction_db.pool.acquire() as conn:
                    result = await conn.execute(index_sql)

                print("✅ Criado!")
                success_count += 1

            except Exception as e:
                error_msg = str(e)
                if "already exists" in error_msg.lower():
                    print("⏭️  Já existe")
                    skip_count += 1
                else:
                    print(f"❌ Erro: {error_msg[:100]}")
                    error_count += 1

        print(f"\n📊 Resumo:")
        print(f"   ✅ Criados: {success_count}")
        print(f"   ⏭️  Já existiam: {skip_count}")
        print(f"   ❌ Erros: {error_count}")
        print(f"   📈 Total: {len(INDEXES)}")

        # Atualizar estatísticas das tabelas
        print(f"\n🔄 Atualizando estatísticas das tabelas...")
        tables = ['orders', 'positions', 'trading_orders', 'exchange_accounts', 'users']
        for table in tables:
            try:
                await transaction_db.execute(f"ANALYZE {table}")
                print(f"   ✅ {table}")
            except Exception as e:
                print(f"   ⚠️  {table}: {e}")

        print(f"\n🎉 Índices aplicados com sucesso!")
        return True

    except Exception as e:
        print(f"\n❌ Erro ao aplicar índices: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        await transaction_db.disconnect()

if __name__ == "__main__":
    result = asyncio.run(apply_indexes())
    sys.exit(0 if result else 1)

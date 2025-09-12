#!/usr/bin/env python3
"""
Script para executar SQL no Supabase usando asyncpg
Compatível com pgBouncer transaction mode
"""

import asyncio
import asyncpg
import ssl
import os
from dotenv import load_dotenv

load_dotenv()


async def execute_sql_file():
    """Executa o arquivo SQL de criação de tabelas"""

    # Pegar DATABASE_URL do .env
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URL não encontrada no .env")
        return False

    # Converter para formato asyncpg
    database_url = database_url.replace("postgresql+asyncpg://", "postgresql://")

    # SSL context para Supabase
    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE

    try:
        print("🔗 Conectando ao Supabase...")

        # Conectar usando asyncpg diretamente
        conn = await asyncpg.connect(
            database_url,
            ssl=ssl_ctx,
            statement_cache_size=0,  # Sem cache para pgBouncer
        )

        print("✅ Conectado!")

        # Ler arquivo SQL
        with open("infrastructure/database/create_orders_tables.sql", "r") as f:
            sql_content = f.read()

        # Executar SQL
        print("📝 Criando tabelas...")
        await conn.execute(sql_content)

        # Verificar tabelas criadas
        tables = await conn.fetch(
            """
            SELECT tablename 
            FROM pg_tables 
            WHERE schemaname = 'public' 
            AND tablename IN (
                'exchange_accounts', 
                'webhook_deliveries', 
                'orders', 
                'trade_executions', 
                'positions'
            )
            ORDER BY tablename
        """
        )

        print("\n✅ Tabelas criadas com sucesso:")
        for table in tables:
            print(f"   • {table['tablename']}")

        await conn.close()
        return True

    except Exception as e:
        print(f"❌ Erro: {e}")
        return False


if __name__ == "__main__":
    print("🚀 Criando tabelas de ordens no Supabase...")
    print("=" * 60)

    success = asyncio.run(execute_sql_file())

    if success:
        print("\n🎉 SUCESSO! Tabelas criadas no banco de dados!")
        print("Próximo passo: Implementar Binance connector")
    else:
        print("\n⚠️ Falha ao criar tabelas")

#!/usr/bin/env python3
"""
Verificar estrutura existente no banco
"""

import asyncio
import asyncpg
import ssl
import os
from dotenv import load_dotenv

load_dotenv()


async def check_existing_tables():
    """Verifica tabelas existentes"""

    database_url = os.getenv("DATABASE_URL").replace(
        "postgresql+asyncpg://", "postgresql://"
    )

    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE

    try:
        conn = await asyncpg.connect(database_url, ssl=ssl_ctx, statement_cache_size=0)

        # Verificar tabelas existentes
        tables = await conn.fetch(
            """
            SELECT tablename 
            FROM pg_tables 
            WHERE schemaname = 'public'
            ORDER BY tablename
        """
        )

        print("📊 TABELAS EXISTENTES:")
        for table in tables:
            print(f"   • {table['tablename']}")

        # Se existir tabela orders, verificar estrutura
        if any(t["tablename"] == "orders" for t in tables):
            print("\n🔍 Estrutura da tabela 'orders':")
            columns = await conn.fetch(
                """
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns 
                WHERE table_name = 'orders'
                ORDER BY ordinal_position
            """
            )

            for col in columns:
                print(
                    f"   • {col['column_name']}: {col['data_type']} ({'NULL' if col['is_nullable'] == 'YES' else 'NOT NULL'})"
                )

        await conn.close()

    except Exception as e:
        print(f"❌ Erro: {e}")


if __name__ == "__main__":
    asyncio.run(check_existing_tables())

#!/usr/bin/env python3
"""Script simplificado para criar webhook de teste sem prepared statements"""

import asyncio
import uuid
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()


async def create_test_webhook():
    """Cria webhook de teste usando conexão direta"""

    # Pegar DATABASE_URL do ambiente
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URL não configurada!")
        return

    # Converter para formato asyncpg se necessário
    if database_url.startswith("postgresql+asyncpg://"):
        database_url = database_url.replace("postgresql+asyncpg://", "postgres://", 1)
    elif database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgres://", 1)

    try:
        # Conectar diretamente ao banco sem prepared statements
        conn = await asyncpg.connect(
            database_url,
            statement_cache_size=0,  # Desabilitar cache de statements
            command_timeout=60,
        )

        try:
            # Buscar usuário demo
            user_row = await conn.fetchrow(
                "SELECT id FROM users WHERE email = 'demo@tradingview.com' LIMIT 1"
            )

            if not user_row:
                print("❌ Usuário demo não encontrado! Faça login primeiro.")
                return

            user_id = user_row["id"]
            webhook_id = str(uuid.uuid4())

            # Inserir webhook diretamente
            await conn.execute(
                """
                INSERT INTO webhooks (
                    id, name, url_path, secret, status, user_id, is_public,
                    rate_limit_per_minute, rate_limit_per_hour, max_retries,
                    retry_delay_seconds, total_deliveries, successful_deliveries,
                    failed_deliveries, auto_pause_on_errors, error_threshold,
                    consecutive_errors, created_at, updated_at
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7,
                    $8, $9, $10, $11, $12, $13,
                    $14, $15, $16, $17, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                )
            """,
                webhook_id,
                "TradingView Test Strategy",
                "webhook_demo_123",
                "minha_secret_key_super_secreta_123",
                "active",
                user_id,
                False,
                60,
                1000,
                3,
                60,
                0,
                0,
                0,
                True,
                10,
                0,
            )

            print("✅ Webhook de teste criado com sucesso!")
            print(f"📝 ID: {webhook_id}")
            print(f"🔗 URL: http://localhost:8000/api/v1/webhooks/tv/webhook_demo_123")
            print(f"🔑 Secret: minha_secret_key_super_secreta_123")
            print(f"👤 Usuario: {user_id}")

            # Verificar se foi inserido
            check_row = await conn.fetchrow(
                "SELECT name FROM webhooks WHERE id = $1", webhook_id
            )

            if check_row:
                print(f"🎯 Webhook encontrado no banco: {check_row['name']}")
            else:
                print("❌ Erro: Webhook não encontrado após inserção")

        finally:
            await conn.close()

    except Exception as e:
        print(f"❌ Erro ao criar webhook: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    print("🚀 Criando webhook de teste (versão simplificada)...")
    asyncio.run(create_test_webhook())

#!/usr/bin/env python3
"""Script para criar webhook de teste no banco de dados"""

import asyncio
import uuid
from sqlalchemy import text
from infrastructure.database.connection import database_manager
from infrastructure.database.models.webhook import Webhook, WebhookStatus


async def create_test_webhook():
    """Cria webhook de teste para demonstração"""

    # Conectar ao banco
    await database_manager.connect()

    try:
        async with database_manager.get_session() as session:
            # Buscar usuário demo
            result = await session.execute(
                text(
                    "SELECT id FROM users WHERE email = 'demo@tradingview.com' LIMIT 1"
                )
            )
            user_row = result.fetchone()

            if not user_row:
                print("❌ Usuário demo não encontrado! Faça login primeiro.")
                return

            user_id = user_row[0]
            webhook_id = str(uuid.uuid4())

            # Inserir webhook usando SQLAlchemy
            insert_query = text(
                """
                INSERT INTO webhooks (
                    id, name, url_path, secret, status, user_id, is_public,
                    rate_limit_per_minute, rate_limit_per_hour, max_retries,
                    retry_delay_seconds, total_deliveries, successful_deliveries,
                    failed_deliveries, auto_pause_on_errors, error_threshold,
                    consecutive_errors, created_at, updated_at
                ) VALUES (
                    :id, :name, :url_path, :secret, :status, :user_id, :is_public,
                    :rate_limit_per_minute, :rate_limit_per_hour, :max_retries,
                    :retry_delay_seconds, :total_deliveries, :successful_deliveries,
                    :failed_deliveries, :auto_pause_on_errors, :error_threshold,
                    :consecutive_errors, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                )
            """
            )

            webhook_data = {
                "id": webhook_id,
                "name": "TradingView Test Strategy",
                "url_path": "webhook_demo_123",
                "secret": "minha_secret_key_super_secreta_123",
                "status": WebhookStatus.ACTIVE.value,
                "user_id": user_id,
                "is_public": False,
                "rate_limit_per_minute": 60,
                "rate_limit_per_hour": 1000,
                "max_retries": 3,
                "retry_delay_seconds": 60,
                "total_deliveries": 0,
                "successful_deliveries": 0,
                "failed_deliveries": 0,
                "auto_pause_on_errors": True,
                "error_threshold": 10,
                "consecutive_errors": 0,
            }

            await session.execute(insert_query, webhook_data)
            await session.commit()

            print("✅ Webhook de teste criado com sucesso!")
            print(f"📝 ID: {webhook_id}")
            print(
                f"🔗 URL: http://localhost:8000/api/v1/webhooks/tv/{webhook_data['url_path']}"
            )
            print(f"🔑 Secret: {webhook_data['secret']}")
            print(f"👤 Usuario: {user_id}")

            # Verificar se foi inserido
            check_result = await session.execute(
                text("SELECT name FROM webhooks WHERE id = :webhook_id"),
                {"webhook_id": webhook_id},
            )
            check_row = check_result.fetchone()

            if check_row:
                print(f"🎯 Webhook encontrado no banco: {check_row[0]}")
            else:
                print("❌ Erro: Webhook não encontrado após inserção")

    except Exception as e:
        print(f"❌ Erro ao criar webhook: {e}")
        import traceback

        traceback.print_exc()
    finally:
        await database_manager.disconnect()


if __name__ == "__main__":
    print("🚀 Criando webhook de teste...")
    asyncio.run(create_test_webhook())

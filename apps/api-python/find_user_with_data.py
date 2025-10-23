#!/usr/bin/env python3
"""
Script para encontrar qual usuário tem bots e webhooks
"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

# Credenciais do Supabase
DATABASE_URL = "postgresql+asyncpg://postgres.zmdqmrugotfftxvrwdsd:Wzg0kBvtrSbclQ9V@aws-1-us-east-2.pooler.supabase.com:5432/postgres"

async def find_users_with_data():
    """Encontrar usuários com dados"""

    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        try:
            print("\n🔍 Buscando usuários com bots e webhooks...\n")

            # Buscar usuários com contagens
            result = await session.execute(text("""
                SELECT
                    u.id,
                    u.email,
                    u.name,
                    u.is_admin,
                    (SELECT COUNT(*) FROM webhooks w WHERE w.user_id = u.id) as webhooks_count,
                    (SELECT COUNT(*) FROM bot_subscriptions bs WHERE bs.user_id = u.id) as bots_count,
                    (SELECT COUNT(*) FROM exchange_accounts ea WHERE ea.user_id = u.id) as accounts_count
                FROM users u
                ORDER BY created_at DESC
            """))

            users = result.fetchall()

            if not users:
                print("❌ Nenhum usuário encontrado!")
                return

            print("📊 USUÁRIOS ENCONTRADOS:\n")
            print(f"{'#':<4} {'Email':<35} {'Nome':<25} {'Admin':<8} {'Webhooks':<10} {'Bots':<10} {'Accounts':<10}")
            print("=" * 120)

            for idx, user in enumerate(users, 1):
                admin_badge = "👑 SIM" if user.is_admin else "   NÃO"
                highlight = "🎯" if (user.webhooks_count > 0 or user.bots_count > 0 or user.accounts_count > 0) else "  "

                print(f"{highlight} {idx:<2} {user.email:<35} {user.name:<25} {admin_badge:<8} {user.webhooks_count:<10} {user.bots_count:<10} {user.accounts_count:<10}")

            print("\n" + "=" * 120)
            print("\n🎯 = Usuário com dados (webhooks, bots ou contas)")
            print("👑 = Usuário admin\n")

            # Contar totais
            total_with_data = sum(1 for u in users if (u.webhooks_count > 0 or u.bots_count > 0 or u.accounts_count > 0))

            if total_with_data > 0:
                print(f"✅ Encontrados {total_with_data} usuário(s) com dados!")
            else:
                print("⚠️  Nenhum usuário tem webhooks, bots ou exchange accounts cadastrados!")
                print("💡 Os dados podem estar no banco de dados LOCAL (SQLite)!")

        except Exception as e:
            print(f"\n❌ Erro: {e}")
            raise
        finally:
            await engine.dispose()

if __name__ == "__main__":
    asyncio.run(find_users_with_data())

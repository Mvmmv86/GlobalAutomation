#!/usr/bin/env python3
"""
Script para promover usuário específico para admin
Uso: python3 promote_user_to_admin.py <email_do_usuario>
"""
import asyncio
import sys
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

# Credenciais do Supabase
DATABASE_URL = "postgresql+asyncpg://postgres.zmdqmrugotfftxvrwdsd:Wzg0kBvtrSbclQ9V@aws-1-us-east-2.pooler.supabase.com:5432/postgres"

async def promote_user(email: str):
    """Promover usuário para admin"""

    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        try:
            print(f"\n🔍 Buscando usuário: {email}")

            # Buscar usuário
            result = await session.execute(text("""
                SELECT id, email, name, is_admin, is_active
                FROM users
                WHERE email = :email
            """), {"email": email})

            user = result.fetchone()

            if not user:
                print(f"❌ Usuário {email} não encontrado!")
                return

            print(f"✅ Usuário encontrado: {user.name}")
            print(f"📧 Email: {user.email}")
            print(f"👑 Admin atual: {user.is_admin}")

            # Atualizar usuário para admin
            print(f"\n🔄 Promovendo para admin...")

            await session.execute(text("""
                UPDATE users
                SET is_admin = true, is_active = true, is_verified = true
                WHERE id = :user_id
            """), {"user_id": user.id})

            # Criar entrada na tabela admins
            await session.execute(text("""
                INSERT INTO admins (user_id, role, permissions, is_active)
                VALUES (:user_id, 'super_admin', :permissions, true)
                ON CONFLICT (user_id) DO UPDATE
                SET role = 'super_admin',
                    permissions = EXCLUDED.permissions,
                    is_active = true
            """), {
                "user_id": user.id,
                "permissions": '{"bots": true, "users": true, "webhooks": true, "reports": true, "admins": true}'
            })

            await session.commit()

            print(f"\n✅ Usuário promovido para SUPER ADMIN!")
            print(f"📧 Email: {user.email}")
            print(f"👑 Role: super_admin")
            print(f"🔐 Permissões: TODAS (bots, users, webhooks, reports, admins)")

            # Verificar dados do usuário
            print(f"\n🤖 Verificando dados preservados...")

            # Contar webhooks
            webhooks_result = await session.execute(text("""
                SELECT COUNT(*) FROM webhooks WHERE user_id = :user_id
            """), {"user_id": user.id})
            webhooks_count = webhooks_result.scalar()

            # Contar subscriptions de bots
            bots_result = await session.execute(text("""
                SELECT COUNT(*) FROM bot_subscriptions WHERE user_id = :user_id
            """), {"user_id": user.id})
            bots_count = bots_result.scalar()

            # Contar exchange accounts
            accounts_result = await session.execute(text("""
                SELECT COUNT(*) FROM exchange_accounts WHERE user_id = :user_id
            """), {"user_id": user.id})
            accounts_count = accounts_result.scalar()

            print(f"📡 Webhooks: {webhooks_count}")
            print(f"🤖 Bot Subscriptions: {bots_count}")
            print(f"💱 Exchange Accounts: {accounts_count}")
            print(f"\n✅ Todos os dados foram preservados!")
            print(f"\n⚠️  A senha atual do usuário foi mantida!")

        except Exception as e:
            print(f"\n❌ Erro: {e}")
            await session.rollback()
            raise
        finally:
            await engine.dispose()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("❌ Uso: python3 promote_user_to_admin.py <email>")
        print("\n📋 Exemplos de emails disponíveis:")
        print("  - test@test.com")
        print("  - marcusvmoraes86@gmail.com")
        print("  - superforte@test.com")
        sys.exit(1)

    email = sys.argv[1]
    asyncio.run(promote_user(email))

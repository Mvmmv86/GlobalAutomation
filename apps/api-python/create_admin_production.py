#!/usr/bin/env python3
"""
Script para criar/promover usuário admin em produção
Conecta direto no Supabase e preserva dados existentes
"""
import asyncio
import bcrypt
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
import os

# Credenciais do Supabase
DATABASE_URL = "postgresql+asyncpg://postgres.zmdqmrugotfftxvrwdsd:Wzg0kBvtrSbclQ9V@aws-1-us-east-2.pooler.supabase.com:5432/postgres"

async def create_admin_user():
    """Criar ou promover usuário para admin"""

    # Criar engine
    engine = create_async_engine(DATABASE_URL, echo=True)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        try:
            print("\n🔍 Verificando usuários existentes...")

            # Listar todos os usuários
            result = await session.execute(text("""
                SELECT id, email, name, is_admin, is_active
                FROM users
                ORDER BY created_at DESC
                LIMIT 10
            """))
            users = result.fetchall()

            print("\n📋 Usuários existentes:")
            for idx, user in enumerate(users, 1):
                admin_badge = "👑 ADMIN" if user.is_admin else ""
                print(f"{idx}. {user.email} - {user.name} {admin_badge}")

            if not users:
                print("\n❌ Nenhum usuário encontrado!")
                print("📝 Criando novo usuário admin...")

                # Gerar hash da senha
                password = "admin123"
                salt = bcrypt.gensalt()
                password_hash = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

                # Criar novo usuário
                await session.execute(text("""
                    INSERT INTO users (email, name, password_hash, is_active, is_verified, is_admin, totp_enabled)
                    VALUES (:email, :name, :password_hash, true, true, true, false)
                """), {
                    "email": "admin@globalautomation.com",
                    "name": "Global Automation Admin",
                    "password_hash": password_hash
                })

                await session.commit()
                print("✅ Usuário admin criado com sucesso!")
                print(f"📧 Email: admin@globalautomation.com")
                print(f"🔑 Password: {password}")

            else:
                # Perguntar qual usuário promover
                print("\n❓ Qual usuário você quer promover para admin?")
                print("Digite o número do usuário (ou 0 para criar novo):")
                choice = input("Escolha: ").strip()

                if choice == "0":
                    # Criar novo admin
                    email = input("📧 Email do novo admin: ").strip()
                    name = input("👤 Nome do admin: ").strip()
                    password = input("🔑 Senha (deixe vazio para 'admin123'): ").strip() or "admin123"

                    # Gerar hash
                    salt = bcrypt.gensalt()
                    password_hash = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

                    await session.execute(text("""
                        INSERT INTO users (email, name, password_hash, is_active, is_verified, is_admin, totp_enabled)
                        VALUES (:email, :name, :password_hash, true, true, true, false)
                    """), {
                        "email": email,
                        "name": name,
                        "password_hash": password_hash
                    })

                    await session.commit()
                    print(f"\n✅ Novo admin criado!")
                    print(f"📧 Email: {email}")
                    print(f"🔑 Password: {password}")

                else:
                    # Promover usuário existente
                    try:
                        idx = int(choice) - 1
                        selected_user = users[idx]

                        print(f"\n🔄 Promovendo {selected_user.email} para admin...")

                        # Atualizar usuário para admin
                        await session.execute(text("""
                            UPDATE users
                            SET is_admin = true, is_active = true, is_verified = true
                            WHERE id = :user_id
                        """), {"user_id": selected_user.id})

                        # Criar entrada na tabela admins
                        await session.execute(text("""
                            INSERT INTO admins (user_id, role, permissions, is_active)
                            VALUES (:user_id, 'super_admin', :permissions, true)
                            ON CONFLICT (user_id) DO UPDATE
                            SET role = 'super_admin',
                                permissions = EXCLUDED.permissions,
                                is_active = true
                        """), {
                            "user_id": selected_user.id,
                            "permissions": '{"bots": true, "users": true, "webhooks": true, "reports": true, "admins": true}'
                        })

                        await session.commit()

                        print(f"\n✅ Usuário promovido para admin!")
                        print(f"📧 Email: {selected_user.email}")
                        print(f"👑 Role: super_admin")
                        print(f"🔐 Permissões: TODAS")
                        print(f"\n⚠️  A senha atual foi mantida!")

                        # Verificar bots e webhooks do usuário
                        print(f"\n🤖 Verificando dados do usuário...")

                        # Contar webhooks
                        webhooks_result = await session.execute(text("""
                            SELECT COUNT(*) FROM webhooks WHERE user_id = :user_id
                        """), {"user_id": selected_user.id})
                        webhooks_count = webhooks_result.scalar()

                        # Contar subscriptions de bots
                        bots_result = await session.execute(text("""
                            SELECT COUNT(*) FROM bot_subscriptions WHERE user_id = :user_id
                        """), {"user_id": selected_user.id})
                        bots_count = bots_result.scalar()

                        print(f"📡 Webhooks: {webhooks_count}")
                        print(f"🤖 Bot Subscriptions: {bots_count}")
                        print(f"\n✅ Todos os dados foram preservados!")

                    except (ValueError, IndexError):
                        print("❌ Escolha inválida!")
                        return

        except Exception as e:
            print(f"\n❌ Erro: {e}")
            await session.rollback()
            raise
        finally:
            await engine.dispose()

if __name__ == "__main__":
    asyncio.run(create_admin_user())

#!/usr/bin/env python3
"""
Script para resetar senha de um usuário
Uso: python3 reset_password.py <email> <nova_senha>
"""
import asyncio
import sys
import bcrypt
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

# Credenciais do Supabase
DATABASE_URL = "postgresql+asyncpg://postgres.zmdqmrugotfftxvrwdsd:Wzg0kBvtrSbclQ9V@aws-1-us-east-2.pooler.supabase.com:5432/postgres"

async def reset_password(email: str, new_password: str):
    """Resetar senha do usuário"""

    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        try:
            print(f"\n🔍 Buscando usuário: {email}")

            # Gerar hash da nova senha
            salt = bcrypt.gensalt()
            password_hash = bcrypt.hashpw(new_password.encode('utf-8'), salt).decode('utf-8')

            # Atualizar senha
            result = await session.execute(text("""
                UPDATE users
                SET password_hash = :password_hash
                WHERE email = :email
                RETURNING id, email, name
            """), {
                "email": email,
                "password_hash": password_hash
            })

            user = result.fetchone()

            if not user:
                print(f"❌ Usuário {email} não encontrado!")
                return

            await session.commit()

            print(f"\n✅ Senha resetada com sucesso!")
            print(f"📧 Email: {user.email}")
            print(f"👤 Nome: {user.name}")
            print(f"🔑 Nova senha: {new_password}")

        except Exception as e:
            print(f"\n❌ Erro: {e}")
            await session.rollback()
            raise
        finally:
            await engine.dispose()

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("❌ Uso: python3 reset_password.py <email> <nova_senha>")
        print("\nExemplo:")
        print("  python3 reset_password.py trader@tradingplatform.com trader123")
        sys.exit(1)

    email = sys.argv[1]
    new_password = sys.argv[2]
    asyncio.run(reset_password(email, new_password))

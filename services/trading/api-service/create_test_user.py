#!/usr/bin/env python3
"""
Criar usuário de teste para login
"""

import asyncio
import bcrypt
from infrastructure.database.connection_transaction_mode import transaction_db


async def create_test_user():
    """Criar usuário de teste"""

    email = "test@test.com"
    password = "123456"
    name = "Test User"

    # Hash da senha usando bcrypt (igual ao AuthService)
    salt = bcrypt.gensalt()
    password_hash = bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

    try:
        await transaction_db.connect()
        print("✅ Conectado ao banco")

        # Verificar se usuário já existe e deletar para recriar com hash correto
        existing_user = await transaction_db.fetchrow(
            "SELECT id FROM users WHERE email = $1", email
        )

        if existing_user:
            print(
                f"⚠️ Usuário {email} já existe, deletando para recriar com hash correto..."
            )
            await transaction_db.execute("DELETE FROM users WHERE email = $1", email)
            print("✅ Usuário anterior deletado")

        # Criar usuário
        await transaction_db.execute(
            """
            INSERT INTO users (id, email, password_hash, name, is_active, is_verified, totp_enabled, created_at, updated_at)
            VALUES (
                gen_random_uuid(),
                $1, $2, $3, true, true, false, 
                CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            )
        """,
            email,
            password_hash,
            name,
        )

        print(f"✅ Usuário criado com sucesso!")
        print(f"   📧 Email: {email}")
        print(f"   🔑 Senha: {password}")
        print(f"   👤 Nome: {name}")

        # Verificar criação
        user = await transaction_db.fetchrow(
            "SELECT id, email, name FROM users WHERE email = $1", email
        )

        if user:
            print(f"✅ Verificação: Usuário {user['email']} criado com ID {user['id']}")

        return True

    except Exception as e:
        print(f"❌ Erro: {e}")
        return False

    finally:
        await transaction_db.disconnect()


if __name__ == "__main__":
    print("👤 Criando usuário de teste...")
    success = asyncio.run(create_test_user())

    if success:
        print("\n🎉 Usuário de teste criado! Agora você pode fazer login com:")
        print("   📧 Email: test@test.com")
        print("   🔑 Senha: 123456")
    else:
        print("\n⚠️ Erro ao criar usuário de teste")

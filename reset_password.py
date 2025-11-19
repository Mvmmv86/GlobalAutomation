#!/usr/bin/env python3
"""
Script para redefinir senha de usuário
"""
import asyncio
import asyncpg
import bcrypt

async def reset_password():
    # Conectar ao banco (statement_cache_size=0 para pgbouncer)
    conn = await asyncpg.connect(
        'postgresql://postgres.zmdqmrugotfftxvrwdsd:Wzg0kBvtrSbclQ9V@aws-1-us-east-2.pooler.supabase.com:6543/postgres',
        statement_cache_size=0
    )

    # Email do usuário
    email = 'test@globalautomation.com'

    # Nova senha
    new_password = 'Test@123'

    # Gerar hash bcrypt
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(new_password.encode("utf-8"), salt)
    hashed_password = hashed.decode("utf-8")

    print(f'\n🔐 Redefinindo senha para: {email}')
    print(f'📝 Nova senha: {new_password}')
    print(f'🔒 Hash gerado: {hashed_password[:50]}...\n')

    # Atualizar senha no banco
    result = await conn.execute(
        'UPDATE users SET password_hash = $1 WHERE email = $2',
        hashed_password,
        email
    )

    if result == 'UPDATE 1':
        print('✅ Senha atualizada com sucesso!')
    else:
        print('❌ Erro ao atualizar senha. Usuário não encontrado?')

    # Verificar atualização
    user = await conn.fetchrow(
        'SELECT email, name, is_active FROM users WHERE email = $1',
        email
    )

    if user:
        print(f'\n📧 Email: {user["email"]}')
        print(f'👤 Nome: {user["name"]}')
        print(f'✓ Ativo: {user["is_active"]}')
        print(f'\n🎯 Use estas credenciais para login:')
        print(f'   Email: {email}')
        print(f'   Senha: {new_password}')

    await conn.close()

if __name__ == '__main__':
    asyncio.run(reset_password())

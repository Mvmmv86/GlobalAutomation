#!/usr/bin/env python3
"""Teste simplificado de login"""

import asyncio
import asyncpg
import bcrypt
import os
from dotenv import load_dotenv

load_dotenv()

async def test_login():
    # Conectar ao banco
    database_url = os.getenv("DATABASE_URL", "").replace("postgresql+asyncpg://", "postgresql://")
    conn = await asyncpg.connect(database_url, statement_cache_size=0)
    
    # Testar com admin
    email = "admin@tradingplatform.com"
    passwords_to_try = [
        "Admin123!@#",
        "SecureAdmin123!",
        "admin123",
        "password",
        "123456"
    ]
    
    print(f"\n🔐 Testando login para: {email}")
    print("=" * 50)
    
    # Buscar usuário
    user = await conn.fetchrow(
        "SELECT id, email, name, password_hash FROM users WHERE email = $1",
        email
    )
    
    if not user:
        print(f"❌ Usuário não encontrado: {email}")
        await conn.close()
        return
    
    print(f"✅ Usuário encontrado: {user['name']}")
    print(f"   ID: {user['id']}")
    print(f"   Hash armazenado: {user['password_hash'][:20]}...")
    
    print("\n🔑 Testando senhas:")
    for password in passwords_to_try:
        try:
            # Testar senha
            is_valid = bcrypt.checkpw(
                password.encode("utf-8"),
                user["password_hash"].encode("utf-8")
            )
            
            if is_valid:
                print(f"   ✅ SENHA CORRETA: {password}")
                break
            else:
                print(f"   ❌ Senha incorreta: {password}")
        except Exception as e:
            print(f"   ⚠️  Erro ao testar {password}: {e}")
    
    await conn.close()

if __name__ == "__main__":
    asyncio.run(test_login())
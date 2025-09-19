#!/usr/bin/env python3
"""Verificar usuários no banco de dados"""

import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

async def check_users():
    # Conectar diretamente ao banco
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        # Converter para formato asyncpg
        database_url = database_url.replace("postgresql+asyncpg://", "postgresql://")
    else:
        database_url = "postgresql://postgres.zmdqmrugotfftxvrwdsd:MFCuJT0Jn04PtCTL@aws-1-us-east-2.pooler.supabase.com:6543/postgres"
    
    conn = await asyncpg.connect(database_url)
    
    print("\n📊 USUÁRIOS CADASTRADOS NO BANCO:")
    print("=" * 60)
    
    users = await conn.fetch("SELECT email, name, is_active, is_verified FROM users ORDER BY email")
    
    if not users:
        print("❌ Nenhum usuário encontrado!")
    else:
        for user in users:
            status = "✅ Ativo" if user['is_active'] else "❌ Inativo"
            verified = "✅" if user['is_verified'] else "❌"
            print(f"📧 Email: {user['email']}")
            print(f"   Nome: {user['name']}")
            print(f"   Status: {status}")
            print(f"   Verificado: {verified}")
            print("-" * 40)
    
    await conn.close()
    print(f"\nTotal: {len(users)} usuários")

if __name__ == "__main__":
    asyncio.run(check_users())
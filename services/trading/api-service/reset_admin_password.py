#!/usr/bin/env python3
"""Reset admin password"""

import asyncio
import asyncpg
import bcrypt
import os
from dotenv import load_dotenv

load_dotenv()

async def reset_password():
    # Conectar ao banco
    database_url = os.getenv("DATABASE_URL", "").replace("postgresql+asyncpg://", "postgresql://")
    conn = await asyncpg.connect(database_url, statement_cache_size=0)
    
    email = "admin@tradingplatform.com"
    new_password = "Admin123!@#"
    
    print(f"\n🔐 Resetando senha para: {email}")
    print("=" * 50)
    
    # Gerar novo hash
    password_hash = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt())
    
    # Atualizar no banco
    result = await conn.execute(
        """
        UPDATE users 
        SET password_hash = $1, 
            failed_login_attempts = 0,
            locked_until = NULL
        WHERE email = $2
        """,
        password_hash.decode("utf-8"),
        email
    )
    
    print(f"✅ Senha atualizada com sucesso!")
    print(f"   Nova senha: {new_password}")
    print(f"   Hash: {password_hash.decode('utf-8')[:20]}...")
    
    await conn.close()

if __name__ == "__main__":
    asyncio.run(reset_password())
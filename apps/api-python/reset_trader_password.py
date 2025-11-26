"""Reset password for trader@tradingplatform.com"""
import asyncio
import os
from dotenv import load_dotenv
import asyncpg
import bcrypt

load_dotenv()

async def reset_password():
    database_url = os.getenv('DATABASE_URL').replace('postgresql+asyncpg://', 'postgresql://')
    conn = await asyncpg.connect(database_url, timeout=30, statement_cache_size=0)

    # Nova senha: Trader@2024
    new_password = "Trader@2024"
    password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    # Atualizar a senha
    result = await conn.execute(
        "UPDATE users SET password_hash = $1 WHERE email = $2",
        password_hash,
        'trader@tradingplatform.com'
    )

    print(f"Resultado: {result}")
    print()
    print("=" * 50)
    print("SENHA ATUALIZADA COM SUCESSO!")
    print("=" * 50)
    print()
    print(f"Email: trader@tradingplatform.com")
    print(f"Nova senha: {new_password}")
    print()

    await conn.close()

asyncio.run(reset_password())

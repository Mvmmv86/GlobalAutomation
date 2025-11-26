"""Check trader account"""
import asyncio
import os
from dotenv import load_dotenv
import asyncpg

load_dotenv()

async def check():
    database_url = os.getenv('DATABASE_URL').replace('postgresql+asyncpg://', 'postgresql://')
    conn = await asyncpg.connect(database_url, timeout=30, statement_cache_size=0)

    trader = await conn.fetchrow(
        "SELECT id, email, name, password_hash FROM users WHERE email = $1",
        'trader@tradingplatform.com'
    )

    if trader:
        print('=== CONTA trader@tradingplatform.com ===')
        print(f'ID: {trader["id"]}')
        print(f'Email: {trader["email"]}')
        print(f'Name: {trader["name"]}')
        ph = trader["password_hash"] if trader["password_hash"] else "NULL"
        print(f'Password Hash: {ph[:40]}...' if len(ph) > 40 else f'Password Hash: {ph}')

    await conn.close()

asyncio.run(check())

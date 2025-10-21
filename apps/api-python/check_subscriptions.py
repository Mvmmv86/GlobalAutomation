#!/usr/bin/env python3
import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

async def check():
    db_url = os.getenv('DATABASE_URL').replace('postgresql+asyncpg://', 'postgresql://')
    conn = await asyncpg.connect(db_url)

    # Get bot subscriptions for user
    subs = await conn.fetch("""
        SELECT
            bs.id,
            bs.bot_id,
            b.name as bot_name,
            bs.status,
            bs.created_at
        FROM bot_subscriptions bs
        JOIN bots b ON b.id = bs.bot_id
        WHERE bs.user_id = '550e8400-e29b-41d4-a716-446655440002'
        ORDER BY bs.created_at DESC
    """)

    print()
    print('🤖 Bot Subscriptions for user 550e8400-e29b-41d4-a716-446655440002:')
    print('=' * 80)

    if not subs:
        print('✅ Nenhuma subscription encontrada - usuário pode se inscrever!')
    else:
        for sub in subs:
            print(f'ID: {sub["id"]}')
            print(f'   Bot: {sub["bot_name"]} ({sub["bot_id"]})')
            print(f'   Status: {sub["status"]}')
            print(f'   Criado em: {sub["created_at"].strftime("%d/%m/%Y %H:%M:%S")}')
            print()

    await conn.close()

asyncio.run(check())

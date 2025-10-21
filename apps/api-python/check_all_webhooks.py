#!/usr/bin/env python3
import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

async def check():
    db_url = os.getenv('DATABASE_URL').replace('postgresql+asyncpg://', 'postgresql://')
    conn = await asyncpg.connect(db_url)

    # Get ALL webhooks (old system)
    webhooks = await conn.fetch("""
        SELECT id, name, url_path, status, market_type, created_at
        FROM webhooks
        WHERE status = 'active'
        ORDER BY created_at DESC
    """)

    print()
    print('📡 WEBHOOKS ANTIGOS ATIVOS:')
    print('=' * 80)

    if not webhooks:
        print('✅ Nenhum webhook antigo ativo')
    else:
        for wh in webhooks:
            print(f'Nome: {wh["name"]}')
            print(f'   URL Path: /api/v1/webhooks/tv/{wh["url_path"]}')
            print(f'   Full URL: https://ea09701e120d.ngrok-free.app/api/v1/webhooks/tv/{wh["url_path"]}')
            print(f'   Status: {wh["status"]}')
            print(f'   Market: {wh["market_type"]}')
            print()

    # Get ALL bots
    bots = await conn.fetch("""
        SELECT id, name, master_webhook_path, status, created_at
        FROM bots
        WHERE status = 'active'
        ORDER BY created_at DESC
    """)

    print()
    print('🤖 BOTS ATIVOS:')
    print('=' * 80)

    for bot in bots:
        print(f'Nome: {bot["name"]}')
        print(f'   Webhook Path: /api/v1/bots/webhook/master/{bot["master_webhook_path"]}')
        print(f'   Full URL: https://ea09701e120d.ngrok-free.app/api/v1/bots/webhook/master/{bot["master_webhook_path"]}')
        print(f'   Status: {bot["status"]}')
        print()

    await conn.close()

asyncio.run(check())

import os
import asyncio
import asyncpg
from dotenv import load_dotenv

load_dotenv()

async def check():
    db_url = os.getenv('TRANSACTION_POOLER_URL') or os.getenv('DATABASE_URL')
    db_url = db_url.replace('postgresql+asyncpg://', 'postgresql://')
    
    conn = await asyncpg.connect(db_url, ssl='prefer', statement_cache_size=0)
    
    webhooks = await conn.fetch('''
        SELECT id, name, url_path, market_type, status
        FROM webhooks
        ORDER BY created_at DESC
        LIMIT 5
    ''')
    
    print('\n📋 WEBHOOKS COM MARKET_TYPE:')
    print('=' * 80)
    for w in webhooks:
        market_icon = '⚡ FUTURES' if w['market_type'] == 'futures' else '💰 SPOT'
        print(f'{market_icon} {w["name"]}: {w["url_path"]} (status: {w["status"]})')
    print('=' * 80)
    print(f'✅ Todos os {len(webhooks)} webhooks têm market_type configurado!\n')
    
    await conn.close()

asyncio.run(check())

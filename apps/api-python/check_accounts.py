"""Script para verificar contas de exchange"""
import asyncio
import os
from dotenv import load_dotenv
import asyncpg

load_dotenv()

async def check_accounts():
    database_url = os.getenv('DATABASE_URL').replace('postgresql+asyncpg://', 'postgresql://')
    conn = await asyncpg.connect(database_url)

    accounts = await conn.fetch('''
        SELECT
            ea.id, ea.name, ea.exchange, ea.testnet, ea.is_active, ea.is_main,
            ea.user_id, u.email, u.name as user_name,
            LEFT(ea.api_key, 10) as api_key_preview
        FROM exchange_accounts ea
        LEFT JOIN users u ON ea.user_id = u.id
        WHERE ea.is_active = true
        ORDER BY ea.is_main DESC, ea.created_at DESC
    ''')

    print('=' * 80)
    print('CONTAS DE EXCHANGE ATIVAS')
    print('=' * 80)

    for acc in accounts:
        main_badge = ' [MAIN]' if acc['is_main'] else ''
        testnet_badge = ' (TESTNET)' if acc['testnet'] else ' (MAINNET)'
        print(f'''
Account ID: {acc['id']}
Name: {acc['name']}{main_badge}{testnet_badge}
Exchange: {acc['exchange'].upper()}
API Key: {acc['api_key_preview']}...
User ID: {acc['user_id']}
User Email: {acc['email']}
User Name: {acc['user_name']}
''')

    print('=' * 80)
    print(f'Total de contas ativas: {len(accounts)}')

    await conn.close()

asyncio.run(check_accounts())

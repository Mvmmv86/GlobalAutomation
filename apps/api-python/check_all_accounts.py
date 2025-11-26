"""Script para verificar TODAS as exchange accounts no banco"""
import asyncio
import os
from dotenv import load_dotenv
import asyncpg

load_dotenv()

async def check():
    database_url = os.getenv('DATABASE_URL').replace('postgresql+asyncpg://', 'postgresql://')
    conn = await asyncpg.connect(database_url, timeout=30, statement_cache_size=0)

    # Verificar exchange accounts do usuario test@globalautomation.com
    user_id = '0004a819-1216-40f1-9fc4-a445b0ef7663'

    print("=" * 80)
    print("EXCHANGE ACCOUNTS de test@globalautomation.com")
    print("=" * 80)

    accounts = await conn.fetch('''
        SELECT id, name, exchange, testnet, is_active, is_main, created_at
        FROM exchange_accounts
        WHERE user_id = $1
    ''', user_id)

    print(f'Total: {len(accounts)}')
    for a in accounts:
        print(f'  - {a["name"]} ({a["exchange"]}) - Active: {a["is_active"]}, Main: {a["is_main"]}')

    # Verificar TODAS as exchange accounts no banco
    print("\n" + "=" * 80)
    print("TODAS AS EXCHANGE ACCOUNTS NO BANCO")
    print("=" * 80)

    all_accounts = await conn.fetch('''
        SELECT ea.id, ea.name, ea.exchange, ea.testnet, ea.is_active, ea.user_id, u.email
        FROM exchange_accounts ea
        LEFT JOIN users u ON ea.user_id = u.id
        ORDER BY ea.created_at DESC
    ''')

    print(f'Total: {len(all_accounts)}')
    for a in all_accounts:
        net = "TESTNET" if a["testnet"] else "MAINNET"
        active = "ACTIVE" if a["is_active"] else "INACTIVE"
        print(f'  - {a["name"]} ({a["exchange"].upper()} {net}) - {active}')
        print(f'    User: {a["email"]} ({a["user_id"]})')
        print()

    # Verificar usuarios que tem exchange accounts
    print("=" * 80)
    print("USUARIOS COM EXCHANGE ACCOUNTS")
    print("=" * 80)

    users_with_accounts = await conn.fetch('''
        SELECT u.id, u.email, u.name, COUNT(ea.id) as account_count
        FROM users u
        LEFT JOIN exchange_accounts ea ON ea.user_id = u.id
        GROUP BY u.id, u.email, u.name
        HAVING COUNT(ea.id) > 0
        ORDER BY account_count DESC
    ''')

    print(f'Total de usuarios com contas: {len(users_with_accounts)}')
    for u in users_with_accounts:
        print(f'  - {u["email"]}: {u["account_count"]} conta(s)')

    # Verificar contas demo do SQL
    print("\n" + "=" * 80)
    print("STATUS DAS CONTAS DEMO (do SQL insert)")
    print("=" * 80)

    demo_users = await conn.fetch('''
        SELECT id, email, name, is_active, is_verified
        FROM users
        WHERE email IN ('demo@tradingplatform.com', 'trader@tradingplatform.com', 'admin@tradingplatform.com')
    ''')

    if demo_users:
        for u in demo_users:
            print(f'  - {u["email"]} - Active: {u["is_active"]}, Verified: {u["is_verified"]}')

            # Buscar exchange accounts desta conta
            demo_accounts = await conn.fetch('''
                SELECT name, exchange, testnet, is_active
                FROM exchange_accounts
                WHERE user_id = $1
            ''', u["id"])

            for acc in demo_accounts:
                print(f'      -> {acc["name"]} ({acc["exchange"]})')
    else:
        print("  Contas demo NAO ENCONTRADAS no banco!")

    await conn.close()

asyncio.run(check())

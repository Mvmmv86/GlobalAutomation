"""Script para verificar estado do banco - todas as contas e exchanges"""
import asyncio
import os
from dotenv import load_dotenv
import asyncpg

load_dotenv()

async def check_db():
    database_url = os.getenv('DATABASE_URL').replace('postgresql+asyncpg://', 'postgresql://')

    try:
        conn = await asyncpg.connect(database_url, timeout=10)

        print("=" * 80)
        print("USUARIOS NO BANCO")
        print("=" * 80)

        users = await conn.fetch('''
            SELECT id, email, name, is_active, created_at
            FROM users
            ORDER BY created_at DESC
        ''')

        for u in users:
            print(f"ID: {u['id']}")
            print(f"Email: {u['email']}")
            print(f"Name: {u['name']}")
            print(f"Active: {u['is_active']}")
            print(f"Created: {u['created_at']}")
            print("-" * 40)

        print(f"\nTotal usuarios: {len(users)}")

        print("\n" + "=" * 80)
        print("EXCHANGE ACCOUNTS NO BANCO")
        print("=" * 80)

        accounts = await conn.fetch('''
            SELECT
                ea.id, ea.name, ea.exchange, ea.testnet, ea.is_active, ea.is_main,
                ea.user_id, u.email as user_email,
                LEFT(ea.api_key, 15) as api_key_preview
            FROM exchange_accounts ea
            LEFT JOIN users u ON ea.user_id = u.id
            ORDER BY ea.created_at DESC
        ''')

        for a in accounts:
            main = " [MAIN]" if a['is_main'] else ""
            net = "TESTNET" if a['testnet'] else "MAINNET"
            active = "ACTIVE" if a['is_active'] else "INACTIVE"
            print(f"ID: {a['id']}")
            print(f"Name: {a['name']}{main}")
            print(f"Exchange: {a['exchange'].upper()} ({net}) - {active}")
            print(f"API Key: {a['api_key_preview']}...")
            print(f"User: {a['user_email']} ({a['user_id']})")
            print("-" * 40)

        print(f"\nTotal exchange accounts: {len(accounts)}")

        # Verificar especificamente a conta test@globalautomation.com
        print("\n" + "=" * 80)
        print("CONTA test@globalautomation.com")
        print("=" * 80)

        test_user = await conn.fetchrow('''
            SELECT id, email, name FROM users WHERE email = $1
        ''', 'test@globalautomation.com')

        if test_user:
            print(f"User ID: {test_user['id']}")

            test_accounts = await conn.fetch('''
                SELECT id, name, exchange, testnet, is_active, is_main
                FROM exchange_accounts
                WHERE user_id = $1
            ''', test_user['id'])

            print(f"Exchange accounts vinculadas: {len(test_accounts)}")
            for ta in test_accounts:
                print(f"  - {ta['name']} ({ta['exchange']}) - Main: {ta['is_main']}")
        else:
            print("Usuario test@globalautomation.com NAO ENCONTRADO!")

        await conn.close()

    except Exception as e:
        print(f"ERRO: {e}")

asyncio.run(check_db())

"""Check exchange account configuration for trader user"""
import asyncio
import os
from sqlalchemy import text
from infrastructure.database.connection_transaction_mode import transaction_db

async def check_account():
    """Check exchange account"""
    await transaction_db.connect()

    async with transaction_db.session() as session:
        # Get exchange account
        result = await session.execute(text("""
            SELECT
                id,
                user_id,
                exchange,
                account_name,
                is_testnet,
                created_at
            FROM exchange_accounts
            WHERE user_id = '550e8400-e29b-41d4-a716-446655440002'
            ORDER BY created_at DESC
            LIMIT 5
        """))

        accounts = result.fetchall()

        print("\n📊 Exchange Accounts for trader@tradingplatform.com:")
        print("=" * 80)
        for acc in accounts:
            print(f"\n🏦 Account ID: {acc[0]}")
            print(f"   User ID: {acc[1]}")
            print(f"   Exchange: {acc[2]}")
            print(f"   Name: {acc[3]}")
            print(f"   Is Testnet: {acc[4]}")
            print(f"   Created: {acc[5]}")

    await transaction_db.disconnect()

if __name__ == "__main__":
    asyncio.run(check_account())

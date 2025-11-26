"""Create exchange account directly in database (bypass timeout issue)"""
import asyncio
import sys
from sqlalchemy import text
from infrastructure.database.connection_transaction_mode import transaction_db

async def create_account(name: str, exchange: str, api_key: str, secret_key: str, testnet: bool = False, is_main: bool = True):
    """Create exchange account directly"""
    await transaction_db.connect()

    async with transaction_db.session() as session:
        # Get user ID (trader@tradingplatform.com)
        result = await session.execute(text("""
            SELECT id FROM users WHERE email = 'trader@tradingplatform.com'
        """))
        user = result.fetchone()

        if not user:
            print("❌ User not found!")
            return

        user_id = user[0]

        # Se esta conta é principal, desmarcar outras
        if is_main:
            await session.execute(text("""
                UPDATE exchange_accounts
                SET is_main = false
                WHERE exchange = :exchange AND user_id = :user_id
            """), {"exchange": exchange, "user_id": user_id})

        # Create account
        result = await session.execute(text("""
            INSERT INTO exchange_accounts (
                name, exchange, testnet, is_active,
                api_key, secret_key, user_id, is_main,
                created_at, updated_at
            ) VALUES (
                :name, :exchange, :testnet, true,
                :api_key, :secret_key, :user_id, :is_main,
                NOW(), NOW()
            )
            RETURNING id, name, exchange
        """), {
            "name": name,
            "exchange": exchange,
            "testnet": testnet,
            "api_key": api_key,
            "secret_key": secret_key,
            "user_id": user_id,
            "is_main": is_main
        })

        account = result.fetchone()

        await session.commit()

        print(f"\n✅ Exchange Account Created Successfully!")
        print(f"   ID: {account[0]}")
        print(f"   Name: {account[1]}")
        print(f"   Exchange: {account[2]}")
        print(f"   Testnet: {testnet}")
        print(f"   Is Main: {is_main}")

    await transaction_db.disconnect()

if __name__ == "__main__":
    print("\n🏦 CREATE EXCHANGE ACCOUNT (Direct Database)")
    print("=" * 50)

    if len(sys.argv) < 5:
        print("\nUsage:")
        print("  python3 create_exchange_account_direct.py <name> <exchange> <api_key> <secret_key> [testnet] [is_main]")
        print("\nExample:")
        print('  python3 create_exchange_account_direct.py "Binance Production" binance "YOUR_API_KEY" "YOUR_SECRET" false true')
        sys.exit(1)

    name = sys.argv[1]
    exchange = sys.argv[2].lower()
    api_key = sys.argv[3]
    secret_key = sys.argv[4]
    testnet = sys.argv[5].lower() == "true" if len(sys.argv) > 5 else False
    is_main = sys.argv[6].lower() == "true" if len(sys.argv) > 6 else True

    asyncio.run(create_account(name, exchange, api_key, secret_key, testnet, is_main))

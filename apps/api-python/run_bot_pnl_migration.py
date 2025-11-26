"""Run bot_pnl_history migration"""
import asyncio
import os
from dotenv import load_dotenv
import asyncpg

load_dotenv()

async def run_migration():
    database_url = os.getenv('DATABASE_URL').replace('postgresql+asyncpg://', 'postgresql://')
    conn = await asyncpg.connect(database_url, timeout=30, statement_cache_size=0)

    try:
        # Read and execute migration
        with open('migrations/create_bot_pnl_history.sql', 'r') as f:
            sql = f.read()

        await conn.execute(sql)
        print("✅ Migration executed successfully!")

        # Verify tables exist
        tables = await conn.fetch("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name IN ('bot_pnl_history', 'bot_trades')
        """)
        print(f"✅ Created tables: {[t['table_name'] for t in tables]}")

    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(run_migration())

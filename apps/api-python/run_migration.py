"""
Script to run migration on Supabase
"""
import asyncio
import asyncpg
import sys

# DEV Database URL
DEV_DATABASE_URL = "postgresql://postgres.zmdqmrugotfftxvrwdsd:Wzg0kBvtrSbclQ9V@aws-1-us-east-2.pooler.supabase.com:6543/postgres"

# PROD Database URL (US-West-2) - Use port 5432 for direct connection (not pooler)
PROD_DATABASE_URL = "postgresql://postgres.wqmqsanuegvzbmjtxzac:ePBYqQKSYK.4y4r@aws-0-us-west-2.pooler.supabase.com:5432/postgres"

MIGRATION_SQL = """
ALTER TABLE bot_signal_executions
ADD COLUMN IF NOT EXISTS sl_order_status VARCHAR(20) DEFAULT 'pending',
ADD COLUMN IF NOT EXISTS tp_order_status VARCHAR(20) DEFAULT 'pending',
ADD COLUMN IF NOT EXISTS sl_filled_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS tp_filled_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS realized_pnl DECIMAL(18,8),
ADD COLUMN IF NOT EXISTS close_reason VARCHAR(20);
"""


async def run_migration(database_url: str, env_name: str):
    print(f"Running migration on {env_name}...")

    try:
        # Set statement_cache_size=0 for pgbouncer compatibility
        conn = await asyncpg.connect(database_url, ssl='require', statement_cache_size=0)

        # Run main migration
        print("Adding columns to bot_signal_executions...")
        await conn.execute(MIGRATION_SQL)
        print("Done: bot_signal_executions")

        # Check and add bot_trades columns
        print("Checking bot_trades columns...")
        
        columns_to_add = [
            ("status", "VARCHAR(20) DEFAULT 'closed'"),
            ("exit_reason", "VARCHAR(20)"),
            ("sl_order_id", "VARCHAR(100)"),
            ("tp_order_id", "VARCHAR(100)"),
            ("pnl_pct", "DECIMAL(10,4)")
        ]
        
        for col_name, col_type in columns_to_add:
            exists = await conn.fetchval(f"""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'bot_trades' AND column_name = '{col_name}'
                )
            """)
            if not exists:
                await conn.execute(f"ALTER TABLE bot_trades ADD COLUMN {col_name} {col_type}")
                print(f"  Added: {col_name}")
            else:
                print(f"  Exists: {col_name}")

        # Create indexes
        print("Creating indexes...")
        try:
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_bot_trades_status ON bot_trades(status)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_bot_trades_subscription_status ON bot_trades(subscription_id, status)")
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_bot_signal_executions_sltp_status
                ON bot_signal_executions(sl_order_status, tp_order_status)
                WHERE sl_order_status = 'pending' OR tp_order_status = 'pending'
            """)
            print("  Indexes created")
        except Exception as e:
            print(f"  Index warning: {e}")

        await conn.close()
        print(f"Migration completed on {env_name}!")
        return True

    except Exception as e:
        print(f"Migration failed: {e}")
        return False


async def main():
    env = sys.argv[1] if len(sys.argv) > 1 else "dev"
    if env == "dev":
        await run_migration(DEV_DATABASE_URL, "DEV")
    elif env == "prod":
        await run_migration(PROD_DATABASE_URL, "PROD")
    else:
        print("Usage: python run_migration.py [dev|prod]")


if __name__ == "__main__":
    asyncio.run(main())

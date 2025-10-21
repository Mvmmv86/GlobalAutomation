"""
Simple synchronous migration to add SL/TP columns
Uses environment variable DATABASE_URL
"""
import os
import asyncpg
import asyncio


async def run_migration():
    """Run the migration"""
    # Get database URL from environment
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ ERROR: DATABASE_URL not set")
        return False

    # Convert asyncpg URL format
    database_url = database_url.replace("postgresql+asyncpg://", "postgresql://")

    print("🚀 Starting migration: add_sl_tp_columns")
    print(f"📡 Connecting to database...")

    try:
        # Connect to database
        conn = await asyncpg.connect(database_url)
        print("✅ Connected to database")

        # Execute ALTER TABLE
        print("📝 Adding columns...")
        await conn.execute("""
            ALTER TABLE bot_signal_executions
            ADD COLUMN IF NOT EXISTS stop_loss_order_id VARCHAR(255),
            ADD COLUMN IF NOT EXISTS take_profit_order_id VARCHAR(255),
            ADD COLUMN IF NOT EXISTS stop_loss_price DECIMAL(18, 8),
            ADD COLUMN IF NOT EXISTS take_profit_price DECIMAL(18, 8)
        """)
        print("✅ Columns added")

        # Create indexes
        print("🔍 Creating indexes...")
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_bot_signal_executions_sl_order
            ON bot_signal_executions(stop_loss_order_id)
            WHERE stop_loss_order_id IS NOT NULL
        """)
        print("✅ SL index created")

        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_bot_signal_executions_tp_order
            ON bot_signal_executions(take_profit_order_id)
            WHERE take_profit_order_id IS NOT NULL
        """)
        print("✅ TP index created")

        # Add comments
        print("📝 Adding column comments...")
        await conn.execute("""
            COMMENT ON COLUMN bot_signal_executions.stop_loss_order_id
            IS 'ID da ordem de Stop Loss criada na exchange'
        """)

        await conn.execute("""
            COMMENT ON COLUMN bot_signal_executions.take_profit_order_id
            IS 'ID da ordem de Take Profit criada na exchange'
        """)

        await conn.execute("""
            COMMENT ON COLUMN bot_signal_executions.stop_loss_price
            IS 'Preço configurado para o Stop Loss'
        """)

        await conn.execute("""
            COMMENT ON COLUMN bot_signal_executions.take_profit_price
            IS 'Preço configurado para o Take Profit'
        """)
        print("✅ Comments added")

        # Close connection
        await conn.close()
        print("🔌 Disconnected from database")

        print("=" * 60)
        print("🎯 MIGRATION COMPLETED SUCCESSFULLY!")
        print("   Added columns:")
        print("   - stop_loss_order_id")
        print("   - take_profit_order_id")
        print("   - stop_loss_price")
        print("   - take_profit_price")
        print("   Added indexes for efficient lookups")
        print("=" * 60)

        return True

    except Exception as e:
        print(f"❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(run_migration())
    exit(0 if success else 1)

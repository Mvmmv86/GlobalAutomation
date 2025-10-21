"""
Execute migration to add allowed_directions column
"""
import os
import asyncpg
import asyncio


async def run_migration():
    """Run the migration"""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ ERROR: DATABASE_URL not set")
        return False

    database_url = database_url.replace("postgresql+asyncpg://", "postgresql://")

    print("🚀 Starting migration: add_allowed_directions")
    print(f"📡 Connecting to database...")

    try:
        conn = await asyncpg.connect(database_url)
        print("✅ Connected to database")

        # Add column
        print("📝 Adding allowed_directions column...")
        await conn.execute("""
            ALTER TABLE bots
            ADD COLUMN IF NOT EXISTS allowed_directions VARCHAR(20) DEFAULT 'both'
        """)
        print("✅ Column added")

        # Add constraint
        print("🔒 Adding constraint...")
        await conn.execute("""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_constraint WHERE conname = 'check_allowed_directions'
                ) THEN
                    ALTER TABLE bots
                    ADD CONSTRAINT check_allowed_directions
                    CHECK (allowed_directions IN ('buy_only', 'sell_only', 'both'));
                END IF;
            END $$;
        """)
        print("✅ Constraint added")

        # Create index
        print("🔍 Creating index...")
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_bots_allowed_directions
            ON bots(allowed_directions)
        """)
        print("✅ Index created")

        # Add comment
        print("📝 Adding column comment...")
        await conn.execute("""
            COMMENT ON COLUMN bots.allowed_directions IS
            'Defines which signal directions are allowed: buy_only (Long only), sell_only (Short only), both (Long and Short)'
        """)
        print("✅ Comment added")

        await conn.close()
        print("🔌 Disconnected from database")

        print("=" * 60)
        print("🎯 MIGRATION COMPLETED SUCCESSFULLY!")
        print("   Added column: allowed_directions")
        print("   Default value: 'both'")
        print("   Valid values: 'buy_only', 'sell_only', 'both'")
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

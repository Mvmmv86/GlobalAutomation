"""
Execute SQL migration to add SL/TP columns to bot_signal_executions
"""
import asyncio
import sys
import os

# Add parent directory to path to import infrastructure modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from infrastructure.database.connection_transaction_mode import transaction_db
import structlog

logger = structlog.get_logger(__name__)


async def run_migration():
    """Execute SQL migration to add SL/TP columns"""
    try:
        logger.info("🚀 Starting SQL migration: add_sl_tp_columns")

        # Connect to database
        await transaction_db.connect()
        logger.info("✅ Connected to database")

        # Read migration SQL file
        migration_file = os.path.join(
            os.path.dirname(__file__),
            "add_sl_tp_columns.sql"
        )

        with open(migration_file, 'r') as f:
            sql_content = f.read()

        logger.info("📄 Migration SQL loaded")

        # Split by semicolons and execute each statement
        statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip() and not stmt.strip().startswith('--')]

        for i, statement in enumerate(statements, 1):
            # Skip comments
            if statement.startswith('--'):
                continue

            logger.info(f"Executing statement {i}/{len(statements)}")
            await transaction_db.execute(statement)
            logger.info(f"✅ Statement {i} executed successfully")

        logger.info("=" * 60)
        logger.info("🎯 MIGRATION COMPLETED SUCCESSFULLY!")
        logger.info("   Added columns:")
        logger.info("   - stop_loss_order_id")
        logger.info("   - take_profit_order_id")
        logger.info("   - stop_loss_price")
        logger.info("   - take_profit_price")
        logger.info("   Added indexes for efficient lookups")
        logger.info("=" * 60)

        return True

    except Exception as e:
        logger.error("❌ Migration failed", error=str(e), exc_info=True)
        raise
    finally:
        # Disconnect from database
        await transaction_db.disconnect()
        logger.info("🔌 Disconnected from database")


async def main():
    """Main entry point"""
    try:
        success = await run_migration()

        if success:
            logger.info("✅ Migration completed successfully!")
            sys.exit(0)
        else:
            logger.error("❌ Migration failed")
            sys.exit(1)

    except Exception as e:
        logger.error("❌ Fatal error", error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

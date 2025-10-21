#!/usr/bin/env python3
"""
Migration: Remove master_secret column from bots table
"""
import asyncio
import asyncpg
import os
from dotenv import load_dotenv
import structlog

load_dotenv()
logger = structlog.get_logger()

async def run_migration():
    """Remove master_secret column"""
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise ValueError("DATABASE_URL not found in environment")

    logger.info("🚀 Starting migration: remove master_secret column")

    # Convert asyncpg URL format
    if database_url.startswith("postgresql+asyncpg://"):
        database_url = database_url.replace("postgresql+asyncpg://", "postgresql://")

    conn = await asyncpg.connect(database_url)

    try:
        # Remove master_secret column
        await conn.execute("""
            ALTER TABLE bots DROP COLUMN IF EXISTS master_secret;
        """)

        logger.info("✅ Successfully removed master_secret column from bots table")

    except Exception as e:
        logger.error(f"❌ Error during migration: {e}")
        raise
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(run_migration())

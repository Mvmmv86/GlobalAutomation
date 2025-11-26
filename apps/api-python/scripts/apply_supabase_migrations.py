#!/usr/bin/env python3
"""Apply migrations to Supabase database"""

import asyncio
import os
import sys
from urllib.parse import quote_plus

# Add parent directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import create_async_engine
from infrastructure.database.models.base import Base


async def test_connection_and_apply_migrations():
    """Test connection and apply migrations to Supabase"""

    print("🔗 Connecting to Supabase PostgreSQL...")

    # URL encode the password to handle special characters
    password = "J9xTUM6GhUym@u*"
    encoded_password = quote_plus(password)

    database_url = f"postgresql+asyncpg://postgres:{encoded_password}@db.zmdqmrugotfftxvrwdsd.supabase.co:5432/postgres"

    try:
        # Create engine
        engine = create_async_engine(database_url, echo=True)

        # Test connection
        async with engine.begin() as conn:
            result = await conn.execute("SELECT version()")
            version = result.scalar()
            print(f"✅ Connected to PostgreSQL: {version}")

            # Create all tables
            print("\n🏗️  Creating all tables...")
            await conn.run_sync(Base.metadata.create_all)
            print("✅ All tables created successfully!")

            # List created tables
            result = await conn.execute(
                """
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                ORDER BY table_name
            """
            )
            tables = [row[0] for row in result.fetchall()]

            print(f"\n📋 Created {len(tables)} tables:")
            for table in tables:
                print(f"   ✅ {table}")

        await engine.dispose()
        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_connection_and_apply_migrations())
    if success:
        print("\n🎉 Supabase setup completed successfully!")
    else:
        print("\n💥 Setup failed!")
    sys.exit(0 if success else 1)

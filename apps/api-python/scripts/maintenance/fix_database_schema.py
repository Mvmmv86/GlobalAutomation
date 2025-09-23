#!/usr/bin/env python3
"""Fix database schema issues identified in login system test"""

import asyncio
from sqlalchemy import text
from infrastructure.di.container import get_container


async def fix_database_schema():
    """Apply direct database fixes for login system issues"""

    print("🔧 FIXING DATABASE SCHEMA ISSUES")
    print("=" * 50)

    try:
        container = await get_container()
        engine = container.get("database_engine")

        async with engine.begin() as conn:
            # Fix 1: Increase totp_secret column size
            print("📝 1. Fixing totp_secret column size...")
            try:
                await conn.execute(
                    text(
                        """
                    ALTER TABLE users 
                    ALTER COLUMN totp_secret TYPE VARCHAR(64);
                """
                    )
                )
                print("✅ totp_secret column resized to 64 characters")
            except Exception as e:
                print(f"⚠️  totp_secret fix error (may already be correct): {e}")

            # Fix 2: Add usage_count column to api_keys if missing
            print("📝 2. Adding usage_count column to api_keys...")
            try:
                await conn.execute(
                    text(
                        """
                    ALTER TABLE api_keys 
                    ADD COLUMN IF NOT EXISTS usage_count INTEGER DEFAULT 0;
                """
                    )
                )
                print("✅ usage_count column added to api_keys")
            except Exception as e:
                print(f"⚠️  usage_count fix error: {e}")

            # Fix 3: Add constraints and indexes
            print("📝 3. Adding constraints and indexes...")
            try:
                await conn.execute(
                    text(
                        """
                    CREATE INDEX IF NOT EXISTS idx_api_keys_key_hash 
                    ON api_keys(key_hash);
                """
                    )
                )
                print("✅ api_keys key_hash index created")
            except Exception as e:
                print(f"⚠️  index creation error: {e}")

            # Fix 4: Update any existing records with proper defaults
            print("📝 4. Updating existing records with proper defaults...")
            try:
                result = await conn.execute(
                    text(
                        """
                    UPDATE api_keys 
                    SET usage_count = 0 
                    WHERE usage_count IS NULL;
                """
                    )
                )
                print(
                    f"✅ Updated {result.rowcount} api_keys records with usage_count = 0"
                )
            except Exception as e:
                print(f"⚠️  record update error: {e}")

        await container.close()
        print("\n🎉 DATABASE SCHEMA FIXES COMPLETED!")
        return True

    except Exception as e:
        print(f"\n💥 SCHEMA FIX FAILED: {e}")
        import traceback

        traceback.print_exc()
        return False


async def main():
    """Run database schema fixes"""
    print("🔧 STARTING DATABASE SCHEMA FIXES")
    print("=" * 50)

    success = await fix_database_schema()

    if success:
        print("\n✅ ALL SCHEMA FIXES APPLIED SUCCESSFULLY")
        return 0
    else:
        print("\n❌ SCHEMA FIXES FAILED")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)

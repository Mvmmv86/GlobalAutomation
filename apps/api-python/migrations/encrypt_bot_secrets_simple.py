"""
Simple migration to encrypt existing bot secrets
Uses direct asyncpg connection
"""
import os
import asyncpg
import asyncio
import sys

# Add parent directory to path to import encryption service
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from infrastructure.security.encryption_service import EncryptionService


async def run_migration():
    """Encrypt all plaintext master_secrets in the bots table"""
    # Get database URL from environment
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ ERROR: DATABASE_URL not set")
        return False

    # Convert asyncpg URL format
    database_url = database_url.replace("postgresql+asyncpg://", "postgresql://")

    # Get encryption key
    encryption_key = os.getenv("ENCRYPTION_MASTER_KEY")
    if not encryption_key:
        print("❌ ERROR: ENCRYPTION_MASTER_KEY not set")
        return False

    print("🔐 Starting encryption of existing bot secrets...")
    print(f"📡 Connecting to database...")

    try:
        # Initialize encryption service
        encryption_service = EncryptionService(encryption_key)

        # Connect to database
        conn = await asyncpg.connect(database_url)
        print("✅ Connected to database")

        # Fetch all bots
        bots = await conn.fetch("""
            SELECT id, name, master_secret
            FROM bots
            WHERE master_secret IS NOT NULL
        """)

        print(f"📊 Found {len(bots)} bots to process")

        encrypted_count = 0
        skipped_count = 0
        error_count = 0

        for bot in bots:
            bot_id = str(bot["id"])
            bot_name = bot["name"]
            current_secret = bot["master_secret"]

            try:
                # Try to decrypt - if it works, it's already encrypted
                try:
                    test_decrypt = encryption_service.decrypt_string(
                        current_secret,
                        context="bot_master_webhook"
                    )
                    print(f"⏭️  Bot '{bot_name}' ({bot_id}) - Already encrypted, skipping")
                    skipped_count += 1
                    continue
                except Exception:
                    # Decryption failed, so it's plaintext - proceed with encryption
                    pass

                # Encrypt the plaintext secret
                encrypted_secret = encryption_service.encrypt_string(
                    current_secret,
                    context="bot_master_webhook"
                )

                # Update the database
                await conn.execute("""
                    UPDATE bots
                    SET master_secret = $1,
                        updated_at = NOW()
                    WHERE id = $2
                """, encrypted_secret, bot["id"])

                print(f"✅ Bot '{bot_name}' ({bot_id}) - Secret encrypted successfully")
                encrypted_count += 1

            except Exception as e:
                print(f"❌ Error encrypting secret for bot '{bot_name}' ({bot_id}): {e}")
                error_count += 1

        # Close connection
        await conn.close()
        print("🔌 Disconnected from database")

        # Summary
        print("=" * 60)
        print("🎯 MIGRATION SUMMARY:")
        print(f"   Total bots processed: {len(bots)}")
        print(f"   ✅ Encrypted: {encrypted_count}")
        print(f"   ⏭️  Already encrypted (skipped): {skipped_count}")
        print(f"   ❌ Errors: {error_count}")
        print("=" * 60)

        if error_count > 0:
            print(f"⚠️  {error_count} bot(s) had errors during encryption.")
            print("Please review logs and re-run if needed.")
            return False

        return True

    except Exception as e:
        print(f"❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(run_migration())
    exit(0 if success else 1)

"""
Migration: Encrypt existing bot master_secrets
This script encrypts all plaintext master_secrets in the bots table
"""
import asyncio
import sys
import os

# Add parent directory to path to import infrastructure modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from infrastructure.database.connection_transaction_mode import transaction_db
from infrastructure.security.encryption_service import EncryptionService
import structlog

logger = structlog.get_logger(__name__)


async def encrypt_existing_secrets():
    """Encrypt all plaintext master_secrets in the bots table"""
    try:
        # Initialize encryption service
        encryption_service = EncryptionService()
        logger.info("🔐 Starting encryption of existing bot secrets...")

        # Connect to database
        await transaction_db.connect()
        logger.info("✅ Connected to database")

        # Fetch all bots
        bots = await transaction_db.fetch("""
            SELECT id, name, master_secret
            FROM bots
            WHERE master_secret IS NOT NULL
        """)

        logger.info(f"📊 Found {len(bots)} bots to process")

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
                    logger.info(
                        f"⏭️  Bot '{bot_name}' ({bot_id}) - Already encrypted, skipping"
                    )
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
                await transaction_db.execute("""
                    UPDATE bots
                    SET master_secret = $1,
                        updated_at = NOW()
                    WHERE id = $2
                """, encrypted_secret, bot["id"])

                logger.info(
                    f"✅ Bot '{bot_name}' ({bot_id}) - Secret encrypted successfully"
                )
                encrypted_count += 1

            except Exception as e:
                logger.error(
                    f"❌ Error encrypting secret for bot '{bot_name}' ({bot_id})",
                    error=str(e),
                    exc_info=True
                )
                error_count += 1

        # Summary
        logger.info("=" * 60)
        logger.info("🎯 MIGRATION SUMMARY:")
        logger.info(f"   Total bots processed: {len(bots)}")
        logger.info(f"   ✅ Encrypted: {encrypted_count}")
        logger.info(f"   ⏭️  Already encrypted (skipped): {skipped_count}")
        logger.info(f"   ❌ Errors: {error_count}")
        logger.info("=" * 60)

        if error_count > 0:
            logger.warning(
                f"⚠️  {error_count} bot(s) had errors during encryption. "
                "Please review logs and re-run if needed."
            )

        return {
            "success": error_count == 0,
            "total": len(bots),
            "encrypted": encrypted_count,
            "skipped": skipped_count,
            "errors": error_count
        }

    except Exception as e:
        logger.error("❌ Fatal error during migration", error=str(e), exc_info=True)
        raise
    finally:
        # Disconnect from database
        await transaction_db.disconnect()
        logger.info("🔌 Disconnected from database")


async def main():
    """Main entry point"""
    logger.info("🚀 Starting bot secrets encryption migration...")

    try:
        result = await encrypt_existing_secrets()

        if result["success"]:
            logger.info("✅ Migration completed successfully!")
            sys.exit(0)
        else:
            logger.error("❌ Migration completed with errors")
            sys.exit(1)

    except Exception as e:
        logger.error("❌ Migration failed", error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    # Check for ENCRYPTION_MASTER_KEY
    if not os.getenv("ENCRYPTION_MASTER_KEY"):
        print("❌ ERROR: ENCRYPTION_MASTER_KEY environment variable not set!")
        print("   Please set it before running this migration.")
        print("   Example: export ENCRYPTION_MASTER_KEY='your-key-here'")
        sys.exit(1)

    asyncio.run(main())

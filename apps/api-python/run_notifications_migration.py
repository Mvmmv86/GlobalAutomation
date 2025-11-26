"""
Script to create the notifications table in the database.
Run this once to create the table structure.
"""

import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def run_migration():
    """Execute the notifications table migration"""
    import asyncpg

    # Get database URL from environment
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        print("ERROR: DATABASE_URL not found in environment")
        return False

    # Fix the URL scheme for asyncpg (remove +asyncpg suffix)
    if "postgresql+asyncpg://" in database_url:
        database_url = database_url.replace("postgresql+asyncpg://", "postgresql://")
    elif "postgres+asyncpg://" in database_url:
        database_url = database_url.replace("postgres+asyncpg://", "postgres://")

    print(f"Connecting to database...")

    try:
        # Connect to the database
        conn = await asyncpg.connect(database_url)

        print("Connected! Running migration...")

        # Drop existing types if they exist (clean slate)
        try:
            await conn.execute("DROP TYPE IF EXISTS notificationtype CASCADE")
            await conn.execute("DROP TYPE IF EXISTS notificationcategory CASCADE")
            print("Dropped existing types (if any)")
        except Exception as e:
            print(f"Note: {e}")

        # Create ENUM types
        await conn.execute("""
            CREATE TYPE notificationtype AS ENUM ('success', 'warning', 'error', 'info')
        """)
        print("Created notificationtype enum")

        await conn.execute("""
            CREATE TYPE notificationcategory AS ENUM ('order', 'position', 'system', 'market', 'bot', 'price_alert')
        """)
        print("Created notificationcategory enum")

        # Create the notifications table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS notifications (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                type notificationtype NOT NULL DEFAULT 'info',
                category notificationcategory NOT NULL DEFAULT 'system',
                title VARCHAR(255) NOT NULL,
                message TEXT NOT NULL,
                read BOOLEAN NOT NULL DEFAULT false,
                action_url VARCHAR(512),
                metadata JSONB,
                user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
        """)
        print("Created notifications table")

        # Create indexes
        await conn.execute("CREATE INDEX IF NOT EXISTS ix_notifications_user_id ON notifications(user_id)")
        await conn.execute("CREATE INDEX IF NOT EXISTS ix_notifications_read ON notifications(read)")
        await conn.execute("CREATE INDEX IF NOT EXISTS ix_notifications_category ON notifications(category)")
        await conn.execute("CREATE INDEX IF NOT EXISTS ix_notifications_created_at ON notifications(created_at DESC)")
        await conn.execute("CREATE INDEX IF NOT EXISTS ix_notifications_user_unread ON notifications(user_id, read) WHERE read = false")
        print("Created indexes")

        # Create trigger function
        await conn.execute("""
            CREATE OR REPLACE FUNCTION update_notifications_updated_at()
            RETURNS TRIGGER AS $$
            BEGIN
                NEW.updated_at = now();
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql
        """)
        print("Created trigger function")

        # Create trigger
        await conn.execute("DROP TRIGGER IF EXISTS trigger_notifications_updated_at ON notifications")
        await conn.execute("""
            CREATE TRIGGER trigger_notifications_updated_at
                BEFORE UPDATE ON notifications
                FOR EACH ROW
                EXECUTE FUNCTION update_notifications_updated_at()
        """)
        print("Created trigger")

        await conn.close()

        print("\n" + "="*50)
        print("SUCCESS! Notifications table created successfully!")
        print("="*50)

        return True

    except Exception as e:
        print(f"ERROR: {e}")
        return False


if __name__ == "__main__":
    asyncio.run(run_migration())

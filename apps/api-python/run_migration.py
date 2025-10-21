"""
Script to run database migrations
"""
import asyncio
import os
import sys
sys.path.insert(0, '/home/globalauto/global/apps/api-python')

from infrastructure.database.connection_transaction_mode import transaction_db

async def run_admin_migration():
    """Execute admin system migration"""
    try:
        with open('migrations/create_admin_system.sql', 'r') as f:
            sql = f.read()

        print("🔄 Running admin system migration...")

        # Split by semicolon but keep DO blocks together
        statements = []
        current = []
        in_do_block = False

        for line in sql.split('\n'):
            if 'DO $$' in line or 'DO$' in line:
                in_do_block = True
            
            current.append(line)
            
            if in_do_block and '$$;' in line:
                in_do_block = False
                statements.append('\n'.join(current))
                current = []
            elif not in_do_block and ';' in line and line.strip() and not line.strip().startswith('--'):
                statements.append('\n'.join(current))
                current = []

        # Execute each statement
        for i, statement in enumerate(statements, 1):
            statement = statement.strip()
            if statement and not statement.startswith('--'):
                try:
                    await transaction_db.execute(statement)
                    print(f"✅ Statement {i}/{len(statements)} executed")
                except Exception as e:
                    error_msg = str(e).lower()
                    if 'already exists' in error_msg or 'duplicate' in error_msg:
                        print(f"⚠️  Statement {i} skipped (already exists)")
                    else:
                        print(f"❌ Error in statement {i}: {e}")

        print("\n✅ Admin system migration completed!")
        print("👤 Default super admin: demo@tradingplatform.com")

    except Exception as e:
        print(f"❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(run_admin_migration())

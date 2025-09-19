#!/usr/bin/env python3
"""Fix exchange_accounts table schema"""

import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

async def fix_exchange_accounts_schema():
    """Add missing columns to exchange_accounts table"""
    
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URL not found")
        return
    
    # Convert to asyncpg format
    database_url = database_url.replace("postgresql+asyncpg://", "postgresql://")
    
    try:
        conn = await asyncpg.connect(
            database_url,
            statement_cache_size=0,
            command_timeout=60
        )
        
        print("✅ Connected to Supabase")
        
        # Check current table structure
        print("\n🔍 Checking current exchange_accounts table...")
        
        columns = await conn.fetch("""
            SELECT column_name, data_type, is_nullable 
            FROM information_schema.columns 
            WHERE table_name = 'exchange_accounts' 
            AND table_schema = 'public'
            ORDER BY ordinal_position
        """)
        
        print(f"📊 Current columns ({len(columns)}):")
        for col in columns:
            print(f"   • {col['column_name']} ({col['data_type']}) - {col['is_nullable']}")
        
        # Check if api_key_encrypted column exists
        has_api_key_encrypted = any(col['column_name'] == 'api_key_encrypted' for col in columns)
        
        if not has_api_key_encrypted:
            print("\n🔧 Adding missing api_key_encrypted column...")
            await conn.execute("""
                ALTER TABLE exchange_accounts 
                ADD COLUMN IF NOT EXISTS api_key_encrypted TEXT
            """)
            print("✅ Added api_key_encrypted column")
        else:
            print("\n✅ api_key_encrypted column already exists")
        
        # Check if secret_key_encrypted column exists
        has_secret_key_encrypted = any(col['column_name'] == 'secret_key_encrypted' for col in columns)
        
        if not has_secret_key_encrypted:
            print("🔧 Adding missing secret_key_encrypted column...")
            await conn.execute("""
                ALTER TABLE exchange_accounts 
                ADD COLUMN IF NOT EXISTS secret_key_encrypted TEXT
            """)
            print("✅ Added secret_key_encrypted column")
        else:
            print("✅ secret_key_encrypted column already exists")
        
        # Check if passphrase_encrypted column exists
        has_passphrase_encrypted = any(col['column_name'] == 'passphrase_encrypted' for col in columns)
        
        if not has_passphrase_encrypted:
            print("🔧 Adding missing passphrase_encrypted column...")
            await conn.execute("""
                ALTER TABLE exchange_accounts 
                ADD COLUMN IF NOT EXISTS passphrase_encrypted TEXT
            """)
            print("✅ Added passphrase_encrypted column")
        else:
            print("✅ passphrase_encrypted column already exists")
        
        # Add other commonly needed columns
        other_columns = [
            ("is_testnet", "BOOLEAN DEFAULT false"),
            ("is_active", "BOOLEAN DEFAULT true"),
            ("last_sync", "TIMESTAMP"),
            ("error_count", "INTEGER DEFAULT 0"),
            ("last_error", "TEXT"),
        ]
        
        for col_name, col_def in other_columns:
            has_column = any(col['column_name'] == col_name for col in columns)
            if not has_column:
                print(f"🔧 Adding missing {col_name} column...")
                await conn.execute(f"""
                    ALTER TABLE exchange_accounts 
                    ADD COLUMN IF NOT EXISTS {col_name} {col_def}
                """)
                print(f"✅ Added {col_name} column")
        
        # Show final table structure
        print("\n📋 Final table structure:")
        final_columns = await conn.fetch("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns 
            WHERE table_name = 'exchange_accounts' 
            AND table_schema = 'public'
            ORDER BY ordinal_position
        """)
        
        for col in final_columns:
            default = col['column_default'] or 'NULL'
            print(f"   • {col['column_name']} ({col['data_type']}) - nullable: {col['is_nullable']}, default: {default}")
        
        await conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

async def create_test_exchange_account():
    """Create a test exchange account"""
    
    database_url = os.getenv("DATABASE_URL")
    database_url = database_url.replace("postgresql+asyncpg://", "postgresql://")
    
    try:
        conn = await asyncpg.connect(
            database_url,
            statement_cache_size=0,
            command_timeout=60
        )
        
        print("\n🧪 Creating test exchange account...")
        
        # Get first user ID
        user = await conn.fetchrow("SELECT id FROM users LIMIT 1")
        if not user:
            print("❌ No users found")
            return False
        
        user_id = user['id']
        
        # Create test account
        await conn.execute("""
            INSERT INTO exchange_accounts (
                user_id, name, exchange, api_key_encrypted, 
                secret_key_encrypted, is_testnet, is_active
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            ON CONFLICT (user_id, name) DO UPDATE SET
                api_key_encrypted = $4,
                secret_key_encrypted = $5,
                is_testnet = $6,
                is_active = $7
        """, user_id, "Binance Demo", "binance", "demo_api_key", "demo_secret_key", True, True)
        
        print("✅ Test exchange account created")
        
        # Show accounts
        accounts = await conn.fetch("""
            SELECT id, user_id, name, exchange, is_testnet, is_active, created_at
            FROM exchange_accounts
            ORDER BY created_at DESC
            LIMIT 5
        """)
        
        print(f"\n📊 Exchange accounts ({len(accounts)}):")
        for acc in accounts:
            print(f"   • {acc['name']} ({acc['exchange']}) - testnet: {acc['is_testnet']}, active: {acc['is_active']}")
        
        await conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error creating test account: {e}")
        return False

if __name__ == "__main__":
    print("🔧 Fixing exchange_accounts schema...")
    print("="*60)
    
    success = asyncio.run(fix_exchange_accounts_schema())
    
    if success:
        print("\n" + "="*60)
        print("✨ SCHEMA FIXED SUCCESSFULLY!")
        
        # Create test account
        test_success = asyncio.run(create_test_exchange_account())
        
        if test_success:
            print("✨ TEST ACCOUNT CREATED!")
            print("="*60)
            print("\n🚀 Now try:")
            print("1. Refresh the dashboard at http://localhost:3000")
            print("2. Click 'Create Test Order' button")
            print("3. Check if TradingView webhooks work")
            print("\n💡 The system should now process orders correctly!")
        
    else:
        print("\n❌ Schema fix failed")
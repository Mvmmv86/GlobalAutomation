#!/usr/bin/env python3
"""Check and create users in Supabase"""

import asyncio
import asyncpg
import bcrypt
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

async def check_and_create_users():
    """Check existing users and create test users if needed"""
    
    # Get database URL from environment
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URL not found in environment")
        return
    
    # Convert to asyncpg format
    database_url = database_url.replace("postgresql+asyncpg://", "postgresql://")
    
    try:
        # Connect to Supabase
        conn = await asyncpg.connect(
            database_url,
            statement_cache_size=0,
            command_timeout=60
        )
        
        print("✅ Connected to Supabase successfully!")
        
        # Check if users table exists
        table_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'users'
            )
        """)
        
        if not table_exists:
            print("⚠️  Users table doesn't exist. Creating it...")
            await create_users_table(conn)
        
        # Check existing users
        users = await conn.fetch("SELECT email, full_name FROM users ORDER BY created_at")
        
        print(f"\n📊 Found {len(users)} users in database:")
        for user in users:
            print(f"   • {user['email']} ({user['full_name'] or 'No name'})")
        
        if len(users) == 0:
            print("\n🔧 No users found. Creating test users...")
            await create_test_users(conn)
        else:
            print("\n💡 Users already exist. You can use existing credentials or create new ones.")
            
            # Reset passwords for common test emails
            test_emails = ['test@test.com', 'admin@trading.com', 'trader@demo.com']
            for email in test_emails:
                existing_user = await conn.fetchrow("SELECT id FROM users WHERE email = $1", email)
                if existing_user:
                    await reset_user_password(conn, email, "Test@123")
                    print(f"🔄 Reset password for {email}")
        
        # Show final user list
        users = await conn.fetch("SELECT email, full_name FROM users ORDER BY created_at")
        print(f"\n📧 Available accounts for login:")
        for user in users[:5]:  # Show first 5
            print(f"   • Email: {user['email']}")
            print(f"     Password: Test@123")
            print()
        
        await conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

async def create_users_table(conn):
    """Create users table"""
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            email VARCHAR(255) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            full_name VARCHAR(255),
            is_active BOOLEAN DEFAULT true,
            is_verified BOOLEAN DEFAULT true,
            totp_secret VARCHAR(255),
            totp_enabled BOOLEAN DEFAULT false,
            failed_login_attempts INTEGER DEFAULT 0,
            locked_until TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("✅ Users table created!")

async def create_test_users(conn):
    """Create test users"""
    test_users = [
        ("test@test.com", "Test@123", "Test User"),
        ("admin@trading.com", "Test@123", "Admin User"),
        ("trader@demo.com", "Test@123", "Demo Trader"),
        ("usuario@teste.com", "Test@123", "Usuário Teste"),
        ("demo@example.com", "Test@123", "Demo Account")
    ]
    
    for email, password, name in test_users:
        # Hash password
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        try:
            await conn.execute("""
                INSERT INTO users (email, password_hash, full_name, is_active, is_verified)
                VALUES ($1, $2, $3, true, true)
                ON CONFLICT (email) 
                DO UPDATE SET 
                    password_hash = $2,
                    full_name = $3,
                    failed_login_attempts = 0,
                    locked_until = NULL,
                    updated_at = CURRENT_TIMESTAMP
            """, email, password_hash, name)
            
            print(f"✅ User created/updated: {email}")
            
        except Exception as e:
            print(f"⚠️  Error with {email}: {e}")

async def reset_user_password(conn, email, password):
    """Reset user password"""
    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    await conn.execute("""
        UPDATE users 
        SET password_hash = $1, 
            failed_login_attempts = 0,
            locked_until = NULL,
            updated_at = CURRENT_TIMESTAMP
        WHERE email = $2
    """, password_hash, email)

if __name__ == "__main__":
    print("🔍 Checking Supabase users...\n")
    success = asyncio.run(check_and_create_users())
    
    if success:
        print("\n" + "="*60)
        print("✨ SUPABASE USERS READY!")
        print("="*60)
        print("\n🚀 You can now login at: http://localhost:3000")
        print("🔑 Use any of the emails above with password: Test@123")
        print("\n💡 The backend is connected to your real Supabase database!")
    else:
        print("\n❌ Failed to setup users")
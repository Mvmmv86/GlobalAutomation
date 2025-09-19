#!/usr/bin/env python3
"""Fix login by creating a user with correct bcrypt hash"""

import asyncio
import bcrypt
import uuid
import asyncpg
from datetime import datetime, timezone

async def create_test_user():
    """Create a test user with proper bcrypt hash"""
    conn = await asyncpg.connect('postgresql://postgres.zmdqmrugotfftxvrwdsd:MFCuJT0Jn04PtCTL@aws-1-us-east-2.pooler.supabase.com:6543/postgres')
    
    # Generate proper bcrypt hash
    password = "teste123"
    salt = bcrypt.gensalt()
    password_hash = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    print(f"🔐 Creating user with bcrypt hash:")
    print(f"   Email: test@teste.com")
    print(f"   Password: {password}")
    print(f"   Hash: {password_hash[:50]}...")
    
    user_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    
    try:
        # Delete existing test user if exists
        await conn.execute("DELETE FROM users WHERE email = 'test@teste.com'")
        
        # Insert new user
        await conn.execute("""
            INSERT INTO users (
                id, email, password_hash, name, is_active, is_verified, 
                totp_enabled, failed_login_attempts, created_at, updated_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
        """, user_id, "test@teste.com", password_hash, "Test User", 
             True, True, False, 0, now, now)
        
        print("✅ User created successfully!")
        
        # Verify the hash works
        test_hash = await conn.fetchval("SELECT password_hash FROM users WHERE email = 'test@teste.com'")
        if bcrypt.checkpw(password.encode('utf-8'), test_hash.encode('utf-8')):
            print("✅ Password verification test passed!")
        else:
            print("❌ Password verification test failed!")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(create_test_user())
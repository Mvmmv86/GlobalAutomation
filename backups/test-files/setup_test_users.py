#!/usr/bin/env python3
"""Setup test users and reset rate limiting"""

import asyncio
import asyncpg
import bcrypt
from datetime import datetime

async def setup_test_users():
    """Create test users for security testing"""
    
    # Connect to database
    conn = await asyncpg.connect(
        "postgresql://fastapi_user:fastapi_password@localhost:5432/fastapi_db"
    )
    
    try:
        # Reset any locked accounts
        await conn.execute("""
            UPDATE users 
            SET failed_login_attempts = 0, 
                locked_until = NULL 
            WHERE email LIKE '%test%'
        """)
        
        # Hash passwords
        password_hash = bcrypt.hashpw("123456".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        # Create/update main test user
        await conn.execute("""
            INSERT INTO users (email, password_hash, full_name, created_at, failed_login_attempts) 
            VALUES ($1, $2, $3, $4, 0)
            ON CONFLICT (email) 
            DO UPDATE SET 
                password_hash = $2,
                failed_login_attempts = 0,
                locked_until = NULL
        """, "test@test.com", password_hash, "Test User", datetime.utcnow())
        
        # Create security test user
        await conn.execute("""
            INSERT INTO users (email, password_hash, full_name, created_at, failed_login_attempts) 
            VALUES ($1, $2, $3, $4, 0)
            ON CONFLICT (email) 
            DO UPDATE SET 
                password_hash = $2,
                failed_login_attempts = 0,
                locked_until = NULL
        """, "security@test.com", password_hash, "Security Test User", datetime.utcnow())
        
        print("✅ Test users created/updated successfully")
        print("  - test@test.com (password: 123456)")
        print("  - security@test.com (password: 123456)")
        print("  - All accounts unlocked and reset")
        
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(setup_test_users())
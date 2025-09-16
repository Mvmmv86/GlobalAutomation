#!/usr/bin/env python3
"""Create demo user using transaction mode database connection"""

import asyncio
import sys
import os
from datetime import datetime
import bcrypt

# Add parent directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from infrastructure.database.connection_transaction_mode import transaction_db

async def create_demo_user():
    """Create demo user for testing"""
    try:
        await transaction_db.connect()
        
        # Check if demo user already exists
        existing = await transaction_db.fetchrow(
            "SELECT id FROM users WHERE email = $1", 
            "test@exemplo.com"
        )
        
        if existing:
            print("✅ Demo user already exists: test@exemplo.com")
            return
        
        # Hash password
        password = "TestPass123"
        salt = bcrypt.gensalt()
        password_hash = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
        
        # Create user
        user_id = await transaction_db.fetchval("""
            INSERT INTO users (
                name, email, password_hash, is_active, is_verified, 
                totp_enabled, created_at, updated_at
            ) VALUES ($1, $2, $3, $4, $5, $6, NOW(), NOW())
            RETURNING id
        """, "Demo User", "test@exemplo.com", password_hash, True, True, False)
        
        print(f"✅ Created demo user: test@exemplo.com (ID: {user_id})")
        print(f"   Password: {password}")
        print("   You can now login in the frontend!")
        
    except Exception as e:
        print(f"❌ Error creating demo user: {e}")
        
    finally:
        await transaction_db.disconnect()

if __name__ == "__main__":
    asyncio.run(create_demo_user())
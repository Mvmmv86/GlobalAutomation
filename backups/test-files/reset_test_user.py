#!/usr/bin/env python3
"""Reset test user without rate limiting issues"""

import asyncio
import sys
sys.path.append('.')

from infrastructure.database.connection_transaction_mode import get_database
from infrastructure.database.user_repository import UserRepository
from datetime import datetime
import bcrypt

async def reset_test_user():
    """Reset test user account"""
    
    db = get_database()
    user_repo = UserRepository(db)
    
    try:
        # Get current user
        user = await user_repo.get_by_email("test@test.com")
        
        if user:
            print(f"Found user: {user.email}")
            print(f"Current failed attempts: {user.failed_login_attempts}")
            print(f"Current locked until: {user.locked_until}")
            
            # Reset failed attempts and unlock
            await user_repo.reset_failed_attempts("test@test.com")
            
            # Verify password hash is correct
            password = "123456"
            if bcrypt.checkpw(password.encode('utf-8'), user.password_hash.encode('utf-8')):
                print("✅ Password verification successful")
            else:
                print("❌ Password verification failed - updating hash")
                new_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                # Update password hash if needed
                query = """
                    UPDATE users 
                    SET password_hash = $1 
                    WHERE email = $2
                """
                await user_repo.db.execute(query, new_hash, "test@test.com")
                print("✅ Password hash updated")
            
            print("✅ Test user reset successfully")
        else:
            print("❌ Test user not found")
            # Create the user
            password_hash = bcrypt.hashpw("123456".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            
            query = """
                INSERT INTO users (email, password_hash, full_name, created_at, failed_login_attempts) 
                VALUES ($1, $2, $3, $4, 0)
            """
            await user_repo.db.execute(
                query, 
                "test@test.com", 
                password_hash, 
                "Test User", 
                datetime.utcnow()
            )
            print("✅ Test user created")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(reset_test_user())
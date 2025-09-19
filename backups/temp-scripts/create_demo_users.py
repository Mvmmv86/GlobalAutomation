#!/usr/bin/env python3
"""Create demo users for testing the platform"""

import sqlite3
import bcrypt
import uuid
from datetime import datetime

def create_demo_users():
    """Create demo users for testing"""
    
    # Connect to SQLite database (will create if doesn't exist)
    conn = sqlite3.connect('demo_users.db')
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            name TEXT,
            is_active BOOLEAN DEFAULT 1,
            is_verified BOOLEAN DEFAULT 1,
            totp_enabled BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Demo users data
    users = [
        {
            'email': 'admin@trading.com',
            'password': 'Admin@123',
            'name': 'Admin User'
        },
        {
            'email': 'trader@demo.com',
            'password': 'Trader@123',
            'name': 'Demo Trader'
        },
        {
            'email': 'test@test.com',
            'password': 'Test@123',
            'name': 'Test User'
        }
    ]
    
    created_users = []
    
    for user_data in users:
        # Generate password hash
        salt = bcrypt.gensalt()
        password_hash = bcrypt.hashpw(user_data['password'].encode('utf-8'), salt).decode('utf-8')
        
        # Generate UUID
        user_id = str(uuid.uuid4())
        
        try:
            # Insert user
            cursor.execute('''
                INSERT OR REPLACE INTO users 
                (id, email, password_hash, name, is_active, is_verified, totp_enabled)
                VALUES (?, ?, ?, ?, 1, 1, 0)
            ''', (user_id, user_data['email'], password_hash, user_data['name']))
            
            created_users.append({
                'email': user_data['email'],
                'password': user_data['password'],
                'name': user_data['name']
            })
            
            print(f"✅ Created user: {user_data['email']}")
            
        except sqlite3.IntegrityError:
            print(f"⚠️ User {user_data['email']} already exists")
    
    # Commit changes
    conn.commit()
    
    # Show all users
    cursor.execute('SELECT email, name FROM users')
    all_users = cursor.fetchall()
    
    print("\n📊 Current users in database:")
    for email, name in all_users:
        print(f"   • {email} ({name})")
    
    conn.close()
    
    return created_users

if __name__ == "__main__":
    print("🚀 Creating demo users for testing...\n")
    
    users = create_demo_users()
    
    if users:
        print("\n" + "="*60)
        print("✨ DEMO USERS CREATED SUCCESSFULLY!")
        print("="*60)
        print("\nYou can login with these credentials:\n")
        
        for user in users:
            print(f"📧 Email: {user['email']}")
            print(f"🔑 Password: {user['password']}")
            print(f"👤 Name: {user['name']}")
            print("-" * 40)
        
        print("\n💡 Note: These are demo users stored locally for testing.")
        print("   The backend API needs to be configured to use this database.")
    else:
        print("\n❌ No users were created")
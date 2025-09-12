#!/usr/bin/env python3
"""Quick demo user creation using direct SQL"""

import asyncio
from infrastructure.services.auth_service import AuthService
from infrastructure.config.settings import get_settings
import asyncpg


async def create_demo_user_direct():
    """Create demo user directly with SQL"""

    print("🚀 CREATING DEMO USER DIRECTLY")
    print("=" * 40)

    try:
        # Get settings and auth service
        settings = get_settings()
        auth_service = AuthService()

        # Demo credentials
        email = "demo@tradingview.com"
        password = "demo123456"
        name = "Demo User"

        # Hash password
        hashed_password = auth_service.hash_password(password)
        print(f"🔑 Password hashed: {len(hashed_password)} chars")

        # Connect directly to database
        # Convert SQLAlchemy URL to asyncpg format
        db_url = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
        conn = await asyncpg.connect(db_url)

        # Check if user exists
        existing = await conn.fetchrow("SELECT id FROM users WHERE email = $1", email)

        if existing:
            print("✅ Demo user already exists!")
            user_id = existing["id"]
        else:
            # Insert user directly
            user_id = await conn.fetchval(
                """
                INSERT INTO users (email, name, password_hash, is_active, is_verified)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING id
            """,
                email,
                name,
                hashed_password,
                True,
                True,
            )
            print(f"✅ Demo user created with ID: {user_id}")

        await conn.close()

        print(f"📧 Email: {email}")
        print(f"🔑 Password: {password}")
        print(f"👤 Name: {name}")

        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        return False


async def test_login_direct():
    """Test login directly"""

    print("\n🔐 TESTING LOGIN")
    print("=" * 40)

    try:
        import aiohttp

        login_data = {"email": "demo@tradingview.com", "password": "demo123456"}

        async with aiohttp.ClientSession() as session:
            async with session.post(
                "http://localhost:8000/api/v1/auth/login", json=login_data
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    print("✅ Login successful!")
                    print(f"🎫 Token: {data['access_token'][:50]}...")
                    return True
                else:
                    error_data = await response.json()
                    print(f"❌ Login failed: {error_data}")
                    return False

    except Exception as e:
        print(f"❌ Login test error: {e}")
        return False


async def main():
    """Main function"""
    print("🎯 QUICK DEMO USER SETUP")
    print("=" * 50)

    # Create user
    user_created = await create_demo_user_direct()

    if user_created:
        # Test login
        login_works = await test_login_direct()

        if login_works:
            print(f"\n🎉 SUCCESS! You can now:")
            print(f"1. Access React Frontend: http://localhost:3000")
            print(f"2. Use credentials: demo@tradingview.com / demo123456")
            print(f"3. Login and access the dark dashboard!")
            return 0

    print(f"\n💥 SETUP FAILED!")
    return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)

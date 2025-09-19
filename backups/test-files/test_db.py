#!/usr/bin/env python3
import asyncio
import asyncpg
import ssl
from dotenv import load_dotenv
import os

async def test_connection():
    load_dotenv('.env')
    
    # Get DATABASE_URL
    database_url = os.getenv('DATABASE_URL')
    print(f"Original URL: {database_url[:60]}...")
    
    # Convert SQLAlchemy URL to asyncpg URL
    if database_url.startswith("postgresql+asyncpg://"):
        database_url = database_url.replace("postgresql+asyncpg://", "postgresql://")
        print(f"Converted URL: {database_url[:60]}...")
    
    # SSL context (same as in the app)
    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE
    
    try:
        # Test with SSL
        print("\n1. Testing with SSL...")
        conn = await asyncpg.connect(database_url, ssl=ssl_ctx)
        result = await conn.fetchval("SELECT 'Connected with SSL'")
        print(f"✅ {result}")
        await conn.close()
        
        # Test without SSL
        print("\n2. Testing without SSL...")
        conn = await asyncpg.connect(database_url, ssl=None)
        result = await conn.fetchval("SELECT 'Connected without SSL'")
        print(f"✅ {result}")
        await conn.close()
        
        print("\n✅ Both connections successful! Database is accessible.")
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_connection())
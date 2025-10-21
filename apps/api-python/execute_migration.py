import asyncio
import sys
import os
sys.path.insert(0, '/home/globalauto/global/apps/api-python')

# Importar depois de adicionar ao path
import asyncpg
from dotenv import load_dotenv

load_dotenv()

async def execute_migration():
    """Execute admin migration directly"""
    try:
        # Get database URL and clean it for asyncpg
        db_url = os.getenv('DATABASE_URL')
        if not db_url:
            print("❌ DATABASE_URL not found in environment")
            return False
            
        # Remove +asyncpg suffix if present
        db_url_clean = db_url.replace('postgresql+asyncpg://', 'postgresql://')
        
        print("🔄 Connecting to database...")
        conn = await asyncpg.connect(db_url_clean)
        
        print("📖 Reading migration file...")
        with open('migrations/create_admin_system.sql', 'r') as f:
            sql_content = f.read()
        
        print("⚡ Executing migration...")
        
        # Execute the entire SQL as a single transaction
        await conn.execute(sql_content)
        
        print("\n✅ Migration executed successfully!")
        print("👤 Super admin: demo@tradingplatform.com")
        print("🔑 Password: same as demo user")
        
        await conn.close()
        return True
        
    except Exception as e:
        print(f"\n❌ Error executing migration: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(execute_migration())
    sys.exit(0 if success else 1)

import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

async def check_tables():
    # Fix DSN for asyncpg (remove +asyncpg suffix)
    dsn = os.getenv('DATABASE_URL').replace('postgresql+asyncpg://', 'postgresql://')
    conn = await asyncpg.connect(dsn)
    
    print("=" * 80)
    print("🔍 VERIFICANDO TABELA 'orders'")
    print("=" * 80)
    
    # Verificar se tabela orders existe
    orders_exists = await conn.fetchval("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_name = 'orders'
        )
    """)
    print(f"✅ Tabela 'orders' existe: {orders_exists}")
    
    if orders_exists:
        # Estrutura da tabela orders
        orders_columns = await conn.fetch("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'orders'
            ORDER BY ordinal_position
        """)
        print(f"\n📋 Estrutura da tabela 'orders' ({len(orders_columns)} colunas):")
        for col in orders_columns:
            print(f"  - {col['column_name']}: {col['data_type']} (nullable: {col['is_nullable']})")
        
        # Contar registros
        orders_count = await conn.fetchval("SELECT COUNT(*) FROM orders")
        print(f"\n📊 Total de registros em 'orders': {orders_count}")
        
        # Distribuição por side
        side_dist = await conn.fetch("""
            SELECT side, COUNT(*) as count
            FROM orders
            GROUP BY side
            ORDER BY count DESC
        """)
        print(f"\n📊 Distribuição por SIDE:")
        for row in side_dist:
            print(f"  - {row['side'].upper()}: {row['count']} ordens")
        
        # Últimas 5 ordens
        if orders_count > 0:
            recent_orders = await conn.fetch("""
                SELECT id, symbol, side, type, quantity, status, created_at
                FROM orders
                ORDER BY created_at DESC
                LIMIT 5
            """)
            print(f"\n🕐 Últimas 5 ordens em 'orders':")
            for order in recent_orders:
                print(f"  - ID: {order['id']}, {order['symbol']}, {order['side'].upper()}, {order['type']}, Qty: {order['quantity']}, Status: {order['status']}")
    
    print("\n" + "=" * 80)
    print("🔍 VERIFICANDO TABELA 'trading_orders'")
    print("=" * 80)
    
    # Verificar se tabela trading_orders existe
    trading_orders_exists = await conn.fetchval("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_name = 'trading_orders'
        )
    """)
    print(f"✅ Tabela 'trading_orders' existe: {trading_orders_exists}")
    
    if trading_orders_exists:
        # Estrutura da tabela trading_orders
        trading_columns = await conn.fetch("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'trading_orders'
            ORDER BY ordinal_position
        """)
        print(f"\n📋 Estrutura da tabela 'trading_orders' ({len(trading_columns)} colunas):")
        for col in trading_columns:
            print(f"  - {col['column_name']}: {col['data_type']} (nullable: {col['is_nullable']})")
        
        # Contar registros
        trading_count = await conn.fetchval("SELECT COUNT(*) FROM trading_orders")
        print(f"\n📊 Total de registros em 'trading_orders': {trading_count}")
        
        # Distribuição por side
        side_dist = await conn.fetch("""
            SELECT side, COUNT(*) as count
            FROM trading_orders
            GROUP BY side
            ORDER BY count DESC
        """)
        print(f"\n📊 Distribuição por SIDE:")
        for row in side_dist:
            print(f"  - {row['side'].upper()}: {row['count']} ordens")
        
        # Últimas 5 ordens
        if trading_count > 0:
            recent_trading = await conn.fetch("""
                SELECT id, symbol, side, order_type, quantity, status, created_at
                FROM trading_orders
                ORDER BY created_at DESC
                LIMIT 5
            """)
            print(f"\n🕐 Últimas 5 ordens em 'trading_orders':")
            for order in recent_trading:
                print(f"  - ID: {order['id']}, {order['symbol']}, {order['side'].upper()}, {order['order_type']}, Qty: {order['quantity']}, Status: {order['status']}")
    
    await conn.close()

asyncio.run(check_tables())

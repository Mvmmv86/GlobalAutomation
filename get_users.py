import asyncio
import asyncpg

async def get_users():
    conn = await asyncpg.connect(
        'postgresql://postgres.zmdqmrugotfftxvrwdsd:Wzg0kBvtrSbclQ9V@aws-1-us-east-2.pooler.supabase.com:6543/postgres'
    )
    
    rows = await conn.fetch('SELECT email, name, is_active FROM users LIMIT 5')
    
    print('\n=== USUÁRIOS NO SISTEMA ===')
    for row in rows:
        print(f'Email: {row["email"]}')
        print(f'Nome: {row["name"]}')
        print(f'Ativo: {row["is_active"]}')
        print('---')
    
    await conn.close()

asyncio.run(get_users())

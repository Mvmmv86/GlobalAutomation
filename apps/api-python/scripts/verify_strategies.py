#!/usr/bin/env python3
import asyncio
import os
from dotenv import load_dotenv
import asyncpg
import ssl

load_dotenv()

async def verify():
    database_url = os.getenv('DATABASE_URL').replace('postgresql+asyncpg://', 'postgresql://')
    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE

    conn = await asyncpg.connect(database_url, ssl=ssl_ctx)

    strategies = await conn.fetch('SELECT id, name, timeframe, symbols FROM strategies ORDER BY created_at')
    print(f'Total estratégias: {len(strategies)}')
    print()

    for s in strategies:
        print(f'Nome: {s["name"]}')
        print(f'Timeframe: {s["timeframe"]}')
        print(f'Símbolos: {s["symbols"]}')

        inds = await conn.fetch('SELECT indicator_type FROM strategy_indicators WHERE strategy_id = $1', s['id'])
        print(f'Indicadores: {[i[0] for i in inds]}')

        conds = await conn.fetch('SELECT condition_type FROM strategy_conditions WHERE strategy_id = $1', s['id'])
        print(f'Condições: {[c[0] for c in conds]}')
        print('-' * 50)

    await conn.close()

if __name__ == '__main__':
    asyncio.run(verify())

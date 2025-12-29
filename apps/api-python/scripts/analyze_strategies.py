#!/usr/bin/env python3
import asyncio
import os
import json
from dotenv import load_dotenv
import asyncpg
import ssl

load_dotenv()

async def analyze():
    database_url = os.getenv('DATABASE_URL').replace('postgresql+asyncpg://', 'postgresql://')
    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE

    conn = await asyncpg.connect(database_url, ssl=ssl_ctx)

    strategies = await conn.fetch('SELECT id, name, description, timeframe, symbols FROM strategies ORDER BY created_at')

    for s in strategies:
        print('=' * 70)
        print(f'ESTRATÉGIA: {s["name"]}')
        print(f'Descrição: {s["description"]}')
        print(f'Timeframe: {s["timeframe"]}')
        print(f'Símbolos: {s["symbols"]}')
        print()

        # Indicadores com parâmetros
        inds = await conn.fetch('SELECT indicator_type, parameters FROM strategy_indicators WHERE strategy_id = $1 ORDER BY order_index', s['id'])
        print('INDICADORES:')
        for i in inds:
            print(f'  - {i[0]}: {i[1]}')
        print()

        # Condições
        conds = await conn.fetch('SELECT condition_type, conditions, logic_operator FROM strategy_conditions WHERE strategy_id = $1 ORDER BY order_index', s['id'])
        print('CONDIÇÕES:')
        for c in conds:
            print(f'  {c[0]} ({c[2]}):')
            conditions = c[1] if isinstance(c[1], list) else json.loads(c[1]) if c[1] else []
            for rule in conditions:
                print(f'    - {rule}')
        print()

    await conn.close()

if __name__ == '__main__':
    asyncio.run(analyze())

#!/usr/bin/env python3
"""Script para verificar posições fechadas no banco"""

import asyncio
from infrastructure.database.connection_transaction_mode import transaction_db
from datetime import datetime

async def show_closed_positions():
    await transaction_db.connect()

    try:
        # Buscar posições fechadas
        closed_positions = await transaction_db.fetch("""
            SELECT
                p.symbol,
                p.side,
                p.size as quantity,
                p.entry_price,
                p.mark_price,
                p.realized_pnl,
                p.unrealized_pnl,
                p.status,
                p.opened_at,
                p.closed_at,
                ea.name as account_name
            FROM positions p
            JOIN exchange_accounts ea ON p.exchange_account_id = ea.id
            WHERE p.status = 'closed'
            ORDER BY p.closed_at DESC
            LIMIT 20
        """)

        if closed_positions:
            print(f'\n📊 POSIÇÕES FECHADAS ENCONTRADAS: {len(closed_positions)}\n')
            print('=' * 80)

            for pos in closed_positions:
                pnl = pos['realized_pnl'] or pos['unrealized_pnl'] or 0
                pnl_emoji = '🟢' if pnl > 0 else '🔴' if pnl < 0 else '⚪'

                print(f'\n{pnl_emoji} {pos["symbol"]} ({pos["side"].upper()})')
                print(f'   Quantidade: {pos["quantity"]:.4f}')
                print(f'   Entrada: ${pos["entry_price"]:.2f}')
                print(f'   Mark Price: ${pos["mark_price"]:.2f}' if pos['mark_price'] else '   Mark Price: N/A')
                print(f'   P&L: ${pnl:.2f}')
                print(f'   Abertura: {pos["opened_at"]}')
                print(f'   Fechamento: {pos["closed_at"]}')
                print(f'   Conta: {pos["account_name"]}')
        else:
            print('\n❌ NENHUMA POSIÇÃO FECHADA encontrada no banco!')
            print('\nIsso significa que:')
            print('1. Você não fechou nenhuma posição ainda')
            print('2. Ou as posições fechadas ainda não foram detectadas')
            print('\nO detector roda a cada 5 minutos no minuto 0, 5, 10, 15...')

        # Verificar posições abertas também
        open_positions = await transaction_db.fetch("""
            SELECT COUNT(*) as count
            FROM positions
            WHERE status = 'open'
        """)

        print(f'\n📈 Posições ABERTAS no momento: {open_positions[0]["count"]}')

        # Verificar total de posições
        all_positions = await transaction_db.fetch("""
            SELECT
                status,
                COUNT(*) as count
            FROM positions
            GROUP BY status
        """)

        print('\n📊 RESUMO GERAL:')
        for row in all_positions:
            print(f'   {row["status"].upper()}: {row["count"]} posições')

    finally:
        await transaction_db.disconnect()

if __name__ == "__main__":
    asyncio.run(show_closed_positions())
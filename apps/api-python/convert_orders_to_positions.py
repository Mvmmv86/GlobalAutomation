#!/usr/bin/env python3
"""
Converter ordens FILLED em posições fechadas
Agrupa ordens do mesmo símbolo para formar posições completas
"""

import asyncio
from datetime import datetime
from infrastructure.database.connection_transaction_mode import transaction_db
from collections import defaultdict

async def convert_orders_to_closed_positions():
    """Convert FILLED orders to closed positions"""

    print("🔄 Convertendo ordens FILLED em posições fechadas...")
    print("=" * 60)

    await transaction_db.connect()

    try:
        account_id = "0bad440b-f800-46ff-812f-5c359969885e"

        # 1. Buscar todas as ordens FILLED
        filled_orders = await transaction_db.fetch("""
            SELECT
                id, symbol, side, quantity, price, average_price,
                created_at, updated_at, exchange_order_id
            FROM trading_orders
            WHERE status = 'filled'
                AND exchange_account_id = $1
            ORDER BY symbol, created_at
        """, account_id)

        print(f"\n📊 Total de ordens FILLED encontradas: {len(filled_orders)}")

        # 2. Agrupar por símbolo
        orders_by_symbol = defaultdict(list)
        for order in filled_orders:
            orders_by_symbol[order['symbol']].append(order)

        print(f"📈 Símbolos únicos: {len(orders_by_symbol)}")

        # 3. Para cada símbolo, identificar posições
        new_positions = []

        for symbol, orders in orders_by_symbol.items():
            print(f"\n🔍 Analisando {symbol}: {len(orders)} ordens")

            # Separar BUY e SELL
            buy_orders = [o for o in orders if o['side'].upper() == 'BUY']
            sell_orders = [o for o in orders if o['side'].upper() == 'SELL']

            print(f"   BUY: {len(buy_orders)}, SELL: {len(sell_orders)}")

            # Estratégia: Parear ordens BUY e SELL sequencialmente
            # Uma posição LONG: BUY (abre) → SELL (fecha)
            # Uma posição SHORT: SELL (abre) → BUY (fecha)

            i, j = 0, 0
            position_count = 0

            while i < len(buy_orders) or j < len(sell_orders):
                # Determinar qual ordem veio primeiro
                if i < len(buy_orders) and j < len(sell_orders):
                    if buy_orders[i]['created_at'] < sell_orders[j]['created_at']:
                        # BUY primeiro = posição LONG
                        opening_order = buy_orders[i]
                        closing_order = sell_orders[j] if j < len(sell_orders) else None
                        side = 'long'
                        i += 1
                        if closing_order:
                            j += 1
                    else:
                        # SELL primeiro = posição SHORT
                        opening_order = sell_orders[j]
                        closing_order = buy_orders[i] if i < len(buy_orders) else None
                        side = 'short'
                        j += 1
                        if closing_order:
                            i += 1
                elif i < len(buy_orders):
                    # Só tem BUY restante - posição aberta LONG
                    opening_order = buy_orders[i]
                    closing_order = None
                    side = 'long'
                    i += 1
                else:
                    # Só tem SELL restante - posição aberta SHORT
                    opening_order = sell_orders[j]
                    closing_order = None
                    side = 'short'
                    j += 1

                # Criar posição
                quantity = float(opening_order['quantity'])
                entry_price = float(opening_order['average_price'] or opening_order['price'])

                if closing_order:
                    # Posição fechada
                    exit_price = float(closing_order['average_price'] or closing_order['price'])

                    # Calcular P&L
                    if side == 'long':
                        pnl = (exit_price - entry_price) * quantity
                    else:
                        pnl = (entry_price - exit_price) * quantity

                    position = {
                        'symbol': symbol,
                        'side': side,
                        'quantity': quantity,
                        'entry_price': entry_price,
                        'exit_price': exit_price,
                        'pnl': pnl,
                        'opened_at': opening_order['created_at'],
                        'closed_at': closing_order['created_at'],
                        'status': 'closed'
                    }

                    new_positions.append(position)
                    position_count += 1
                    print(f"   ✅ Posição {position_count} ({side.upper()}): P&L ${pnl:.2f}")

        print(f"\n\n📊 Total de posições identificadas: {len(new_positions)}")

        # 4. Inserir posições no banco
        inserted = 0
        skipped = 0

        for pos in new_positions:
            # Verificar se já existe
            existing = await transaction_db.fetchrow("""
                SELECT id FROM positions
                WHERE symbol = $1
                    AND exchange_account_id = $2
                    AND opened_at = $3
                    AND side = $4
            """, pos['symbol'], account_id, pos['opened_at'], pos['side'])

            if not existing:
                await transaction_db.execute("""
                    INSERT INTO positions (
                        symbol, side, size, entry_price, exit_price,
                        unrealized_pnl, realized_pnl, status,
                        opened_at, closed_at, exchange_account_id,
                        created_at, updated_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                """,
                    pos['symbol'], pos['side'], pos['quantity'],
                    pos['entry_price'], pos['exit_price'],
                    pos['pnl'], pos['pnl'], pos['status'],
                    pos['opened_at'], pos['closed_at'],
                    account_id,
                    datetime.now(), datetime.now()
                )
                inserted += 1
            else:
                skipped += 1

        print(f"\n✅ Conversão concluída:")
        print(f"   Inseridas: {inserted}")
        print(f"   Já existentes: {skipped}")

        # 5. Verificar total de posições
        total_positions = await transaction_db.fetchval("""
            SELECT COUNT(*) FROM positions
            WHERE exchange_account_id = $1
        """, account_id)

        print(f"\n📊 Total de posições no banco agora: {total_positions}")

    except Exception as e:
        print(f"\n❌ Erro: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await transaction_db.disconnect()

    print("\n" + "=" * 60)
    print("✅ Processo finalizado!")

if __name__ == "__main__":
    asyncio.run(convert_orders_to_closed_positions())
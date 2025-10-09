#!/usr/bin/env python3
"""Script to sync closed positions from Binance trade history"""

import asyncio
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from infrastructure.exchanges.binance_connector import BinanceConnector
from infrastructure.database.connection_transaction_mode import transaction_db
import structlog

load_dotenv()

logger = structlog.get_logger(__name__)

async def sync_closed_positions_from_trades():
    """Sync closed positions from Binance trade history"""

    account_id = "0bad440b-f800-46ff-812f-5c359969885e"

    print("🔍 Sincronizando posições fechadas da Binance...")
    print("=" * 60)

    # Initialize database connection
    await transaction_db.connect()

    try:
        # Get account from database
        account = await transaction_db.fetchrow("""
            SELECT id, api_key, secret_key, testnet
            FROM exchange_accounts
            WHERE id = $1 AND is_active = true
        """, account_id)

        if not account:
            print("❌ Conta não encontrada!")
            return

        # Decrypt credentials
        from infrastructure.security.encryption_service import EncryptionService
        encryption = EncryptionService()

        api_key = encryption.decrypt_string(account['api_key'])
        api_secret = encryption.decrypt_string(account['secret_key'])
        testnet = account['testnet']

        # Create connector
        connector = BinanceConnector(api_key, api_secret, testnet=False)

        # Get all futures orders from last 90 days
        print("\n📊 Buscando histórico de ordens FUTURES (últimos 90 dias)...")

        end_time = int(datetime.now().timestamp() * 1000)
        start_time = int((datetime.now() - timedelta(days=90)).timestamp() * 1000)

        # Buscar todas as ordens FILLED (preenchidas)
        orders_result = await connector.get_account_orders(
            limit=500,  # Máximo permitido
            start_time=start_time,
            end_time=end_time
        )

        if not orders_result.get('success'):
            print(f"❌ Erro ao buscar ordens: {orders_result.get('error')}")
            return

        orders = orders_result.get('orders', [])
        print(f"✅ Total de ordens encontradas: {len(orders)}")

        # Filtrar apenas ordens FILLED (executadas)
        filled_orders = [o for o in orders if o.get('status') == 'FILLED']
        print(f"📈 Ordens executadas: {len(filled_orders)}")

        # Agrupar ordens por símbolo para identificar posições
        positions_by_symbol = {}

        for order in filled_orders:
            symbol = order.get('symbol')
            if not symbol:
                continue

            if symbol not in positions_by_symbol:
                positions_by_symbol[symbol] = {
                    'buy_orders': [],
                    'sell_orders': [],
                    'trades': []
                }

            side = order.get('side', '').upper()
            if side == 'BUY':
                positions_by_symbol[symbol]['buy_orders'].append(order)
            elif side == 'SELL':
                positions_by_symbol[symbol]['sell_orders'].append(order)

        print(f"\n📊 Símbolos negociados: {len(positions_by_symbol)}")

        # Para cada símbolo, identificar posições fechadas
        closed_positions = []

        for symbol, data in positions_by_symbol.items():
            buy_orders = sorted(data['buy_orders'], key=lambda x: x.get('time', 0))
            sell_orders = sorted(data['sell_orders'], key=lambda x: x.get('time', 0))

            # Simplificação: considerar cada par buy/sell como uma posição
            # (Na prática, isso é mais complexo e requer análise de volumes)

            total_buy_qty = sum(float(o.get('executedQty', 0)) for o in buy_orders)
            total_sell_qty = sum(float(o.get('executedQty', 0)) for o in sell_orders)

            if buy_orders and sell_orders:
                # Há trades em ambas direções - possível posição fechada
                avg_buy_price = sum(float(o.get('price', 0)) * float(o.get('executedQty', 0)) for o in buy_orders) / max(total_buy_qty, 0.000001)
                avg_sell_price = sum(float(o.get('price', 0)) * float(o.get('executedQty', 0)) for o in sell_orders) / max(total_sell_qty, 0.000001)

                # Determinar se a posição foi LONG ou SHORT baseado na ordem inicial
                first_order = buy_orders[0] if buy_orders[0].get('time', 0) < sell_orders[0].get('time', 0) else sell_orders[0]
                is_long = first_order.get('side') == 'BUY'

                # Quantidade da posição (mínimo entre buys e sells)
                position_qty = min(total_buy_qty, total_sell_qty)

                if position_qty > 0:
                    # Calcular P&L
                    if is_long:
                        pnl = (avg_sell_price - avg_buy_price) * position_qty
                        entry_price = avg_buy_price
                        exit_price = avg_sell_price
                    else:
                        pnl = (avg_buy_price - avg_sell_price) * position_qty
                        entry_price = avg_sell_price
                        exit_price = avg_buy_price

                    # Data de abertura e fechamento
                    open_time = min(buy_orders[0].get('time', 0), sell_orders[0].get('time', 0))
                    close_time = max(buy_orders[-1].get('time', 0), sell_orders[-1].get('time', 0))

                    closed_positions.append({
                        'symbol': symbol,
                        'side': 'LONG' if is_long else 'SHORT',
                        'quantity': position_qty,
                        'entry_price': entry_price,
                        'exit_price': exit_price,
                        'pnl': pnl,
                        'opened_at': datetime.fromtimestamp(open_time / 1000),
                        'closed_at': datetime.fromtimestamp(close_time / 1000)
                    })

        print(f"\n✅ Posições fechadas identificadas: {len(closed_positions)}")

        # Inserir posições fechadas no banco de dados
        inserted = 0
        updated = 0

        for pos in closed_positions:
            print(f"\n📊 {pos['symbol']} ({pos['side']})")
            print(f"   Qtd: {pos['quantity']:.4f}")
            print(f"   Entrada: ${pos['entry_price']:.2f}")
            print(f"   Saída: ${pos['exit_price']:.2f}")
            print(f"   P&L: ${pos['pnl']:.2f}")
            print(f"   Abertura: {pos['opened_at']}")
            print(f"   Fechamento: {pos['closed_at']}")

            # Verificar se já existe
            existing = await transaction_db.fetchrow("""
                SELECT id FROM positions
                WHERE symbol = $1
                    AND exchange_account_id = $2
                    AND opened_at >= $3 AND opened_at <= $4
                    AND status = 'closed'
            """, pos['symbol'], account_id,
                pos['opened_at'] - timedelta(hours=1),
                pos['opened_at'] + timedelta(hours=1))

            if not existing:
                # Inserir nova posição fechada
                await transaction_db.execute("""
                    INSERT INTO positions (
                        symbol, side, size, entry_price, exit_price,
                        unrealized_pnl, realized_pnl, status,
                        opened_at, closed_at, exchange_account_id,
                        created_at, updated_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                """,
                    pos['symbol'],
                    pos['side'].lower(),
                    pos['quantity'],
                    pos['entry_price'],
                    pos['exit_price'],
                    pos['pnl'],  # unrealized_pnl
                    pos['pnl'],  # realized_pnl
                    'closed',
                    pos['opened_at'],
                    pos['closed_at'],
                    account_id,
                    datetime.now(),
                    datetime.now()
                )
                inserted += 1
                print("   ✅ Inserida no banco!")
            else:
                updated += 1
                print("   ⚠️ Já existe no banco")

        print(f"\n📊 Resumo da sincronização:")
        print(f"   Inseridas: {inserted}")
        print(f"   Já existentes: {updated}")
        print(f"   Total processadas: {len(closed_positions)}")

    except Exception as e:
        print(f"\n❌ Erro: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Close database connection
        await transaction_db.disconnect()

    print("\n" + "=" * 60)
    print("✅ Sincronização concluída!")

if __name__ == "__main__":
    asyncio.run(sync_closed_positions_from_trades())
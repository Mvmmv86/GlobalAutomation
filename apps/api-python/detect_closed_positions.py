#!/usr/bin/env python3
"""
Script SEGURO para detectar posições fechadas
NÃO modifica nada existente, apenas atualiza status de posições
Funciona para TODAS as exchanges configuradas
"""

import asyncio
from datetime import datetime
from infrastructure.database.connection_transaction_mode import transaction_db
from infrastructure.exchanges.binance_connector import BinanceConnector
from infrastructure.exchanges.bybit_connector import BybitConnector
from infrastructure.exchanges.bingx_connector import BingXConnector
from infrastructure.exchanges.bitget_connector import BitgetConnector
from infrastructure.security.encryption_service import EncryptionService
import structlog

logger = structlog.get_logger(__name__)

async def detect_closed_positions():
    """
    Detecta posições que foram fechadas comparando:
    1. Posições abertas no banco
    2. Posições reais na exchange
    """

    print("🔍 Detector de Posições Fechadas - MODO SEGURO")
    print("=" * 60)
    print("✅ Este script NÃO modifica código existente")
    print("✅ Apenas detecta e marca posições fechadas")
    print("=" * 60)

    await transaction_db.connect()
    encryption = EncryptionService()

    try:
        # 1. Buscar TODAS as contas ativas (multi-exchange)
        accounts = await transaction_db.fetch("""
            SELECT
                id, name, exchange,
                api_key, secret_key, passphrase, testnet
            FROM exchange_accounts
            WHERE is_active = true
        """)

        print(f"\n📊 Contas encontradas: {len(accounts)}")

        total_detected = 0

        for account in accounts:
            try:
                account_id = account['id']
                exchange = account['exchange'].lower()

                print(f"\n🏦 Processando {account['name']} ({exchange})...")

                # 2. Buscar posições "abertas" no banco para esta conta
                db_positions = await transaction_db.fetch("""
                    SELECT id, symbol, side, size, entry_price
                    FROM positions
                    WHERE exchange_account_id = $1
                        AND status = 'open'
                """, account_id)

                if not db_positions:
                    print(f"   Nenhuma posição aberta no banco")
                    continue

                print(f"   📋 Posições no banco: {len(db_positions)}")

                # 3. Criar connector apropriado para a exchange
                try:
                    # Descriptografar credenciais
                    api_key = encryption.decrypt_string(account['api_key'])
                    api_secret = encryption.decrypt_string(account['secret_key'])
                    passphrase = None
                    if account['passphrase']:
                        passphrase = encryption.decrypt_string(account['passphrase'])
                except:
                    # Se falhar, tentar usar como texto plano
                    api_key = account['api_key']
                    api_secret = account['secret_key']
                    passphrase = account['passphrase']

                # Criar connector baseado na exchange
                if exchange == 'binance':
                    connector = BinanceConnector(api_key, api_secret, testnet=account['testnet'])
                elif exchange == 'bybit':
                    connector = BybitConnector(api_key, api_secret, testnet=account['testnet'])
                elif exchange == 'bingx':
                    connector = BingXConnector(api_key, api_secret, testnet=account['testnet'])
                elif exchange == 'bitget':
                    connector = BitgetConnector(api_key, api_secret, passphrase, testnet=account['testnet'])
                else:
                    print(f"   ⚠️ Exchange {exchange} não suportada")
                    continue

                # 4. Buscar posições reais na exchange
                positions_result = await connector.get_futures_positions()

                if not positions_result.get('success'):
                    print(f"   ❌ Erro ao buscar posições: {positions_result.get('error')}")
                    continue

                exchange_positions = positions_result.get('positions', [])
                print(f"   📡 Posições na exchange: {len(exchange_positions)}")

                # 5. Criar set de símbolos ainda abertos na exchange
                open_symbols = set()
                for pos in exchange_positions:
                    symbol = pos.get('symbol', '').replace('-', '')
                    if symbol and float(pos.get('size', pos.get('positionAmt', 0))) != 0:
                        open_symbols.add(symbol)

                # 6. Detectar posições que foram fechadas
                for db_pos in db_positions:
                    if db_pos['symbol'] not in open_symbols:
                        # Esta posição foi fechada!
                        print(f"\n   🔴 DETECTADO FECHAMENTO: {db_pos['symbol']}")
                        print(f"      Side: {db_pos['side'].upper()}")
                        print(f"      Size: {db_pos['size']}")

                        # 7. Atualizar status para 'closed' no banco
                        # Calcular P&L estimado (será refinado depois)
                        # Por ora, apenas marcar como fechada

                        await transaction_db.execute("""
                            UPDATE positions
                            SET
                                status = 'closed',
                                closed_at = $1,
                                updated_at = $1,
                                last_update_at = $1
                            WHERE id = $2
                        """, datetime.now(), db_pos['id'])

                        total_detected += 1
                        print(f"      ✅ Marcada como FECHADA")

                        # Notificar via WebSocket (se disponível)
                        try:
                            from presentation.controllers.websocket_controller import notify_position_update
                            await notify_position_update(
                                action='position_closed',
                                position_id=db_pos['id'],
                                symbol=db_pos['symbol'],
                                side=db_pos['side']
                            )
                        except:
                            pass  # WebSocket é opcional

            except Exception as e:
                print(f"   ❌ Erro processando conta: {e}")
                continue

        print(f"\n" + "=" * 60)
        print(f"✅ Total de posições fechadas detectadas: {total_detected}")

        if total_detected > 0:
            print("📊 As posições agora aparecerão na aba 'Fechadas'!")

    except Exception as e:
        print(f"\n❌ Erro geral: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await transaction_db.disconnect()

    return total_detected

async def main():
    """Função principal - pode rodar standalone ou ser chamada"""
    detected = await detect_closed_positions()
    return detected

if __name__ == "__main__":
    # Rodar manualmente
    print("\n🚀 Iniciando detector de posições fechadas...")
    asyncio.run(main())
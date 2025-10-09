"""SL/TP Update Controller - Endpoint para modificar Stop Loss e Take Profit"""

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from decimal import Decimal
from datetime import datetime
from typing import Optional
import structlog
import uuid
import asyncio
import json

from infrastructure.database.connection_transaction_mode import transaction_db
from infrastructure.exchanges.binance_connector import BinanceConnector
from infrastructure.cache.idempotency_cache import check_idempotency, cache_response
from binance.exceptions import BinanceAPIException

logger = structlog.get_logger(__name__)

router = APIRouter()


class UpdateSLTPRequest(BaseModel):
    """Request para atualizar SL/TP"""
    position_id: str
    type: str  # 'stopLoss' ou 'takeProfit'
    price: float


@router.patch("/positions/{position_id}/sltp")
async def update_position_sltp(
    position_id: str,
    update_data: UpdateSLTPRequest,
    x_idempotency_key: Optional[str] = Header(None)
):
    """
    Atualiza Stop Loss ou Take Profit de uma posição existente

    Este endpoint:
    1. Verifica idempotência (previne duplicação)
    2. Busca a posição e suas credenciais
    3. Cancela a ordem SL/TP antiga na Binance (se existir)
    4. Cria uma nova ordem SL/TP com o novo preço
    5. Atualiza o banco de dados
    6. Cacheia resultado (para idempotência)

    Headers opcionais:
    - X-Idempotency-Key: Previne processamento duplicado de mesma requisição
    """
    logger.info(f"📝 Atualizando SL/TP da posição {position_id}")
    logger.info(f"📊 Tipo: {update_data.type}, Novo preço: ${update_data.price}")

    # ✅ IDEMPOTÊNCIA: Verificar se esta requisição já foi processada
    if x_idempotency_key:
        cached_response = await check_idempotency(x_idempotency_key)
        if cached_response:
            logger.info(f"✅ Retornando resposta cacheada para idempotency_key: {x_idempotency_key}")
            return cached_response

    try:
        # 1. Buscar a posição no banco
        position = await transaction_db.fetchrow("""
            SELECT
                p.*,
                ea.api_key,
                ea.secret_key,
                ea.testnet
            FROM positions p
            JOIN exchange_accounts ea ON p.exchange_account_id = ea.id
            WHERE p.id = $1
        """, position_id)

        if not position:
            raise HTTPException(status_code=404, detail="Posição não encontrada")

        logger.info(f"✅ Posição encontrada: {position['symbol']} {position['side']}")

        # 2. Criar connector da Binance
        connector = BinanceConnector(
            api_key=position['api_key'],
            api_secret=position['secret_key'],
            testnet=position['testnet']
        )

        # 3. Determinar parâmetros
        order_type = update_data.type  # 'stopLoss' ou 'takeProfit'
        new_price = update_data.price

        logger.info(f"🎯 Modificando {order_type} para ${new_price}")

        # 4. Buscar ordem SL/TP existente no banco
        sl_tp_prefix = 'sl' if order_type == 'stopLoss' else 'tp'

        existing_order = await transaction_db.fetchrow("""
            SELECT id, external_id
            FROM orders
            WHERE symbol = $1
              AND client_order_id LIKE $2
              AND status IN ('pending', 'submitted', 'open')
            ORDER BY created_at DESC
            LIMIT 1
        """, position['symbol'], f"{sl_tp_prefix}_%")

        # 5. Cancelar ordem antiga se existir
        if existing_order and existing_order['external_id']:
            logger.info(f"🗑️ Cancelando ordem antiga: {existing_order['external_id']}")

            try:
                await asyncio.to_thread(
                    connector.client.futures_cancel_order,
                    symbol=position['symbol'].upper(),
                    orderId=existing_order['external_id']
                )

                # Marcar ordem como cancelada no banco
                await transaction_db.execute("""
                    UPDATE orders
                    SET status = 'canceled',
                        updated_at = $1
                    WHERE id = $2
                """, datetime.utcnow(), existing_order['id'])

                logger.info(f"✅ Ordem antiga cancelada")

            except BinanceAPIException as e:
                if 'Unknown order' in str(e):
                    logger.warning(f"⚠️ Ordem já não existe na Binance: {existing_order['external_id']}")
                    # Marcar como cancelada mesmo assim
                    await transaction_db.execute("""
                        UPDATE orders SET status = 'canceled', updated_at = $1 WHERE id = $2
                    """, datetime.utcnow(), existing_order['id'])
                else:
                    raise

        # 6. Arredondar preço para precisão correta da Binance
        # BTCUSDT: 1 decimal, ETHUSDT: 2 decimais, outros: 2 decimais
        symbol = position['symbol'].upper()
        if 'BTC' in symbol:
            rounded_price = round(new_price, 1)
        elif 'ETH' in symbol:
            rounded_price = round(new_price, 2)
        else:
            rounded_price = round(new_price, 2)

        logger.info(f"📝 Criando nova ordem {order_type} @ ${rounded_price} (original: ${new_price})")

        # 7. Criar nova ordem SL/TP na Binance
        side = 'SELL' if position['side'] == 'long' else 'BUY'

        if order_type == 'stopLoss':
            order_params = {
                'symbol': position['symbol'].upper(),
                'side': side,
                'type': 'STOP_MARKET',
                'stopPrice': rounded_price,
                'closePosition': 'true'
            }
        else:  # takeProfit
            order_params = {
                'symbol': position['symbol'].upper(),
                'side': side,
                'type': 'TAKE_PROFIT_MARKET',
                'stopPrice': rounded_price,
                'closePosition': 'true'
            }

        logger.info(f"🎯 Parâmetros da ordem: {order_params}")

        order_result = await asyncio.to_thread(
            connector.client.futures_create_order,
            **order_params
        )

        new_order_id = str(order_result.get('orderId'))
        logger.info(f"✅ Nova ordem criada na Binance: {new_order_id}")

        # 7. Salvar nova ordem no banco
        client_order_id = f"{sl_tp_prefix}_{uuid.uuid4().hex[:16]}"

        db_order_id = await transaction_db.fetchval("""
            INSERT INTO orders (
                client_order_id,
                source,
                exchange_account_id,
                external_id,
                symbol,
                side,
                type,
                status,
                quantity,
                stop_price,
                filled_quantity,
                fees_paid,
                time_in_force,
                retry_count,
                reduce_only,
                post_only,
                created_at,
                updated_at
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $17)
            RETURNING id
        """,
            client_order_id,
            'PLATFORM',
            position['exchange_account_id'],
            new_order_id,
            position['symbol'],
            side.lower(),
            'market',  # Compatibilidade com enum
            'submitted',
            Decimal(str(position['size'])),
            Decimal(str(new_price)),
            Decimal('0'),
            Decimal('0'),
            'gtc',
            0,
            True,  # reduce_only
            False,
            datetime.utcnow()
        )

        logger.info(f"✅ Nova ordem salva no banco: {db_order_id}")

        # Preparar resposta
        response = {
            "success": True,
            "message": f"{order_type} atualizado com sucesso",
            "order_id": new_order_id,
            "new_price": rounded_price
        }

        # ✅ IDEMPOTÊNCIA: Cachear resposta para prevenir duplicação
        if x_idempotency_key:
            await cache_response(x_idempotency_key, response, ttl=60)
            logger.info(f"✅ Resposta cacheada para idempotency_key: {x_idempotency_key}")

        return response

    except BinanceAPIException as e:
        logger.error(f"❌ Erro da API Binance: {e}")
        raise HTTPException(status_code=400, detail=f"Erro da Binance: {e.message}")
    except Exception as e:
        logger.error(f"❌ Erro ao atualizar SL/TP: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

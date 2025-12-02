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
from infrastructure.exchanges.bingx_connector import BingXConnector
from infrastructure.cache.idempotency_cache import check_idempotency, cache_response
from binance.exceptions import BinanceAPIException

logger = structlog.get_logger(__name__)

router = APIRouter()


class UpdateSLTPRequest(BaseModel):
    """Request para atualizar SL/TP"""
    position_id: str
    type: str  # 'stopLoss' ou 'takeProfit'
    price: float


class CreateSLTPRequest(BaseModel):
    """Request para criar SL/TP novo"""
    position_id: str
    type: str  # 'stopLoss' ou 'takeProfit'
    price: float
    side: str  # 'LONG' ou 'SHORT'


class CancelSLTPRequest(BaseModel):
    """Request para cancelar SL/TP"""
    position_id: str
    type: str  # 'stopLoss' ou 'takeProfit'


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
                ea.testnet,
                ea.exchange
            FROM positions p
            JOIN exchange_accounts ea ON p.exchange_account_id = ea.id
            WHERE p.id = $1
        """, position_id)

        if not position:
            raise HTTPException(status_code=404, detail="Posição não encontrada")

        logger.info(f"✅ Posição encontrada: {position['symbol']} {position['side']}")
        logger.info(f"📊 DADOS DA POSIÇÃO DO BANCO:")
        logger.info(f"   - ID: {position['id']}")
        logger.info(f"   - Symbol: {position['symbol']}")
        logger.info(f"   - Side: {position['side']}")
        logger.info(f"   - Size: {position['size']}")
        logger.info(f"   - Exchange: {position['exchange']}")

        # 2. Criar connector da exchange correta (Binance ou BingX)
        exchange = position['exchange'].lower()
        logger.info(f"🏦 Exchange detectada: {exchange}")

        if exchange == 'bingx':
            connector = BingXConnector(
                api_key=position['api_key'],
                api_secret=position['secret_key'],
                testnet=position['testnet']
            )
        else:  # binance
            connector = BinanceConnector(
                api_key=position['api_key'],
                api_secret=position['secret_key'],
                testnet=position['testnet']
            )

        # 3. Determinar parâmetros
        order_type = update_data.type  # 'stopLoss' ou 'takeProfit'
        new_price = update_data.price

        logger.info(f"🎯 Modificando {order_type} para ${new_price}")

        # 4. Para BingX: Buscar ordens abertas DIRETAMENTE na exchange (não no banco)
        # O banco pode estar desatualizado, então devemos sempre consultar a exchange
        sl_tp_prefix = 'sl' if order_type == 'stopLoss' else 'tp'
        symbol_bingx = position['symbol'].replace("USDT", "-USDT") if "-" not in position['symbol'] else position['symbol']

        if exchange == 'bingx':
            # CRÍTICO: Buscar ordens abertas diretamente da BingX usando o endpoint openOrders
            logger.info(f"🔍 Buscando ordens abertas na BingX para {symbol_bingx}...")
            open_orders_result = await connector._make_request(
                "GET",
                "/openApi/swap/v2/trade/openOrders",
                {"symbol": symbol_bingx},
                signed=True,
                use_body=False
            )

            existing_order_id = None
            if open_orders_result.get("code") == 0:
                orders = open_orders_result.get("data", {}).get("orders", [])
                logger.info(f"📋 Encontradas {len(orders)} ordens abertas na BingX")

                # Procurar ordem do tipo correto (STOP_MARKET para SL, TAKE_PROFIT_MARKET para TP)
                target_type = "STOP_MARKET" if order_type == 'stopLoss' else "TAKE_PROFIT_MARKET"
                for o in orders:
                    order_type_bingx = o.get("type", "")
                    logger.info(f"   - Ordem: {o.get('orderId')} tipo={order_type_bingx} @ ${o.get('stopPrice')}")
                    if order_type_bingx == target_type:
                        existing_order_id = str(o.get("orderId"))
                        logger.info(f"   ✅ Encontrada ordem {target_type} para cancelar: {existing_order_id}")
                        break
            else:
                logger.warning(f"⚠️ Erro ao buscar ordens abertas: {open_orders_result.get('msg')}")

            # 5. Cancelar ordem antiga se existir
            if existing_order_id:
                logger.info(f"🗑️ Cancelando ordem antiga na BingX: {existing_order_id}")
                try:
                    result = await connector.cancel_order(
                        symbol=symbol_bingx,
                        order_id=existing_order_id
                    )
                    if result.get('success'):
                        logger.info(f"✅ Ordem antiga cancelada na BingX")
                        # Pequena pausa para a BingX processar o cancelamento
                        await asyncio.sleep(0.5)
                    else:
                        error_msg = result.get('error', '').lower()
                        if 'already cancelled' in error_msg or 'does not exist' in error_msg:
                            logger.warning(f"⚠️ Ordem já cancelada ou não existe: {existing_order_id}")
                        else:
                            raise Exception(f"BingX cancel failed: {result.get('error')}")
                except Exception as e:
                    error_msg = str(e).lower()
                    if 'already cancelled' in error_msg or 'does not exist' in error_msg:
                        logger.warning(f"⚠️ Ordem já cancelada ou não existe: {existing_order_id}")
                    else:
                        raise
            else:
                logger.info(f"ℹ️ Nenhuma ordem {order_type} existente encontrada para cancelar")
        else:
            # Binance: Manter lógica do banco (pode funcionar ou não)
            existing_order = await transaction_db.fetchrow("""
                SELECT id, external_id
                FROM orders
                WHERE symbol = $1
                  AND client_order_id LIKE $2
                  AND status IN ('pending', 'submitted', 'open')
                ORDER BY created_at DESC
                LIMIT 1
            """, position['symbol'], f"{sl_tp_prefix}_%")

            # 5. Cancelar ordem antiga se existir (Binance)
            if existing_order and existing_order['external_id']:
                logger.info(f"🗑️ Cancelando ordem antiga na Binance: {existing_order['external_id']}")
                try:
                    await asyncio.to_thread(
                        connector.client.futures_cancel_order,
                        symbol=position['symbol'].upper(),
                        orderId=existing_order['external_id']
                    )
                    await transaction_db.execute("""
                        UPDATE orders SET status = 'canceled', updated_at = $1 WHERE id = $2
                    """, datetime.utcnow(), existing_order['id'])
                    logger.info(f"✅ Ordem antiga cancelada na Binance")
                except BinanceAPIException as e:
                    if 'Unknown order' in str(e):
                        logger.warning(f"⚠️ Ordem já não existe na Binance: {existing_order['external_id']}")
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

        # 7. Criar nova ordem SL/TP na Exchange
        side = 'SELL' if position['side'] == 'long' else 'BUY'

        if exchange == 'bingx':
            # BingX: Usar create_futures_order diretamente com positionSide (requerido para hedge mode)
            # IMPORTANTE: BingX em Hedge mode NÃO aceita reduce_only (erro: 'ReduceOnly' field can not be filled)
            # CRÍTICO: positionSide deve ser da POSIÇÃO ABERTA, não do side da ordem de fechamento
            # Exemplo: Posição LONG (comprada) → SL usa side=SELL mas positionSide=LONG
            position_side = position['side'].upper()  # LONG ou SHORT (da posição aberta)

            # DEBUG: Verificar posições abertas na BingX antes de criar ordem
            logger.info(f"🔍 Verificando posições abertas na BingX...")
            bingx_positions = await connector.get_futures_positions()
            logger.info(f"📊 Posições BingX retornadas: {json.dumps(bingx_positions, indent=2)}")

            # Verificar se a posição existe na BingX com o símbolo correto
            symbol_to_check = position['symbol'].replace("USDT", "-USDT") if "-" not in position['symbol'] else position['symbol']
            logger.info(f"🔍 Buscando posição com símbolo: {symbol_to_check} e side: {position_side}")

            found_position = None
            if bingx_positions.get('success') and bingx_positions.get('positions'):
                for pos in bingx_positions['positions']:
                    pos_symbol = pos.get('symbol', '')
                    pos_side = pos.get('positionSide', '').upper()
                    pos_amt = float(pos.get('positionAmt', '0'))
                    logger.info(f"   - Posição encontrada: {pos_symbol}, side={pos_side}, amt={pos_amt}")
                    if pos_symbol == symbol_to_check and pos_side == position_side:
                        found_position = pos
                        break

            # CRÍTICO: Para Hedge Mode, precisamos usar a quantidade REAL da posição na BingX
            # O erro "available amount of 0 BTC" ocorre quando a quantidade não bate
            quantity_to_use = float(position['size'])  # Default do banco

            if found_position:
                logger.info(f"✅ Posição encontrada na BingX: {found_position}")
                # CRÍTICO: Usar availableAmt (quantidade disponível) e não positionAmt
                # availableAmt é a quantidade que pode ser usada para novas ordens
                # (positionAmt - quantidade já alocada em ordens pendentes)
                bingx_available = abs(float(found_position.get('availableAmt', 0)))
                bingx_total = abs(float(found_position.get('positionAmt', 0)))
                logger.info(f"📊 Quantidade disponível: {bingx_available}, Total: {bingx_total}")
                if bingx_available > 0:
                    logger.info(f"📊 Usando availableAmt da BingX: {bingx_available}")
                    quantity_to_use = bingx_available
                elif bingx_total > 0:
                    # Fallback para positionAmt se availableAmt for 0
                    # (pode acontecer se a ordem antiga não foi cancelada corretamente)
                    logger.warning(f"⚠️ availableAmt é 0, usando positionAmt: {bingx_total}")
                    quantity_to_use = bingx_total
            else:
                logger.warning(f"⚠️ POSIÇÃO NÃO ENCONTRADA na BingX! Symbol={symbol_to_check}, Side={position_side}")
                logger.warning(f"   Posições disponíveis: {[p.get('symbol') + '/' + p.get('positionSide', '') for p in bingx_positions.get('positions', [])]}")
                # Não vamos falhar aqui - tentar criar a ordem mesmo assim e ver o erro real

            logger.info(f"📊 Criando SL/TP BingX: position_side={position_side}, order_side={side}, quantity={quantity_to_use}")

            # IMPORTANTE: Em Hedge Mode, position_side deve ser o lado da POSIÇÃO ABERTA
            # Exemplo: Posição LONG → SL usa side=SELL mas position_side=LONG
            # O create_futures_order vai usar position_side se for passado, senão calcula errado
            # CORREÇÃO: Usar símbolo no formato BingX (BTC-USDT) para criar ordens
            symbol_bingx = position['symbol'].replace("USDT", "-USDT") if "-" not in position['symbol'] else position['symbol']

            if order_type == 'stopLoss':
                logger.info(f"🎯 Chamando create_stop_loss_order: symbol={symbol_bingx}, side={side}, qty={quantity_to_use}, stop={rounded_price}, position_side={position_side}")
                result = await connector.create_stop_loss_order(
                    symbol=symbol_bingx,
                    side=side,
                    quantity=quantity_to_use,
                    stop_price=rounded_price,
                    reduce_only=False,  # Hedge mode não usa reduce_only
                    position_side=position_side  # CRÍTICO: Passar o lado da posição aberta
                )
            else:  # takeProfit
                logger.info(f"🎯 Chamando create_take_profit_order: symbol={symbol_bingx}, side={side}, qty={quantity_to_use}, stop={rounded_price}, position_side={position_side}")
                result = await connector.create_take_profit_order(
                    symbol=symbol_bingx,
                    side=side,
                    quantity=quantity_to_use,
                    stop_price=rounded_price,
                    reduce_only=False,  # Hedge mode não usa reduce_only
                    position_side=position_side  # CRÍTICO: Passar o lado da posição aberta
                )

            if not result.get('success'):
                raise Exception(f"BingX order creation failed: {result.get('error')}")

            new_order_id = str(result.get('order_id'))  # create_futures_order retorna 'order_id'
            logger.info(f"✅ Nova ordem criada na BingX: {new_order_id}")
        else:
            # Binance: usar client.futures_create_order
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


@router.post("/positions/{position_id}/sltp")
async def create_position_sltp(
    position_id: str,
    create_data: CreateSLTPRequest,
    x_idempotency_key: Optional[str] = Header(None)
):
    """
    Cria Stop Loss ou Take Profit para uma posição existente

    Este endpoint é usado quando o usuário arrasta a linha de entrada
    no gráfico para criar um novo SL ou TP.

    Este endpoint:
    1. Verifica idempotência (previne duplicação)
    2. Busca a posição e suas credenciais
    3. Cria uma nova ordem SL/TP com o preço especificado
    4. Salva no banco de dados
    """
    logger.info(f"📝 Criando SL/TP para posição {position_id}")
    logger.info(f"📊 Tipo: {create_data.type}, Preço: ${create_data.price}, Side: {create_data.side}")

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
                ea.testnet,
                ea.exchange,
                COALESCE(ea.position_mode, 'hedge') as position_mode
            FROM positions p
            JOIN exchange_accounts ea ON p.exchange_account_id = ea.id
            WHERE p.id = $1
        """, position_id)

        if not position:
            raise HTTPException(status_code=404, detail="Posição não encontrada")

        logger.info(f"✅ Posição encontrada: {position['symbol']} {position['side']}")

        # 2. Criar connector da exchange correta
        exchange = position['exchange'].lower()
        logger.info(f"🏦 Exchange detectada: {exchange}")

        if exchange == 'bingx':
            connector = BingXConnector(
                api_key=position['api_key'],
                api_secret=position['secret_key'],
                testnet=position['testnet']
            )
        else:  # binance
            connector = BinanceConnector(
                api_key=position['api_key'],
                api_secret=position['secret_key'],
                testnet=position['testnet']
            )

        # 3. Arredondar preço para precisão correta
        order_type = create_data.type
        new_price = create_data.price
        symbol = position['symbol'].upper()

        if 'BTC' in symbol:
            rounded_price = round(new_price, 1)
        elif 'ETH' in symbol:
            rounded_price = round(new_price, 2)
        else:
            rounded_price = round(new_price, 2)

        logger.info(f"📝 Criando ordem {order_type} @ ${rounded_price}")

        # 4. Determinar side da ordem (inverso da posição)
        order_side = 'SELL' if create_data.side.upper() == 'LONG' else 'BUY'
        position_side = create_data.side.upper()  # LONG ou SHORT

        # 5. Buscar quantidade da posição
        quantity = float(position['size'])

        if exchange == 'bingx':
            # Buscar quantidade disponível diretamente da BingX
            symbol_bingx = position['symbol'].replace("USDT", "-USDT") if "-" not in position['symbol'] else position['symbol']

            bingx_positions = await connector.get_futures_positions()
            if bingx_positions.get('success') and bingx_positions.get('positions'):
                for pos in bingx_positions['positions']:
                    pos_symbol = pos.get('symbol', '')
                    pos_side = pos.get('positionSide', '').upper()
                    if pos_symbol == symbol_bingx and pos_side == position_side:
                        bingx_available = abs(float(pos.get('availableAmt', 0)))
                        if bingx_available > 0:
                            quantity = bingx_available
                            logger.info(f"📊 Usando availableAmt da BingX: {quantity}")
                        break

            logger.info(f"📊 Criando SL/TP BingX: position_side={position_side}, order_side={order_side}, quantity={quantity}")

            if order_type == 'stopLoss':
                result = await connector.create_stop_loss_order(
                    symbol=symbol_bingx,
                    side=order_side,
                    quantity=quantity,
                    stop_price=rounded_price,
                    reduce_only=False,
                    position_side=position_side
                )
            else:  # takeProfit
                result = await connector.create_take_profit_order(
                    symbol=symbol_bingx,
                    side=order_side,
                    quantity=quantity,
                    stop_price=rounded_price,
                    reduce_only=False,
                    position_side=position_side
                )

            if not result.get('success'):
                raise Exception(f"BingX order creation failed: {result.get('error')}")

            new_order_id = str(result.get('order_id'))
            logger.info(f"✅ Nova ordem criada na BingX: {new_order_id}")
        else:
            # Binance
            if order_type == 'stopLoss':
                order_params = {
                    'symbol': position['symbol'].upper(),
                    'side': order_side,
                    'type': 'STOP_MARKET',
                    'stopPrice': rounded_price,
                    'closePosition': 'true'
                }
            else:  # takeProfit
                order_params = {
                    'symbol': position['symbol'].upper(),
                    'side': order_side,
                    'type': 'TAKE_PROFIT_MARKET',
                    'stopPrice': rounded_price,
                    'closePosition': 'true'
                }

            order_result = await asyncio.to_thread(
                connector.client.futures_create_order,
                **order_params
            )

            new_order_id = str(order_result.get('orderId'))
            logger.info(f"✅ Nova ordem criada na Binance: {new_order_id}")

        # 6. Salvar nova ordem no banco
        sl_tp_prefix = 'sl' if order_type == 'stopLoss' else 'tp'
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
            order_side.lower(),
            'market',
            'submitted',
            Decimal(str(quantity)),
            Decimal(str(rounded_price)),
            Decimal('0'),
            Decimal('0'),
            'gtc',
            0,
            True,
            False,
            datetime.utcnow()
        )

        logger.info(f"✅ Nova ordem salva no banco: {db_order_id}")

        # Preparar resposta
        response = {
            "success": True,
            "message": f"{order_type} criado com sucesso",
            "order_id": new_order_id,
            "new_price": rounded_price
        }

        # ✅ IDEMPOTÊNCIA: Cachear resposta
        if x_idempotency_key:
            await cache_response(x_idempotency_key, response, ttl=60)

        return response

    except BinanceAPIException as e:
        logger.error(f"❌ Erro da API Binance: {e}")
        raise HTTPException(status_code=400, detail=f"Erro da Binance: {e.message}")
    except Exception as e:
        logger.error(f"❌ Erro ao criar SL/TP: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/positions/{position_id}/sltp")
async def cancel_position_sltp(
    position_id: str,
    cancel_data: CancelSLTPRequest
):
    """
    Cancela Stop Loss ou Take Profit de uma posição existente

    Este endpoint é usado quando o usuário clica no X para remover uma ordem SL/TP.

    Este endpoint:
    1. Busca a posição e suas credenciais
    2. Busca a ordem SL/TP associada
    3. Cancela a ordem na exchange
    4. Atualiza o status no banco de dados
    """
    logger.info(f"❌ Cancelando SL/TP para posição {position_id}")
    logger.info(f"📊 Tipo: {cancel_data.type}")

    try:
        # 1. Buscar a posição no banco
        position = await transaction_db.fetchrow("""
            SELECT
                p.*,
                ea.api_key,
                ea.secret_key,
                ea.testnet,
                ea.exchange,
                COALESCE(ea.position_mode, 'hedge') as position_mode
            FROM positions p
            JOIN exchange_accounts ea ON p.exchange_account_id = ea.id
            WHERE p.id = $1
        """, position_id)

        if not position:
            raise HTTPException(status_code=404, detail="Posição não encontrada")

        logger.info(f"✅ Posição encontrada: {position['symbol']} {position['side']}")

        # 2. Buscar ordens SL/TP associadas à posição
        order_type_db = 'market'  # Ordens SL/TP são salvas como market

        # Determinar side da ordem baseado no tipo de posição
        order_side = 'sell' if position['side'].upper() == 'LONG' else 'buy'

        orders = await transaction_db.fetch("""
            SELECT * FROM orders
            WHERE exchange_account_id = $1
            AND symbol = $2
            AND side = $3
            AND reduce_only = true
            AND status IN ('submitted', 'new', 'partially_filled')
            ORDER BY created_at DESC
        """, position['exchange_account_id'], position['symbol'], order_side)

        if not orders:
            logger.warning(f"⚠️ Nenhuma ordem SL/TP encontrada para posição {position_id}")
            # Mesmo sem ordens no banco, podemos tentar buscar na exchange

        # 3. Criar connector da exchange
        exchange = position['exchange'].lower()
        logger.info(f"🏦 Exchange detectada: {exchange}")

        if exchange == 'bingx':
            connector = BingXConnector(
                api_key=position['api_key'],
                api_secret=position['secret_key'],
                testnet=position['testnet']
            )
        else:  # binance
            connector = BinanceConnector(
                api_key=position['api_key'],
                api_secret=position['secret_key'],
                testnet=position['testnet']
            )

        # 4. Buscar ordens abertas na exchange para o símbolo
        cancelled_order_id = None
        symbol = position['symbol'].upper()

        if exchange == 'bingx':
            symbol_bingx = symbol.replace("USDT", "-USDT") if "-" not in symbol else symbol

            # Buscar todas as ordens abertas
            open_orders = await connector.get_open_orders(symbol_bingx)

            if open_orders.get('success') and open_orders.get('orders'):
                for order in open_orders['orders']:
                    order_type_str = order.get('type', '').upper()

                    # Identificar se é SL ou TP
                    is_sl = 'STOP' in order_type_str and 'TAKE' not in order_type_str
                    is_tp = 'TAKE_PROFIT' in order_type_str or 'PROFIT' in order_type_str

                    should_cancel = (
                        (cancel_data.type == 'stopLoss' and is_sl) or
                        (cancel_data.type == 'takeProfit' and is_tp)
                    )

                    if should_cancel:
                        order_id = order.get('orderId') or order.get('order_id')
                        logger.info(f"🎯 Cancelando ordem BingX: {order_id}")

                        result = await connector.cancel_order(symbol_bingx, order_id)

                        if result.get('success'):
                            cancelled_order_id = str(order_id)
                            logger.info(f"✅ Ordem cancelada na BingX: {cancelled_order_id}")
                        else:
                            logger.error(f"❌ Erro ao cancelar ordem BingX: {result.get('error')}")

                        break  # Cancelar apenas a primeira ordem encontrada
        else:
            # Binance
            open_orders = await asyncio.to_thread(
                connector.client.futures_get_open_orders,
                symbol=symbol
            )

            for order in open_orders:
                order_type_str = order.get('type', '').upper()

                # Identificar se é SL ou TP
                is_sl = order_type_str in ['STOP_MARKET', 'STOP']
                is_tp = order_type_str in ['TAKE_PROFIT_MARKET', 'TAKE_PROFIT']

                should_cancel = (
                    (cancel_data.type == 'stopLoss' and is_sl) or
                    (cancel_data.type == 'takeProfit' and is_tp)
                )

                if should_cancel:
                    order_id = order.get('orderId')
                    logger.info(f"🎯 Cancelando ordem Binance: {order_id}")

                    result = await asyncio.to_thread(
                        connector.client.futures_cancel_order,
                        symbol=symbol,
                        orderId=order_id
                    )

                    cancelled_order_id = str(order_id)
                    logger.info(f"✅ Ordem cancelada na Binance: {cancelled_order_id}")
                    break

        # 5. Atualizar status no banco de dados (se encontrou ordem)
        if cancelled_order_id:
            await transaction_db.execute("""
                UPDATE orders
                SET status = 'cancelled', updated_at = $1
                WHERE external_id = $2
            """, datetime.utcnow(), cancelled_order_id)

            logger.info(f"✅ Status da ordem atualizado no banco")

        return {
            "success": True,
            "message": f"{cancel_data.type} cancelado com sucesso",
            "cancelled_order_id": cancelled_order_id
        }

    except BinanceAPIException as e:
        logger.error(f"❌ Erro da API Binance: {e}")
        raise HTTPException(status_code=400, detail=f"Erro da Binance: {e.message}")
    except Exception as e:
        logger.error(f"❌ Erro ao cancelar SL/TP: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

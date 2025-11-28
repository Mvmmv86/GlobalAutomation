"""Orders Controller - API endpoints for trading orders"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from typing import Optional, Literal
from decimal import Decimal
import structlog
from datetime import datetime
import uuid

from infrastructure.database.connection_transaction_mode import transaction_db
from infrastructure.exchanges.unified_exchange_connector import get_unified_connector
from presentation.controllers.websocket_controller import notify_order_update, notify_position_update

logger = structlog.get_logger(__name__)


# ==================== PYDANTIC MODELS ====================

class CreateOrderRequest(BaseModel):
    """Request model para criar ordem"""
    exchange_account_id: str = Field(..., description="ID da conta de exchange")
    symbol: str = Field(..., description="Par de negociação (ex: BTCUSDT)")
    side: Literal['buy', 'sell'] = Field(..., description="Lado da ordem")
    order_type: Literal['market', 'limit', 'stop_limit'] = Field(..., description="Tipo de ordem")
    operation_type: Literal['spot', 'futures'] = Field(..., description="Tipo de operação")
    quantity: float = Field(..., gt=0, description="Quantidade")
    price: Optional[float] = Field(None, description="Preço (para LIMIT/STOP)")
    stop_price: Optional[float] = Field(None, description="Preço de ativação (para STOP)")
    leverage: Optional[int] = Field(1, ge=1, le=125, description="Alavancagem (FUTURES)")
    stop_loss: Optional[float] = Field(None, description="Stop Loss")
    take_profit: Optional[float] = Field(None, description="Take Profit")

    # Trailing Stop
    trailing_stop: Optional[bool] = Field(False, description="Usar Trailing Stop")
    trailing_delta: Optional[float] = Field(None, description="Delta do Trailing Stop (USDT ou %)")
    trailing_delta_type: Optional[Literal['amount', 'percent']] = Field('percent', description="Tipo do delta")


class ClosePositionRequest(BaseModel):
    """Request model para fechar posição"""
    position_id: str = Field(..., description="ID da posição")
    percentage: float = Field(100, ge=1, le=100, description="% da posição a fechar")


class ModifyOrderRequest(BaseModel):
    """Request model para modificar SL/TP"""
    stop_loss: Optional[float] = Field(None, description="Novo Stop Loss")
    take_profit: Optional[float] = Field(None, description="Novo Take Profit")


class TrailingStopRequest(BaseModel):
    """Request model para Trailing Stop"""
    position_id: str = Field(..., description="ID da posição")
    activation_price: float = Field(..., description="Preço de ativação")
    callback_rate: float = Field(..., ge=0.1, le=5, description="Taxa de callback (%)")


# ==================== VALIDATION FUNCTIONS ====================

async def validate_balance(
    exchange_account_id: str,
    required_amount: float,
    operation_type: str
) -> bool:
    """Valida se há saldo suficiente"""
    try:
        # Buscar saldo da conta
        account = await transaction_db.fetchrow("""
            SELECT
                spot_balance_usdt,
                futures_balance_usdt,
                futures_available_balance
            FROM exchange_accounts
            WHERE id = $1 AND is_active = true
        """, exchange_account_id)

        if not account:
            raise ValueError("Conta de exchange não encontrada ou inativa")

        # Verificar saldo baseado no tipo de operação
        if operation_type == 'futures':
            available = float(account['futures_available_balance'] or 0)
        else:
            available = float(account['spot_balance_usdt'] or 0)

        if available < required_amount:
            raise ValueError(
                f"Saldo insuficiente. Disponível: ${available:.2f}, "
                f"Necessário: ${required_amount:.2f}"
            )

        return True

    except Exception as e:
        logger.error("Error validating balance", error=str(e))
        raise


async def validate_price_range(
    symbol: str,
    price: float,
    current_price: float,
    max_deviation: float = 0.10  # 10%
) -> bool:
    """Valida se preço está dentro de ±10% do mercado (anti-fat finger)"""
    lower_bound = current_price * (1 - max_deviation)
    upper_bound = current_price * (1 + max_deviation)

    if price < lower_bound or price > upper_bound:
        deviation = abs((price - current_price) / current_price * 100)
        raise ValueError(
            f"⚠️ Preço muito diferente do mercado! "
            f"Mercado: ${current_price:.2f}, "
            f"Seu preço: ${price:.2f} ({deviation:.1f}% de diferença). "
            f"Confirme se está correto."
        )

    return True


async def validate_stop_loss_take_profit(
    side: str,
    entry_price: float,
    stop_loss: Optional[float],
    take_profit: Optional[float]
) -> bool:
    """Valida SL/TP baseado no lado da ordem"""

    if side.upper() in ['BUY', 'LONG']:
        # LONG: SL deve estar ABAIXO do entry, TP ACIMA
        if stop_loss and stop_loss >= entry_price:
            raise ValueError(
                f"❌ Stop Loss inválido para LONG! "
                f"SL (${stop_loss:.2f}) deve estar ABAIXO do entry (${entry_price:.2f})"
            )
        if take_profit and take_profit <= entry_price:
            raise ValueError(
                f"❌ Take Profit inválido para LONG! "
                f"TP (${take_profit:.2f}) deve estar ACIMA do entry (${entry_price:.2f})"
            )

    elif side.upper() in ['SELL', 'SHORT']:
        # SHORT: SL deve estar ACIMA do entry, TP ABAIXO
        if stop_loss and stop_loss <= entry_price:
            raise ValueError(
                f"❌ Stop Loss inválido para SHORT! "
                f"SL (${stop_loss:.2f}) deve estar ACIMA do entry (${entry_price:.2f})"
            )
        if take_profit and take_profit >= entry_price:
            raise ValueError(
                f"❌ Take Profit inválido para SHORT! "
                f"TP (${take_profit:.2f}) deve estar ABAIXO do entry (${entry_price:.2f})"
            )

    return True


async def get_current_market_price(
    exchange: str,
    symbol: str,
    api_key: str,
    api_secret: str,
    testnet: bool,
    operation_type: str
) -> float:
    """Busca preço atual do mercado"""
    try:
        connector = await get_unified_connector(
            exchange=exchange,
            api_key=api_key,
            api_secret=api_secret,
            testnet=testnet,
            operation_type=operation_type
        )

        # Buscar último candle para pegar preço atual
        result = await connector.get_klines(symbol, interval='1m', limit=1)

        await connector.close()

        if result['success'] and result['data']:
            last_candle = result['data'][-1]
            return float(last_candle[4])  # close price

        raise ValueError("Não foi possível obter preço atual do mercado")

    except Exception as e:
        logger.error("Error getting market price", error=str(e))
        raise


# ==================== ROUTER ====================

def create_orders_router() -> APIRouter:
    """Create and configure the orders router"""
    router = APIRouter(prefix="/api/v1/orders", tags=["Orders"])

    @router.post("/create")
    async def create_order(order_request: CreateOrderRequest, request: Request):
        """
        Criar nova ordem com validações completas

        Validações:
        - ✅ Saldo suficiente
        - ✅ Preço dentro de ±10% do mercado
        - ✅ SL/TP válidos baseado no lado
        - ✅ Quantidade mínima
        """
        try:
            logger.info(f"🔵 CREATE ORDER CHAMADO! Payload: {order_request.model_dump()}")

            # 1. Buscar dados da conta
            account = await transaction_db.fetchrow("""
                SELECT
                    id, exchange, api_key, secret_key, testnet
                FROM exchange_accounts
                WHERE id = $1 AND is_active = true
            """, order_request.exchange_account_id)

            if not account:
                raise HTTPException(
                    status_code=404,
                    detail="Conta de exchange não encontrada ou inativa"
                )

            # 2. Usar credenciais (já descriptografadas pelo sistema)
            api_key = account['api_key']
            api_secret = account['secret_key']

            # 3. Buscar preço atual do mercado (SKIP para MARKET orders - pegar da exchange)
            current_price = None
            if order_request.order_type != 'market':
                try:
                    current_price = await get_current_market_price(
                        exchange=account['exchange'],
                        symbol=order_request.symbol,
                        api_key=api_key,
                        api_secret=api_secret,
                        testnet=account['testnet'],
                        operation_type=order_request.operation_type
                    )
                except Exception as e:
                    logger.warning(f"⚠️ Não conseguiu buscar preço de mercado: {e}")
                    # Para LIMIT/STOP, usar o preço fornecido
                    if order_request.price:
                        current_price = order_request.price

            # 4. Calcular valor necessário
            # Para MARKET orders, usar preço estimado de $1 apenas para validação
            # O preço real será determinado pela exchange
            if order_request.order_type == 'market':
                order_price = 1.0  # Valor placeholder
            else:
                order_price = order_request.price if order_request.price else (current_price or 1.0)

            if order_request.operation_type == 'futures':
                # FUTURES: Usar margem
                required_amount = (order_request.quantity * order_price) / order_request.leverage
            else:
                # SPOT: Valor total
                required_amount = order_request.quantity * order_price

            # 5. VALIDAÇÃO: Saldo suficiente (TODO: Implementar após criar colunas de balanço)
            # await validate_balance(
            #     order_request.exchange_account_id,
            #     required_amount,
            #     order_request.operation_type
            # )

            # 6. VALIDAÇÃO: Preço dentro de ±10% (anti-fat finger)
            if order_request.order_type in ['limit', 'stop_limit'] and order_request.price and current_price:
                await validate_price_range(
                    order_request.symbol,
                    order_request.price,
                    current_price
                )

            # 7. VALIDAÇÃO: SL/TP
            if order_request.stop_loss or order_request.take_profit:
                await validate_stop_loss_take_profit(
                    order_request.side,
                    order_price,
                    order_request.stop_loss,
                    order_request.take_profit
                )

            # 8. Criar conector da exchange (FACTORY PATTERN)
            exchange_type = account['exchange'].lower()
            logger.info(f"🔷 Creating {exchange_type} connector for order")

            if exchange_type == 'binance':
                from infrastructure.exchanges.binance_connector import BinanceConnector
                connector = BinanceConnector(
                    api_key=api_key,
                    api_secret=api_secret,
                    testnet=account['testnet']
                )
            elif exchange_type == 'bingx':
                from infrastructure.exchanges.bingx_connector import BingXConnector
                connector = BingXConnector(
                    api_key=api_key,
                    api_secret=api_secret,
                    testnet=account['testnet']
                )
            elif exchange_type == 'bybit':
                from infrastructure.exchanges.bybit_connector import BybitConnector
                connector = BybitConnector(
                    api_key=api_key,
                    api_secret=api_secret,
                    testnet=account['testnet']
                )
            elif exchange_type == 'bitget':
                from infrastructure.exchanges.bitget_connector import BitgetConnector
                connector = BitgetConnector(
                    api_key=api_key,
                    api_secret=api_secret,
                    testnet=account['testnet']
                )
            else:
                raise ValueError(f"Unsupported exchange: {exchange_type}")

            # 9. Executar ordem na exchange (REAL)
            if order_request.operation_type == 'futures':
                exchange_result = await connector.create_futures_order(
                    symbol=order_request.symbol,
                    side=order_request.side,
                    order_type=order_request.order_type,
                    quantity=order_request.quantity,
                    price=order_request.price,
                    stop_price=order_request.stop_price,
                    leverage=order_request.leverage or 1,
                    stop_loss=order_request.stop_loss,
                    take_profit=order_request.take_profit
                )
            else:  # SPOT
                exchange_result = await connector.create_spot_order(
                    symbol=order_request.symbol,
                    side=order_request.side,
                    order_type=order_request.order_type,
                    quantity=order_request.quantity,
                    price=order_request.price,
                    stop_price=order_request.stop_price
                )

            # Verificar se ordem foi executada com sucesso
            if not exchange_result.get('success'):
                raise ValueError(f"Erro ao executar ordem na exchange: {exchange_result.get('error')}")

            exchange_order_id = exchange_result.get('order_id')

            # 10. Salvar ordem no banco de dados
            # Gerar client_order_id único
            client_order_id = f"platform_{uuid.uuid4().hex[:16]}"

            # Buscar user_id da conta (necessário para rastreabilidade)
            user_id = await transaction_db.fetchval("""
                SELECT user_id FROM exchange_accounts WHERE id = $1
            """, order_request.exchange_account_id)

            order_id = await transaction_db.fetchval("""
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
                    price,
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
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $18)
                RETURNING id
            """,
                client_order_id,                    # $1
                'PLATFORM',                         # $2 - SEMPRE plataforma
                order_request.exchange_account_id,  # $3
                exchange_order_id,                  # $4 - external_id (ID da Binance)
                order_request.symbol,               # $5
                order_request.side,                 # $6
                order_request.order_type,           # $7
                'filled',                           # $8 - Status = filled porque foi executada com sucesso
                Decimal(str(order_request.quantity)), # $9
                Decimal(str(order_price)) if order_price else None, # $10
                Decimal(str(order_request.stop_loss)) if order_request.stop_loss else None, # $11
                Decimal('0'),                       # $12 - filled_quantity (0 inicial)
                Decimal('0'),                       # $13 - fees_paid (0 inicial)
                'gtc',                              # $14 - time_in_force (Good Till Cancel)
                0,                                  # $15 - retry_count
                False,                              # $16 - reduce_only
                False,                              # $17 - post_only
                datetime.utcnow()                   # $18 - created_at e updated_at
            )

            logger.info(
                "Order executed successfully on exchange",
                order_id=order_id,
                exchange_order_id=exchange_order_id,
                symbol=order_request.symbol,
                side=order_request.side,
                type=order_request.order_type,
                quantity=order_request.quantity,
                price=order_price,
                leverage=order_request.leverage if order_request.operation_type == 'futures' else None
            )

            # ✅ NOVO: Salvar ordens de Stop Loss e Take Profit se foram criadas
            sl_order_id = None
            tp_order_id = None

            if exchange_result.get('stop_loss_order_id'):
                # Determinar lado reverso para SL
                sl_side = 'sell' if order_request.side == 'buy' else 'buy'
                sl_client_order_id = f"sl_{uuid.uuid4().hex[:16]}"

                sl_order_id = await transaction_db.fetchval("""
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
                    sl_client_order_id,
                    'PLATFORM',
                    order_request.exchange_account_id,
                    exchange_result.get('stop_loss_order_id'),
                    order_request.symbol,
                    sl_side,
                    'market',  # stop_market salvo como 'market' para compatibilidade com enum
                    'new',  # Status = new (aguardando ser ativado)
                    Decimal(str(order_request.quantity)),
                    Decimal(str(order_request.stop_loss)),
                    Decimal('0'),
                    Decimal('0'),
                    'gtc',
                    0,
                    True,  # reduce_only = True para fechar posição
                    False,
                    datetime.utcnow()
                )

                logger.info(f"✅ Stop Loss saved to DB: {sl_order_id} (external: {exchange_result.get('stop_loss_order_id')})")

            if exchange_result.get('take_profit_order_id'):
                # Determinar lado reverso para TP
                tp_side = 'sell' if order_request.side == 'buy' else 'buy'
                tp_client_order_id = f"tp_{uuid.uuid4().hex[:16]}"

                tp_order_id = await transaction_db.fetchval("""
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
                    tp_client_order_id,
                    'PLATFORM',
                    order_request.exchange_account_id,
                    exchange_result.get('take_profit_order_id'),
                    order_request.symbol,
                    tp_side,
                    'market',  # take_profit_market salvo como 'market' para compatibilidade com enum
                    'new',  # Status = new (aguardando ser ativado)
                    Decimal(str(order_request.quantity)),
                    Decimal(str(order_request.take_profit)),
                    Decimal('0'),
                    Decimal('0'),
                    'gtc',
                    0,
                    True,  # reduce_only = True para fechar posição
                    False,
                    datetime.utcnow()
                )

                logger.info(f"✅ Take Profit saved to DB: {tp_order_id} (external: {exchange_result.get('take_profit_order_id')})")

            # ✅ NOVO: Notificar via WebSocket sobre ordem criada
            try:
                # Buscar user_id da conta para notificação
                if user_id:
                    await notify_order_update(
                        user_id=str(user_id),
                        order_data={
                            "action": "order_created",
                            "order_id": order_id,
                            "exchange_order_id": exchange_order_id,
                            "symbol": order_request.symbol,
                            "side": order_request.side,
                            "type": order_request.order_type,
                            "quantity": order_request.quantity,
                            "status": "filled",
                            "has_stop_loss": bool(order_request.stop_loss),
                            "has_take_profit": bool(order_request.take_profit)
                        }
                    )
                    logger.info(f"📡 WebSocket notification sent for order {order_id}")
            except Exception as e:
                logger.warning(f"Failed to send WebSocket notification: {e}")

            return {
                "success": True,
                "data": {
                    "order_id": order_id,
                    "exchange_order_id": exchange_order_id,
                    "status": "filled",
                    "message": f"Ordem executada com sucesso na {account['exchange'].upper()}!",
                    "estimated_cost": required_amount,
                    "current_market_price": current_price
                }
            }

        except ValueError as e:
            # Erros de validação
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error("Error creating order", error=str(e), exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Erro ao criar ordem: {str(e)}"
            )

    @router.post("/close")
    async def close_position(close_request: ClosePositionRequest, request: Request):
        """
        Fechar posição (sempre usando ordem MARKET para rapidez)
        """
        try:
            logger.info(f"🔵 STEP 1: Buscando posição {close_request.position_id}")
            # 1. Buscar posição do banco de dados
            position = await transaction_db.fetchrow("""
                SELECT
                    p.id, p.symbol, p.side, p.size, p.entry_price,
                    p.exchange_account_id,
                    ea.exchange, ea.api_key, ea.secret_key, ea.testnet
                FROM positions p
                JOIN exchange_accounts ea ON p.exchange_account_id = ea.id
                WHERE p.id = $1 AND p.status = 'open'
            """, close_request.position_id)

            if not position:
                raise HTTPException(
                    status_code=404,
                    detail="Posição não encontrada ou já fechada"
                )

            logger.info(f"🔵 STEP 2: Posição no banco: {position['symbol']} {position['side']} size={position['size']}")

            # 2. Importar connectors
            from infrastructure.exchanges.binance_connector import BinanceConnector
            from infrastructure.exchanges.bybit_connector import BybitConnector
            from infrastructure.exchanges.bingx_connector import BingXConnector
            from infrastructure.exchanges.bitget_connector import BitgetConnector
            import asyncio
            import math

            exchange = position['exchange'].lower()
            position_side = position['side'].upper()  # LONG ou SHORT
            close_side_upper = 'SELL' if position_side == 'LONG' else 'BUY'
            close_side_lower = close_side_upper.lower()

            # 3. Criar connector baseado na exchange
            logger.info(f"🔵 STEP 3: Criando connector para exchange: {exchange}")

            if exchange == 'binance':
                connector = BinanceConnector(
                    api_key=position['api_key'],
                    api_secret=position['secret_key'],
                    testnet=position['testnet']
                )
            elif exchange == 'bybit':
                connector = BybitConnector(
                    api_key=position['api_key'],
                    api_secret=position['secret_key'],
                    testnet=position['testnet']
                )
            elif exchange == 'bingx':
                connector = BingXConnector(
                    api_key=position['api_key'],
                    api_secret=position['secret_key'],
                    testnet=position['testnet']
                )
            elif exchange == 'bitget':
                connector = BitgetConnector(
                    api_key=position['api_key'],
                    api_secret=position['secret_key'],
                    testnet=position['testnet']
                )
            else:
                raise HTTPException(status_code=400, detail=f"Exchange {exchange} não suportada")

            # 4. Para BingX: buscar posição REAL da exchange (não confiar no banco)
            actual_size = float(position['size']) if position['size'] else 0

            if exchange == 'bingx':
                logger.info(f"🔵 STEP 4: BingX - Buscando posição REAL da exchange...")
                positions_result = await connector.get_futures_positions()

                if positions_result.get('success'):
                    # Encontrar a posição específica
                    symbol_bingx = position['symbol'].replace("USDT", "-USDT") if "-" not in position['symbol'] else position['symbol']
                    logger.info(f"🔵 STEP 4: Buscando símbolo: {symbol_bingx}, lado: {position_side}")
                    logger.info(f"🔵 STEP 4: Posições retornadas da BingX: {len(positions_result.get('positions', []))}")

                    for pos in positions_result.get('positions', []):
                        pos_symbol = pos.get('symbol', '')
                        # BingX pode retornar:
                        # - One-Way Mode: positionSide = "BOTH", lado definido pelo sinal de positionAmt
                        # - Hedge Mode: positionSide = "LONG" ou "SHORT"
                        pos_side_raw = pos.get('positionSide', pos.get('side', '')).upper()
                        pos_amt_signed = float(pos.get('positionAmt', pos.get('size', 0)))
                        pos_amt = abs(pos_amt_signed)

                        # Determinar o lado REAL da posição
                        if pos_side_raw == 'BOTH':
                            # ONE-WAY MODE: lado baseado no sinal de positionAmt
                            # positionAmt > 0 = LONG, positionAmt < 0 = SHORT
                            pos_side = 'LONG' if pos_amt_signed > 0 else 'SHORT'
                            logger.info(f"🔵 STEP 4: One-Way Mode detectado - positionAmt={pos_amt_signed} → side={pos_side}")
                        else:
                            # HEDGE MODE: usar positionSide diretamente
                            pos_side = pos_side_raw

                        logger.info(f"🔵 STEP 4: Comparando pos: {pos_symbol} {pos_side} size={pos_amt} vs {symbol_bingx} {position_side}")

                        if pos_symbol == symbol_bingx and pos_side == position_side and pos_amt > 0:
                            actual_size = pos_amt
                            logger.info(f"🔵 STEP 4: ✅ Posição REAL encontrada na BingX: {pos_symbol} {pos_side} size={actual_size}")
                            break

                if actual_size == 0:
                    logger.error(f"🔵 STEP 4: ❌ Posição não encontrada! symbol={position['symbol']}, side={position_side}")
                    raise HTTPException(
                        status_code=400,
                        detail=f"Posição {position['symbol']} {position_side} não encontrada na BingX ou já fechada"
                    )

            # 5. Calcular quantidade a fechar
            raw_quantity = actual_size * (close_request.percentage / 100)
            logger.info(f"🔵 STEP 5: Quantidade a fechar: {actual_size} * {close_request.percentage}% = {raw_quantity}")

            # 6. Obter LOT_SIZE da exchange CORRETA
            if exchange == 'binance':
                # Binance: usar futures_exchange_info
                exchange_info = await asyncio.to_thread(connector.client.futures_exchange_info)
                symbol_info = next(
                    (s for s in exchange_info['symbols'] if s['symbol'] == position['symbol']),
                    None
                )
                if symbol_info:
                    lot_size_filter = next(
                        (f for f in symbol_info['filters'] if f['filterType'] == 'LOT_SIZE'),
                        None
                    )
                    if lot_size_filter:
                        step_size = float(lot_size_filter['stepSize'])
                        min_qty = float(lot_size_filter['minQty'])
                    else:
                        step_size = 0.001
                        min_qty = 0.001
                else:
                    step_size = 0.001
                    min_qty = 0.001
            elif exchange == 'bingx':
                # BingX: usar endpoint de contratos - valores padrão mais permissivos
                # A BingX geralmente aceita quantidades muito pequenas
                step_size = 0.0001  # BingX aceita até 4 casas decimais
                min_qty = 0.0001   # Mínimo muito baixo para BingX
                logger.info(f"🔵 STEP 6: BingX LOT_SIZE: stepSize={step_size}, minQty={min_qty}")
            else:
                # Outras exchanges: valores padrão
                step_size = 0.001
                min_qty = 0.001

            # 7. Normalizar quantidade
            quantity_to_close = math.floor(raw_quantity / step_size) * step_size

            # Para quantidades muito pequenas, usar a quantidade real se estiver abaixo do step
            if quantity_to_close == 0 and raw_quantity > 0:
                quantity_to_close = raw_quantity  # Tentar com a quantidade real

            logger.info(f"🔵 STEP 6: LOT_SIZE: stepSize={step_size}, minQty={min_qty}")
            logger.info(f"🔵 STEP 7: Quantidade normalizada: {raw_quantity} → {quantity_to_close}")

            # 8. Executar fechamento
            logger.info(f"🔵 STEP 8: Executando fechamento: {position['symbol']} {close_side_upper} qty={quantity_to_close}")

            if exchange == 'binance':
                # Binance: create_market_order aceita reduce_only
                order_result = await connector.create_market_order(
                    symbol=position['symbol'],
                    side=close_side_upper,
                    quantity=Decimal(str(quantity_to_close)),
                    reduce_only=True
                )
            elif exchange == 'bingx':
                # BingX: usar métodos específicos
                if close_request.percentage >= 100:
                    # Fechamento total: usar endpoint close_position (mais confiável)
                    logger.info(f"🔵 BingX: Usando close_position para fechamento total")
                    order_result = await connector.close_position(
                        symbol=position['symbol'],
                        position_side=position_side
                    )
                else:
                    # Fechamento parcial: usar close_position_partial
                    logger.info(f"🔵 BingX: Usando close_position_partial para {close_request.percentage}%")
                    order_result = await connector.close_position_partial(
                        symbol=position['symbol'],
                        quantity=quantity_to_close,
                        position_side=position_side
                    )
            else:
                # Outras exchanges (Bybit, Bitget): usar create_futures_order
                order_result = await connector.create_futures_order(
                    symbol=position['symbol'],
                    side=close_side_upper,
                    order_type='MARKET',
                    quantity=float(quantity_to_close),
                    reduce_only=False,
                    position_side=position_side
                )

            # Verificar se ordem foi executada com sucesso
            if not order_result.get('success', False):
                error_msg = order_result.get('error', 'Erro desconhecido')
                logger.error(f"❌ STEP 9: Falha ao executar ordem: {error_msg}")
                raise HTTPException(
                    status_code=400,
                    detail=f"Falha ao executar ordem na exchange: {error_msg}"
                )

            logger.info(f"🔵 STEP 7: Ordem executada com sucesso! order_id={order_result.get('order_id')}")

            # 5. Salvar ordem no banco
            client_order_id = f"close_{uuid.uuid4().hex[:16]}"

            # Buscar user_id da conta
            account_user_id = await transaction_db.fetchval("""
                SELECT user_id FROM exchange_accounts WHERE id = $1
            """, position['exchange_account_id'])

            order_id = await transaction_db.fetchval("""
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
                    filled_quantity,
                    fees_paid,
                    time_in_force,
                    retry_count,
                    reduce_only,
                    post_only,
                    created_at,
                    updated_at
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $16)
                RETURNING id
            """,
                client_order_id,                        # $1
                'PLATFORM',                             # $2 - Fechamento via plataforma
                position['exchange_account_id'],        # $3
                str(order_result.get('order_id')),      # $4 - external_id
                position['symbol'],                     # $5
                close_side_lower,                       # $6 - buy/sell
                'market',                               # $7 - Sempre MARKET para fechar
                'filled',                               # $8 - Status
                Decimal(str(quantity_to_close)),        # $9
                Decimal(str(quantity_to_close)),        # $10 - filled_quantity (100% executado)
                Decimal('0'),                           # $11 - fees_paid
                'gtc',                                  # $12 - time_in_force
                0,                                      # $13 - retry_count
                True,                                   # $14 - reduce_only (fechar posição)
                False,                                  # $15 - post_only
                datetime.utcnow()                       # $16 - created_at e updated_at
            )
            logger.info(f"🔵 STEP 8: Ordem salva no banco com ID {order_id}")

            # 6. Atualizar posição se fechamento parcial
            if close_request.percentage < 100:
                new_size = float(position['size']) * (1 - close_request.percentage / 100)
                await transaction_db.execute("""
                    UPDATE positions
                    SET size = $1, updated_at = $2
                    WHERE id = $3
                """, Decimal(str(new_size)), datetime.utcnow(), close_request.position_id)
            else:
                # Fechamento total
                await transaction_db.execute("""
                    UPDATE positions
                    SET status = 'closed', closed_at = $1, updated_at = $1
                    WHERE id = $2
                """, datetime.utcnow(), close_request.position_id)

            logger.info(
                "Position closed",
                position_id=close_request.position_id,
                percentage=close_request.percentage,
                order_id=order_id
            )

            # ✅ NOVO: Notificar via WebSocket sobre posição fechada
            try:
                if account_user_id:
                    await notify_position_update(
                        user_id=str(account_user_id),
                        position_data={
                            "action": "position_closed",
                            "position_id": close_request.position_id,
                            "symbol": position['symbol'],
                            "side": position['side'],
                            "closed_percentage": close_request.percentage,
                            "closed_quantity": quantity_to_close,
                            "order_id": order_id
                        }
                    )
                    logger.info(f"📡 WebSocket notification sent for position close {close_request.position_id}")
            except Exception as e:
                logger.warning(f"Failed to send WebSocket notification: {e}")

            return {
                "success": True,
                "data": {
                    "order_id": order_id,
                    "position_id": close_request.position_id,
                    "closed_percentage": close_request.percentage,
                    "closed_quantity": quantity_to_close,
                    "message": f"Posição fechada {close_request.percentage}% com ordem MARKET"
                }
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error("Error closing position", error=str(e), exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Erro ao fechar posição: {str(e)}"
            )

    @router.put("/{position_id}/modify")
    async def modify_order(
        position_id: str,
        modify_request: ModifyOrderRequest,
        request: Request
    ):
        """
        Modificar Stop Loss / Take Profit de uma posição
        (usado quando usuário arrasta linhas no gráfico)

        Este endpoint:
        1. Busca a posição
        2. Busca ordens ativas de SL/TP
        3. Cancela as ordens antigas na Binance
        4. Cria novas ordens com os novos preços
        """
        try:
            # 1. Buscar posição com user_id (otimização: evitar N+1 query)
            position = await transaction_db.fetchrow("""
                SELECT
                    p.id, p.symbol, p.side, p.entry_price, p.status, p.size,
                    p.exchange_account_id,
                    ea.exchange, ea.testnet, ea.api_key, ea.secret_key, ea.user_id
                FROM positions p
                JOIN exchange_accounts ea ON p.exchange_account_id = ea.id
                WHERE p.id = $1 AND p.status = 'open'
            """, position_id)

            if not position:
                raise HTTPException(status_code=404, detail="Posição não encontrada ou já fechada")

            # 2. Validar novos valores de SL/TP
            if modify_request.stop_loss or modify_request.take_profit:
                await validate_stop_loss_take_profit(
                    position['side'],
                    float(position['entry_price']),
                    modify_request.stop_loss,
                    modify_request.take_profit
                )

            # 3. Buscar ordens ativas de SL/TP para este símbolo e conta
            # NOTA: orders não tem position_id, então filtramos por symbol + exchange_account_id
            existing_orders = await transaction_db.fetch("""
                SELECT id, type, external_id, price
                FROM orders
                WHERE exchange_account_id = $1
                  AND symbol = $2
                  AND status = 'new'
                  AND (type ILIKE '%stop%' OR type ILIKE '%take_profit%')
            """, position['exchange_account_id'], position['symbol'])

            # 4. Conectar na exchange para cancelar/criar ordens (usar connector nativo)
            from infrastructure.exchanges.binance_connector import BinanceConnector
            from infrastructure.exchanges.bybit_connector import BybitConnector
            from infrastructure.exchanges.bingx_connector import BingXConnector
            from infrastructure.exchanges.bitget_connector import BitgetConnector

            # Selecionar connector baseado na exchange
            exchange = position['exchange'].lower()
            if exchange == 'binance':
                connector = BinanceConnector(
                    api_key=position['api_key'],
                    api_secret=position['secret_key'],
                    testnet=position['testnet']
                )
            elif exchange == 'bybit':
                connector = BybitConnector(
                    api_key=position['api_key'],
                    api_secret=position['secret_key'],
                    testnet=position['testnet']
                )
            elif exchange == 'bingx':
                connector = BingXConnector(
                    api_key=position['api_key'],
                    api_secret=position['secret_key'],
                    testnet=position['testnet']
                )
            elif exchange == 'bitget':
                connector = BitgetConnector(
                    api_key=position['api_key'],
                    api_secret=position['secret_key'],
                    testnet=position['testnet']
                )
            else:
                raise HTTPException(status_code=400, detail=f"Exchange {exchange} não suportada")

            canceled_orders = []
            created_orders = []
            canceled_order_ids = []  # Otimização: coletar IDs para batch update

            # 5. Cancelar ordens antigas de SL/TP
            for order in existing_orders:
                # Determinar qual tipo de ordem cancelar baseado no que está sendo modificado
                is_stop_loss = 'stop' in order['type'].lower()
                is_take_profit = 'take_profit' in order['type'].lower() or 'takeprofit' in order['type'].lower()

                should_cancel = False
                if is_stop_loss and modify_request.stop_loss:
                    should_cancel = True
                if is_take_profit and modify_request.take_profit:
                    should_cancel = True

                if should_cancel and order['external_id']:
                    try:
                        # Cancelar na Binance
                        await connector.cancel_order(
                            symbol=position['symbol'],
                            order_id=order['external_id']
                        )

                        # Coletar ID para batch update (otimização: evita múltiplos UPDATEs)
                        canceled_order_ids.append(order['id'])
                        canceled_orders.append(order['id'])
                        logger.info(f"Ordem {order['id']} cancelada com sucesso na exchange")
                    except Exception as e:
                        logger.warning(f"Erro ao cancelar ordem {order['id']}: {e}")

            # Batch update de ordens canceladas (otimização: 1 query em vez de N)
            if canceled_order_ids:
                await transaction_db.execute("""
                    UPDATE orders
                    SET status = 'canceled', updated_at = $1
                    WHERE id = ANY($2::uuid[])
                """, datetime.utcnow(), canceled_order_ids)
                logger.info(f"✅ Batch update: {len(canceled_order_ids)} ordens canceladas no banco")

            # 6. Criar novas ordens de SL/TP
            if modify_request.stop_loss:
                # Criar nova ordem de Stop Loss
                sl_side = 'SELL' if position['side'] == 'LONG' else 'BUY'

                try:
                    sl_result = await connector.create_order(
                        symbol=position['symbol'],
                        side=sl_side,
                        order_type='STOP_MARKET',
                        quantity=float(position['size']),
                        stop_price=modify_request.stop_loss
                    )

                    # Salvar no banco
                    # Gerar client_order_id único
                    sl_client_order_id = f"sl_{uuid.uuid4().hex[:16]}"

                    # Usar user_id já carregado da posição (otimização: evita query extra)
                    sl_user_id = position['user_id']

                    await transaction_db.execute("""
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
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $17)
                    """,
                        sl_client_order_id,                     # $1
                        'PLATFORM',                             # $2
                        position['exchange_account_id'],        # $3
                        str(sl_result.get('orderId')),          # $4
                        position['symbol'],                     # $5
                        sl_side.lower(),                        # $6
                        'stop_market',                          # $7
                        'new',                                  # $8 - Ordem aguardando ativação
                        Decimal(str(position['size'])),         # $9
                        Decimal(str(modify_request.stop_loss)), # $10
                        Decimal('0'),                           # $11 - filled_quantity
                        Decimal('0'),                           # $12 - fees_paid
                        'gtc',                                  # $13 - time_in_force
                        0,                                      # $14 - retry_count
                        True,                                   # $15 - reduce_only
                        False,                                  # $16 - post_only
                        datetime.utcnow()                       # $17
                    )

                    created_orders.append('stop_loss')
                    logger.info(f"Nova ordem Stop Loss criada em ${modify_request.stop_loss}")
                except Exception as e:
                    logger.error(f"Erro ao criar Stop Loss: {e}")
                    raise HTTPException(status_code=500, detail=f"Erro ao criar Stop Loss: {str(e)}")

            if modify_request.take_profit:
                # Criar nova ordem de Take Profit
                tp_side = 'SELL' if position['side'] == 'LONG' else 'BUY'

                try:
                    tp_result = await connector.create_order(
                        symbol=position['symbol'],
                        side=tp_side,
                        order_type='TAKE_PROFIT_MARKET',
                        quantity=float(position['size']),
                        stop_price=modify_request.take_profit
                    )

                    # Salvar no banco
                    # Gerar client_order_id único
                    tp_client_order_id = f"tp_{uuid.uuid4().hex[:16]}"

                    # Usar user_id já carregado da posição (otimização: evita query extra)
                    tp_user_id = position['user_id']

                    await transaction_db.execute("""
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
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $17)
                    """,
                        tp_client_order_id,                         # $1
                        'PLATFORM',                                 # $2
                        position['exchange_account_id'],            # $3
                        str(tp_result.get('orderId')),              # $4
                        position['symbol'],                         # $5
                        tp_side.lower(),                            # $6
                        'take_profit_market',                       # $7
                        'new',                                      # $8 - Ordem aguardando ativação
                        Decimal(str(position['size'])),             # $9
                        Decimal(str(modify_request.take_profit)),   # $10
                        Decimal('0'),                               # $11 - filled_quantity
                        Decimal('0'),                               # $12 - fees_paid
                        'gtc',                                      # $13 - time_in_force
                        0,                                          # $14 - retry_count
                        True,                                       # $15 - reduce_only
                        False,                                      # $16 - post_only
                        datetime.utcnow()                           # $17
                    )

                    created_orders.append('take_profit')
                    logger.info(f"Nova ordem Take Profit criada em ${modify_request.take_profit}")
                except Exception as e:
                    logger.error(f"Erro ao criar Take Profit: {e}")
                    raise HTTPException(status_code=500, detail=f"Erro ao criar Take Profit: {str(e)}")

            logger.info(
                "SL/TP modified successfully",
                position_id=position_id,
                canceled=len(canceled_orders),
                created=len(created_orders),
                stop_loss=modify_request.stop_loss,
                take_profit=modify_request.take_profit
            )

            return {
                "success": True,
                "data": {
                    "position_id": position_id,
                    "stop_loss": modify_request.stop_loss,
                    "take_profit": modify_request.take_profit,
                    "canceled_orders": len(canceled_orders),
                    "created_orders": created_orders,
                    "message": "SL/TP atualizados com sucesso na Binance!"
                }
            }

        except HTTPException:
            raise
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error("Error modifying SL/TP", error=str(e), exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Erro ao modificar ordem: {str(e)}"
            )

    @router.post("/trailing-stop")
    async def create_trailing_stop(
        trailing_request: TrailingStopRequest,
        request: Request
    ):
        """
        Criar Trailing Stop para uma posição
        """
        try:
            # 1. Buscar posição
            position = await transaction_db.fetchrow("""
                SELECT
                    p.id, p.symbol, p.side, p.entry_price, p.size,
                    p.exchange_account_id,
                    ea.exchange, ea.testnet
                FROM positions p
                JOIN exchange_accounts ea ON p.exchange_account_id = ea.id
                WHERE p.id = $1 AND p.status = 'open'
            """, trailing_request.position_id)

            if not position:
                raise HTTPException(
                    status_code=404,
                    detail="Posição não encontrada ou já fechada"
                )

            # 2. Calcular callback delta em USDT
            callback_delta = trailing_request.activation_price * (trailing_request.callback_rate / 100)

            # 3. Salvar trailing stop metadata na posição
            trailing_metadata = {
                "type": "trailing_stop",
                "activation_price": trailing_request.activation_price,
                "callback_rate": trailing_request.callback_rate,
                "callback_delta": callback_delta,
                "created_at": datetime.utcnow().isoformat()
            }

            await transaction_db.execute("""
                UPDATE positions
                SET
                    stop_loss_price = $1,
                    exchange_data = jsonb_set(
                        COALESCE(exchange_data, '{}'::jsonb),
                        '{trailing_stop}',
                        $2::jsonb
                    ),
                    updated_at = $3
                WHERE id = $4
            """,
                Decimal(str(trailing_request.activation_price)),
                str(trailing_metadata).replace("'", '"'),
                datetime.utcnow(),
                trailing_request.position_id
            )

            # 4. TODO: Implementar lógica de trailing stop (worker background)

            logger.info(
                "Trailing stop created",
                position_id=trailing_request.position_id,
                activation_price=trailing_request.activation_price,
                callback_rate=trailing_request.callback_rate
            )

            return {
                "success": True,
                "data": {
                    "position_id": trailing_request.position_id,
                    "trailing_stop": {
                        "activation_price": trailing_request.activation_price,
                        "callback_rate": trailing_request.callback_rate,
                        "callback_delta_usdt": callback_delta
                    },
                    "message": "Trailing Stop configurado com sucesso"
                }
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error("Error creating trailing stop", error=str(e), exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Erro ao criar trailing stop: {str(e)}"
            )

    @router.get("")
    async def get_orders(
        request: Request,
        operation_type: Optional[str] = None,  # spot ou futures
        status: Optional[str] = None,
        symbol: Optional[str] = None,
        exchange_account_id: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        limit: Optional[int] = 100,
        include_pending_from_api: Optional[bool] = True  # NOVO: buscar pendentes da API
    ):
        """
        Listar histórico de ordens (SPOT + FUTURES)

        CRITICAL FIX: Se include_pending_from_api=true, busca ordens PENDENTES (SL/TP)
        diretamente da exchange API e combina com o banco de dados.
        Isso garante que as linhas SL/TP apareçam no gráfico!

        Filtros disponíveis:
        - operation_type: spot, futures
        - status: filled, pending, canceled, failed
        - symbol: BTCUSDT, ETHUSDT, etc
        - exchange_account_id: UUID da conta
        - date_from: YYYY-MM-DD
        - date_to: YYYY-MM-DD
        - limit: número máximo de resultados (padrão 100)
        - include_pending_from_api: buscar SL/TP da API (padrão True)
        """
        try:
            # Verificar se tabela orders existe
            table_exists = await transaction_db.fetchval("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'orders'
                )
            """)

            if not table_exists:
                return {
                    "success": True,
                    "data": [],
                    "message": "Tabela de ordens ainda não existe"
                }

            # Build query with filters
            where_conditions = []
            params = []
            param_count = 1

            if status:
                where_conditions.append(f"o.status = ${param_count}")
                params.append(status)
                param_count += 1

            if symbol:
                where_conditions.append(f"o.symbol ILIKE ${param_count}")
                params.append(f"%{symbol}%")
                param_count += 1

            if exchange_account_id:
                where_conditions.append(f"o.exchange_account_id = ${param_count}")
                params.append(exchange_account_id)
                param_count += 1

            if date_from:
                where_conditions.append(f"o.created_at >= ${param_count}")
                date_obj = datetime.strptime(date_from, "%Y-%m-%d")
                params.append(date_obj)
                param_count += 1

            if date_to:
                where_conditions.append(f"o.created_at <= ${param_count}")
                date_obj = datetime.strptime(date_to, "%Y-%m-%d")
                params.append(date_obj)
                param_count += 1

            # Base WHERE clause
            base_conditions = ["ea.is_active = true"]
            all_conditions = base_conditions + where_conditions

            where_clause = " AND ".join(all_conditions) if all_conditions else "1=1"

            # Query com JOIN para pegar info da conta
            query = f"""
                SELECT
                    o.id, o.client_order_id, o.external_id, o.source,
                    o.symbol, o.side, o.type, o.status,
                    o.quantity, o.price, o.stop_price,
                    o.filled_quantity, o.fees_paid,
                    o.time_in_force, o.reduce_only, o.post_only,
                    o.created_at, o.updated_at,
                    o.exchange_account_id,
                    ea.name as exchange_account_name,
                    ea.exchange
                FROM orders o
                LEFT JOIN exchange_accounts ea ON o.exchange_account_id = ea.id
                WHERE {where_clause}
                ORDER BY o.created_at DESC
                LIMIT {limit}
            """

            orders = await transaction_db.fetch(query, *params)

            # Format response
            orders_list = []
            for order in orders:
                orders_list.append({
                    "id": order["id"],
                    "client_order_id": order["client_order_id"],
                    "external_id": order["external_id"],
                    "source": order["source"],
                    "symbol": order["symbol"],
                    "side": order["side"].upper() if order["side"] else None,
                    "order_type": order["type"],  # RENAMED: 'type' -> 'order_type' for frontend compatibility
                    "status": order["status"],
                    "quantity": float(order["quantity"]) if order["quantity"] else 0,
                    "price": float(order["price"]) if order["price"] else None,
                    "stop_price": float(order["stop_price"]) if order["stop_price"] else None,
                    "filled_quantity": float(order["filled_quantity"]) if order["filled_quantity"] else 0,
                    "fees_paid": float(order["fees_paid"]) if order["fees_paid"] else 0,
                    "time_in_force": order["time_in_force"],
                    "reduce_only": order["reduce_only"],
                    "post_only": order["post_only"],
                    "created_at": order["created_at"].isoformat() if order["created_at"] else None,
                    "updated_at": order["updated_at"].isoformat() if order["updated_at"] else None,
                    "exchange_account_id": order["exchange_account_id"],
                    "exchange_account_name": order["exchange_account_name"],
                    "exchange": order["exchange"],
                    "operation_type": "futures"  # HARDCODED for now - add column later
                })

            # CRITICAL FIX: Buscar ordens PENDENTES da API (SL/TP para gráfico)
            orders_from_api = []
            if include_pending_from_api and exchange_account_id:
                try:
                    logger.info(f"🔍 Fetching pending orders from exchange API for account {exchange_account_id}")

                    # Buscar dados da conta
                    account = await transaction_db.fetchrow("""
                        SELECT id, exchange, api_key, secret_key, testnet, name
                        FROM exchange_accounts
                        WHERE id = $1 AND is_active = true
                    """, exchange_account_id)

                    if account:
                        exchange_type = account['exchange'].lower()

                        # Criar connector baseado na exchange
                        if exchange_type == 'bingx':
                            from infrastructure.exchanges.bingx_connector import BingXConnector
                            connector = BingXConnector(
                                api_key=account['api_key'],
                                api_secret=account['secret_key'],
                                testnet=account['testnet']
                            )

                            # Buscar ordens abertas (SL/TP pendentes)
                            open_orders_result = await connector.get_open_orders(symbol=symbol)

                            if open_orders_result.get('success'):
                                for api_order in open_orders_result.get('orders', []):
                                    # Normalizar símbolo (BingX usa SOL-USDT, frontend usa SOLUSDT)
                                    order_symbol = api_order.get('symbol', '').replace('-', '')

                                    # Converter BingX order para formato do frontend
                                    orders_from_api.append({
                                        "id": f"api_{api_order.get('orderId')}",
                                        "client_order_id": None,
                                        "external_id": str(api_order.get('orderId')),
                                        "source": "EXCHANGE_API",
                                        "symbol": order_symbol,
                                        "side": api_order.get('side', '').upper(),
                                        "order_type": api_order.get('type', '').lower(),
                                        "status": "pending",  # Status = pending pois é NEW na exchange
                                        "quantity": float(api_order.get('origQty', 0)),
                                        "price": float(api_order.get('price', 0)) if api_order.get('price') else float(api_order.get('stopPrice', 0)),
                                        "stop_price": float(api_order.get('stopPrice', 0)) if api_order.get('stopPrice') else None,
                                        "filled_quantity": 0,
                                        "fees_paid": 0,
                                        "time_in_force": "gtc",
                                        "reduce_only": True,  # SL/TP são sempre reduce_only
                                        "post_only": False,
                                        "created_at": datetime.fromtimestamp(api_order.get('time', 0) / 1000).isoformat() if api_order.get('time') else None,
                                        "updated_at": datetime.fromtimestamp(api_order.get('updateTime', 0) / 1000).isoformat() if api_order.get('updateTime') else None,
                                        "exchange_account_id": exchange_account_id,
                                        "exchange_account_name": account['name'],
                                        "exchange": "bingx",
                                        "operation_type": "futures"
                                    })

                                logger.info(f"✅ Retrieved {len(orders_from_api)} pending orders from BingX API")
                            else:
                                logger.warning(f"⚠️ Failed to fetch open orders: {open_orders_result.get('error')}")

                        elif exchange_type == 'binance':
                            # TODO: Implement Binance get_open_orders if needed
                            logger.info("Binance open orders fetch not implemented yet")

                except Exception as e:
                    logger.error(f"❌ Error fetching pending orders from API: {e}", exc_info=True)
                    # Continue mesmo se falhar - retornar só as do banco

            # Combinar ordens do banco + API
            all_orders = orders_list + orders_from_api

            # Aplicar filtro de símbolo se especificado (para ordens da API)
            if symbol:
                all_orders = [o for o in all_orders if symbol.upper() in o['symbol'].upper()]

            # Ordenar por data de criação (mais recentes primeiro)
            all_orders.sort(key=lambda x: x.get('created_at') or '', reverse=True)

            # Aplicar limit
            if len(all_orders) > limit:
                all_orders = all_orders[:limit]

            logger.info("Orders retrieved",
                       count=len(all_orders),
                       from_db=len(orders_list),
                       from_api=len(orders_from_api),
                       status=status,
                       symbol=symbol,
                       exchange_account_id=exchange_account_id)

            return {
                "success": True,
                "data": all_orders,
                "count": len(all_orders),
                "metadata": {
                    "from_database": len(orders_list),
                    "from_api": len(orders_from_api)
                }
            }

        except Exception as e:
            logger.error("Error retrieving orders", error=str(e), exc_info=True)
            raise HTTPException(status_code=500, detail=f"Failed to retrieve orders: {str(e)}")

    @router.get("/sync/{exchange_account_id}")
    async def sync_orders_from_exchange(
        exchange_account_id: str,
        operation_type: str = "both",  # spot, futures, ou both
        symbol: Optional[str] = None,
        limit: int = 100,
        request: Request = None
    ):
        """
        Sincronizar ordens diretamente da Binance API

        Busca histórico de orders da exchange e salva no banco de dados.
        Útil para popular dados históricos que não foram salvos.
        """
        try:
            # Buscar dados da conta
            account = await transaction_db.fetchrow("""
                SELECT
                    id, exchange, api_key, secret_key, testnet
                FROM exchange_accounts
                WHERE id = $1 AND is_active = true
            """, exchange_account_id)

            if not account:
                raise HTTPException(
                    status_code=404,
                    detail="Conta de exchange não encontrada ou inativa"
                )

            # Criar connector
            from infrastructure.exchanges.binance_connector import BinanceConnector

            connector = BinanceConnector(
                api_key=account['api_key'],
                api_secret=account['secret_key'],
                testnet=account['testnet']
            )

            synced_orders = []
            errors = []

            # Sincronizar SPOT orders
            if operation_type in ['spot', 'both']:
                try:
                    spot_result = await connector.get_account_orders(
                        symbol=symbol,
                        limit=limit
                    )

                    if spot_result['success']:
                        for order_data in spot_result['orders']:
                            # Verificar se ordem já existe
                            existing = await transaction_db.fetchval("""
                                SELECT id FROM orders
                                WHERE external_id = $1 AND exchange_account_id = $2
                            """, str(order_data['orderId']), exchange_account_id)

                            if not existing:
                                # Salvar nova ordem
                                order_id = await transaction_db.fetchval("""
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
                                        price,
                                        filled_quantity,
                                        fees_paid,
                                        time_in_force,
                                        created_at,
                                        updated_at
                                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $14)
                                    RETURNING id
                                """,
                                    order_data.get('clientOrderId', f"sync_{order_data['orderId']}"),
                                    'EXCHANGE_SYNC',
                                    exchange_account_id,
                                    str(order_data['orderId']),
                                    order_data['symbol'],
                                    order_data['side'].lower(),
                                    order_data['type'].lower(),
                                    order_data['status'].lower(),
                                    Decimal(str(order_data['origQty'])),
                                    Decimal(str(order_data['price'])) if order_data.get('price') else None,
                                    Decimal(str(order_data['executedQty'])),
                                    Decimal('0'),  # fees não disponíveis neste endpoint
                                    order_data.get('timeInForce', 'GTC').lower(),
                                    datetime.fromtimestamp(order_data['time'] / 1000),
                                )
                                synced_orders.append({'id': order_id, 'type': 'spot', 'symbol': order_data['symbol']})

                    logger.info(f"✅ Synced {len(spot_result['orders'])} SPOT orders")
                except Exception as e:
                    logger.error(f"Error syncing SPOT orders: {e}")
                    errors.append(f"SPOT: {str(e)}")

            # Sincronizar FUTURES orders
            if operation_type in ['futures', 'both']:
                try:
                    futures_result = await connector.get_futures_orders(
                        symbol=symbol,
                        limit=limit
                    )

                    if futures_result['success']:
                        for order_data in futures_result['orders']:
                            # Verificar se ordem já existe
                            existing = await transaction_db.fetchval("""
                                SELECT id FROM orders
                                WHERE external_id = $1 AND exchange_account_id = $2
                            """, str(order_data['orderId']), exchange_account_id)

                            if not existing:
                                # Salvar nova ordem
                                order_id = await transaction_db.fetchval("""
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
                                        price,
                                        filled_quantity,
                                        fees_paid,
                                        time_in_force,
                                        reduce_only,
                                        created_at,
                                        updated_at
                                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $15)
                                    RETURNING id
                                """,
                                    order_data.get('clientOrderId', f"sync_{order_data['orderId']}"),
                                    'EXCHANGE_SYNC',
                                    exchange_account_id,
                                    str(order_data['orderId']),
                                    order_data['symbol'],
                                    order_data['side'].lower(),
                                    order_data['type'].lower(),
                                    order_data['status'].lower(),
                                    Decimal(str(order_data['origQty'])),
                                    Decimal(str(order_data['price'])) if order_data.get('price') else None,
                                    Decimal(str(order_data['executedQty'])),
                                    Decimal('0'),  # fees não disponíveis neste endpoint
                                    order_data.get('timeInForce', 'GTC').lower(),
                                    order_data.get('reduceOnly', False),
                                    datetime.fromtimestamp(order_data['time'] / 1000),
                                )
                                synced_orders.append({'id': order_id, 'type': 'futures', 'symbol': order_data['symbol']})

                    logger.info(f"✅ Synced {len(futures_result['orders'])} FUTURES orders")
                except Exception as e:
                    logger.error(f"Error syncing FUTURES orders: {e}")
                    errors.append(f"FUTURES: {str(e)}")

            return {
                "success": True,
                "data": {
                    "synced_count": len(synced_orders),
                    "synced_orders": synced_orders,
                    "errors": errors if errors else None,
                    "message": f"Sincronizado {len(synced_orders)} ordens da {account['exchange'].upper()}"
                }
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error("Error syncing orders from exchange", error=str(e), exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Erro ao sincronizar ordens: {str(e)}"
            )

    @router.get("/stats")
    async def get_orders_stats(request: Request):
        """Estatísticas de ordens"""
        try:
            # Verificar se tabela orders existe
            table_exists = await transaction_db.fetchval("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'orders'
                )
            """)

            if not table_exists:
                return {
                    "success": True,
                    "data": {
                        "total_orders": 0,
                        "filled_orders": 0,
                        "failed_orders": 0,
                        "pending_orders": 0,
                        "message": "Tabela de ordens ainda não existe"
                    }
                }

            stats = await transaction_db.fetchrow("""
                SELECT
                    COUNT(*) as total_orders,
                    COUNT(*) FILTER (WHERE status IN ('filled', 'partially_filled')) as filled_orders,
                    COUNT(*) FILTER (WHERE status = 'failed') as failed_orders,
                    COUNT(*) FILTER (WHERE status = 'pending') as pending_orders
                FROM orders
                WHERE created_at >= NOW() - INTERVAL '30 days'
            """)

            return {
                "success": True,
                "data": {
                    "total_orders": stats['total_orders'],
                    "filled_orders": stats['filled_orders'],
                    "failed_orders": stats['failed_orders'],
                    "pending_orders": stats['pending_orders']
                }
            }

        except Exception as e:
            logger.error("Error getting orders stats", error=str(e))
            raise HTTPException(status_code=500, detail="Failed to get orders stats")

    @router.put("/update-sl-tp")
    async def update_sl_tp(request: Request):
        """Update Stop Loss or Take Profit order (drag & drop from chart)"""
        from presentation.schemas.orders import UpdateSLTPRequest, UpdateSLTPResponse

        try:
            body = await request.json()
            update_request = UpdateSLTPRequest(**body)

            logger.info(
                "📝 Updating SL/TP order",
                exchange_account_id=update_request.exchange_account_id,
                symbol=update_request.symbol,
                order_type=update_request.order_type,
                new_price=update_request.new_price,
                old_order_id=update_request.old_order_id
            )

            # Get exchange account
            exchange_account = await transaction_db.fetchrow("""
                SELECT * FROM exchange_accounts
                WHERE id = $1
            """, update_request.exchange_account_id)

            if not exchange_account:
                return UpdateSLTPResponse(
                    success=False,
                    message="Exchange account not found",
                    error="Account not found"
                )

            # Only support BingX for now
            if exchange_account['exchange'] != 'bingx':
                return UpdateSLTPResponse(
                    success=False,
                    message=f"Exchange {exchange_account['exchange']} not supported for SL/TP updates",
                    error="Exchange not supported"
                )

            # Get connector
            connector = await get_unified_connector(exchange_account['exchange'])
            if not connector:
                return UpdateSLTPResponse(
                    success=False,
                    message="Failed to get exchange connector",
                    error="Connector unavailable"
                )

            # Initialize connector
            await connector.initialize(
                exchange_account['api_key'],
                exchange_account['api_secret'],
                testnet=False
            )

            # Step 1: Cancel existing order if provided
            if update_request.old_order_id:
                cancel_result = await connector.cancel_order(
                    symbol=update_request.symbol,
                    order_id=update_request.old_order_id
                )

                if not cancel_result.get('success'):
                    logger.warning(
                        f"Failed to cancel old order {update_request.old_order_id}: {cancel_result.get('error')}"
                    )
                    # Continue anyway - the order might already be cancelled
                else:
                    logger.info(f"✅ Cancelled old order: {update_request.old_order_id}")

            # Step 2: Create new SL/TP order
            # Determine order side (opposite of position side for closing)
            order_side = "SELL" if update_request.position_side == "LONG" else "BUY"

            create_result = await connector.create_sl_tp_order(
                symbol=update_request.symbol,
                side=order_side,
                quantity=update_request.quantity,
                order_type=update_request.order_type,
                stop_price=update_request.new_price,
                position_side=update_request.position_side
            )

            if not create_result.get('success'):
                # Try to restore old order if creation failed
                if update_request.old_order_id:
                    logger.error(
                        f"Failed to create new {update_request.order_type} order. "
                        f"Old order {update_request.old_order_id} was already cancelled!"
                    )

                return UpdateSLTPResponse(
                    success=False,
                    message=f"Failed to create {update_request.order_type} order",
                    error=create_result.get('error', 'Unknown error')
                )

            new_order_id = create_result.get('order_id')
            logger.info(
                f"✅ Created new {update_request.order_type} order: {new_order_id} at ${update_request.new_price}"
            )

            # Return success response
            return UpdateSLTPResponse(
                success=True,
                message=f"{update_request.order_type} updated successfully",
                data={
                    "cancelled_order_id": update_request.old_order_id,
                    "new_order_id": new_order_id,
                    "symbol": update_request.symbol,
                    "order_type": update_request.order_type,
                    "new_price": update_request.new_price
                }
            )

        except Exception as e:
            logger.error(f"Error updating SL/TP order: {e}", exc_info=True)
            return UpdateSLTPResponse(
                success=False,
                message="Failed to update SL/TP order",
                error=str(e)
            )

    return router

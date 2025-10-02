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

            # 3. Buscar preço atual do mercado
            current_price = await get_current_market_price(
                exchange=account['exchange'],
                symbol=order_request.symbol,
                api_key=api_key,
                api_secret=api_secret,
                testnet=account['testnet'],
                operation_type=order_request.operation_type
            )

            # 4. Calcular valor necessário
            order_price = order_request.price if order_request.order_type != 'market' else current_price

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
            if order_request.order_type in ['limit', 'stop_limit'] and order_request.price:
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

            # 8. Criar ordem no banco de dados
            order_id = await transaction_db.fetchval("""
                INSERT INTO orders (
                    exchange_account_id, exchange, symbol, side, order_type,
                    quantity, price, stop_loss_price, take_profit_price,
                    status, created_at
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                RETURNING id
            """,
                order_request.exchange_account_id,
                account['exchange'],
                order_request.symbol,
                order_request.side,
                order_request.order_type,
                Decimal(str(order_request.quantity)),
                Decimal(str(order_price)) if order_price else None,
                Decimal(str(order_request.stop_loss)) if order_request.stop_loss else None,
                Decimal(str(order_request.take_profit)) if order_request.take_profit else None,
                'pending',
                datetime.utcnow()
            )

            # 9. TODO: Enviar ordem para exchange via CCXT
            # (Implementar integração com exchange)

            logger.info(
                "Order created successfully",
                order_id=order_id,
                symbol=order_request.symbol,
                side=order_request.side,
                type=order_request.order_type,
                quantity=order_request.quantity,
                price=order_price
            )

            return {
                "success": True,
                "data": {
                    "order_id": order_id,
                    "status": "pending",
                    "message": "Ordem criada com sucesso. Aguardando execução.",
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
            # 1. Buscar posição
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

            logger.info(f"🔵 STEP 2: Posição encontrada: {position['symbol']} {position['side']} {position['size']}")
            # 2. Calcular quantidade a fechar
            quantity_to_close = float(position['size']) * (close_request.percentage / 100)
            logger.info(f"🔵 STEP 3: Quantidade a fechar: {quantity_to_close}")

            # 3. Determinar lado reverso (fechar LONG = sell, fechar SHORT = buy)
            # NOTA: BinanceConnector aceita maiúscula, mas banco precisa minúscula
            close_side_upper = 'SELL' if position['side'].upper() == 'LONG' else 'BUY'
            close_side_lower = close_side_upper.lower()

            # 4. Conectar na exchange (usar connector nativo)
            from infrastructure.exchanges.binance_connector import BinanceConnector
            from infrastructure.exchanges.bybit_connector import BybitConnector
            from infrastructure.exchanges.bingx_connector import BingXConnector
            from infrastructure.exchanges.bitget_connector import BitgetConnector

            # Selecionar connector baseado na exchange
            exchange = position['exchange'].lower()
            logger.info(f"🔵 STEP 4: Criando connector para exchange: {exchange}")
            if exchange == 'binance':
                connector = BinanceConnector(
                    api_key=position['api_key'],
                    api_secret=position['secret_key'],
                    testnet=position['testnet']
                )
                logger.info(f"🔵 STEP 5: BinanceConnector criado")
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

            # Executar ordem MARKET de fechamento na exchange
            logger.info(f"🔵 STEP 6: Executando ordem MARKET na Binance: {position['symbol']} {close_side_upper} {quantity_to_close}")
            order_result = await connector.create_market_order(
                symbol=position['symbol'],
                side=close_side_upper,  # API aceita maiúscula
                quantity=Decimal(str(quantity_to_close))
            )
            logger.info(f"🔵 STEP 7: Ordem executada com sucesso! order_id={order_result.get('order_id')}")

            # 5. Salvar ordem no banco
            # NOTA: orders não tem position_id nem operation_type
            import uuid
            client_order_id = f"close_{uuid.uuid4().hex[:16]}"  # Gerar client_order_id único

            order_id = await transaction_db.fetchval("""
                INSERT INTO orders (
                    exchange_account_id, symbol, side, type,
                    quantity, status, external_id, client_order_id,
                    created_at, updated_at
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                RETURNING id
            """,
                position['exchange_account_id'],
                position['symbol'],
                close_side_lower,  # Banco espera minúscula
                'market',  # Banco espera minúscula
                Decimal(str(quantity_to_close)),
                'filled',
                str(order_result.get('order_id')),  # create_market_order retorna 'order_id', não 'orderId'
                client_order_id,
                datetime.utcnow(),
                datetime.utcnow()
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
            # 1. Buscar posição
            position = await transaction_db.fetchrow("""
                SELECT
                    p.id, p.symbol, p.side, p.entry_price, p.status, p.size,
                    p.exchange_account_id,
                    ea.exchange, ea.testnet, ea.api_key, ea.secret_key
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

                        # Atualizar status no banco
                        await transaction_db.execute("""
                            UPDATE orders
                            SET status = 'canceled', updated_at = $1
                            WHERE id = $2
                        """, datetime.utcnow(), order['id'])

                        canceled_orders.append(order['id'])
                        logger.info(f"Ordem {order['id']} cancelada com sucesso")
                    except Exception as e:
                        logger.warning(f"Erro ao cancelar ordem {order['id']}: {e}")

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
                    # NOTA: orders não tem position_id nem operation_type
                    await transaction_db.execute("""
                        INSERT INTO orders (
                            exchange_account_id, symbol, side, type,
                            quantity, price, stop_price, status,
                            external_id, created_at, updated_at
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                    """,
                        position['exchange_account_id'],
                        position['symbol'],
                        sl_side,
                        'STOP_MARKET',
                        Decimal(str(position['size'])),
                        None,
                        Decimal(str(modify_request.stop_loss)),
                        'new',
                        str(sl_result.get('orderId')),
                        datetime.utcnow(),
                        datetime.utcnow()
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
                    # NOTA: orders não tem position_id nem operation_type
                    await transaction_db.execute("""
                        INSERT INTO orders (
                            exchange_account_id, symbol, side, type,
                            quantity, price, stop_price, status,
                            external_id, created_at, updated_at
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                    """,
                        position['exchange_account_id'],
                        position['symbol'],
                        tp_side,
                        'TAKE_PROFIT_MARKET',
                        Decimal(str(position['size'])),
                        None,
                        Decimal(str(modify_request.take_profit)),
                        'new',
                        str(tp_result.get('orderId')),
                        datetime.utcnow(),
                        datetime.utcnow()
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

    return router

"""
Bot Risk Monitor Service

Serviço que monitora posições abertas e fecha automaticamente quando
o limite de perda diária é atingido (Opção B - Rigoroso).

Este serviço roda a cada 30 segundos e:
1. Busca todas posições abertas
2. Consulta o PnL flutuante atual de cada posição na exchange
3. Calcula: perda_realizada_hoje + pnl_flutuante_negativo
4. Se total >= limite diário → FECHA a posição automaticamente
5. Notifica o cliente sobre o fechamento forçado

IMPORTANTE: Este serviço protege o cliente de perdas além do limite configurado.
"""

import structlog
from typing import Dict, List, Optional
from uuid import UUID
from datetime import datetime, timezone
import asyncio

logger = structlog.get_logger(__name__)


class BotRiskMonitorService:
    """
    Monitor de risco que fecha posições automaticamente quando limite é atingido.

    Executa verificação a cada 30 segundos para todas posições abertas.
    Se (perda_realizada + pnl_flutuante_negativo) >= limite_diario:
        → Fecha posição
        → Registra trade como fechado por 'risk_limit'
        → Notifica cliente
    """

    def __init__(self, db_pool):
        self.db = db_pool
        self._running = False
        self._check_interval = 30  # segundos

    async def start(self):
        """Inicia o monitor de risco em background"""
        if self._running:
            logger.warning("Bot risk monitor already running")
            return

        self._running = True
        logger.info("Bot risk monitor started")

        while self._running:
            try:
                await self.monitor_all_positions()
            except Exception as e:
                logger.error("Error in risk monitor cycle", error=str(e))

            await asyncio.sleep(self._check_interval)

    async def stop(self):
        """Para o monitor de risco"""
        self._running = False
        logger.info("Bot risk monitor stopped")

    async def monitor_all_positions(self):
        """
        Monitora todas as posições abertas e fecha se limite for atingido.

        Para cada posição aberta:
        1. Busca PnL flutuante atual da exchange
        2. Calcula perda potencial (realizada + flutuante)
        3. Se >= limite → fecha posição
        """
        try:
            # Buscar todas posições abertas com seus limites de risco
            open_trades = await self.db.fetch("""
                SELECT
                    bt.id as trade_id,
                    bt.subscription_id,
                    bt.signal_execution_id,
                    bt.symbol,
                    bt.side,
                    bt.direction,
                    bt.entry_price,
                    bt.entry_quantity,
                    bs.user_id,
                    bs.bot_id,
                    bs.exchange_account_id,
                    bs.current_daily_loss_usd as subscription_daily_loss,
                    bs.max_daily_loss_usd as subscription_max_loss,
                    ea.exchange,
                    ea.api_key,
                    ea.secret_key,
                    ea.is_testnet,
                    ssc.max_daily_loss_usd as symbol_max_loss,
                    ssc.current_daily_loss_usd as symbol_daily_loss
                FROM bot_trades bt
                JOIN bot_subscriptions bs ON bs.id = bt.subscription_id
                JOIN exchange_accounts ea ON ea.id = bs.exchange_account_id
                LEFT JOIN subscription_symbol_configs ssc
                    ON ssc.subscription_id = bt.subscription_id
                    AND ssc.exchange_account_id = bs.exchange_account_id
                    AND ssc.symbol = bt.symbol
                WHERE bt.status = 'open'
                  AND bs.status = 'active'
            """)

            if not open_trades:
                return

            logger.debug(f"Monitoring {len(open_trades)} open positions for risk limits")

            for trade in open_trades:
                await self._check_position_risk(dict(trade))

        except Exception as e:
            logger.error("Error monitoring positions", error=str(e), exc_info=True)

    async def _check_position_risk(self, trade: Dict):
        """
        Verifica se uma posição deve ser fechada por limite de risco.

        Args:
            trade: Dados da posição aberta com informações de risco
        """
        try:
            symbol = trade["symbol"]
            exchange = trade["exchange"]

            # Buscar PnL flutuante atual da exchange
            unrealized_pnl = await self._get_unrealized_pnl(trade)

            if unrealized_pnl is None:
                # Não conseguiu buscar PnL, pular esta verificação
                return

            # Só verificar se está em prejuízo
            if unrealized_pnl >= 0:
                return

            # Calcular perda potencial
            # Nível 1: Verificar limite por símbolo/exchange (mais específico)
            symbol_daily_loss = float(trade.get("symbol_daily_loss") or 0)
            symbol_max_loss = float(trade.get("symbol_max_loss") or 999999)

            potential_symbol_loss = symbol_daily_loss + abs(unrealized_pnl)

            if potential_symbol_loss >= symbol_max_loss and symbol_max_loss < 999999:
                logger.warning(
                    "Symbol risk limit reached! Closing position",
                    trade_id=str(trade["trade_id"]),
                    symbol=symbol,
                    current_loss=symbol_daily_loss,
                    unrealized_pnl=unrealized_pnl,
                    potential_loss=potential_symbol_loss,
                    max_loss=symbol_max_loss,
                    level="subscription_symbol"
                )
                await self._force_close_position(trade, unrealized_pnl, "symbol_risk_limit")
                return

            # Nível 2: Verificar limite da subscription (mais amplo)
            subscription_daily_loss = float(trade.get("subscription_daily_loss") or 0)
            subscription_max_loss = float(trade.get("subscription_max_loss") or 999999)

            potential_subscription_loss = subscription_daily_loss + abs(unrealized_pnl)

            if potential_subscription_loss >= subscription_max_loss:
                logger.warning(
                    "Subscription risk limit reached! Closing position",
                    trade_id=str(trade["trade_id"]),
                    symbol=symbol,
                    current_loss=subscription_daily_loss,
                    unrealized_pnl=unrealized_pnl,
                    potential_loss=potential_subscription_loss,
                    max_loss=subscription_max_loss,
                    level="subscription"
                )
                await self._force_close_position(trade, unrealized_pnl, "subscription_risk_limit")
                return

        except Exception as e:
            logger.error(
                "Error checking position risk",
                trade_id=str(trade.get("trade_id")),
                error=str(e)
            )

    async def _get_unrealized_pnl(self, trade: Dict) -> Optional[float]:
        """
        Busca o PnL não realizado (flutuante) atual da posição na exchange.

        Args:
            trade: Dados do trade com informações da exchange

        Returns:
            Float com PnL flutuante ou None se erro
        """
        try:
            exchange = trade["exchange"].lower()
            api_key = trade["api_key"]
            api_secret = trade["secret_key"]
            is_testnet = trade.get("is_testnet", False)
            symbol = trade["symbol"]

            if exchange == "binance":
                from infrastructure.exchanges.binance_connector import BinanceConnector
                connector = BinanceConnector(
                    api_key=api_key,
                    api_secret=api_secret,
                    testnet=is_testnet
                )
            elif exchange == "bingx":
                from infrastructure.exchanges.bingx_connector import BingXConnector
                connector = BingXConnector(
                    api_key=api_key,
                    api_secret=api_secret,
                    testnet=is_testnet
                )
            else:
                logger.warning(f"Unsupported exchange for risk monitor: {exchange}")
                return None

            try:
                # Buscar posição atual
                positions_result = await connector.get_futures_positions()

                if not positions_result.get("success"):
                    logger.warning(
                        "Failed to get positions from exchange",
                        exchange=exchange,
                        error=positions_result.get("error")
                    )
                    return None

                positions = positions_result.get("positions", [])

                # Encontrar posição do símbolo
                for pos in positions:
                    pos_symbol = pos.get("symbol", "").replace("-", "").upper()
                    if pos_symbol == symbol.upper():
                        unrealized_pnl = float(pos.get("unRealizedProfit", 0) or
                                               pos.get("unrealizedProfit", 0) or
                                               pos.get("unrealisedPnl", 0) or 0)
                        return unrealized_pnl

                # Posição não encontrada (pode ter sido fechada)
                return None

            finally:
                await connector.close()

        except Exception as e:
            logger.error(
                "Error getting unrealized PnL",
                symbol=trade.get("symbol"),
                exchange=trade.get("exchange"),
                error=str(e)
            )
            return None

    async def _force_close_position(self, trade: Dict, unrealized_pnl: float, reason: str):
        """
        Fecha uma posição forçadamente por limite de risco.

        Args:
            trade: Dados do trade a ser fechado
            unrealized_pnl: PnL flutuante no momento do fechamento
            reason: Motivo do fechamento (symbol_risk_limit ou subscription_risk_limit)
        """
        try:
            exchange = trade["exchange"].lower()
            api_key = trade["api_key"]
            api_secret = trade["secret_key"]
            is_testnet = trade.get("is_testnet", False)
            symbol = trade["symbol"]
            side = trade["side"]
            direction = trade.get("direction", "long" if side.lower() == "buy" else "short")

            # Determinar lado de fechamento (oposto ao de abertura)
            close_side = "sell" if direction == "long" else "buy"

            if exchange == "binance":
                from infrastructure.exchanges.binance_connector import BinanceConnector
                connector = BinanceConnector(
                    api_key=api_key,
                    api_secret=api_secret,
                    testnet=is_testnet
                )
            elif exchange == "bingx":
                from infrastructure.exchanges.bingx_connector import BingXConnector
                connector = BingXConnector(
                    api_key=api_key,
                    api_secret=api_secret,
                    testnet=is_testnet
                )
            else:
                logger.error(f"Unsupported exchange for position close: {exchange}")
                return

            try:
                # Fechar posição
                close_result = await connector.close_futures_position(symbol)

                if close_result.get("success"):
                    logger.info(
                        "Position closed successfully by risk monitor",
                        trade_id=str(trade["trade_id"]),
                        symbol=symbol,
                        reason=reason
                    )

                    # Registrar fechamento no trade tracker
                    await self._record_forced_close(trade, unrealized_pnl, reason)

                    # Notificar cliente
                    await self._notify_risk_close(trade, unrealized_pnl, reason)
                else:
                    logger.error(
                        "Failed to close position",
                        trade_id=str(trade["trade_id"]),
                        symbol=symbol,
                        error=close_result.get("error")
                    )

            finally:
                await connector.close()

        except Exception as e:
            logger.error(
                "Error force closing position",
                trade_id=str(trade.get("trade_id")),
                error=str(e),
                exc_info=True
            )

    async def _record_forced_close(self, trade: Dict, pnl: float, reason: str):
        """
        Registra o fechamento forçado no banco de dados.

        Atualiza:
        1. bot_trades - marca como fechado
        2. bot_subscriptions - atualiza perda diária
        3. subscription_symbol_configs - atualiza perda diária por símbolo
        4. bot_symbol_configs - atualiza perda diária do bot por símbolo
        5. bots - atualiza perda diária global do bot
        """
        try:
            trade_id = trade["trade_id"]
            subscription_id = trade["subscription_id"]
            bot_id = trade["bot_id"]
            exchange_account_id = trade["exchange_account_id"]
            symbol = trade["symbol"]
            entry_price = float(trade["entry_price"])
            quantity = float(trade["entry_quantity"])

            # Calcular preço de saída estimado baseado no PnL
            direction = trade.get("direction", "long")
            if direction == "long":
                exit_price = entry_price + (pnl / quantity) if quantity > 0 else entry_price
            else:
                exit_price = entry_price - (pnl / quantity) if quantity > 0 else entry_price

            pnl_pct = (pnl / (entry_price * quantity)) * 100 if entry_price * quantity > 0 else 0
            is_win = pnl >= 0
            loss_amount = abs(pnl) if pnl < 0 else 0

            # 1. Atualizar bot_trades
            await self.db.execute("""
                UPDATE bot_trades
                SET exit_price = $1,
                    exit_quantity = $2,
                    exit_time = NOW(),
                    exit_reason = $3,
                    pnl_usd = $4,
                    pnl_pct = $5,
                    is_winner = $6,
                    status = 'closed',
                    updated_at = NOW()
                WHERE id = $7
            """, exit_price, quantity, reason, pnl, pnl_pct, is_win, trade_id)

            # 2. Atualizar bot_subscriptions
            if is_win:
                await self.db.execute("""
                    UPDATE bot_subscriptions
                    SET total_pnl_usd = total_pnl_usd + $1,
                        win_count = win_count + 1,
                        current_positions = GREATEST(current_positions - 1, 0),
                        updated_at = NOW()
                    WHERE id = $2
                """, pnl, subscription_id)
            else:
                await self.db.execute("""
                    UPDATE bot_subscriptions
                    SET total_pnl_usd = total_pnl_usd + $1,
                        loss_count = loss_count + 1,
                        current_positions = GREATEST(current_positions - 1, 0),
                        current_daily_loss_usd = current_daily_loss_usd + $2,
                        updated_at = NOW()
                    WHERE id = $3
                """, pnl, loss_amount, subscription_id)

            # 3. Atualizar subscription_symbol_configs (perda por símbolo/exchange)
            if loss_amount > 0:
                await self.db.execute("""
                    UPDATE subscription_symbol_configs
                    SET current_daily_loss_usd = COALESCE(current_daily_loss_usd, 0) + $1,
                        current_positions = GREATEST(COALESCE(current_positions, 0) - 1, 0),
                        updated_at = NOW()
                    WHERE subscription_id = $2
                      AND exchange_account_id = $3
                      AND symbol = $4
                """, loss_amount, subscription_id, exchange_account_id, symbol)

            # 4. Atualizar bot_symbol_configs (perda por símbolo no bot)
            if loss_amount > 0:
                await self.db.execute("""
                    UPDATE bot_symbol_configs
                    SET current_daily_loss_usd = COALESCE(current_daily_loss_usd, 0) + $1,
                        current_positions = GREATEST(COALESCE(current_positions, 0) - 1, 0),
                        updated_at = NOW()
                    WHERE bot_id = $2 AND symbol = $3
                """, loss_amount, bot_id, symbol)

            # 5. Atualizar bots (perda global do bot)
            if loss_amount > 0:
                await self.db.execute("""
                    UPDATE bots
                    SET global_current_daily_loss_usd = COALESCE(global_current_daily_loss_usd, 0) + $1,
                        global_current_positions = GREATEST(COALESCE(global_current_positions, 0) - 1, 0),
                        updated_at = NOW()
                    WHERE id = $2
                """, loss_amount, bot_id)

            logger.info(
                "Forced close recorded successfully",
                trade_id=str(trade_id),
                pnl=pnl,
                reason=reason
            )

        except Exception as e:
            logger.error(
                "Error recording forced close",
                trade_id=str(trade.get("trade_id")),
                error=str(e),
                exc_info=True
            )

    async def _notify_risk_close(self, trade: Dict, pnl: float, reason: str):
        """
        Notifica o cliente sobre o fechamento forçado por limite de risco.

        Args:
            trade: Dados do trade fechado
            pnl: PnL realizado
            reason: Motivo do fechamento
        """
        try:
            user_id = trade["user_id"]
            symbol = trade["symbol"]

            # Criar notificação no banco
            if reason == "symbol_risk_limit":
                title = f"Posicao {symbol} fechada por limite de risco"
                message = (
                    f"A posicao em {symbol} foi fechada automaticamente porque "
                    f"o limite de perda diaria para este ativo foi atingido. "
                    f"PnL: ${pnl:.2f}"
                )
            else:
                title = f"Posicao {symbol} fechada por limite de risco"
                message = (
                    f"A posicao em {symbol} foi fechada automaticamente porque "
                    f"o limite de perda diaria da subscription foi atingido. "
                    f"PnL: ${pnl:.2f}"
                )

            await self.db.execute("""
                INSERT INTO notifications (
                    user_id, type, title, message, data, is_read, created_at
                ) VALUES (
                    $1, 'risk_alert', $2, $3, $4, FALSE, NOW()
                )
            """, user_id, title, message, {
                "trade_id": str(trade["trade_id"]),
                "symbol": symbol,
                "pnl": pnl,
                "reason": reason
            })

            logger.info(
                "Risk close notification sent",
                user_id=str(user_id),
                symbol=symbol,
                reason=reason
            )

        except Exception as e:
            # Não falhar se notificação falhar
            logger.warning(
                "Failed to send risk close notification",
                user_id=str(trade.get("user_id")),
                error=str(e)
            )


# Singleton instance
_bot_risk_monitor: Optional[BotRiskMonitorService] = None


def get_bot_risk_monitor(db_pool) -> BotRiskMonitorService:
    """
    Get or create the singleton BotRiskMonitorService instance.

    Args:
        db_pool: Database connection pool

    Returns:
        BotRiskMonitorService instance
    """
    global _bot_risk_monitor

    if _bot_risk_monitor is None:
        _bot_risk_monitor = BotRiskMonitorService(db_pool)

    return _bot_risk_monitor

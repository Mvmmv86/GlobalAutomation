"""Enhanced TradingView Webhook Service with complete HMAC validation and order execution"""

import json
import hmac
import hashlib
import time
from typing import Dict, Any, Optional, List
from uuid import UUID
from datetime import datetime, timedelta
import structlog
from decimal import Decimal

from application.services.webhook_service import WebhookService
from application.services.secure_exchange_service import SecureExchangeService
from infrastructure.database.repositories import (
    ExchangeAccountRepository,
    UserRepository,
)
from infrastructure.database.models.webhook import WebhookDeliveryStatus
from infrastructure.database.models.exchange_account import (
    ExchangeType,
    ExchangeEnvironment,
)
from presentation.schemas.tradingview import TradingViewOrderWebhook


logger = structlog.get_logger()


class TradingViewWebhookService:
    """Enhanced service for processing TradingView webhooks with complete HMAC validation"""

    def __init__(
        self,
        webhook_service: WebhookService,
        secure_exchange_service: SecureExchangeService,
        exchange_account_repository: ExchangeAccountRepository,
        user_repository: UserRepository,
    ):
        self.webhook_service = webhook_service
        self.secure_exchange_service = secure_exchange_service
        self.exchange_account_repository = exchange_account_repository
        self.user_repository = user_repository

        # Configuration
        self.max_retries = 3
        self.retry_delays = [1, 5, 15]  # seconds
        self.signature_tolerance = 300  # 5 minutes tolerance for timestamp

    async def process_tradingview_webhook(
        self,
        webhook_id: UUID,
        payload: Dict[str, Any],
        headers: Dict[str, str],
        user_ip: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Process incoming TradingView webhook with complete validation and execution

        Args:
            webhook_id: Webhook configuration ID
            payload: Webhook payload from TradingView
            headers: HTTP headers
            user_ip: Client IP for additional security logging

        Returns:
            Processing result with order details
        """
        start_time = time.time()

        try:
            # Get webhook configuration
            webhook = await self.webhook_service.webhook_repository.get(webhook_id)
            if not webhook:
                raise ValueError(f"Webhook {webhook_id} not found")

            if not webhook.is_active:
                raise ValueError(f"Webhook {webhook_id} is disabled")

            logger.info(
                "Processing TradingView webhook",
                webhook_id=str(webhook_id),
                user_id=webhook.user_id,
                client_ip=user_ip,
                payload_keys=list(payload.keys()),
            )

            # Step 1: Enhanced HMAC Validation (skip if webhook is public)
            if not webhook.is_public:
                signature = headers.get("X-TradingView-Signature") or headers.get(
                    "X-Signature"
                )
                if webhook.secret:
                    is_valid = await self._enhanced_hmac_validation(
                        payload=payload,
                        signature=signature,
                        secret=webhook.secret,
                        headers=headers,
                        webhook_id=webhook_id,
                    )

                    if not is_valid:
                        await self._record_security_violation(
                            webhook_id, payload, headers, user_ip
                        )
                        raise ValueError("HMAC signature validation failed")
            else:
                logger.info("Public webhook - skipping HMAC validation", webhook_id=str(webhook_id))

            # Step 2: Validate and parse TradingView payload
            trading_signal = await self._validate_tradingview_payload(payload)

            # Step 3: Process the trading signal
            result = await self._process_trading_signal(
                webhook=webhook,
                trading_signal=trading_signal,
                payload=payload,
                headers=headers,
            )

            processing_time = time.time() - start_time

            logger.info(
                "TradingView webhook processed successfully",
                webhook_id=str(webhook_id),
                user_id=webhook.user_id,
                processing_time_ms=int(processing_time * 1000),
                orders_created=result.get("orders_created", 0),
                orders_executed=result.get("orders_executed", 0),
            )

            return {
                "success": True,
                "processing_time_ms": int(processing_time * 1000),
                **result,
            }

        except Exception as e:
            processing_time = time.time() - start_time

            logger.error(
                "TradingView webhook processing failed",
                webhook_id=str(webhook_id),
                error=str(e),
                processing_time_ms=int(processing_time * 1000),
                exc_info=True,
            )

            return {
                "success": False,
                "error": str(e),
                "processing_time_ms": int(processing_time * 1000),
            }

    async def _enhanced_hmac_validation(
        self,
        payload: Dict[str, Any],
        signature: Optional[str],
        secret: str,
        headers: Dict[str, str],
        webhook_id: UUID,
    ) -> bool:
        """
        Enhanced HMAC validation with multiple security checks

        Args:
            payload: Webhook payload
            signature: Received signature
            secret: Webhook secret
            headers: HTTP headers
            webhook_id: Webhook ID for logging

        Returns:
            True if validation passes
        """
        if not signature:
            logger.warning("No signature provided", webhook_id=str(webhook_id))
            return False

        # Normalize payload for consistent hashing
        normalized_payload = json.dumps(payload, separators=(",", ":"), sort_keys=True)

        # Check multiple signature formats
        valid_formats = [
            self._validate_signature_format(
                normalized_payload, signature, secret, "sha256="
            ),
            self._validate_signature_format(normalized_payload, signature, secret, ""),
            self._validate_signature_format(
                normalized_payload, signature, secret, "hmac-sha256="
            ),
        ]

        if not any(valid_formats):
            logger.warning(
                "HMAC signature validation failed - all formats",
                webhook_id=str(webhook_id),
                signature_length=len(signature) if signature else 0,
                payload_length=len(normalized_payload),
            )
            return False

        # Additional security checks
        timestamp = headers.get("X-Timestamp") or payload.get("timestamp")
        if timestamp:
            if not self._validate_timestamp(timestamp):
                logger.warning(
                    "Timestamp validation failed",
                    webhook_id=str(webhook_id),
                    timestamp=timestamp,
                )
                return False

        # Rate limiting check
        if not await self._check_rate_limiting(webhook_id):
            logger.warning("Rate limiting triggered", webhook_id=str(webhook_id))
            return False

        logger.info("HMAC signature validated successfully", webhook_id=str(webhook_id))
        return True

    def _validate_signature_format(
        self, payload: str, signature: str, secret: str, prefix: str
    ) -> bool:
        """Validate signature with specific format"""
        try:
            if signature.startswith(prefix):
                received_signature = signature[len(prefix) :]
            else:
                received_signature = signature

            expected_signature = hmac.new(
                secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256
            ).hexdigest()

            return hmac.compare_digest(expected_signature, received_signature)
        except Exception:
            return False

    def _validate_timestamp(self, timestamp: str) -> bool:
        """Validate webhook timestamp to prevent replay attacks"""
        try:
            # Try different timestamp formats
            ts_formats = [
                lambda x: int(x),  # Unix timestamp
                lambda x: int(
                    datetime.fromisoformat(x.replace("Z", "+00:00")).timestamp()
                ),  # ISO format
                lambda x: int(
                    datetime.strptime(x, "%Y-%m-%d %H:%M:%S").timestamp()
                ),  # Custom format
            ]

            webhook_time = None
            for fmt in ts_formats:
                try:
                    webhook_time = fmt(str(timestamp))
                    break
                except:
                    continue

            if webhook_time is None:
                return False

            current_time = int(time.time())
            time_diff = abs(current_time - webhook_time)

            return time_diff <= self.signature_tolerance

        except Exception as e:
            logger.warning(f"Timestamp validation error: {e}")
            return False

    async def _check_rate_limiting(self, webhook_id: UUID) -> bool:
        """Check rate limiting for webhook"""
        # Implementation would check recent webhook deliveries
        # For now, return True - can be enhanced with Redis rate limiting
        return True

    def _normalize_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normaliza payload para formato padrão, independente da origem
        Aceita formatos: simples (TradingView) e complexo (Indicadores customizados)
        """
        normalized = {}

        # 1. TICKER/SYMBOL - Priorizar 'ticker', fallback para 'symbol'
        if "ticker" in payload:
            normalized["ticker"] = payload["ticker"]
        elif "symbol" in payload:
            normalized["ticker"] = payload["symbol"]

        # 2. ACTION - Normalizar "Compra"/"Venda" para "buy"/"sell"
        action = payload.get("action", "").lower()
        if action in ["compra", "buy", "long"]:
            normalized["action"] = "buy"
        elif action in ["venda", "sell", "short"]:
            normalized["action"] = "sell"
        else:
            normalized["action"] = action

        # 3. PRICE - Extrair de diferentes locais
        if "price" in payload:
            normalized["price"] = payload["price"]
        elif "position" in payload and isinstance(payload["position"], dict):
            pos = payload["position"]
            if "entry_price" in pos:
                normalized["price"] = float(pos["entry_price"])

        # 4. QUANTITY - Extrair mas será IGNORADA (usaremos parâmetros do webhook)
        if "quantity" in payload:
            normalized["quantity"] = payload["quantity"]
        elif "position" in payload and isinstance(payload["position"], dict):
            pos = payload["position"]
            if "quantity" in pos:
                normalized["quantity"] = float(pos["quantity"])

        return normalized

    async def _validate_tradingview_payload(
        self, payload: Dict[str, Any]
    ) -> TradingViewOrderWebhook:
        """
        Validate and parse TradingView payload

        Args:
            payload: Raw webhook payload

        Returns:
            Validated TradingView signal
        """
        try:
            # 🔄 NORMALIZAR payload para aceitar múltiplos formatos (simples e complexo)
            normalized_payload = self._normalize_payload(payload)

            # Convert normalized payload to TradingView schema
            trading_signal = TradingViewOrderWebhook.parse_obj(normalized_payload)

            logger.info(
                "TradingView payload validated",
                ticker=trading_signal.ticker,
                action=trading_signal.action,
                order_type=trading_signal.order_type,
                quantity=str(trading_signal.quantity)
                if trading_signal.quantity
                else None,
            )

            return trading_signal

        except Exception as e:
            logger.error(f"TradingView payload validation failed: {e}")
            raise ValueError(f"Invalid TradingView payload: {e}")

    async def _process_trading_signal(
        self,
        webhook: Any,
        trading_signal: TradingViewOrderWebhook,
        payload: Dict[str, Any],
        headers: Dict[str, str],
    ) -> Dict[str, Any]:
        """
        Process validated trading signal and execute orders

        Args:
            webhook: Webhook configuration
            trading_signal: Validated TradingView signal
            payload: Original payload
            headers: HTTP headers

        Returns:
            Processing results
        """
        user_id = UUID(webhook.user_id)

        # Record webhook delivery
        delivery = await self.webhook_service.webhook_delivery_repository.create(
            {
                "webhook_id": str(webhook.id),
                "payload": payload,
                "headers": headers,
                "status": WebhookDeliveryStatus.PROCESSING,
                "processing_started_at": datetime.now(),
            }
        )

        try:
            # Get user's exchange accounts
            exchange_accounts = (
                await self.exchange_account_repository.get_user_active_accounts(user_id)
            )

            if not exchange_accounts:
                raise ValueError("No active exchange accounts found for user")

            # Select appropriate exchange account
            selected_account = await self._select_exchange_account(
                exchange_accounts, trading_signal
            )

            if not selected_account:
                raise ValueError(
                    "No suitable exchange account found for trading signal"
                )

            # Execute the trading order (passing webhook for trading parameters)
            order_result = await self._execute_trading_order(
                account=selected_account, user_id=user_id, signal=trading_signal, webhook=webhook
            )

            # Update delivery status
            processing_duration = int(
                (datetime.now() - delivery.processing_started_at).total_seconds() * 1000
            )

            await self.webhook_service.webhook_delivery_repository.update(
                delivery.id,
                {
                    "orders_created": 1,
                    "orders_executed": 1 if order_result.get("success") else 0,
                    "orders_failed": 0 if order_result.get("success") else 1,
                    "processing_duration_ms": processing_duration,
                },
            )

            await self.webhook_service.webhook_delivery_repository.update_delivery_status(
                delivery.id, WebhookDeliveryStatus.SUCCESS
            )

            return {
                "orders_created": 1,
                "orders_executed": 1 if order_result.get("success") else 0,
                "orders_failed": 0 if order_result.get("success") else 1,
                "order_details": order_result,
                "exchange_account": str(selected_account.id),
                "exchange_type": selected_account.exchange_type.value
                if hasattr(selected_account, "exchange_type")
                else "unknown",
            }

        except Exception as e:
            # Update delivery as failed
            await self.webhook_service.webhook_delivery_repository.update_delivery_status(
                delivery.id,
                WebhookDeliveryStatus.FAILED,
                error_message=str(e),
                error_details={"error_type": type(e).__name__},
            )

            raise

    async def _select_exchange_account(
        self, exchange_accounts: List[Any], signal: TradingViewOrderWebhook
    ) -> Optional[Any]:
        """
        Select appropriate exchange account for trading signal

        Args:
            exchange_accounts: Available exchange accounts
            signal: TradingView signal

        Returns:
            Selected exchange account
        """
        # Priority selection logic:
        # 1. Account matching signal's exchange preference
        # 2. Default account for the exchange type
        # 3. First active account

        preferred_exchange = signal.exchange
        if preferred_exchange:
            for account in exchange_accounts:
                if (
                    hasattr(account, "exchange_type")
                    and account.exchange_type.value.lower()
                    == preferred_exchange.lower()
                ):
                    return account

        # Look for default account
        for account in exchange_accounts:
            if hasattr(account, "is_default") and account.is_default:
                return account

        # Return first active account
        return exchange_accounts[0] if exchange_accounts else None

    async def _execute_trading_order(
        self,
        account: Any,
        user_id: UUID,
        signal: TradingViewOrderWebhook,
        webhook: Any = None,
    ) -> Dict[str, Any]:
        """
        Execute trading order on selected exchange

        Args:
            account: Exchange account
            user_id: User ID
            signal: TradingView signal
            webhook: Webhook configuration with trading parameters

        Returns:
            Order execution result
        """
        try:
            # Handle different actions
            if signal.action == "close":
                return await self._close_positions(account, user_id, signal)
            else:
                return await self._create_order(account, user_id, signal, webhook)

        except Exception as e:
            logger.error(
                "Order execution failed",
                account_id=str(account.id),
                user_id=str(user_id),
                signal_action=signal.action,
                error=str(e),
            )
            return {"success": False, "error": str(e), "order_id": None}

    async def _create_order(
        self,
        account: Any,
        user_id: UUID,
        signal: TradingViewOrderWebhook,
        webhook: Any = None,
    ) -> Dict[str, Any]:
        """Create new trading order using webhook trading parameters"""

        # ✅ NOVA LÓGICA: Usar parâmetros do webhook para calcular quantidade
        if webhook and hasattr(webhook, 'default_margin_usd') and hasattr(webhook, 'default_leverage'):
            # Buscar preço atual do símbolo
            try:
                # TODO: Implementar busca de preço da exchange
                # Por enquanto, usar preço do signal se disponível, senão usar valor default
                current_price = float(signal.price) if signal.price else 50000.0  # Fallback

                margin_usd = float(webhook.default_margin_usd)
                leverage = int(webhook.default_leverage)

                # 🎯 FÓRMULA DO TRADINGPANEL (linha 224):
                # quantity = (margin_usd * leverage) / current_price
                calculated_quantity = (margin_usd * leverage) / current_price

                quantity = Decimal(str(calculated_quantity))

                logger.info(
                    "Quantity calculated from webhook parameters",
                    margin_usd=margin_usd,
                    leverage=leverage,
                    current_price=current_price,
                    calculated_quantity=calculated_quantity,
                    symbol=signal.ticker
                )
            except Exception as e:
                logger.warning(f"Failed to calculate quantity from webhook params: {e}, using default")
                quantity = signal.quantity or Decimal("0.001")
        else:
            # Fallback: usar quantidade do signal ou valor padrão
            quantity = signal.quantity or Decimal("0.001")

        # Criar ordem principal
        order_result = await self.secure_exchange_service.create_order(
            account_id=account.id,
            user_id=user_id,
            symbol=signal.ticker,
            side=signal.action,  # buy/sell
            order_type=signal.order_type or "market",
            quantity=str(quantity),
            price=str(signal.price) if signal.price else None,
        )

        entry_price = float(signal.price) if signal.price else None

        # ✅ NOVO: Colocar ordens de Stop Loss e Take Profit se configurado
        sl_order = None
        tp_order = None

        if webhook and entry_price:
            try:
                # Stop Loss Order
                if hasattr(webhook, 'default_stop_loss_pct') and webhook.default_stop_loss_pct:
                    sl_pct = float(webhook.default_stop_loss_pct)
                    # Calcular preço de stop loss
                    if signal.action == "buy":
                        sl_price = entry_price * (1 - sl_pct / 100)  # Para compra: SL abaixo do entry
                    else:
                        sl_price = entry_price * (1 + sl_pct / 100)  # Para venda: SL acima do entry

                    # Colocar ordem de stop loss
                    # ✅ FIX: Binance Futures requer "STOP_MARKET" não "stop"
                    sl_order = await self.secure_exchange_service.create_order(
                        account_id=account.id,
                        user_id=user_id,
                        symbol=signal.ticker,
                        side="sell" if signal.action == "buy" else "buy",  # Lado oposto
                        order_type="STOP_MARKET",
                        quantity=str(quantity),
                        price=str(sl_price),  # stopPrice para STOP_MARKET
                    )
                    logger.info(f"Stop Loss order placed at {sl_price} ({sl_pct}%)")

                # Take Profit Order
                if hasattr(webhook, 'default_take_profit_pct') and webhook.default_take_profit_pct:
                    tp_pct = float(webhook.default_take_profit_pct)
                    # Calcular preço de take profit
                    if signal.action == "buy":
                        tp_price = entry_price * (1 + tp_pct / 100)  # Para compra: TP acima do entry
                    else:
                        tp_price = entry_price * (1 - tp_pct / 100)  # Para venda: TP abaixo do entry

                    # Colocar ordem de take profit
                    # ✅ FIX: Binance Futures requer "TAKE_PROFIT_MARKET" não "limit"
                    tp_order = await self.secure_exchange_service.create_order(
                        account_id=account.id,
                        user_id=user_id,
                        symbol=signal.ticker,
                        side="sell" if signal.action == "buy" else "buy",  # Lado oposto
                        order_type="TAKE_PROFIT_MARKET",
                        quantity=str(quantity),
                        price=str(tp_price),  # stopPrice para TAKE_PROFIT_MARKET
                    )
                    logger.info(f"Take Profit order placed at {tp_price} ({tp_pct}%)")

            except Exception as e:
                logger.warning(f"Failed to place SL/TP orders: {e}")

        logger.info(
            "Order created successfully",
            account_id=str(account.id),
            order_id=order_result.get("order_id"),
            symbol=signal.ticker,
            side=signal.action,
            has_stop_loss=sl_order is not None,
            has_take_profit=tp_order is not None,
        )

        return {
            "success": True,
            "order_id": order_result.get("order_id"),
            "order_type": "new_order",
            "details": order_result,
            "stop_loss_order": sl_order,
            "take_profit_order": tp_order,
        }

    async def _close_positions(
        self,
        account: Any,
        user_id: UUID,
        signal: TradingViewOrderWebhook,
    ) -> Dict[str, Any]:
        """Close existing positions for symbol"""

        try:
            # Get current positions
            positions = await self.secure_exchange_service.get_positions(
                account.id, user_id
            )

            # Filter positions for the specific symbol
            symbol_positions = [
                pos for pos in positions if pos.get("symbol") == signal.ticker
            ]

            if not symbol_positions:
                return {
                    "success": True,
                    "message": "No positions to close",
                    "order_type": "close_positions",
                    "closed_positions": 0,
                }

            closed_orders = []
            for position in symbol_positions:
                # Determine opposite side to close
                close_side = "sell" if position["side"] == "long" else "buy"
                quantity = position["size"]

                order_result = await self.secure_exchange_service.create_order(
                    account_id=account.id,
                    user_id=user_id,
                    symbol=signal.ticker,
                    side=close_side,
                    order_type="market",
                    quantity=quantity,
                )

                closed_orders.append(order_result)

            logger.info(
                "Positions closed successfully",
                account_id=str(account.id),
                symbol=signal.ticker,
                positions_closed=len(closed_orders),
            )

            return {
                "success": True,
                "order_type": "close_positions",
                "closed_positions": len(closed_orders),
                "orders": closed_orders,
            }

        except Exception as e:
            logger.error(
                "Position closing failed",
                account_id=str(account.id),
                symbol=signal.ticker,
                error=str(e),
            )
            return {"success": False, "error": str(e), "order_type": "close_positions"}

    async def _record_security_violation(
        self,
        webhook_id: UUID,
        payload: Dict[str, Any],
        headers: Dict[str, str],
        user_ip: Optional[str],
    ):
        """Record security violation for monitoring"""

        violation_data = {
            "webhook_id": str(webhook_id),
            "violation_type": "hmac_signature_failure",
            "client_ip": user_ip,
            "timestamp": datetime.now().isoformat(),
            "headers_sample": {
                k: v
                for k, v in headers.items()
                if k.lower() in ["user-agent", "x-forwarded-for", "content-type"]
            },
            "payload_sample": {k: str(v)[:50] for k, v in payload.items()},
        }

        logger.warning("Security violation recorded", **violation_data)

        # Could also store in database or send alerts

    async def retry_failed_delivery(
        self, delivery_id: UUID, max_attempts: Optional[int] = None
    ) -> bool:
        """
        Retry failed webhook delivery with exponential backoff

        Args:
            delivery_id: Webhook delivery ID
            max_attempts: Maximum retry attempts

        Returns:
            True if retry successful
        """
        max_attempts = max_attempts or self.max_retries

        delivery = await self.webhook_service.webhook_delivery_repository.get(
            delivery_id
        )
        if not delivery or delivery.status != WebhookDeliveryStatus.FAILED:
            return False

        webhook = await self.webhook_service.webhook_repository.get(delivery.webhook_id)
        if not webhook:
            return False

        retry_count = delivery.retry_count or 0
        if retry_count >= max_attempts:
            logger.info(
                "Maximum retry attempts reached",
                delivery_id=str(delivery_id),
                retry_count=retry_count,
            )
            return False

        try:
            # Increment retry count
            await self.webhook_service.webhook_delivery_repository.update(
                delivery_id,
                {
                    "retry_count": retry_count + 1,
                    "status": WebhookDeliveryStatus.PROCESSING,
                    "processing_started_at": datetime.now(),
                },
            )

            # Retry processing
            result = await self.process_tradingview_webhook(
                webhook_id=webhook.id,
                payload=delivery.payload,
                headers=delivery.headers or {},
            )

            if result.get("success"):
                logger.info(
                    "Webhook delivery retry successful",
                    delivery_id=str(delivery_id),
                    retry_count=retry_count + 1,
                )
                return True
            else:
                # Schedule next retry
                delay = self.retry_delays[min(retry_count, len(self.retry_delays) - 1)]
                await self._schedule_retry(delivery_id, delay)
                return False

        except Exception as e:
            logger.error(
                "Webhook delivery retry failed",
                delivery_id=str(delivery_id),
                retry_count=retry_count + 1,
                error=str(e),
            )

            # Schedule next retry
            delay = self.retry_delays[min(retry_count, len(self.retry_delays) - 1)]
            await self._schedule_retry(delivery_id, delay)
            return False

    async def _schedule_retry(self, delivery_id: UUID, delay_seconds: int):
        """Schedule retry for later (would integrate with task queue in production)"""
        next_retry = datetime.now() + timedelta(seconds=delay_seconds)

        await self.webhook_service.webhook_delivery_repository.update(
            delivery_id,
            {"next_retry_at": next_retry, "status": WebhookDeliveryStatus.FAILED},
        )

        logger.info(
            "Webhook retry scheduled",
            delivery_id=str(delivery_id),
            delay_seconds=delay_seconds,
            next_retry=next_retry.isoformat(),
        )

    async def get_webhook_stats(self, user_id: UUID, days: int = 30) -> Dict[str, Any]:
        """Get comprehensive webhook statistics"""

        stats = await self.webhook_service.get_webhook_performance_stats(user_id, days)
        delivery_stats = await self.webhook_service.get_delivery_stats(None, days)

        return {
            "webhook_performance": stats,
            "delivery_statistics": delivery_stats,
            "period_days": days,
            "generated_at": datetime.now().isoformat(),
        }

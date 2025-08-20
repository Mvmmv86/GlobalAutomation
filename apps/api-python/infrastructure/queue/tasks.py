"""Celery background tasks"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import asyncio
from decimal import Decimal

from celery import Task

from .celery_app import celery_app
from infrastructure.database.connection import get_async_session
from infrastructure.database.repositories import (
    WebhookRepository,
    WebhookDeliveryRepository,
    ExchangeAccountRepository,
    OrderRepository,
    UserRepository,
)
from application.services.tradingview_service import TradingViewService
from application.services.account_selection_service import (
    AccountSelectionService,
    TradingRequest,
    SelectionCriteria,
)
from application.services.exchange_adapter_factory import ExchangeAdapterFactory
from infrastructure.database.models.order import OrderStatus

logger = logging.getLogger(__name__)


class AsyncTask(Task):
    """Base task that supports async operations"""

    def __call__(self, *args, **kwargs):
        """Override to run async tasks"""
        loop = None
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # No event loop running, create a new one
            return asyncio.run(self.run_async(*args, **kwargs))
        else:
            # Event loop is running, we're probably in a worker
            # Create a new event loop for this task
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, self.run_async(*args, **kwargs))
                return future.result()

    async def run_async(self, *args, **kwargs):
        """Async implementation - override in subclasses"""
        return self.run(*args, **kwargs)


@celery_app.task(
    bind=True, base=AsyncTask, name="infrastructure.queue.tasks.process_webhook_task"
)
async def process_webhook_task(
    self,
    webhook_path: str,
    payload: Dict[str, Any],
    headers: Dict[str, str],
    signature: Optional[str] = None,
):
    """Process TradingView webhook asynchronously"""

    try:
        logger.info(f"Processing webhook task for path: {webhook_path}")

        async with get_async_session() as session:
            # Initialize repositories
            webhook_repo = WebhookRepository(session)
            webhook_delivery_repo = WebhookDeliveryRepository(session)
            user_repo = UserRepository(session)
            order_repo = OrderRepository(session)

            # Initialize service
            tradingview_service = TradingViewService(
                webhook_repo, webhook_delivery_repo, user_repo, order_repo
            )

            # Process webhook
            success, result = await tradingview_service.process_webhook_delivery(
                webhook_path, payload, headers, signature
            )

            await session.commit()

            if success:
                logger.info(
                    f"Webhook processed successfully: {result.get('delivery_id')}"
                )

                # If orders should be created, trigger trading task
                if result.get("orders_created", 0) > 0:
                    execute_trading_order_task.delay(
                        delivery_id=result.get("delivery_id"), webhook_data=payload
                    )

                return result
            else:
                logger.error(f"Webhook processing failed: {result.get('error')}")
                raise Exception(f"Webhook processing failed: {result.get('error')}")

    except Exception as exc:
        logger.error(f"Error processing webhook task: {str(exc)}")
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=60 * (2**self.request.retries))


@celery_app.task(
    bind=True,
    base=AsyncTask,
    name="infrastructure.queue.tasks.execute_trading_order_task",
)
async def execute_trading_order_task(
    self, delivery_id: str, webhook_data: Dict[str, Any], user_id: Optional[str] = None
):
    """Execute trading orders based on webhook data"""

    try:
        logger.info(f"Executing trading order for delivery: {delivery_id}")

        async with get_async_session() as session:
            # Initialize repositories
            exchange_account_repo = ExchangeAccountRepository(session)
            webhook_delivery_repo = WebhookDeliveryRepository(session)
            order_repo = OrderRepository(session)

            # Get delivery info
            delivery = await webhook_delivery_repo.get(delivery_id)
            if not delivery:
                raise ValueError(f"Delivery {delivery_id} not found")

            # Get webhook to find user
            webhook_repo = WebhookRepository(session)
            webhook = await webhook_repo.get(delivery.webhook_id)
            if not webhook:
                raise ValueError(f"Webhook {delivery.webhook_id} not found")

            user_id = user_id or webhook.user_id

            # Create trading request from webhook data
            trading_request = TradingRequest(
                symbol=webhook_data.get("ticker", "BTCUSDT"),
                side=webhook_data.get("action", "buy"),
                quantity=Decimal(str(webhook_data.get("quantity", "0.001"))),
                order_type=webhook_data.get("order_type", "market"),
            )

            # Initialize account selection service
            account_selection_service = AccountSelectionService(exchange_account_repo)

            # Select best account
            best_account = await account_selection_service.select_best_account(
                user_id, trading_request, SelectionCriteria.BALANCED
            )

            if not best_account:
                raise ValueError("No suitable account found for trading")

            # Execute order through exchange adapter
            adapter = best_account.adapter

            try:
                order_response = await adapter.create_order(
                    symbol=trading_request.symbol,
                    side=trading_request.side.upper(),
                    order_type=trading_request.order_type.upper(),
                    quantity=trading_request.quantity,
                    price=Decimal(str(webhook_data.get("price")))
                    if webhook_data.get("price")
                    else None,
                )

                # Save order to database
                order_data = {
                    "user_id": user_id,
                    "exchange_account_id": best_account.account.id,
                    "webhook_delivery_id": delivery_id,
                    "external_order_id": order_response.order_id,
                    "symbol": order_response.symbol,
                    "side": order_response.side.value,
                    "order_type": order_response.order_type.value,
                    "quantity": order_response.quantity,
                    "price": order_response.price,
                    "status": order_response.status.value,
                    "filled_quantity": order_response.filled_quantity,
                    "average_price": order_response.average_price,
                }

                order = await order_repo.create(order_data)
                await session.commit()

                logger.info(f"Order executed successfully: {order.id}")
                return {
                    "order_id": str(order.id),
                    "external_order_id": order_response.order_id,
                    "status": order_response.status.value,
                }

            except Exception as e:
                logger.error(f"Failed to execute order: {str(e)}")
                # Record failed order
                order_data = {
                    "user_id": user_id,
                    "exchange_account_id": best_account.account.id,
                    "webhook_delivery_id": delivery_id,
                    "symbol": trading_request.symbol,
                    "side": trading_request.side,
                    "order_type": trading_request.order_type,
                    "quantity": trading_request.quantity,
                    "status": OrderStatus.REJECTED.value,
                    "error_message": str(e),
                }

                await order_repo.create(order_data)
                await session.commit()
                raise

            finally:
                await account_selection_service.close_adapters()

    except Exception as exc:
        logger.error(f"Error executing trading order: {str(exc)}")
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=120 * (2**self.request.retries))


@celery_app.task(
    bind=True,
    base=AsyncTask,
    name="infrastructure.queue.tasks.health_check_accounts_task",
)
async def health_check_accounts_task(self):
    """Periodic health check for exchange accounts"""

    try:
        logger.info("Starting health check for exchange accounts")

        async with get_async_session() as session:
            exchange_account_repo = ExchangeAccountRepository(session)

            # Get accounts that need health check
            accounts = await exchange_account_repo.get_accounts_needing_health_check(
                max_age_minutes=5
            )

            logger.info(f"Found {len(accounts)} accounts needing health check")

            for account in accounts:
                try:
                    adapter = ExchangeAdapterFactory.create_adapter(
                        account.exchange_type.value,
                        "dummy_api_key",  # Would be decrypted in production
                        "dummy_api_secret",  # Would be decrypted in production
                        account.environment.value == "testnet",
                    )

                    # Test connection
                    is_healthy = await adapter.test_connection()

                    if is_healthy:
                        await exchange_account_repo.update_health_status(
                            account.id, "healthy"
                        )
                        logger.debug(f"Account {account.id} is healthy")
                    else:
                        await exchange_account_repo.update_health_status(
                            account.id, "unhealthy", "Connection failed"
                        )
                        logger.warning(f"Account {account.id} connection failed")

                except Exception as e:
                    await exchange_account_repo.update_health_status(
                        account.id, "error", str(e)
                    )
                    logger.error(f"Error checking account {account.id}: {str(e)}")

                finally:
                    if hasattr(adapter, "close"):
                        await adapter.close()

            await session.commit()

            return {
                "accounts_checked": len(accounts),
                "timestamp": datetime.utcnow().isoformat(),
            }

    except Exception as exc:
        logger.error(f"Error in health check task: {str(exc)}")
        raise self.retry(exc=exc, countdown=300)  # Retry in 5 minutes


@celery_app.task(
    bind=True, base=AsyncTask, name="infrastructure.queue.tasks.cleanup_old_data_task"
)
async def cleanup_old_data_task(self, days_old: int = 30):
    """Clean up old webhook deliveries and completed orders"""

    try:
        logger.info(f"Starting cleanup of data older than {days_old} days")

        async with get_async_session() as session:
            webhook_delivery_repo = WebhookDeliveryRepository(session)
            order_repo = OrderRepository(session)

            # Cleanup old webhook deliveries (keep failed ones)
            cleaned_deliveries = await webhook_delivery_repo.cleanup_old_deliveries(
                days_old=days_old, keep_failed=True
            )

            # Cleanup old completed orders
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            cleaned_orders = await order_repo.cleanup_old_orders(cutoff_date)

            await session.commit()

            logger.info(
                f"Cleanup completed: {cleaned_deliveries} deliveries, {cleaned_orders} orders"
            )

            return {
                "cleaned_deliveries": cleaned_deliveries,
                "cleaned_orders": cleaned_orders,
                "cutoff_date": cutoff_date.isoformat(),
            }

    except Exception as exc:
        logger.error(f"Error in cleanup task: {str(exc)}")
        raise self.retry(exc=exc, countdown=1800)  # Retry in 30 minutes


@celery_app.task(name="infrastructure.queue.tasks.test_task")
def test_task(message: str = "Hello from Celery!"):
    """Simple test task"""
    logger.info(f"Test task executed: {message}")
    return {
        "message": message,
        "timestamp": datetime.utcnow().isoformat(),
        "worker_id": test_task.request.id,
    }

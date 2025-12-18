"""
Background Scheduler for Data Synchronization
Executa sincronização automática a cada 30 segundos (60s para BingX)
Includes SL/TP monitoring for bot trades
"""

import asyncio
import structlog
import time
from datetime import datetime, timezone
from typing import Dict, Any
from dotenv import load_dotenv

# Carrega variáveis de ambiente do .env
load_dotenv()

from infrastructure.database.connection_transaction_mode import transaction_db
from infrastructure.exchanges.binance_connector import BinanceConnector
from infrastructure.exchanges.bybit_connector import BybitConnector
from infrastructure.exchanges.bingx_connector import BingXConnector
from infrastructure.exchanges.bitget_connector import BitgetConnector
from infrastructure.pricing.binance_price_service import BinancePriceService
from infrastructure.services.bot_sltp_monitor_service import get_bot_sltp_monitor
from infrastructure.services.indicator_alert_monitor import get_indicator_alert_monitor

logger = structlog.get_logger(__name__)

# 🚀 RATE LIMIT FIX: Track last sync time per account to respect different intervals
# BingX has more restrictive rate limits, so we sync it less frequently
BINGX_SYNC_INTERVAL = 60  # 60 seconds for BingX
DEFAULT_SYNC_INTERVAL = 30  # 30 seconds for other exchanges


class SyncScheduler:
    """Scheduler para sincronização automática de dados das exchanges"""

    def __init__(self):
        self.is_running = False
        self._task = None
        # 🚀 RATE LIMIT FIX: Track last sync time per account
        self._last_sync_times: Dict[str, float] = {}
        # 📅 Daily reset tracking - stores the last date when daily counters were reset
        self._last_daily_reset_date: str = None
        # 🔔 Indicator Alert Monitor instance
        self._indicator_alert_monitor = None

    async def start(self):
        """Inicia o scheduler"""
        if self.is_running:
            logger.warning("Sync scheduler already running")
            return

        self.is_running = True
        self._task = asyncio.create_task(self._sync_loop())
        logger.info("🔄 Sync scheduler started - syncing every 30 seconds (optimized for 100-500 clients)")

        # Start Indicator Alert Monitor
        try:
            self._indicator_alert_monitor = get_indicator_alert_monitor(transaction_db)
            await self._indicator_alert_monitor.start()
        except Exception as e:
            logger.error(f"❌ Failed to start Indicator Alert Monitor: {e}")

    async def stop(self):
        """Para o scheduler"""
        self.is_running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        # Stop Indicator Alert Monitor
        if self._indicator_alert_monitor:
            try:
                await self._indicator_alert_monitor.stop()
            except Exception as e:
                logger.error(f"❌ Error stopping Indicator Alert Monitor: {e}")

        logger.info("⏹️ Sync scheduler stopped")

    async def _sync_loop(self):
        """Loop principal de sincronização"""
        while self.is_running:
            try:
                await self._sync_all_accounts()

                # Monitor SL/TP orders for bot subscriptions
                await self._monitor_bot_sltp_orders()

                # 📅 Check and reset daily loss counters at midnight UTC
                await self._check_daily_reset()

                await asyncio.sleep(30)  # Aguarda 30 segundos (otimizado para 100-500 clientes)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in sync loop: {e}")
                await asyncio.sleep(10)  # Aguarda 10 segundos em caso de erro

    async def _sync_all_accounts(self):
        """Sincroniza todas as contas de exchange ativas"""
        try:
            # Buscar todas as contas ativas
            accounts = await transaction_db.fetch("""
                SELECT id, name, exchange, api_key, secret_key, testnet, is_active, user_id
                FROM exchange_accounts
                WHERE is_active = true
            """)

            logger.info(f"🔄 Syncing {len(accounts)} active accounts")

            current_time = time.time()

            for account in accounts:
                try:
                    account_id = str(account['id'])
                    exchange = account['exchange'].lower()

                    # 🚀 RATE LIMIT FIX: Check if enough time has passed for this account
                    sync_interval = BINGX_SYNC_INTERVAL if exchange == 'bingx' else DEFAULT_SYNC_INTERVAL

                    if account_id in self._last_sync_times:
                        elapsed = current_time - self._last_sync_times[account_id]
                        if elapsed < sync_interval:
                            logger.debug(f"⏭️ Skipping {exchange} account {account['name']} - next sync in {sync_interval - elapsed:.0f}s")
                            continue

                    await self._sync_account_data(account)

                    # Update last sync time
                    self._last_sync_times[account_id] = current_time

                except Exception as e:
                    logger.error(f"Error syncing account {account['id']}: {e}")

        except Exception as e:
            logger.error(f"Error fetching accounts for sync: {e}")

    async def _sync_account_data(self, account):
        """Sincroniza dados de uma conta específica"""
        account_id = account['id']

        try:
            # Criar connector para a exchange
            connector = await self._get_exchange_connector(account)

            # Sincronizar saldos (com preços reais)
            await self._sync_account_balances(account_id, connector)

            # Sincronizar posições futures (para P&L real)
            await self._sync_account_positions(account_id, connector)

            logger.debug(f"✅ Synced account {account['name']} ({account_id}) - balances & positions")

        except Exception as e:
            logger.error(f"Error syncing account {account_id}: {e}")

    async def _get_exchange_connector(self, account):
        """Cria connector para a exchange (MULTI-EXCHANGE SUPPORT)"""
        exchange = account['exchange'].lower()

        # API keys estão em PLAIN TEXT no banco (Supabase encryption at rest)
        api_key = account['api_key']
        secret_key = account['secret_key']
        passphrase = account.get('passphrase')
        testnet = account.get('testnet', False)

        # Validar que as chaves existem
        if not api_key or not secret_key:
            logger.error(
                f"❌ CRITICAL: API key or secret key is missing for account {account['id']}",
                account_name=account.get('name', 'Unknown'),
                user_id=account.get('user_id', 'Unknown')
            )
            raise ValueError(f"Missing API credentials for account {account['id']}")

        # Create connector based on exchange type (MULTI-EXCHANGE)
        if exchange == 'binance':
            return BinanceConnector(api_key=api_key, api_secret=secret_key, testnet=testnet)
        elif exchange == 'bybit':
            return BybitConnector(api_key=api_key, api_secret=secret_key, testnet=testnet)
        elif exchange == 'bingx':
            return BingXConnector(api_key=api_key, api_secret=secret_key, testnet=testnet)
        elif exchange == 'bitget':
            return BitgetConnector(api_key=api_key, api_secret=secret_key, passphrase=passphrase, testnet=testnet)
        else:
            raise ValueError(f"Unsupported exchange: {exchange}")

    async def _sync_account_balances(self, account_id: str, connector):
        """Sincroniza saldos de uma conta usando o sistema de preços reais"""
        try:
            logger.debug(f"🔄 Syncing balances for account {account_id}")

            # Usar HTTP interno para evitar problemas de import
            import httpx
            import os
            api_port = os.getenv('PORT', '8001')  # Usa PORT do .env ou 8001 como padrão
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(f"http://localhost:{api_port}/api/v1/sync/balances/{account_id}")
                result = response.json()

            if result.get('success'):
                logger.info(f"✅ Account {account_id}: Synced {result.get('synced_count', 0)} balances")
            else:
                logger.warning(f"⚠️ Sync failed for account {account_id}: {result}")

        except Exception as e:
            logger.error(f"❌ Error syncing balances for account {account_id}: {e}")

    async def _sync_account_positions(self, account_id: str, connector):
        """Sincroniza posições futures de uma conta usando preços reais"""
        try:
            logger.debug(f"🎯 Syncing futures positions for account {account_id}")

            # Usar HTTP interno para evitar problemas de import
            import httpx
            import os
            api_port = os.getenv('PORT', '8001')  # Usa PORT do .env ou 8001 como padrão
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(f"http://localhost:{api_port}/api/v1/sync/positions/{account_id}")
                result = response.json()

            if result.get('success'):
                count = result.get('synced_count', 0)
                logger.info(f"🎯 Account {account_id}: Synced {count} positions")
            else:
                logger.warning(f"⚠️ Positions sync failed for account {account_id}: {result}")

        except Exception as e:
            logger.error(f"❌ Error syncing positions for account {account_id}: {e}")

    async def _monitor_bot_sltp_orders(self):
        """
        Monitor SL/TP orders for bot subscriptions.
        Checks if any Stop Loss or Take Profit orders have been filled
        and updates trade records and P&L accordingly.
        """
        try:
            # Get or create the SL/TP monitor service
            sltp_monitor = get_bot_sltp_monitor(transaction_db)

            # Run the monitoring cycle
            result = await sltp_monitor.monitor_all_subscriptions()

            if result.get("success"):
                checked = result.get("checked", 0)
                closed = result.get("closed", 0)
                if closed > 0:
                    logger.info(
                        f"🤖 Bot SL/TP Monitor: {closed} trades closed out of {checked} checked",
                        duration_ms=result.get("duration_ms")
                    )
                elif checked > 0:
                    logger.debug(f"🤖 Bot SL/TP Monitor: Checked {checked} open trades, none closed")
            else:
                if result.get("reason") != "already_running":
                    logger.warning(f"⚠️ Bot SL/TP Monitor failed: {result.get('error')}")

        except Exception as e:
            logger.error(f"❌ Error in bot SL/TP monitoring: {e}")

    async def _check_daily_reset(self):
        """
        Check if it's a new day (UTC) and reset daily loss counters.
        This runs every 30 seconds but only resets once per day.
        Also generates daily P&L snapshots for historical tracking.
        """
        try:
            # Get current date in UTC
            current_date_utc = datetime.now(timezone.utc).strftime('%Y-%m-%d')

            # If we already reset today, skip
            if self._last_daily_reset_date == current_date_utc:
                return

            # It's a new day! First, generate yesterday's P&L snapshots before resetting
            logger.info(f"📅 New day detected ({current_date_utc}) - Generating daily snapshots and resetting counters...")

            # Generate daily P&L snapshots for yesterday (before reset)
            await self._generate_daily_pnl_snapshots()

            # Reset the daily loss counters
            result = await transaction_db.execute("""
                UPDATE bot_subscriptions
                SET current_daily_loss_usd = 0,
                    updated_at = NOW()
                WHERE status = 'active'
            """)

            # Update last reset date
            self._last_daily_reset_date = current_date_utc

            logger.info(f"✅ Daily loss counters reset successfully for all active subscriptions")

        except Exception as e:
            logger.error(f"❌ Error resetting daily loss counters: {e}")

    async def _generate_daily_pnl_snapshots(self):
        """
        Generate daily P&L snapshots for all active subscriptions.
        This creates historical records for performance tracking.
        """
        try:
            from datetime import date, timedelta
            yesterday = date.today() - timedelta(days=1)

            # Get all active subscriptions that don't have yesterday's snapshot
            subscriptions = await transaction_db.fetch("""
                SELECT
                    bs.id as subscription_id,
                    bs.user_id,
                    bs.bot_id,
                    bs.total_pnl_usd,
                    bs.win_count,
                    bs.loss_count
                FROM bot_subscriptions bs
                WHERE bs.status = 'active'
                  AND NOT EXISTS (
                      SELECT 1 FROM bot_pnl_history ph
                      WHERE ph.subscription_id = bs.id AND ph.snapshot_date = $1
                  )
            """, yesterday)

            if not subscriptions:
                logger.debug("📊 No subscriptions need daily snapshots")
                return

            snapshots_created = 0

            for sub in subscriptions:
                subscription_id = sub["subscription_id"]
                user_id = sub["user_id"]
                bot_id = sub["bot_id"]

                # Get the previous day's cumulative values
                prev = await transaction_db.fetchrow("""
                    SELECT cumulative_pnl_usd, cumulative_wins, cumulative_losses
                    FROM bot_pnl_history
                    WHERE subscription_id = $1 AND snapshot_date < $2
                    ORDER BY snapshot_date DESC
                    LIMIT 1
                """, subscription_id, yesterday)

                prev_pnl = float(prev["cumulative_pnl_usd"]) if prev else 0
                prev_wins = prev["cumulative_wins"] if prev else 0
                prev_losses = prev["cumulative_losses"] if prev else 0

                current_pnl = float(sub["total_pnl_usd"]) if sub["total_pnl_usd"] else 0
                current_wins = sub["win_count"] or 0
                current_losses = sub["loss_count"] or 0

                daily_pnl = current_pnl - prev_pnl
                daily_wins = current_wins - prev_wins
                daily_losses = current_losses - prev_losses

                # Only create snapshot if there was activity
                if daily_pnl != 0 or daily_wins != 0 or daily_losses != 0:
                    total_daily = daily_wins + daily_losses
                    win_rate = (daily_wins / total_daily * 100) if total_daily > 0 else 0

                    await transaction_db.execute("""
                        INSERT INTO bot_pnl_history (
                            subscription_id, user_id, bot_id, snapshot_date,
                            daily_pnl_usd, cumulative_pnl_usd,
                            daily_wins, daily_losses, cumulative_wins, cumulative_losses,
                            win_rate_pct
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                        ON CONFLICT (subscription_id, snapshot_date) DO NOTHING
                    """,
                        subscription_id, user_id, bot_id, yesterday,
                        daily_pnl, current_pnl,
                        daily_wins, daily_losses, current_wins, current_losses,
                        win_rate
                    )
                    snapshots_created += 1

            if snapshots_created > 0:
                logger.info(f"📊 Created {snapshots_created} daily P&L snapshots for {yesterday}")

        except Exception as e:
            logger.error(f"❌ Error generating daily P&L snapshots: {e}")


# Instância global do scheduler
sync_scheduler = SyncScheduler()
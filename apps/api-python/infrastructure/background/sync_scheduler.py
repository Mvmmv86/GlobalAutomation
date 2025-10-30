"""
Background Scheduler for Data Synchronization
Executa sincronização automática a cada 30 segundos
"""

import asyncio
import structlog
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

logger = structlog.get_logger(__name__)


class SyncScheduler:
    """Scheduler para sincronização automática de dados das exchanges"""

    def __init__(self):
        self.is_running = False
        self._task = None

    async def start(self):
        """Inicia o scheduler"""
        if self.is_running:
            logger.warning("Sync scheduler already running")
            return

        self.is_running = True
        self._task = asyncio.create_task(self._sync_loop())
        logger.info("🔄 Sync scheduler started - syncing every 30 seconds (optimized for 100-500 clients)")

    async def stop(self):
        """Para o scheduler"""
        self.is_running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("⏹️ Sync scheduler stopped")

    async def _sync_loop(self):
        """Loop principal de sincronização"""
        while self.is_running:
            try:
                await self._sync_all_accounts()
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

            for account in accounts:
                try:
                    await self._sync_account_data(account)
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
            api_port = os.getenv('PORT', '3001')  # Usa PORT do .env ou 3001 como padrão
            async with httpx.AsyncClient() as client:
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
            api_port = os.getenv('PORT', '3001')  # Usa PORT do .env ou 3001 como padrão
            async with httpx.AsyncClient() as client:
                response = await client.post(f"http://localhost:{api_port}/api/v1/sync/positions/{account_id}")
                result = response.json()

            if result.get('success'):
                count = result.get('synced_count', 0)
                logger.info(f"🎯 Account {account_id}: Synced {count} positions")
            else:
                logger.warning(f"⚠️ Positions sync failed for account {account_id}: {result}")

        except Exception as e:
            logger.error(f"❌ Error syncing positions for account {account_id}: {e}")



# Instância global do scheduler
sync_scheduler = SyncScheduler()
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
from infrastructure.security.encryption_service import EncryptionService
from infrastructure.pricing.binance_price_service import BinancePriceService

logger = structlog.get_logger(__name__)


class SyncScheduler:
    """Scheduler para sincronização automática de dados das exchanges"""

    def __init__(self):
        self.encryption_service = EncryptionService()
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
        """Cria connector para a exchange"""
        exchange = account['exchange'].lower()

        if exchange == 'binance':
            from infrastructure.security.encryption_service import EncryptionService
            encryption_service = EncryptionService()

            # Usar as chaves do banco de dados
            api_key = account['api_key']
            secret_key = account['secret_key']
            # IMPORTANTE: Usar False como default para REAL trading
            testnet = account.get('testnet', False)

            # Tentar descriptografar as credenciais
            try:
                if api_key and len(api_key) > 10:
                    api_key = encryption_service.decrypt_string(api_key)
                    logger.debug(f"✅ API key decrypted successfully for account {account['id']}")
                if secret_key and len(secret_key) > 10:
                    secret_key = encryption_service.decrypt_string(secret_key)
                    logger.debug(f"✅ Secret key decrypted successfully for account {account['id']}")
            except Exception as e:
                # ERRO CRÍTICO: Não conseguiu descriptografar as chaves do cliente
                # Isso significa que a conta não vai funcionar para este cliente
                logger.error(
                    f"❌ CRITICAL: Failed to decrypt API keys for account {account['id']}",
                    error_type=type(e).__name__,
                    error_message=str(e),
                    account_name=account.get('name', 'Unknown'),
                    user_id=account.get('user_id', 'Unknown')
                )
                # NÃO fazer fallback para variáveis de ambiente - isso quebraria a escalabilidade
                # Cada cliente deve ter suas próprias chaves descriptografadas corretamente
                from infrastructure.security.encryption_service import EncryptionError
                raise EncryptionError(f"Cannot decrypt API keys for account {account['id']}: {str(e)}")

            # Validar que as chaves foram descriptografadas corretamente
            if not api_key or len(api_key) < 10:
                logger.error(
                    f"❌ CRITICAL: API key is empty or invalid after decryption for account {account['id']}",
                    account_name=account.get('name', 'Unknown'),
                    user_id=account.get('user_id', 'Unknown')
                )
                raise ValueError(f"Invalid API key for account {account['id']} - cannot access exchange API")

            # Usar as chaves reais
            return BinanceConnector(
                api_key=api_key,
                api_secret=secret_key,
                testnet=testnet
            )
        else:
            raise ValueError(f"Unsupported exchange: {exchange}")

    async def _sync_account_balances(self, account_id: str, connector):
        """Sincroniza saldos de uma conta usando o sistema de preços reais"""
        try:
            logger.debug(f"🔄 Syncing balances for account {account_id}")

            # Usar HTTP interno para evitar problemas de import
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.post(f"http://localhost:8000/api/v1/sync/balances/{account_id}")
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
            async with httpx.AsyncClient() as client:
                response = await client.post(f"http://localhost:8000/api/v1/sync/positions/{account_id}")
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
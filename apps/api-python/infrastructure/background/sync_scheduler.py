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
from infrastructure.ai.data_collector import TradingDataCollector
from infrastructure.news.news_collector import NewsCollector

logger = structlog.get_logger(__name__)

# 🚀 RATE LIMIT FIX: Track last sync time per account to respect different intervals
# BingX has more restrictive rate limits, so we sync it less frequently
BINGX_SYNC_INTERVAL = 60  # 60 seconds for BingX
DEFAULT_SYNC_INTERVAL = 30  # 30 seconds for other exchanges


class SyncScheduler:
    """Scheduler para sincronização automática de dados das exchanges"""

    # ⏰ Horário para enviar resumo diário (UTC)
    # 11:00 UTC = 08:00 Brasília (horário de verão) / 09:00 Brasília (horário normal)
    DAILY_REPORT_HOUR_UTC = 11  # 8h Brasília

    def __init__(self):
        self.is_running = False
        self._task = None
        # 🚀 RATE LIMIT FIX: Track last sync time per account
        self._last_sync_times: Dict[str, float] = {}
        # 📅 Daily reset tracking - stores the last date when daily counters were reset
        self._last_daily_reset_date: str = None
        # 🔔 Indicator Alert Monitor instance
        self._indicator_alert_monitor = None
        # 📊 Track when daily report was last sent
        self._last_daily_report_date: str = None

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

                # 📊 Check if it's time to send daily AI market report
                await self._check_daily_report()

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

            # It's a new day! Start daily maintenance window
            logger.info(f"📅 Daily maintenance window opened ({current_date_utc})")

            # 1. Generate daily P&L snapshots for yesterday (before reset)
            await self._generate_daily_pnl_snapshots()

            # 2. Collect AI training data from yesterday
            await self._collect_ai_training_data()

            # 3. Collect daily news for market context
            await self._collect_daily_news()

            # 4. Reset the daily loss counters
            result = await transaction_db.execute("""
                UPDATE bot_subscriptions
                SET current_daily_loss_usd = 0,
                    updated_at = NOW()
                WHERE status = 'active'
            """)

            # Update last reset date
            self._last_daily_reset_date = current_date_utc

            logger.info(f"✅ Daily maintenance window completed successfully")

        except Exception as e:
            logger.error(f"❌ Error in daily maintenance: {e}")

    async def _collect_ai_training_data(self):
        """
        Coleta diária de dados para alimentar a IA.
        Roda automaticamente à meia-noite UTC.
        """
        try:
            logger.info("🤖 Starting AI daily data collection...")

            collector = TradingDataCollector()
            await collector.connect()

            try:
                snapshot = await collector.collect_daily_data()

                logger.info(
                    "✅ AI data collected successfully",
                    date=snapshot.date,
                    total_pnl=snapshot.total_pnl,
                    trades=snapshot.total_trades,
                    win_rate=f"{snapshot.win_rate:.1f}%",
                    alerts=len(snapshot.alerts),
                    active_bots=snapshot.active_bots
                )

                # Log alerts for visibility
                if snapshot.alerts:
                    for alert in snapshot.alerts[:5]:  # Limit to 5 alerts in log
                        logger.warning(f"📊 AI Alert: {alert}")

            finally:
                await collector.disconnect()

        except Exception as e:
            logger.error(f"❌ Failed to collect AI training data: {e}")

    async def _collect_daily_news(self):
        """
        Coleta diária de notícias de mercado.
        Roda automaticamente à meia-noite UTC.
        """
        try:
            logger.info("📰 Starting daily news collection...")

            collector = NewsCollector(transaction_db)
            digest = await collector.collect_daily_news()

            logger.info(
                "✅ News collected successfully",
                total_articles=digest.total_articles,
                sentiment=digest.market_sentiment.value,
                bullish=digest.bullish_count,
                bearish=digest.bearish_count,
                trending=digest.trending_currencies[:5]
            )

        except Exception as e:
            logger.error(f"❌ Failed to collect daily news: {e}")

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

    async def _check_daily_report(self):
        """
        Verifica se é hora de enviar o resumo diário da IA.
        Roda no horário definido em DAILY_REPORT_HOUR_UTC.
        """
        try:
            now = datetime.now(timezone.utc)
            current_date = now.strftime('%Y-%m-%d')

            # Só envia uma vez por dia
            if self._last_daily_report_date == current_date:
                return

            # Verifica se é o horário certo (com margem de 5 minutos)
            if now.hour != self.DAILY_REPORT_HOUR_UTC:
                return

            logger.info(f"📊 Generating AI daily market report...")

            # Gerar o relatório inteligente da IA
            await self._generate_ai_market_report()

            # Marca como enviado hoje
            self._last_daily_report_date = current_date
            logger.info(f"✅ Daily AI market report generated and alert created")

        except Exception as e:
            logger.error(f"❌ Error in daily report check: {e}")

    async def _generate_ai_market_report(self):
        """
        Gera relatório diário de mercado usando a IA.
        Analisa notícias, estratégias e dá insights de posicionamento.
        """
        try:
            from infrastructure.ai.trading_ai_service import TradingAIService
            from infrastructure.news.news_collector import NewsCollector
            import json

            # 1. Buscar notícias do dia
            news_data = await transaction_db.fetchrow("""
                SELECT data FROM ai_news_digests
                WHERE date = CURRENT_DATE
                ORDER BY created_at DESC LIMIT 1
            """)

            # 2. Buscar estratégias ativas e importantes
            strategies = await transaction_db.fetch("""
                SELECT
                    s.id, s.name, s.symbol, s.direction, s.timeframe,
                    s.is_important, s.is_active,
                    COUNT(DISTINCT ss.id) as total_signals,
                    SUM(CASE WHEN ss.result = 'win' THEN 1 ELSE 0 END) as wins,
                    SUM(CASE WHEN ss.result = 'loss' THEN 1 ELSE 0 END) as losses
                FROM strategies s
                LEFT JOIN strategy_signals ss ON ss.strategy_id = s.id
                    AND ss.created_at > NOW() - INTERVAL '7 days'
                WHERE s.is_active = true
                GROUP BY s.id
                ORDER BY s.is_important DESC, wins DESC
                LIMIT 20
            """)

            # 3. Buscar performance dos bots ativos
            bots_performance = await transaction_db.fetch("""
                SELECT
                    b.id, b.name, b.symbol, b.exchange,
                    COUNT(DISTINCT bs.id) as subscribers,
                    AVG(bs.total_pnl_usd) as avg_pnl,
                    AVG(bs.win_count::float / NULLIF(bs.win_count + bs.loss_count, 0) * 100) as avg_win_rate
                FROM bots b
                JOIN bot_subscriptions bs ON bs.bot_id = b.id
                WHERE b.is_active = true AND bs.status = 'active'
                GROUP BY b.id
                ORDER BY avg_pnl DESC
                LIMIT 10
            """)

            # 4. Preparar contexto para a IA
            news_context = ""
            market_sentiment = "neutral"
            trending_coins = []

            if news_data and news_data['data']:
                data = json.loads(news_data['data']) if isinstance(news_data['data'], str) else news_data['data']
                market_sentiment = data.get('market_sentiment', 'neutral')
                trending_coins = data.get('trending_currencies', [])[:5]

                articles = data.get('articles', [])[:10]
                news_context = "\n".join([
                    f"- [{a.get('source', 'unknown')}] {a.get('title', '')} (sentiment: {a.get('sentiment', 'neutral')})"
                    for a in articles
                ])

            strategies_context = "\n".join([
                f"- {s['name']} ({s['symbol']}, {s['direction']}): {s['wins'] or 0}W/{s['losses'] or 0}L nos últimos 7 dias"
                + (" ⭐ IMPORTANTE" if s['is_important'] else "")
                for s in strategies
            ])

            bots_context = "\n".join([
                f"- {b['name']} ({b['symbol']}): {b['subscribers']} assinantes, PnL médio ${float(b['avg_pnl'] or 0):.2f}, Win rate {float(b['avg_win_rate'] or 0):.1f}%"
                for b in bots_performance
            ])

            # 5. Gerar análise com a IA
            ai_service = TradingAIService()

            prompt = f"""Como analista de trading institucional, gere um RESUMO DIÁRIO DO MERCADO CRYPTO.

## DADOS DO DIA

### Sentimento Geral do Mercado: {market_sentiment.upper()}
### Moedas em Tendência: {', '.join(trending_coins) if trending_coins else 'Nenhuma específica'}

### Principais Notícias:
{news_context if news_context else 'Sem notícias coletadas ainda hoje.'}

### Estratégias Ativas da Plataforma:
{strategies_context if strategies_context else 'Nenhuma estratégia ativa.'}

### Performance dos Bots:
{bots_context if bots_context else 'Nenhum bot ativo.'}

## INSTRUÇÕES

Por favor, gere um relatório CONCISO e ACIONÁVEL com:

1. **ANÁLISE DE MERCADO** (2-3 parágrafos)
   - Interpretação das notícias principais
   - Impacto esperado no mercado crypto
   - Fatores macro relevantes

2. **SENTIMENTO E VIÉS** (1 parágrafo)
   - Seu viés direcional (bullish/bearish/neutro)
   - Confiança no viés (alta/média/baixa)
   - Principais riscos

3. **INSIGHTS PARA POSICIONAMENTO** (bullet points)
   - Quais estratégias da plataforma podem se beneficiar hoje
   - Moedas para observar com mais atenção
   - Níveis de preço importantes se relevante

4. **O QUE EVITAR HOJE** (bullet points)
   - Estratégias ou pares que podem sofrer com o cenário atual
   - Movimentos arriscados a evitar
   - Moedas/setores com maior risco no momento

5. **RECOMENDAÇÕES PRÁTICAS** (bullet points)
   - O que fazer: aumentar exposição, reduzir, manter?
   - Pares específicos para focar baseado nas estratégias ativas
   - Alertas ou cuidados especiais para o dia

Seja direto e prático. Foque em insights ACIONÁVEIS baseados nas estratégias e bots da plataforma. Seja específico sobre quais estratégias ativas podem se beneficiar ou devem ser evitadas."""

            response = await ai_service.chat(
                message=prompt,
                context_type="market"
            )

            report_content = response.get('response', 'Erro ao gerar relatório')

            # 6. Salvar o alerta para aparecer no chat
            report_date = datetime.now(timezone.utc).strftime('%Y-%m-%d')
            alert_data = {
                "type": "info",
                "category": "system",  # Changed to 'system' to trigger the report viewer
                "title": f"📊 Resumo Diario de Mercado - {datetime.now(timezone.utc).strftime('%d/%m/%Y')}",
                "message": f"Sentimento: {market_sentiment.upper()}. Clique para ver a analise completa.",
                "full_report": report_content,
                "report_date": report_date,
                "market_sentiment": market_sentiment,
                "trending": trending_coins,
                "strategies_analyzed": len(strategies),
                "generated_at": datetime.now(timezone.utc).isoformat()
            }

            # Salvar na tabela de alertas
            await transaction_db.execute("""
                INSERT INTO ai_alerts (type, category, title, message, data, created_at, is_read)
                VALUES ($1, $2, $3, $4, $5, NOW(), false)
            """,
                alert_data["type"],
                alert_data["category"],
                alert_data["title"],
                alert_data["message"],
                json.dumps(alert_data)
            )

            logger.info(
                "📊 AI Market Report generated",
                sentiment=market_sentiment,
                strategies=len(strategies),
                trending=trending_coins
            )

        except Exception as e:
            logger.error(f"❌ Error generating AI market report: {e}")
            import traceback
            logger.error(traceback.format_exc())


# Instância global do scheduler
sync_scheduler = SyncScheduler()
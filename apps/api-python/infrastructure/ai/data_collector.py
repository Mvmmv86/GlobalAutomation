"""
Trading AI Data Collector

Script que coleta dados diarios de todos os bots e estrategias
para alimentar a IA com conhecimento atualizado.

Funcionalidades:
1. Coleta metricas de todos os bots ativos
2. Agrega performance por estrategia
3. Identifica padroes e anomalias
4. Armazena snapshots para analise historica
5. Gera alertas automaticos

Executar via cron diariamente:
0 0 * * * python -m infrastructure.ai.data_collector
"""

import asyncio
import os
import json
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, asdict
import ssl

import asyncpg
import structlog
from dotenv import load_dotenv

load_dotenv()

logger = structlog.get_logger(__name__)


@dataclass
class DailySnapshot:
    """Snapshot diario de performance"""
    date: str
    total_capital: float
    total_pnl: float
    total_pnl_percent: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    best_performing_bot: Optional[str]
    worst_performing_bot: Optional[str]
    best_performing_strategy: Optional[str]
    worst_performing_strategy: Optional[str]
    active_bots: int
    active_strategies: int
    alerts: List[str]
    market_conditions: Dict[str, Any]


@dataclass
class BotSnapshot:
    """Snapshot de um bot"""
    bot_id: str
    bot_name: str
    date: str
    pnl: float
    pnl_percent: float
    trades: int
    wins: int
    losses: int
    win_rate: float
    avg_trade_pnl: float
    max_profit: float
    max_loss: float
    open_positions: int
    total_exposure: float


@dataclass
class StrategySnapshot:
    """Snapshot de uma estrategia"""
    strategy_id: str
    strategy_name: str
    date: str
    signals_generated: int
    signals_executed: int
    execution_rate: float
    avg_signal_quality: float


class TradingDataCollector:
    """
    Coletor de dados para alimentar a IA

    Roda diariamente e coleta:
    - Performance de todos os bots
    - Metricas de todas as estrategias
    - Dados de mercado
    - Anomalias e alertas
    """

    def __init__(self, database_url: Optional[str] = None):
        self.database_url = database_url or os.getenv("DATABASE_URL")
        if self.database_url:
            self.database_url = self.database_url.replace(
                "postgresql+asyncpg://", "postgresql://"
            )
        self.conn: Optional[asyncpg.Connection] = None

    async def connect(self):
        """Conecta ao banco de dados"""
        ssl_ctx = ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE

        self.conn = await asyncpg.connect(self.database_url, ssl=ssl_ctx)
        logger.info("Connected to database")

    async def disconnect(self):
        """Desconecta do banco"""
        if self.conn:
            await self.conn.close()
            logger.info("Disconnected from database")

    async def collect_daily_data(self, date: Optional[datetime] = None) -> DailySnapshot:
        """
        Coleta todos os dados do dia

        Args:
            date: Data para coletar (default: ontem)

        Returns:
            DailySnapshot com todos os dados
        """
        if date is None:
            date = datetime.now() - timedelta(days=1)

        date_str = date.strftime("%Y-%m-%d")
        logger.info(f"Collecting data for {date_str}")

        # Coletar dados de bots
        bot_snapshots = await self._collect_bot_data(date)

        # Coletar dados de estrategias
        strategy_snapshots = await self._collect_strategy_data(date)

        # Agregar metricas
        total_pnl = sum(b.pnl for b in bot_snapshots)
        total_trades = sum(b.trades for b in bot_snapshots)
        winning_trades = sum(b.wins for b in bot_snapshots)
        losing_trades = sum(b.losses for b in bot_snapshots)

        # Identificar melhores e piores
        if bot_snapshots:
            best_bot = max(bot_snapshots, key=lambda x: x.pnl)
            worst_bot = min(bot_snapshots, key=lambda x: x.pnl)
        else:
            best_bot = worst_bot = None

        # Gerar alertas
        alerts = await self._generate_alerts(bot_snapshots, strategy_snapshots)

        # Coletar condicoes de mercado
        market_conditions = await self._collect_market_conditions()

        snapshot = DailySnapshot(
            date=date_str,
            total_capital=0,  # Sera calculado
            total_pnl=total_pnl,
            total_pnl_percent=0,  # Sera calculado
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=(winning_trades / total_trades * 100) if total_trades > 0 else 0,
            best_performing_bot=best_bot.bot_name if best_bot else None,
            worst_performing_bot=worst_bot.bot_name if worst_bot else None,
            best_performing_strategy=None,
            worst_performing_strategy=None,
            active_bots=len([b for b in bot_snapshots if b.trades > 0]),
            active_strategies=len([s for s in strategy_snapshots if s.signals_generated > 0]),
            alerts=alerts,
            market_conditions=market_conditions
        )

        # Salvar snapshot no banco
        await self._save_daily_snapshot(snapshot)

        # Salvar snapshots individuais
        for bot_snap in bot_snapshots:
            await self._save_bot_snapshot(bot_snap)

        for strategy_snap in strategy_snapshots:
            await self._save_strategy_snapshot(strategy_snap)

        logger.info(
            f"Daily collection complete",
            total_pnl=total_pnl,
            total_trades=total_trades,
            alerts=len(alerts)
        )

        return snapshot

    async def _collect_bot_data(self, date: datetime) -> List[BotSnapshot]:
        """Coleta dados de todos os bots"""
        date_str = date.strftime("%Y-%m-%d")
        next_date_str = (date + timedelta(days=1)).strftime("%Y-%m-%d")

        query = """
            SELECT
                b.id as bot_id,
                b.name as bot_name,
                COALESCE(SUM(bs.pnl), 0) as total_pnl,
                COUNT(bs.id) as total_trades,
                COUNT(CASE WHEN bs.pnl > 0 THEN 1 END) as wins,
                COUNT(CASE WHEN bs.pnl < 0 THEN 1 END) as losses,
                COALESCE(MAX(bs.pnl), 0) as max_profit,
                COALESCE(MIN(bs.pnl), 0) as max_loss,
                COALESCE(AVG(bs.pnl), 0) as avg_pnl
            FROM bots b
            LEFT JOIN bot_signals bs ON b.id = bs.bot_id
                AND bs.created_at >= $1
                AND bs.created_at < $2
            WHERE b.is_active = true
            GROUP BY b.id, b.name
        """

        try:
            rows = await self.conn.fetch(query, date_str, next_date_str)

            snapshots = []
            for row in rows:
                trades = row["total_trades"] or 0
                wins = row["wins"] or 0

                snapshot = BotSnapshot(
                    bot_id=str(row["bot_id"]),
                    bot_name=row["bot_name"],
                    date=date_str,
                    pnl=float(row["total_pnl"] or 0),
                    pnl_percent=0,
                    trades=trades,
                    wins=wins,
                    losses=row["losses"] or 0,
                    win_rate=(wins / trades * 100) if trades > 0 else 0,
                    avg_trade_pnl=float(row["avg_pnl"] or 0),
                    max_profit=float(row["max_profit"] or 0),
                    max_loss=float(row["max_loss"] or 0),
                    open_positions=0,
                    total_exposure=0
                )
                snapshots.append(snapshot)

            return snapshots

        except Exception as e:
            logger.error(f"Error collecting bot data: {e}")
            return []

    async def _collect_strategy_data(self, date: datetime) -> List[StrategySnapshot]:
        """Coleta dados de todas as estrategias"""
        date_str = date.strftime("%Y-%m-%d")
        next_date_str = (date + timedelta(days=1)).strftime("%Y-%m-%d")

        query = """
            SELECT
                s.id as strategy_id,
                s.name as strategy_name,
                COUNT(ss.id) as signals_generated,
                COUNT(CASE WHEN ss.status = 'executed' THEN 1 END) as signals_executed
            FROM strategies s
            LEFT JOIN strategy_signals ss ON s.id = ss.strategy_id
                AND ss.created_at >= $1
                AND ss.created_at < $2
            GROUP BY s.id, s.name
        """

        try:
            rows = await self.conn.fetch(query, date_str, next_date_str)

            snapshots = []
            for row in rows:
                generated = row["signals_generated"] or 0
                executed = row["signals_executed"] or 0

                snapshot = StrategySnapshot(
                    strategy_id=str(row["strategy_id"]),
                    strategy_name=row["strategy_name"],
                    date=date_str,
                    signals_generated=generated,
                    signals_executed=executed,
                    execution_rate=(executed / generated * 100) if generated > 0 else 0,
                    avg_signal_quality=0
                )
                snapshots.append(snapshot)

            return snapshots

        except Exception as e:
            logger.error(f"Error collecting strategy data: {e}")
            return []

    async def _generate_alerts(
        self,
        bot_snapshots: List[BotSnapshot],
        strategy_snapshots: List[StrategySnapshot]
    ) -> List[str]:
        """Gera alertas baseados nos dados coletados"""
        alerts = []

        # Alertas de bots
        for bot in bot_snapshots:
            # Bot com perda significativa
            if bot.pnl < -100:
                alerts.append(f"ALERTA: Bot '{bot.bot_name}' teve perda de ${abs(bot.pnl):.2f}")

            # Win rate muito baixo
            if bot.trades >= 10 and bot.win_rate < 30:
                alerts.append(f"ALERTA: Bot '{bot.bot_name}' com win rate de {bot.win_rate:.1f}%")

            # Perda maxima muito alta
            if bot.max_loss < -500:
                alerts.append(f"CRITICO: Bot '{bot.bot_name}' teve trade com perda de ${abs(bot.max_loss):.2f}")

        # Alertas de estrategias
        for strategy in strategy_snapshots:
            # Taxa de execucao baixa
            if strategy.signals_generated >= 10 and strategy.execution_rate < 50:
                alerts.append(
                    f"ALERTA: Estrategia '{strategy.strategy_name}' com "
                    f"{strategy.execution_rate:.1f}% de execucao"
                )

        # Alertas gerais
        total_pnl = sum(b.pnl for b in bot_snapshots)
        if total_pnl < -1000:
            alerts.append(f"CRITICO: Perda diaria total de ${abs(total_pnl):.2f}")

        return alerts

    async def _collect_market_conditions(self) -> Dict[str, Any]:
        """Coleta condicoes atuais de mercado"""
        # Aqui poderiamos integrar com APIs de mercado
        # Por enquanto retorna placeholder
        return {
            "btc_24h_change": 0,
            "market_sentiment": "neutral",
            "volatility": "normal",
            "volume": "average"
        }

    async def _save_daily_snapshot(self, snapshot: DailySnapshot):
        """Salva snapshot diario no banco"""
        query = """
            INSERT INTO ai_daily_snapshots (
                date, data, created_at
            ) VALUES ($1, $2, NOW())
            ON CONFLICT (date) DO UPDATE SET
                data = $2,
                updated_at = NOW()
        """

        try:
            await self.conn.execute(
                query,
                snapshot.date,
                json.dumps(asdict(snapshot), default=str)
            )
        except Exception as e:
            logger.error(f"Error saving daily snapshot: {e}")

    async def _save_bot_snapshot(self, snapshot: BotSnapshot):
        """Salva snapshot de bot"""
        query = """
            INSERT INTO ai_bot_snapshots (
                bot_id, date, data, created_at
            ) VALUES ($1, $2, $3, NOW())
            ON CONFLICT (bot_id, date) DO UPDATE SET
                data = $3,
                updated_at = NOW()
        """

        try:
            await self.conn.execute(
                query,
                snapshot.bot_id,
                snapshot.date,
                json.dumps(asdict(snapshot), default=str)
            )
        except Exception as e:
            logger.error(f"Error saving bot snapshot: {e}")

    async def _save_strategy_snapshot(self, snapshot: StrategySnapshot):
        """Salva snapshot de estrategia"""
        query = """
            INSERT INTO ai_strategy_snapshots (
                strategy_id, date, data, created_at
            ) VALUES ($1, $2, $3, NOW())
            ON CONFLICT (strategy_id, date) DO UPDATE SET
                data = $3,
                updated_at = NOW()
        """

        try:
            await self.conn.execute(
                query,
                snapshot.strategy_id,
                snapshot.date,
                json.dumps(asdict(snapshot), default=str)
            )
        except Exception as e:
            logger.error(f"Error saving strategy snapshot: {e}")

    async def get_historical_data(
        self,
        days: int = 30
    ) -> List[DailySnapshot]:
        """Busca dados historicos para analise da IA"""
        query = """
            SELECT data
            FROM ai_daily_snapshots
            WHERE date >= (CURRENT_DATE - INTERVAL '%s days')
            ORDER BY date DESC
        """

        try:
            rows = await self.conn.fetch(query % days)
            return [DailySnapshot(**json.loads(row["data"])) for row in rows]
        except Exception as e:
            logger.error(f"Error fetching historical data: {e}")
            return []

    async def get_bot_history(
        self,
        bot_id: str,
        days: int = 30
    ) -> List[BotSnapshot]:
        """Busca historico de um bot"""
        query = """
            SELECT data
            FROM ai_bot_snapshots
            WHERE bot_id = $1
            AND date >= (CURRENT_DATE - INTERVAL '%s days')
            ORDER BY date DESC
        """

        try:
            rows = await self.conn.fetch(query % days, bot_id)
            return [BotSnapshot(**json.loads(row["data"])) for row in rows]
        except Exception as e:
            logger.error(f"Error fetching bot history: {e}")
            return []


async def run_daily_collection():
    """Funcao principal para rodar coleta diaria"""
    collector = TradingDataCollector()

    try:
        await collector.connect()
        snapshot = await collector.collect_daily_data()

        print("=" * 60)
        print("COLETA DIARIA COMPLETA")
        print("=" * 60)
        print(f"Data: {snapshot.date}")
        print(f"P&L Total: ${snapshot.total_pnl:.2f}")
        print(f"Trades: {snapshot.total_trades}")
        print(f"Win Rate: {snapshot.win_rate:.1f}%")
        print(f"Bots Ativos: {snapshot.active_bots}")
        print(f"Alertas: {len(snapshot.alerts)}")

        if snapshot.alerts:
            print("\nALERTAS:")
            for alert in snapshot.alerts:
                print(f"  - {alert}")

    finally:
        await collector.disconnect()


if __name__ == "__main__":
    asyncio.run(run_daily_collection())

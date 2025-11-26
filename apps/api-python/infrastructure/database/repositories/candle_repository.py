"""
Candle Repository - Gerencia o cache de candles no banco de dados
"""
from typing import List, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy import select, delete, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert
import structlog

from infrastructure.database.models.candle import Candle


logger = structlog.get_logger()


class CandleRepository:
    """Repository para gerenciar cache de candles no banco de dados"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def save_candles(self, candles: List[Candle]) -> int:
        """
        Salva múltiplos candles no banco usando UPSERT

        Args:
            candles: Lista de objetos Candle para salvar

        Returns:
            Número de candles salvos/atualizados
        """
        if not candles:
            return 0

        try:
            # Preparar dados para bulk upsert
            candles_data = [
                {
                    "symbol": candle.symbol,
                    "interval": candle.interval,
                    "time": candle.time,
                    "open": candle.open,
                    "high": candle.high,
                    "low": candle.low,
                    "close": candle.close,
                    "volume": candle.volume,
                    "created_at": candle.created_at,
                    "updated_at": candle.updated_at,
                }
                for candle in candles
            ]

            # UPSERT usando PostgreSQL ON CONFLICT
            stmt = insert(Candle).values(candles_data)
            stmt = stmt.on_conflict_do_update(
                index_elements=["symbol", "interval", "time"],
                set_={
                    "open": stmt.excluded.open,
                    "high": stmt.excluded.high,
                    "low": stmt.excluded.low,
                    "close": stmt.excluded.close,
                    "volume": stmt.excluded.volume,
                    "updated_at": stmt.excluded.updated_at,
                },
            )

            await self.session.execute(stmt)
            await self.session.commit()

            logger.info(
                "Candles saved to cache",
                count=len(candles),
                symbol=candles[0].symbol if candles else None,
                interval=candles[0].interval if candles else None,
            )

            return len(candles)

        except Exception as e:
            await self.session.rollback()
            logger.error("Error saving candles to cache", error=str(e))
            raise

    async def get_candles(
        self,
        symbol: str,
        interval: str,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> List[Candle]:
        """
        Busca candles do cache

        Args:
            symbol: Símbolo do par (ex: BTCUSDT)
            interval: Intervalo do candle (1m, 5m, 1h, etc)
            start_time: Timestamp inicial em milissegundos (opcional)
            end_time: Timestamp final em milissegundos (opcional)
            limit: Número máximo de candles (opcional)

        Returns:
            Lista de candles ordenados por tempo
        """
        try:
            query = select(Candle).where(
                and_(
                    Candle.symbol == symbol,
                    Candle.interval == interval,
                )
            )

            # Aplicar filtros de tempo se fornecidos
            if start_time is not None:
                query = query.where(Candle.time >= start_time)

            if end_time is not None:
                query = query.where(Candle.time <= end_time)

            # Ordenar por tempo
            query = query.order_by(Candle.time.asc())

            # Aplicar limite se fornecido
            if limit is not None:
                query = query.limit(limit)

            result = await self.session.execute(query)
            candles = result.scalars().all()

            logger.debug(
                "Candles retrieved from cache",
                count=len(candles),
                symbol=symbol,
                interval=interval,
            )

            return list(candles)

        except Exception as e:
            logger.error("Error retrieving candles from cache", error=str(e))
            raise

    async def get_latest_candle(
        self, symbol: str, interval: str
    ) -> Optional[Candle]:
        """
        Busca o candle mais recente para um símbolo/intervalo

        Args:
            symbol: Símbolo do par
            interval: Intervalo do candle

        Returns:
            Candle mais recente ou None se não existir
        """
        try:
            query = (
                select(Candle)
                .where(
                    and_(
                        Candle.symbol == symbol,
                        Candle.interval == interval,
                    )
                )
                .order_by(Candle.time.desc())
                .limit(1)
            )

            result = await self.session.execute(query)
            candle = result.scalar_one_or_none()

            return candle

        except Exception as e:
            logger.error("Error getting latest candle", error=str(e))
            raise

    async def update_candle(self, candle: Candle) -> None:
        """
        Atualiza um candle específico

        Args:
            candle: Objeto Candle com dados atualizados
        """
        try:
            # Usar merge para atualizar
            await self.session.merge(candle)
            await self.session.commit()

            logger.debug(
                "Candle updated",
                symbol=candle.symbol,
                interval=candle.interval,
                time=candle.time,
            )

        except Exception as e:
            await self.session.rollback()
            logger.error("Error updating candle", error=str(e))
            raise

    async def delete_old_candles(self, days_to_keep: int = 30) -> int:
        """
        Remove candles antigos do cache

        Args:
            days_to_keep: Número de dias de dados para manter (padrão: 30)

        Returns:
            Número de candles deletados
        """
        try:
            # Calcular timestamp de corte (em milissegundos)
            cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
            cutoff_timestamp = int(cutoff_date.timestamp() * 1000)

            # Deletar candles antigos
            stmt = delete(Candle).where(Candle.time < cutoff_timestamp)
            result = await self.session.execute(stmt)
            await self.session.commit()

            deleted_count = result.rowcount

            logger.info(
                "Old candles deleted from cache",
                deleted_count=deleted_count,
                days_to_keep=days_to_keep,
            )

            return deleted_count

        except Exception as e:
            await self.session.rollback()
            logger.error("Error deleting old candles", error=str(e))
            raise

    async def get_gaps(
        self,
        symbol: str,
        interval: str,
        start_time: int,
        end_time: int,
        expected_interval_ms: int,
    ) -> List[Tuple[int, int]]:
        """
        Identifica gaps (períodos sem dados) no cache

        Args:
            symbol: Símbolo do par
            interval: Intervalo do candle
            start_time: Timestamp inicial em ms
            end_time: Timestamp final em ms
            expected_interval_ms: Intervalo esperado entre candles em ms

        Returns:
            Lista de tuplas (gap_start, gap_end) em milissegundos
        """
        try:
            # Buscar todos os candles no período
            query = (
                select(Candle.time)
                .where(
                    and_(
                        Candle.symbol == symbol,
                        Candle.interval == interval,
                        Candle.time >= start_time,
                        Candle.time <= end_time,
                    )
                )
                .order_by(Candle.time.asc())
            )

            result = await self.session.execute(query)
            timestamps = [row[0] for row in result.all()]

            if not timestamps:
                # Se não há dados, todo o período é um gap
                return [(start_time, end_time)]

            gaps = []

            # Verificar gap no início
            if timestamps[0] > start_time:
                gaps.append((start_time, timestamps[0] - expected_interval_ms))

            # Verificar gaps entre candles
            for i in range(len(timestamps) - 1):
                current_time = timestamps[i]
                next_time = timestamps[i + 1]
                expected_next = current_time + expected_interval_ms

                # Se há um gap maior que o esperado
                if next_time > expected_next + (expected_interval_ms * 0.1):
                    gaps.append((expected_next, next_time - expected_interval_ms))

            # Verificar gap no final
            if timestamps[-1] < end_time:
                gaps.append((timestamps[-1] + expected_interval_ms, end_time))

            logger.debug(
                "Gaps identified in cache",
                gaps_count=len(gaps),
                symbol=symbol,
                interval=interval,
            )

            return gaps

        except Exception as e:
            logger.error("Error identifying gaps", error=str(e))
            raise

    async def get_cache_stats(self, symbol: str, interval: str) -> dict:
        """
        Retorna estatísticas do cache para um símbolo/intervalo

        Args:
            symbol: Símbolo do par
            interval: Intervalo do candle

        Returns:
            Dicionário com estatísticas (count, oldest, newest)
        """
        try:
            # Contar total de candles
            from sqlalchemy import func

            count_query = select(func.count(Candle.id)).where(
                and_(
                    Candle.symbol == symbol,
                    Candle.interval == interval,
                )
            )
            count_result = await self.session.execute(count_query)
            total_count = count_result.scalar() or 0

            # Buscar timestamps mais antigo e mais recente
            stats_query = select(
                func.min(Candle.time).label("oldest"),
                func.max(Candle.time).label("newest"),
            ).where(
                and_(
                    Candle.symbol == symbol,
                    Candle.interval == interval,
                )
            )
            stats_result = await self.session.execute(stats_query)
            stats = stats_result.one_or_none()

            return {
                "total_candles": total_count,
                "oldest_timestamp": stats[0] if stats and stats[0] else None,
                "newest_timestamp": stats[1] if stats and stats[1] else None,
                "symbol": symbol,
                "interval": interval,
            }

        except Exception as e:
            logger.error("Error getting cache stats", error=str(e))
            raise

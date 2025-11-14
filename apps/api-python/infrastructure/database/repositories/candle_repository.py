"""
Repositório para operações com candles no banco de dados
"""

from typing import List, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, and_, desc
from sqlalchemy.dialects.postgresql import insert

from infrastructure.database.models.candle import Candle


class CandleRepository:
    """Repositório para gerenciar candles no banco de dados"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_candles(
        self,
        symbol: str,
        interval: str,
        start_time: int,
        end_time: int,
        limit: Optional[int] = None
    ) -> List[Candle]:
        """
        Busca candles do banco de dados
        """
        query = select(Candle).where(
            and_(
                Candle.symbol == symbol,
                Candle.interval == interval,
                Candle.time >= start_time,
                Candle.time <= end_time
            )
        ).order_by(Candle.time)

        if limit:
            query = query.limit(limit)

        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_latest_candle(
        self,
        symbol: str,
        interval: str
    ) -> Optional[Candle]:
        """
        Busca o candle mais recente
        """
        query = select(Candle).where(
            and_(
                Candle.symbol == symbol,
                Candle.interval == interval
            )
        ).order_by(desc(Candle.time)).limit(1)

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def upsert_candle(
        self,
        symbol: str,
        interval: str,
        time: int,
        open: float,
        high: float,
        low: float,
        close: float,
        volume: float
    ) -> Candle:
        """
        Insere ou atualiza um candle
        Usa UPSERT para evitar duplicatas
        """
        now = int(datetime.now().timestamp() * 1000)

        stmt = insert(Candle).values(
            symbol=symbol,
            interval=interval,
            time=time,
            open=open,
            high=high,
            low=low,
            close=close,
            volume=volume,
            created_at=now,
            updated_at=now
        )

        # Em caso de conflito, atualizar valores
        stmt = stmt.on_conflict_do_update(
            index_elements=["symbol", "interval", "time"],
            set_={
                "open": open,
                "high": high,
                "low": low,
                "close": close,
                "volume": volume,
                "updated_at": now
            }
        )

        await self.session.execute(stmt)

        # Retornar o candle
        return await self.get_candle(symbol, interval, time)

    async def get_candle(
        self,
        symbol: str,
        interval: str,
        time: int
    ) -> Optional[Candle]:
        """
        Busca um candle específico
        """
        query = select(Candle).where(
            and_(
                Candle.symbol == symbol,
                Candle.interval == interval,
                Candle.time == time
            )
        )

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def bulk_insert_candles(
        self,
        candles: List[dict]
    ) -> int:
        """
        Insere múltiplos candles de uma vez
        """
        if not candles:
            return 0

        now = int(datetime.now().timestamp() * 1000)

        # Preparar dados para insert
        values = []
        for candle in candles:
            values.append({
                "symbol": candle["symbol"],
                "interval": candle["interval"],
                "time": candle["time"],
                "open": candle["open"],
                "high": candle["high"],
                "low": candle["low"],
                "close": candle["close"],
                "volume": candle["volume"],
                "created_at": now,
                "updated_at": now
            })

        # Usar insert com on_conflict_do_nothing para evitar erros
        stmt = insert(Candle).values(values)
        stmt = stmt.on_conflict_do_nothing(
            index_elements=["symbol", "interval", "time"]
        )

        result = await self.session.execute(stmt)
        return result.rowcount

    async def delete_candles(
        self,
        symbol: str,
        interval: Optional[str] = None,
        before_time: Optional[int] = None
    ) -> int:
        """
        Deleta candles do banco
        """
        conditions = [Candle.symbol == symbol]

        if interval:
            conditions.append(Candle.interval == interval)

        if before_time:
            conditions.append(Candle.time < before_time)

        stmt = delete(Candle).where(and_(*conditions))
        result = await self.session.execute(stmt)
        return result.rowcount

    async def delete_all_candles(self) -> int:
        """
        Deleta todos os candles (usar com cuidado!)
        """
        stmt = delete(Candle)
        result = await self.session.execute(stmt)
        return result.rowcount

    async def get_candle_count(
        self,
        symbol: Optional[str] = None,
        interval: Optional[str] = None
    ) -> int:
        """
        Conta quantos candles existem no banco
        """
        from sqlalchemy import func

        query = select(func.count(Candle.time))

        if symbol:
            query = query.where(Candle.symbol == symbol)

        if interval:
            query = query.where(Candle.interval == interval)

        result = await self.session.execute(query)
        return result.scalar() or 0

    async def get_gaps(
        self,
        symbol: str,
        interval: str,
        start_time: int,
        end_time: int
    ) -> List[dict]:
        """
        Identifica gaps nos dados de candles
        """
        candles = await self.get_candles(symbol, interval, start_time, end_time)

        if len(candles) < 2:
            return []

        # Calcular intervalo em millisegundos
        interval_ms = self._get_interval_ms(interval)
        gaps = []

        for i in range(1, len(candles)):
            expected_time = candles[i - 1].time + interval_ms
            actual_time = candles[i].time

            if actual_time > expected_time + interval_ms:
                gaps.append({
                    "start": candles[i - 1].time,
                    "end": candles[i].time,
                    "missing_candles": int((actual_time - expected_time) / interval_ms)
                })

        return gaps

    def _get_interval_ms(self, interval: str) -> int:
        """Converte intervalo para millisegundos"""
        intervals = {
            "1m": 60000,
            "3m": 180000,
            "5m": 300000,
            "15m": 900000,
            "30m": 1800000,
            "1h": 3600000,
            "2h": 7200000,
            "4h": 14400000,
            "6h": 21600000,
            "8h": 28800000,
            "12h": 43200000,
            "1d": 86400000,
            "3d": 259200000,
            "1w": 604800000,
            "1M": 2592000000
        }
        return intervals.get(interval, 60000)
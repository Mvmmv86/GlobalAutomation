"""
Modelo de banco de dados para armazenar candles (OHLCV)
"""

from sqlalchemy import Column, String, BigInteger, Float, Index, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base

from infrastructure.database.base import Base


class Candle(Base):
    """
    Modelo para armazenar dados de candles (OHLCV)
    """
    __tablename__ = "candles"

    # Chave primária composta
    symbol = Column(String(20), primary_key=True)
    interval = Column(String(10), primary_key=True)
    time = Column(BigInteger, primary_key=True)  # Timestamp em millisegundos

    # Dados OHLCV
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Float, nullable=False)

    # Metadata
    created_at = Column(BigInteger, nullable=False)  # Quando foi criado no DB
    updated_at = Column(BigInteger, nullable=False)  # Última atualização

    __table_args__ = (
        # Índices para queries comuns
        Index("idx_candles_symbol_interval", "symbol", "interval"),
        Index("idx_candles_time", "time"),
        Index("idx_candles_symbol_time", "symbol", "time"),

        # Constraint única para evitar duplicatas
        UniqueConstraint("symbol", "interval", "time", name="uq_candle"),
    )

    def __repr__(self):
        return f"<Candle {self.symbol} {self.interval} {self.time}>"
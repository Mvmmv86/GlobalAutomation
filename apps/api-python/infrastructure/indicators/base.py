"""Base classes for technical indicators"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional


@dataclass
class Candle:
    """OHLCV candle data structure"""
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal

    @classmethod
    def from_binance(cls, data: List) -> "Candle":
        """Create Candle from Binance kline data

        Binance format: [timestamp, open, high, low, close, volume, ...]
        """
        return cls(
            timestamp=datetime.fromtimestamp(data[0] / 1000),
            open=Decimal(str(data[1])),
            high=Decimal(str(data[2])),
            low=Decimal(str(data[3])),
            close=Decimal(str(data[4])),
            volume=Decimal(str(data[5]))
        )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Candle":
        """Create Candle from dictionary"""
        return cls(
            timestamp=data.get("timestamp") or datetime.now(),
            open=Decimal(str(data.get("open", 0))),
            high=Decimal(str(data.get("high", 0))),
            low=Decimal(str(data.get("low", 0))),
            close=Decimal(str(data.get("close", 0))),
            volume=Decimal(str(data.get("volume", 0)))
        )


@dataclass
class IndicatorResult:
    """Result from an indicator calculation"""
    name: str
    timestamp: datetime
    values: Dict[str, Decimal]

    def get(self, key: str, default: Optional[Decimal] = None) -> Optional[Decimal]:
        """Get a specific value from the result"""
        return self.values.get(key, default)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "name": self.name,
            "timestamp": self.timestamp.isoformat(),
            "values": {k: float(v) for k, v in self.values.items()}
        }


class BaseIndicatorCalculator(ABC):
    """Base class for all indicator calculators"""

    name: str = "base"
    required_candles: int = 100

    def __init__(self, parameters: Optional[Dict[str, Any]] = None):
        """Initialize calculator with optional parameters"""
        self.parameters = parameters or {}
        self._validate_parameters()

    def _validate_parameters(self) -> None:
        """Validate parameters - override in subclasses"""
        pass

    @abstractmethod
    def calculate(self, candles: List[Candle]) -> IndicatorResult:
        """Calculate indicator values from candles

        Args:
            candles: List of OHLCV candles (oldest first)

        Returns:
            IndicatorResult with calculated values
        """
        pass

    def calculate_series(self, candles: List[Candle]) -> List[IndicatorResult]:
        """Calculate indicator values for all valid points in the series

        Args:
            candles: List of OHLCV candles (oldest first)

        Returns:
            List of IndicatorResult for each valid calculation point
        """
        results = []
        for i in range(self.required_candles, len(candles) + 1):
            subset = candles[:i]
            try:
                result = self.calculate(subset)
                results.append(result)
            except Exception:
                continue
        return results

    def get_parameter(self, key: str, default: Any = None) -> Any:
        """Get a parameter value with optional default"""
        return self.parameters.get(key, default)

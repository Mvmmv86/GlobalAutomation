"""
Indicator Calculator Controller
Provides API endpoints for calculating and retrieving technical indicators.

Used by:
- Frontend charts (Trading tab)
- Real-time indicator visualization
- Strategy backtesting preview
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

import structlog

# Lazy imports for indicators
INDICATORS_AVAILABLE = False
try:
    from infrastructure.indicators import (
        Candle,
        StochasticCalculator,
        StochasticRSICalculator,
        SuperTrendCalculator,
        ADXCalculator,
        VWAPCalculator,
        NadarayaWatsonCalculator,
        TPOCalculator,
        IchimokuCalculator,
        OBVCalculator,
    )
    INDICATORS_AVAILABLE = True
except ImportError:
    pass

from infrastructure.database.connection_transaction_mode import transaction_db

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/indicators", tags=["indicators"])


# ============================================================================
# Response Models
# ============================================================================

class IndicatorDataPoint(BaseModel):
    """Single indicator data point"""
    timestamp: datetime
    values: Dict[str, float]


class IndicatorResponse(BaseModel):
    """Response with indicator calculation results"""
    success: bool
    indicator_type: str
    symbol: str
    timeframe: str
    data: List[IndicatorDataPoint]
    parameters: Dict[str, Any]


class IndicatorListResponse(BaseModel):
    """List of available indicators"""
    success: bool
    indicators: List[Dict[str, Any]]


# ============================================================================
# Indicator Metadata
# ============================================================================

INDICATOR_METADATA = {
    "stochastic": {
        "name": "Stochastic Oscillator",
        "description": "Momentum indicator comparing close price to price range over time",
        "default_params": {"k_period": 14, "d_period": 3, "smooth_k": 3},
        "output_fields": ["k", "d", "signal"],
        "category": "momentum"
    },
    "stochastic_rsi": {
        "name": "Stochastic RSI",
        "description": "Stochastic applied to RSI values for enhanced momentum detection",
        "default_params": {"rsi_period": 14, "stoch_period": 14, "k_period": 3, "d_period": 3},
        "output_fields": ["k", "d", "rsi", "signal"],
        "category": "momentum"
    },
    "supertrend": {
        "name": "SuperTrend",
        "description": "Trend-following indicator using ATR for dynamic support/resistance",
        "default_params": {"period": 10, "multiplier": 3.0},
        "output_fields": ["supertrend", "trend", "upper_band", "lower_band", "signal"],
        "category": "trend"
    },
    "adx": {
        "name": "ADX (Average Directional Index)",
        "description": "Measures trend strength regardless of direction",
        "default_params": {"period": 14, "trend_threshold": 25},
        "output_fields": ["adx", "plus_di", "minus_di", "trend_strength", "signal"],
        "category": "trend"
    },
    "vwap": {
        "name": "VWAP (Volume Weighted Average Price)",
        "description": "Price benchmark weighted by volume, useful for intraday trading",
        "default_params": {"use_bands": True, "band_multiplier": 2.0},
        "output_fields": ["vwap", "upper_band", "lower_band", "deviation", "signal"],
        "category": "volume"
    },
    "nadaraya_watson": {
        "name": "Nadaraya-Watson Envelope",
        "description": "Non-parametric regression with envelope bands for mean reversion",
        "default_params": {"bandwidth": 8, "mult": 3.0},
        "output_fields": ["estimate", "upper", "lower", "signal"],
        "category": "regression"
    },
    "tpo": {
        "name": "TPO (Time Price Opportunity)",
        "description": "Market profile indicator showing value areas",
        "default_params": {"lookback": 20, "tick_size": 0.01},
        "output_fields": ["poc", "vah", "val", "signal"],
        "category": "volume"
    },
    "ichimoku": {
        "name": "Ichimoku Cloud",
        "description": "Japanese trend indicator with support/resistance, trend direction and momentum. Sharpe 1.25, CAGR 78%",
        "default_params": {"tenkan_period": 20, "kijun_period": 60, "senkou_b_period": 120, "displacement": 30},
        "output_fields": ["tenkan", "kijun", "senkou_a", "senkou_b", "cloud_top", "cloud_bottom", "trend", "signal"],
        "category": "trend"
    },
    "obv": {
        "name": "OBV (On-Balance Volume)",
        "description": "Momentum indicator using volume flow to predict price changes. Detects accumulation/distribution",
        "default_params": {"sma_period": 20, "signal_period": 14},
        "output_fields": ["obv", "obv_sma", "obv_normalized", "trend", "divergence", "signal"],
        "category": "volume"
    }
}

INDICATOR_CALCULATORS = {
    "stochastic": StochasticCalculator if INDICATORS_AVAILABLE else None,
    "stochastic_rsi": StochasticRSICalculator if INDICATORS_AVAILABLE else None,
    "supertrend": SuperTrendCalculator if INDICATORS_AVAILABLE else None,
    "adx": ADXCalculator if INDICATORS_AVAILABLE else None,
    "vwap": VWAPCalculator if INDICATORS_AVAILABLE else None,
    "nadaraya_watson": NadarayaWatsonCalculator if INDICATORS_AVAILABLE else None,
    "tpo": TPOCalculator if INDICATORS_AVAILABLE else None,
    "ichimoku": IchimokuCalculator if INDICATORS_AVAILABLE else None,
    "obv": OBVCalculator if INDICATORS_AVAILABLE else None,
}


# ============================================================================
# Helper Functions
# ============================================================================

async def fetch_candles(symbol: str, timeframe: str, limit: int = 500) -> List[Dict]:
    """
    Fetch candle data from database or cache
    """
    try:
        # Try to fetch from candles table
        query = """
            SELECT timestamp, open, high, low, close, volume
            FROM candles
            WHERE symbol = $1 AND timeframe = $2
            ORDER BY timestamp DESC
            LIMIT $3
        """
        rows = await transaction_db.fetch(query, symbol, timeframe, limit)

        if rows:
            return [dict(row) for row in reversed(rows)]

        # If no data in DB, return empty (frontend should fetch from exchange)
        logger.warning(f"No candle data found for {symbol} {timeframe}")
        return []

    except Exception as e:
        logger.error(f"Error fetching candles: {e}")
        return []


def convert_to_candle_objects(candle_data: List[Dict]) -> List:
    """Convert dict candles to Candle objects for indicator calculation"""
    if not INDICATORS_AVAILABLE:
        return []

    candles = []
    for c in candle_data:
        candles.append(Candle(
            timestamp=c.get('timestamp', datetime.now()),
            open=float(c.get('open', 0)),
            high=float(c.get('high', 0)),
            low=float(c.get('low', 0)),
            close=float(c.get('close', 0)),
            volume=float(c.get('volume', 0))
        ))
    return candles


# ============================================================================
# API Endpoints
# ============================================================================

@router.get("/available")
async def list_available_indicators() -> IndicatorListResponse:
    """
    List all available technical indicators with their metadata
    """
    indicators = []
    for ind_type, metadata in INDICATOR_METADATA.items():
        indicators.append({
            "type": ind_type,
            "name": metadata["name"],
            "description": metadata["description"],
            "category": metadata["category"],
            "default_params": metadata["default_params"],
            "output_fields": metadata["output_fields"],
            "available": INDICATOR_CALCULATORS.get(ind_type) is not None
        })

    return IndicatorListResponse(
        success=True,
        indicators=indicators
    )


@router.get("/{indicator_type}")
async def calculate_indicator(
    indicator_type: str,
    symbol: str = Query(..., description="Trading symbol (e.g., BTCUSDT)"),
    timeframe: str = Query(default="1h", description="Candle timeframe"),
    limit: int = Query(default=200, ge=50, le=1000, description="Number of candles"),
    # Common parameters
    period: Optional[int] = Query(None, description="Main period parameter"),
    k_period: Optional[int] = Query(None, description="K period for stochastic"),
    d_period: Optional[int] = Query(None, description="D period for stochastic"),
    smooth_k: Optional[int] = Query(None, description="K smoothing period"),
    rsi_period: Optional[int] = Query(None, description="RSI period"),
    stoch_period: Optional[int] = Query(None, description="Stochastic period"),
    multiplier: Optional[float] = Query(None, description="Multiplier for bands/ATR"),
    bandwidth: Optional[int] = Query(None, description="Bandwidth for Nadaraya-Watson"),
    mult: Optional[float] = Query(None, description="Multiplier for envelope"),
    use_bands: Optional[bool] = Query(None, description="Include deviation bands"),
    band_multiplier: Optional[float] = Query(None, description="Band width multiplier"),
    trend_threshold: Optional[float] = Query(None, description="ADX trend threshold"),
):
    """
    Calculate a specific indicator for given symbol/timeframe

    Returns series of indicator values that can be plotted on charts.
    """
    if not INDICATORS_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Indicator calculations not available. NumPy may not be installed."
        )

    if indicator_type not in INDICATOR_METADATA:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown indicator type: {indicator_type}. Available: {list(INDICATOR_METADATA.keys())}"
        )

    calculator_class = INDICATOR_CALCULATORS.get(indicator_type)
    if calculator_class is None:
        raise HTTPException(
            status_code=503,
            detail=f"Indicator {indicator_type} calculator not available"
        )

    # Build parameters from query params
    default_params = INDICATOR_METADATA[indicator_type]["default_params"].copy()

    # Override with provided params
    param_mapping = {
        "period": period,
        "k_period": k_period,
        "d_period": d_period,
        "smooth_k": smooth_k,
        "rsi_period": rsi_period,
        "stoch_period": stoch_period,
        "multiplier": multiplier,
        "bandwidth": bandwidth,
        "mult": mult,
        "use_bands": use_bands,
        "band_multiplier": band_multiplier,
        "trend_threshold": trend_threshold,
    }

    for param_name, param_value in param_mapping.items():
        if param_value is not None and param_name in default_params:
            default_params[param_name] = param_value

    try:
        # Fetch candle data
        candle_data = await fetch_candles(symbol, timeframe, limit)

        if not candle_data:
            raise HTTPException(
                status_code=404,
                detail=f"No candle data found for {symbol} {timeframe}"
            )

        # Convert to Candle objects
        candles = convert_to_candle_objects(candle_data)

        if len(candles) < 50:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient candle data. Need at least 50 candles, got {len(candles)}"
            )

        # Calculate indicator series
        calculator = calculator_class(default_params)
        results = calculator.calculate_series(candles)

        # Convert results to response format
        data_points = []
        for result in results:
            values = {}
            for key, value in result.values.items():
                try:
                    values[key] = float(value)
                except (TypeError, ValueError):
                    values[key] = 0.0
            data_points.append(IndicatorDataPoint(
                timestamp=result.timestamp,
                values=values
            ))

        return IndicatorResponse(
            success=True,
            indicator_type=indicator_type,
            symbol=symbol,
            timeframe=timeframe,
            data=data_points,
            parameters=default_params
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculating {indicator_type}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{indicator_type}/latest")
async def get_latest_indicator_value(
    indicator_type: str,
    symbol: str = Query(..., description="Trading symbol"),
    timeframe: str = Query(default="1h", description="Candle timeframe"),
    # Parameters (same as above)
    period: Optional[int] = Query(None),
    k_period: Optional[int] = Query(None),
    d_period: Optional[int] = Query(None),
    smooth_k: Optional[int] = Query(None),
    rsi_period: Optional[int] = Query(None),
    stoch_period: Optional[int] = Query(None),
    multiplier: Optional[float] = Query(None),
    bandwidth: Optional[int] = Query(None),
    mult: Optional[float] = Query(None),
    use_bands: Optional[bool] = Query(None),
    band_multiplier: Optional[float] = Query(None),
    trend_threshold: Optional[float] = Query(None),
):
    """
    Get only the latest indicator value (for real-time updates)
    """
    if not INDICATORS_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Indicator calculations not available"
        )

    if indicator_type not in INDICATOR_METADATA:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown indicator type: {indicator_type}"
        )

    calculator_class = INDICATOR_CALCULATORS.get(indicator_type)
    if calculator_class is None:
        raise HTTPException(
            status_code=503,
            detail=f"Indicator {indicator_type} calculator not available"
        )

    # Build parameters
    default_params = INDICATOR_METADATA[indicator_type]["default_params"].copy()

    param_mapping = {
        "period": period, "k_period": k_period, "d_period": d_period,
        "smooth_k": smooth_k, "rsi_period": rsi_period, "stoch_period": stoch_period,
        "multiplier": multiplier, "bandwidth": bandwidth, "mult": mult,
        "use_bands": use_bands, "band_multiplier": band_multiplier,
        "trend_threshold": trend_threshold,
    }

    for param_name, param_value in param_mapping.items():
        if param_value is not None and param_name in default_params:
            default_params[param_name] = param_value

    try:
        # Fetch minimal candle data for latest value
        candle_data = await fetch_candles(symbol, timeframe, 100)

        if not candle_data:
            raise HTTPException(
                status_code=404,
                detail=f"No candle data found for {symbol} {timeframe}"
            )

        candles = convert_to_candle_objects(candle_data)

        calculator = calculator_class(default_params)
        result = calculator.calculate(candles)

        values = {}
        for key, value in result.values.items():
            try:
                values[key] = float(value)
            except (TypeError, ValueError):
                values[key] = 0.0

        return {
            "success": True,
            "indicator_type": indicator_type,
            "symbol": symbol,
            "timeframe": timeframe,
            "timestamp": result.timestamp.isoformat(),
            "values": values,
            "parameters": default_params
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting latest {indicator_type}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch")
async def calculate_multiple_indicators(
    symbol: str = Query(..., description="Trading symbol"),
    timeframe: str = Query(default="1h", description="Candle timeframe"),
    indicators: List[str] = Query(..., description="List of indicator types to calculate"),
    limit: int = Query(default=200, ge=50, le=1000),
):
    """
    Calculate multiple indicators at once for efficient charting
    """
    if not INDICATORS_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Indicator calculations not available"
        )

    # Validate all indicator types
    invalid_indicators = [i for i in indicators if i not in INDICATOR_METADATA]
    if invalid_indicators:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown indicators: {invalid_indicators}"
        )

    try:
        # Fetch candles once
        candle_data = await fetch_candles(symbol, timeframe, limit)

        if not candle_data:
            raise HTTPException(
                status_code=404,
                detail=f"No candle data found for {symbol} {timeframe}"
            )

        candles = convert_to_candle_objects(candle_data)

        results = {}
        for ind_type in indicators:
            calculator_class = INDICATOR_CALCULATORS.get(ind_type)
            if calculator_class is None:
                results[ind_type] = {"error": "Calculator not available"}
                continue

            try:
                default_params = INDICATOR_METADATA[ind_type]["default_params"].copy()
                calculator = calculator_class(default_params)
                series = calculator.calculate_series(candles)

                data_points = []
                for result in series:
                    values = {}
                    for key, value in result.values.items():
                        try:
                            values[key] = float(value)
                        except (TypeError, ValueError):
                            values[key] = 0.0
                    data_points.append({
                        "timestamp": result.timestamp.isoformat(),
                        "values": values
                    })

                results[ind_type] = {
                    "success": True,
                    "data": data_points,
                    "parameters": default_params
                }

            except Exception as e:
                results[ind_type] = {"error": str(e)}

        return {
            "success": True,
            "symbol": symbol,
            "timeframe": timeframe,
            "indicators": results
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in batch calculation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

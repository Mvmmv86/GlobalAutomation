"""Indicator Alerts Controller - API endpoints for managing indicator signal alerts"""

from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Optional
import structlog
from datetime import datetime
import uuid as uuid_module
from uuid import UUID
from pydantic import BaseModel
from enum import Enum

from infrastructure.database.connection_transaction_mode import transaction_db
from presentation.middleware.auth import get_current_user_id

logger = structlog.get_logger(__name__)


# =====================================================
# ENUMS
# =====================================================

class IndicatorType(str, Enum):
    NADARAYA_WATSON = "nadaraya_watson"
    TPO = "tpo"
    RSI = "rsi"
    MACD = "macd"
    BOLLINGER = "bollinger"
    EMA_CROSS = "ema_cross"
    VOLUME_PROFILE = "volume_profile"
    CUSTOM = "custom"


class SignalType(str, Enum):
    BUY = "buy"
    SELL = "sell"
    BOTH = "both"


class AlertTimeframe(str, Enum):
    M1 = "1m"
    M3 = "3m"
    M5 = "5m"
    M15 = "15m"
    M30 = "30m"
    H1 = "1h"
    H2 = "2h"
    H4 = "4h"
    H6 = "6h"
    H8 = "8h"
    H12 = "12h"
    D1 = "1d"
    D3 = "3d"
    W1 = "1w"
    MO1 = "1M"


class AlertSoundType(str, Enum):
    DEFAULT = "default"
    BELL = "bell"
    CHIME = "chime"
    ALERT = "alert"
    ALARM = "alarm"  # Frontend compatibility
    CASH = "cash"
    SUCCESS = "success"
    NOTIFICATION = "notification"
    NONE = "none"


# =====================================================
# REQUEST/RESPONSE MODELS
# =====================================================

class IndicatorAlertCreate(BaseModel):
    """Request model for creating an indicator alert"""
    indicator_type: IndicatorType
    symbol: str
    timeframe: AlertTimeframe
    signal_type: SignalType = SignalType.BOTH
    indicator_params: Optional[dict] = None
    message_template: Optional[str] = None
    push_enabled: bool = True
    email_enabled: bool = False
    sound_type: AlertSoundType = AlertSoundType.DEFAULT
    cooldown_seconds: int = 300


class IndicatorAlertUpdate(BaseModel):
    """Request model for updating an indicator alert"""
    signal_type: Optional[SignalType] = None
    indicator_params: Optional[dict] = None
    message_template: Optional[str] = None
    push_enabled: Optional[bool] = None
    email_enabled: Optional[bool] = None
    sound_type: Optional[AlertSoundType] = None
    cooldown_seconds: Optional[int] = None
    is_active: Optional[bool] = None


class IndicatorAlertResponse(BaseModel):
    """Response model for an indicator alert"""
    id: str
    indicator_type: str
    symbol: str
    timeframe: str
    signal_type: str
    indicator_params: Optional[dict]
    message_template: str
    push_enabled: bool
    email_enabled: bool
    sound_type: str
    is_active: bool
    last_triggered_at: Optional[str]
    trigger_count: int
    cooldown_seconds: int
    created_at: str
    updated_at: str


# =====================================================
# HELPER FUNCTIONS
# =====================================================

def format_alert_response(alert: dict) -> dict:
    """Format alert record for API response"""
    return {
        "id": str(alert["id"]),
        "indicator_type": alert["indicator_type"],
        "symbol": alert["symbol"],
        "timeframe": alert["timeframe"],
        "signal_type": alert["signal_type"],
        "indicator_params": alert["indicator_params"],
        "message_template": alert["message_template"],
        "push_enabled": alert["push_enabled"],
        "email_enabled": alert["email_enabled"],
        "sound_type": alert["sound_type"],
        "is_active": alert["is_active"],
        "last_triggered_at": alert["last_triggered_at"].isoformat() if alert["last_triggered_at"] else None,
        "trigger_count": alert["trigger_count"],
        "cooldown_seconds": alert["cooldown_seconds"],
        "created_at": alert["created_at"].isoformat() if alert["created_at"] else None,
        "updated_at": alert["updated_at"].isoformat() if alert["updated_at"] else None
    }


# =====================================================
# ROUTER FACTORY
# =====================================================

def create_indicator_alerts_router() -> APIRouter:
    """Create and configure the indicator alerts router"""
    router = APIRouter(prefix="/api/v1/indicator-alerts", tags=["Indicator Alerts"])

    # =====================================================
    # GET /meta/available-indicators - List supported indicators
    # IMPORTANT: This must come BEFORE routes with {alert_id} parameter
    # =====================================================
    @router.get("/meta/available-indicators")
    async def get_available_indicators():
        """Get list of available indicators for alerts"""
        return {
            "success": True,
            "data": {
                "indicators": [
                    {
                        "type": "nadaraya_watson",
                        "name": "Nadaraya-Watson Envelope",
                        "description": "Gaussian Kernel Regression with MAE bands. Generates BUY/SELL signals on band crossings.",
                        "has_signals": True,
                        "params": {
                            "bandwidth": {"type": "integer", "default": 8, "min": 1, "max": 100},
                            "mult": {"type": "float", "default": 3.0, "min": 0.1, "max": 10.0}
                        }
                    },
                    {
                        "type": "tpo",
                        "name": "Time Price Opportunity (Market Profile)",
                        "description": "Market Profile with POC, VAH, VAL. Provides structural levels.",
                        "has_signals": False,
                        "params": {
                            "row_size": {"type": "integer", "default": 50}
                        }
                    },
                    {
                        "type": "rsi",
                        "name": "Relative Strength Index",
                        "description": "Momentum oscillator. Signals on overbought/oversold levels.",
                        "has_signals": True,
                        "params": {
                            "period": {"type": "integer", "default": 14},
                            "overbought": {"type": "integer", "default": 70},
                            "oversold": {"type": "integer", "default": 30}
                        }
                    },
                    {
                        "type": "macd",
                        "name": "MACD",
                        "description": "Moving Average Convergence Divergence. Signals on crossovers.",
                        "has_signals": True,
                        "params": {
                            "fast": {"type": "integer", "default": 12},
                            "slow": {"type": "integer", "default": 26},
                            "signal": {"type": "integer", "default": 9}
                        }
                    },
                    {
                        "type": "bollinger",
                        "name": "Bollinger Bands",
                        "description": "Volatility bands. Signals on band touches/crossings.",
                        "has_signals": True,
                        "params": {
                            "period": {"type": "integer", "default": 20},
                            "stddev": {"type": "float", "default": 2.0}
                        }
                    },
                    {
                        "type": "ema_cross",
                        "name": "EMA Crossover",
                        "description": "EMA crossover signals.",
                        "has_signals": True,
                        "params": {
                            "fast_period": {"type": "integer", "default": 9},
                            "slow_period": {"type": "integer", "default": 21}
                        }
                    }
                ],
                "timeframes": [
                    {"value": "1m", "label": "1 Minute"},
                    {"value": "3m", "label": "3 Minutes"},
                    {"value": "5m", "label": "5 Minutes"},
                    {"value": "15m", "label": "15 Minutes"},
                    {"value": "30m", "label": "30 Minutes"},
                    {"value": "1h", "label": "1 Hour"},
                    {"value": "2h", "label": "2 Hours"},
                    {"value": "4h", "label": "4 Hours"},
                    {"value": "6h", "label": "6 Hours"},
                    {"value": "8h", "label": "8 Hours"},
                    {"value": "12h", "label": "12 Hours"},
                    {"value": "1d", "label": "1 Day"},
                    {"value": "3d", "label": "3 Days"},
                    {"value": "1w", "label": "1 Week"},
                    {"value": "1M", "label": "1 Month"}
                ],
                "sounds": [
                    {"value": "default", "label": "Default"},
                    {"value": "bell", "label": "Bell"},
                    {"value": "chime", "label": "Chime"},
                    {"value": "alert", "label": "Alert"},
                    {"value": "cash", "label": "Cash Register"},
                    {"value": "success", "label": "Success"},
                    {"value": "notification", "label": "Notification"},
                    {"value": "none", "label": "No Sound"}
                ]
            }
        }

    # =====================================================
    # GET /indicator-alerts - List all alerts for user
    # =====================================================
    @router.get("")
    async def get_indicator_alerts(
        current_user_id: UUID = Depends(get_current_user_id),
        indicator_type: Optional[str] = Query(None, description="Filter by indicator type"),
        symbol: Optional[str] = Query(None, description="Filter by symbol"),
        active_only: bool = Query(False, description="Show only active alerts"),
        limit: int = Query(50, description="Maximum number of alerts to return"),
        offset: int = Query(0, description="Number of alerts to skip")
    ):
        """Get all indicator alerts for the authenticated user"""
        try:
            # Build query with filters
            query_conditions = ["user_id = $1"]
            params = [current_user_id]
            param_count = 2

            if indicator_type:
                query_conditions.append(f"indicator_type = ${param_count}")
                params.append(indicator_type)
                param_count += 1

            if symbol:
                query_conditions.append(f"symbol = ${param_count}")
                params.append(symbol.upper())
                param_count += 1

            if active_only:
                query_conditions.append("is_active = true")

            where_clause = " AND ".join(query_conditions)

            # Get alerts with pagination
            alerts = await transaction_db.fetch(f"""
                SELECT
                    id, indicator_type, symbol, timeframe, signal_type,
                    indicator_params, message_template, push_enabled, email_enabled,
                    sound_type, is_active, last_triggered_at, trigger_count,
                    cooldown_seconds, created_at, updated_at
                FROM indicator_alerts
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT ${param_count} OFFSET ${param_count + 1}
            """, *params, limit, offset)

            # Get total count
            total_result = await transaction_db.fetchrow(f"""
                SELECT COUNT(*) as total
                FROM indicator_alerts
                WHERE {where_clause}
            """, *params)

            alerts_list = [format_alert_response(a) for a in alerts]

            logger.info("Indicator alerts retrieved",
                       user_id=str(current_user_id),
                       count=len(alerts_list))

            return {
                "success": True,
                "data": alerts_list,
                "total": total_result["total"]
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error("Error retrieving indicator alerts", error=str(e), exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to retrieve indicator alerts")

    # =====================================================
    # GET /indicator-alerts/{id} - Get specific alert
    # =====================================================
    @router.get("/{alert_id}")
    async def get_indicator_alert(
        alert_id: str,
        current_user_id: UUID = Depends(get_current_user_id)
    ):
        """Get a specific indicator alert"""
        try:
            alert = await transaction_db.fetchrow("""
                SELECT
                    id, indicator_type, symbol, timeframe, signal_type,
                    indicator_params, message_template, push_enabled, email_enabled,
                    sound_type, is_active, last_triggered_at, trigger_count,
                    cooldown_seconds, created_at, updated_at
                FROM indicator_alerts
                WHERE id = $1 AND user_id = $2
            """, alert_id, current_user_id)

            if not alert:
                raise HTTPException(status_code=404, detail="Alert not found")

            return {
                "success": True,
                "data": format_alert_response(alert)
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error("Error retrieving indicator alert", alert_id=alert_id, error=str(e), exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to retrieve indicator alert")

    # =====================================================
    # POST /indicator-alerts - Create a new alert
    # =====================================================
    @router.post("")
    async def create_indicator_alert(
        alert: IndicatorAlertCreate,
        current_user_id: UUID = Depends(get_current_user_id)
    ):
        """Create a new indicator alert"""
        try:
            # Validate symbol format
            symbol = alert.symbol.upper()
            if len(symbol) < 3 or len(symbol) > 20:
                raise HTTPException(status_code=400, detail="Invalid symbol format")

            # Check if similar alert already exists
            existing = await transaction_db.fetchrow("""
                SELECT id FROM indicator_alerts
                WHERE user_id = $1 AND indicator_type = $2 AND symbol = $3 AND timeframe = $4
            """, current_user_id, alert.indicator_type.value, symbol, alert.timeframe.value)

            if existing:
                raise HTTPException(
                    status_code=400,
                    detail="Alert for this indicator/symbol/timeframe combination already exists"
                )

            # Default message template if not provided
            message_template = alert.message_template or f"Signal {{signal_type}} detected for {{symbol}} on {{timeframe}}"

            # Insert alert
            alert_id = await transaction_db.fetchval("""
                INSERT INTO indicator_alerts (
                    user_id, indicator_type, symbol, timeframe, signal_type,
                    indicator_params, message_template, push_enabled, email_enabled,
                    sound_type, cooldown_seconds, is_active, trigger_count,
                    created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, true, 0, NOW(), NOW())
                RETURNING id
            """, current_user_id, alert.indicator_type.value, symbol, alert.timeframe.value,
               alert.signal_type.value, alert.indicator_params, message_template,
               alert.push_enabled, alert.email_enabled, alert.sound_type.value,
               alert.cooldown_seconds)

            logger.info("Indicator alert created",
                       alert_id=str(alert_id),
                       user_id=str(current_user_id),
                       indicator_type=alert.indicator_type.value,
                       symbol=symbol)

            return {
                "success": True,
                "message": "Indicator alert created successfully",
                "data": {
                    "id": str(alert_id),
                    "indicator_type": alert.indicator_type.value,
                    "symbol": symbol,
                    "timeframe": alert.timeframe.value,
                    "signal_type": alert.signal_type.value
                }
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error("Error creating indicator alert", error=str(e), exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to create indicator alert")

    # =====================================================
    # PUT /indicator-alerts/{id} - Update an alert
    # =====================================================
    @router.put("/{alert_id}")
    async def update_indicator_alert(
        alert_id: str,
        alert: IndicatorAlertUpdate,
        current_user_id: UUID = Depends(get_current_user_id)
    ):
        """Update an indicator alert"""
        try:
            # Check if alert exists and belongs to user
            existing = await transaction_db.fetchrow("""
                SELECT id FROM indicator_alerts
                WHERE id = $1 AND user_id = $2
            """, alert_id, current_user_id)

            if not existing:
                raise HTTPException(status_code=404, detail="Alert not found")

            # Build update query dynamically
            update_fields = []
            params = []
            param_count = 1

            if alert.signal_type is not None:
                update_fields.append(f"signal_type = ${param_count}")
                params.append(alert.signal_type.value)
                param_count += 1

            if alert.indicator_params is not None:
                update_fields.append(f"indicator_params = ${param_count}")
                params.append(alert.indicator_params)
                param_count += 1

            if alert.message_template is not None:
                update_fields.append(f"message_template = ${param_count}")
                params.append(alert.message_template)
                param_count += 1

            if alert.push_enabled is not None:
                update_fields.append(f"push_enabled = ${param_count}")
                params.append(alert.push_enabled)
                param_count += 1

            if alert.email_enabled is not None:
                update_fields.append(f"email_enabled = ${param_count}")
                params.append(alert.email_enabled)
                param_count += 1

            if alert.sound_type is not None:
                update_fields.append(f"sound_type = ${param_count}")
                params.append(alert.sound_type.value)
                param_count += 1

            if alert.cooldown_seconds is not None:
                update_fields.append(f"cooldown_seconds = ${param_count}")
                params.append(alert.cooldown_seconds)
                param_count += 1

            if alert.is_active is not None:
                update_fields.append(f"is_active = ${param_count}")
                params.append(alert.is_active)
                param_count += 1

            if not update_fields:
                raise HTTPException(status_code=400, detail="No valid fields to update")

            update_fields.append("updated_at = NOW()")
            params.extend([alert_id, current_user_id])

            await transaction_db.execute(f"""
                UPDATE indicator_alerts
                SET {", ".join(update_fields)}
                WHERE id = ${param_count} AND user_id = ${param_count + 1}
            """, *params)

            logger.info("Indicator alert updated", alert_id=alert_id)

            return {"success": True, "message": "Indicator alert updated successfully"}

        except HTTPException:
            raise
        except Exception as e:
            logger.error("Error updating indicator alert", alert_id=alert_id, error=str(e), exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to update indicator alert")

    # =====================================================
    # DELETE /indicator-alerts/{id} - Delete an alert
    # =====================================================
    @router.delete("/{alert_id}")
    async def delete_indicator_alert(
        alert_id: str,
        current_user_id: UUID = Depends(get_current_user_id)
    ):
        """Delete an indicator alert"""
        try:
            # Delete only if belongs to user
            result = await transaction_db.execute("""
                DELETE FROM indicator_alerts
                WHERE id = $1 AND user_id = $2
            """, alert_id, current_user_id)

            logger.info("Indicator alert deleted", alert_id=alert_id)

            return {"success": True, "message": "Indicator alert deleted successfully"}

        except HTTPException:
            raise
        except Exception as e:
            logger.error("Error deleting indicator alert", alert_id=alert_id, error=str(e), exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to delete indicator alert")

    # =====================================================
    # POST /indicator-alerts/{id}/toggle - Toggle active state
    # =====================================================
    @router.post("/{alert_id}/toggle")
    async def toggle_indicator_alert(
        alert_id: str,
        current_user_id: UUID = Depends(get_current_user_id)
    ):
        """Toggle the active state of an indicator alert"""
        try:
            # Toggle the is_active field
            result = await transaction_db.fetchrow("""
                UPDATE indicator_alerts
                SET is_active = NOT is_active, updated_at = NOW()
                WHERE id = $1 AND user_id = $2
                RETURNING is_active
            """, alert_id, current_user_id)

            if not result:
                raise HTTPException(status_code=404, detail="Alert not found")

            logger.info("Indicator alert toggled", alert_id=alert_id, is_active=result["is_active"])

            return {
                "success": True,
                "message": f"Alert {'activated' if result['is_active'] else 'deactivated'}",
                "data": {"is_active": result["is_active"]}
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error("Error toggling indicator alert", alert_id=alert_id, error=str(e), exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to toggle indicator alert")

    # =====================================================
    # GET /indicator-alerts/{id}/history - Get alert trigger history
    # =====================================================
    @router.get("/{alert_id}/history")
    async def get_alert_history(
        alert_id: str,
        current_user_id: UUID = Depends(get_current_user_id),
        limit: int = Query(50, description="Maximum number of history entries"),
        offset: int = Query(0, description="Number of entries to skip")
    ):
        """Get the trigger history of an indicator alert"""
        try:
            # Verify alert belongs to user
            alert = await transaction_db.fetchrow("""
                SELECT id FROM indicator_alerts
                WHERE id = $1 AND user_id = $2
            """, alert_id, current_user_id)

            if not alert:
                raise HTTPException(status_code=404, detail="Alert not found")

            # Get history
            history = await transaction_db.fetch("""
                SELECT
                    id, signal_type, signal_price, push_sent, email_sent,
                    metadata, triggered_at
                FROM indicator_alert_history
                WHERE alert_id = $1
                ORDER BY triggered_at DESC
                LIMIT $2 OFFSET $3
            """, alert_id, limit, offset)

            history_list = []
            for h in history:
                history_list.append({
                    "id": str(h["id"]),
                    "signal_type": h["signal_type"],
                    "signal_price": float(h["signal_price"]) if h["signal_price"] else None,
                    "push_sent": h["push_sent"],
                    "email_sent": h["email_sent"],
                    "metadata": h["metadata"],
                    "triggered_at": h["triggered_at"].isoformat() if h["triggered_at"] else None
                })

            return {
                "success": True,
                "data": history_list
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error("Error retrieving alert history", alert_id=alert_id, error=str(e), exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to retrieve alert history")

    return router

"""
Indicator Alert Monitor Service
Monitors configured indicators and triggers alerts when signals are detected
"""

import asyncio
import structlog
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
import uuid as uuid_module

logger = structlog.get_logger(__name__)

# Try to import numpy, but don't fail if not available
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    np = None
    logger.warning("NumPy not available - Indicator Alert Monitor will be disabled")


class IndicatorAlertMonitor:
    """
    Background service that monitors indicator signals and triggers alerts.

    This service:
    1. Fetches active indicator alerts from the database
    2. Gets candle data for each symbol/timeframe combination
    3. Calculates indicator values and checks for signals
    4. Triggers notifications when signals are detected (respecting cooldown)
    """

    def __init__(self, db):
        self.db = db
        self.is_running = False
        self._task = None
        # Cache for last signal per alert (to avoid duplicate triggers)
        self._last_signals: Dict[str, Dict[str, Any]] = {}

    async def start(self):
        """Start the monitor service"""
        print(f"🔔 [IndicatorAlertMonitor] start() called - NumPy: {NUMPY_AVAILABLE}, is_running: {self.is_running}")

        if not NUMPY_AVAILABLE:
            print("❌ [IndicatorAlertMonitor] Cannot start - NumPy is not installed")
            logger.warning("Cannot start Indicator Alert Monitor - NumPy is not installed")
            return

        if self.is_running:
            print("⚠️ [IndicatorAlertMonitor] Already running, skipping start")
            logger.warning("Indicator alert monitor already running")
            return

        self.is_running = True
        self._task = asyncio.create_task(self._monitor_loop())
        print("✅ [IndicatorAlertMonitor] Started successfully - checking signals every 30 seconds")
        logger.info("🔔 Indicator Alert Monitor started successfully - checking signals every 30 seconds")

    async def stop(self):
        """Stop the monitor service"""
        self.is_running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("⏹️ Indicator Alert Monitor stopped")

    async def _monitor_loop(self):
        """Main monitoring loop"""
        while self.is_running:
            try:
                await self._check_all_alerts()
                await asyncio.sleep(30)  # Check every 30 seconds
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in indicator alert monitor loop: {e}")
                await asyncio.sleep(10)  # Wait before retry

    async def _check_all_alerts(self):
        """Check all active alerts for signals"""
        try:
            # Fetch all active alerts
            alerts = await self.db.fetch("""
                SELECT
                    ia.id, ia.user_id, ia.indicator_type, ia.symbol, ia.timeframe,
                    ia.signal_type, ia.indicator_params, ia.message_template,
                    ia.push_enabled, ia.email_enabled, ia.sound_type,
                    ia.cooldown_seconds, ia.last_triggered_at
                FROM indicator_alerts ia
                WHERE ia.is_active = true
            """)

            print(f"🔍 [IndicatorAlertMonitor] Found {len(alerts) if alerts else 0} active alerts")

            if not alerts:
                print("⚠️ [IndicatorAlertMonitor] No active alerts configured in database")
                return

            logger.debug(f"🔍 Checking {len(alerts)} active indicator alerts")

            # Group alerts by symbol/timeframe to minimize API calls
            grouped_alerts: Dict[str, List[dict]] = {}
            for alert in alerts:
                key = f"{alert['symbol']}_{alert['timeframe']}"
                if key not in grouped_alerts:
                    grouped_alerts[key] = []
                grouped_alerts[key].append(dict(alert))

            # Process each group
            for key, alert_group in grouped_alerts.items():
                try:
                    symbol = alert_group[0]['symbol']
                    timeframe = alert_group[0]['timeframe']

                    print(f"📈 [IndicatorAlertMonitor] Processing {symbol} {timeframe} ({len(alert_group)} alerts)")

                    # Fetch candle data for this symbol/timeframe
                    candles = await self._fetch_candles(symbol, timeframe)

                    print(f"📊 [IndicatorAlertMonitor] Got {len(candles) if candles else 0} candles for {symbol}")

                    if not candles or len(candles) < 50:
                        print(f"⚠️ [IndicatorAlertMonitor] Not enough candles for {symbol} {timeframe} (need 50, got {len(candles) if candles else 0})")
                        continue

                    # Check each alert in this group
                    for alert in alert_group:
                        await self._check_alert_signal(alert, candles)

                except Exception as e:
                    logger.error(f"Error checking alerts for {key}: {e}")

        except Exception as e:
            logger.error(f"Error fetching alerts: {e}")

    async def _fetch_candles(self, symbol: str, timeframe: str, limit: int = 200) -> List[Dict]:
        """Fetch candle data from the market API"""
        try:
            import httpx
            import os

            api_port = os.getenv('PORT', '8001')
            url = f"http://localhost:{api_port}/api/v1/market/candles"

            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(
                    url,
                    params={
                        "symbol": symbol,
                        "interval": timeframe,
                        "limit": limit
                    }
                )

                print(f"📡 [IndicatorAlertMonitor] Candles API response: status={response.status_code}, url={url}")

                if response.status_code == 200:
                    data = response.json()
                    print(f"📦 [IndicatorAlertMonitor] Response keys: {list(data.keys()) if isinstance(data, dict) else type(data)}, success={data.get('success') if isinstance(data, dict) else 'N/A'}")
                    if data.get("success"):
                        # API returns candles under "candles" key, not "data"
                        candles = data.get("candles", [])
                        print(f"📊 [IndicatorAlertMonitor] Parsed {len(candles)} candles from response")
                        return candles
                    else:
                        print(f"⚠️ [IndicatorAlertMonitor] API returned success=False: {data}")
                else:
                    print(f"❌ [IndicatorAlertMonitor] API error {response.status_code}: {response.text[:200]}")

                return []

        except Exception as e:
            print(f"❌ [IndicatorAlertMonitor] Exception fetching candles for {symbol}: {e}")
            logger.error(f"Error fetching candles for {symbol}: {e}")
            return []

    async def _check_alert_signal(self, alert: dict, candles: List[Dict]):
        """Check if alert conditions are met and trigger if necessary"""
        try:
            alert_id = str(alert['id'])
            indicator_type = alert['indicator_type']
            signal_type = alert['signal_type']  # 'buy', 'sell', or 'both'
            cooldown = alert['cooldown_seconds']
            last_triggered = alert['last_triggered_at']

            print(f"🔎 [IndicatorAlertMonitor] Checking alert {alert_id[:8]}... indicator={indicator_type}, signal_type={signal_type}")

            # Check cooldown
            if last_triggered:
                time_since_trigger = (datetime.now(timezone.utc) - last_triggered).total_seconds()
                if time_since_trigger < cooldown:
                    print(f"⏳ [IndicatorAlertMonitor] Alert {alert_id[:8]} in cooldown ({int(time_since_trigger)}s / {cooldown}s)")
                    return  # Still in cooldown

            # Calculate indicator and check for signals
            detected_signal = await self._calculate_indicator_signal(
                indicator_type,
                candles,
                alert.get('indicator_params') or {}
            )

            print(f"📉 [IndicatorAlertMonitor] Signal calculation result: {detected_signal}")

            if not detected_signal:
                print(f"❌ [IndicatorAlertMonitor] No signal detected for alert {alert_id[:8]}")
                return

            # Check if this signal type matches alert configuration
            if signal_type != 'both' and detected_signal['type'] != signal_type:
                return

            # Check if this is a new signal (not same as last)
            last_signal = self._last_signals.get(alert_id, {})
            if (last_signal.get('type') == detected_signal['type'] and
                last_signal.get('candle_time') == detected_signal.get('candle_time')):
                return  # Same signal on same candle

            # NEW SIGNAL DETECTED! Trigger alert
            logger.info(
                f"🔔 SIGNAL DETECTED: {alert['symbol']} {indicator_type} {detected_signal['type'].upper()}",
                alert_id=alert_id,
                price=detected_signal.get('price')
            )

            # Update last signal cache
            self._last_signals[alert_id] = {
                'type': detected_signal['type'],
                'candle_time': detected_signal.get('candle_time'),
                'price': detected_signal.get('price'),
                'triggered_at': datetime.now(timezone.utc)
            }

            # Create notification and update alert
            await self._trigger_alert(alert, detected_signal)

        except Exception as e:
            logger.error(f"Error checking alert signal: {e}")

    async def _calculate_indicator_signal(
        self,
        indicator_type: str,
        candles: List[Dict],
        params: dict
    ) -> Optional[Dict]:
        """
        Calculate indicator values and detect signals.
        Returns signal dict if detected, None otherwise.
        """
        try:
            # Extract OHLC data
            closes = np.array([float(c.get('close', c.get('c', 0))) for c in candles])
            highs = np.array([float(c.get('high', c.get('h', 0))) for c in candles])
            lows = np.array([float(c.get('low', c.get('l', 0))) for c in candles])
            times = [c.get('time', c.get('t', 0)) for c in candles]

            if len(closes) < 50:
                return None

            # Calculate based on indicator type
            print(f"🧮 [IndicatorAlertMonitor] Calculating {indicator_type} with {len(closes)} candles, params={params}")

            if indicator_type == 'nadaraya_watson':
                return self._calc_nadaraya_watson_signal(closes, times, params)
            elif indicator_type == 'rsi':
                return self._calc_rsi_signal(closes, times, params)
            elif indicator_type == 'macd':
                return self._calc_macd_signal(closes, times, params)
            elif indicator_type == 'bollinger':
                return self._calc_bollinger_signal(closes, times, params)
            elif indicator_type == 'ema_cross':
                return self._calc_ema_cross_signal(closes, times, params)
            elif indicator_type == 'custom':
                # Custom indicators handled differently - they rely on external signals
                print(f"⚠️ [IndicatorAlertMonitor] Custom indicator type not supported in automatic detection")
                return None
            else:
                print(f"⚠️ [IndicatorAlertMonitor] Unknown indicator type: {indicator_type}")
                return None

        except Exception as e:
            logger.error(f"Error calculating indicator {indicator_type}: {e}")
            return None

    def _calc_nadaraya_watson_signal(
        self,
        closes,  # np.ndarray when numpy available
        times: List,
        params: dict
    ) -> Optional[Dict]:
        """
        Calculate Nadaraya-Watson Envelope indicator signals.
        Signal: BUY when close < lower band, SELL when close > upper band
        """
        bandwidth = params.get('bandwidth', 8)
        mult = params.get('mult', 3.0)

        n = len(closes)
        if n < bandwidth * 2:
            return None

        # Gaussian Kernel Regression
        y_hat = np.zeros(n)

        for i in range(n):
            sum_weights = 0.0
            sum_weighted = 0.0

            for j in range(n):
                # Gaussian kernel
                distance = (i - j) / bandwidth
                weight = np.exp(-0.5 * distance * distance)
                sum_weights += weight
                sum_weighted += weight * closes[j]

            y_hat[i] = sum_weighted / sum_weights if sum_weights > 0 else closes[i]

        # Calculate MAE for bands
        mae = np.mean(np.abs(closes - y_hat))
        upper = y_hat + mult * mae
        lower = y_hat - mult * mae

        # Check last completed candle (not current)
        idx = -2  # Second to last candle (completed)
        curr_close = closes[idx]

        # BUY signal: close below lower band
        if curr_close < lower[idx]:
            return {
                'type': 'buy',
                'price': curr_close,
                'candle_time': times[idx],
                'indicator_value': y_hat[idx],
                'band_value': lower[idx]
            }

        # SELL signal: close above upper band
        if curr_close > upper[idx]:
            return {
                'type': 'sell',
                'price': curr_close,
                'candle_time': times[idx],
                'indicator_value': y_hat[idx],
                'band_value': upper[idx]
            }

        return None

    def _calc_rsi_signal(
        self,
        closes,  # np.ndarray when numpy available
        times: List,
        params: dict
    ) -> Optional[Dict]:
        """
        Calculate RSI signals.
        Signal: BUY when RSI < oversold, SELL when RSI > overbought
        """
        period = params.get('period', 14)
        overbought = params.get('overbought', 70)
        oversold = params.get('oversold', 30)

        if len(closes) < period + 1:
            return None

        # Calculate RSI
        deltas = np.diff(closes)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)

        avg_gain = np.zeros(len(deltas))
        avg_loss = np.zeros(len(deltas))

        # Initial SMA
        avg_gain[period-1] = np.mean(gains[:period])
        avg_loss[period-1] = np.mean(losses[:period])

        # EMA
        for i in range(period, len(deltas)):
            avg_gain[i] = (avg_gain[i-1] * (period-1) + gains[i]) / period
            avg_loss[i] = (avg_loss[i-1] * (period-1) + losses[i]) / period

        rs = np.where(avg_loss != 0, avg_gain / avg_loss, 100)
        rsi = 100 - (100 / (1 + rs))

        # Check last completed candle
        idx = -2
        rsi_value = rsi[idx]

        if rsi_value < oversold:
            return {
                'type': 'buy',
                'price': closes[idx],
                'candle_time': times[idx],
                'indicator_value': rsi_value
            }

        if rsi_value > overbought:
            return {
                'type': 'sell',
                'price': closes[idx],
                'candle_time': times[idx],
                'indicator_value': rsi_value
            }

        return None

    def _calc_macd_signal(
        self,
        closes,  # np.ndarray when numpy available
        times: List,
        params: dict
    ) -> Optional[Dict]:
        """
        Calculate MACD crossover signals.
        Signal: BUY on bullish cross, SELL on bearish cross
        """
        fast = params.get('fast', 12)
        slow = params.get('slow', 26)
        signal_period = params.get('signal', 9)

        if len(closes) < slow + signal_period:
            return None

        # Calculate EMAs
        def ema(data, period):
            alpha = 2 / (period + 1)
            result = np.zeros(len(data))
            result[0] = data[0]
            for i in range(1, len(data)):
                result[i] = alpha * data[i] + (1 - alpha) * result[i-1]
            return result

        ema_fast = ema(closes, fast)
        ema_slow = ema(closes, slow)
        macd_line = ema_fast - ema_slow
        signal_line = ema(macd_line, signal_period)

        # Check for crossover on last completed candle
        idx = -2
        prev_idx = -3

        # Bullish cross (MACD crosses above signal)
        if macd_line[prev_idx] < signal_line[prev_idx] and macd_line[idx] > signal_line[idx]:
            return {
                'type': 'buy',
                'price': closes[idx],
                'candle_time': times[idx],
                'indicator_value': macd_line[idx]
            }

        # Bearish cross (MACD crosses below signal)
        if macd_line[prev_idx] > signal_line[prev_idx] and macd_line[idx] < signal_line[idx]:
            return {
                'type': 'sell',
                'price': closes[idx],
                'candle_time': times[idx],
                'indicator_value': macd_line[idx]
            }

        return None

    def _calc_bollinger_signal(
        self,
        closes,  # np.ndarray when numpy available
        times: List,
        params: dict
    ) -> Optional[Dict]:
        """
        Calculate Bollinger Bands signals.
        Signal: BUY when close touches lower band, SELL when close touches upper band
        """
        period = params.get('period', 20)
        stddev = params.get('stddev', 2.0)

        if len(closes) < period:
            return None

        # Calculate Bollinger Bands
        sma = np.zeros(len(closes))
        upper = np.zeros(len(closes))
        lower = np.zeros(len(closes))

        for i in range(period - 1, len(closes)):
            window = closes[i - period + 1:i + 1]
            sma[i] = np.mean(window)
            std = np.std(window)
            upper[i] = sma[i] + stddev * std
            lower[i] = sma[i] - stddev * std

        # Check last completed candle
        idx = -2
        curr_close = closes[idx]

        if curr_close <= lower[idx]:
            return {
                'type': 'buy',
                'price': curr_close,
                'candle_time': times[idx],
                'indicator_value': sma[idx],
                'band_value': lower[idx]
            }

        if curr_close >= upper[idx]:
            return {
                'type': 'sell',
                'price': curr_close,
                'candle_time': times[idx],
                'indicator_value': sma[idx],
                'band_value': upper[idx]
            }

        return None

    def _calc_ema_cross_signal(
        self,
        closes,  # np.ndarray when numpy available
        times: List,
        params: dict
    ) -> Optional[Dict]:
        """
        Calculate EMA crossover signals.
        Signal: BUY on golden cross, SELL on death cross
        """
        fast_period = params.get('fast_period', 9)
        slow_period = params.get('slow_period', 21)

        if len(closes) < slow_period + 2:
            return None

        def ema(data, period):
            alpha = 2 / (period + 1)
            result = np.zeros(len(data))
            result[0] = data[0]
            for i in range(1, len(data)):
                result[i] = alpha * data[i] + (1 - alpha) * result[i-1]
            return result

        ema_fast = ema(closes, fast_period)
        ema_slow = ema(closes, slow_period)

        # Check for crossover on last completed candle
        idx = -2
        prev_idx = -3

        # Golden cross (fast crosses above slow)
        if ema_fast[prev_idx] < ema_slow[prev_idx] and ema_fast[idx] > ema_slow[idx]:
            return {
                'type': 'buy',
                'price': closes[idx],
                'candle_time': times[idx],
                'indicator_value': ema_fast[idx]
            }

        # Death cross (fast crosses below slow)
        if ema_fast[prev_idx] > ema_slow[prev_idx] and ema_fast[idx] < ema_slow[idx]:
            return {
                'type': 'sell',
                'price': closes[idx],
                'candle_time': times[idx],
                'indicator_value': ema_fast[idx]
            }

        return None

    async def _trigger_alert(self, alert: dict, signal: dict):
        """Trigger the alert - create notification and update database"""
        import json

        try:
            alert_id = alert['id']
            user_id = alert['user_id']
            symbol = alert['symbol']
            indicator_type = alert['indicator_type']
            signal_type = signal['type']
            # Convert numpy float to Python float for JSON serialization
            price = float(signal.get('price', 0))

            # Format message from template
            message_template = alert.get('message_template') or "Signal {signal_type} detected for {symbol} on {timeframe}"
            message = message_template.format(
                signal_type=signal_type.upper(),
                symbol=symbol,
                timeframe=alert['timeframe'],
                price=f"${price:.2f}" if price else "N/A",
                indicator=indicator_type
            )

            # Create notification if push is enabled
            # Category 'price_alert' is used for indicator signals (valid enum values: order, position, system, market, bot, price_alert)
            if alert.get('push_enabled', True):
                notification_metadata = json.dumps({
                    'alert_id': str(alert_id),
                    'indicator_type': indicator_type,
                    'signal_type': signal_type,
                    'symbol': symbol,
                    'timeframe': alert['timeframe'],
                    'price': price,
                    'sound_type': alert.get('sound_type', 'default')
                })

                print(f"📢 [IndicatorAlertMonitor] Creating notification: {signal_type.upper()} for {symbol} @ ${price:.2f}, user_id={user_id}")

                try:
                    await self.db.execute("""
                        INSERT INTO notifications (
                            type, category, title, message, user_id,
                            metadata, created_at, updated_at
                        ) VALUES (
                            $1, 'price_alert', $2, $3, $4, $5::jsonb, NOW(), NOW()
                        )
                    """,
                        'success' if signal_type == 'buy' else 'warning',
                        f"{'🟢' if signal_type == 'buy' else '🔴'} {indicator_type.upper()}: {symbol} {signal_type.upper()}",
                        message,
                        user_id,
                        notification_metadata
                    )
                    print(f"✅ [IndicatorAlertMonitor] Notification INSERT succeeded!")
                except Exception as insert_err:
                    print(f"❌ [IndicatorAlertMonitor] Notification INSERT failed: {insert_err}")

            # Record in alert history - convert numpy values to Python types for JSON serialization
            history_metadata = {}
            for k, v in signal.items():
                if hasattr(v, 'item'):  # numpy scalar
                    history_metadata[k] = v.item()
                else:
                    history_metadata[k] = v

            await self.db.execute("""
                INSERT INTO indicator_alert_history (
                    alert_id, signal_type, signal_price, push_sent, email_sent,
                    metadata, triggered_at
                ) VALUES ($1, $2, $3, $4, $5, $6::jsonb, NOW())
            """,
                alert_id,
                signal_type,
                price,
                alert.get('push_enabled', True),
                False,  # Email not implemented yet
                json.dumps(history_metadata)
            )

            # Update alert's last_triggered_at and trigger_count
            await self.db.execute("""
                UPDATE indicator_alerts
                SET last_triggered_at = NOW(),
                    trigger_count = trigger_count + 1,
                    updated_at = NOW()
                WHERE id = $1
            """, alert_id)

            logger.info(
                f"✅ Alert triggered successfully",
                alert_id=str(alert_id),
                symbol=symbol,
                signal=signal_type
            )

            # TODO: Send email if email_enabled
            if alert.get('email_enabled', False):
                logger.info(f"📧 Email notification would be sent to user {user_id}")
                # await self._send_email_alert(alert, signal, message)

        except Exception as e:
            logger.error(f"Error triggering alert: {e}")


# Global instance
_indicator_alert_monitor = None


def get_indicator_alert_monitor(db) -> IndicatorAlertMonitor:
    """Get or create the indicator alert monitor instance"""
    global _indicator_alert_monitor
    # Always create a new instance to avoid stale state from previous reload cycles
    # This fixes the "already running" bug when uvicorn reloads the server
    if _indicator_alert_monitor is not None:
        # Reset the old instance state
        _indicator_alert_monitor.is_running = False
        _indicator_alert_monitor._task = None
    _indicator_alert_monitor = IndicatorAlertMonitor(db)
    return _indicator_alert_monitor

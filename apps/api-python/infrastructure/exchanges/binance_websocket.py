"""
Binance WebSocket Manager for Real-Time Market Data

Provides WebSocket connections to Binance for streaming:
- Kline/Candlestick data
- Ticker updates
- Market depth (orderbook)

This is used by the Strategy Engine for real-time signal generation.
No API keys required - uses public WebSocket endpoints.
"""

import asyncio
import json
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

import structlog
import websockets
from websockets.exceptions import ConnectionClosed, ConnectionClosedError

logger = structlog.get_logger()


class StreamType(str, Enum):
    """WebSocket stream types"""
    KLINE = "kline"
    TICKER = "ticker"
    DEPTH = "depth"
    TRADE = "trade"


@dataclass
class KlineData:
    """Parsed kline/candlestick data from WebSocket"""
    symbol: str
    interval: str
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    is_closed: bool  # True when candle is complete

    @classmethod
    def from_ws_message(cls, data: Dict[str, Any]) -> "KlineData":
        """Parse from Binance WebSocket kline message"""
        k = data.get("k", {})
        return cls(
            symbol=data.get("s", ""),
            interval=k.get("i", ""),
            timestamp=datetime.fromtimestamp(k.get("t", 0) / 1000),
            open=Decimal(str(k.get("o", "0"))),
            high=Decimal(str(k.get("h", "0"))),
            low=Decimal(str(k.get("l", "0"))),
            close=Decimal(str(k.get("c", "0"))),
            volume=Decimal(str(k.get("v", "0"))),
            is_closed=k.get("x", False)
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict format for indicators"""
        return {
            'time': int(self.timestamp.timestamp() * 1000),
            'open': float(self.open),
            'high': float(self.high),
            'low': float(self.low),
            'close': float(self.close),
            'volume': float(self.volume)
        }


@dataclass
class TickerData:
    """Parsed 24hr ticker data from WebSocket"""
    symbol: str
    price: Decimal
    price_change: Decimal
    price_change_percent: Decimal
    volume: Decimal
    high: Decimal
    low: Decimal

    @classmethod
    def from_ws_message(cls, data: Dict[str, Any]) -> "TickerData":
        """Parse from Binance WebSocket ticker message"""
        return cls(
            symbol=data.get("s", ""),
            price=Decimal(str(data.get("c", "0"))),
            price_change=Decimal(str(data.get("p", "0"))),
            price_change_percent=Decimal(str(data.get("P", "0"))),
            volume=Decimal(str(data.get("v", "0"))),
            high=Decimal(str(data.get("h", "0"))),
            low=Decimal(str(data.get("l", "0")))
        )


# Type alias for callbacks
KlineCallback = Callable[[KlineData], None]
TickerCallback = Callable[[TickerData], None]


class BinanceWebSocketManager:
    """
    Manager for Binance WebSocket connections

    Handles:
    - Multiple symbol subscriptions
    - Automatic reconnection
    - Message routing to callbacks
    - Connection health monitoring

    Usage:
        manager = BinanceWebSocketManager()
        await manager.start()

        # Subscribe to kline updates
        await manager.subscribe_kline("BTCUSDT", "5m", callback_function)

        # When done
        await manager.stop()
    """

    # Binance WebSocket endpoints
    SPOT_WS_URL = "wss://stream.binance.com:9443/ws"
    FUTURES_WS_URL = "wss://fstream.binance.com/ws"
    COMBINED_STREAM_URL = "wss://stream.binance.com:9443/stream"
    FUTURES_COMBINED_URL = "wss://fstream.binance.com/stream"

    def __init__(self, use_futures: bool = True):
        """
        Initialize WebSocket manager

        Args:
            use_futures: Use futures streams (default True)
        """
        self.use_futures = use_futures
        self.base_url = self.FUTURES_COMBINED_URL if use_futures else self.COMBINED_STREAM_URL

        # Connection state
        self._ws: Optional[websockets.WebSocketClientProtocol] = None
        self._running = False
        self._reconnect_attempts = 0
        self._max_reconnect_attempts = 10
        self._reconnect_delay = 5  # seconds

        # Subscriptions
        self._kline_callbacks: Dict[str, List[KlineCallback]] = {}  # stream_id -> callbacks
        self._ticker_callbacks: Dict[str, List[TickerCallback]] = {}

        # Active streams
        self._subscribed_streams: Set[str] = set()

        # Tasks
        self._receive_task: Optional[asyncio.Task] = None
        self._heartbeat_task: Optional[asyncio.Task] = None

        # Message queue for processing
        self._message_queue: asyncio.Queue = asyncio.Queue()

        logger.info(
            "BinanceWebSocketManager initialized",
            use_futures=use_futures,
            base_url=self.base_url
        )

    async def start(self) -> None:
        """Start the WebSocket manager"""
        if self._running:
            logger.warning("WebSocket manager already running")
            return

        self._running = True
        await self._connect()

        # Start background tasks
        self._receive_task = asyncio.create_task(self._receive_loop())
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

        logger.info("BinanceWebSocketManager started")

    async def stop(self) -> None:
        """Stop the WebSocket manager"""
        self._running = False

        # Cancel tasks
        if self._receive_task:
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass

        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass

        # Close connection
        if self._ws:
            await self._ws.close()
            self._ws = None

        # Clear state
        self._subscribed_streams.clear()
        self._kline_callbacks.clear()
        self._ticker_callbacks.clear()

        logger.info("BinanceWebSocketManager stopped")

    async def _connect(self) -> None:
        """Establish WebSocket connection"""
        try:
            # Build URL with streams
            if self._subscribed_streams:
                streams = "/".join(self._subscribed_streams)
                url = f"{self.base_url}?streams={streams}"
            else:
                # Connect without streams initially
                url = self.base_url

            logger.info(f"Connecting to WebSocket: {url[:80]}...")

            self._ws = await websockets.connect(
                url,
                ping_interval=20,
                ping_timeout=20,
                close_timeout=10
            )

            self._reconnect_attempts = 0
            logger.info("WebSocket connected successfully")

        except Exception as e:
            logger.error(f"Failed to connect to WebSocket: {e}")
            await self._handle_reconnect()

    async def _handle_reconnect(self) -> None:
        """Handle reconnection after connection loss"""
        if not self._running:
            return

        self._reconnect_attempts += 1

        if self._reconnect_attempts > self._max_reconnect_attempts:
            logger.error("Max reconnection attempts reached, giving up")
            self._running = False
            return

        delay = min(self._reconnect_delay * self._reconnect_attempts, 60)
        logger.warning(
            f"Reconnecting in {delay}s (attempt {self._reconnect_attempts}/{self._max_reconnect_attempts})"
        )

        await asyncio.sleep(delay)
        await self._connect()

        # Resubscribe to all streams
        if self._ws and self._subscribed_streams:
            await self._send_subscribe(list(self._subscribed_streams))

    async def _receive_loop(self) -> None:
        """Background task to receive and process messages"""
        while self._running:
            try:
                if not self._ws:
                    await asyncio.sleep(1)
                    continue

                message = await self._ws.recv()
                await self._process_message(message)

            except ConnectionClosed:
                logger.warning("WebSocket connection closed")
                if self._running:
                    await self._handle_reconnect()

            except Exception as e:
                logger.error(f"Error in receive loop: {e}")
                await asyncio.sleep(1)

    async def _heartbeat_loop(self) -> None:
        """Background task for connection health monitoring"""
        while self._running:
            try:
                await asyncio.sleep(30)

                if self._ws and self._ws.open:
                    # Send ping
                    await self._ws.ping()
                else:
                    logger.warning("WebSocket not connected, triggering reconnect")
                    await self._handle_reconnect()

            except Exception as e:
                logger.error(f"Heartbeat error: {e}")

    async def _process_message(self, raw_message: str) -> None:
        """Process incoming WebSocket message"""
        try:
            data = json.loads(raw_message)

            # Combined stream format: {"stream": "...", "data": {...}}
            if "stream" in data:
                stream_name = data.get("stream", "")
                payload = data.get("data", {})
            else:
                # Single stream format
                stream_name = ""
                payload = data

            # Route by event type
            event_type = payload.get("e", "")

            if event_type == "kline":
                await self._handle_kline(stream_name, payload)
            elif event_type == "24hrTicker":
                await self._handle_ticker(stream_name, payload)

        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON received: {raw_message[:100]}")
        except Exception as e:
            logger.error(f"Error processing message: {e}")

    async def _handle_kline(self, stream_name: str, data: Dict[str, Any]) -> None:
        """Handle kline/candlestick message"""
        try:
            kline = KlineData.from_ws_message(data)

            # Get callbacks for this stream
            callbacks = self._kline_callbacks.get(stream_name, [])

            for callback in callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(kline)
                    else:
                        callback(kline)
                except Exception as e:
                    logger.error(f"Kline callback error: {e}")

        except Exception as e:
            logger.error(f"Error handling kline: {e}")

    async def _handle_ticker(self, stream_name: str, data: Dict[str, Any]) -> None:
        """Handle 24hr ticker message"""
        try:
            ticker = TickerData.from_ws_message(data)

            callbacks = self._ticker_callbacks.get(stream_name, [])

            for callback in callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(ticker)
                    else:
                        callback(ticker)
                except Exception as e:
                    logger.error(f"Ticker callback error: {e}")

        except Exception as e:
            logger.error(f"Error handling ticker: {e}")

    async def _send_subscribe(self, streams: List[str]) -> None:
        """Send subscription message to WebSocket"""
        if not self._ws:
            logger.warning("Cannot subscribe - WebSocket not connected")
            return

        try:
            subscribe_msg = {
                "method": "SUBSCRIBE",
                "params": streams,
                "id": int(datetime.now().timestamp())
            }

            await self._ws.send(json.dumps(subscribe_msg))
            logger.info(f"Subscribed to streams: {streams}")

        except Exception as e:
            logger.error(f"Error subscribing to streams: {e}")

    async def _send_unsubscribe(self, streams: List[str]) -> None:
        """Send unsubscribe message to WebSocket"""
        if not self._ws:
            return

        try:
            unsubscribe_msg = {
                "method": "UNSUBSCRIBE",
                "params": streams,
                "id": int(datetime.now().timestamp())
            }

            await self._ws.send(json.dumps(unsubscribe_msg))
            logger.info(f"Unsubscribed from streams: {streams}")

        except Exception as e:
            logger.error(f"Error unsubscribing from streams: {e}")

    async def subscribe_kline(
        self,
        symbol: str,
        interval: str,
        callback: KlineCallback
    ) -> str:
        """
        Subscribe to kline/candlestick stream

        Args:
            symbol: Trading symbol (e.g., "BTCUSDT")
            interval: Timeframe (1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d, 3d, 1w)
            callback: Function to call with each kline update

        Returns:
            Stream ID for unsubscribing
        """
        stream_name = f"{symbol.lower()}@kline_{interval}"

        # Add callback
        if stream_name not in self._kline_callbacks:
            self._kline_callbacks[stream_name] = []
        self._kline_callbacks[stream_name].append(callback)

        # Subscribe if not already
        if stream_name not in self._subscribed_streams:
            self._subscribed_streams.add(stream_name)
            if self._ws:
                await self._send_subscribe([stream_name])

        logger.info(f"Subscribed to kline stream: {stream_name}")
        return stream_name

    async def subscribe_ticker(
        self,
        symbol: str,
        callback: TickerCallback
    ) -> str:
        """
        Subscribe to 24hr ticker stream

        Args:
            symbol: Trading symbol (e.g., "BTCUSDT")
            callback: Function to call with each ticker update

        Returns:
            Stream ID for unsubscribing
        """
        stream_name = f"{symbol.lower()}@ticker"

        if stream_name not in self._ticker_callbacks:
            self._ticker_callbacks[stream_name] = []
        self._ticker_callbacks[stream_name].append(callback)

        if stream_name not in self._subscribed_streams:
            self._subscribed_streams.add(stream_name)
            if self._ws:
                await self._send_subscribe([stream_name])

        logger.info(f"Subscribed to ticker stream: {stream_name}")
        return stream_name

    async def unsubscribe(self, stream_name: str) -> None:
        """
        Unsubscribe from a stream

        Args:
            stream_name: Stream ID returned from subscribe methods
        """
        if stream_name in self._subscribed_streams:
            self._subscribed_streams.remove(stream_name)
            await self._send_unsubscribe([stream_name])

        # Remove callbacks
        self._kline_callbacks.pop(stream_name, None)
        self._ticker_callbacks.pop(stream_name, None)

        logger.info(f"Unsubscribed from stream: {stream_name}")

    def get_subscribed_streams(self) -> List[str]:
        """Get list of currently subscribed streams"""
        return list(self._subscribed_streams)

    def is_connected(self) -> bool:
        """Check if WebSocket is connected"""
        return self._ws is not None and self._ws.open

    @property
    def running(self) -> bool:
        """Check if manager is running"""
        return self._running


# Singleton instance
_ws_manager: Optional[BinanceWebSocketManager] = None


def get_binance_ws_manager(use_futures: bool = True) -> BinanceWebSocketManager:
    """Get or create singleton WebSocket manager instance"""
    global _ws_manager

    if _ws_manager is None:
        _ws_manager = BinanceWebSocketManager(use_futures=use_futures)

    return _ws_manager


async def start_ws_manager() -> BinanceWebSocketManager:
    """Start and return the WebSocket manager"""
    manager = get_binance_ws_manager()
    await manager.start()
    return manager

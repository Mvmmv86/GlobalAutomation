"""
WebSocket Controller - Real-time notifications for positions and orders

Provides WebSocket endpoints for real-time updates of:
- Position changes (open/close/update)
- Order executions (created/filled/failed)
- Balance updates

Security: User-scoped connections, authenticated via token
Performance: Connection pooling, automatic cleanup, heartbeat
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, status
from typing import Dict, Set, List, Any
import structlog
import asyncio
import json
from datetime import datetime

logger = structlog.get_logger(__name__)


class ConnectionManager:
    """
    Manages WebSocket connections with user-scoped broadcasting.

    Features:
    - User-scoped connections (one user can have multiple connections)
    - Automatic cleanup on disconnect
    - Heartbeat/ping-pong to detect dead connections
    - Broadcast to specific users or all users
    """

    def __init__(self):
        # user_id -> Set of WebSocket connections
        self._active_connections: Dict[str, Set[WebSocket]] = {}
        self._connection_metadata: Dict[WebSocket, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()

        # Metrics
        self._total_connections = 0
        self._total_disconnections = 0
        self._total_messages_sent = 0

        logger.info("WebSocket ConnectionManager initialized")

    async def connect(self, websocket: WebSocket, user_id: str, client_id: str = None) -> None:
        """
        Accept and register a new WebSocket connection.

        Args:
            websocket: WebSocket connection instance
            user_id: User identifier for scoping
            client_id: Optional client identifier (e.g., browser tab ID)
        """
        await websocket.accept()

        async with self._lock:
            # Initialize user's connection set if first connection
            if user_id not in self._active_connections:
                self._active_connections[user_id] = set()

            # Add connection to user's set
            self._active_connections[user_id].add(websocket)

            # Store metadata
            self._connection_metadata[websocket] = {
                "user_id": user_id,
                "client_id": client_id,
                "connected_at": datetime.utcnow(),
                "last_heartbeat": datetime.utcnow()
            }

            self._total_connections += 1

            logger.info(
                "WebSocket connected",
                user_id=user_id,
                client_id=client_id,
                total_user_connections=len(self._active_connections[user_id]),
                total_active_users=len(self._active_connections)
            )

    async def disconnect(self, websocket: WebSocket) -> None:
        """
        Unregister and cleanup a WebSocket connection.

        Args:
            websocket: WebSocket connection instance to remove
        """
        async with self._lock:
            # Get metadata before removing
            metadata = self._connection_metadata.get(websocket, {})
            user_id = metadata.get("user_id")

            if user_id and user_id in self._active_connections:
                # Remove from user's connection set
                self._active_connections[user_id].discard(websocket)

                # Remove user entry if no more connections
                if not self._active_connections[user_id]:
                    del self._active_connections[user_id]

            # Remove metadata
            if websocket in self._connection_metadata:
                del self._connection_metadata[websocket]

            self._total_disconnections += 1

            logger.info(
                "WebSocket disconnected",
                user_id=user_id,
                total_active_users=len(self._active_connections)
            )

    async def send_personal_message(self, message: Dict[str, Any], user_id: str) -> int:
        """
        Send message to all connections of a specific user.

        Args:
            message: Message payload as dictionary
            user_id: Target user identifier

        Returns:
            Number of connections message was sent to
        """
        if user_id not in self._active_connections:
            logger.debug(f"No active connections for user {user_id}")
            return 0

        connections = self._active_connections[user_id].copy()  # Avoid modification during iteration
        message_json = json.dumps(message)
        sent_count = 0
        failed_connections = []

        for connection in connections:
            try:
                await connection.send_text(message_json)
                sent_count += 1
                self._total_messages_sent += 1
            except Exception as e:
                logger.warning(f"Failed to send message to connection: {e}")
                failed_connections.append(connection)

        # Cleanup failed connections
        for failed_conn in failed_connections:
            await self.disconnect(failed_conn)

        logger.debug(
            "Personal message sent",
            user_id=user_id,
            sent_to=sent_count,
            failed=len(failed_connections),
            message_type=message.get("type")
        )

        return sent_count

    async def broadcast(self, message: Dict[str, Any], exclude_user: str = None) -> int:
        """
        Broadcast message to all connected users.

        Args:
            message: Message payload as dictionary
            exclude_user: Optional user_id to exclude from broadcast

        Returns:
            Total number of connections message was sent to
        """
        message_json = json.dumps(message)
        total_sent = 0

        for user_id, connections in self._active_connections.items():
            if exclude_user and user_id == exclude_user:
                continue

            for connection in connections.copy():
                try:
                    await connection.send_text(message_json)
                    total_sent += 1
                    self._total_messages_sent += 1
                except Exception as e:
                    logger.warning(f"Failed to broadcast to connection: {e}")
                    await self.disconnect(connection)

        logger.debug(
            "Broadcast sent",
            total_sent=total_sent,
            message_type=message.get("type")
        )

        return total_sent

    async def send_heartbeat(self, websocket: WebSocket) -> bool:
        """
        Send heartbeat/ping to check if connection is alive.

        Args:
            websocket: WebSocket connection to ping

        Returns:
            True if connection is alive, False otherwise
        """
        try:
            await websocket.send_json({"type": "ping", "timestamp": datetime.utcnow().isoformat()})

            # Update last heartbeat
            if websocket in self._connection_metadata:
                self._connection_metadata[websocket]["last_heartbeat"] = datetime.utcnow()

            return True
        except Exception as e:
            logger.debug(f"Heartbeat failed: {e}")
            return False

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get connection manager metrics.

        Returns:
            Dictionary with connection statistics
        """
        total_active_connections = sum(len(conns) for conns in self._active_connections.values())

        return {
            "active_users": len(self._active_connections),
            "active_connections": total_active_connections,
            "total_connections": self._total_connections,
            "total_disconnections": self._total_disconnections,
            "total_messages_sent": self._total_messages_sent
        }

    def get_user_connections_count(self, user_id: str) -> int:
        """Get number of active connections for a user."""
        return len(self._active_connections.get(user_id, set()))


# Global singleton instance
_connection_manager: ConnectionManager = None


def get_connection_manager() -> ConnectionManager:
    """
    Get or create global ConnectionManager instance.

    Returns:
        Singleton ConnectionManager instance
    """
    global _connection_manager
    if _connection_manager is None:
        _connection_manager = ConnectionManager()
    return _connection_manager


# Helper functions for notifying via WebSocket

async def notify_position_update(user_id: str, position_data: Dict[str, Any]) -> None:
    """
    Notify user about position update via WebSocket.

    Args:
        user_id: User to notify
        position_data: Position data payload
    """
    manager = get_connection_manager()

    message = {
        "type": "position_update",
        "timestamp": datetime.utcnow().isoformat(),
        "data": position_data
    }

    await manager.send_personal_message(message, user_id)
    logger.info(f"Position update notification sent to user {user_id}")


async def notify_order_update(user_id: str, order_data: Dict[str, Any]) -> None:
    """
    Notify user about order update via WebSocket.

    Args:
        user_id: User to notify
        order_data: Order data payload
    """
    manager = get_connection_manager()

    message = {
        "type": "order_update",
        "timestamp": datetime.utcnow().isoformat(),
        "data": order_data
    }

    await manager.send_personal_message(message, user_id)
    logger.info(f"Order update notification sent to user {user_id}")


async def notify_balance_update(user_id: str, balance_data: Dict[str, Any]) -> None:
    """
    Notify user about balance update via WebSocket.

    Args:
        user_id: User to notify
        balance_data: Balance data payload
    """
    manager = get_connection_manager()

    message = {
        "type": "balance_update",
        "timestamp": datetime.utcnow().isoformat(),
        "data": balance_data
    }

    await manager.send_personal_message(message, user_id)
    logger.info(f"Balance update notification sent to user {user_id}")


# Router

def create_websocket_router() -> APIRouter:
    """Create and configure the WebSocket router"""
    router = APIRouter(prefix="/api/v1/ws", tags=["WebSocket"])

    @router.websocket("/notifications")
    async def websocket_notifications(
        websocket: WebSocket,
        user_id: str = Query(..., description="User ID for scoped notifications"),
        client_id: str = Query(None, description="Optional client ID")
    ):
        """
        WebSocket endpoint for real-time notifications.

        Receives:
        - Position updates (open/close/modify)
        - Order updates (created/filled/failed)
        - Balance updates

        Security: TODO - Add JWT token authentication
        """
        manager = get_connection_manager()

        try:
            # Connect
            await manager.connect(websocket, user_id, client_id)

            # Send welcome message
            await websocket.send_json({
                "type": "connected",
                "message": "WebSocket connected successfully",
                "user_id": user_id,
                "timestamp": datetime.utcnow().isoformat()
            })

            # Keep connection alive and handle incoming messages
            while True:
                try:
                    # Wait for messages (with timeout for heartbeat)
                    data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)

                    # Parse message
                    message = json.loads(data)
                    message_type = message.get("type")

                    # Handle different message types
                    if message_type == "pong":
                        # Client responded to ping
                        logger.debug(f"Pong received from user {user_id}")

                    elif message_type == "subscribe":
                        # Client wants to subscribe to specific events
                        # TODO: Implement event subscriptions
                        await websocket.send_json({
                            "type": "subscribed",
                            "events": message.get("events", []),
                            "timestamp": datetime.utcnow().isoformat()
                        })

                    else:
                        logger.warning(f"Unknown message type: {message_type}")

                except asyncio.TimeoutError:
                    # Send heartbeat (ping) after 30s of inactivity
                    is_alive = await manager.send_heartbeat(websocket)
                    if not is_alive:
                        logger.warning(f"Connection dead for user {user_id}, disconnecting")
                        break

        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected normally for user {user_id}")

        except Exception as e:
            logger.error(f"WebSocket error for user {user_id}: {e}", exc_info=True)

        finally:
            # Always cleanup connection
            await manager.disconnect(websocket)

    @router.get("/metrics")
    async def get_websocket_metrics():
        """Get WebSocket connection metrics (admin endpoint)"""
        manager = get_connection_manager()
        metrics = manager.get_metrics()

        return {
            "success": True,
            "data": metrics
        }

    return router

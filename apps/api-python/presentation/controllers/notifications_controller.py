"""Notifications Controller - API endpoints for managing user notifications"""

from fastapi import APIRouter, HTTPException, Request, Query
from typing import List, Optional
import structlog
from datetime import datetime
import jwt
import uuid as uuid_module
from pydantic import BaseModel

import os
from infrastructure.database.connection_transaction_mode import transaction_db

logger = structlog.get_logger(__name__)

# JWT Secret Key from environment variable
JWT_SECRET_KEY = os.getenv("SECRET_KEY", "trading_platform_secret_key_2024")


# =====================================================
# REQUEST/RESPONSE MODELS
# =====================================================

class NotificationCreate(BaseModel):
    """Request model for creating a notification"""
    type: str = "info"  # success, warning, error, info
    category: str = "system"  # order, position, system, market, bot, price_alert
    title: str
    message: str
    action_url: Optional[str] = None
    metadata: Optional[dict] = None


class NotificationUpdate(BaseModel):
    """Request model for updating a notification"""
    read: Optional[bool] = None


# =====================================================
# HELPER FUNCTIONS
# =====================================================

def get_user_id_from_request(request: Request) -> Optional[str]:
    """Extract user_id from JWT token in Authorization header"""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None

    token = auth_header.split(" ")[1]
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=["HS256"])
        return payload.get("user_id")
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None


def get_user_uuid_from_request(request: Request) -> Optional[uuid_module.UUID]:
    """Extract user_id from JWT and convert to UUID"""
    user_id = get_user_id_from_request(request)
    if not user_id:
        return None
    try:
        return uuid_module.UUID(user_id) if isinstance(user_id, str) else user_id
    except ValueError:
        return None


# =====================================================
# ROUTER FACTORY
# =====================================================

def create_notifications_router() -> APIRouter:
    """Create and configure the notifications router"""
    router = APIRouter(prefix="/api/v1/notifications", tags=["Notifications"])

    # =====================================================
    # GET /notifications - List all notifications for user
    # =====================================================
    @router.get("")
    async def get_notifications(
        request: Request,
        category: Optional[str] = Query(None, description="Filter by category"),
        unread_only: bool = Query(False, description="Show only unread notifications"),
        limit: int = Query(50, description="Maximum number of notifications to return"),
        offset: int = Query(0, description="Number of notifications to skip")
    ):
        """Get all notifications for the authenticated user"""
        try:
            user_uuid = get_user_uuid_from_request(request)

            if not user_uuid:
                return {"success": True, "data": [], "total": 0, "unread_count": 0}

            # Build query with filters
            query_conditions = ["user_id = $1"]
            params = [user_uuid]
            param_count = 2

            if category:
                query_conditions.append(f"category = ${param_count}")
                params.append(category)
                param_count += 1

            if unread_only:
                query_conditions.append("read = false")

            where_clause = " AND ".join(query_conditions)

            # Get notifications with pagination
            notifications = await transaction_db.fetch(f"""
                SELECT
                    id, type, category, title, message, read,
                    action_url, metadata, created_at, updated_at
                FROM notifications
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT ${param_count} OFFSET ${param_count + 1}
            """, *params, limit, offset)

            # Get total count
            total_result = await transaction_db.fetchrow(f"""
                SELECT COUNT(*) as total
                FROM notifications
                WHERE {where_clause}
            """, *params)

            # Get unread count
            unread_result = await transaction_db.fetchrow("""
                SELECT COUNT(*) as unread
                FROM notifications
                WHERE user_id = $1 AND read = false
            """, user_uuid)

            notifications_list = []
            for n in notifications:
                notifications_list.append({
                    "id": str(n["id"]),
                    "type": n["type"],
                    "category": n["category"],
                    "title": n["title"],
                    "message": n["message"],
                    "read": n["read"],
                    "actionUrl": n["action_url"],
                    "metadata": n["metadata"],
                    "timestamp": n["created_at"].isoformat() if n["created_at"] else None,
                    "createdAt": n["created_at"].isoformat() if n["created_at"] else None,
                    "updatedAt": n["updated_at"].isoformat() if n["updated_at"] else None
                })

            logger.info("Notifications retrieved",
                       user_id=str(user_uuid),
                       count=len(notifications_list),
                       unread=unread_result["unread"])

            return {
                "success": True,
                "data": notifications_list,
                "total": total_result["total"],
                "unread_count": unread_result["unread"]
            }

        except Exception as e:
            logger.error("Error retrieving notifications", error=str(e), exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to retrieve notifications")

    # =====================================================
    # GET /notifications/count - Get unread count
    # =====================================================
    @router.get("/count")
    async def get_notifications_count(request: Request):
        """Get count of unread notifications"""
        try:
            user_uuid = get_user_uuid_from_request(request)

            if not user_uuid:
                return {"success": True, "unread_count": 0, "total_count": 0}

            counts = await transaction_db.fetchrow("""
                SELECT
                    COUNT(*) as total,
                    COUNT(CASE WHEN read = false THEN 1 END) as unread
                FROM notifications
                WHERE user_id = $1
            """, user_uuid)

            return {
                "success": True,
                "unread_count": counts["unread"],
                "total_count": counts["total"]
            }

        except Exception as e:
            logger.error("Error getting notification count", error=str(e), exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to get notification count")

    # =====================================================
    # POST /notifications - Create a notification (internal use)
    # =====================================================
    @router.post("")
    async def create_notification(request: Request, notification: NotificationCreate):
        """Create a new notification for the authenticated user"""
        try:
            user_uuid = get_user_uuid_from_request(request)

            if not user_uuid:
                raise HTTPException(status_code=401, detail="Authentication required")

            # Validate type and category
            valid_types = ["success", "warning", "error", "info"]
            valid_categories = ["order", "position", "system", "market", "bot", "price_alert"]

            if notification.type not in valid_types:
                notification.type = "info"

            if notification.category not in valid_categories:
                notification.category = "system"

            # Insert notification
            notification_id = await transaction_db.fetchval("""
                INSERT INTO notifications (
                    type, category, title, message, action_url, metadata, user_id, created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, NOW(), NOW())
                RETURNING id
            """, notification.type, notification.category, notification.title,
               notification.message, notification.action_url,
               notification.metadata, user_uuid)

            logger.info("Notification created",
                       notification_id=str(notification_id),
                       user_id=str(user_uuid),
                       category=notification.category)

            return {
                "success": True,
                "message": "Notification created successfully",
                "data": {
                    "id": str(notification_id),
                    "type": notification.type,
                    "category": notification.category,
                    "title": notification.title,
                    "message": notification.message
                }
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error("Error creating notification", error=str(e), exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to create notification")

    # =====================================================
    # PUT /notifications/{id} - Update notification (mark as read)
    # =====================================================
    @router.put("/{notification_id}")
    async def update_notification(notification_id: str, request: Request):
        """Update a notification (typically mark as read)"""
        try:
            user_uuid = get_user_uuid_from_request(request)

            if not user_uuid:
                raise HTTPException(status_code=401, detail="Authentication required")

            body = await request.json()
            read = body.get("read")

            if read is None:
                raise HTTPException(status_code=400, detail="No valid fields to update")

            # Update notification (only if belongs to user)
            result = await transaction_db.execute("""
                UPDATE notifications
                SET read = $1, updated_at = NOW()
                WHERE id = $2 AND user_id = $3
            """, read, notification_id, user_uuid)

            logger.info("Notification updated", notification_id=notification_id, read=read)

            return {"success": True, "message": "Notification updated successfully"}

        except HTTPException:
            raise
        except Exception as e:
            logger.error("Error updating notification", notification_id=notification_id, error=str(e), exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to update notification")

    # =====================================================
    # PUT /notifications/mark-all-read - Mark all as read
    # =====================================================
    @router.put("/mark-all-read")
    async def mark_all_as_read(request: Request):
        """Mark all notifications as read for the authenticated user"""
        try:
            user_uuid = get_user_uuid_from_request(request)

            if not user_uuid:
                raise HTTPException(status_code=401, detail="Authentication required")

            result = await transaction_db.execute("""
                UPDATE notifications
                SET read = true, updated_at = NOW()
                WHERE user_id = $1 AND read = false
            """, user_uuid)

            logger.info("All notifications marked as read", user_id=str(user_uuid))

            return {"success": True, "message": "All notifications marked as read"}

        except HTTPException:
            raise
        except Exception as e:
            logger.error("Error marking all notifications as read", error=str(e), exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to mark all notifications as read")

    # =====================================================
    # DELETE /notifications/{id} - Delete notification
    # =====================================================
    @router.delete("/{notification_id}")
    async def delete_notification(notification_id: str, request: Request):
        """Delete a notification"""
        try:
            user_uuid = get_user_uuid_from_request(request)

            if not user_uuid:
                raise HTTPException(status_code=401, detail="Authentication required")

            # Delete only if belongs to user
            result = await transaction_db.execute("""
                DELETE FROM notifications
                WHERE id = $1 AND user_id = $2
            """, notification_id, user_uuid)

            logger.info("Notification deleted", notification_id=notification_id)

            return {"success": True, "message": "Notification deleted successfully"}

        except HTTPException:
            raise
        except Exception as e:
            logger.error("Error deleting notification", notification_id=notification_id, error=str(e), exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to delete notification")

    # =====================================================
    # DELETE /notifications - Clear all notifications
    # =====================================================
    @router.delete("")
    async def clear_all_notifications(request: Request):
        """Clear all notifications for the authenticated user"""
        try:
            user_uuid = get_user_uuid_from_request(request)

            if not user_uuid:
                raise HTTPException(status_code=401, detail="Authentication required")

            result = await transaction_db.execute("""
                DELETE FROM notifications
                WHERE user_id = $1
            """, user_uuid)

            logger.info("All notifications cleared", user_id=str(user_uuid))

            return {"success": True, "message": "All notifications cleared"}

        except HTTPException:
            raise
        except Exception as e:
            logger.error("Error clearing all notifications", error=str(e), exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to clear notifications")

    return router


# =====================================================
# NOTIFICATION SERVICE - For creating system notifications
# =====================================================

class NotificationService:
    """Service for creating notifications from system events"""

    @staticmethod
    async def create_notification(
        user_id: uuid_module.UUID,
        notification_type: str,
        category: str,
        title: str,
        message: str,
        action_url: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> Optional[str]:
        """Create a notification for a user (called by system/bots)"""
        try:
            notification_id = await transaction_db.fetchval("""
                INSERT INTO notifications (
                    type, category, title, message, action_url, metadata, user_id, created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, NOW(), NOW())
                RETURNING id
            """, notification_type, category, title, message, action_url, metadata, user_id)

            logger.info("System notification created",
                       notification_id=str(notification_id),
                       user_id=str(user_id),
                       category=category,
                       title=title)

            return str(notification_id)

        except Exception as e:
            logger.error("Failed to create system notification", error=str(e), exc_info=True)
            return None

    @staticmethod
    async def notify_order_executed(
        user_id: uuid_module.UUID,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        order_id: str
    ):
        """Notify user about an order execution"""
        return await NotificationService.create_notification(
            user_id=user_id,
            notification_type="success",
            category="order",
            title=f"Order Executed: {symbol}",
            message=f"{side.upper()} {quantity} {symbol} at ${price:.2f}",
            action_url=f"/orders/{order_id}",
            metadata={
                "order_id": order_id,
                "symbol": symbol,
                "side": side,
                "quantity": quantity,
                "price": price
            }
        )

    @staticmethod
    async def notify_order_failed(
        user_id: uuid_module.UUID,
        symbol: str,
        side: str,
        error_message: str,
        order_id: str
    ):
        """Notify user about a failed order"""
        return await NotificationService.create_notification(
            user_id=user_id,
            notification_type="error",
            category="order",
            title=f"Order Failed: {symbol}",
            message=f"{side.upper()} order failed: {error_message}",
            action_url=f"/orders/{order_id}",
            metadata={
                "order_id": order_id,
                "symbol": symbol,
                "side": side,
                "error": error_message
            }
        )

    @staticmethod
    async def notify_position_opened(
        user_id: uuid_module.UUID,
        symbol: str,
        side: str,
        size: float,
        entry_price: float,
        position_id: str
    ):
        """Notify user about a new position"""
        return await NotificationService.create_notification(
            user_id=user_id,
            notification_type="info",
            category="position",
            title=f"Position Opened: {symbol}",
            message=f"{side.upper()} {size} {symbol} at ${entry_price:.2f}",
            action_url=f"/positions/{position_id}",
            metadata={
                "position_id": position_id,
                "symbol": symbol,
                "side": side,
                "size": size,
                "entry_price": entry_price
            }
        )

    @staticmethod
    async def notify_position_closed(
        user_id: uuid_module.UUID,
        symbol: str,
        pnl: float,
        position_id: str
    ):
        """Notify user about a closed position"""
        pnl_type = "success" if pnl >= 0 else "warning"
        pnl_emoji = "+" if pnl >= 0 else ""

        return await NotificationService.create_notification(
            user_id=user_id,
            notification_type=pnl_type,
            category="position",
            title=f"Position Closed: {symbol}",
            message=f"P&L: {pnl_emoji}${pnl:.2f}",
            action_url=f"/positions/{position_id}",
            metadata={
                "position_id": position_id,
                "symbol": symbol,
                "pnl": pnl
            }
        )

    @staticmethod
    async def notify_price_alert(
        user_id: uuid_module.UUID,
        symbol: str,
        current_price: float,
        alert_price: float,
        alert_type: str  # "above" or "below"
    ):
        """Notify user about a price alert"""
        return await NotificationService.create_notification(
            user_id=user_id,
            notification_type="info",
            category="price_alert",
            title=f"Price Alert: {symbol}",
            message=f"{symbol} is now {alert_type} ${alert_price:.2f} (Current: ${current_price:.2f})",
            action_url=f"/trading?symbol={symbol}",
            metadata={
                "symbol": symbol,
                "current_price": current_price,
                "alert_price": alert_price,
                "alert_type": alert_type
            }
        )

    @staticmethod
    async def notify_bot_action(
        user_id: uuid_module.UUID,
        bot_name: str,
        action: str,
        details: str,
        bot_id: str
    ):
        """Notify user about bot activity"""
        return await NotificationService.create_notification(
            user_id=user_id,
            notification_type="info",
            category="bot",
            title=f"Bot: {bot_name}",
            message=f"{action}: {details}",
            action_url=f"/bots/{bot_id}",
            metadata={
                "bot_id": bot_id,
                "bot_name": bot_name,
                "action": action,
                "details": details
            }
        )

    @staticmethod
    async def notify_system_event(
        user_id: uuid_module.UUID,
        title: str,
        message: str,
        notification_type: str = "info"
    ):
        """Notify user about a system event"""
        return await NotificationService.create_notification(
            user_id=user_id,
            notification_type=notification_type,
            category="system",
            title=title,
            message=message
        )


# Export the service for use in other modules
notification_service = NotificationService()

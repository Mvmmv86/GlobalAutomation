"""Webhooks CRUD Controller - API endpoints for managing webhooks"""

from fastapi import APIRouter, HTTPException, Request
from typing import List, Optional
import structlog
from datetime import datetime
import uuid

from infrastructure.database.connection_transaction_mode import transaction_db

logger = structlog.get_logger(__name__)

def create_webhooks_crud_router() -> APIRouter:
    """Create and configure the webhooks CRUD router"""
    router = APIRouter(prefix="/api/v1/webhooks", tags=["Webhooks CRUD"])

    @router.get("")
    async def get_webhooks(request: Request, status: Optional[str] = None):
        """Get all webhooks with optional status filtering"""
        try:
            # Build query with optional filters
            where_conditions = []
            params = []
            param_count = 1
            
            if status:
                where_conditions.append(f"status = ${param_count}")
                params.append(status)
                param_count += 1
            
            where_clause = ""
            if where_conditions:
                where_clause = "WHERE " + " AND ".join(where_conditions)
            
            query = f"""
                SELECT 
                    id, name, url_path, status, is_public,
                    rate_limit_per_minute, rate_limit_per_hour,
                    max_retries, retry_delay_seconds,
                    total_deliveries, successful_deliveries, failed_deliveries,
                    last_delivery_at, last_success_at,
                    auto_pause_on_errors, error_threshold, consecutive_errors,
                    user_id, created_at, updated_at
                FROM webhooks
                {where_clause}
                ORDER BY created_at DESC
            """
            
            webhooks = await transaction_db.fetch(query, *params)
            
            webhooks_list = []
            for webhook in webhooks:
                webhooks_list.append({
                    "id": webhook["id"],
                    "name": webhook["name"],
                    "url_path": webhook["url_path"],
                    "status": webhook["status"],
                    "is_public": webhook["is_public"],
                    "rate_limit_per_minute": webhook["rate_limit_per_minute"],
                    "rate_limit_per_hour": webhook["rate_limit_per_hour"],
                    "max_retries": webhook["max_retries"],
                    "retry_delay_seconds": webhook["retry_delay_seconds"],
                    "total_deliveries": webhook["total_deliveries"],
                    "successful_deliveries": webhook["successful_deliveries"],
                    "failed_deliveries": webhook["failed_deliveries"],
                    "last_delivery_at": webhook["last_delivery_at"].isoformat() if webhook["last_delivery_at"] else None,
                    "last_success_at": webhook["last_success_at"].isoformat() if webhook["last_success_at"] else None,
                    "auto_pause_on_errors": webhook["auto_pause_on_errors"],
                    "error_threshold": webhook["error_threshold"],
                    "consecutive_errors": webhook["consecutive_errors"],
                    "user_id": webhook["user_id"],
                    "created_at": webhook["created_at"].isoformat() if webhook["created_at"] else None,
                    "updated_at": webhook["updated_at"].isoformat() if webhook["updated_at"] else None,
                    # Calculate success rate
                    "success_rate": round(
                        (webhook["successful_deliveries"] / webhook["total_deliveries"] * 100) 
                        if webhook["total_deliveries"] > 0 else 0, 2
                    )
                })
            
            logger.info("Webhooks retrieved", count=len(webhooks_list), status=status)
            return {"success": True, "data": webhooks_list}
            
        except Exception as e:
            logger.error("Error retrieving webhooks", error=str(e), exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to retrieve webhooks")

    @router.get("/{webhook_id}")
    async def get_webhook(webhook_id: str, request: Request):
        """Get a specific webhook by ID"""
        try:
            webhook = await transaction_db.fetchrow("""
                SELECT 
                    id, name, url_path, secret, status, is_public,
                    rate_limit_per_minute, rate_limit_per_hour,
                    max_retries, retry_delay_seconds,
                    allowed_ips, required_headers, payload_validation_schema,
                    total_deliveries, successful_deliveries, failed_deliveries,
                    last_delivery_at, last_success_at,
                    auto_pause_on_errors, error_threshold, consecutive_errors,
                    user_id, created_at, updated_at
                FROM webhooks 
                WHERE id = $1
            """, webhook_id)
            
            if not webhook:
                raise HTTPException(status_code=404, detail="Webhook not found")
            
            webhook_data = {
                "id": webhook["id"],
                "name": webhook["name"],
                "url_path": webhook["url_path"],
                "status": webhook["status"],
                "is_public": webhook["is_public"],
                "rate_limit_per_minute": webhook["rate_limit_per_minute"],
                "rate_limit_per_hour": webhook["rate_limit_per_hour"],
                "max_retries": webhook["max_retries"],
                "retry_delay_seconds": webhook["retry_delay_seconds"],
                "allowed_ips": webhook["allowed_ips"],
                "required_headers": webhook["required_headers"],
                "payload_validation_schema": webhook["payload_validation_schema"],
                "total_deliveries": webhook["total_deliveries"],
                "successful_deliveries": webhook["successful_deliveries"],
                "failed_deliveries": webhook["failed_deliveries"],
                "last_delivery_at": webhook["last_delivery_at"].isoformat() if webhook["last_delivery_at"] else None,
                "last_success_at": webhook["last_success_at"].isoformat() if webhook["last_success_at"] else None,
                "auto_pause_on_errors": webhook["auto_pause_on_errors"],
                "error_threshold": webhook["error_threshold"],
                "consecutive_errors": webhook["consecutive_errors"],
                "user_id": webhook["user_id"],
                "created_at": webhook["created_at"].isoformat() if webhook["created_at"] else None,
                "updated_at": webhook["updated_at"].isoformat() if webhook["updated_at"] else None,
                "success_rate": round(
                    (webhook["successful_deliveries"] / webhook["total_deliveries"] * 100) 
                    if webhook["total_deliveries"] > 0 else 0, 2
                )
            }
            
            logger.info("Webhook retrieved", webhook_id=webhook_id)
            return {"success": True, "data": webhook_data}
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Error retrieving webhook", webhook_id=webhook_id, error=str(e), exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to retrieve webhook")

    @router.post("")
    async def create_webhook(request: Request):
        """Create a new webhook"""
        try:
            body = await request.json()
            
            # Validate required fields
            required_fields = ["name", "url_path"]
            for field in required_fields:
                if field not in body:
                    raise HTTPException(status_code=400, detail=f"Missing required field: {field}")
            
            name = body.get("name", "").strip()
            url_path = body.get("url_path", "").strip()
            secret = body.get("secret", str(uuid.uuid4()))  # Generate secret if not provided
            status = body.get("status", "active")
            is_public = body.get("is_public", False)
            rate_limit_per_minute = body.get("rate_limit_per_minute", 60)
            rate_limit_per_hour = body.get("rate_limit_per_hour", 1000)
            max_retries = body.get("max_retries", 3)
            retry_delay_seconds = body.get("retry_delay_seconds", 60)
            
            # Validate status
            if status not in ["active", "paused", "disabled", "error"]:
                raise HTTPException(status_code=400, detail="Invalid status. Use: active, paused, disabled, error")
            
            # Check if url_path already exists
            existing = await transaction_db.fetchrow(
                "SELECT id FROM webhooks WHERE url_path = $1", url_path
            )
            if existing:
                raise HTTPException(status_code=400, detail="URL path already exists")
            
            # TODO: Get user_id from JWT token
            # For now, use a default user (first user in database)
            user = await transaction_db.fetchrow("SELECT id FROM users LIMIT 1")
            if not user:
                raise HTTPException(status_code=400, detail="No users found. Please create a user first.")
            
            user_id = user["id"]
            
            # Create the webhook
            webhook_id = await transaction_db.fetchval("""
                INSERT INTO webhooks (
                    name, url_path, secret, status, is_public,
                    rate_limit_per_minute, rate_limit_per_hour,
                    max_retries, retry_delay_seconds,
                    auto_pause_on_errors, error_threshold,
                    user_id, created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, NOW(), NOW())
                RETURNING id
            """, name, url_path, secret, status, is_public, 
                rate_limit_per_minute, rate_limit_per_hour,
                max_retries, retry_delay_seconds, True, 10, user_id)
            
            logger.info("Webhook created", 
                       webhook_id=webhook_id, name=name, url_path=url_path, status=status)
            
            return {
                "success": True,
                "message": "Webhook created successfully",
                "data": {
                    "id": webhook_id,
                    "name": name,
                    "url_path": url_path,
                    "secret": secret,
                    "status": status,
                    "is_public": is_public
                }
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Error creating webhook", error=str(e), exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to create webhook")

    @router.put("/{webhook_id}")
    async def update_webhook(webhook_id: str, request: Request):
        """Update an existing webhook"""
        try:
            body = await request.json()
            
            # Check if webhook exists
            existing = await transaction_db.fetchrow(
                "SELECT id FROM webhooks WHERE id = $1", webhook_id
            )
            if not existing:
                raise HTTPException(status_code=404, detail="Webhook not found")
            
            # Build update query dynamically
            update_fields = []
            params = []
            param_count = 1
            
            updateable_fields = [
                "name", "status", "is_public", "rate_limit_per_minute", 
                "rate_limit_per_hour", "max_retries", "retry_delay_seconds",
                "auto_pause_on_errors", "error_threshold"
            ]
            
            for field in updateable_fields:
                if field in body:
                    update_fields.append(f"{field} = ${param_count}")
                    params.append(body[field])
                    param_count += 1
            
            if not update_fields:
                raise HTTPException(status_code=400, detail="No valid fields to update")
            
            # Add updated_at
            update_fields.append(f"updated_at = ${param_count}")
            params.append(datetime.utcnow())
            param_count += 1
            
            # Add webhook_id for WHERE clause
            params.append(webhook_id)
            
            query = f"""
                UPDATE webhooks 
                SET {', '.join(update_fields)}
                WHERE id = ${param_count}
            """
            
            await transaction_db.execute(query, *params)
            
            logger.info("Webhook updated", webhook_id=webhook_id)
            return {"success": True, "message": "Webhook updated successfully"}
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Error updating webhook", webhook_id=webhook_id, error=str(e), exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to update webhook")

    @router.delete("/{webhook_id}")
    async def delete_webhook(webhook_id: str, request: Request):
        """Delete a webhook"""
        try:
            # Check if webhook exists
            existing = await transaction_db.fetchrow(
                "SELECT id FROM webhooks WHERE id = $1", webhook_id
            )
            if not existing:
                raise HTTPException(status_code=404, detail="Webhook not found")
            
            # Delete the webhook (cascade will handle deliveries)
            await transaction_db.execute(
                "DELETE FROM webhooks WHERE id = $1", webhook_id
            )
            
            logger.info("Webhook deleted", webhook_id=webhook_id)
            return {"success": True, "message": "Webhook deleted successfully"}
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Error deleting webhook", webhook_id=webhook_id, error=str(e), exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to delete webhook")

    return router
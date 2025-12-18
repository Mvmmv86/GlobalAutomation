"""Exchange Account Controller - API endpoints for managing exchange accounts"""

from fastapi import APIRouter, HTTPException, Depends, Request
from typing import List, Optional
import structlog
from datetime import datetime
import jwt
import uuid as uuid_module

from infrastructure.database.connection_transaction_mode import transaction_db
import os

logger = structlog.get_logger(__name__)

# JWT Secret Key from environment
JWT_SECRET_KEY = os.getenv("SECRET_KEY", "trading_platform_secret_key_2024")


def get_user_id_from_request(request: Request) -> Optional[str]:
    """Extract user_id from JWT token in Authorization header"""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None

    token = auth_header.split(" ")[1]
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=["HS256"])
        # JWT uses "sub" as standard field for subject (user_id)
        return payload.get("sub") or payload.get("user_id")
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

def create_exchange_account_router() -> APIRouter:
    """Create and configure the exchange account router"""
    router = APIRouter(prefix="/api/v1/exchange-accounts", tags=["Exchange Accounts"])

    @router.get("")
    async def get_exchange_accounts(request: Request):
        """Get all exchange accounts for the authenticated user"""
        try:
            # Extract user_id from JWT token
            user_uuid = get_user_uuid_from_request(request)

            # If no user authenticated, return empty list
            if not user_uuid:
                return {"success": True, "data": []}

            # Get accounts FILTERED BY USER_ID
            accounts = await transaction_db.fetch("""
                SELECT
                    id, name, exchange, testnet, is_active, is_main,
                    created_at, updated_at, user_id
                FROM exchange_accounts
                WHERE testnet = false AND is_active = true AND user_id = $1
                ORDER BY created_at DESC
            """, user_uuid)
            
            accounts_list = []
            for account in accounts:
                accounts_list.append({
                    "id": account["id"],
                    "name": account["name"],
                    "exchange": account["exchange"],
                    "environment": "testnet" if account["testnet"] else "mainnet",
                    "is_active": account["is_active"],
                    "is_main": account.get("is_main", False),
                    "created_at": account["created_at"].isoformat() if account["created_at"] else None,
                    "updated_at": account["updated_at"].isoformat() if account["updated_at"] else None,
                    "user_id": account["user_id"]
                })
            
            logger.info("Exchange accounts retrieved", count=len(accounts_list))
            return {"success": True, "data": accounts_list}
            
        except Exception as e:
            logger.error("Error retrieving exchange accounts", error=str(e), exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to retrieve exchange accounts")

    @router.get("/{account_id}")
    async def get_exchange_account(account_id: str, request: Request):
        """Get a specific exchange account by ID - filtered by user"""
        try:
            # Extract user_id from JWT token
            user_uuid = get_user_uuid_from_request(request)

            # If no user authenticated, return 401
            if not user_uuid:
                raise HTTPException(status_code=401, detail="Authentication required")

            # Get account FILTERED BY USER_ID
            account = await transaction_db.fetchrow("""
                SELECT
                    id, name, exchange, testnet, is_active, is_main,
                    created_at, updated_at, user_id
                FROM exchange_accounts
                WHERE id = $1 AND user_id = $2
            """, account_id, user_uuid)
            
            if not account:
                raise HTTPException(status_code=404, detail="Exchange account not found")
            
            account_data = {
                "id": account["id"],
                "name": account["name"],
                "exchange": account["exchange"],
                "environment": "testnet" if account["testnet"] else "mainnet",
                "is_active": account["is_active"],
                "is_main": account.get("is_main", False),
                "created_at": account["created_at"].isoformat() if account["created_at"] else None,
                "updated_at": account["updated_at"].isoformat() if account["updated_at"] else None,
                "user_id": account["user_id"]
            }
            
            logger.info("Exchange account retrieved", account_id=account_id)
            return {"success": True, "data": account_data}
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Error retrieving exchange account", account_id=account_id, error=str(e), exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to retrieve exchange account")

    @router.post("")
    async def create_exchange_account(request: Request):
        """Create a new exchange account"""
        logger.info("🔍 STARTING EXCHANGE ACCOUNT CREATION")

        try:
            # Try to read body
            try:
                body = await request.json()
                logger.info("🔍 BODY SUCCESSFULLY PARSED", body=body, body_keys=list(body.keys()) if isinstance(body, dict) else "NOT_DICT")
            except Exception as json_error:
                logger.error("🔍 JSON PARSE ERROR", error=str(json_error))
                raise HTTPException(status_code=400, detail=f"Invalid JSON: {str(json_error)}")

            # Check if body is dict
            if not isinstance(body, dict):
                logger.error("🔍 BODY IS NOT DICT", body_type=type(body))
                raise HTTPException(status_code=400, detail="Request body must be a JSON object")
            
            # Validate required fields
            required_fields = ["name", "exchange", "api_key", "secret_key"]
            for field in required_fields:
                if field not in body:
                    raise HTTPException(status_code=400, detail=f"Missing required field: {field}")
            
            name = body.get("name", "").strip()
            exchange = body.get("exchange", "").lower()
            api_key = body.get("api_key", "").strip()
            secret_key = body.get("secret_key", "").strip()
            testnet = body.get("testnet", True)  # Default to testnet for safety
            is_main = body.get("is_main", False)  # Nova opção para conta principal
            
            # Validate exchange type
            if exchange not in ["binance", "bybit", "bingx", "okx", "bitget", "coinbase"]:
                raise HTTPException(status_code=400, detail=f"Unsupported exchange '{exchange}'. Supported: binance, bybit, bingx, okx, bitget, coinbase")
            
            # Get user_id from JWT token
            user_uuid = get_user_uuid_from_request(request)
            if not user_uuid:
                raise HTTPException(status_code=401, detail="Authentication required")

            user_id = user_uuid
            logger.info("✅ STEP 1: Usuário autenticado via JWT", user_id=str(user_id))

            # Se esta conta está sendo marcada como principal, desmarcar todas as outras
            if is_main:
                logger.info("🔍 STEP 2: Desmarcando contas principais anteriores...")
                await transaction_db.execute("""
                    UPDATE exchange_accounts
                    SET is_main = false
                    WHERE exchange = $1 AND user_id = $2
                """, exchange, user_id)
                logger.info("✅ STEP 2: Contas desmarcadas")
            else:
                logger.info("⏭️ STEP 2: Pulado (is_main=False)")

            # Store API credentials in plain text (Supabase encryption at rest)
            logger.info("🔍 STEP 3: Armazenando credenciais (plain text - Supabase encryption)")

            # Create the exchange account
            logger.info("🔍 STEP 4: Inserindo no banco de dados...")
            import time
            start_insert = time.time()
            account_id = await transaction_db.fetchval("""
                INSERT INTO exchange_accounts (
                    name, exchange, testnet, is_active,
                    api_key, secret_key, user_id, is_main,
                    created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW(), NOW())
                RETURNING id
            """, name, exchange, testnet, True, api_key, secret_key, user_id, is_main)
            insert_time = (time.time() - start_insert) * 1000
            logger.info("✅ STEP 4: Conta inserida no banco", insert_time_ms=f"{insert_time:.2f}ms")
            
            logger.info("Exchange account created", 
                       account_id=account_id, name=name, exchange=exchange, testnet=testnet)
            
            return {
                "success": True,
                "message": "Exchange account created successfully",
                "data": {
                    "id": account_id,
                    "name": name,
                    "exchange": exchange,
                    "environment": "testnet" if testnet else "mainnet",
                    "is_active": True,
                    "is_main": is_main
                }
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Error creating exchange account", error=str(e), exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to create exchange account")

    @router.put("/{account_id}")
    async def update_exchange_account(account_id: str, request: Request):
        """Update an existing exchange account - validates user ownership"""
        try:
            # Get user_id from JWT token
            user_uuid = get_user_uuid_from_request(request)
            if not user_uuid:
                raise HTTPException(status_code=401, detail="Authentication required")

            body = await request.json()

            # Check if account exists AND belongs to user
            existing = await transaction_db.fetchrow(
                "SELECT id FROM exchange_accounts WHERE id = $1 AND user_id = $2", account_id, user_uuid
            )
            if not existing:
                raise HTTPException(status_code=404, detail="Exchange account not found")
            
            # Build update query dynamically
            update_fields = []
            params = []
            param_count = 1
            
            if "name" in body:
                update_fields.append(f"name = ${param_count}")
                params.append(body["name"].strip())
                param_count += 1
            
            if "testnet" in body:
                update_fields.append(f"testnet = ${param_count}")
                params.append(body["testnet"])
                param_count += 1
            
            if "is_active" in body:
                update_fields.append(f"is_active = ${param_count}")
                params.append(body["is_active"])
                param_count += 1

            if "is_main" in body:
                # Se está marcando como principal, desmarcar TODAS as outras contas (global)
                if body["is_main"]:
                    await transaction_db.execute("""
                        UPDATE exchange_accounts
                        SET is_main = false
                        WHERE id != $1
                    """, account_id)

                update_fields.append(f"is_main = ${param_count}")
                params.append(body["is_main"])
                param_count += 1

            if not update_fields:
                raise HTTPException(status_code=400, detail="No valid fields to update")
            
            # Add updated_at
            update_fields.append(f"updated_at = ${param_count}")
            params.append(datetime.utcnow())
            param_count += 1
            
            # Add account_id for WHERE clause
            params.append(account_id)
            
            query = f"""
                UPDATE exchange_accounts 
                SET {', '.join(update_fields)}
                WHERE id = ${param_count}
            """
            
            await transaction_db.execute(query, *params)
            
            logger.info("Exchange account updated", account_id=account_id)
            return {"success": True, "message": "Exchange account updated successfully"}
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Error updating exchange account", account_id=account_id, error=str(e), exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to update exchange account")

    @router.delete("/{account_id}")
    async def delete_exchange_account(account_id: str, request: Request):
        """Delete an exchange account - validates user ownership"""
        try:
            # Get user_id from JWT token
            user_uuid = get_user_uuid_from_request(request)
            if not user_uuid:
                raise HTTPException(status_code=401, detail="Authentication required")

            # Check if account exists AND belongs to user
            existing = await transaction_db.fetchrow(
                "SELECT id FROM exchange_accounts WHERE id = $1 AND user_id = $2", account_id, user_uuid
            )
            if not existing:
                raise HTTPException(status_code=404, detail="Exchange account not found")

            # Delete the account (only if belongs to user)
            await transaction_db.execute(
                "DELETE FROM exchange_accounts WHERE id = $1 AND user_id = $2", account_id, user_uuid
            )
            
            logger.info("Exchange account deleted", account_id=account_id)
            return {"success": True, "message": "Exchange account deleted successfully"}
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Error deleting exchange account", account_id=account_id, error=str(e), exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to delete exchange account")

    return router
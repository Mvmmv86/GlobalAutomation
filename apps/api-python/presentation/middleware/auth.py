"""Authentication middleware and dependencies"""

from typing import Optional
from uuid import UUID
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from infrastructure.services.auth_service import AuthService
from infrastructure.database.models.user import User
from infrastructure.di.dependencies import get_user_service
from application.services.user_service import UserService


# Security scheme
security = HTTPBearer()


def get_auth_service() -> AuthService:
    """Get AuthService instance"""
    return AuthService()


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_service: AuthService = Depends(get_auth_service),
) -> UUID:
    """
    Extract user ID from JWT token

    Args:
        credentials: JWT token from Authorization header
        auth_service: Authentication service

    Returns:
        UUID: User ID

    Raises:
        HTTPException: If token is invalid or expired
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        user_id_str = auth_service.extract_user_id_from_token(credentials.credentials)
        if user_id_str is None:
            raise credentials_exception

        # Convert to UUID
        user_id = UUID(user_id_str)

    except (ValueError, TypeError):
        raise credentials_exception

    return user_id


async def get_current_user(
    user_id: UUID = Depends(get_current_user_id),
    user_service: UserService = Depends(get_user_service),
) -> User:
    """
    Get current authenticated user

    Args:
        user_id: Current user ID from token
        user_service: User service

    Returns:
        User: Current user object

    Raises:
        HTTPException: If user not found
    """
    user = await user_service.get_user_by_id(user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Inactive user"
        )

    return user


async def get_optional_current_user_id(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    auth_service: AuthService = Depends(get_auth_service),
) -> Optional[UUID]:
    """
    Extract user ID from JWT token (optional)

    Args:
        credentials: Optional JWT token from Authorization header
        auth_service: Authentication service

    Returns:
        Optional[UUID]: User ID if valid token provided, None otherwise
    """
    if not credentials:
        return None

    try:
        user_id_str = auth_service.extract_user_id_from_token(credentials.credentials)
        if user_id_str:
            return UUID(user_id_str)
    except (ValueError, TypeError):
        pass

    return None


# Dependency shortcuts
CurrentUser = Depends(get_current_user)
CurrentUserID = Depends(get_current_user_id)
OptionalUserID = Depends(get_optional_current_user_id)
AuthSvc = Depends(get_auth_service)

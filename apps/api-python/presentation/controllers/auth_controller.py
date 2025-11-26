"""Authentication controller with JWT and 2FA endpoints"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from uuid import UUID

from application.services.user_service import UserService
from infrastructure.services.auth_service import AuthService
from infrastructure.di.dependencies import get_user_service
from presentation.middleware.auth import get_auth_service, CurrentUser, CurrentUserID
from presentation.schemas.auth import (
    LoginRequest,
    LoginResponse,
    RefreshTokenRequest,
    RefreshTokenResponse,
    RegisterRequest,
    RegisterResponse,
    ChangePasswordRequest,
    Enable2FAResponse,
    Verify2FARequest,
    TOTPSetupRequest,
    APIKeyCreateRequest,
    APIKeyResponse,
    UserProfileResponse,
    UpdateProfileRequest,
    SuccessResponse,
)
from infrastructure.database.models.user import User


def create_auth_router() -> APIRouter:
    """Create authentication router"""
    router = APIRouter(prefix="/auth", tags=["Authentication"])

    @router.post(
        "/register",
        response_model=RegisterResponse,
        status_code=status.HTTP_201_CREATED,
    )
    async def register(
        request: RegisterRequest,
        user_service: UserService = Depends(get_user_service),
        auth_service: AuthService = Depends(get_auth_service),
    ):
        """Register a new user"""
        try:
            # Hash password
            hashed_password = auth_service.hash_password(request.password)

            # Create user
            user_data = {
                "email": request.email,
                "password_hash": hashed_password,
                "name": request.name,
                "is_active": True,
                "is_verified": False,  # Would require email verification in production
            }

            user = await user_service.create_user(user_data)

            return RegisterResponse(
                user_id=UUID(user.id),
                email=user.email,
                message="User registered successfully",
            )

        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    @router.post("/login", response_model=LoginResponse)
    async def login(
        request: LoginRequest,
        user_service: UserService = Depends(get_user_service),
        auth_service: AuthService = Depends(get_auth_service),
    ):
        """Authenticate user and return tokens"""
        user = await user_service.authenticate_user(request.email, request.password)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
            )

        # Check 2FA if enabled
        if user.totp_enabled:
            if not request.totp_token:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="2FA token required",
                )

            if not await user_service.verify_2fa_token(
                UUID(user.id), request.totp_token
            ):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid 2FA token"
                )

        # Create tokens
        access_token, refresh_token = auth_service.create_token_pair(
            user.id, user.email
        )

        return LoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=auth_service.settings.access_token_expire_minutes * 60,
        )

    @router.post("/refresh", response_model=RefreshTokenResponse)
    async def refresh_token(
        request: RefreshTokenRequest,
        auth_service: AuthService = Depends(get_auth_service),
    ):
        """Refresh access token"""
        new_access_token = auth_service.refresh_access_token(request.refresh_token)

        if not new_access_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
            )

        return RefreshTokenResponse(
            access_token=new_access_token,
            expires_in=auth_service.settings.access_token_expire_minutes * 60,
        )

    @router.get("/me", response_model=UserProfileResponse)
    async def get_profile(current_user: User = CurrentUser):
        """Get current user profile"""
        return UserProfileResponse(
            id=UUID(current_user.id),
            email=current_user.email,
            name=current_user.name,
            is_active=current_user.is_active,
            is_verified=current_user.is_verified,
            totp_enabled=current_user.totp_enabled,
            created_at=current_user.created_at.isoformat(),
            last_login_at=current_user.last_login_at.isoformat()
            if current_user.last_login_at
            else None,
        )

    @router.put("/me", response_model=UserProfileResponse)
    async def update_profile(
        request: UpdateProfileRequest,
        current_user: User = CurrentUser,
        user_service: UserService = Depends(get_user_service),
    ):
        """Update current user profile"""
        update_data = {}
        if request.name is not None:
            update_data["name"] = request.name

        updated_user = await user_service.update_user(
            UUID(current_user.id), update_data
        )

        if not updated_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

        return UserProfileResponse(
            id=UUID(updated_user.id),
            email=updated_user.email,
            name=updated_user.name,
            is_active=updated_user.is_active,
            is_verified=updated_user.is_verified,
            totp_enabled=updated_user.totp_enabled,
            created_at=updated_user.created_at.isoformat(),
            last_login_at=updated_user.last_login_at.isoformat()
            if updated_user.last_login_at
            else None,
        )

    @router.post("/change-password", response_model=SuccessResponse)
    async def change_password(
        request: ChangePasswordRequest,
        current_user_id: UUID = CurrentUserID,
        user_service: UserService = Depends(get_user_service),
        auth_service: AuthService = Depends(get_auth_service),
    ):
        """Change user password"""
        # Hash new password
        new_hashed_password = auth_service.hash_password(request.new_password)

        success = await user_service.change_password(
            current_user_id, request.current_password, request.new_password
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect",
            )

        return SuccessResponse(message="Password changed successfully")

    @router.post("/2fa/enable", response_model=Enable2FAResponse)
    async def enable_2fa(
        current_user: User = CurrentUser,
        auth_service: AuthService = Depends(get_auth_service),
    ):
        """Enable 2FA for user"""
        if current_user.totp_enabled:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="2FA is already enabled"
            )

        # Generate TOTP secret
        secret = auth_service.generate_totp_secret()
        provisioning_uri = auth_service.get_totp_provisioning_uri(
            secret, current_user.email
        )

        # Generate backup codes (simplified - in production, generate proper codes)
        backup_codes = [f"BACKUP-{i:04d}" for i in range(1, 9)]

        # Store secret temporarily (in production, store in secure temporary storage)
        # For now, we'll return it and expect the user to confirm with TOTP token

        return Enable2FAResponse(
            secret=secret, provisioning_uri=provisioning_uri, backup_codes=backup_codes
        )

    @router.post("/2fa/setup", response_model=SuccessResponse)
    async def setup_2fa(
        request: TOTPSetupRequest,
        current_user_id: UUID = CurrentUserID,
        user_service: UserService = Depends(get_user_service),
        auth_service: AuthService = Depends(get_auth_service),
    ):
        """Complete 2FA setup with verification"""
        # In production, you'd retrieve the temporary secret from secure storage
        # For now, this is a simplified implementation
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="2FA setup requires session storage implementation",
        )

    @router.post("/2fa/verify", response_model=SuccessResponse)
    async def verify_2fa(
        request: Verify2FARequest,
        current_user_id: UUID = CurrentUserID,
        user_service: UserService = Depends(get_user_service),
    ):
        """Verify 2FA token"""
        valid = await user_service.verify_2fa_token(current_user_id, request.totp_token)

        if not valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid 2FA token"
            )

        return SuccessResponse(message="2FA token verified successfully")

    @router.delete("/2fa/disable", response_model=SuccessResponse)
    async def disable_2fa(
        current_user_id: UUID = CurrentUserID,
        user_service: UserService = Depends(get_user_service),
    ):
        """Disable 2FA for user"""
        success = await user_service.disable_2fa(current_user_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to disable 2FA"
            )

        return SuccessResponse(message="2FA disabled successfully")

    @router.get("/api-keys", response_model=List[APIKeyResponse])
    async def get_api_keys(
        current_user_id: UUID = CurrentUserID,
        user_service: UserService = Depends(get_user_service),
    ):
        """Get user's API keys"""
        api_keys = await user_service.get_user_api_keys(current_user_id)

        return [
            APIKeyResponse(
                id=UUID(key.id),
                name=key.name,
                created_at=key.created_at.isoformat(),
                expires_at=key.expires_at.isoformat() if key.expires_at else None,
                last_used=key.last_used_at.isoformat() if key.last_used_at else None,
                usage_count=key.usage_count,
                is_active=key.is_active,
            )
            for key in api_keys
        ]

    @router.post(
        "/api-keys", response_model=APIKeyResponse, status_code=status.HTTP_201_CREATED
    )
    async def create_api_key(
        request: APIKeyCreateRequest,
        current_user_id: UUID = CurrentUserID,
        user_service: UserService = Depends(get_user_service),
    ):
        """Create new API key"""
        try:
            api_key = await user_service.create_api_key(
                current_user_id, request.name, request.expires_days
            )

            return APIKeyResponse(
                id=UUID(api_key.id),
                name=api_key.name,
                key=api_key.key_hash,  # Return actual key only on creation
                created_at=api_key.created_at.isoformat(),
                expires_at=api_key.expires_at.isoformat()
                if api_key.expires_at
                else None,
                last_used=None,
                usage_count=0,
                is_active=api_key.is_active,
            )

        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    @router.delete("/api-keys/{key_id}", response_model=SuccessResponse)
    async def revoke_api_key(
        key_id: UUID,
        current_user_id: UUID = CurrentUserID,
        user_service: UserService = Depends(get_user_service),
    ):
        """Revoke API key"""
        success = await user_service.revoke_api_key(current_user_id, key_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API key not found or not owned by user",
            )

        return SuccessResponse(message="API key revoked successfully")

    return router

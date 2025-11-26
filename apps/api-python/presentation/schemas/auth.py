"""Authentication schemas"""

from typing import Optional
from pydantic import BaseModel, Field, EmailStr
from uuid import UUID


class LoginRequest(BaseModel):
    """Login request schema"""

    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=1, description="User password")
    totp_token: Optional[str] = Field(None, description="TOTP token for 2FA")


class LoginResponse(BaseModel):
    """Login response schema"""

    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration in seconds")


class RefreshTokenRequest(BaseModel):
    """Refresh token request schema"""

    refresh_token: str = Field(..., description="Refresh token")


class RefreshTokenResponse(BaseModel):
    """Refresh token response schema"""

    access_token: str = Field(..., description="New JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration in seconds")


class RegisterRequest(BaseModel):
    """User registration request schema"""

    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="User password")
    name: Optional[str] = Field(None, description="User display name")


class RegisterResponse(BaseModel):
    """User registration response schema"""

    user_id: UUID = Field(..., description="Created user ID")
    email: str = Field(..., description="User email")
    message: str = Field(..., description="Registration success message")


class ChangePasswordRequest(BaseModel):
    """Change password request schema"""

    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, description="New password")


class Enable2FAResponse(BaseModel):
    """Enable 2FA response schema"""

    secret: str = Field(..., description="TOTP secret key")
    provisioning_uri: str = Field(..., description="Provisioning URI for QR code")
    backup_codes: list[str] = Field(..., description="Backup recovery codes")


class Verify2FARequest(BaseModel):
    """Verify 2FA request schema"""

    totp_token: str = Field(..., description="TOTP token")


class TOTPSetupRequest(BaseModel):
    """TOTP setup request schema"""

    totp_token: str = Field(..., description="TOTP token to verify setup")


class APIKeyCreateRequest(BaseModel):
    """API key creation request schema"""

    name: str = Field(..., min_length=1, max_length=100, description="API key name")
    expires_days: Optional[int] = Field(
        None, gt=0, le=365, description="Expiration in days"
    )


class APIKeyResponse(BaseModel):
    """API key response schema"""

    id: UUID = Field(..., description="API key ID")
    name: str = Field(..., description="API key name")
    key: Optional[str] = Field(None, description="API key (only on creation)")
    created_at: str = Field(..., description="Creation timestamp")
    expires_at: Optional[str] = Field(None, description="Expiration timestamp")
    last_used: Optional[str] = Field(None, description="Last usage timestamp")
    usage_count: int = Field(..., description="Total usage count")
    is_active: bool = Field(..., description="Whether key is active")


class UserProfileResponse(BaseModel):
    """User profile response schema"""

    id: UUID = Field(..., description="User ID")
    email: str = Field(..., description="User email")
    name: Optional[str] = Field(None, description="User display name")
    is_active: bool = Field(..., description="Whether user is active")
    is_verified: bool = Field(..., description="Whether user is verified")
    totp_enabled: bool = Field(..., description="Whether 2FA is enabled")
    created_at: str = Field(..., description="Account creation timestamp")
    last_login_at: Optional[str] = Field(None, description="Last login timestamp")


class UpdateProfileRequest(BaseModel):
    """Update profile request schema"""

    name: Optional[str] = Field(None, max_length=100, description="User display name")


class AuthError(BaseModel):
    """Authentication error response"""

    error: str = Field(..., description="Error type")
    detail: str = Field(..., description="Error details")
    code: Optional[str] = Field(None, description="Error code")


class TokenValidationResponse(BaseModel):
    """Token validation response"""

    valid: bool = Field(..., description="Whether token is valid")
    user_id: Optional[UUID] = Field(None, description="User ID if token is valid")
    expires_at: Optional[str] = Field(None, description="Token expiration")


# Success responses
class SuccessResponse(BaseModel):
    """Generic success response"""

    success: bool = Field(True, description="Operation success")
    message: str = Field(..., description="Success message")

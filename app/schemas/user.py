from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field
from uuid import UUID


# ========================
# User Schemas
# ========================

class UserBase(BaseModel):
    """Base user schema with common fields."""
    email: EmailStr
    display_name: str = Field(..., min_length=2, max_length=100)


class UserCreate(UserBase):
    """Schema for user registration."""
    password: str = Field(..., min_length=8, max_length=72)  # bcrypt limit is 72 bytes


class UserLogin(BaseModel):
    """Schema for user login."""
    email: EmailStr
    password: str


class UserUpdate(BaseModel):
    """Schema for updating user profile."""
    display_name: Optional[str] = Field(None, min_length=2, max_length=100)


class PasswordChange(BaseModel):
    """Schema for changing password."""
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, max_length=72)  # bcrypt limit is 72 bytes


class UserResponse(UserBase):
    """Schema for user response (excludes password)."""
    id: UUID
    is_active: bool
    is_verified: bool
    onboarding_complete: bool
    auth_provider: str = "email"  # "email" or "google"
    profile_picture_url: Optional[str] = None
    disclaimer_accepted_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserWithAllergens(UserResponse):
    """User response including their allergens."""
    allergens: List["UserAllergenResponse"] = []


# ========================
# Token Schemas
# ========================

class Token(BaseModel):
    """JWT token response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    """JWT token payload."""
    sub: str  # User ID
    exp: datetime
    type: str  # "access" or "refresh"


class TokenRefresh(BaseModel):
    """Schema for token refresh request."""
    refresh_token: str


# ========================
# Auth Response Schemas
# ========================

class AuthResponse(BaseModel):
    """Response after successful login/register."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse
    is_new_user: bool = False  # True if user was just created (for onboarding flow)


# ========================
# OAuth Schemas
# ========================

class GoogleAuthRequest(BaseModel):
    """
    Request for Google OAuth authentication.

    The id_token is obtained from Google Sign-In SDK on the client.
    We verify it server-side to ensure authenticity.
    """
    id_token: str = Field(..., description="Google ID token from client-side sign-in")


class OAuthUserInfo(BaseModel):
    """Parsed user info from OAuth provider."""
    provider: str  # "google"
    provider_user_id: str  # Google's unique user ID
    email: EmailStr
    display_name: str
    profile_picture_url: Optional[str] = None
    email_verified: bool = False


# Forward reference for circular import
from app.schemas.allergen import UserAllergenResponse
UserWithAllergens.model_rebuild()

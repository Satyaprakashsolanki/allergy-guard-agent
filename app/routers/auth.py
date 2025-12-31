import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_

from app.core.database import get_db
from app.core.security import verify_password, get_password_hash, create_access_token, create_refresh_token, decode_token
from app.models.user import User
from app.schemas.user import UserCreate, UserLogin, AuthResponse, TokenRefresh, UserResponse, GoogleAuthRequest
from app.services.google_oauth import verify_google_token, GoogleOAuthError, GoogleOAuthNotConfiguredError

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    """Register a new user."""
    # Check if email already exists
    result = await db.execute(select(User).where(User.email == user_data.email))
    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Create new user
    hashed_password = get_password_hash(user_data.password)
    new_user = User(
        email=user_data.email,
        password_hash=hashed_password,
        display_name=user_data.display_name,
    )

    try:
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
    except Exception:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user account. Please try again."
        )

    # Generate tokens
    access_token = create_access_token(data={"sub": str(new_user.id)})
    refresh_token = create_refresh_token(data={"sub": str(new_user.id)})

    return AuthResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse.model_validate(new_user)
    )


@router.post("/login", response_model=AuthResponse)
async def login(credentials: UserLogin, db: AsyncSession = Depends(get_db)):
    """Login user and return tokens."""
    # Find user by email
    result = await db.execute(select(User).where(User.email == credentials.email))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    # Check if user is a Google-only user (no password set)
    if user.password_hash is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This account uses Google Sign-In. Please sign in with Google."
        )

    if not verify_password(credentials.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled"
        )

    # Generate tokens
    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})

    return AuthResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse.model_validate(user)
    )


@router.post("/refresh", response_model=AuthResponse)
async def refresh_token(token_data: TokenRefresh, db: AsyncSession = Depends(get_db)):
    """Refresh access token using refresh token."""
    payload = decode_token(token_data.refresh_token)

    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )

    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )

    # Generate new tokens
    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})

    return AuthResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse.model_validate(user)
    )


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout():
    """Logout user (client should discard tokens)."""
    # For stateless JWT, just return success
    # Client is responsible for removing tokens
    return {"message": "Successfully logged out"}


@router.post("/google", response_model=AuthResponse)
async def google_auth(auth_data: GoogleAuthRequest, db: AsyncSession = Depends(get_db)):
    """
    Authenticate user with Google Sign-In.

    This endpoint handles both login and registration:
    - If user exists (by google_id or email): logs them in
    - If user doesn't exist: creates a new account

    Account Linking Logic:
    1. First, try to find user by google_id (returning Google user)
    2. If not found, check if email exists (email-registered user trying Google)
    3. If email exists with auth_provider='email': link Google to existing account
    4. If no user found: create new account

    Security:
    - Token is verified server-side with Google's API
    - Google users are auto-verified (email_verified from Google)
    - No password required for Google users
    """
    try:
        # Verify the Google token and extract user info
        google_user = await verify_google_token(auth_data.id_token)

    except GoogleOAuthNotConfiguredError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google Sign-In is not available at this time."
        )
    except GoogleOAuthError as e:
        logger.warning(f"Google auth failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google authentication failed. Please try again."
        )

    is_new_user = False

    # Try to find existing user by google_id first, then by email
    result = await db.execute(
        select(User).where(
            or_(
                User.google_id == google_user.provider_user_id,
                User.email == google_user.email
            )
        )
    )
    user = result.scalar_one_or_none()

    if user:
        # Existing user found
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is disabled"
            )

        # Account linking: if user registered with email but now using Google
        if user.google_id is None and user.auth_provider == "email":
            logger.info(f"Linking Google account to existing email user: {user.email}")
            user.google_id = google_user.provider_user_id
            user.is_verified = True  # Google verifies email
            if google_user.profile_picture_url and not user.profile_picture_url:
                user.profile_picture_url = google_user.profile_picture_url
            await db.commit()
            await db.refresh(user)

    else:
        # Create new user
        is_new_user = True
        logger.info(f"Creating new Google user: {google_user.email}")

        user = User(
            email=google_user.email,
            display_name=google_user.display_name,
            password_hash=None,  # No password for Google users
            auth_provider="google",
            google_id=google_user.provider_user_id,
            profile_picture_url=google_user.profile_picture_url,
            is_verified=google_user.email_verified,  # Trust Google's verification
        )

        try:
            db.add(user)
            await db.commit()
            await db.refresh(user)
        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to create Google user: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create account. Please try again."
            )

    # Generate JWT tokens
    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})

    return AuthResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse.model_validate(user),
        is_new_user=is_new_user,
    )

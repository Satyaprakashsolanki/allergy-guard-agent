"""
Google OAuth Service

Handles verification of Google ID tokens and extraction of user information.
This service verifies tokens server-side to prevent token spoofing attacks.
"""

import logging
from typing import Optional
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

from app.config import get_settings
from app.schemas.user import OAuthUserInfo

logger = logging.getLogger(__name__)
settings = get_settings()


class GoogleOAuthError(Exception):
    """Raised when Google OAuth verification fails."""
    pass


class GoogleOAuthNotConfiguredError(GoogleOAuthError):
    """Raised when Google OAuth credentials are not configured."""
    pass


async def verify_google_token(token: str) -> OAuthUserInfo:
    """
    Verify a Google ID token and extract user information.

    Args:
        token: The ID token received from Google Sign-In on the client

    Returns:
        OAuthUserInfo with verified user data from Google

    Raises:
        GoogleOAuthNotConfiguredError: If GOOGLE_CLIENT_ID is not set
        GoogleOAuthError: If token verification fails

    Security Notes:
        - Always verify tokens server-side, never trust client claims
        - The token is cryptographically signed by Google
        - We verify the token was issued for our app (audience check)
    """
    google_client_id = getattr(settings, 'GOOGLE_CLIENT_ID', None)

    if not google_client_id:
        logger.error("GOOGLE_CLIENT_ID not configured in settings")
        raise GoogleOAuthNotConfiguredError(
            "Google OAuth is not configured. Please contact support."
        )

    try:
        # Verify the token with Google's servers
        # This checks:
        # 1. Token signature is valid (signed by Google)
        # 2. Token is not expired
        # 3. Token was issued for our app (audience = our client ID)
        # 4. Token issuer is Google (accounts.google.com)
        idinfo = id_token.verify_oauth2_token(
            token,
            google_requests.Request(),
            google_client_id
        )

        # Additional security checks
        # Verify issuer
        if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
            raise GoogleOAuthError("Invalid token issuer")

        # Extract user info
        google_user_id = idinfo['sub']  # Google's unique user ID (stable across sessions)
        email = idinfo.get('email')
        email_verified = idinfo.get('email_verified', False)
        display_name = idinfo.get('name', email.split('@')[0] if email else 'User')
        profile_picture = idinfo.get('picture')

        if not email:
            raise GoogleOAuthError("Email not provided in Google token")

        logger.info(f"Successfully verified Google token for user: {email}")

        return OAuthUserInfo(
            provider="google",
            provider_user_id=google_user_id,
            email=email,
            display_name=display_name,
            profile_picture_url=profile_picture,
            email_verified=email_verified,
        )

    except ValueError as e:
        # Token is invalid (expired, wrong audience, etc.)
        logger.warning(f"Google token verification failed: {e}")
        raise GoogleOAuthError(f"Invalid Google token: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error verifying Google token: {e}")
        raise GoogleOAuthError("Failed to verify Google authentication")

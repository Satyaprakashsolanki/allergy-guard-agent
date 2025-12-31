from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.security import verify_password, get_password_hash
from app.models.user import User
from app.models.allergen import UserAllergen, Allergen
from app.models.preferences import UserPreferences
from app.schemas.user import UserResponse, UserUpdate, PasswordChange
from app.schemas.allergen import UpdateUserAllergensRequest, UserAllergenResponse
from app.schemas.preferences import (
    PreferencesUpdate,
    PreferencesResponse,
    CUISINE_OPTIONS,
    RISK_TOLERANCE_OPTIONS,
    DINING_CONTEXT_OPTIONS,
)

router = APIRouter()


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """Get current user's profile."""
    return UserResponse.model_validate(current_user)


@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update current user's profile."""
    if user_data.display_name:
        current_user.display_name = user_data.display_name

    await db.commit()
    await db.refresh(current_user)

    return UserResponse.model_validate(current_user)


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_current_user(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete current user's account (GDPR compliance)."""
    try:
        await db.delete(current_user)
        await db.commit()
    except Exception:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete account. Please try again."
        )
    return None


@router.put("/me/password", response_model=UserResponse)
async def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Change current user's password.

    Requires current password verification for security.
    Note: Google-only users (no password) cannot use this endpoint.
    """
    # Check if user has a password (Google-only users don't)
    if current_user.password_hash is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot change password for accounts created with Google Sign-In. Please use Google to sign in."
        )

    # Verify current password
    if not verify_password(password_data.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect."
        )

    # Ensure new password is different from current
    if verify_password(password_data.new_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from current password."
        )

    try:
        # Update password
        current_user.password_hash = get_password_hash(password_data.new_password)
        await db.commit()
        await db.refresh(current_user)

        return UserResponse.model_validate(current_user)
    except Exception:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update password. Please try again."
        )


@router.put("/me/allergens", response_model=list[UserAllergenResponse])
async def update_user_allergens(
    allergen_data: UpdateUserAllergensRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update user's allergen preferences."""
    # Validate all allergen IDs exist
    allergen_ids = [a.allergen_id for a in allergen_data.allergens]
    result = await db.execute(select(Allergen).where(Allergen.id.in_(allergen_ids)))
    valid_allergens = {a.id for a in result.scalars().all()}

    invalid_ids = set(allergen_ids) - valid_allergens
    if invalid_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid allergen IDs: {', '.join(invalid_ids)}"
        )

    try:
        # Delete existing user allergens
        await db.execute(delete(UserAllergen).where(UserAllergen.user_id == current_user.id))

        # Add new allergens
        new_allergens = []
        for allergen in allergen_data.allergens:
            user_allergen = UserAllergen(
                user_id=current_user.id,
                allergen_id=allergen.allergen_id,
                severity=allergen.severity
            )
            db.add(user_allergen)
            new_allergens.append(user_allergen)

        await db.commit()

        # Refresh to get IDs
        for ua in new_allergens:
            await db.refresh(ua)

        return [UserAllergenResponse.model_validate(ua) for ua in new_allergens]
    except HTTPException:
        raise
    except Exception:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update allergens. Please try again."
        )


@router.get("/me/allergens", response_model=list[UserAllergenResponse])
async def get_user_allergens(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user's allergen preferences."""
    result = await db.execute(
        select(UserAllergen).where(UserAllergen.user_id == current_user.id)
    )
    user_allergens = result.scalars().all()
    return [UserAllergenResponse.model_validate(ua) for ua in user_allergens]


@router.post("/me/onboarding", response_model=UserResponse)
async def complete_onboarding(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Mark user's onboarding as complete."""
    current_user.onboarding_complete = True
    current_user.disclaimer_accepted_at = datetime.utcnow()

    await db.commit()
    await db.refresh(current_user)

    return UserResponse.model_validate(current_user)


# ========================
# Preferences Endpoints
# ========================

@router.get("/me/preferences", response_model=PreferencesResponse)
async def get_user_preferences(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get user's context preferences.

    Returns the user's preferences for AI analysis customization.
    If no preferences exist, creates default preferences.
    """
    result = await db.execute(
        select(UserPreferences).where(UserPreferences.user_id == current_user.id)
    )
    preferences = result.scalar_one_or_none()

    # Create default preferences if none exist
    if not preferences:
        preferences = UserPreferences(
            user_id=current_user.id,
            favorite_cuisines=[],
            risk_tolerance="standard",
            default_dining_context="restaurant"
        )
        db.add(preferences)
        await db.commit()
        await db.refresh(preferences)

    return PreferencesResponse.model_validate(preferences)


@router.put("/me/preferences", response_model=PreferencesResponse)
async def update_user_preferences(
    preferences_data: PreferencesUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update user's context preferences.

    Allows partial updates - only provided fields will be changed.
    """
    result = await db.execute(
        select(UserPreferences).where(UserPreferences.user_id == current_user.id)
    )
    preferences = result.scalar_one_or_none()

    # Create preferences if none exist
    if not preferences:
        preferences = UserPreferences(
            user_id=current_user.id,
            favorite_cuisines=[],
            risk_tolerance="standard",
            default_dining_context="restaurant"
        )
        db.add(preferences)

    # Update only provided fields
    if preferences_data.favorite_cuisines is not None:
        # Validate cuisine IDs
        valid_cuisine_ids = {c["id"] for c in CUISINE_OPTIONS}
        for cuisine in preferences_data.favorite_cuisines:
            if cuisine not in valid_cuisine_ids:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid cuisine type: {cuisine}"
                )
        preferences.favorite_cuisines = preferences_data.favorite_cuisines

    if preferences_data.risk_tolerance is not None:
        preferences.risk_tolerance = preferences_data.risk_tolerance.value

    if preferences_data.default_dining_context is not None:
        preferences.default_dining_context = preferences_data.default_dining_context.value

    try:
        await db.commit()
        await db.refresh(preferences)
        return PreferencesResponse.model_validate(preferences)
    except Exception:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update preferences. Please try again."
        )


@router.get("/me/preferences/options")
async def get_preference_options():
    """
    Get available options for preferences.

    Returns all valid options for cuisines, risk tolerance, and dining context.
    Useful for building the frontend preferences UI.
    """
    return {
        "cuisines": CUISINE_OPTIONS,
        "risk_tolerance": RISK_TOLERANCE_OPTIONS,
        "dining_context": DINING_CONTEXT_OPTIONS,
    }

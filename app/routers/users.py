from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.allergen import UserAllergen, Allergen
from app.schemas.user import UserResponse, UserUpdate
from app.schemas.allergen import UpdateUserAllergensRequest, UserAllergenResponse

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
    current_user.disclaimer_accepted_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(current_user)

    return UserResponse.model_validate(current_user)

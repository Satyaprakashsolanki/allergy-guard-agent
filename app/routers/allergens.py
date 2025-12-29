from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.allergen import Allergen
from app.schemas.allergen import AllergenResponse

router = APIRouter()


@router.get("", response_model=list[AllergenResponse])
async def get_all_allergens(db: AsyncSession = Depends(get_db)):
    """Get all supported allergens."""
    result = await db.execute(select(Allergen).order_by(Allergen.name))
    allergens = result.scalars().all()
    return [AllergenResponse.model_validate(a) for a in allergens]


@router.get("/{allergen_id}", response_model=AllergenResponse)
async def get_allergen(allergen_id: str, db: AsyncSession = Depends(get_db)):
    """Get allergen details by ID."""
    result = await db.execute(select(Allergen).where(Allergen.id == allergen_id))
    allergen = result.scalar_one_or_none()

    if not allergen:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Allergen '{allergen_id}' not found"
        )

    return AllergenResponse.model_validate(allergen)


@router.get("/{allergen_id}/hidden-sources", response_model=list[str])
async def get_allergen_hidden_sources(allergen_id: str, db: AsyncSession = Depends(get_db)):
    """Get hidden sources for an allergen."""
    result = await db.execute(select(Allergen).where(Allergen.id == allergen_id))
    allergen = result.scalar_one_or_none()

    if not allergen:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Allergen '{allergen_id}' not found"
        )

    return allergen.hidden_sources or []

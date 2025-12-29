"""Analysis endpoints for menu scanning and response analysis."""

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.scan import Scan, ScanDish
from app.schemas.analysis import (
    MenuAnalysisRequest,
    MenuAnalysisResponse,
    DishAnalysis,
    ResponseAnalysisRequest,
    ResponseAnalysisResponse,
)
from app.services.openai_service import analyze_menu_text, analyze_staff_response

router = APIRouter()


@router.post("/menu", response_model=MenuAnalysisResponse)
async def analyze_menu(
    request: MenuAnalysisRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Analyze menu text for potential allergens.

    Uses OpenAI for advanced analysis, with rule-based fallback.
    CRITICAL: On any error, returns 'Insufficient Information' - NEVER 'Low Risk'.
    """
    try:
        # Call OpenAI service
        analysis_result = await analyze_menu_text(
            menu_text=request.menu_text,
            user_allergens=request.user_allergens,
            cuisine_hint=request.cuisine_hint
        )

        dishes = analysis_result.get("dishes", [])

        # Calculate average confidence
        avg_confidence = 0.0
        if dishes:
            avg_confidence = sum(d.get("confidence", 0.5) for d in dishes) / len(dishes)

        # Save scan to database
        scan = Scan(
            user_id=current_user.id,
            raw_text=request.menu_text,
            dish_count=len(dishes),
            avg_confidence=avg_confidence
        )
        db.add(scan)
        await db.flush()

        # Save individual dishes
        for dish_data in dishes:
            scan_dish = ScanDish(
                scan_id=scan.id,
                name=dish_data.get("name", "Unknown"),
                risk_level=dish_data.get("risk_level", "medium"),
                detected_allergens=dish_data.get("detected_allergens", []),
                confidence=dish_data.get("confidence", 0.5),
                notes=dish_data.get("notes")
            )
            db.add(scan_dish)

        await db.commit()
        await db.refresh(scan)

        # Build response
        dish_analyses = [
            DishAnalysis(
                name=d.get("name", "Unknown"),
                risk_level=d.get("risk_level", "medium"),
                detected_allergens=d.get("detected_allergens", []),
                confidence=d.get("confidence", 0.5),
                notes=d.get("notes")
            )
            for d in dishes
        ]

        return MenuAnalysisResponse(
            scan_id=scan.id,
            dishes=dish_analyses,
            raw_text=request.menu_text,
            dish_count=len(dishes),
            analyzed_at=datetime.utcnow()
        )

    except Exception as e:
        print(f"Analysis error: {e}")
        # CRITICAL: On error, return insufficient info result
        return MenuAnalysisResponse(
            scan_id=None,
            dishes=[
                DishAnalysis(
                    name="Analysis Error",
                    risk_level="medium",  # NEVER low on error
                    detected_allergens=[],
                    confidence=0.0,
                    notes="Unable to analyze menu. Please verify all ingredients with restaurant staff."
                )
            ],
            raw_text=request.menu_text,
            dish_count=0,
            analyzed_at=datetime.utcnow()
        )


@router.post("/response", response_model=ResponseAnalysisResponse)
async def analyze_response(
    request: ResponseAnalysisRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Analyze restaurant staff response for clarity and safety.

    Detects uncertainty indicators and provides recommendations.
    CRITICAL: On error, returns 'unclear' - NEVER 'clear'.
    """
    try:
        result = await analyze_staff_response(
            response_text=request.response_text,
            user_allergens=request.user_allergens
        )

        return ResponseAnalysisResponse(
            clarity=result.get("clarity", "unclear"),
            confidence=result.get("confidence", 0.5),
            flags=result.get("flags", []),
            recommendation=result.get("recommendation", "Please verify with restaurant staff."),
            analyzed_at=datetime.utcnow()
        )

    except Exception as e:
        print(f"Response analysis error: {e}")
        # CRITICAL: On error, return unclear
        return ResponseAnalysisResponse(
            clarity="unclear",  # NEVER clear on error
            confidence=0.0,
            flags=["Analysis error occurred"],
            recommendation="Unable to analyze response. Please verify directly with restaurant staff and use your own judgment.",
            analyzed_at=datetime.utcnow()
        )


@router.post("/dish", response_model=DishAnalysis)
async def analyze_single_dish(
    dish_name: str,
    user_allergens: list[str],
    ingredients: str = None,
    current_user: User = Depends(get_current_user)
):
    """Analyze a single dish for allergens."""
    menu_text = dish_name
    if ingredients:
        menu_text += f"\nIngredients: {ingredients}"

    try:
        result = await analyze_menu_text(
            menu_text=menu_text,
            user_allergens=user_allergens
        )

        dishes = result.get("dishes", [])
        if dishes:
            dish = dishes[0]
            return DishAnalysis(
                name=dish.get("name", dish_name),
                risk_level=dish.get("risk_level", "medium"),
                detected_allergens=dish.get("detected_allergens", []),
                confidence=dish.get("confidence", 0.5),
                notes=dish.get("notes")
            )

        # No dishes found
        return DishAnalysis(
            name=dish_name,
            risk_level="medium",
            detected_allergens=[],
            confidence=0.5,
            notes="Unable to analyze dish. Please verify with restaurant staff."
        )

    except Exception as e:
        print(f"Dish analysis error: {e}")
        return DishAnalysis(
            name=dish_name,
            risk_level="medium",  # NEVER low on error
            detected_allergens=[],
            confidence=0.0,
            notes="Analysis error. Please verify all ingredients with restaurant staff."
        )

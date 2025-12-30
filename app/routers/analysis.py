"""Analysis endpoints for menu scanning and response analysis."""

import logging
from datetime import datetime, timezone
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
    DishAnalysisRequest,
    ResponseAnalysisRequest,
    ResponseAnalysisResponse,
)
from app.services.openai_service import (
    analyze_menu_text,
    analyze_staff_response,
    OpenAINotConfiguredError,
)

logger = logging.getLogger(__name__)
router = APIRouter()

# Error message constants
ERROR_AI_SERVICE_UNAVAILABLE = "AI analysis service is not available. Please contact support."


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
            analyzed_at=datetime.now(timezone.utc)
        )

    except OpenAINotConfiguredError as e:
        logger.error(f"OpenAI not configured: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=ERROR_AI_SERVICE_UNAVAILABLE
        )
    except Exception as e:
        logger.error(f"Menu analysis error: {e}")
        # Rollback any partial database changes
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis failed: {str(e)}. Please try again or verify ingredients with restaurant staff."
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
            analyzed_at=datetime.now(timezone.utc)
        )

    except OpenAINotConfiguredError as e:
        logger.error(f"OpenAI not configured: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=ERROR_AI_SERVICE_UNAVAILABLE
        )
    except Exception as e:
        logger.error(f"Response analysis error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Response analysis failed: {str(e)}. Please verify directly with restaurant staff."
        )


@router.post("/dish", response_model=DishAnalysis)
async def analyze_single_dish(
    request: DishAnalysisRequest,
    current_user: User = Depends(get_current_user)
):
    """Analyze a single dish for allergens."""
    menu_text = request.dish_name
    if request.ingredients:
        menu_text += f"\nIngredients: {request.ingredients}"

    try:
        result = await analyze_menu_text(
            menu_text=menu_text,
            user_allergens=request.user_allergens
        )

        dishes = result.get("dishes", [])
        if dishes:
            dish = dishes[0]
            return DishAnalysis(
                name=dish.get("name", request.dish_name),
                risk_level=dish.get("risk_level", "medium"),
                detected_allergens=dish.get("detected_allergens", []),
                confidence=dish.get("confidence", 0.5),
                notes=dish.get("notes")
            )

        # No dishes found in response - still a valid scenario
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Could not extract dish information. Please provide more details or verify with restaurant staff."
        )

    except OpenAINotConfiguredError as e:
        logger.error(f"OpenAI not configured: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=ERROR_AI_SERVICE_UNAVAILABLE
        )
    except HTTPException:
        raise  # Re-raise HTTP exceptions as-is
    except Exception as e:
        logger.error(f"Dish analysis error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Dish analysis failed: {str(e)}. Please verify ingredients with restaurant staff."
        )

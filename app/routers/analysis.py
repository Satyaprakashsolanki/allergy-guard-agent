"""Analysis endpoints for menu scanning and response analysis."""

import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.scan import Scan, ScanDish
from app.models.response_analysis import ResponseAnalysis
from app.models.preferences import UserPreferences
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from app.schemas.analysis import (
    MenuAnalysisRequest,
    MenuAnalysisResponse,
    DishAnalysis,
    DishAnalysisRequest,
    ResponseAnalysisRequest,
    ResponseAnalysisResponse,
    ScanSummary,
    ScanDetail,
    ScanHistoryResponse,
    ResponseAnalysisSummary,
    ResponseAnalysisDetail,
    ResponseHistoryResponse,
    ResponseAnalysisInScan,
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
        # Fetch user preferences for context-aware analysis
        prefs_result = await db.execute(
            select(UserPreferences).where(UserPreferences.user_id == current_user.id)
        )
        user_prefs = prefs_result.scalar_one_or_none()

        # Build preferences dict for AI service
        user_preferences = None
        if user_prefs:
            user_preferences = {
                "favorite_cuisines": user_prefs.favorite_cuisines or [],
                "risk_tolerance": user_prefs.risk_tolerance,
                "default_dining_context": user_prefs.default_dining_context,
            }

        # Call OpenAI service with preferences
        analysis_result = await analyze_menu_text(
            menu_text=request.menu_text,
            user_allergens=request.user_allergens,
            cuisine_hint=request.cuisine_hint,
            user_preferences=user_preferences
        )

        dishes = analysis_result.get("dishes", [])

        # Calculate average confidence
        avg_confidence = 0.0
        if dishes:
            avg_confidence = sum(d.get("confidence", 0.5) for d in dishes) / len(dishes)

        # Save scan to database with full context
        scan = Scan(
            user_id=current_user.id,
            raw_text=request.menu_text,
            dish_count=len(dishes),
            avg_confidence=avg_confidence,
            cuisine_hint=request.cuisine_hint,  # Store cuisine for future reference
            allergens_used=request.user_allergens,  # Store which allergens were checked
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
                notes=d.get("notes"),
                allergen_breakdown=d.get("allergen_breakdown")  # Include itemized breakdown
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
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
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

        clarity = result.get("clarity", "unclear")
        confidence = result.get("confidence", 0.5)
        flags = result.get("flags", [])
        recommendation = result.get("recommendation", "Please verify with restaurant staff.")

        # Persist analysis to database for history tracking
        response_analysis = ResponseAnalysis(
            user_id=current_user.id,
            scan_id=request.scan_id,  # Optional link to scan
            response_text=request.response_text,
            clarity=clarity,
            confidence=confidence,
            flags=flags,
            recommendation=recommendation,
            allergens_checked=request.user_allergens,
        )
        db.add(response_analysis)
        await db.commit()

        return ResponseAnalysisResponse(
            id=response_analysis.id,
            clarity=clarity,
            confidence=confidence,
            flags=flags,
            recommendation=recommendation,
            analyzed_at=datetime.now(timezone.utc),
            scan_id=request.scan_id
        )

    except OpenAINotConfiguredError as e:
        logger.error(f"OpenAI not configured: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=ERROR_AI_SERVICE_UNAVAILABLE
        )
    except Exception as e:
        logger.error(f"Response analysis error: {e}")
        await db.rollback()
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


# ========================
# Scan History Endpoints
# ========================

@router.get("/history", response_model=ScanHistoryResponse)
async def get_scan_history(
    page: int = 1,
    page_size: int = 10,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get user's scan history with pagination.

    Returns a list of scan summaries for the current user,
    ordered by most recent first.
    """
    # Validate pagination
    if page < 1:
        page = 1
    if page_size < 1 or page_size > 50:
        page_size = 10

    offset = (page - 1) * page_size

    try:
        # Get total count
        count_query = select(func.count(Scan.id)).where(Scan.user_id == current_user.id)
        total_result = await db.execute(count_query)
        total_count = total_result.scalar() or 0

        # Get scans with dishes for risk counting
        query = (
            select(Scan)
            .options(selectinload(Scan.dishes))
            .where(Scan.user_id == current_user.id)
            .order_by(Scan.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        result = await db.execute(query)
        scans = result.scalars().all()

        # Build summaries with risk counts
        scan_summaries = []
        for scan in scans:
            high_risk = sum(1 for d in scan.dishes if d.risk_level == "high")
            medium_risk = sum(1 for d in scan.dishes if d.risk_level == "medium")
            low_risk = sum(1 for d in scan.dishes if d.risk_level == "low")

            scan_summaries.append(ScanSummary(
                id=scan.id,
                dish_count=scan.dish_count,
                avg_confidence=float(scan.avg_confidence),
                cuisine_hint=scan.cuisine_hint,
                allergens_used=scan.allergens_used or [],
                created_at=scan.created_at,
                high_risk_count=high_risk,
                medium_risk_count=medium_risk,
                low_risk_count=low_risk,
            ))

        return ScanHistoryResponse(
            scans=scan_summaries,
            total_count=total_count,
            page=page,
            page_size=page_size,
        )

    except Exception as e:
        logger.error(f"Error fetching scan history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load scan history."
        )


@router.get("/history/{scan_id}", response_model=ScanDetail)
async def get_scan_detail(
    scan_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed scan data by ID.

    Returns full scan details including all dishes and their analysis.
    """
    try:
        from uuid import UUID as PyUUID
        scan_uuid = PyUUID(scan_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid scan ID format."
        )

    try:
        query = (
            select(Scan)
            .options(
                selectinload(Scan.dishes),
                selectinload(Scan.response_analyses)
            )
            .where(Scan.id == scan_uuid, Scan.user_id == current_user.id)
        )
        result = await db.execute(query)
        scan = result.scalar_one_or_none()

        if not scan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Scan not found."
            )

        # Build dish analysis list
        dishes = [
            DishAnalysis(
                name=dish.name,
                description=dish.description,
                risk_level=dish.risk_level,
                detected_allergens=dish.detected_allergens or [],
                confidence=float(dish.confidence),
                notes=dish.notes,
            )
            for dish in scan.dishes
        ]

        # Build response analysis list with truncated preview
        response_analyses = [
            ResponseAnalysisInScan(
                id=resp.id,
                clarity=resp.clarity,
                confidence=float(resp.confidence),
                response_preview=resp.response_text[:100] + "..." if len(resp.response_text) > 100 else resp.response_text,
                created_at=resp.created_at,
            )
            for resp in scan.response_analyses
        ]

        return ScanDetail(
            id=scan.id,
            dish_count=scan.dish_count,
            avg_confidence=float(scan.avg_confidence),
            cuisine_hint=scan.cuisine_hint,
            allergens_used=scan.allergens_used or [],
            raw_text=scan.raw_text,
            dishes=dishes,
            response_analyses=response_analyses,
            created_at=scan.created_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching scan detail: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load scan details."
        )


# ========================
# Response Analysis History Endpoints
# ========================

@router.get("/responses", response_model=ResponseHistoryResponse)
async def get_response_history(
    page: int = 1,
    page_size: int = 10,
    scan_id: str = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get user's response analysis history with pagination.

    Optionally filter by scan_id to get responses for a specific scan.
    Returns a list of response summaries ordered by most recent first.
    """
    # Validate pagination
    if page < 1:
        page = 1
    if page_size < 1 or page_size > 50:
        page_size = 10

    offset = (page - 1) * page_size

    try:
        # Build base query filter
        filters = [ResponseAnalysis.user_id == current_user.id]

        # Optional scan_id filter
        if scan_id:
            from uuid import UUID as PyUUID
            try:
                scan_uuid = PyUUID(scan_id)
                filters.append(ResponseAnalysis.scan_id == scan_uuid)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid scan ID format."
                )

        # Get total count
        count_query = select(func.count(ResponseAnalysis.id)).where(*filters)
        total_result = await db.execute(count_query)
        total_count = total_result.scalar() or 0

        # Get responses
        query = (
            select(ResponseAnalysis)
            .where(*filters)
            .order_by(ResponseAnalysis.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        result = await db.execute(query)
        responses = result.scalars().all()

        # Build summaries with truncated preview
        response_summaries = []
        for resp in responses:
            preview = resp.response_text[:100] + "..." if len(resp.response_text) > 100 else resp.response_text
            response_summaries.append(ResponseAnalysisSummary(
                id=resp.id,
                clarity=resp.clarity,
                confidence=float(resp.confidence),
                scan_id=resp.scan_id,
                allergens_checked=resp.allergens_checked or [],
                created_at=resp.created_at,
                response_preview=preview,
            ))

        return ResponseHistoryResponse(
            responses=response_summaries,
            total_count=total_count,
            page=page,
            page_size=page_size,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching response history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load response history."
        )


@router.get("/responses/{response_id}", response_model=ResponseAnalysisDetail)
async def get_response_detail(
    response_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed response analysis data by ID.

    Returns full response details including text, flags, and recommendation.
    """
    try:
        from uuid import UUID as PyUUID
        response_uuid = PyUUID(response_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid response ID format."
        )

    try:
        query = (
            select(ResponseAnalysis)
            .where(ResponseAnalysis.id == response_uuid, ResponseAnalysis.user_id == current_user.id)
        )
        result = await db.execute(query)
        response_analysis = result.scalar_one_or_none()

        if not response_analysis:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Response analysis not found."
            )

        return ResponseAnalysisDetail(
            id=response_analysis.id,
            response_text=response_analysis.response_text,
            clarity=response_analysis.clarity,
            confidence=float(response_analysis.confidence),
            flags=response_analysis.flags or [],
            recommendation=response_analysis.recommendation,
            scan_id=response_analysis.scan_id,
            allergens_checked=response_analysis.allergens_checked or [],
            created_at=response_analysis.created_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching response detail: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load response details."
        )


# ========================
# Delete Endpoints
# ========================

@router.delete("/history/{scan_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_scan(
    scan_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a scan and all associated dishes and response analyses.

    This permanently removes the scan from history.
    """
    try:
        from uuid import UUID as PyUUID
        scan_uuid = PyUUID(scan_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid scan ID format."
        )

    try:
        # Find the scan
        query = select(Scan).where(Scan.id == scan_uuid, Scan.user_id == current_user.id)
        result = await db.execute(query)
        scan = result.scalar_one_or_none()

        if not scan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Scan not found."
            )

        # Delete the scan (cascade will delete dishes and response analyses)
        await db.delete(scan)
        await db.commit()

        logger.info(f"User {current_user.id} deleted scan {scan_id}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting scan: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete scan."
        )


@router.delete("/responses/{response_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_response_analysis(
    response_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a response analysis from history.

    This permanently removes the response analysis.
    """
    try:
        from uuid import UUID as PyUUID
        response_uuid = PyUUID(response_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid response ID format."
        )

    try:
        # Find the response
        query = select(ResponseAnalysis).where(
            ResponseAnalysis.id == response_uuid,
            ResponseAnalysis.user_id == current_user.id
        )
        result = await db.execute(query)
        response_analysis = result.scalar_one_or_none()

        if not response_analysis:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Response analysis not found."
            )

        # Delete the response
        await db.delete(response_analysis)
        await db.commit()

        logger.info(f"User {current_user.id} deleted response analysis {response_id}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting response analysis: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete response analysis."
        )


@router.delete("/history", status_code=status.HTTP_204_NO_CONTENT)
async def clear_scan_history(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Clear all scan history for the current user.

    This permanently removes all scans, dishes, and response analyses.
    Use with caution.
    """
    try:
        from sqlalchemy import delete as sql_delete

        # First delete all response analyses (both linked and unlinked)
        await db.execute(
            sql_delete(ResponseAnalysis).where(ResponseAnalysis.user_id == current_user.id)
        )

        # Then delete all scans (cascade will delete dishes)
        await db.execute(
            sql_delete(Scan).where(Scan.user_id == current_user.id)
        )

        await db.commit()

        logger.info(f"User {current_user.id} cleared all scan history")

    except Exception as e:
        logger.error(f"Error clearing scan history: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clear scan history."
        )

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from uuid import UUID


# ========================
# Menu Analysis Schemas
# ========================

class MenuAnalysisRequest(BaseModel):
    """Request for menu text analysis."""
    menu_text: str = Field(..., min_length=1, max_length=50000, description="OCR extracted menu text (max 50KB)")
    user_allergens: List[str] = Field(..., min_length=1, max_length=50, description="List of user's allergen IDs")
    cuisine_hint: Optional[str] = Field(None, max_length=100, description="Optional cuisine type hint")


class DishAnalysis(BaseModel):
    """Analysis result for a single dish."""
    name: str
    description: Optional[str] = None
    risk_level: str = Field(..., pattern="^(low|medium|high)$")
    detected_allergens: List[str] = []
    confidence: float = Field(..., ge=0.0, le=1.0)
    notes: Optional[str] = None


class MenuAnalysisResponse(BaseModel):
    """Response from menu analysis."""
    scan_id: Optional[UUID] = None
    dishes: List[DishAnalysis]
    raw_text: str
    dish_count: int
    analyzed_at: datetime


# ========================
# Single Dish Analysis Schemas
# ========================

class DishAnalysisRequest(BaseModel):
    """Request for single dish analysis."""
    dish_name: str
    ingredients: Optional[str] = None
    user_allergens: List[str]


class DishAnalysisResponse(DishAnalysis):
    """Response for single dish analysis."""
    pass


# ========================
# Response Analysis Schemas
# ========================

class ResponseAnalysisRequest(BaseModel):
    """Request to analyze restaurant staff response."""
    response_text: str = Field(..., min_length=1, description="Staff's response text")
    user_allergens: List[str] = Field(..., description="User's allergen IDs")


class ResponseAnalysisResponse(BaseModel):
    """Analysis of staff response clarity."""
    clarity: str = Field(..., pattern="^(clear|unclear|dangerous)$")
    confidence: float = Field(..., ge=0.0, le=1.0)
    flags: List[str] = []  # Uncertainty indicators found
    recommendation: str
    analyzed_at: datetime


# ========================
# Scan History Schemas
# ========================

class ScanSummary(BaseModel):
    """Summary of a scan for history."""
    id: UUID
    dish_count: int
    avg_confidence: float
    created_at: datetime

    class Config:
        from_attributes = True


class ScanDetail(ScanSummary):
    """Detailed scan with dishes."""
    raw_text: str
    dishes: List[DishAnalysis]

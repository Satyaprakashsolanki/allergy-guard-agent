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


class AllergenBreakdown(BaseModel):
    """Detailed breakdown of why a specific allergen was flagged."""
    allergen_id: str
    allergen_name: str
    risk_level: str = Field(..., pattern="^(low|medium|high)$")
    source: str  # Where the allergen was detected (e.g., "mentioned in description", "hidden in sauce")
    reasoning: str  # Why this risk level was assigned


class DishAnalysis(BaseModel):
    """Analysis result for a single dish."""
    name: str
    description: Optional[str] = None
    risk_level: str = Field(..., pattern="^(low|medium|high)$")
    detected_allergens: List[str] = []
    confidence: float = Field(..., ge=0.0, le=1.0)
    notes: Optional[str] = None
    allergen_breakdown: Optional[List[AllergenBreakdown]] = None  # Itemized allergen analysis


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
    scan_id: Optional[UUID] = Field(None, description="Optional scan ID to link this response to")


class ResponseAnalysisResponse(BaseModel):
    """Analysis of staff response clarity."""
    id: Optional[UUID] = None  # ID for retrieving/linking this analysis
    clarity: str = Field(..., pattern="^(clear|unclear|dangerous)$")
    confidence: float = Field(..., ge=0.0, le=1.0)
    flags: List[str] = []  # Uncertainty indicators found
    recommendation: str
    analyzed_at: datetime
    scan_id: Optional[UUID] = None  # Link to originating scan if available


# ========================
# Scan History Schemas
# ========================

class ScanSummary(BaseModel):
    """Summary of a scan for history listing."""
    id: UUID
    dish_count: int
    avg_confidence: float
    cuisine_hint: Optional[str] = None
    allergens_used: List[str] = []
    created_at: datetime
    # Quick risk summary for display
    high_risk_count: int = 0
    medium_risk_count: int = 0
    low_risk_count: int = 0

    class Config:
        from_attributes = True


class ResponseAnalysisInScan(BaseModel):
    """Response analysis info embedded in scan detail."""
    id: UUID
    clarity: str
    confidence: float
    response_preview: str
    created_at: datetime

    class Config:
        from_attributes = True


class ScanDetail(BaseModel):
    """Detailed scan with full dish data - for viewing a specific scan."""
    id: UUID
    dish_count: int
    avg_confidence: float
    cuisine_hint: Optional[str] = None
    allergens_used: List[str] = []
    raw_text: str
    dishes: List[DishAnalysis]
    response_analyses: List[ResponseAnalysisInScan] = []  # Linked conversations
    created_at: datetime

    class Config:
        from_attributes = True


class ScanHistoryResponse(BaseModel):
    """Response for scan history list."""
    scans: List[ScanSummary]
    total_count: int
    page: int
    page_size: int


# ========================
# Response Analysis History Schemas
# ========================

class ResponseAnalysisSummary(BaseModel):
    """Summary of a response analysis for history listing."""
    id: UUID
    clarity: str
    confidence: float
    scan_id: Optional[UUID] = None
    allergens_checked: List[str] = []
    created_at: datetime
    # Preview of response text (truncated)
    response_preview: str

    class Config:
        from_attributes = True


class ResponseAnalysisDetail(BaseModel):
    """Detailed response analysis data."""
    id: UUID
    response_text: str
    clarity: str
    confidence: float
    flags: List[str] = []
    recommendation: Optional[str] = None
    scan_id: Optional[UUID] = None
    allergens_checked: List[str] = []
    created_at: datetime

    class Config:
        from_attributes = True


class ResponseHistoryResponse(BaseModel):
    """Response for response analysis history list."""
    responses: List[ResponseAnalysisSummary]
    total_count: int
    page: int
    page_size: int

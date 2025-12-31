"""Pydantic schemas for user preferences."""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field
from uuid import UUID
from enum import Enum


class RiskTolerance(str, Enum):
    """Risk tolerance levels for AI analysis."""
    CAUTIOUS = "cautious"    # Maximum warnings, flag even low-probability risks
    STANDARD = "standard"    # Balanced approach (default)
    RELAXED = "relaxed"      # Only flag high-probability risks


class DiningContext(str, Enum):
    """Default dining context for AI analysis."""
    RESTAURANT = "restaurant"  # Higher cross-contamination risk, can ask staff
    HOME = "home"              # User has control over ingredients
    TAKEOUT = "takeout"        # Can't easily ask questions, need detailed analysis
    TRAVEL = "travel"          # Unfamiliar environment, extra caution needed


class CuisineType(str, Enum):
    """Supported cuisine types for preferences."""
    AMERICAN = "american"
    CHINESE = "chinese"
    INDIAN = "indian"
    ITALIAN = "italian"
    JAPANESE = "japanese"
    KOREAN = "korean"
    MEXICAN = "mexican"
    THAI = "thai"
    VIETNAMESE = "vietnamese"
    MEDITERRANEAN = "mediterranean"
    FRENCH = "french"
    GREEK = "greek"
    MIDDLE_EASTERN = "middle_eastern"
    SPANISH = "spanish"
    OTHER = "other"


# ========================
# Request Schemas
# ========================

class PreferencesUpdate(BaseModel):
    """Schema for updating user preferences."""
    favorite_cuisines: Optional[List[str]] = Field(
        None,
        description="List of cuisine types the user frequently eats",
        max_length=10
    )
    risk_tolerance: Optional[RiskTolerance] = Field(
        None,
        description="User's risk tolerance level for AI analysis"
    )
    default_dining_context: Optional[DiningContext] = Field(
        None,
        description="User's default dining context"
    )


class PreferencesCreate(BaseModel):
    """Schema for creating user preferences (internal use)."""
    favorite_cuisines: List[str] = Field(default_factory=list)
    risk_tolerance: RiskTolerance = RiskTolerance.STANDARD
    default_dining_context: DiningContext = DiningContext.RESTAURANT


# ========================
# Response Schemas
# ========================

class PreferencesResponse(BaseModel):
    """Schema for preferences response."""
    id: UUID
    user_id: UUID
    favorite_cuisines: List[str]
    risk_tolerance: str
    default_dining_context: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ========================
# Constants for Frontend
# ========================

CUISINE_OPTIONS = [
    {"id": "american", "name": "American", "icon": "🍔"},
    {"id": "chinese", "name": "Chinese", "icon": "🥡"},
    {"id": "indian", "name": "Indian", "icon": "🍛"},
    {"id": "italian", "name": "Italian", "icon": "🍝"},
    {"id": "japanese", "name": "Japanese", "icon": "🍣"},
    {"id": "korean", "name": "Korean", "icon": "🍜"},
    {"id": "mexican", "name": "Mexican", "icon": "🌮"},
    {"id": "thai", "name": "Thai", "icon": "🍲"},
    {"id": "vietnamese", "name": "Vietnamese", "icon": "🍜"},
    {"id": "mediterranean", "name": "Mediterranean", "icon": "🥗"},
    {"id": "french", "name": "French", "icon": "🥐"},
    {"id": "greek", "name": "Greek", "icon": "🥙"},
    {"id": "middle_eastern", "name": "Middle Eastern", "icon": "🧆"},
    {"id": "spanish", "name": "Spanish", "icon": "🥘"},
    {"id": "other", "name": "Other", "icon": "🍽️"},
]

RISK_TOLERANCE_OPTIONS = [
    {
        "id": "cautious",
        "name": "Extra Cautious",
        "description": "Maximum warnings - flag even low-probability risks",
        "icon": "🛡️"
    },
    {
        "id": "standard",
        "name": "Standard",
        "description": "Balanced approach with reasonable warnings",
        "icon": "⚖️"
    },
    {
        "id": "relaxed",
        "name": "Relaxed",
        "description": "Only flag high-probability risks",
        "icon": "😌"
    },
]

DINING_CONTEXT_OPTIONS = [
    {
        "id": "restaurant",
        "name": "Restaurant",
        "description": "Dining in - can ask staff questions",
        "icon": "🍽️"
    },
    {
        "id": "home",
        "name": "Home Cooking",
        "description": "You control the ingredients",
        "icon": "🏠"
    },
    {
        "id": "takeout",
        "name": "Takeout/Delivery",
        "description": "Can't easily ask questions",
        "icon": "📦"
    },
    {
        "id": "travel",
        "name": "Traveling",
        "description": "Unfamiliar environment - extra caution",
        "icon": "✈️"
    },
]

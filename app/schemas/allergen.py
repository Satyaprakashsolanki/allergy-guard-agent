from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from uuid import UUID


# ========================
# Allergen Schemas
# ========================

class AllergenBase(BaseModel):
    """Base allergen schema."""
    id: str
    name: str
    icon: str


class AllergenResponse(AllergenBase):
    """Full allergen response with all metadata."""
    synonyms: List[str] = []
    hidden_sources: List[str] = []
    cuisine_patterns: Optional[dict] = None

    class Config:
        from_attributes = True


class AllergenList(BaseModel):
    """List of allergens."""
    allergens: List[AllergenResponse]


# ========================
# User Allergen Schemas
# ========================

class UserAllergenBase(BaseModel):
    """Base user allergen schema."""
    allergen_id: str
    severity: str = Field(default="severe", pattern="^(mild|moderate|severe)$")


class UserAllergenCreate(UserAllergenBase):
    """Schema for adding user allergen."""
    pass


class UserAllergenResponse(UserAllergenBase):
    """User allergen response."""
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


class UserAllergenWithDetails(UserAllergenResponse):
    """User allergen with full allergen details."""
    allergen: AllergenResponse


class UpdateUserAllergensRequest(BaseModel):
    """Request to update user's allergens."""
    allergens: List[UserAllergenCreate]


class UserAllergensResponse(BaseModel):
    """Response with list of user's allergens."""
    allergens: List[UserAllergenResponse]

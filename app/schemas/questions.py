from typing import Optional, List
from pydantic import BaseModel, Field


# ========================
# Question Template Schemas
# ========================

class QuestionTemplate(BaseModel):
    """A question template for restaurant staff."""
    id: str
    category: str
    question: str
    icon: str


class QuestionsResponse(BaseModel):
    """Response with list of question templates."""
    questions: List[QuestionTemplate]


# ========================
# Personalized Questions (Legacy - template based)
# ========================

class GenerateQuestionsRequest(BaseModel):
    """Request to generate personalized questions."""
    allergens: List[str] = Field(..., description="User's allergen IDs")
    dish_name: Optional[str] = Field(None, description="Specific dish to ask about")


class PersonalizedQuestion(BaseModel):
    """A personalized question for the user."""
    id: Optional[str] = None
    category: str
    question: str
    priority: str = Field(..., pattern="^(high|medium|low)$")
    reasoning: Optional[str] = None  # Why this question matters for the user's safety


class GenerateQuestionsResponse(BaseModel):
    """Response with personalized questions."""
    questions: List[PersonalizedQuestion]
    allergen_summary: str  # Summary of allergens for context


# ========================
# Smart AI Questions (Context-aware)
# ========================

class DishContext(BaseModel):
    """Dish analysis context from a menu scan."""
    name: str
    risk_level: str = Field(..., pattern="^(low|medium|high)$")
    detected_allergens: List[str] = []
    notes: Optional[str] = None


class UserAllergenWithSeverity(BaseModel):
    """User allergen with severity level."""
    allergen_id: str
    severity: str = Field(default="moderate", pattern="^(mild|moderate|severe)$")


class ScanContext(BaseModel):
    """Context from a menu scan for smart question generation."""
    dishes: List[DishContext] = Field(..., description="Analyzed dishes from scan")
    cuisine_hint: Optional[str] = Field(None, description="Detected cuisine type")
    raw_text: Optional[str] = Field(None, description="Original menu text")


class SmartQuestionsRequest(BaseModel):
    """Request for AI-powered context-aware questions."""
    scan_context: ScanContext = Field(..., description="Results from menu scan")
    user_allergens: List[UserAllergenWithSeverity] = Field(..., description="User's allergens with severity")


class SmartQuestion(BaseModel):
    """An AI-generated context-aware question."""
    id: Optional[str] = None
    category: str
    question: str
    priority: str = Field(..., pattern="^(high|medium|low)$")
    related_dish: Optional[str] = None  # Which dish this question is about
    reasoning: Optional[str] = None  # Why this question is important


class SmartQuestionsResponse(BaseModel):
    """Response with AI-generated smart questions."""
    questions: List[SmartQuestion]
    risk_summary: str  # AI-generated summary of overall risk
    critical_allergens: List[str] = []  # Allergens marked as severe
    most_concerning: List[str] = []  # Most concerning dishes/ingredients

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
# Personalized Questions
# ========================

class GenerateQuestionsRequest(BaseModel):
    """Request to generate personalized questions."""
    allergens: List[str] = Field(..., description="User's allergen IDs")
    dish_name: Optional[str] = Field(None, description="Specific dish to ask about")


class PersonalizedQuestion(BaseModel):
    """A personalized question for the user."""
    category: str
    question: str
    priority: str = Field(..., pattern="^(high|medium|low)$")


class GenerateQuestionsResponse(BaseModel):
    """Response with personalized questions."""
    questions: List[PersonalizedQuestion]
    allergen_summary: str  # Summary of allergens for context

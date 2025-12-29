"""Question template endpoints for restaurant staff communication."""

from fastapi import APIRouter, Depends
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.questions import (
    QuestionTemplate,
    QuestionsResponse,
    GenerateQuestionsRequest,
    GenerateQuestionsResponse,
    PersonalizedQuestion,
)
from app.services.seed_data import ALLERGENS_DATA

router = APIRouter()

# Pre-built question templates
QUESTION_TEMPLATES = [
    {
        "id": "general_contains",
        "category": "General",
        "question": "Does this dish contain any {allergens}?",
        "icon": "❓"
    },
    {
        "id": "cross_contact",
        "category": "Cross-Contact",
        "question": "Is this dish prepared in a separate area from dishes containing {allergens}?",
        "icon": "🍳"
    },
    {
        "id": "ingredients_check",
        "category": "Ingredients",
        "question": "Can you please check the full ingredients list for any {allergens} or derivatives?",
        "icon": "📋"
    },
    {
        "id": "hidden_sources",
        "category": "Hidden Sources",
        "question": "Does the sauce, oil, or seasoning used in this dish contain any {allergens}?",
        "icon": "🥫"
    },
    {
        "id": "cooking_equipment",
        "category": "Cooking Equipment",
        "question": "Is the cooking equipment (grill, fryer, utensils) shared with dishes containing {allergens}?",
        "icon": "🥘"
    },
    {
        "id": "chef_consultation",
        "category": "Chef Consultation",
        "question": "Could I speak with the chef about my severe {allergens} allergy to ensure my meal is prepared safely?",
        "icon": "👨‍🍳"
    },
    {
        "id": "modification",
        "category": "Modifications",
        "question": "Can this dish be prepared without {allergens}?",
        "icon": "✏️"
    },
    {
        "id": "fryer_shared",
        "category": "Cross-Contact",
        "question": "Is the fryer used for this dish also used for items containing {allergens}?",
        "icon": "🍟"
    }
]


def get_allergen_names(allergen_ids: list[str]) -> str:
    """Get comma-separated allergen names from IDs."""
    names = []
    for allergen_data in ALLERGENS_DATA:
        if allergen_data["id"] in allergen_ids:
            names.append(allergen_data["name"])
    return ", ".join(names) if names else "your allergens"


@router.get("", response_model=QuestionsResponse)
async def get_questions():
    """Get all question templates."""
    questions = [
        QuestionTemplate(
            id=q["id"],
            category=q["category"],
            question=q["question"],
            icon=q["icon"]
        )
        for q in QUESTION_TEMPLATES
    ]
    return QuestionsResponse(questions=questions)


@router.post("/generate", response_model=GenerateQuestionsResponse)
async def generate_questions(
    request: GenerateQuestionsRequest,
    current_user: User = Depends(get_current_user)
):
    """Generate personalized questions based on user's allergens."""
    allergen_names = get_allergen_names(request.allergens)

    # Get allergen data for hidden sources
    relevant_allergens = [
        a for a in ALLERGENS_DATA
        if a["id"] in request.allergens
    ]

    questions = []

    # Always include these high-priority questions
    questions.append(PersonalizedQuestion(
        category="General",
        question=f"Does this dish contain any {allergen_names}?",
        priority="high"
    ))

    questions.append(PersonalizedQuestion(
        category="Cross-Contact",
        question=f"Is this dish prepared separately from items containing {allergen_names}?",
        priority="high"
    ))

    # Add hidden sources question if relevant
    all_hidden_sources = []
    for allergen in relevant_allergens:
        all_hidden_sources.extend(allergen.get("hidden_sources", [])[:3])

    if all_hidden_sources:
        questions.append(PersonalizedQuestion(
            category="Hidden Sources",
            question=f"I have allergies to {allergen_names}. Can you check if any sauces, oils, or seasonings contain these? Some hidden sources include: {', '.join(all_hidden_sources[:5])}.",
            priority="high"
        ))

    # Add dish-specific question if dish name provided
    if request.dish_name:
        questions.append(PersonalizedQuestion(
            category="Specific Dish",
            question=f"For the {request.dish_name}, can you confirm it doesn't contain {allergen_names} or come into contact with them during preparation?",
            priority="high"
        ))

    # Add medium priority questions
    questions.append(PersonalizedQuestion(
        category="Cooking Equipment",
        question=f"Is the cooking equipment cleaned between uses, or is it shared with dishes containing {allergen_names}?",
        priority="medium"
    ))

    questions.append(PersonalizedQuestion(
        category="Chef Consultation",
        question=f"Could I speak with the chef about my severe allergy to {allergen_names}?",
        priority="medium"
    ))

    # Add modification option
    questions.append(PersonalizedQuestion(
        category="Modifications",
        question=f"Can this dish be prepared without any {allergen_names}?",
        priority="low"
    ))

    return GenerateQuestionsResponse(
        questions=questions,
        allergen_summary=f"You are avoiding: {allergen_names}"
    )

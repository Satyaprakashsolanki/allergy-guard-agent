"""Question template endpoints for restaurant staff communication."""

import logging
import uuid
from fastapi import APIRouter, Depends, HTTPException
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.questions import (
    QuestionTemplate,
    QuestionsResponse,
    GenerateQuestionsRequest,
    GenerateQuestionsResponse,
    PersonalizedQuestion,
    SmartQuestionsRequest,
    SmartQuestionsResponse,
    SmartQuestion,
)
from app.services.seed_data import ALLERGENS_DATA
from app.services.openai_service import generate_smart_questions, OpenAINotConfiguredError

logger = logging.getLogger(__name__)
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
        priority="high",
        reasoning=f"Direct confirmation is the first and most important step to identify if your allergens ({allergen_names}) are present in the dish."
    ))

    questions.append(PersonalizedQuestion(
        category="Cross-Contact",
        question=f"Is this dish prepared separately from items containing {allergen_names}?",
        priority="high",
        reasoning="Even allergen-free dishes can become unsafe if prepared on shared surfaces or with shared utensils. Cross-contact is a leading cause of allergic reactions."
    ))

    # Add hidden sources question if relevant
    all_hidden_sources = []
    for allergen in relevant_allergens:
        all_hidden_sources.extend(allergen.get("hidden_sources", [])[:3])

    if all_hidden_sources:
        hidden_sources_str = ', '.join(all_hidden_sources[:5])
        questions.append(PersonalizedQuestion(
            category="Hidden Sources",
            question=f"I have allergies to {allergen_names}. Can you check if any sauces, oils, or seasonings contain these? Some hidden sources include: {hidden_sources_str}.",
            priority="high",
            reasoning=f"Your allergens can hide in unexpected ingredients. Common hidden sources include: {hidden_sources_str}. Staff may not think to mention these unless asked directly."
        ))

    # Add dish-specific question if dish name provided
    if request.dish_name:
        questions.append(PersonalizedQuestion(
            category="Specific Dish",
            question=f"For the {request.dish_name}, can you confirm it doesn't contain {allergen_names} or come into contact with them during preparation?",
            priority="high",
            reasoning=f"Getting specific confirmation for '{request.dish_name}' ensures the staff checks this exact dish rather than giving a general response."
        ))

    # Add medium priority questions
    questions.append(PersonalizedQuestion(
        category="Cooking Equipment",
        question=f"Is the cooking equipment cleaned between uses, or is it shared with dishes containing {allergen_names}?",
        priority="medium",
        reasoning="Shared fryers, grills, and utensils can transfer allergen proteins even after visual cleaning. This is especially important for severe allergies."
    ))

    questions.append(PersonalizedQuestion(
        category="Chef Consultation",
        question=f"Could I speak with the chef about my severe allergy to {allergen_names}?",
        priority="medium",
        reasoning="The chef has the most detailed knowledge of ingredients and preparation. Direct communication reduces the risk of miscommunication through servers."
    ))

    # Add modification option
    questions.append(PersonalizedQuestion(
        category="Modifications",
        question=f"Can this dish be prepared without any {allergen_names}?",
        priority="low",
        reasoning="Some dishes can be safely modified by omitting or substituting allergenic ingredients. This gives you more menu options."
    ))

    return GenerateQuestionsResponse(
        questions=questions,
        allergen_summary=f"You are avoiding: {allergen_names}"
    )


@router.post("/smart", response_model=SmartQuestionsResponse)
async def generate_smart_questions_endpoint(
    request: SmartQuestionsRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Generate AI-powered context-aware questions based on scan results.

    This endpoint connects the menu scan analysis to personalized questions,
    making the app truly intelligent. It considers:
    - Specific dishes and their detected allergens
    - User's allergen severity levels
    - Cuisine-specific hidden sources
    - Cross-contamination risks
    """
    try:
        # Convert request to dict format for OpenAI service
        scan_context = {
            "dishes": [
                {
                    "name": dish.name,
                    "risk_level": dish.risk_level,
                    "detected_allergens": dish.detected_allergens,
                    "notes": dish.notes
                }
                for dish in request.scan_context.dishes
            ],
            "cuisine_hint": request.scan_context.cuisine_hint,
            "raw_text": request.scan_context.raw_text
        }

        user_allergens = [
            {"allergen_id": ua.allergen_id, "severity": ua.severity}
            for ua in request.user_allergens
        ]

        # Call AI service
        result = await generate_smart_questions(scan_context, user_allergens)

        # Transform to response format with unique IDs
        questions = [
            SmartQuestion(
                id=str(uuid.uuid4()),
                category=q.get("category", "General"),
                question=q.get("question", ""),
                priority=q.get("priority", "medium"),
                related_dish=q.get("related_dish"),
                reasoning=q.get("reasoning")
            )
            for q in result.get("questions", [])
        ]

        return SmartQuestionsResponse(
            questions=questions,
            risk_summary=result.get("risk_summary", "Please verify all ingredients with restaurant staff."),
            critical_allergens=result.get("critical_allergens", []),
            most_concerning=result.get("most_concerning", [])
        )

    except OpenAINotConfiguredError as e:
        logger.error(f"OpenAI not configured: {e}")
        raise HTTPException(
            status_code=503,
            detail="AI service is not available. Please try again later."
        )
    except Exception as e:
        logger.error(f"Error generating smart questions: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to generate questions. Please try again."
        )

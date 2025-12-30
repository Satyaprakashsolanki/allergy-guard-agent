"""OpenAI integration service for allergen analysis."""

import json
import logging
from typing import Optional
from openai import AsyncOpenAI

from app.config import get_settings
from app.services.seed_data import ALLERGENS_DATA

logger = logging.getLogger(__name__)
settings = get_settings()

# Initialize OpenAI client - REQUIRED for production
if not settings.OPENAI_API_KEY:
    if settings.ENVIRONMENT == "production":
        raise RuntimeError("OPENAI_API_KEY is required in production environment")
    else:
        logger.warning("OPENAI_API_KEY not configured - AI analysis will not be available")

client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else None


def get_allergen_synonyms(allergen_ids: list[str]) -> dict:
    """Get synonyms for given allergen IDs."""
    synonyms = {}
    for allergen_data in ALLERGENS_DATA:
        if allergen_data["id"] in allergen_ids:
            synonyms[allergen_data["id"]] = {
                "name": allergen_data["name"],
                "synonyms": allergen_data["synonyms"],
                "hidden_sources": allergen_data["hidden_sources"]
            }
    return synonyms


MENU_ANALYSIS_SYSTEM_PROMPT = """You are an expert allergen detection assistant helping people with food allergies make informed decisions.

CRITICAL RULES:
1. Be CONSERVATIVE - when uncertain, flag as potential risk
2. NEVER say a dish is "safe" or "guaranteed allergen-free"
3. Consider hidden sources and cross-contact risks
4. Return structured JSON only

RISK LEVELS:
- "high": Allergen definitely or very likely present
- "medium": Uncertain, ambiguous, or missing information (DEFAULT when unsure)
- "low": No detected allergens, but always mention verification is needed

Always include helpful notes explaining your reasoning."""


class OpenAINotConfiguredError(Exception):
    """Raised when OpenAI API key is not configured."""
    pass


def _is_section_header(line: str) -> bool:
    """Check if a line is likely a menu section header."""
    header_patterns = ['appetizer', 'entree', 'dessert', 'drink', 'beverage', 'side',
                      'lunch', 'dinner', 'breakfast', 'special', 'menu', 'price']
    line_lower = line.lower()
    return any(pattern in line_lower for pattern in header_patterns) and len(line.split()) <= 2


def _is_price_only(line: str) -> bool:
    """Check if a line is just a price."""
    return line.replace('$', '').replace('.', '').replace(',', '').isdigit()


def _extract_dishes_from_text(menu_text: str) -> list[str]:
    """Extract potential dish names from menu text."""
    lines = [line.strip() for line in menu_text.split('\n') if line.strip() and len(line.strip()) > 3]

    potential_dishes = [
        line for line in lines
        if not _is_price_only(line) and not _is_section_header(line)
    ]

    if not potential_dishes:
        return [menu_text[:100] + "..." if len(menu_text) > 100 else menu_text]

    return potential_dishes[:15]  # Limit to 15 dishes


def _check_allergens_in_text(dish_text: str, allergen_info: dict) -> list[str]:
    """Check for allergen keywords in dish text."""
    dish_lower = dish_text.lower()
    detected = []

    for allergen_id, info in allergen_info.items():
        allergen_name = info["name"].lower()
        synonyms = [s.lower() for s in info["synonyms"]]
        hidden_sources = [h.lower() for h in info["hidden_sources"]]

        # Check name, synonyms, and hidden sources
        all_terms = [allergen_name] + synonyms + hidden_sources
        if any(term in dish_lower for term in all_terms):
            detected.append(allergen_id)

    return detected


def rule_based_menu_analysis(menu_text: str, user_allergens: list[str]) -> dict:
    """
    Rule-based fallback analysis when OpenAI is unavailable.

    IMPORTANT: This is a CONSERVATIVE fallback that marks most items as 'medium' risk
    (requiring verification) because we cannot guarantee accuracy without AI analysis.
    """
    allergen_info = get_allergen_synonyms(user_allergens)
    potential_dishes = _extract_dishes_from_text(menu_text)

    dishes = []
    for dish_text in potential_dishes:
        detected_allergens = _check_allergens_in_text(dish_text, allergen_info)

        if detected_allergens:
            risk_level = "high"
            notes = f"⚠️ RULE-BASED ANALYSIS: Detected keywords for: {', '.join(detected_allergens)}. AI analysis unavailable - please verify all ingredients with restaurant staff."
        else:
            risk_level = "medium"  # Cannot confirm safety without AI
            notes = "⚠️ RULE-BASED ANALYSIS: No obvious allergen keywords found, but AI analysis unavailable. Verify ALL ingredients with restaurant staff before ordering."

        dishes.append({
            "name": dish_text[:80],
            "risk_level": risk_level,
            "detected_allergens": detected_allergens,
            "confidence": 0.3,  # Low confidence for rule-based
            "notes": notes
        })

    return {"dishes": dishes}


async def analyze_menu_text(
    menu_text: str,
    user_allergens: list[str],
    cuisine_hint: Optional[str] = None
) -> dict:
    """
    Analyze menu text for potential allergens using OpenAI.

    CRITICAL: Requires OpenAI API. Raises error if not configured.
    """
    if not client:
        logger.error("OpenAI client not available - cannot analyze menu")
        raise OpenAINotConfiguredError("OpenAI API is not configured. Please contact support.")

    allergen_info = get_allergen_synonyms(user_allergens)
    allergen_list = ", ".join([f"{a['name']} (also known as: {', '.join(a['synonyms'][:5])})"
                               for a in allergen_info.values()])

    user_prompt = f"""Analyze this menu text for allergens.

USER'S ALLERGENS: {allergen_list}
{f'CUISINE TYPE: {cuisine_hint}' if cuisine_hint else ''}

MENU TEXT:
{menu_text}

Return a JSON object with this exact structure:
{{
    "dishes": [
        {{
            "name": "dish name",
            "risk_level": "high|medium|low",
            "detected_allergens": ["allergen_id1", "allergen_id2"],
            "confidence": 0.0-1.0,
            "notes": "explanation of why this risk level"
        }}
    ]
}}

Important:
- detected_allergens should use these exact IDs: {list(allergen_info.keys())}
- When in doubt, use "medium" risk level
- Include notes explaining hidden sources or cross-contact risks"""

    try:
        response = await client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": MENU_ANALYSIS_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            response_format={"type": "json_object"}
        )

        result = json.loads(response.choices[0].message.content)
        return result

    except OpenAINotConfiguredError:
        raise  # Re-raise configuration errors
    except Exception as e:
        logger.error(f"OpenAI API error during menu analysis: {e}")
        # Re-raise the error - user should know AI analysis failed
        # Do NOT silently fall back - transparency is critical for safety
        raise RuntimeError(f"AI analysis failed: {str(e)}")


RESPONSE_ANALYSIS_SYSTEM_PROMPT = """You are an expert at analyzing restaurant staff responses about food allergens.

Your job is to detect:
1. UNCERTAINTY INDICATORS: "I think", "probably", "should be", "might", "maybe", "not sure", "I believe"
2. DANGEROUS DISMISSALS: "it's fine", "don't worry", "a little won't hurt"
3. CLEAR CONFIRMATIONS: Direct yes/no answers with specifics

CLARITY LEVELS:
- "clear": Direct, specific answer without uncertainty
- "unclear": Contains uncertainty indicators or vague language
- "dangerous": Dismissive or potentially dangerous response

Be CONSERVATIVE - when in doubt, mark as "unclear"."""


async def analyze_staff_response(
    response_text: str,
    user_allergens: list[str]
) -> dict:
    """
    Analyze restaurant staff response for clarity and safety.

    CRITICAL: Requires OpenAI API. Raises error if not configured.
    """
    if not client:
        logger.error("OpenAI client not available - cannot analyze response")
        raise OpenAINotConfiguredError("OpenAI API is not configured. Please contact support.")

    allergen_info = get_allergen_synonyms(user_allergens)
    allergen_names = ", ".join([a["name"] for a in allergen_info.values()])

    user_prompt = f"""Analyze this restaurant staff response about allergens.

USER'S ALLERGENS: {allergen_names}

STAFF RESPONSE:
"{response_text}"

Return a JSON object with this exact structure:
{{
    "clarity": "clear|unclear|dangerous",
    "confidence": 0.0-1.0,
    "flags": ["list of concerning phrases found"],
    "recommendation": "what the user should do next"
}}

Be conservative - if there's any uncertainty, mark as "unclear"."""

    try:
        response = await client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": RESPONSE_ANALYSIS_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            response_format={"type": "json_object"}
        )

        result = json.loads(response.choices[0].message.content)
        return result

    except OpenAINotConfiguredError:
        raise  # Re-raise configuration errors
    except Exception as e:
        logger.error(f"OpenAI API error during response analysis: {e}")
        # Re-raise the error - let the router handle it
        raise RuntimeError(f"AI analysis failed: {str(e)}")

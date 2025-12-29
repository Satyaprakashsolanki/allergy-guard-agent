"""OpenAI integration service for allergen analysis."""

import json
from typing import Optional
from openai import AsyncOpenAI

from app.config import get_settings
from app.services.seed_data import ALLERGENS_DATA

settings = get_settings()

# Initialize OpenAI client
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


async def analyze_menu_text(
    menu_text: str,
    user_allergens: list[str],
    cuisine_hint: Optional[str] = None
) -> dict:
    """
    Analyze menu text for potential allergens using OpenAI.

    CRITICAL: On any error, returns medium risk (insufficient info) - NEVER low risk.
    """
    if not client:
        # Fallback to rule-based detection if OpenAI not configured
        return await rule_based_menu_analysis(menu_text, user_allergens)

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

    except Exception as e:
        print(f"OpenAI API error: {e}")
        # CRITICAL: On error, return insufficient info - NEVER low risk
        return await rule_based_menu_analysis(menu_text, user_allergens)


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

    CRITICAL: On error, returns "unclear" - NEVER "clear".
    """
    if not client:
        return rule_based_response_analysis(response_text)

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

    except Exception as e:
        print(f"OpenAI API error: {e}")
        # CRITICAL: On error, return unclear - NEVER clear
        return rule_based_response_analysis(response_text)


# ========================
# Rule-based Fallbacks
# ========================

async def rule_based_menu_analysis(menu_text: str, user_allergens: list[str]) -> dict:
    """Simple rule-based allergen detection as fallback."""
    menu_lower = menu_text.lower()
    allergen_info = get_allergen_synonyms(user_allergens)

    # Simple dish splitting (by newline or common separators)
    potential_dishes = [d.strip() for d in menu_text.split('\n') if d.strip()]

    if not potential_dishes:
        potential_dishes = ["Menu Item"]

    dishes = []
    for dish_text in potential_dishes[:20]:  # Limit to 20 dishes
        dish_lower = dish_text.lower()
        detected = []

        for allergen_id, info in allergen_info.items():
            # Check for allergen name and synonyms
            check_terms = [info["name"].lower()] + [s.lower() for s in info["synonyms"]]
            for term in check_terms:
                if term in dish_lower or term in menu_lower:
                    if allergen_id not in detected:
                        detected.append(allergen_id)
                    break

        if detected:
            risk_level = "high"
            notes = f"Potential {', '.join(detected)} detected. Please verify with staff."
        else:
            risk_level = "medium"  # Default to medium when using fallback
            notes = "AI analysis unavailable. Please verify ingredients with restaurant staff."

        dishes.append({
            "name": dish_text[:100],
            "risk_level": risk_level,
            "detected_allergens": detected,
            "confidence": 0.5,  # Lower confidence for rule-based
            "notes": notes
        })

    return {"dishes": dishes}


def rule_based_response_analysis(response_text: str) -> dict:
    """Simple rule-based response analysis as fallback."""
    response_lower = response_text.lower()

    uncertainty_indicators = [
        "i think", "probably", "should be", "might", "maybe",
        "not sure", "i believe", "possibly", "likely"
    ]

    dangerous_indicators = [
        "it's fine", "don't worry", "a little won't hurt",
        "you'll be okay", "it's just a little"
    ]

    flags = []

    for indicator in uncertainty_indicators:
        if indicator in response_lower:
            flags.append(f"Uncertainty: '{indicator}'")

    for indicator in dangerous_indicators:
        if indicator in response_lower:
            flags.append(f"Concerning: '{indicator}'")

    if any("Concerning" in f for f in flags):
        clarity = "dangerous"
        recommendation = "This response is concerning. Do NOT eat this food without further verification."
    elif flags:
        clarity = "unclear"
        recommendation = "The response contains uncertain language. Ask for more specific confirmation."
    else:
        clarity = "unclear"  # Default to unclear for safety
        recommendation = "AI analysis unavailable. Please verify directly with restaurant staff."

    return {
        "clarity": clarity,
        "confidence": 0.5,
        "flags": flags,
        "recommendation": recommendation
    }

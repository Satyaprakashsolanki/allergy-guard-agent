"""Seed data for the 14 major allergens."""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.allergen import Allergen


# 14 Major Allergens with comprehensive data
ALLERGENS_DATA = [
    {
        "id": "peanuts",
        "name": "Peanuts",
        "icon": "🥜",
        "synonyms": [
            "groundnuts", "arachis oil", "monkey nuts", "earth nuts",
            "goober peas", "peanut butter", "peanut oil", "arachis hypogaea"
        ],
        "hidden_sources": [
            "Satay sauce", "Some curries (Thai, Indonesian)", "African stews",
            "Pad Thai", "Peanut oil (may be refined)", "Some salad dressings",
            "Egg rolls", "Marzipan (sometimes)", "Nougat", "Some ice creams",
            "Chili", "Baked goods", "Candy", "Energy bars"
        ],
        "cuisine_patterns": {
            "thai": "high_risk",
            "indonesian": "high_risk",
            "vietnamese": "medium_risk",
            "chinese": "medium_risk",
            "african": "high_risk"
        }
    },
    {
        "id": "treenuts",
        "name": "Tree Nuts",
        "icon": "🌰",
        "synonyms": [
            "almonds", "cashews", "walnuts", "pecans", "pistachios",
            "macadamia", "brazil nuts", "hazelnuts", "chestnuts",
            "pine nuts", "praline", "marzipan", "nougat", "gianduja"
        ],
        "hidden_sources": [
            "Pesto (pine nuts)", "Marzipan", "Praline", "Nougat",
            "Baklava", "Some cereals", "Mortadella", "Natural extracts",
            "Nut oils", "Nut butters", "Baked goods", "Ice cream",
            "Salads", "Desserts", "Energy bars"
        ],
        "cuisine_patterns": {
            "italian": "medium_risk",
            "middle_eastern": "high_risk",
            "indian": "medium_risk",
            "french": "medium_risk"
        }
    },
    {
        "id": "dairy",
        "name": "Dairy",
        "icon": "🥛",
        "synonyms": [
            "milk", "lactose", "casein", "whey", "cream", "butter",
            "cheese", "ghee", "yogurt", "lactalbumin", "lactoglobulin",
            "curds", "custard", "half-and-half", "sour cream"
        ],
        "hidden_sources": [
            "Bread and baked goods", "Processed meats", "Salad dressings",
            "Chocolate", "Caramel", "Nougat", "Some margarines",
            "Instant mashed potatoes", "Cream soups", "Sauces",
            "Non-dairy creamers (may contain casein)", "Some medications"
        ],
        "cuisine_patterns": {
            "italian": "high_risk",
            "french": "high_risk",
            "indian": "high_risk",
            "american": "high_risk"
        }
    },
    {
        "id": "eggs",
        "name": "Eggs",
        "icon": "🥚",
        "synonyms": [
            "albumin", "globulin", "lysozyme", "mayonnaise", "meringue",
            "ovalbumin", "ovomucin", "ovomucoid", "ovovitellin",
            "egg lecithin", "livetin", "vitellin"
        ],
        "hidden_sources": [
            "Pasta (fresh)", "Mayonnaise", "Meringue", "Marshmallows",
            "Meatballs and meatloaf", "Baked goods", "Breaded foods",
            "Egg wash on pastries", "Some wines (fining)", "Foam on coffee",
            "Some vaccines", "Hollandaise sauce", "Caesar dressing"
        ],
        "cuisine_patterns": {
            "french": "high_risk",
            "italian": "medium_risk",
            "american": "medium_risk",
            "japanese": "medium_risk"
        }
    },
    {
        "id": "wheat",
        "name": "Wheat/Gluten",
        "icon": "🌾",
        "synonyms": [
            "flour", "semolina", "durum", "spelt", "kamut", "einkorn",
            "farina", "graham", "bulgur", "couscous", "seitan",
            "gluten", "bread crumbs", "bran", "germ", "starch"
        ],
        "hidden_sources": [
            "Soy sauce", "Beer", "Imitation crab", "Processed meats",
            "Ice cream", "Marinades", "Salad dressings", "Soups",
            "Candy", "Modified food starch", "Hydrolyzed vegetable protein",
            "Some medications", "Communion wafers", "Play-Doh"
        ],
        "cuisine_patterns": {
            "italian": "high_risk",
            "chinese": "medium_risk",
            "japanese": "medium_risk",
            "american": "high_risk"
        }
    },
    {
        "id": "soy",
        "name": "Soy",
        "icon": "🫘",
        "synonyms": [
            "soya", "edamame", "tofu", "tempeh", "miso", "soy sauce",
            "soy lecithin", "soy protein", "textured vegetable protein",
            "soybean oil", "soy milk", "tamari"
        ],
        "hidden_sources": [
            "Vegetable oil", "Vegetable broth", "Processed foods",
            "Baked goods", "Canned tuna", "Cereals", "Infant formula",
            "Sauces", "Soups", "Low-fat peanut butter", "Meat alternatives"
        ],
        "cuisine_patterns": {
            "chinese": "high_risk",
            "japanese": "high_risk",
            "korean": "high_risk",
            "thai": "medium_risk"
        }
    },
    {
        "id": "fish",
        "name": "Fish",
        "icon": "🐟",
        "synonyms": [
            "cod", "salmon", "tuna", "bass", "flounder", "haddock",
            "halibut", "perch", "pike", "pollock", "snapper", "sole",
            "swordfish", "tilapia", "trout", "anchovies", "sardines"
        ],
        "hidden_sources": [
            "Worcestershire sauce", "Caesar salad dressing", "Caponata",
            "Fish sauce", "Asian dishes", "Some BBQ sauces",
            "Gelatin (sometimes)", "Imitation crab", "Omega-3 supplements"
        ],
        "cuisine_patterns": {
            "japanese": "high_risk",
            "thai": "high_risk",
            "vietnamese": "high_risk",
            "mediterranean": "medium_risk"
        }
    },
    {
        "id": "shellfish",
        "name": "Shellfish",
        "icon": "🦐",
        "synonyms": [
            "shrimp", "prawns", "crab", "lobster", "crayfish", "crawfish",
            "scampi", "langoustine", "krill"
        ],
        "hidden_sources": [
            "Fish sauce", "XO sauce", "Oyster sauce", "Bouillabaisse",
            "Fried rice (often)", "Pad Thai", "Spring rolls",
            "Glucosamine supplements", "Some calcium supplements"
        ],
        "cuisine_patterns": {
            "chinese": "high_risk",
            "thai": "high_risk",
            "japanese": "high_risk",
            "cajun": "high_risk"
        }
    },
    {
        "id": "sesame",
        "name": "Sesame",
        "icon": "🌱",
        "synonyms": [
            "tahini", "sesame oil", "sesame seeds", "halvah", "hummus",
            "benne seeds", "gingelly oil", "sesamol", "sesamolin"
        ],
        "hidden_sources": [
            "Hummus", "Bread and buns (on top)", "Falafel", "Sushi",
            "Salad dressings", "Margarine", "Some soaps and cosmetics",
            "Pasteli", "Asian dishes", "Middle Eastern cuisine"
        ],
        "cuisine_patterns": {
            "middle_eastern": "high_risk",
            "asian": "medium_risk",
            "japanese": "medium_risk",
            "korean": "medium_risk"
        }
    },
    {
        "id": "mustard",
        "name": "Mustard",
        "icon": "🟡",
        "synonyms": [
            "mustard seed", "mustard powder", "mustard oil", "mustard flour",
            "dijon", "yellow mustard", "brown mustard", "sinapis"
        ],
        "hidden_sources": [
            "Salad dressings", "Marinades", "Sauces", "Processed meats",
            "Curry powder", "Pickles", "Indian food", "BBQ sauce",
            "Mayonnaise (sometimes)", "Ketchup (sometimes)"
        ],
        "cuisine_patterns": {
            "indian": "high_risk",
            "french": "medium_risk",
            "american": "medium_risk"
        }
    },
    {
        "id": "celery",
        "name": "Celery",
        "icon": "🥬",
        "synonyms": [
            "celeriac", "celery salt", "celery seed", "celery powder",
            "celery root", "celery leaf"
        ],
        "hidden_sources": [
            "Stocks and broths", "Soups", "Stews", "Salads",
            "Bloody Mary mix", "Spice mixes", "Processed meats",
            "Stuffing", "Some seasonings"
        ],
        "cuisine_patterns": {
            "european": "medium_risk",
            "american": "medium_risk"
        }
    },
    {
        "id": "lupin",
        "name": "Lupin",
        "icon": "🌸",
        "synonyms": [
            "lupine", "lupin flour", "lupin seeds", "lupin beans",
            "lupini beans"
        ],
        "hidden_sources": [
            "Bread", "Pastries", "Pasta", "Some gluten-free products",
            "Mediterranean appetizers", "Beer (sometimes)"
        ],
        "cuisine_patterns": {
            "mediterranean": "medium_risk",
            "european": "medium_risk"
        }
    },
    {
        "id": "molluscs",
        "name": "Molluscs",
        "icon": "🦑",
        "synonyms": [
            "squid", "calamari", "octopus", "snails", "escargot",
            "clams", "mussels", "oysters", "scallops", "abalone"
        ],
        "hidden_sources": [
            "Oyster sauce", "Fish sauce", "Paella", "Bouillabaisse",
            "Some Asian dishes", "Sushi", "Seafood salads"
        ],
        "cuisine_patterns": {
            "chinese": "high_risk",
            "japanese": "high_risk",
            "french": "medium_risk",
            "spanish": "medium_risk"
        }
    },
    {
        "id": "sulphites",
        "name": "Sulphites",
        "icon": "🍷",
        "synonyms": [
            "sulphur dioxide", "sodium sulphite", "sodium bisulphite",
            "sodium metabisulphite", "potassium bisulphite",
            "E220", "E221", "E222", "E223", "E224", "E225", "E226", "E227", "E228"
        ],
        "hidden_sources": [
            "Wine", "Dried fruits", "Preserved vegetables",
            "Pickled foods", "Vinegar", "Grape juice", "Beer",
            "Some medications", "Processed potatoes", "Shrimp"
        ],
        "cuisine_patterns": {
            "general": "medium_risk"
        }
    }
]


async def seed_allergens(db: AsyncSession) -> None:
    """Seed the database with the 14 major allergens."""
    for allergen_data in ALLERGENS_DATA:
        # Check if allergen already exists
        result = await db.execute(
            select(Allergen).where(Allergen.id == allergen_data["id"])
        )
        existing = result.scalar_one_or_none()

        if not existing:
            allergen = Allergen(
                id=allergen_data["id"],
                name=allergen_data["name"],
                icon=allergen_data["icon"],
                synonyms=allergen_data["synonyms"],
                hidden_sources=allergen_data["hidden_sources"],
                cuisine_patterns=allergen_data.get("cuisine_patterns")
            )
            db.add(allergen)

    await db.commit()
    print("✅ Allergens seeded successfully")

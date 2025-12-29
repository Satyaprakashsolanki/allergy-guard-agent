# Pydantic Schemas
from app.schemas.user import (
    UserCreate,
    UserLogin,
    UserUpdate,
    UserResponse,
    UserWithAllergens,
    Token,
    TokenRefresh,
    AuthResponse,
)
from app.schemas.allergen import (
    AllergenResponse,
    AllergenList,
    UserAllergenCreate,
    UserAllergenResponse,
    UpdateUserAllergensRequest,
    UserAllergensResponse,
)
from app.schemas.analysis import (
    MenuAnalysisRequest,
    MenuAnalysisResponse,
    DishAnalysis,
    DishAnalysisRequest,
    DishAnalysisResponse,
    ResponseAnalysisRequest,
    ResponseAnalysisResponse,
    ScanSummary,
    ScanDetail,
)
from app.schemas.questions import (
    QuestionTemplate,
    QuestionsResponse,
    GenerateQuestionsRequest,
    GenerateQuestionsResponse,
)

__all__ = [
    # User
    "UserCreate",
    "UserLogin",
    "UserUpdate",
    "UserResponse",
    "UserWithAllergens",
    "Token",
    "TokenRefresh",
    "AuthResponse",
    # Allergen
    "AllergenResponse",
    "AllergenList",
    "UserAllergenCreate",
    "UserAllergenResponse",
    "UpdateUserAllergensRequest",
    "UserAllergensResponse",
    # Analysis
    "MenuAnalysisRequest",
    "MenuAnalysisResponse",
    "DishAnalysis",
    "DishAnalysisRequest",
    "DishAnalysisResponse",
    "ResponseAnalysisRequest",
    "ResponseAnalysisResponse",
    "ScanSummary",
    "ScanDetail",
    # Questions
    "QuestionTemplate",
    "QuestionsResponse",
    "GenerateQuestionsRequest",
    "GenerateQuestionsResponse",
]

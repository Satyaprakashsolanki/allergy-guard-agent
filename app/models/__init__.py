# Database Models
from app.models.user import User
from app.models.allergen import Allergen, UserAllergen
from app.models.scan import Scan, ScanDish

__all__ = ["User", "Allergen", "UserAllergen", "Scan", "ScanDish"]

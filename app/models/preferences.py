"""User Preferences model for context-aware AI analysis."""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class UserPreferences(Base):
    """
    User preferences model for storing context-aware settings.

    These preferences help the AI provide more personalized and relevant
    allergen analysis based on the user's eating habits and risk tolerance.
    """

    __tablename__ = "user_preferences"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)

    # Cuisine preferences - cuisines the user frequently eats
    # Stored as JSON array: ["thai", "indian", "italian", "chinese", "mexican"]
    favorite_cuisines = Column(JSON, default=list, nullable=False)

    # Risk tolerance level: "cautious", "standard", "relaxed"
    # - cautious: Maximum warnings, flag even low-probability risks
    # - standard: Balanced approach (default)
    # - relaxed: Only flag high-probability risks
    risk_tolerance = Column(String(20), default="standard", nullable=False)

    # Default dining context: "restaurant", "home", "takeout", "travel"
    # - restaurant: Higher cross-contamination risk, can ask staff
    # - home: User has control over ingredients
    # - takeout: Can't easily ask questions, need detailed analysis
    # - travel: Unfamiliar environment, extra caution needed
    default_dining_context = Column(String(20), default="restaurant", nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationship to user
    user = relationship("User", back_populates="preferences")

    def __repr__(self):
        return f"<UserPreferences user_id={self.user_id}>"

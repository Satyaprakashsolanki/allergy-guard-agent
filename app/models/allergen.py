import uuid
from datetime import datetime
from sqlalchemy import Column, String, ForeignKey, DateTime, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.core.database import Base


class Allergen(Base):
    """Allergen model - stores the 14 major allergens and their metadata."""

    __tablename__ = "allergens"

    id = Column(String(50), primary_key=True)  # e.g., 'peanuts', 'dairy'
    name = Column(String(100), nullable=False)  # Display name
    icon = Column(String(10), nullable=False)  # Emoji icon

    # JSON fields for flexible data
    synonyms = Column(JSONB, nullable=False, default=list)  # Alternative names
    hidden_sources = Column(JSONB, nullable=False, default=list)  # Common hidden sources
    cuisine_patterns = Column(JSONB, nullable=True)  # Cuisine-specific patterns

    # Relationships
    user_allergens = relationship("UserAllergen", back_populates="allergen")

    def __repr__(self):
        return f"<Allergen {self.id}: {self.name}>"


class UserAllergen(Base):
    """Junction table linking users to their allergens with severity."""

    __tablename__ = "user_allergens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    allergen_id = Column(String(50), ForeignKey("allergens.id", ondelete="CASCADE"), nullable=False)

    # Severity level: mild, moderate, severe
    severity = Column(String(20), nullable=False, default="severe")

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="allergens")
    allergen = relationship("Allergen", back_populates="user_allergens")

    # Constraints and indexes
    __table_args__ = (
        # Prevent duplicate allergen entries for same user
        UniqueConstraint('user_id', 'allergen_id', name='uq_user_allergen'),
        # Fast lookup by user
        Index('idx_user_allergens_user', 'user_id'),
        # Fast lookup by allergen (for analytics)
        Index('idx_user_allergens_allergen', 'allergen_id'),
        # Filter by severity
        Index('idx_user_allergens_severity', 'severity'),
    )

    def __repr__(self):
        return f"<UserAllergen user={self.user_id} allergen={self.allergen_id}>"

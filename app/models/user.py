import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class User(Base):
    """User model for authentication and profile management."""

    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=True)  # Nullable for OAuth users
    display_name = Column(String(100), nullable=False)

    # OAuth fields
    auth_provider = Column(String(20), default="email", nullable=False)  # "email", "google"
    google_id = Column(String(255), unique=True, nullable=True, index=True)
    profile_picture_url = Column(String(500), nullable=True)  # From Google profile

    # Account status
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)  # Auto-verified for Google users

    # Onboarding
    onboarding_complete = Column(Boolean, default=False, nullable=False)
    disclaimer_accepted_at = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    allergens = relationship("UserAllergen", back_populates="user", cascade="all, delete-orphan")
    scans = relationship("Scan", back_populates="user", cascade="all, delete-orphan")
    response_analyses = relationship("ResponseAnalysis", back_populates="user", cascade="all, delete-orphan")
    preferences = relationship("UserPreferences", back_populates="user", uselist=False, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User {self.email}>"

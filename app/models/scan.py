import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Text, ForeignKey, DateTime, Numeric
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.core.database import Base


class Scan(Base):
    """Scan model - stores menu scan data and metadata."""

    __tablename__ = "scans"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # OCR data
    raw_text = Column(Text, nullable=False)  # Extracted text from OCR
    dish_count = Column(Integer, nullable=False, default=0)
    avg_confidence = Column(Numeric(3, 2), nullable=False, default=0.0)  # OCR confidence

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="scans")
    dishes = relationship("ScanDish", back_populates="scan", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Scan {self.id} by user {self.user_id}>"


class ScanDish(Base):
    """Individual dish from a menu scan with allergen analysis."""

    __tablename__ = "scan_dishes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scan_id = Column(UUID(as_uuid=True), ForeignKey("scans.id", ondelete="CASCADE"), nullable=False)

    # Dish info
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Risk assessment
    risk_level = Column(String(20), nullable=False)  # low, medium, high
    detected_allergens = Column(JSONB, nullable=False, default=list)  # Array of allergen IDs
    confidence = Column(Numeric(3, 2), nullable=False, default=0.0)  # AI confidence

    # AI analysis
    notes = Column(Text, nullable=True)  # AI-generated notes/explanation

    # Relationships
    scan = relationship("Scan", back_populates="dishes")

    def __repr__(self):
        return f"<ScanDish {self.name} - {self.risk_level}>"

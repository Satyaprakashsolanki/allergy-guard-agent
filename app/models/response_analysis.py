"""Response Analysis model - stores staff response analysis for historical reference."""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, ForeignKey, DateTime, Numeric, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.core.database import Base


class ResponseAnalysis(Base):
    """
    Stores AI analysis of restaurant staff responses.

    This enables users to:
    - Review past safety conversations
    - Track patterns in restaurant staff responses
    - Build a history of verified safe/unsafe restaurants
    """

    __tablename__ = "response_analyses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Optional link to the scan that prompted these questions
    scan_id = Column(UUID(as_uuid=True), ForeignKey("scans.id", ondelete="SET NULL"), nullable=True)

    # The staff's response text
    response_text = Column(Text, nullable=False)

    # AI Analysis results
    clarity = Column(String(20), nullable=False)  # clear, unclear, dangerous
    confidence = Column(Numeric(3, 2), nullable=False, default=0.5)
    flags = Column(JSONB, nullable=False, default=list)  # Uncertainty indicators found
    recommendation = Column(Text, nullable=True)

    # Context at time of analysis
    allergens_checked = Column(JSONB, nullable=True, default=list)  # Which allergens were being verified

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="response_analyses")
    scan = relationship("Scan", back_populates="response_analyses")

    # Indexes for common queries
    __table_args__ = (
        Index('idx_response_analyses_user_created', 'user_id', 'created_at'),
        Index('idx_response_analyses_scan', 'scan_id'),
        Index('idx_response_analyses_clarity', 'clarity'),
    )

    def __repr__(self):
        return f"<ResponseAnalysis {self.id} clarity={self.clarity}>"

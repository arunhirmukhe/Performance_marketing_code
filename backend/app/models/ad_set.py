"""Ad Set model - represents ad sets within campaigns."""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Float, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base


class AdSet(Base):
    __tablename__ = "ad_sets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_id = Column(UUID(as_uuid=True), ForeignKey("campaigns.id"), nullable=False, index=True)
    platform_adset_id = Column(String(255))
    name = Column(String(255), nullable=False)
    targeting_type = Column(String(100))  # broad, interest, lookalike, retargeting
    status = Column(String(50), default="draft")
    daily_budget = Column(Float, default=0.0)
    bid_strategy = Column(String(100))
    targeting_spec = Column(JSON)  # Platform-specific targeting JSON
    age_min = Column(String(10))
    age_max = Column(String(10))
    genders = Column(String(50))
    placements = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    campaign = relationship("Campaign", back_populates="ad_sets")
    ads = relationship("Ad", back_populates="ad_set", cascade="all, delete-orphan")

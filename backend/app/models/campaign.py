"""Campaign model - represents ad campaigns on Meta/Google."""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Float, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base


class Campaign(Base):
    __tablename__ = "campaigns"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False, index=True)
    ad_account_id = Column(UUID(as_uuid=True), ForeignKey("ad_accounts.id"), nullable=False)
    platform_campaign_id = Column(String(255))  # ID from Meta/Google
    name = Column(String(255), nullable=False)
    platform = Column(String(50), nullable=False)  # "meta" or "google"
    objective = Column(String(100))  # e.g., "SALES", "CONVERSIONS"
    campaign_type = Column(String(100))  # prospecting, retargeting, scaling, testing
    status = Column(String(50), default="draft")  # draft, active, paused, completed, error
    daily_budget = Column(Float, default=0.0)
    lifetime_budget = Column(Float)
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    client = relationship("Client", back_populates="campaigns")
    ad_account = relationship("AdAccount", back_populates="campaigns")
    ad_sets = relationship("AdSet", back_populates="campaign", cascade="all, delete-orphan")
    daily_metrics = relationship("DailyMetrics", back_populates="campaign", cascade="all, delete-orphan")
    optimization_logs = relationship("OptimizationLog", back_populates="campaign", cascade="all, delete-orphan")

"""Daily Metrics model - stores daily performance data per campaign."""

import uuid
from datetime import datetime, date
from sqlalchemy import Column, String, Float, Integer, Date, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base


class DailyMetrics(Base):
    __tablename__ = "daily_metrics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False, index=True)
    campaign_id = Column(UUID(as_uuid=True), ForeignKey("campaigns.id"), index=True)
    platform = Column(String(50))  # meta, google, ga4
    date = Column(Date, nullable=False, index=True)

    # Performance Metrics
    spend = Column(Float, default=0.0)
    impressions = Column(Integer, default=0)
    clicks = Column(Integer, default=0)
    ctr = Column(Float, default=0.0)  # Click-through rate
    cpc = Column(Float, default=0.0)  # Cost per click
    cpm = Column(Float, default=0.0)  # Cost per mille

    # Conversion Metrics
    conversions = Column(Integer, default=0)
    conversion_value = Column(Float, default=0.0)
    revenue = Column(Float, default=0.0)
    roas = Column(Float, default=0.0)  # Return on ad spend
    cpa = Column(Float, default=0.0)  # Cost per acquisition

    # Engagement
    frequency = Column(Float, default=0.0)
    reach = Column(Integer, default=0)

    # GA4 specific
    sessions = Column(Integer, default=0)
    bounce_rate = Column(Float)

    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("client_id", "campaign_id", "platform", "date", name="uq_daily_metrics"),
    )

    # Relationships
    client = relationship("Client", back_populates="daily_metrics")
    campaign = relationship("Campaign", back_populates="daily_metrics")

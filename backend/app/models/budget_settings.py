"""Budget Settings model - stores budget allocation configuration per client."""

import uuid
from datetime import datetime
from sqlalchemy import Column, Float, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base


class BudgetSettings(Base):
    __tablename__ = "budget_settings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False, unique=True)

    # Monthly Budget
    monthly_cap = Column(Float, default=0.0)
    current_month_spend = Column(Float, default=0.0)

    # Allocation Percentages (should sum to 1.0)
    prospecting_pct = Column(Float, default=0.50)  # 50% default
    retargeting_pct = Column(Float, default=0.35)  # 35% default
    testing_pct = Column(Float, default=0.15)       # 15% default

    # Safety thresholds
    daily_spend_alert_pct = Column(Float, default=0.10)  # Alert if daily > 10% of monthly
    monthly_spend_alert_pct = Column(Float, default=0.90)  # Alert at 90% of cap

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    client = relationship("Client", back_populates="budget_settings")

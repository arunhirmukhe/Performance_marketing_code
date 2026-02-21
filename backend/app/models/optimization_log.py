"""Optimization Log model - tracks all automated actions taken."""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Float, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base


class OptimizationLog(Base):
    __tablename__ = "optimization_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False, index=True)
    campaign_id = Column(UUID(as_uuid=True), ForeignKey("campaigns.id"), index=True)

    action = Column(String(100), nullable=False)  # budget_increase, budget_decrease, pause, duplicate, etc.
    reason = Column(Text)  # Human-readable reason
    entity_type = Column(String(50))  # campaign, ad_set, ad
    entity_id = Column(String(255))  # Platform entity ID
    old_value = Column(String(255))
    new_value = Column(String(255))
    status = Column(String(50), default="completed")  # completed, failed, pending
    error_message = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    client = relationship("Client", back_populates="optimization_logs")
    campaign = relationship("Campaign", back_populates="optimization_logs")

"""Audience model - stores targeting audiences for campaigns."""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base


class Audience(Base):
    __tablename__ = "audiences"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False, index=True)
    platform = Column(String(50), nullable=False)  # "meta" or "google"
    audience_type = Column(String(100))  # custom, lookalike, interest, remarketing
    name = Column(String(255), nullable=False)
    platform_audience_id = Column(String(255))
    size = Column(Integer)
    description = Column(String(500))
    spec = Column(JSON)  # Audience specification details
    status = Column(String(50), default="active")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    client = relationship("Client", back_populates="audiences")

"""Creative model - stores ad creative assets."""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base


class Creative(Base):
    __tablename__ = "creatives"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    creative_type = Column(String(50))  # image, video, carousel
    media_url = Column(String(500))
    thumbnail_url = Column(String(500))
    headline = Column(String(255))
    body = Column(Text)
    cta = Column(String(100))  # e.g., "SHOP_NOW", "LEARN_MORE"
    platform_creative_id = Column(String(255))
    status = Column(String(50), default="active")  # active, fatigued, archived
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    client = relationship("Client", back_populates="creatives")
    ads = relationship("Ad", back_populates="creative")

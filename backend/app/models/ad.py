"""Ad model - represents individual ads within ad sets."""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base


class Ad(Base):
    __tablename__ = "ads"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ad_set_id = Column(UUID(as_uuid=True), ForeignKey("ad_sets.id"), nullable=False, index=True)
    creative_id = Column(UUID(as_uuid=True), ForeignKey("creatives.id"))
    platform_ad_id = Column(String(255))
    name = Column(String(255), nullable=False)
    status = Column(String(50), default="draft")  # draft, active, paused, rejected
    preview_url = Column(String(500))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    ad_set = relationship("AdSet", back_populates="ads")
    creative = relationship("Creative", back_populates="ads")

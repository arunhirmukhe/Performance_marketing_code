"""Ad Account model - stores connected Meta/Google ad accounts."""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base


class AdAccount(Base):
    __tablename__ = "ad_accounts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False, index=True)
    platform = Column(String(50), nullable=False)  # "meta" or "google"
    account_id = Column(String(255), nullable=False)  # Platform-specific account ID
    account_name = Column(String(255))
    access_token = Column(Text)  # Encrypted in production
    refresh_token = Column(Text)  # Encrypted in production
    token_expires_at = Column(DateTime)
    status = Column(String(50), default="connected")  # connected, disconnected, error
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    client = relationship("Client", back_populates="ad_accounts")
    campaigns = relationship("Campaign", back_populates="ad_account", cascade="all, delete-orphan")

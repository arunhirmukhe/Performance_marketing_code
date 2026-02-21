"""Client model - represents a business/brand using the platform."""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Float, Boolean, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base
import enum


class AutomationStatus(str, enum.Enum):
    INACTIVE = "inactive"
    DEPLOYING = "deploying"
    ACTIVE = "active"
    PAUSED = "paused"
    ERROR = "error"


class Client(Base):
    __tablename__ = "clients"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    company_name = Column(String(255), nullable=False)
    website = Column(String(500))
    country = Column(String(100), default="US")
    industry = Column(String(100))
    monthly_budget = Column(Float, default=0.0)
    currency = Column(String(10), default="USD")
    automation_status = Column(
        SAEnum(AutomationStatus), default=AutomationStatus.INACTIVE
    )
    is_active = Column(Boolean, default=True)

    # Ad Platform Credentials (Client-provided)
    meta_app_id = Column(String(100), nullable=True)
    meta_app_secret = Column(String(200), nullable=True)
    google_client_id = Column(String(200), nullable=True)
    google_client_secret = Column(String(200), nullable=True)
    google_developer_token = Column(String(200), nullable=True)
    ga4_property_id = Column(String(100), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="clients")
    ad_accounts = relationship("AdAccount", back_populates="client", cascade="all, delete-orphan")
    campaigns = relationship("Campaign", back_populates="client", cascade="all, delete-orphan")
    creatives = relationship("Creative", back_populates="client", cascade="all, delete-orphan")
    audiences = relationship("Audience", back_populates="client", cascade="all, delete-orphan")
    products = relationship("Product", back_populates="client", cascade="all, delete-orphan")
    daily_metrics = relationship("DailyMetrics", back_populates="client", cascade="all, delete-orphan")
    budget_settings = relationship("BudgetSettings", back_populates="client", uselist=False, cascade="all, delete-orphan")
    optimization_logs = relationship("OptimizationLog", back_populates="client", cascade="all, delete-orphan")

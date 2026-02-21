"""Application configuration loaded from environment variables."""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "FAGE - Fibonce Autonomous Growth Engine"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    API_PREFIX: str = "/api"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://fage_user:fage_password@localhost:5432/fage_db"
    DATABASE_URL_SYNC: str = "postgresql://fage_user:fage_password@localhost:5432/fage_db"

    # JWT Authentication
    JWT_SECRET_KEY: str = "change-this-to-a-secure-random-string"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # CORS
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173"

    # Meta / Facebook Ads
    META_APP_ID: Optional[str] = None
    META_APP_SECRET: Optional[str] = None
    META_REDIRECT_URI: str = "http://localhost:8000/api/ad-accounts/meta/callback"

    # Google Ads
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    GOOGLE_DEVELOPER_TOKEN: Optional[str] = None
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/ad-accounts/google/callback"

    # Google Analytics 4
    GA4_PROPERTY_ID: Optional[str] = None

    # Redis (for future Celery)
    REDIS_URL: str = "redis://localhost:6379/0"

    # Alerts - Email
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    ALERT_FROM_EMAIL: str = "alerts@fibonce.com"
    ALERT_TO_EMAILS: str = ""

    # Alerts - Slack
    SLACK_WEBHOOK_URL: Optional[str] = None

    # Optimization Defaults
    DEFAULT_ROAS_THRESHOLD: float = 3.0
    DEFAULT_CPA_THRESHOLD: float = 50.0
    DEFAULT_CTR_THRESHOLD: float = 0.008  # 0.8%
    DEFAULT_FREQUENCY_THRESHOLD: float = 3.0
    BUDGET_INCREASE_PCT: float = 0.20  # 20%
    BUDGET_DECREASE_PCT: float = 0.15  # 15%

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

"""
Configuration management for Rainmaker
"""

from pydantic import SecretStr
from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    """Application settings"""
    
    # Database
    TIDB_URL: str = "sqlite+aiosqlite:///./rainmaker.db"  # Default to SQLite for development
    TIDB_HOST: Optional[str] = None
    TIDB_PORT: int = 4000
    TIDB_USER: Optional[str] = None
    TIDB_PASSWORD: Optional[SecretStr] = None
    TIDB_DATABASE: str = "rainmaker"
    REDIS_URL: str = "redis://localhost:6379"
    
    @property
    def tidb_url(self) -> str:
        """Construct TiDB URL from components if provided, otherwise use TIDB_URL"""
        if self.TIDB_HOST and self.TIDB_USER and self.TIDB_PASSWORD:
            password = self.TIDB_PASSWORD.get_secret_value()
            return f"mysql+aiomysql://{self.TIDB_USER}:{password}@{self.TIDB_HOST}:{self.TIDB_PORT}/{self.TIDB_DATABASE}?ssl=true"
        return self.TIDB_URL
    
    # External APIs
    OPENAI_API_KEY: SecretStr
    SONAR_API_KEY: Optional[SecretStr] = None
    SENDGRID_API_KEY: Optional[SecretStr] = None
    CLEARBIT_API_KEY: Optional[SecretStr] = None
    GOOGLE_CALENDAR_CREDENTIALS: Optional[SecretStr] = None
    LINKEDIN_API_KEY: Optional[SecretStr] = None
    
    # AWS
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[SecretStr] = None
    AWS_S3_BUCKET: Optional[str] = None
    AWS_REGION: str = "us-west-2"
    
    # Email Configuration
    EMAIL_ADDRESS: Optional[str] = None
    EMAIL_PASSWORD: Optional[SecretStr] = None
    SMTP_SERVER: Optional[str] = None
    IMAP_SERVER: Optional[str] = None
    TEST_RECIPIENT_EMAIL: Optional[str] = None
    
    # Feature Flags
    ENABLE_AUTOMATIC_OUTREACH: bool = False
    REQUIRE_HUMAN_APPROVAL: bool = True
    
    # Rate Limiting
    MAX_PROSPECTS_PER_DAY: int = 50
    MAX_OUTREACH_PER_HOUR: int = 25
    
    # JWT Authentication
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours
    
    # Application
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Rainmaker"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Create global settings instance
settings = Settings()
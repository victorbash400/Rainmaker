"""
Configuration management for Rainmaker
"""

from pydantic import SecretStr
from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    """Application settings"""
    
    # Database - TiDB Serverless only (no SQLite fallback)
    # TIDB_URL: str = "sqlite+aiosqlite:///./rainmaker.db"  # Commented out - TiDB only
    TIDB_HOST: str  # Required - no default, will fail if not provided
    TIDB_PORT: int = 4000
    TIDB_USER: str  # Required - no default, will fail if not provided  
    TIDB_PASSWORD: SecretStr  # Required - no default, will fail if not provided
    TIDB_DATABASE: str = "github_sample"  # Default to your current database
    REDIS_URL: str = "redis://localhost:6379"
    
    @property
    def tidb_url(self) -> str:
        """Construct TiDB URL - TiDB Serverless only, no fallback"""
        if not self.TIDB_HOST or not self.TIDB_USER or not self.TIDB_PASSWORD:
            raise ValueError("TiDB credentials are required! Please set TIDB_HOST, TIDB_USER, and TIDB_PASSWORD in your .env file")
        
        password = self.TIDB_PASSWORD.get_secret_value()
        return f"mysql+pymysql://{self.TIDB_USER}:{password}@{self.TIDB_HOST}:{self.TIDB_PORT}/{self.TIDB_DATABASE}"
    
    # External APIs - NO OPENAI (using Google Vertex AI)
    SONAR_API_KEY: Optional[SecretStr] = None
    SENDGRID_API_KEY: Optional[SecretStr] = None
    CLEARBIT_API_KEY: Optional[SecretStr] = None
    GOOGLE_CALENDAR_CREDENTIALS: Optional[SecretStr] = None
    LINKEDIN_API_KEY: Optional[SecretStr] = None
    GOOGLE_APPLICATION_CREDENTIALS: Optional[str] = None
    GOOGLE_SERVICE_ACCOUNT_FILE: str = r"C:\Users\Victo\Desktop\Rainmaker\Rainmaker-backend\ascendant-woods-462020-n0-78d818c9658e.json"  # Required path to service account
    GOOGLE_CLOUD_PROJECT: Optional[str] = None
    GOOGLE_CLOUD_LOCATION: Optional[str] = None
    
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
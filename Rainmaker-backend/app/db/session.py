"""
Database session management with TiDB Serverless support
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import NullPool
from app.core.config import settings
import logging
import ssl
import os

logger = logging.getLogger(__name__)

# TiDB Serverless optimized connection settings
def get_engine_config():
    """Get engine configuration optimized for TiDB Serverless"""
    base_config = {
        "echo": settings.DEBUG,
        "pool_pre_ping": True,
        "pool_recycle": 3600,  # 1 hour for TiDB Serverless
    }
    
    # TiDB Serverless specific optimizations
    if "tidbcloud.com" in settings.tidb_url:
        cert_path = os.path.abspath("isrgrootx1.pem")
        
        base_config.update({
            "poolclass": NullPool,  # Use NullPool for serverless
            "connect_args": {
                "charset": "utf8mb4",
                "ssl_ca": cert_path,
                "ssl_verify_cert": True,
                "ssl_verify_identity": True,
            }
        })
        logger.info(f"Configured engine for TiDB Serverless with SSL cert: {cert_path}")
    else:
        # Local development settings
        base_config.update({
            "pool_size": 5,
            "max_overflow": 0,
        })
        logger.info("Configured engine for local development")
    
    return base_config

# Create synchronous engine with optimized settings
engine = create_engine(
    settings.tidb_url,
    **get_engine_config()
)

# Create session factory
SessionLocal = sessionmaker(
    bind=engine,
    expire_on_commit=False,
)

# Create declarative base
Base = declarative_base()


def get_db():
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_connection():
    """Test database connectivity"""
    try:
        from sqlalchemy import text
        with SessionLocal() as session:
            result = session.execute(text("SELECT 1"))
            result.fetchone()
            logger.info("Database connection test successful")
            return True
    except Exception as e:
        logger.error(f"Database connection test failed: {e}")
        return False


def close_db():
    """Close database connections"""
    engine.dispose()
    logger.info("Database connections closed")
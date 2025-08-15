"""
Database session management with TiDB Serverless support
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import QueuePool
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

# TiDB Serverless optimized connection settings
def get_engine_config():
    """Get engine configuration optimized for TiDB Serverless"""
    base_config = {
        "echo": settings.DEBUG,
        "future": True,
        "pool_pre_ping": True,
        "pool_recycle": 3600,  # 1 hour for TiDB Serverless
    }
    
    # TiDB Serverless specific optimizations
    if "tidbcloud.com" in settings.tidb_url:
        base_config.update({
            "poolclass": QueuePool,
            "pool_size": 5,  # Conservative for serverless
            "max_overflow": 10,
            "pool_timeout": 30,
            "pool_recycle": 1800,  # 30 minutes for serverless
            "connect_args": {
                "connect_timeout": 10,
                "read_timeout": 30,
                "write_timeout": 30,
            }
        })
        logger.info("Configured engine for TiDB Serverless")
    else:
        # Local development settings
        base_config.update({
            "pool_size": 5,
            "max_overflow": 0,
        })
        logger.info("Configured engine for local development")
    
    return base_config

# Create async engine with optimized settings
engine = create_async_engine(
    settings.tidb_url,
    **get_engine_config()
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Create declarative base
Base = declarative_base()


async def get_db() -> AsyncSession:
    """Dependency to get database session"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def test_connection():
    """Test database connectivity"""
    try:
        from sqlalchemy import text
        async with AsyncSessionLocal() as session:
            result = await session.execute(text("SELECT 1"))
            result.fetchone()
            logger.info("Database connection test successful")
            return True
    except Exception as e:
        logger.error(f"Database connection test failed: {e}")
        return False


async def close_db():
    """Close database connections"""
    await engine.dispose()
    logger.info("Database connections closed")
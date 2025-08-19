"""
Migrate data from SQLite to TiDB Serverless
Run from Rainmaker-backend: python migrate_to_tidb.py
"""

import sys
from pathlib import Path
from sqlalchemy import create_engine, text, MetaData, Table
from sqlalchemy.orm import sessionmaker
import logging

# Add app directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from app.core.config import settings
from app.db.models import *
from app.db.session import Base

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_sqlite_engine():
    """Create SQLite engine for source database"""
    sqlite_url = "sqlite:///./rainmaker.db"
    engine = create_engine(sqlite_url, echo=False)
    return engine

def create_tidb_engine():
    """Create TiDB engine for destination database"""
    # Use the same engine configuration as our session.py
    from app.db.session import engine
    logger.info(f"Using configured TiDB engine")
    return engine

def check_sqlite_data(sqlite_engine):
    """Check what data exists in SQLite"""
    logger.info("📊 Checking SQLite database contents...")
    
    with sqlite_engine.connect() as conn:
        # Get all tables
        result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
        tables = [row[0] for row in result.fetchall()]
        
        if not tables:
            logger.warning("❌ No tables found in SQLite database")
            return False
            
        logger.info(f"✅ Found {len(tables)} tables: {', '.join(tables)}")
        
        # Check row counts
        total_rows = 0
        for table in tables:
            if not table.startswith('sqlite_'):  # Skip SQLite system tables
                try:
                    result = conn.execute(text(f"SELECT COUNT(*) FROM `{table}`"))
                    count = result.fetchone()[0]
                    if count > 0:
                        logger.info(f"  📋 {table}: {count} rows")
                        total_rows += count
                    else:
                        logger.info(f"  📋 {table}: empty")
                except Exception as e:
                    logger.warning(f"  ❌ {table}: error reading ({e})")
        
        if total_rows == 0:
            logger.warning("⚠️ All tables are empty - nothing to migrate")
            return False
            
        logger.info(f"✅ Total rows to migrate: {total_rows}")
        return True

def create_tidb_tables(tidb_engine):
    """Create tables in TiDB using SQLAlchemy models"""
    logger.info("🏗️ Creating TiDB tables...")
    
    try:
        # Create all tables
        Base.metadata.create_all(bind=tidb_engine)
        logger.info("✅ TiDB tables created successfully")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to create TiDB tables: {e}")
        return False

def migrate_table_data(sqlite_engine, tidb_engine, table_name):
    """Migrate data from one table"""
    logger.info(f"🚚 Migrating table: {table_name}")
    
    try:
        # Create sessions
        SqliteSession = sessionmaker(bind=sqlite_engine)
        TiDBSession = sessionmaker(bind=tidb_engine)
        
        with SqliteSession() as sqlite_session, TiDBSession() as tidb_session:
            # Get table metadata
            metadata = MetaData()
            metadata.reflect(bind=sqlite_engine)
            
            if table_name not in metadata.tables:
                logger.warning(f"⚠️ Table {table_name} not found in SQLite")
                return False
            
            table = metadata.tables[table_name]
            
            # Read all data from SQLite
            result = sqlite_session.execute(table.select())
            rows = result.fetchall()
            
            if not rows:
                logger.info(f"  📋 {table_name}: empty table, skipping")
                return True
            
            # Insert data into TiDB
            insert_stmt = table.insert()
            
            # Convert rows to dictionaries
            row_dicts = []
            for row in rows:
                row_dict = {}
                for i, column in enumerate(table.columns):
                    row_dict[column.name] = row[i]
                row_dicts.append(row_dict)
            
            # Batch insert
            tidb_session.execute(insert_stmt, row_dicts)
            tidb_session.commit()
            
            logger.info(f"  ✅ {table_name}: migrated {len(rows)} rows")
            return True
            
    except Exception as e:
        logger.error(f"  ❌ {table_name}: migration failed - {e}")
        return False

def verify_migration(tidb_engine):
    """Verify data was migrated correctly"""
    logger.info("🔍 Verifying migration...")
    
    try:
        TiDBSession = sessionmaker(bind=tidb_engine)
        with TiDBSession() as session:
            # Check key tables
            tables_to_check = ['prospects', 'campaigns', 'conversations', 'messages', 'proposals', 'users']
            
            total_rows = 0
            for table_name in tables_to_check:
                try:
                    result = session.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                    count = result.fetchone()[0]
                    if count > 0:
                        logger.info(f"  ✅ {table_name}: {count} rows")
                        total_rows += count
                    else:
                        logger.info(f"  📋 {table_name}: empty")
                except Exception as e:
                    logger.info(f"  ⚠️ {table_name}: table may not exist")
            
            logger.info(f"✅ Total rows in TiDB: {total_rows}")
            return True
            
    except Exception as e:
        logger.error(f"❌ Verification failed: {e}")
        return False

def main():
    """Main migration process"""
    logger.info("🚀 Starting SQLite to TiDB migration...")
    logger.info("=" * 60)
    
    # Step 1: Check SQLite data
    sqlite_engine = create_sqlite_engine()
    if not check_sqlite_data(sqlite_engine):
        logger.error("❌ No data to migrate from SQLite")
        return False
    
    # Step 2: Connect to TiDB
    try:
        tidb_engine = create_tidb_engine()
        logger.info("✅ Connected to TiDB Serverless")
    except Exception as e:
        logger.error(f"❌ Failed to connect to TiDB: {e}")
        return False
    
    # Step 3: Create TiDB tables
    if not create_tidb_tables(tidb_engine):
        return False
    
    # Step 4: Migrate data
    logger.info("🚚 Starting data migration...")
    
    # Get tables from SQLite
    metadata = MetaData()
    metadata.reflect(bind=sqlite_engine)
    
    success_count = 0
    total_tables = 0
    
    for table_name in metadata.tables.keys():
        if not table_name.startswith('sqlite_'):  # Skip SQLite system tables
            total_tables += 1
            if migrate_table_data(sqlite_engine, tidb_engine, table_name):
                success_count += 1
    
    # Step 5: Verify migration
    logger.info("=" * 60)
    if success_count == total_tables and verify_migration(tidb_engine):
        logger.info("🎉 Migration completed successfully!")
        logger.info(f"✅ Migrated {success_count}/{total_tables} tables")
        logger.info("🔗 Your data is now in TiDB Serverless")
        return True
    else:
        logger.error(f"❌ Migration incomplete: {success_count}/{total_tables} tables migrated")
        return False

if __name__ == "__main__":
    success = main()
    if not success:
        sys.exit(1)
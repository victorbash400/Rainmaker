"""
Test which database the application is currently using
"""
import sys
from pathlib import Path

# Add app directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from app.core.config import settings
from app.db.session import SessionLocal
from sqlalchemy import text

def test_current_database():
    """Test which database the application is currently configured to use"""
    
    print("🔍 CHECKING CURRENT DATABASE CONFIGURATION")
    print("=" * 60)
    
    # Check configuration
    print("1. Configuration Check:")
    print(f"   TIDB_HOST: {settings.TIDB_HOST}")
    print(f"   TIDB_USER: {settings.TIDB_USER}")
    print(f"   TIDB_DATABASE: {settings.TIDB_DATABASE}")
    print(f"   TIDB_PASSWORD: {'***' if settings.TIDB_PASSWORD else 'Not set'}")
    
    # Check constructed URL
    print(f"\n2. Database URL:")
    tidb_url = settings.tidb_url
    # Hide password in output
    safe_url = tidb_url.replace(settings.TIDB_PASSWORD.get_secret_value(), "***") if settings.TIDB_PASSWORD else tidb_url
    print(f"   {safe_url}")
    
    # Test actual connection
    print(f"\n3. Connection Test:")
    try:
        with SessionLocal() as session:
            # Get database info
            result = session.execute(text("SELECT VERSION() as version, DATABASE() as db"))
            row = result.fetchone()
            
            if row:
                version = row[0]
                database = row[1]
                
                if "TiDB" in version:
                    print(f"   ✅ Connected to TiDB!")
                    print(f"   ✅ Version: {version}")
                    print(f"   ✅ Database: {database}")
                    
                    # Test if we can see migrated data
                    result = session.execute(text("SELECT COUNT(*) FROM users"))
                    user_count = result.fetchone()[0]
                    print(f"   ✅ Users in database: {user_count}")
                    
                    result = session.execute(text("SELECT COUNT(*) FROM campaign_plans"))
                    campaign_count = result.fetchone()[0]
                    print(f"   ✅ Campaign plans in database: {campaign_count}")
                    
                    return True
                else:
                    print(f"   ❌ Connected to: {version}")
                    print(f"   ❌ Database: {database}")
                    print(f"   ⚠️  This appears to be SQLite, not TiDB!")
                    return False
            else:
                print("   ❌ No response from database")
                return False
                
    except Exception as e:
        print(f"   ❌ Connection failed: {e}")
        return False

if __name__ == "__main__":
    success = test_current_database()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 SUCCESS: Your application is using TiDB Serverless!")
        print("✅ All data operations will now use TiDB instead of SQLite.")
    else:
        print("❌ ISSUE: Your application is still using SQLite.")
        print("💡 Check your .env file configuration.")
"""
Test TiDB Serverless connection.
Run from Rainmaker-backend: python test_tidb_connection.py
"""

import sys
from pathlib import Path
from sqlalchemy import text
from app.core.config import settings
from app.db.session import SessionLocal, test_connection, close_db

# Add app directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

def check_config():
    """Check if the configuration is set up for TiDB."""
    print("1. Verifying configuration...")
    if not settings.TIDB_HOST:
        print("❌ TIDB_HOST is not set in your .env file.")
        return False
    if "tidbcloud.com" not in settings.TIDB_HOST:
        print(f"⚠️ WARNING: TIDB_HOST '{settings.TIDB_HOST}' does not look like a TiDB Cloud address.")
    print(f"✅ Configuration check passed (Host: {settings.TIDB_HOST}).")
    return True

def check_connection():
    """Test the basic database connection."""
    print("\n2. Testing database connection...")
    try:
        result = test_connection()
        if result:
            print("✅ Database connection successful.")
            return True
        else:
            print("❌ Database connection failed.")
            return False
    except Exception as e:
        print(f"❌ An error occurred during connection test: {e}")
        return False

def check_basic_query():
    """Test a simple query to get version and database name."""
    print("\n3. Running basic query...")
    try:
        with SessionLocal() as session:
            result = session.execute(text("SELECT VERSION() as version, DATABASE() as db"))
            row = result.fetchone()
            if not row:
                print("❌ Basic query failed: No rows returned.")
                return False
            print(f"✅ TiDB Version: {row.version}")
            print(f"✅ Database: {row.db}")
            return True
    except Exception as e:
        print(f"❌ Basic query failed: {e}")
        return False

def check_vector_support():
    """Check if the database supports vector operations."""
    print("\n4. Checking for vector support...")
    try:
        with SessionLocal() as session:
            session.execute(text("CREATE TABLE IF NOT EXISTS _gemini_test_vector (v VECTOR(3))"))
            session.execute(text("DROP TABLE _gemini_test_vector"))
            session.commit()
            print("✅ Vector type is supported.")
            return True
    except Exception as e:
        # Check if the error is about vector type not being supported
        if "type not supported" in str(e).lower() or "Unknown data type" in str(e):
             print("❌ Vector type is not supported on this TiDB version.")
        else:
            print(f"❌ Vector check failed with an unexpected error: {e}")
        return False

def main():
    """Run all TiDB connection tests."""
    print("🚀 Starting TiDB Serverless connection test...")
    print("=" * 50)

    tests = [
        check_config,
        check_connection,
        check_basic_query,
        check_vector_support,
    ]

    all_passed = True
    for test_func in tests:
        if not test_func():
            all_passed = False
            break

    print("=" * 50)
    if all_passed:
        print("🎉 All tests passed! Your connection is correctly configured.")
    else:
        print("❌ One or more tests failed. Please review the output above.")
    
    # Clean up database connections
    close_db()

if __name__ == "__main__":
    main()
"""
Test that the application fails properly without TiDB credentials (no SQLite fallback)
"""
import os
import sys
from pathlib import Path

# Add app directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

def test_no_fallback():
    """Test that the application fails without TiDB credentials"""
    
    print("🔍 TESTING NO FALLBACK TO SQLITE")
    print("=" * 50)
    
    # Temporarily remove TiDB credentials
    original_host = os.environ.get('TIDB_HOST')
    original_user = os.environ.get('TIDB_USER')
    original_password = os.environ.get('TIDB_PASSWORD')
    
    try:
        # Remove credentials
        if 'TIDB_HOST' in os.environ:
            del os.environ['TIDB_HOST']
        if 'TIDB_USER' in os.environ:
            del os.environ['TIDB_USER']
        if 'TIDB_PASSWORD' in os.environ:
            del os.environ['TIDB_PASSWORD']
        
        print("1. Removed TiDB credentials from environment")
        
        # Try to import settings (this should fail)
        try:
            from app.core.config import settings
            tidb_url = settings.tidb_url  # This should raise an error
            print(f"❌ UNEXPECTED: Got URL without credentials: {tidb_url}")
            return False
        except ValueError as e:
            print(f"✅ EXPECTED: Configuration failed as expected: {e}")
            return True
        except Exception as e:
            print(f"❌ UNEXPECTED ERROR: {e}")
            return False
            
    finally:
        # Restore original credentials
        if original_host:
            os.environ['TIDB_HOST'] = original_host
        if original_user:
            os.environ['TIDB_USER'] = original_user
        if original_password:
            os.environ['TIDB_PASSWORD'] = original_password
        print("2. Restored TiDB credentials")

if __name__ == "__main__":
    success = test_no_fallback()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 SUCCESS: No SQLite fallback - TiDB credentials are required!")
        print("✅ Your application will never accidentally use SQLite.")
    else:
        print("❌ ISSUE: Application might still fall back to SQLite.")
        
    # Test that credentials work again
    print("\n🔍 VERIFYING TIDB STILL WORKS...")
    try:
        from app.core.config import settings
        tidb_url = settings.tidb_url
        print("✅ TiDB configuration restored and working!")
    except Exception as e:
        print(f"❌ TiDB configuration broken: {e}")
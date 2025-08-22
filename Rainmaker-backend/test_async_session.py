#!/usr/bin/env python3
"""
Test script to verify AsyncSessionLocal works correctly
"""

import asyncio
import sys
import os

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

async def test_async_session():
    """Test async database session"""
    try:
        from app.db.session import AsyncSessionLocal
        from sqlalchemy import text
        
        print("✓ AsyncSessionLocal imported successfully")
        
        # Test basic connection
        async with AsyncSessionLocal() as session:
            result = await session.execute(text("SELECT 1 as test"))
            row = result.fetchone()
            print(f"✓ Async database connection successful: {row}")
            
        print("✓ All async session tests passed!")
        return True
        
    except Exception as e:
        print(f"✗ Async session test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_async_session())
    sys.exit(0 if success else 1)
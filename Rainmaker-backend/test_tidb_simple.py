"""
Simple TiDB connection test with timeout
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

async def quick_test():
    print("Quick TiDB test...")
    
    try:
        from sqlalchemy.ext.asyncio import create_async_engine
        from sqlalchemy import text
        
        # Simple engine with timeout
        engine = create_async_engine(
            "mysql+aiomysql://2jp9LEhYwkC25yz.root:KUftSfJPYUDjQUF7@gateway01.eu-central-1.prod.aws.tidbcloud.com:4000/github_sample",
            connect_args={"autocommit": True},
            pool_timeout=10,
            pool_pre_ping=True
        )
        
        print("Connecting...")
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT 1 as test"))
            row = result.fetchone()
            print(f"✅ Connected! Test result: {row.test}")
            
        await engine.dispose()
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    try:
        success = asyncio.wait_for(quick_test(), timeout=15)
        result = asyncio.run(success)
        if result:
            print("🎉 TiDB connection works!")
        else:
            print("❌ Connection failed")
    except asyncio.TimeoutError:
        print("⏰ Connection timed out - might be SSL/firewall issue")
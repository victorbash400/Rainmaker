"""
Direct aiomysql connection test for TiDB
"""
import asyncio
import aiomysql
import ssl
import os

async def test_direct_connection():
    """Test direct connection to TiDB using aiomysql"""
    
    # Connection parameters
    host = "gateway01.eu-central-1.prod.aws.tidbcloud.com"
    port = 4000
    user = "2jp9LEhYwkC25yz.root"
    password = "KUftSfJPYUDjQUF7"
    database = "github_sample"
    
    print("Testing direct aiomysql connection...")
    print(f"Host: {host}")
    print(f"Port: {port}")
    print(f"User: {user}")
    print(f"Database: {database}")
    
    # Test 1: Connection without SSL
    print("\n1. Testing without SSL...")
    try:
        conn = await aiomysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            db=database,
        )
        print("✅ Connection without SSL successful")
        await conn.ensure_closed()
    except Exception as e:
        print(f"❌ Connection without SSL failed: {e}")
    
    # Test 2: Connection with SSL (no verification)
    print("\n2. Testing with SSL (no verification)...")
    try:
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        conn = await aiomysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            db=database,
            ssl=ssl_context
        )
        print("✅ Connection with SSL (no verification) successful")
        
        # Test a simple query
        cursor = await conn.cursor()
        await cursor.execute("SELECT 1 as test")
        result = await cursor.fetchone()
        print(f"✅ Query result: {result}")
        await cursor.close()
        await conn.ensure_closed()
        
    except Exception as e:
        print(f"❌ Connection with SSL (no verification) failed: {e}")
    
    # Test 3: Connection with SSL certificate
    print("\n3. Testing with SSL certificate...")
    try:
        if os.path.exists("isrgrootx1.pem"):
            ssl_context = ssl.create_default_context(cafile="isrgrootx1.pem")
            ssl_context.check_hostname = True
            ssl_context.verify_mode = ssl.CERT_REQUIRED
            
            conn = await aiomysql.connect(
                host=host,
                port=port,
                user=user,
                password=password,
                db=database,
                ssl=ssl_context
            )
            print("✅ Connection with SSL certificate successful")
            
            # Test a simple query
            cursor = await conn.cursor()
            await cursor.execute("SELECT VERSION() as version")
            result = await cursor.fetchone()
            print(f"✅ TiDB Version: {result[0]}")
            await cursor.close()
            await conn.ensure_closed()
        else:
            print("❌ SSL certificate file 'isrgrootx1.pem' not found")
            
    except Exception as e:
        print(f"❌ Connection with SSL certificate failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_direct_connection())
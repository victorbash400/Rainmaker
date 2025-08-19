"""
Test MySQL connection using PyMySQL (synchronous) to isolate async issues
"""
import pymysql
import ssl
import os

def test_pymysql_connection():
    """Test connection using synchronous PyMySQL"""
    
    host = "gateway01.eu-central-1.prod.aws.tidbcloud.com"
    port = 4000
    user = "2jp9LEhYwkC25yz.root"
    password = "KUftSfJPYUDjQUF7"
    database = "github_sample"
    
    print("=== PYMYSQL CONNECTION TEST ===")
    print(f"Host: {host}:{port}")
    print(f"User: {user}")
    print(f"Database: {database}")
    
    # Test 1: Connection with SSL (TiDB recommended way)
    print("\n1. Testing with SSL (TiDB recommended)...")
    try:
        # Check if certificate exists
        cert_path = "isrgrootx1.pem"
        if not os.path.exists(cert_path):
            print(f"❌ Certificate file not found: {cert_path}")
            return False
            
        connection = pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database,
            ssl_ca=cert_path,
            ssl_verify_cert=True,
            ssl_verify_identity=True
        )
        
        print("✅ PyMySQL SSL connection successful!")
        
        # Test a query
        with connection.cursor() as cursor:
            cursor.execute("SELECT VERSION() as version, DATABASE() as db")
            result = cursor.fetchone()
            print(f"✅ TiDB Version: {result[0]}")
            print(f"✅ Database: {result[1]}")
        
        connection.close()
        return True
        
    except Exception as e:
        print(f"❌ PyMySQL SSL connection failed: {e}")
    
    # Test 2: Connection with SSL but no verification
    print("\n2. Testing with SSL (no verification)...")
    try:
        connection = pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database,
            ssl_ca=cert_path,
            ssl_verify_cert=False,
            ssl_verify_identity=False
        )
        
        print("✅ PyMySQL SSL (no verification) connection successful!")
        
        # Test a query
        with connection.cursor() as cursor:
            cursor.execute("SELECT VERSION() as version, DATABASE() as db")
            result = cursor.fetchone()
            print(f"✅ TiDB Version: {result[0]}")
            print(f"✅ Database: {result[1]}")
        
        connection.close()
        return True
        
    except Exception as e:
        print(f"❌ PyMySQL SSL (no verification) connection failed: {e}")
    
    # Test 3: Connection with SSL context
    print("\n3. Testing with SSL context...")
    try:
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        connection = pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database,
            ssl=ssl_context
        )
        
        print("✅ PyMySQL SSL context connection successful!")
        
        # Test a query
        with connection.cursor() as cursor:
            cursor.execute("SELECT VERSION() as version, DATABASE() as db")
            result = cursor.fetchone()
            print(f"✅ TiDB Version: {result[0]}")
            print(f"✅ Database: {result[1]}")
        
        connection.close()
        return True
        
    except Exception as e:
        print(f"❌ PyMySQL SSL context connection failed: {e}")
    
    return False

if __name__ == "__main__":
    if test_pymysql_connection():
        print("\n🎉 SUCCESS! PyMySQL can connect to TiDB.")
        print("The issue is likely with the async driver (aiomysql/asyncmy) configuration.")
        print("Consider using PyMySQL with SQLAlchemy's sync engine for now.")
    else:
        print("\n❌ All PyMySQL connection attempts failed.")
        print("The issue might be:")
        print("1. Incorrect credentials")
        print("2. TiDB cluster configuration")
        print("3. SSL certificate issues")
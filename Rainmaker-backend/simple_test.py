"""
Simple connectivity test to isolate the issue
"""
import socket
import ssl
import requests

def test_basic_connectivity():
    """Test basic network connectivity to TiDB"""
    host = "gateway01.eu-central-1.prod.aws.tidbcloud.com"
    port = 4000
    
    print("=== BASIC CONNECTIVITY TEST ===")
    print(f"Testing connection to {host}:{port}")
    
    # Test 1: Basic socket connection
    print("\n1. Testing basic socket connection...")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        result = sock.connect_ex((host, port))
        sock.close()
        
        if result == 0:
            print("✅ Socket connection successful")
        else:
            print(f"❌ Socket connection failed with error code: {result}")
            return False
    except Exception as e:
        print(f"❌ Socket connection failed: {e}")
        return False
    
    # Test 2: SSL socket connection
    print("\n2. Testing SSL socket connection...")
    try:
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        
        with socket.create_connection((host, port), timeout=10) as sock:
            with context.wrap_socket(sock, server_hostname=host) as ssock:
                print("✅ SSL socket connection successful")
                print(f"✅ SSL version: {ssock.version()}")
    except Exception as e:
        print(f"❌ SSL socket connection failed: {e}")
        return False
    
    # Test 3: Check if we can resolve the hostname
    print("\n3. Testing DNS resolution...")
    try:
        ip = socket.gethostbyname(host)
        print(f"✅ DNS resolution successful: {host} -> {ip}")
    except Exception as e:
        print(f"❌ DNS resolution failed: {e}")
        return False
    
    # Test 4: Check internet connectivity
    print("\n4. Testing general internet connectivity...")
    try:
        response = requests.get("https://httpbin.org/ip", timeout=10)
        if response.status_code == 200:
            print(f"✅ Internet connectivity OK. Your IP: {response.json().get('origin')}")
        else:
            print("❌ Internet connectivity issue")
            return False
    except Exception as e:
        print(f"❌ Internet connectivity test failed: {e}")
        return False
    
    return True

def test_tidb_web_console():
    """Test if we can reach TiDB web console"""
    print("\n=== TIDB WEB CONSOLE TEST ===")
    try:
        # Try to reach TiDB Cloud console
        response = requests.get("https://tidbcloud.com", timeout=10)
        if response.status_code == 200:
            print("✅ TiDB Cloud website is reachable")
        else:
            print(f"❌ TiDB Cloud website returned status: {response.status_code}")
    except Exception as e:
        print(f"❌ Cannot reach TiDB Cloud website: {e}")

if __name__ == "__main__":
    print("🔍 DIAGNOSING TIDB CONNECTION ISSUES")
    print("=" * 50)
    
    if test_basic_connectivity():
        print("\n🎉 Basic connectivity tests passed!")
        print("The issue is likely with the MySQL driver configuration or authentication.")
        print("\nNext steps:")
        print("1. Check if your TiDB cluster is active in the web console")
        print("2. Verify your credentials are correct")
        print("3. Try a different MySQL driver or connection method")
    else:
        print("\n❌ Basic connectivity failed!")
        print("The issue is likely:")
        print("1. Network/firewall blocking the connection")
        print("2. TiDB cluster is paused or unavailable")
        print("3. IP address not whitelisted")
        print("4. DNS resolution issues")
    
    test_tidb_web_console()
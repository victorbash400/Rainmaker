#!/usr/bin/env python3
"""
Final comprehensive test for Database MCP server
"""

import asyncio
import json
import sys
from pathlib import Path

# Add the app directory to the path
sys.path.append(str(Path(__file__).parent))

from app.mcp.database import database_mcp
from app.db.session import test_connection


async def test_database_mcp_comprehensive():
    """Comprehensive test of Database MCP server functionality"""
    print("Database MCP Comprehensive Test")
    print("=" * 50)
    
    test_results = {
        "database_connection": False,
        "server_initialization": False,
        "query_safety": False,
        "table_validation": False,
        "complexity_analysis": False,
        "index_suggestions": False,
        "connection_stats": False
    }
    
    # Test 1: Database connection
    print("1. Testing database connection...")
    try:
        connection_ok = await test_connection()
        test_results["database_connection"] = connection_ok
        if connection_ok:
            print("✅ Database connection successful")
        else:
            print("❌ Database connection failed")
    except Exception as e:
        print(f"❌ Database connection error: {e}")
    
    # Test 2: Server initialization
    print("\n2. Testing server initialization...")
    try:
        assert database_mcp is not None
        assert hasattr(database_mcp, 'server')
        assert hasattr(database_mcp, 'connection_pool_stats')
        assert database_mcp.server.name == "database"
        
        test_results["server_initialization"] = True
        print("✅ Server initialization successful")
        print(f"   Server name: {database_mcp.server.name}")
        print(f"   Server type: {type(database_mcp.server).__name__}")
    except Exception as e:
        print(f"❌ Server initialization error: {e}")
    
    # Test 3: Query safety validation
    print("\n3. Testing query safety validation...")
    try:
        safe_queries = [
            "SELECT * FROM prospects",
            "INSERT INTO prospects (name) VALUES ('test')",
            "UPDATE prospects SET name = 'updated' WHERE id = 1",
            "DELETE FROM prospects WHERE id = 1"
        ]
        
        unsafe_queries = [
            "DROP TABLE prospects",
            "TRUNCATE TABLE prospects",
            "ALTER TABLE prospects ADD COLUMN test VARCHAR(255)",
            "CREATE USER test@localhost",
            "GRANT ALL ON *.* TO test@localhost"
        ]
        
        safe_results = [database_mcp._is_safe_query(q) for q in safe_queries]
        unsafe_results = [database_mcp._is_safe_query(q) for q in unsafe_queries]
        
        all_safe_passed = all(safe_results)
        all_unsafe_blocked = not any(unsafe_results)
        
        test_results["query_safety"] = all_safe_passed and all_unsafe_blocked
        
        if test_results["query_safety"]:
            print("✅ Query safety validation working correctly")
            print(f"   Safe queries: {sum(safe_results)}/{len(safe_queries)} passed")
            print(f"   Unsafe queries: {sum(unsafe_results)}/{len(unsafe_queries)} blocked")
        else:
            print("❌ Query safety validation failed")
            print(f"   Safe queries: {safe_results}")
            print(f"   Unsafe queries: {unsafe_results}")
            
    except Exception as e:
        print(f"❌ Query safety validation error: {e}")
    
    # Test 4: Table validation
    print("\n4. Testing table validation...")
    try:
        valid_tables = ["prospects", "campaigns", "conversations", "proposals", "meetings", "users"]
        invalid_tables = ["invalid_table", "malicious_table", "", "users; DROP TABLE prospects;"]
        
        valid_results = [database_mcp._is_valid_table_name(t) for t in valid_tables]
        invalid_results = [database_mcp._is_valid_table_name(t) for t in invalid_tables]
        
        all_valid_passed = all(valid_results)
        all_invalid_blocked = not any(invalid_results)
        
        test_results["table_validation"] = all_valid_passed and all_invalid_blocked
        
        if test_results["table_validation"]:
            print("✅ Table validation working correctly")
            print(f"   Valid tables: {sum(valid_results)}/{len(valid_tables)} passed")
            print(f"   Invalid tables: {sum(invalid_results)}/{len(invalid_tables)} blocked")
        else:
            print("❌ Table validation failed")
            
    except Exception as e:
        print(f"❌ Table validation error: {e}")
    
    # Test 5: Query complexity analysis
    print("\n5. Testing query complexity analysis...")
    try:
        test_queries = [
            ("SELECT id FROM prospects", "simple"),
            ("SELECT p.id, COUNT(c.id) FROM prospects p JOIN campaigns c ON p.id = c.prospect_id GROUP BY p.id", "moderate"),
            ("SELECT p.id, (SELECT COUNT(*) FROM campaigns WHERE prospect_id = p.id) FROM prospects p JOIN campaigns c ON p.id = c.prospect_id WHERE p.id IN (SELECT id FROM prospects WHERE lead_score > 80) GROUP BY p.id ORDER BY p.created_at", "complex")
        ]
        
        complexity_correct = 0
        for query, expected in test_queries:
            actual = database_mcp._analyze_select_complexity(query)
            if actual == expected:
                complexity_correct += 1
            print(f"   Query: {query[:50]}... -> {actual} (expected: {expected})")
        
        test_results["complexity_analysis"] = complexity_correct == len(test_queries)
        
        if test_results["complexity_analysis"]:
            print("✅ Query complexity analysis working correctly")
        else:
            print(f"❌ Query complexity analysis failed ({complexity_correct}/{len(test_queries)} correct)")
            
    except Exception as e:
        print(f"❌ Query complexity analysis error: {e}")
    
    # Test 6: Index suggestions
    print("\n6. Testing index suggestions...")
    try:
        test_queries = [
            "SELECT * FROM prospects WHERE email = 'test@example.com'",
            "SELECT p.name FROM prospects p JOIN campaigns c ON p.id = c.prospect_id",
            "SELECT * FROM prospects ORDER BY created_at DESC"
        ]
        
        suggestions_generated = 0
        for query in test_queries:
            suggestions = database_mcp._suggest_indexes(query)
            if suggestions:
                suggestions_generated += 1
            print(f"   Query: {query[:40]}... -> {len(suggestions)} suggestions")
        
        test_results["index_suggestions"] = suggestions_generated > 0
        
        if test_results["index_suggestions"]:
            print("✅ Index suggestions working correctly")
        else:
            print("❌ Index suggestions not generating suggestions")
            
    except Exception as e:
        print(f"❌ Index suggestions error: {e}")
    
    # Test 7: Connection pool statistics
    print("\n7. Testing connection pool statistics...")
    try:
        stats = database_mcp.connection_pool_stats
        required_keys = [
            "total_connections", "active_connections", "failed_connections",
            "last_health_check", "query_count", "slow_queries", "error_count"
        ]
        
        has_all_keys = all(key in stats for key in required_keys)
        
        # Test updating stats
        original_query_count = stats["query_count"]
        database_mcp.connection_pool_stats["query_count"] += 1
        updated_query_count = database_mcp.connection_pool_stats["query_count"]
        
        stats_updateable = updated_query_count == original_query_count + 1
        
        test_results["connection_stats"] = has_all_keys and stats_updateable
        
        if test_results["connection_stats"]:
            print("✅ Connection pool statistics working correctly")
            print(f"   Stats keys: {list(stats.keys())}")
            print(f"   Query count: {stats['query_count']}")
        else:
            print("❌ Connection pool statistics failed")
            print(f"   Has all keys: {has_all_keys}")
            print(f"   Stats updateable: {stats_updateable}")
            
    except Exception as e:
        print(f"❌ Connection pool statistics error: {e}")
    
    # Summary
    print(f"\n" + "=" * 50)
    print("TEST SUMMARY")
    print("=" * 50)
    
    passed_tests = sum(test_results.values())
    total_tests = len(test_results)
    
    for test_name, result in test_results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name.replace('_', ' ').title():<25} {status}")
    
    print(f"\nOverall: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("🎉 All Database MCP tests passed!")
        return True
    else:
        print("❌ Some Database MCP tests failed!")
        return False


async def main():
    """Main test function"""
    try:
        success = await test_database_mcp_comprehensive()
        if not success:
            sys.exit(1)
    except Exception as e:
        print(f"❌ Test suite failed with exception: {e}")
        sys.exit(1)
    finally:
        # Clean up
        try:
            await database_mcp.close()
        except:
            pass


if __name__ == "__main__":
    asyncio.run(main())
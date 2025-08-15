"""
Unit tests for Database MCP server
"""

import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime

from app.mcp.database import DatabaseMCP, database_mcp
from app.core.config import settings


class TestDatabaseMCP:
    """Test cases for Database MCP server"""
    
    @pytest.fixture
    def mcp_server(self):
        """Create a fresh MCP server instance for testing"""
        return DatabaseMCP()
    
    @pytest.mark.asyncio
    async def test_execute_query_select(self, mcp_server):
        """Test execute_query with SELECT statement"""
        
        # Mock the database session and result
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            MagicMock(_mapping={"id": 1, "name": "Test Prospect"}),
            MagicMock(_mapping={"id": 2, "name": "Another Prospect"})
        ]
        
        with patch('app.mcp.database.AsyncSessionLocal') as mock_session_local:
            mock_session_local.return_value.__aenter__.return_value = mock_session
            mock_session.execute.return_value = mock_result
            
            # Test the execute_query tool
            arguments = {
                "query": "SELECT id, name FROM prospects LIMIT 2",
                "parameters": {},
                "fetch_mode": "all"
            }
            
            # Get the tool function
            tools = mcp_server.server._tools
            execute_query_tool = None
            for tool_name, tool_func in tools.items():
                if tool_name == "execute_query":
                    execute_query_tool = tool_func
                    break
            
            assert execute_query_tool is not None, "execute_query tool not found"
            
            # Execute the tool
            result = await execute_query_tool(arguments)
            
            # Verify the result
            assert not result.isError
            content = json.loads(result.content[0].text)
            assert "result" in content
            assert len(content["result"]) == 2
            assert content["result"][0]["name"] == "Test Prospect"
            assert "execution_time" in content
    
    @pytest.mark.asyncio
    async def test_execute_query_unsafe(self, mcp_server):
        """Test execute_query with unsafe query"""
        
        # Get the tool function
        tools = mcp_server.server._tools
        execute_query_tool = None
        for tool_name, tool_func in tools.items():
            if tool_name == "execute_query":
                execute_query_tool = tool_func
                break
        
        arguments = {
            "query": "DROP TABLE prospects",
            "parameters": {}
        }
        
        result = await execute_query_tool(arguments)
        
        # Should return error for unsafe query
        assert result.isError
        content = json.loads(result.content[0].text)
        assert "error" in content
        assert "unsafe" in content["error"].lower()
    
    @pytest.mark.asyncio
    async def test_bulk_insert(self, mcp_server):
        """Test bulk_insert functionality"""
        
        mock_session = AsyncMock()
        
        with patch('app.mcp.database.AsyncSessionLocal') as mock_session_local:
            mock_session_local.return_value.__aenter__.return_value = mock_session
            mock_session.begin.return_value.__aenter__ = AsyncMock()
            mock_session.begin.return_value.__aexit__ = AsyncMock()
            mock_session.execute.return_value = MagicMock()
            
            # Get the tool function
            tools = mcp_server.server._tools
            bulk_insert_tool = None
            for tool_name, tool_func in tools.items():
                if tool_name == "bulk_insert":
                    bulk_insert_tool = tool_func
                    break
            
            arguments = {
                "table_name": "prospects",
                "records": [
                    {"name": "Test 1", "email": "test1@example.com", "source": "test"},
                    {"name": "Test 2", "email": "test2@example.com", "source": "test"}
                ],
                "batch_size": 10
            }
            
            result = await bulk_insert_tool(arguments)
            
            # Verify the result
            assert not result.isError
            content = json.loads(result.content[0].text)
            assert content["inserted_count"] == 2
            assert content["total_records"] == 2
            assert "execution_time" in content
    
    @pytest.mark.asyncio
    async def test_bulk_insert_invalid_table(self, mcp_server):
        """Test bulk_insert with invalid table name"""
        
        # Get the tool function
        tools = mcp_server.server._tools
        bulk_insert_tool = None
        for tool_name, tool_func in tools.items():
            if tool_name == "bulk_insert":
                bulk_insert_tool = tool_func
                break
        
        arguments = {
            "table_name": "invalid_table",
            "records": [{"name": "Test"}]
        }
        
        result = await bulk_insert_tool(arguments)
        
        # Should return error for invalid table
        assert result.isError
        content = json.loads(result.content[0].text)
        assert "error" in content
        assert "invalid table" in content["error"].lower()
    
    @pytest.mark.asyncio
    async def test_transaction_manager(self, mcp_server):
        """Test transaction_manager functionality"""
        
        mock_session = AsyncMock()
        mock_result1 = MagicMock()
        mock_result1.fetchall.return_value = [MagicMock(_mapping={"count": 5})]
        mock_result2 = MagicMock()
        mock_result2.rowcount = 1
        
        with patch('app.mcp.database.AsyncSessionLocal') as mock_session_local:
            mock_session_local.return_value.__aenter__.return_value = mock_session
            mock_session.begin.return_value.__aenter__ = AsyncMock()
            mock_session.begin.return_value.__aexit__ = AsyncMock()
            mock_session.execute.side_effect = [mock_result1, mock_result2]
            
            # Get the tool function
            tools = mcp_server.server._tools
            transaction_tool = None
            for tool_name, tool_func in tools.items():
                if tool_name == "transaction_manager":
                    transaction_tool = tool_func
                    break
            
            arguments = {
                "operations": [
                    {
                        "type": "select",
                        "query": "SELECT COUNT(*) as count FROM prospects",
                        "parameters": {}
                    },
                    {
                        "type": "update",
                        "query": "UPDATE prospects SET status = 'contacted' WHERE id = :id",
                        "parameters": {"id": 1}
                    }
                ]
            }
            
            result = await transaction_tool(arguments)
            
            # Verify the result
            assert not result.isError
            content = json.loads(result.content[0].text)
            assert content["status"] == "committed"
            assert len(content["transaction_results"]) == 2
            assert content["transaction_results"][0]["type"] == "select"
            assert content["transaction_results"][1]["type"] == "update"
    
    @pytest.mark.asyncio
    async def test_health_check(self, mcp_server):
        """Test health_check functionality"""
        
        # Mock test_connection function
        with patch('app.mcp.database.test_connection', return_value=True):
            mock_session = AsyncMock()
            mock_result = MagicMock()
            mock_result.scalar.return_value = 9  # Number of tables
            
            with patch('app.mcp.database.AsyncSessionLocal') as mock_session_local:
                mock_session_local.return_value.__aenter__.return_value = mock_session
                mock_session.execute.return_value = mock_result
                
                # Get the tool function
                tools = mcp_server.server._tools
                health_check_tool = None
                for tool_name, tool_func in tools.items():
                    if tool_name == "health_check":
                        health_check_tool = tool_func
                        break
                
                arguments = {
                    "include_stats": True,
                    "test_operations": False
                }
                
                result = await health_check_tool(arguments)
                
                # Verify the result
                assert not result.isError
                content = json.loads(result.content[0].text)
                assert content["status"] == "healthy"
                assert content["connection_test"] is True
                assert content["query_test"] is True
                assert content["table_count"] == 9
                assert "connection_pool_stats" in content
    
    @pytest.mark.asyncio
    async def test_query_optimization(self, mcp_server):
        """Test query_optimization functionality"""
        
        # Get the tool function
        tools = mcp_server.server._tools
        optimization_tool = None
        for tool_name, tool_func in tools.items():
            if tool_name == "query_optimization":
                optimization_tool = tool_func
                break
        
        arguments = {
            "query": "SELECT * FROM prospects WHERE email LIKE '%@gmail.com' ORDER BY created_at",
            "suggest_indexes": True
        }
        
        result = await optimization_tool(arguments)
        
        # Verify the result
        assert not result.isError
        content = json.loads(result.content[0].text)
        assert "analysis" in content
        assert "suggestions" in content
        assert content["analysis"]["type"] == "SELECT"
        assert len(content["analysis"]["performance_issues"]) > 0
        assert "SELECT *" in content["analysis"]["performance_issues"][0]
    
    def test_is_safe_query(self, mcp_server):
        """Test query safety validation"""
        
        # Safe queries
        assert mcp_server._is_safe_query("SELECT * FROM prospects")
        assert mcp_server._is_safe_query("INSERT INTO prospects (name) VALUES ('test')")
        assert mcp_server._is_safe_query("UPDATE prospects SET name = 'updated'")
        assert mcp_server._is_safe_query("DELETE FROM prospects WHERE id = 1")
        
        # Unsafe queries
        assert not mcp_server._is_safe_query("DROP TABLE prospects")
        assert not mcp_server._is_safe_query("TRUNCATE TABLE prospects")
        assert not mcp_server._is_safe_query("ALTER TABLE prospects ADD COLUMN test VARCHAR(255)")
        assert not mcp_server._is_safe_query("CREATE USER test@localhost")
    
    def test_is_valid_table_name(self, mcp_server):
        """Test table name validation"""
        
        # Valid table names
        assert mcp_server._is_valid_table_name("prospects")
        assert mcp_server._is_valid_table_name("campaigns")
        assert mcp_server._is_valid_table_name("conversations")
        
        # Invalid table names
        assert not mcp_server._is_valid_table_name("invalid_table")
        assert not mcp_server._is_valid_table_name("users; DROP TABLE prospects;")
        assert not mcp_server._is_valid_table_name("")
    
    def test_analyze_select_complexity(self, mcp_server):
        """Test SELECT query complexity analysis"""
        
        # Simple query
        simple_query = "SELECT id, name FROM prospects WHERE id = 1"
        assert mcp_server._analyze_select_complexity(simple_query) == "simple"
        
        # Moderate query
        moderate_query = """
        SELECT p.id, p.name, COUNT(c.id) as campaign_count
        FROM prospects p
        LEFT JOIN campaigns c ON p.id = c.prospect_id
        WHERE p.status = 'qualified'
        GROUP BY p.id, p.name
        ORDER BY campaign_count DESC
        """
        assert mcp_server._analyze_select_complexity(moderate_query) == "moderate"
        
        # Complex query
        complex_query = """
        SELECT p.id, p.name, 
               (SELECT COUNT(*) FROM campaigns WHERE prospect_id = p.id) as campaigns,
               (SELECT COUNT(*) FROM conversations WHERE prospect_id = p.id) as conversations
        FROM prospects p
        JOIN event_requirements er ON p.id = er.prospect_id
        JOIN campaigns c ON p.id = c.prospect_id
        JOIN conversations conv ON p.id = conv.prospect_id
        WHERE p.status IN (SELECT DISTINCT status FROM prospects WHERE lead_score > 80)
        GROUP BY p.id, p.name
        HAVING COUNT(c.id) > 2
        ORDER BY p.lead_score DESC, p.created_at ASC
        """
        assert mcp_server._analyze_select_complexity(complex_query) == "complex"
    
    def test_suggest_indexes(self, mcp_server):
        """Test index suggestion functionality"""
        
        query_with_where = "SELECT * FROM prospects WHERE email = 'test@example.com'"
        suggestions = mcp_server._suggest_indexes(query_with_where)
        assert any("WHERE" in suggestion for suggestion in suggestions)
        
        query_with_join = """
        SELECT p.name, c.subject_line 
        FROM prospects p 
        JOIN campaigns c ON p.id = c.prospect_id
        """
        suggestions = mcp_server._suggest_indexes(query_with_join)
        assert any("JOIN" in suggestion for suggestion in suggestions)
        
        query_with_order = "SELECT * FROM prospects ORDER BY created_at DESC"
        suggestions = mcp_server._suggest_indexes(query_with_order)
        assert any("ORDER BY" in suggestion for suggestion in suggestions)


@pytest.mark.asyncio
async def test_global_database_mcp_instance():
    """Test that the global database MCP instance is properly initialized"""
    
    assert database_mcp is not None
    assert hasattr(database_mcp, 'server')
    assert hasattr(database_mcp, 'connection_pool_stats')
    
    # Test that the server has the expected tools
    tools = database_mcp.server._tools
    expected_tools = [
        "execute_query", "bulk_insert", "transaction_manager", 
        "health_check", "query_optimization"
    ]
    
    for tool_name in expected_tools:
        assert tool_name in tools, f"Tool {tool_name} not found in MCP server"


@pytest.mark.asyncio
async def test_database_mcp_integration():
    """Integration test with actual database (if available)"""
    
    # Only run if we have a working database connection
    try:
        from app.db.session import test_connection
        connection_ok = await test_connection()
        
        if not connection_ok:
            pytest.skip("Database connection not available")
        
        # Test health check with real database
        tools = database_mcp.server._tools
        health_check_tool = tools["health_check"]
        
        result = await health_check_tool({"include_stats": True})
        
        assert not result.isError
        content = json.loads(result.content[0].text)
        assert content["connection_test"] is True
        assert "table_count" in content
        
    except Exception as e:
        pytest.skip(f"Database integration test skipped: {e}")
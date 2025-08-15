"""
Database MCP server for TiDB operations with connection pooling and monitoring
"""

import asyncio
import json
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
import structlog
from sqlalchemy import text, inspect
from sqlalchemy.exc import SQLAlchemyError, OperationalError
from mcp.server import Server
from mcp.types import Tool, TextContent, CallToolResult

from app.core.config import settings
from app.db.session import AsyncSessionLocal, engine, test_connection
from app.db.models import (
    Prospect, EventRequirements, Campaign, Conversation, 
    Message, Proposal, Meeting, AgentActivity, User
)

logger = structlog.get_logger(__name__)


class DatabaseMCP:
    """
    MCP server for database operations with TiDB optimization and monitoring
    """
    
    def __init__(self):
        self.server = Server("database")
        self.connection_pool_stats = {
            "total_connections": 0,
            "active_connections": 0,
            "failed_connections": 0,
            "last_health_check": None,
            "query_count": 0,
            "slow_queries": 0,
            "error_count": 0
        }
        
        # Register MCP tools
        self._register_tools()
    
    def _register_tools(self):
        """Register MCP tools for database operations"""
        
        @self.server.call_tool()
        async def execute_query(arguments: Dict[str, Any]) -> CallToolResult:
            """
            Execute a SQL query with parameters
            
            Args:
                query: SQL query string
                parameters: Query parameters (optional)
                fetch_mode: 'all', 'one', 'scalar', or 'none' (default: 'all')
                timeout: Query timeout in seconds (default: 30)
            """
            try:
                query_str = arguments.get("query")
                parameters = arguments.get("parameters", {})
                fetch_mode = arguments.get("fetch_mode", "all")
                timeout = arguments.get("timeout", 30)
                
                if not query_str:
                    raise ValueError("query is required")
                
                # Validate query safety
                if not self._is_safe_query(query_str):
                    raise ValueError("Query contains potentially unsafe operations")
                
                start_time = datetime.now()
                result = await self._execute_query_with_monitoring(
                    query_str, parameters, fetch_mode, timeout
                )
                execution_time = (datetime.now() - start_time).total_seconds()
                
                # Track slow queries
                if execution_time > 1.0:
                    self.connection_pool_stats["slow_queries"] += 1
                    logger.warning("Slow query detected", 
                                 query=query_str[:100], 
                                 execution_time=execution_time)
                
                self.connection_pool_stats["query_count"] += 1
                
                return CallToolResult(
                    content=[TextContent(
                        type="text",
                        text=json.dumps({
                            "result": result,
                            "execution_time": execution_time,
                            "row_count": len(result) if isinstance(result, list) else 1,
                            "query": query_str[:200] + "..." if len(query_str) > 200 else query_str
                        }, indent=2, default=str)
                    )]
                )
                
            except Exception as e:
                self.connection_pool_stats["error_count"] += 1
                logger.error("Query execution failed", error=str(e), query=query_str[:100])
                return CallToolResult(
                    content=[TextContent(
                        type="text",
                        text=json.dumps({"error": f"Query execution failed: {str(e)}"})
                    )],
                    isError=True
                )
        
        @self.server.call_tool()
        async def bulk_insert(arguments: Dict[str, Any]) -> CallToolResult:
            """
            Perform bulk insert operations for better performance
            
            Args:
                table_name: Name of the table
                records: List of dictionaries containing record data
                batch_size: Number of records per batch (default: 100)
                on_conflict: Action on conflict - 'ignore', 'update', or 'error' (default: 'error')
            """
            try:
                table_name = arguments.get("table_name")
                records = arguments.get("records", [])
                batch_size = arguments.get("batch_size", 100)
                on_conflict = arguments.get("on_conflict", "error")
                
                if not table_name or not records:
                    raise ValueError("table_name and records are required")
                
                # Validate table name
                if not self._is_valid_table_name(table_name):
                    raise ValueError(f"Invalid table name: {table_name}")
                
                start_time = datetime.now()
                inserted_count = 0
                
                # Process in batches
                for i in range(0, len(records), batch_size):
                    batch = records[i:i + batch_size]
                    batch_result = await self._bulk_insert_batch(
                        table_name, batch, on_conflict
                    )
                    inserted_count += batch_result
                
                execution_time = (datetime.now() - start_time).total_seconds()
                
                return CallToolResult(
                    content=[TextContent(
                        type="text",
                        text=json.dumps({
                            "inserted_count": inserted_count,
                            "total_records": len(records),
                            "execution_time": execution_time,
                            "batches_processed": (len(records) + batch_size - 1) // batch_size
                        }, indent=2)
                    )]
                )
                
            except Exception as e:
                logger.error("Bulk insert failed", error=str(e), table=table_name)
                return CallToolResult(
                    content=[TextContent(
                        type="text",
                        text=json.dumps({"error": f"Bulk insert failed: {str(e)}"})
                    )],
                    isError=True
                )
        
        @self.server.call_tool()
        async def transaction_manager(arguments: Dict[str, Any]) -> CallToolResult:
            """
            Execute multiple operations in a transaction
            
            Args:
                operations: List of operations to execute
                isolation_level: Transaction isolation level (optional)
            """
            try:
                operations = arguments.get("operations", [])
                isolation_level = arguments.get("isolation_level")
                
                if not operations:
                    raise ValueError("operations list is required")
                
                start_time = datetime.now()
                results = []
                
                async with AsyncSessionLocal() as session:
                    async with session.begin():
                        for i, operation in enumerate(operations):
                            op_type = operation.get("type")
                            op_query = operation.get("query")
                            op_params = operation.get("parameters", {})
                            
                            if not op_type or not op_query:
                                raise ValueError(f"Operation {i}: type and query are required")
                            
                            if not self._is_safe_query(op_query):
                                raise ValueError(f"Operation {i}: unsafe query detected")
                            
                            result = await session.execute(text(op_query), op_params)
                            
                            if op_type == "select":
                                op_result = [dict(row._mapping) for row in result.fetchall()]
                            elif op_type == "insert":
                                op_result = {"inserted_id": result.lastrowid}
                            elif op_type in ["update", "delete"]:
                                op_result = {"affected_rows": result.rowcount}
                            else:
                                op_result = {"status": "executed"}
                            
                            results.append({
                                "operation": i,
                                "type": op_type,
                                "result": op_result
                            })
                
                execution_time = (datetime.now() - start_time).total_seconds()
                
                return CallToolResult(
                    content=[TextContent(
                        type="text",
                        text=json.dumps({
                            "transaction_results": results,
                            "operations_count": len(operations),
                            "execution_time": execution_time,
                            "status": "committed"
                        }, indent=2, default=str)
                    )]
                )
                
            except Exception as e:
                logger.error("Transaction failed", error=str(e))
                return CallToolResult(
                    content=[TextContent(
                        type="text",
                        text=json.dumps({
                            "error": f"Transaction failed: {str(e)}",
                            "status": "rolled_back"
                        })
                    )],
                    isError=True
                )
        
        @self.server.call_tool()
        async def health_check(arguments: Dict[str, Any]) -> CallToolResult:
            """
            Perform comprehensive database health check
            
            Args:
                include_stats: Include detailed connection pool statistics
                test_operations: Run test CRUD operations
            """
            try:
                include_stats = arguments.get("include_stats", True)
                test_operations = arguments.get("test_operations", False)
                
                health_status = {
                    "status": "unknown",
                    "timestamp": datetime.now().isoformat(),
                    "database_url": settings.tidb_url.split("@")[1] if "@" in settings.tidb_url else "local",
                    "connection_test": False,
                    "query_test": False,
                    "table_count": 0,
                    "issues": []
                }
                
                # Test basic connectivity
                try:
                    connection_ok = await test_connection()
                    health_status["connection_test"] = connection_ok
                    if connection_ok:
                        self.connection_pool_stats["total_connections"] += 1
                    else:
                        self.connection_pool_stats["failed_connections"] += 1
                        health_status["issues"].append("Database connection failed")
                except Exception as e:
                    health_status["issues"].append(f"Connection test error: {str(e)}")
                
                # Test query operations
                try:
                    async with AsyncSessionLocal() as session:
                        # Count tables
                        if "sqlite" in settings.tidb_url:
                            result = await session.execute(text("SELECT COUNT(*) FROM sqlite_master WHERE type='table'"))
                        else:
                            result = await session.execute(text("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = DATABASE()"))
                        
                        health_status["table_count"] = result.scalar()
                        health_status["query_test"] = True
                        
                        # Test each main table
                        tables_to_check = ["prospects", "campaigns", "conversations", "proposals", "meetings"]
                        table_stats = {}
                        
                        for table in tables_to_check:
                            try:
                                count_result = await session.execute(text(f"SELECT COUNT(*) FROM {table}"))
                                table_stats[table] = count_result.scalar()
                            except Exception as e:
                                table_stats[table] = f"Error: {str(e)}"
                                health_status["issues"].append(f"Table {table} check failed: {str(e)}")
                        
                        health_status["table_stats"] = table_stats
                        
                except Exception as e:
                    health_status["issues"].append(f"Query test error: {str(e)}")
                
                # Test CRUD operations if requested
                if test_operations:
                    try:
                        crud_test = await self._test_crud_operations()
                        health_status["crud_test"] = crud_test
                    except Exception as e:
                        health_status["issues"].append(f"CRUD test error: {str(e)}")
                
                # Include connection pool stats
                if include_stats:
                    self.connection_pool_stats["last_health_check"] = datetime.now().isoformat()
                    health_status["connection_pool_stats"] = self.connection_pool_stats.copy()
                
                # Determine overall status
                if not health_status["issues"]:
                    health_status["status"] = "healthy"
                elif health_status["connection_test"] and health_status["query_test"]:
                    health_status["status"] = "degraded"
                else:
                    health_status["status"] = "unhealthy"
                
                return CallToolResult(
                    content=[TextContent(
                        type="text",
                        text=json.dumps(health_status, indent=2, default=str)
                    )]
                )
                
            except Exception as e:
                logger.error("Health check failed", error=str(e))
                return CallToolResult(
                    content=[TextContent(
                        type="text",
                        text=json.dumps({
                            "status": "error",
                            "error": f"Health check failed: {str(e)}",
                            "timestamp": datetime.now().isoformat()
                        })
                    )],
                    isError=True
                )
        
        @self.server.call_tool()
        async def query_optimization(arguments: Dict[str, Any]) -> CallToolResult:
            """
            Analyze and optimize database queries
            
            Args:
                query: SQL query to analyze
                suggest_indexes: Whether to suggest index optimizations
            """
            try:
                query_str = arguments.get("query")
                suggest_indexes = arguments.get("suggest_indexes", True)
                
                if not query_str:
                    raise ValueError("query is required")
                
                optimization_report = {
                    "query": query_str,
                    "analysis": {},
                    "suggestions": [],
                    "estimated_performance": "unknown"
                }
                
                # Basic query analysis
                query_lower = query_str.lower().strip()
                
                # Analyze query type
                if query_lower.startswith("select"):
                    optimization_report["analysis"]["type"] = "SELECT"
                    optimization_report["analysis"]["complexity"] = self._analyze_select_complexity(query_str)
                elif query_lower.startswith(("insert", "update", "delete")):
                    optimization_report["analysis"]["type"] = query_lower.split()[0].upper()
                    optimization_report["analysis"]["complexity"] = "write_operation"
                
                # Check for common performance issues
                performance_issues = []
                
                if "select *" in query_lower:
                    performance_issues.append("Using SELECT * - consider specifying columns")
                
                if " like " in query_lower and query_lower.count("%") > 0:
                    performance_issues.append("LIKE with wildcards may be slow - consider full-text search")
                
                if "order by" in query_lower and "limit" not in query_lower:
                    performance_issues.append("ORDER BY without LIMIT may be inefficient for large datasets")
                
                if query_lower.count("join") > 3:
                    performance_issues.append("Multiple JOINs detected - consider query optimization")
                
                optimization_report["analysis"]["performance_issues"] = performance_issues
                
                # Generate suggestions
                suggestions = []
                
                if suggest_indexes:
                    index_suggestions = self._suggest_indexes(query_str)
                    suggestions.extend(index_suggestions)
                
                if performance_issues:
                    suggestions.append("Review and address performance issues listed above")
                
                if "sqlite" not in settings.tidb_url:
                    suggestions.append("Consider using TiDB's HTAP capabilities for analytical queries")
                
                optimization_report["suggestions"] = suggestions
                
                # Estimate performance level
                issue_count = len(performance_issues)
                if issue_count == 0:
                    optimization_report["estimated_performance"] = "good"
                elif issue_count <= 2:
                    optimization_report["estimated_performance"] = "moderate"
                else:
                    optimization_report["estimated_performance"] = "poor"
                
                return CallToolResult(
                    content=[TextContent(
                        type="text",
                        text=json.dumps(optimization_report, indent=2)
                    )]
                )
                
            except Exception as e:
                logger.error("Query optimization failed", error=str(e))
                return CallToolResult(
                    content=[TextContent(
                        type="text",
                        text=json.dumps({"error": f"Query optimization failed: {str(e)}"})
                    )],
                    isError=True
                )
    
    async def _execute_query_with_monitoring(
        self, 
        query: str, 
        parameters: Dict[str, Any], 
        fetch_mode: str,
        timeout: int
    ) -> Union[List[Dict], Dict, Any, None]:
        """Execute query with monitoring and timeout"""
        
        async with AsyncSessionLocal() as session:
            try:
                # Set query timeout if supported
                if "mysql" in settings.tidb_url:
                    await session.execute(text(f"SET SESSION max_execution_time = {timeout * 1000}"))
                
                result = await session.execute(text(query), parameters)
                
                if fetch_mode == "all":
                    return [dict(row._mapping) for row in result.fetchall()]
                elif fetch_mode == "one":
                    row = result.fetchone()
                    return dict(row._mapping) if row else None
                elif fetch_mode == "scalar":
                    return result.scalar()
                else:  # fetch_mode == "none"
                    return {"affected_rows": result.rowcount}
                    
            except asyncio.TimeoutError:
                raise Exception(f"Query timeout after {timeout} seconds")
    
    async def _bulk_insert_batch(
        self, 
        table_name: str, 
        records: List[Dict[str, Any]], 
        on_conflict: str
    ) -> int:
        """Insert a batch of records"""
        
        if not records:
            return 0
        
        # Build bulk insert query
        columns = list(records[0].keys())
        placeholders = ", ".join([f":{col}" for col in columns])
        
        if on_conflict == "ignore":
            if "mysql" in settings.tidb_url:
                query = f"INSERT IGNORE INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"
            else:  # SQLite
                query = f"INSERT OR IGNORE INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"
        elif on_conflict == "update":
            # This would need more complex logic for UPSERT
            query = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"
        else:  # on_conflict == "error"
            query = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"
        
        async with AsyncSessionLocal() as session:
            async with session.begin():
                for record in records:
                    await session.execute(text(query), record)
                
        return len(records)
    
    async def _test_crud_operations(self) -> Dict[str, bool]:
        """Test basic CRUD operations"""
        crud_results = {
            "create": False,
            "read": False,
            "update": False,
            "delete": False
        }
        
        test_prospect_id = None
        
        try:
            async with AsyncSessionLocal() as session:
                async with session.begin():
                    # Create
                    insert_query = """
                    INSERT INTO prospects (prospect_type, name, email, source, status)
                    VALUES ('individual', 'Test CRUD', 'crud@test.com', 'health_check', 'discovered')
                    """
                    result = await session.execute(text(insert_query))
                    test_prospect_id = result.lastrowid
                    crud_results["create"] = True
                    
                    # Read
                    select_query = "SELECT * FROM prospects WHERE id = :id"
                    result = await session.execute(text(select_query), {"id": test_prospect_id})
                    row = result.fetchone()
                    crud_results["read"] = row is not None
                    
                    # Update
                    update_query = "UPDATE prospects SET name = 'Updated CRUD Test' WHERE id = :id"
                    result = await session.execute(text(update_query), {"id": test_prospect_id})
                    crud_results["update"] = result.rowcount > 0
                    
                    # Delete
                    delete_query = "DELETE FROM prospects WHERE id = :id"
                    result = await session.execute(text(delete_query), {"id": test_prospect_id})
                    crud_results["delete"] = result.rowcount > 0
                    
        except Exception as e:
            logger.error("CRUD test failed", error=str(e))
            # Clean up if needed
            if test_prospect_id:
                try:
                    async with AsyncSessionLocal() as session:
                        await session.execute(
                            text("DELETE FROM prospects WHERE id = :id"), 
                            {"id": test_prospect_id}
                        )
                        await session.commit()
                except:
                    pass
        
        return crud_results
    
    def _is_safe_query(self, query: str) -> bool:
        """Check if query is safe to execute"""
        query_lower = query.lower().strip()
        
        # Block dangerous operations
        dangerous_keywords = [
            "drop table", "drop database", "truncate", "alter table",
            "create user", "drop user", "grant", "revoke",
            "shutdown", "restart", "kill"
        ]
        
        for keyword in dangerous_keywords:
            if keyword in query_lower:
                return False
        
        # Allow common operations
        allowed_starts = [
            "select", "insert", "update", "delete",
            "with", "explain", "describe", "show"
        ]
        
        return any(query_lower.startswith(start) for start in allowed_starts)
    
    def _is_valid_table_name(self, table_name: str) -> bool:
        """Validate table name"""
        valid_tables = [
            "prospects", "event_requirements", "campaigns", "conversations",
            "messages", "proposals", "meetings", "agent_activities", "users"
        ]
        return table_name in valid_tables
    
    def _analyze_select_complexity(self, query: str) -> str:
        """Analyze SELECT query complexity"""
        query_lower = query.lower()
        
        complexity_score = 0
        
        # Count JOINs
        complexity_score += query_lower.count("join") * 2
        
        # Count subqueries
        complexity_score += query_lower.count("select") - 1
        
        # Check for aggregations
        if any(func in query_lower for func in ["count(", "sum(", "avg(", "max(", "min("]):
            complexity_score += 1
        
        # Check for GROUP BY
        if "group by" in query_lower:
            complexity_score += 1
        
        # Check for ORDER BY
        if "order by" in query_lower:
            complexity_score += 1
        
        if complexity_score <= 2:
            return "simple"
        elif complexity_score <= 5:
            return "moderate"
        else:
            return "complex"
    
    def _suggest_indexes(self, query: str) -> List[str]:
        """Suggest database indexes based on query"""
        suggestions = []
        query_lower = query.lower()
        
        # Look for WHERE clauses
        if "where" in query_lower:
            suggestions.append("Consider adding indexes on columns used in WHERE clauses")
        
        # Look for JOIN conditions
        if "join" in query_lower:
            suggestions.append("Ensure indexes exist on JOIN columns")
        
        # Look for ORDER BY
        if "order by" in query_lower:
            suggestions.append("Consider adding indexes on ORDER BY columns")
        
        # TiDB specific suggestions
        if "tidbcloud.com" in settings.tidb_url:
            suggestions.append("Consider using TiDB's clustered indexes for better performance")
            if "group by" in query_lower:
                suggestions.append("TiDB's columnar storage can optimize GROUP BY queries")
        
        return suggestions
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> CallToolResult:
        """Call a specific MCP tool by name"""
        if tool_name == "execute_query":
            # Call the registered execute_query tool
            return await self._execute_query_tool(arguments)
        else:
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=json.dumps({"error": f"Unknown tool: {tool_name}"})
                )],
                isError=True
            )
    
    async def _execute_query_tool(self, arguments: Dict[str, Any]) -> CallToolResult:
        """Execute the query tool"""
        try:
            query = arguments.get("query")
            parameters = arguments.get("parameters", [])
            fetch_mode = arguments.get("fetch_mode", "none")
            
            if not query:
                raise ValueError("Query is required")
            
            # Safety check
            if not self._is_safe_query(query):
                raise ValueError("Unsafe query detected")
            
            async with AsyncSessionLocal() as session:
                try:
                    if parameters:
                        if isinstance(parameters, list):
                            # For positional parameters with ?, convert to tuple
                            if "?" in query:
                                result = await session.execute(text(query), tuple(parameters))
                            else:
                                # For named parameters, convert list to dict if needed
                                result = await session.execute(text(query), parameters)
                        else:
                            # For named parameters (dict)
                            result = await session.execute(text(query), parameters)
                    else:
                        result = await session.execute(text(query))
                    
                    await session.commit()
                    
                    # Handle different fetch modes
                    if fetch_mode == "one":
                        row = result.fetchone()
                        data = dict(row._mapping) if row else None
                    elif fetch_mode == "all":
                        rows = result.fetchall()
                        data = [dict(row._mapping) for row in rows]
                    else:  # fetch_mode == "none"
                        data = {"affected_rows": result.rowcount}
                    
                    return CallToolResult(
                        content=[TextContent(
                            type="text",
                            text=json.dumps({"success": True, "data": data})
                        )]
                    )
                    
                except SQLAlchemyError as e:
                    await session.rollback()
                    raise e
                    
        except Exception as e:
            logger.error("Query execution failed", error=str(e), query=query)
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=json.dumps({"error": f"Query execution failed: {str(e)}"})
                )],
                isError=True
            )
    
    def get_server(self) -> Server:
        """Get the MCP server instance"""
        return self.server
    
    async def close(self):
        """Close database connections"""
        await engine.dispose()


# Create global MCP server instance
database_mcp = DatabaseMCP()
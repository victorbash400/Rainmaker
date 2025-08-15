"""
State persistence layer for workflow recovery and state management.

This module handles saving, loading, and archiving workflow states for
recovery and audit purposes.
"""

import json
import asyncio
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import uuid

import structlog
from sqlalchemy import text, select, insert, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.state import RainmakerState, StateManager
from app.db.session import get_async_session
from app.mcp.database import database_mcp

logger = structlog.get_logger(__name__)


class StatePersistence:
    """
    Handles persistence operations for workflow states.
    
    Provides functionality to save, load, archive, and query workflow states
    for recovery and audit purposes.
    """
    
    def __init__(self):
        self.table_name = "workflow_states"
        self._ensure_table_task = asyncio.create_task(self._ensure_tables_exist())
    
    async def _ensure_tables_exist(self):
        """Ensure required database tables exist"""
        try:
            # Create workflow_states table if it doesn't exist
            create_table_sql = f"""
            CREATE TABLE IF NOT EXISTS {self.table_name} (
                workflow_id VARCHAR(255) PRIMARY KEY,
                state_data LONGTEXT NOT NULL,
                stage VARCHAR(50) NOT NULL,
                prospect_name VARCHAR(255),
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL,
                completed_at DATETIME NULL,
                is_archived BOOLEAN DEFAULT FALSE,
                INDEX idx_stage (stage),
                INDEX idx_created_at (created_at),
                INDEX idx_updated_at (updated_at),
                INDEX idx_archived (is_archived)
            )
            """
            
            # Use database MCP to create table
            await database_mcp.server.call_tool("execute_query", {
                "query": create_table_sql,
                "params": {}
            })
            
            logger.info("Workflow states table ensured")
            
        except Exception as e:
            logger.error("Failed to create workflow states table", error=str(e))
            raise
    
    async def save_state(self, workflow_id: str, state: RainmakerState) -> bool:
        """
        Save workflow state to persistence layer.
        
        Args:
            workflow_id: Unique workflow identifier
            state: Workflow state to save
            
        Returns:
            True if saved successfully
        """
        try:
            await self._ensure_table_task  # Wait for table creation
            
            # Serialize state
            serialized_state = StateManager.serialize_state(state)
            
            # Check if record exists
            check_query = f"SELECT workflow_id FROM {self.table_name} WHERE workflow_id = %s"
            check_result = await database_mcp.server.call_tool("execute_query", {
                "query": check_query,
                "params": [workflow_id]
            })
            
            now = datetime.now()
            prospect_name = state.get("prospect_data", {}).get("name", "Unknown")
            current_stage = state.get("current_stage", "unknown")
            completed_at = now if current_stage in ["completed", "failed"] else None
            
            if check_result and not check_result.isError:
                # Update existing record
                update_query = f"""
                UPDATE {self.table_name} 
                SET state_data = %s, stage = %s, prospect_name = %s, 
                    updated_at = %s, completed_at = %s
                WHERE workflow_id = %s
                """
                params = [
                    serialized_state, current_stage, prospect_name,
                    now, completed_at, workflow_id
                ]
            else:
                # Insert new record
                insert_query = f"""
                INSERT INTO {self.table_name} 
                (workflow_id, state_data, stage, prospect_name, created_at, updated_at, completed_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """
                params = [
                    workflow_id, serialized_state, current_stage, prospect_name,
                    now, now, completed_at
                ]
                update_query = insert_query
            
            result = await database_mcp.server.call_tool("execute_query", {
                "query": update_query,
                "params": params
            })
            
            if result.isError:
                raise Exception(f"Database operation failed: {result.content[0].text}")
            
            logger.debug("State saved", workflow_id=workflow_id, stage=current_stage)
            return True
            
        except Exception as e:
            logger.error("Failed to save state", workflow_id=workflow_id, error=str(e))
            return False
    
    async def load_state(self, workflow_id: str) -> Optional[RainmakerState]:
        """
        Load workflow state from persistence layer.
        
        Args:
            workflow_id: Unique workflow identifier
            
        Returns:
            Workflow state or None if not found
        """
        try:
            await self._ensure_table_task
            
            query = f"""
            SELECT state_data FROM {self.table_name} 
            WHERE workflow_id = %s AND is_archived = FALSE
            """
            
            result = await database_mcp.server.call_tool("execute_query", {
                "query": query,
                "params": [workflow_id]
            })
            
            if result.isError or not result.content[0].text:
                return None
            
            # Parse result (assuming it returns JSON with results)
            data = json.loads(result.content[0].text)
            if not data.get("results"):
                return None
            
            state_data = data["results"][0]["state_data"]
            
            # Deserialize state
            state = StateManager.deserialize_state(state_data)
            
            logger.debug("State loaded", workflow_id=workflow_id)
            return state
            
        except Exception as e:
            logger.error("Failed to load state", workflow_id=workflow_id, error=str(e))
            return None
    
    async def archive_state(self, workflow_id: str) -> bool:
        """
        Archive a workflow state (mark as archived, don't delete).
        
        Args:
            workflow_id: Unique workflow identifier
            
        Returns:
            True if archived successfully
        """
        try:
            await self._ensure_table_task
            
            query = f"""
            UPDATE {self.table_name} 
            SET is_archived = TRUE, updated_at = %s
            WHERE workflow_id = %s
            """
            
            result = await database_mcp.server.call_tool("execute_query", {
                "query": query,
                "params": [datetime.now(), workflow_id]
            })
            
            if result.isError:
                raise Exception(f"Archive operation failed: {result.content[0].text}")
            
            logger.info("State archived", workflow_id=workflow_id)
            return True
            
        except Exception as e:
            logger.error("Failed to archive state", workflow_id=workflow_id, error=str(e))
            return False
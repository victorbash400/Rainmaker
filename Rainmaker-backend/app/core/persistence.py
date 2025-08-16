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
from app.db.session import get_db
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
        self._ensure_table_task = None
        self._table_ensured = False
    
    async def _ensure_tables_exist(self):
        """Ensure required database tables exist"""
        if self._table_ensured:
            return
            
        try:
            # Create workflow_states table using direct database session
            async for db in get_db():
                create_table_sql = f"""
                CREATE TABLE IF NOT EXISTS {self.table_name} (
                    workflow_id VARCHAR(255) PRIMARY KEY,
                    state_data TEXT NOT NULL,
                    stage VARCHAR(50) NOT NULL,
                    prospect_name VARCHAR(255),
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL,
                    completed_at DATETIME NULL,
                    is_archived BOOLEAN DEFAULT FALSE
                )
                """
                
                await db.execute(text(create_table_sql))
                await db.commit()
                break
            
            self._table_ensured = True
            logger.info("Workflow states table created successfully")
            
        except Exception as e:
            logger.error("Failed to create workflow states table", error=str(e))
            raise
    
    async def _ensure_table_ready(self):
        """Lazy initialization of table creation"""
        if self._ensure_table_task is None:
            self._ensure_table_task = asyncio.create_task(self._ensure_tables_exist())
        await self._ensure_table_task
    
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
            await self._ensure_table_ready()  # Wait for table creation
            
            # Clean and serialize state with error handling
            try:
                clean_state = StateManager.clean_state_for_persistence(state)
                serialized_state = StateManager.serialize_state(clean_state)
            except Exception as serialize_error:
                logger.error("Failed to serialize state", 
                           workflow_id=workflow_id, 
                           error=str(serialize_error),
                           state_keys=list(state.keys()) if isinstance(state, dict) else "not_dict",
                           clean_state_keys=list(clean_state.keys()) if 'clean_state' in locals() else "not_available")
                return False
            
            # Use direct database session
            async for db in get_db():
                # Check if record exists
                check_query = f"SELECT workflow_id FROM {self.table_name} WHERE workflow_id = :workflow_id"
                check_result = await db.execute(text(check_query), {"workflow_id": workflow_id})
                existing = check_result.fetchone()
                
                now = datetime.now()
                
                # Safely extract prospect name from clean state
                prospect_data = clean_state.get("prospect_data")
                if prospect_data:
                    if hasattr(prospect_data, 'name'):
                        prospect_name = prospect_data.name
                    elif isinstance(prospect_data, dict):
                        prospect_name = prospect_data.get("name", "Unknown")
                    else:
                        prospect_name = "Unknown"
                else:
                    prospect_name = "Unknown"
                
                # Safely extract current stage from clean state
                current_stage = clean_state.get("current_stage", "unknown")
                if hasattr(current_stage, 'value'):
                    current_stage = current_stage.value
                elif not isinstance(current_stage, str):
                    current_stage = str(current_stage)
                
                completed_at = now if current_stage in ["completed", "failed"] else None
                

                
                if existing:
                    # Update existing record
                    update_query = f"""
                    UPDATE {self.table_name} 
                    SET state_data = :state_data, stage = :stage, prospect_name = :prospect_name, 
                        updated_at = :updated_at, completed_at = :completed_at
                    WHERE workflow_id = :workflow_id
                    """
                    params = {
                        "state_data": serialized_state,
                        "stage": current_stage,
                        "prospect_name": prospect_name,
                        "updated_at": now,
                        "completed_at": completed_at,
                        "workflow_id": workflow_id
                    }
                    await db.execute(text(update_query), params)
                else:
                    # Insert new record
                    insert_query = f"""
                    INSERT INTO {self.table_name} 
                    (workflow_id, state_data, stage, prospect_name, created_at, updated_at, completed_at)
                    VALUES (:workflow_id, :state_data, :stage, :prospect_name, :created_at, :updated_at, :completed_at)
                    """
                    params = {
                        "workflow_id": workflow_id,
                        "state_data": serialized_state,
                        "stage": current_stage,
                        "prospect_name": prospect_name,
                        "created_at": now,
                        "updated_at": now,
                        "completed_at": completed_at
                    }
                    await db.execute(text(insert_query), params)
                
                await db.commit()
                break
            
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
            await self._ensure_table_ready()
            
            # Use direct database session
            async for db in get_db():
                query = f"""
                SELECT state_data FROM {self.table_name} 
                WHERE workflow_id = :workflow_id AND is_archived = FALSE
                """
                
                result = await db.execute(text(query), {"workflow_id": workflow_id})
                row = result.fetchone()
                
                if not row:
                    return None
                
                state_data = row[0]
                
                # Deserialize state with error handling
                try:
                    state = StateManager.deserialize_state(state_data)
                except Exception as deserialize_error:
                    logger.error("Failed to deserialize state", 
                               workflow_id=workflow_id, 
                               error=str(deserialize_error),
                               state_data_preview=state_data[:200] if isinstance(state_data, str) else "not_string")
                    return None
                
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
            await self._ensure_table_ready()
            
            query = f"""
            UPDATE {self.table_name} 
            SET is_archived = TRUE, updated_at = ?
            WHERE workflow_id = ?
            """
            
            result = await database_mcp.call_tool("execute_query", {
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
    
    async def get_workflow_states(
        self, 
        stage: Optional[str] = None,
        limit: int = 100,
        include_archived: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get workflow states with optional filtering.
        
        Args:
            stage: Filter by workflow stage
            limit: Maximum number of results
            include_archived: Include archived workflows
            
        Returns:
            List of workflow state summaries
        """
        try:
            await self._ensure_table_ready()
            
            where_clauses = []
            params = []
            
            if not include_archived:
                where_clauses.append("is_archived = FALSE")
                
            if stage:
                where_clauses.append("stage = ?")
                params.append(stage)
            
            where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
            
            query = f"""
            SELECT workflow_id, stage, prospect_name, created_at, updated_at, completed_at
            FROM {self.table_name} 
            WHERE {where_sql}
            ORDER BY updated_at DESC
            LIMIT ?
            """
            params.append(limit)
            
            result = await database_mcp.call_tool("execute_query", {
                "query": query,
                "params": params
            })
            
            if result.isError:
                return []
            
            data = json.loads(result.content[0].text)
            return data.get("results", [])
            
        except Exception as e:
            logger.error("Failed to get workflow states", error=str(e))
            return []


# Global persistence manager instance
persistence_manager = StatePersistence()
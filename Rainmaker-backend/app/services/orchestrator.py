"""
Agent orchestrator class with error handling, retry logic, and state persistence.

This module implements the main orchestrator that manages workflow execution,
handles state persistence, and provides monitoring and control capabilities.
"""

import asyncio
import json
from typing import Dict, List, Optional, Any, Callable, AsyncGenerator
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
import uuid

import structlog
from fastapi import WebSocket

from app.core.state import (
    RainmakerState, StateManager, WorkflowStage, ProspectData, AgentError
)
from app.core.persistence import StatePersistence
from app.services.workflow import rainmaker_workflow
from app.mcp.database import database_mcp

logger = structlog.get_logger(__name__)


class WorkflowMetrics:
    """Workflow execution metrics"""
    def __init__(self):
        self.workflows_started = 0
        self.workflows_completed = 0
        self.workflows_failed = 0
        self.average_duration = 0.0
        self.error_count_by_type = {}
        self.stage_success_rates = {}


class AgentOrchestrator:
    """
    Main orchestrator for Rainmaker agent workflows.
    
    Manages workflow execution, state persistence, error handling,
    and provides monitoring capabilities with WebSocket broadcasting.
    """
    
    def __init__(self):
        self.active_workflows: Dict[str, RainmakerState] = {}
        self.workflow_locks: Dict[str, asyncio.Lock] = {}
        self.websocket_connections: List[WebSocket] = []
        self.metrics = WorkflowMetrics()
        self.state_persistence = StatePersistence()
        
        # Background task for cleanup
        self._cleanup_task = None
        self._running = False
        
        logger.info("AgentOrchestrator initialized")
    
    async def start(self):
        """Start the orchestrator and background tasks"""
        if self._running:
            return
        
        self._running = True
        self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
        
        logger.info("AgentOrchestrator started")
    
    async def stop(self):
        """Stop the orchestrator and cleanup resources"""
        self._running = False
        
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        # Close all WebSocket connections
        for ws in self.websocket_connections.copy():
            try:
                await ws.close()
            except Exception:
                pass
        
        logger.info("AgentOrchestrator stopped")
    
    async def start_workflow(
        self,
        prospect_data: ProspectData,
        workflow_id: Optional[str] = None,
        assigned_human: Optional[str] = None,
        priority: int = 5
    ) -> str:
        """
        Start a new workflow for a prospect.
        
        Args:
            prospect_data: Prospect information
            workflow_id: Optional custom workflow ID
            assigned_human: Optional human assignee
            priority: Workflow priority (1-10, higher is more urgent)
            
        Returns:
            Workflow ID
        """
        if workflow_id is None:
            workflow_id = str(uuid.uuid4())
        
        logger.info(
            "Starting new workflow",
            workflow_id=workflow_id,
            prospect_name=prospect_data.name
        )
        
        # Create initial state
        initial_state = StateManager.create_initial_state(
            prospect_data=prospect_data,
            workflow_id=workflow_id,
            assigned_human=assigned_human
        )
        initial_state["priority"] = priority
        
        # Store in active workflows
        self.active_workflows[workflow_id] = initial_state
        self.workflow_locks[workflow_id] = asyncio.Lock()
        
        # Persist initial state
        self.state_persistence.save_state(workflow_id, initial_state)
        
        # Update metrics
        self.metrics.workflows_started += 1
        
        # Broadcast start event
        await self._broadcast_workflow_event(workflow_id, "workflow_started", initial_state)
        
        # Start execution in background
        asyncio.create_task(self._execute_workflow_safely(workflow_id))
        
        return workflow_id
    
    async def _execute_workflow_safely(self, workflow_id: str):
        """Execute workflow with comprehensive error handling"""
        try:
            async with self.workflow_locks[workflow_id]:
                state = self.active_workflows[workflow_id]
                
                logger.info(
                    "Executing workflow",
                    workflow_id=workflow_id,
                    current_stage=state.get("current_stage")
                )
                
                # Execute the workflow
                final_state = await rainmaker_workflow.execute_workflow(state)
                
                # Update active workflows
                self.active_workflows[workflow_id] = final_state
                
                # Persist final state
                self.state_persistence.save_state(workflow_id, final_state)
                
                # Update metrics
                if final_state.get("current_stage") == WorkflowStage.COMPLETED:
                    self.metrics.workflows_completed += 1
                    
                    # Update average duration
                    if final_state.get("total_duration"):
                        duration = final_state["total_duration"]
                        total_completed = self.metrics.workflows_completed
                        self.metrics.average_duration = (
                            (self.metrics.average_duration * (total_completed - 1) + duration) / total_completed
                        )
                else:
                    self.metrics.workflows_failed += 1
                
                # Broadcast completion event
                await self._broadcast_workflow_event(
                    workflow_id, 
                    "workflow_completed" if final_state.get("current_stage") == WorkflowStage.COMPLETED else "workflow_failed",
                    final_state
                )
                
                logger.info(
                    "Workflow execution completed",
                    workflow_id=workflow_id,
                    final_stage=final_state.get("current_stage"),
                    total_duration=final_state.get("total_duration")
                )
                
        except Exception as e:
            logger.error(
                "Workflow execution failed with exception",
                workflow_id=workflow_id,
                error=str(e)
            )
            
            # Update workflow state with error
            if workflow_id in self.active_workflows:
                error_state = StateManager.add_error(
                    self.active_workflows[workflow_id],
                    "workflow_orchestrator",
                    "execution_error",
                    str(e),
                    {"exception_type": type(e).__name__}
                )
                error_state["current_stage"] = WorkflowStage.FAILED
                
                self.active_workflows[workflow_id] = error_state
                self.state_persistence.save_state(workflow_id, error_state)
            
            # Update metrics
            self.metrics.workflows_failed += 1
            
            # Broadcast error event
            await self._broadcast_workflow_event(workflow_id, "workflow_error", {"error": str(e)})
    
    async def get_workflow_status(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """
        Get current workflow status and progress.
        
        Args:
            workflow_id: Workflow identifier
            
        Returns:
            Workflow status or None if not found
        """
        if workflow_id not in self.active_workflows:
            # Try to load from persistence
            state = self.state_persistence.load_state(workflow_id)
            if state:
                self.active_workflows[workflow_id] = state
                self.workflow_locks[workflow_id] = asyncio.Lock()
            else:
                return None
        
        state = self.active_workflows[workflow_id]
        
        return {
            "workflow_id": workflow_id,
            "current_stage": state.get("current_stage"),
            "completed_stages": state.get("completed_stages", []),
            "progress_percentage": StateManager.calculate_progress(state),
            "prospect_name": state["prospect_data"].name,
            "started_at": state.get("workflow_started_at"),
            "last_updated": state.get("last_updated_at"),
            "total_duration": state.get("total_duration"),
            "errors": [
                {
                    "agent_name": err.agent_name,
                    "error_type": err.error_type,
                    "error_message": err.error_message,
                    "timestamp": err.timestamp
                }
                for err in state.get("errors", [])
            ],
            "human_intervention_needed": state.get("human_intervention_needed", False),
            "approval_pending": state.get("approval_pending", False),
            "retry_count": state.get("retry_count", 0),
            "priority": state.get("priority", 5)
        }
    
    async def pause_workflow(self, workflow_id: str) -> bool:
        """
        Pause a running workflow.
        
        Args:
            workflow_id: Workflow identifier
            
        Returns:
            True if paused successfully
        """
        if workflow_id not in self.active_workflows:
            return False
        
        async with self.workflow_locks[workflow_id]:
            state = self.active_workflows[workflow_id]
            
            # Add pause flag to state
            state["paused"] = True
            state["paused_at"] = datetime.now()
            
            self.state_persistence.save_state(workflow_id, state)
            await self._broadcast_workflow_event(workflow_id, "workflow_paused", state)
            
            logger.info("Workflow paused", workflow_id=workflow_id)
            return True
    
    async def resume_workflow(self, workflow_id: str) -> bool:
        """
        Resume a paused workflow.
        
        Args:
            workflow_id: Workflow identifier
            
        Returns:
            True if resumed successfully
        """
        if workflow_id not in self.active_workflows:
            return False
        
        async with self.workflow_locks[workflow_id]:
            state = self.active_workflows[workflow_id]
            
            if not state.get("paused"):
                return False  # Not paused
            
            # Remove pause flag
            state.pop("paused", None)
            state.pop("paused_at", None)
            state["resumed_at"] = datetime.now()
            
            self.state_persistence.save_state(workflow_id, state)
            await self._broadcast_workflow_event(workflow_id, "workflow_resumed", state)
            
            # Restart execution
            asyncio.create_task(self._execute_workflow_safely(workflow_id))
            
            logger.info("Workflow resumed", workflow_id=workflow_id)
            return True
    
    async def retry_workflow(self, workflow_id: str, from_stage: Optional[WorkflowStage] = None) -> bool:
        """
        Retry a failed workflow from a specific stage.
        
        Args:
            workflow_id: Workflow identifier
            from_stage: Optional stage to retry from (default: current stage)
            
        Returns:
            True if retry started successfully
        """
        if workflow_id not in self.active_workflows:
            return False
        
        async with self.workflow_locks[workflow_id]:
            state = self.active_workflows[workflow_id]
            
            if from_stage:
                state["current_stage"] = from_stage
                # Remove this stage from completed stages if present
                completed = state.get("completed_stages", [])
                if from_stage in completed:
                    completed.remove(from_stage)
                    state["completed_stages"] = completed
            
            # Reset error-related flags
            state["human_intervention_needed"] = False
            state["approval_pending"] = False
            state["retry_count"] = state.get("retry_count", 0) + 1
            state["last_updated_at"] = datetime.now()
            
            self.state_persistence.save_state(workflow_id, state)
            await self._broadcast_workflow_event(workflow_id, "workflow_retrying", state)
            
            # Restart execution
            asyncio.create_task(self._execute_workflow_safely(workflow_id))
            
            logger.info(
                "Workflow retry initiated",
                workflow_id=workflow_id,
                from_stage=from_stage,
                retry_count=state["retry_count"]
            )
            return True
    
    async def cancel_workflow(self, workflow_id: str, reason: str = "Cancelled by user") -> bool:
        """
        Cancel a running workflow.
        
        Args:
            workflow_id: Workflow identifier
            reason: Cancellation reason
            
        Returns:
            True if cancelled successfully
        """
        if workflow_id not in self.active_workflows:
            return False
        
        async with self.workflow_locks[workflow_id]:
            state = self.active_workflows[workflow_id]
            
            # Mark as cancelled
            state["current_stage"] = WorkflowStage.FAILED
            state["cancelled"] = True
            state["cancelled_at"] = datetime.now()
            state["cancellation_reason"] = reason
            
            self.state_persistence.save_state(workflow_id, state)
            await self._broadcast_workflow_event(workflow_id, "workflow_cancelled", {
                "reason": reason,
                "cancelled_at": datetime.now()
            })
            
            logger.info("Workflow cancelled", workflow_id=workflow_id, reason=reason)
            return True
    
    async def get_active_workflows(self) -> List[Dict[str, Any]]:
        """Get all active workflows with their status"""
        workflows = []
        
        for workflow_id in list(self.active_workflows.keys()):
            status = await self.get_workflow_status(workflow_id)
            if status:
                workflows.append(status)
        
        # Sort by priority and start time
        workflows.sort(key=lambda x: (-x.get("priority", 5), x.get("started_at", datetime.min)))
        
        return workflows
    
    async def get_metrics(self) -> Dict[str, Any]:
        """Get orchestrator metrics"""
        active_count = len(self.active_workflows)
        
        # Calculate stage success rates
        stage_counts = {}
        for state in self.active_workflows.values():
            for stage in state.get("completed_stages", []):
                stage_counts[stage.value] = stage_counts.get(stage.value, 0) + 1
        
        return {
            "workflows_started": self.metrics.workflows_started,
            "workflows_completed": self.metrics.workflows_completed,
            "workflows_failed": self.metrics.workflows_failed,
            "workflows_active": active_count,
            "average_duration_seconds": self.metrics.average_duration,
            "error_count_by_type": self.metrics.error_count_by_type,
            "stage_completion_counts": stage_counts,
            "websocket_connections": len(self.websocket_connections)
        }
    
    async def add_websocket(self, websocket: WebSocket):
        """Add a WebSocket connection for real-time updates"""
        self.websocket_connections.append(websocket)
        logger.info("WebSocket connection added", total_connections=len(self.websocket_connections))
    
    async def remove_websocket(self, websocket: WebSocket):
        """Remove a WebSocket connection"""
        if websocket in self.websocket_connections:
            self.websocket_connections.remove(websocket)
            logger.info("WebSocket connection removed", total_connections=len(self.websocket_connections))
    
    async def _broadcast_workflow_event(self, workflow_id: str, event_type: str, data: Any):
        """Broadcast workflow events to connected WebSocket clients"""
        if not self.websocket_connections:
            return
        
        message = {
            "type": "workflow_event",
            "workflow_id": workflow_id,
            "event_type": event_type,
            "timestamp": datetime.now().isoformat(),
            "data": self._serialize_event_data(data)
        }
        
        # Send to all connected clients
        disconnected_clients = []
        for websocket in self.websocket_connections:
            try:
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                logger.warning("Failed to send WebSocket message", error=str(e))
                disconnected_clients.append(websocket)
        
        # Remove disconnected clients
        for client in disconnected_clients:
            await self.remove_websocket(client)
    
    def _serialize_event_data(self, data: Any) -> Dict[str, Any]:
        """Serialize event data for WebSocket transmission"""
        if isinstance(data, dict):
            return data
        elif hasattr(data, '__dict__'):
            return data.__dict__
        elif hasattr(data, 'dict'):
            return data.dict()
        else:
            return {"value": str(data)}
    
    async def _periodic_cleanup(self):
        """Periodic cleanup of completed workflows and old data"""
        while self._running:
            try:
                await asyncio.sleep(3600)  # Run every hour
                
                logger.info("Running periodic cleanup")
                
                # Remove completed workflows older than 24 hours
                cutoff_time = datetime.now() - timedelta(hours=24)
                workflows_to_remove = []
                
                for workflow_id, state in self.active_workflows.items():
                    if (state.get("current_stage") in [WorkflowStage.COMPLETED, WorkflowStage.FAILED] and
                        state.get("last_updated_at", datetime.max) < cutoff_time):
                        workflows_to_remove.append(workflow_id)
                
                for workflow_id in workflows_to_remove:
                    # Archive before removing
                    self.state_persistence.archive_state(workflow_id)
                    
                    # Remove from active workflows
                    self.active_workflows.pop(workflow_id, None)
                    self.workflow_locks.pop(workflow_id, None)
                
                logger.info(
                    "Cleanup completed",
                    workflows_archived=len(workflows_to_remove),
                    active_workflows=len(self.active_workflows)
                )
                
            except Exception as e:
                logger.error("Periodic cleanup failed", error=str(e))


# Global orchestrator instance
agent_orchestrator = AgentOrchestrator()
"""
Human-in-the-loop approval workflow system.

This module handles approval requests, notifications, and decision processing
for workflow tasks that require human oversight.
"""

import asyncio
import json
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from enum import Enum
import uuid

import structlog
from fastapi import WebSocket

from app.core.state import RainmakerState, StateManager, WorkflowStage
from app.mcp.database import database_mcp
from app.mcp.email import email_mcp

logger = structlog.get_logger(__name__)


class ApprovalType(str, Enum):
    """Types of approval requests"""
    OUTREACH_MESSAGE = "outreach_message"
    PROPOSAL_CONTENT = "proposal_content"
    MEETING_SCHEDULE = "meeting_schedule"
    DATA_QUALITY = "data_quality"
    WORKFLOW_RETRY = "workflow_retry"
    ESCALATION = "escalation"


class ApprovalStatus(str, Enum):
    """Status of approval requests"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class ApprovalRequest:
    """Represents a human approval request"""
    
    def __init__(
        self,
        approval_id: str,
        workflow_id: str,
        approval_type: ApprovalType,
        data: Dict[str, Any],
        reason: str,
        requested_by: Optional[str] = None,
        assigned_to: Optional[str] = None,
        priority: int = 5,
        expires_at: Optional[datetime] = None
    ):
        self.approval_id = approval_id
        self.workflow_id = workflow_id
        self.approval_type = approval_type
        self.data = data
        self.reason = reason
        self.requested_by = requested_by
        self.assigned_to = assigned_to
        self.priority = priority
        self.status = ApprovalStatus.PENDING
        self.requested_at = datetime.now()
        self.expires_at = expires_at or (datetime.now() + timedelta(hours=24))
        self.responded_at: Optional[datetime] = None
        self.response_data: Dict[str, Any] = {}
        self.notes: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "approval_id": self.approval_id,
            "workflow_id": self.workflow_id,
            "approval_type": self.approval_type.value,
            "data": self.data,
            "reason": self.reason,
            "requested_by": self.requested_by,
            "assigned_to": self.assigned_to,
            "priority": self.priority,
            "status": self.status.value,
            "requested_at": self.requested_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "responded_at": self.responded_at.isoformat() if self.responded_at else None,
            "response_data": self.response_data,
            "notes": self.notes
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ApprovalRequest":
        """Create from dictionary"""
        request = cls(
            approval_id=data["approval_id"],
            workflow_id=data["workflow_id"],
            approval_type=ApprovalType(data["approval_type"]),
            data=data["data"],
            reason=data["reason"],
            requested_by=data.get("requested_by"),
            assigned_to=data.get("assigned_to"),
            priority=data.get("priority", 5),
            expires_at=datetime.fromisoformat(data["expires_at"]) if data.get("expires_at") else None
        )
        
        request.status = ApprovalStatus(data.get("status", "pending"))
        request.requested_at = datetime.fromisoformat(data["requested_at"])
        request.responded_at = datetime.fromisoformat(data["responded_at"]) if data.get("responded_at") else None
        request.response_data = data.get("response_data", {})
        request.notes = data.get("notes", "")
        
        return request


class ApprovalSystem:
    """
    Human-in-the-loop approval system for workflow tasks.
    
    Manages approval requests, notifications, and decision processing.
    """
    
    def __init__(self):
        self.pending_approvals: Dict[str, ApprovalRequest] = {}
        self.approval_callbacks: Dict[str, Callable[[ApprovalRequest], None]] = {}
        self.websocket_connections: List[WebSocket] = []
        self.table_name = "approval_requests"
        
        # Start background tasks
        self._running = False
        self._expiry_task = None
        self._notification_task = None
        
        logger.info("ApprovalSystem initialized")
    
    async def start(self):
        """Start the approval system and background tasks"""
        if self._running:
            return
        
        self._running = True
        await self._ensure_table_exists()
        await self._load_pending_approvals()
        
        # Start background tasks
        self._expiry_task = asyncio.create_task(self._check_expired_approvals())
        self._notification_task = asyncio.create_task(self._send_pending_notifications())
        
        logger.info("ApprovalSystem started")
    
    async def stop(self):
        """Stop the approval system"""
        self._running = False
        
        # Cancel background tasks
        if self._expiry_task:
            self._expiry_task.cancel()
        if self._notification_task:
            self._notification_task.cancel()
        
        # Close WebSocket connections
        for ws in self.websocket_connections.copy():
            try:
                await ws.close()
            except Exception:
                pass
        
        logger.info("ApprovalSystem stopped")
    
    async def _ensure_table_exists(self):
        """Ensure approval requests table exists"""
        create_table_sql = f"""
        CREATE TABLE IF NOT EXISTS {self.table_name} (
            approval_id VARCHAR(255) PRIMARY KEY,
            workflow_id VARCHAR(255) NOT NULL,
            approval_type VARCHAR(50) NOT NULL,
            approval_data LONGTEXT NOT NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'pending',
            requested_at DATETIME NOT NULL,
            expires_at DATETIME NOT NULL,
            responded_at DATETIME NULL,
            assigned_to VARCHAR(255),
            priority INT DEFAULT 5,
            created_at DATETIME NOT NULL DEFAULT NOW(),
            updated_at DATETIME NOT NULL DEFAULT NOW() ON UPDATE NOW(),
            INDEX idx_status (status),
            INDEX idx_workflow (workflow_id),
            INDEX idx_assigned (assigned_to),
            INDEX idx_expires (expires_at),
            INDEX idx_priority (priority)
        )
        """
        
        try:
            await database_mcp.server.call_tool("execute_query", {
                "query": create_table_sql,
                "params": {}
            })
            logger.info("Approval requests table ensured")
        except Exception as e:
            logger.error("Failed to create approval requests table", error=str(e))
            raise
    
    async def _load_pending_approvals(self):
        """Load pending approvals from database"""
        try:
            query = f"""
            SELECT approval_data FROM {self.table_name}
            WHERE status = 'pending' AND expires_at > NOW()
            ORDER BY priority DESC, requested_at ASC
            """
            
            result = await database_mcp.server.call_tool("execute_query", {
                "query": query,
                "params": []
            })
            
            if not result.isError:
                data = json.loads(result.content[0].text)
                for row in data.get("results", []):
                    approval_data = json.loads(row["approval_data"])
                    approval = ApprovalRequest.from_dict(approval_data)
                    self.pending_approvals[approval.approval_id] = approval
            
            logger.info("Loaded pending approvals", count=len(self.pending_approvals))
            
        except Exception as e:
            logger.error("Failed to load pending approvals", error=str(e))
    
    async def request_approval(
        self,
        workflow_id: str,
        approval_type: ApprovalType,
        data: Dict[str, Any],
        reason: str,
        requested_by: Optional[str] = None,
        assigned_to: Optional[str] = None,
        priority: int = 5,
        expires_in_hours: int = 24,
        callback: Optional[Callable[[ApprovalRequest], None]] = None
    ) -> str:
        """
        Request human approval for a workflow task.
        
        Args:
            workflow_id: Associated workflow ID
            approval_type: Type of approval needed
            data: Data requiring approval
            reason: Reason for approval request
            requested_by: Who requested approval
            assigned_to: Who should approve (optional)
            priority: Priority level (1-10, higher is more urgent)
            expires_in_hours: Hours until approval expires
            callback: Optional callback when decision is made
            
        Returns:
            Approval request ID
        """
        approval_id = str(uuid.uuid4())
        expires_at = datetime.now() + timedelta(hours=expires_in_hours)
        
        approval = ApprovalRequest(
            approval_id=approval_id,
            workflow_id=workflow_id,
            approval_type=approval_type,
            data=data,
            reason=reason,
            requested_by=requested_by,
            assigned_to=assigned_to,
            priority=priority,
            expires_at=expires_at
        )
        
        # Store in memory
        self.pending_approvals[approval_id] = approval
        
        # Register callback
        if callback:
            self.approval_callbacks[approval_id] = callback
        
        # Persist to database
        await self._save_approval_request(approval)
        
        # Send notifications
        await self._send_approval_notification(approval)
        
        # Broadcast to WebSocket clients
        await self._broadcast_approval_event(approval_id, "approval_requested", approval.to_dict())
        
        logger.info(
            "Approval requested",
            approval_id=approval_id,
            workflow_id=workflow_id,
            approval_type=approval_type.value,
            priority=priority
        )
        
        return approval_id
    
    async def process_approval_decision(
        self,
        approval_id: str,
        approved: bool,
        response_data: Optional[Dict[str, Any]] = None,
        notes: str = "",
        decided_by: Optional[str] = None
    ) -> bool:
        """
        Process an approval decision.
        
        Args:
            approval_id: Approval request ID
            approved: Whether approved or rejected
            response_data: Additional response data
            notes: Decision notes
            decided_by: Who made the decision
            
        Returns:
            True if processed successfully
        """
        if approval_id not in self.pending_approvals:
            logger.warning("Approval request not found", approval_id=approval_id)
            return False
        
        approval = self.pending_approvals[approval_id]
        
        # Check if expired
        if datetime.now() > approval.expires_at:
            approval.status = ApprovalStatus.EXPIRED
            logger.warning("Approval request expired", approval_id=approval_id)
            return False
        
        # Update approval
        approval.status = ApprovalStatus.APPROVED if approved else ApprovalStatus.REJECTED
        approval.responded_at = datetime.now()
        approval.response_data = response_data or {}
        approval.notes = notes
        
        if decided_by:
            approval.response_data["decided_by"] = decided_by
        
        # Update in database
        await self._update_approval_request(approval)
        
        # Execute callback
        if approval_id in self.approval_callbacks:
            try:
                callback = self.approval_callbacks.pop(approval_id)
                await asyncio.create_task(asyncio.coroutine(callback)(approval))
            except Exception as e:
                logger.error("Approval callback failed", error=str(e), approval_id=approval_id)
        
        # Remove from pending
        self.pending_approvals.pop(approval_id, None)
        
        # Broadcast decision
        await self._broadcast_approval_event(
            approval_id, 
            "approval_decided", 
            approval.to_dict()
        )
        
        logger.info(
            "Approval decision processed",
            approval_id=approval_id,
            approved=approved,
            decided_by=decided_by
        )
        
        return True
    
    async def get_pending_approvals(
        self,
        assigned_to: Optional[str] = None,
        approval_type: Optional[ApprovalType] = None,
        workflow_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get pending approval requests.
        
        Args:
            assigned_to: Filter by assignee
            approval_type: Filter by approval type
            workflow_id: Filter by workflow ID
            
        Returns:
            List of pending approvals
        """
        approvals = []
        
        for approval in self.pending_approvals.values():
            if assigned_to and approval.assigned_to != assigned_to:
                continue
            if approval_type and approval.approval_type != approval_type:
                continue
            if workflow_id and approval.workflow_id != workflow_id:
                continue
            
            approvals.append(approval.to_dict())
        
        # Sort by priority and date
        approvals.sort(key=lambda x: (-x["priority"], x["requested_at"]))
        
        return approvals
    
    async def cancel_approval(self, approval_id: str, reason: str = "") -> bool:
        """
        Cancel a pending approval request.
        
        Args:
            approval_id: Approval request ID
            reason: Cancellation reason
            
        Returns:
            True if cancelled successfully
        """
        if approval_id not in self.pending_approvals:
            return False
        
        approval = self.pending_approvals.pop(approval_id)
        approval.status = ApprovalStatus.CANCELLED
        approval.responded_at = datetime.now()
        approval.notes = f"Cancelled: {reason}"
        
        # Update in database
        await self._update_approval_request(approval)
        
        # Remove callback
        self.approval_callbacks.pop(approval_id, None)
        
        # Broadcast cancellation
        await self._broadcast_approval_event(approval_id, "approval_cancelled", {
            "approval_id": approval_id,
            "reason": reason
        })
        
        logger.info("Approval cancelled", approval_id=approval_id, reason=reason)
        return True
    
    async def _save_approval_request(self, approval: ApprovalRequest):
        """Save approval request to database"""
        try:
            query = f"""
            INSERT INTO {self.table_name} 
            (approval_id, workflow_id, approval_type, approval_data, status, 
             requested_at, expires_at, assigned_to, priority)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            params = [
                approval.approval_id,
                approval.workflow_id,
                approval.approval_type.value,
                json.dumps(approval.to_dict()),
                approval.status.value,
                approval.requested_at,
                approval.expires_at,
                approval.assigned_to,
                approval.priority
            ]
            
            await database_mcp.server.call_tool("execute_query", {
                "query": query,
                "params": params
            })
            
        except Exception as e:
            logger.error("Failed to save approval request", error=str(e))
    
    async def _update_approval_request(self, approval: ApprovalRequest):
        """Update approval request in database"""
        try:
            query = f"""
            UPDATE {self.table_name}
            SET approval_data = %s, status = %s, responded_at = %s, updated_at = NOW()
            WHERE approval_id = %s
            """
            
            params = [
                json.dumps(approval.to_dict()),
                approval.status.value,
                approval.responded_at,
                approval.approval_id
            ]
            
            await database_mcp.server.call_tool("execute_query", {
                "query": query,
                "params": params
            })
            
        except Exception as e:
            logger.error("Failed to update approval request", error=str(e))
    
    async def _send_approval_notification(self, approval: ApprovalRequest):
        """Send notification for new approval request"""
        try:
            # Send email notification if assigned to someone
            if approval.assigned_to:
                await email_mcp.server.call_tool("send_approval_notification", {
                    "recipient": approval.assigned_to,
                    "approval_id": approval.approval_id,
                    "approval_type": approval.approval_type.value,
                    "workflow_id": approval.workflow_id,
                    "reason": approval.reason,
                    "priority": approval.priority,
                    "expires_at": approval.expires_at.isoformat()
                })
            
        except Exception as e:
            logger.error("Failed to send approval notification", error=str(e))
    
    async def _check_expired_approvals(self):
        """Background task to check for expired approvals"""
        while self._running:
            try:
                await asyncio.sleep(300)  # Check every 5 minutes
                
                now = datetime.now()
                expired_approvals = []
                
                for approval_id, approval in self.pending_approvals.items():
                    if now > approval.expires_at:
                        expired_approvals.append(approval_id)
                
                for approval_id in expired_approvals:
                    approval = self.pending_approvals.pop(approval_id, None)
                    if approval:
                        approval.status = ApprovalStatus.EXPIRED
                        approval.responded_at = now
                        approval.notes = "Expired - no response received"
                        
                        await self._update_approval_request(approval)
                        await self._broadcast_approval_event(approval_id, "approval_expired", {
                            "approval_id": approval_id
                        })
                        
                        # Remove callback
                        self.approval_callbacks.pop(approval_id, None)
                
                if expired_approvals:
                    logger.info("Expired approvals processed", count=len(expired_approvals))
                
            except Exception as e:
                logger.error("Error checking expired approvals", error=str(e))
    
    async def _send_pending_notifications(self):
        """Background task to send periodic notifications for pending approvals"""
        while self._running:
            try:
                await asyncio.sleep(3600)  # Check every hour
                
                # Send reminders for high-priority pending approvals
                high_priority_approvals = [
                    approval for approval in self.pending_approvals.values()
                    if approval.priority >= 8 and 
                    (datetime.now() - approval.requested_at).total_seconds() > 1800  # > 30 minutes
                ]
                
                for approval in high_priority_approvals:
                    await self._send_approval_notification(approval)
                
                if high_priority_approvals:
                    logger.info("Sent reminder notifications", count=len(high_priority_approvals))
                
            except Exception as e:
                logger.error("Error sending pending notifications", error=str(e))
    
    async def add_websocket(self, websocket: WebSocket):
        """Add WebSocket connection for real-time approval updates"""
        self.websocket_connections.append(websocket)
        logger.info("Approval WebSocket connection added", total=len(self.websocket_connections))
    
    async def remove_websocket(self, websocket: WebSocket):
        """Remove WebSocket connection"""
        if websocket in self.websocket_connections:
            self.websocket_connections.remove(websocket)
            logger.info("Approval WebSocket connection removed", total=len(self.websocket_connections))
    
    async def _broadcast_approval_event(self, approval_id: str, event_type: str, data: Dict[str, Any]):
        """Broadcast approval events to WebSocket clients"""
        if not self.websocket_connections:
            return
        
        message = {
            "type": "approval_event",
            "approval_id": approval_id,
            "event_type": event_type,
            "timestamp": datetime.now().isoformat(),
            "data": data
        }
        
        disconnected_clients = []
        for websocket in self.websocket_connections:
            try:
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                logger.warning("Failed to send approval WebSocket message", error=str(e))
                disconnected_clients.append(websocket)
        
        # Remove disconnected clients
        for client in disconnected_clients:
            await self.remove_websocket(client)


# Global approval system instance
approval_system = ApprovalSystem()
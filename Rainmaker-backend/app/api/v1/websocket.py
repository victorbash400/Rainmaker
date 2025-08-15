"""
WebSocket endpoints for real-time workflow and approval updates.

This module provides WebSocket connections for broadcasting workflow progress,
approval requests, and system events to connected clients.
"""

import json
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime

import structlog
from fastapi import WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from fastapi.routing import APIRouter

from app.services.orchestrator import agent_orchestrator
from app.services.approval import approval_system
from app.core.security import get_current_user
from app.db.schemas import User

logger = structlog.get_logger(__name__)

router = APIRouter()


class WebSocketManager:
    """
    Manages WebSocket connections and message broadcasting.
    
    Handles client connections, authentication, subscription management,
    and real-time event broadcasting.
    """
    
    def __init__(self):
        self.active_connections: Dict[str, Dict[str, Any]] = {}
        self.subscriptions: Dict[str, List[str]] = {
            "workflows": [],
            "approvals": [], 
            "system": []
        }
        self.connection_count = 0
    
    async def connect(
        self, 
        websocket: WebSocket, 
        client_id: str,
        user: Optional[User] = None
    ):
        """Accept WebSocket connection and register client"""
        await websocket.accept()
        
        self.active_connections[client_id] = {
            "websocket": websocket,
            "user": user,
            "connected_at": datetime.now(),
            "subscriptions": [],
            "last_ping": datetime.now()
        }
        
        self.connection_count += 1
        
        # Register with orchestrator and approval system
        await agent_orchestrator.add_websocket(websocket)
        await approval_system.add_websocket(websocket)
        
        # Send welcome message
        await self.send_to_client(client_id, {
            "type": "connection_established",
            "client_id": client_id,
            "timestamp": datetime.now().isoformat(),
            "server_info": {
                "active_workflows": len(agent_orchestrator.active_workflows),
                "pending_approvals": len(approval_system.pending_approvals)
            }
        })
        
        logger.info("WebSocket client connected", client_id=client_id, total_connections=self.connection_count)
    
    async def disconnect(self, client_id: str):
        """Remove client connection and cleanup"""
        if client_id not in self.active_connections:
            return
        
        connection_info = self.active_connections.pop(client_id)
        websocket = connection_info["websocket"]
        
        # Unsubscribe from all channels
        for subscription_type, subscribers in self.subscriptions.items():
            if client_id in subscribers:
                subscribers.remove(client_id)
        
        # Remove from orchestrator and approval system
        await agent_orchestrator.remove_websocket(websocket)
        await approval_system.remove_websocket(websocket)
        
        self.connection_count -= 1
        
        logger.info("WebSocket client disconnected", client_id=client_id, total_connections=self.connection_count)
    
    async def send_to_client(self, client_id: str, message: Dict[str, Any]) -> bool:
        """Send message to specific client"""
        if client_id not in self.active_connections:
            return False
        
        try:
            websocket = self.active_connections[client_id]["websocket"]
            await websocket.send_text(json.dumps(message))
            return True
        except Exception as e:
            logger.warning("Failed to send message to client", client_id=client_id, error=str(e))
            await self.disconnect(client_id)
            return False
    
    async def broadcast_to_subscribers(self, subscription_type: str, message: Dict[str, Any]):
        """Broadcast message to all subscribers of a specific type"""
        if subscription_type not in self.subscriptions:
            return
        
        subscribers = self.subscriptions[subscription_type].copy()
        failed_clients = []
        
        for client_id in subscribers:
            success = await self.send_to_client(client_id, message)
            if not success:
                failed_clients.append(client_id)
        
        # Remove failed clients from subscriptions
        for client_id in failed_clients:
            if client_id in self.subscriptions[subscription_type]:
                self.subscriptions[subscription_type].remove(client_id)
    
    async def handle_client_message(self, client_id: str, message: Dict[str, Any]):
        """Process incoming client messages"""
        try:
            message_type = message.get("type")
            
            if message_type == "subscribe":
                await self._handle_subscription(client_id, message)
            elif message_type == "unsubscribe":
                await self._handle_unsubscription(client_id, message)
            elif message_type == "ping":
                await self._handle_ping(client_id, message)
            elif message_type == "get_status":
                await self._handle_status_request(client_id, message)
            else:
                await self.send_to_client(client_id, {
                    "type": "error",
                    "message": f"Unknown message type: {message_type}"
                })
        
        except Exception as e:
            logger.error("Error handling client message", client_id=client_id, error=str(e))
            await self.send_to_client(client_id, {
                "type": "error",
                "message": "Internal server error processing message"
            })
    
    async def _handle_subscription(self, client_id: str, message: Dict[str, Any]):
        """Handle subscription requests"""
        subscription_types = message.get("subscriptions", [])
        
        for sub_type in subscription_types:
            if sub_type in self.subscriptions:
                if client_id not in self.subscriptions[sub_type]:
                    self.subscriptions[sub_type].append(client_id)
                
                # Update client subscription list
                if client_id in self.active_connections:
                    client_subs = self.active_connections[client_id]["subscriptions"]
                    if sub_type not in client_subs:
                        client_subs.append(sub_type)
        
        await self.send_to_client(client_id, {
            "type": "subscription_confirmed",
            "subscriptions": subscription_types,
            "timestamp": datetime.now().isoformat()
        })
        
        logger.info("Client subscriptions updated", client_id=client_id, subscriptions=subscription_types)
    
    async def _handle_unsubscription(self, client_id: str, message: Dict[str, Any]):
        """Handle unsubscription requests"""
        subscription_types = message.get("subscriptions", [])
        
        for sub_type in subscription_types:
            if sub_type in self.subscriptions:
                if client_id in self.subscriptions[sub_type]:
                    self.subscriptions[sub_type].remove(client_id)
                
                # Update client subscription list
                if client_id in self.active_connections:
                    client_subs = self.active_connections[client_id]["subscriptions"]
                    if sub_type in client_subs:
                        client_subs.remove(sub_type)
        
        await self.send_to_client(client_id, {
            "type": "unsubscription_confirmed",
            "subscriptions": subscription_types,
            "timestamp": datetime.now().isoformat()
        })
    
    async def _handle_ping(self, client_id: str, message: Dict[str, Any]):
        """Handle ping messages and update last activity"""
        if client_id in self.active_connections:
            self.active_connections[client_id]["last_ping"] = datetime.now()
        
        await self.send_to_client(client_id, {
            "type": "pong",
            "timestamp": datetime.now().isoformat()
        })
    
    async def _handle_status_request(self, client_id: str, message: Dict[str, Any]):
        """Handle status information requests"""
        request_type = message.get("request", "general")
        
        if request_type == "workflows":
            workflows = await agent_orchestrator.get_active_workflows()
            response = {
                "type": "status_response",
                "request": "workflows",
                "data": workflows,
                "timestamp": datetime.now().isoformat()
            }
        elif request_type == "approvals":
            approvals = await approval_system.get_pending_approvals()
            response = {
                "type": "status_response",
                "request": "approvals", 
                "data": approvals,
                "timestamp": datetime.now().isoformat()
            }
        elif request_type == "metrics":
            metrics = await agent_orchestrator.get_metrics()
            response = {
                "type": "status_response",
                "request": "metrics",
                "data": metrics,
                "timestamp": datetime.now().isoformat()
            }
        else:
            response = {
                "type": "status_response",
                "request": "general",
                "data": {
                    "active_connections": self.connection_count,
                    "active_workflows": len(agent_orchestrator.active_workflows),
                    "pending_approvals": len(approval_system.pending_approvals),
                    "server_time": datetime.now().isoformat()
                },
                "timestamp": datetime.now().isoformat()
            }
        
        await self.send_to_client(client_id, response)
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get WebSocket connection statistics"""
        return {
            "total_connections": self.connection_count,
            "subscription_counts": {
                sub_type: len(subscribers) 
                for sub_type, subscribers in self.subscriptions.items()
            },
            "active_connections": [
                {
                    "client_id": client_id,
                    "connected_at": conn["connected_at"].isoformat(),
                    "subscriptions": conn["subscriptions"],
                    "last_ping": conn["last_ping"].isoformat(),
                    "user": conn["user"].email if conn.get("user") else None
                }
                for client_id, conn in self.active_connections.items()
            ]
        }


# Global WebSocket manager
websocket_manager = WebSocketManager()


@router.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """
    Main WebSocket endpoint for real-time updates.
    
    Clients can subscribe to different event types:
    - workflows: Workflow progress and status updates
    - approvals: Approval requests and decisions
    - system: System events and metrics
    """
    await websocket_manager.connect(websocket, client_id)
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                await websocket_manager.handle_client_message(client_id, message)
            except json.JSONDecodeError:
                await websocket_manager.send_to_client(client_id, {
                    "type": "error",
                    "message": "Invalid JSON format"
                })
            except Exception as e:
                logger.error("Error processing WebSocket message", client_id=client_id, error=str(e))
                await websocket_manager.send_to_client(client_id, {
                    "type": "error", 
                    "message": "Error processing message"
                })
    
    except WebSocketDisconnect:
        await websocket_manager.disconnect(client_id)
    except Exception as e:
        logger.error("WebSocket error", client_id=client_id, error=str(e))
        await websocket_manager.disconnect(client_id)


@router.websocket("/ws/authenticated/{client_id}")
async def authenticated_websocket_endpoint(
    websocket: WebSocket, 
    client_id: str,
    # Note: WebSocket authentication would need to be handled differently in production
    # This is a simplified version - in practice you'd verify tokens in the connection
):
    """
    Authenticated WebSocket endpoint with user context.
    
    Provides additional features for authenticated users:
    - User-specific workflow and approval filtering
    - Enhanced permissions for system operations
    - Personalized notifications
    """
    # In a real implementation, you'd extract and verify the user from
    # the WebSocket headers or query parameters
    user = None  # Would be extracted from authentication
    
    await websocket_manager.connect(websocket, client_id, user)
    
    try:
        while True:
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                await websocket_manager.handle_client_message(client_id, message)
            except json.JSONDecodeError:
                await websocket_manager.send_to_client(client_id, {
                    "type": "error",
                    "message": "Invalid JSON format"
                })
            except Exception as e:
                logger.error("Error processing authenticated WebSocket message", 
                           client_id=client_id, error=str(e))
                await websocket_manager.send_to_client(client_id, {
                    "type": "error",
                    "message": "Error processing message"
                })
    
    except WebSocketDisconnect:
        await websocket_manager.disconnect(client_id)
    except Exception as e:
        logger.error("Authenticated WebSocket error", client_id=client_id, error=str(e))
        await websocket_manager.disconnect(client_id)


# Additional utility endpoints for WebSocket management

@router.get("/websocket/stats")
async def get_websocket_stats():
    """Get WebSocket connection statistics"""
    return websocket_manager.get_connection_stats()


@router.post("/websocket/broadcast")
async def broadcast_message(
    message: Dict[str, Any],
    subscription_type: str = "system",
    # current_user: User = Depends(get_current_user)  # Uncomment for auth
):
    """
    Broadcast a custom message to all subscribers of a specific type.
    
    Requires appropriate permissions.
    """
    # Add metadata to the message
    message.update({
        "timestamp": datetime.now().isoformat(),
        "broadcast": True
    })
    
    await websocket_manager.broadcast_to_subscribers(subscription_type, message)
    
    return {
        "success": True,
        "message": "Broadcast sent",
        "subscription_type": subscription_type,
        "subscriber_count": len(websocket_manager.subscriptions.get(subscription_type, []))
    }


# Background task for connection health monitoring
async def monitor_websocket_connections():
    """Background task to monitor and cleanup stale WebSocket connections"""
    while True:
        try:
            await asyncio.sleep(60)  # Check every minute
            
            current_time = datetime.now()
            stale_connections = []
            
            for client_id, conn_info in websocket_manager.active_connections.items():
                last_ping = conn_info["last_ping"]
                if (current_time - last_ping).total_seconds() > 300:  # 5 minutes
                    stale_connections.append(client_id)
            
            for client_id in stale_connections:
                logger.info("Removing stale WebSocket connection", client_id=client_id)
                await websocket_manager.disconnect(client_id)
            
            if stale_connections:
                logger.info("Cleaned up stale connections", count=len(stale_connections))
        
        except Exception as e:
            logger.error("Error in WebSocket connection monitoring", error=str(e))


# Start the monitoring task when the module is loaded
asyncio.create_task(monitor_websocket_connections())
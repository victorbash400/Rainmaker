"""
Browser Viewer WebSocket API for real-time browser automation viewing
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict, Set
import json
import structlog
import asyncio

logger = structlog.get_logger(__name__)

router = APIRouter()

# Active WebSocket connections organized by workflow_id
active_connections: Dict[str, Set[WebSocket]] = {}

async def broadcast_to_workflow(workflow_id: str, data: dict):
    """Broadcast data to all connections watching a specific workflow"""
    if workflow_id not in active_connections:
        logger.debug("No connections for workflow", workflow_id=workflow_id)
        return
    
    connections_to_remove = set()
    message = json.dumps(data)
    connection_count = len(active_connections[workflow_id])
    
    logger.debug("Broadcasting to connections", 
                workflow_id=workflow_id, 
                connection_count=connection_count,
                data_type=data.get('type', 'unknown'))
    
    for websocket in active_connections[workflow_id].copy():
        try:
            await websocket.send_text(message)
            logger.debug("Successfully sent to websocket", workflow_id=workflow_id)
        except Exception as e:
            logger.warning("Failed to send to websocket", error=str(e))
            connections_to_remove.add(websocket)
    
    # Clean up dead connections
    for websocket in connections_to_remove:
        active_connections[workflow_id].discard(websocket)
        logger.debug("Removed dead connection", workflow_id=workflow_id)

def browser_viewer_callback(viewer_data: dict):
    """Callback function for browser updates - called from MCP server"""
    workflow_id = viewer_data.get("workflow_id")
    if workflow_id:
        try:
            # Get the current event loop
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Schedule broadcast in event loop
                asyncio.create_task(broadcast_to_workflow(workflow_id, viewer_data))
            else:
                # If no loop is running, run it synchronously
                asyncio.run(broadcast_to_workflow(workflow_id, viewer_data))
        except Exception as e:
            logger.warning("Failed to schedule browser update broadcast", error=str(e))

@router.websocket("/ws/{workflow_id}")
async def browser_viewer_websocket(websocket: WebSocket, workflow_id: str):
    """WebSocket endpoint for browser viewer updates"""
    await websocket.accept()
    
    # Add connection to active connections
    if workflow_id not in active_connections:
        active_connections[workflow_id] = set()
    active_connections[workflow_id].add(websocket)
    
    logger.info("Browser viewer connected", workflow_id=workflow_id, 
               total_connections=len(active_connections[workflow_id]))
    
    try:
        # Send initial status
        await websocket.send_text(json.dumps({
            "workflow_id": workflow_id,
            "step": "Connected",
            "details": "Browser viewer connected",
            "status": "connected",
            "timestamp": "now"
        }))
        
        # Keep connection alive with ping/pong
        while True:
            try:
                # Wait for message with timeout
                message = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                logger.debug("Received websocket message", data=message[:100])
                
                try:
                    parsed_message = json.loads(message)
                    if parsed_message.get("type") == "pong":
                        logger.debug("Received pong from client")
                        continue
                except json.JSONDecodeError:
                    pass
                
                # Send pong response to keep connection alive
                await websocket.send_text(json.dumps({
                    "type": "pong",
                    "timestamp": "now"
                }))
                
            except asyncio.TimeoutError:
                # Send ping to keep connection alive
                try:
                    await websocket.send_text(json.dumps({
                        "type": "ping",
                        "timestamp": "now"
                    }))
                except Exception as ping_error:
                    logger.warning("Failed to send ping", error=str(ping_error))
                    break
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.warning("WebSocket message handling error", error=str(e))
                break
                
    except WebSocketDisconnect:
        logger.info("Browser viewer disconnected", workflow_id=workflow_id)
    except Exception as e:
        logger.error("WebSocket error", error=str(e), workflow_id=workflow_id)
    finally:
        # Clean up connection
        if workflow_id in active_connections:
            active_connections[workflow_id].discard(websocket)
            if not active_connections[workflow_id]:
                del active_connections[workflow_id]
        
        logger.info("Browser viewer cleanup completed", workflow_id=workflow_id)

@router.post("/update")
async def receive_browser_update(data: dict):
    """Receive browser updates from MCP server via HTTP"""
    try:
        workflow_id = data.get("workflow_id")
        if workflow_id:
            await broadcast_to_workflow(workflow_id, {
                "type": "browser_update", 
                "data": data
            })
            logger.debug("Browser update broadcasted", workflow_id=workflow_id)
        return {"status": "ok"}
    except Exception as e:
        logger.error("Failed to process browser update", error=str(e))
        return {"status": "error", "error": str(e)}

# Initialize callback in MCP server
def setup_browser_viewer():
    """Setup browser viewer callback in MCP server"""
    try:
        # Setup for simple browser MCP (legacy)
        from app.mcp.playwright_scraper import set_browser_viewer_callback as set_simple_callback
        set_simple_callback(browser_viewer_callback)
        logger.info("Simple browser viewer callback registered")
    except ImportError:
        logger.warning("Simple browser MCP not available")
    
    try:
        # Setup for enhanced browser MCP (current)
        from app.mcp.enhanced_playwright_mcp import set_browser_viewer_callback as set_enhanced_callback
        set_enhanced_callback(browser_viewer_callback)
        logger.info("Enhanced browser viewer callback registered")
    except ImportError:
        logger.warning("Enhanced browser MCP not available")
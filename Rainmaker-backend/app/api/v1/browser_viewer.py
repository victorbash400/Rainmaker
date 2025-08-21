"""
Browser Viewer WebSocket API for real-time browser automation viewing
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import JSONResponse
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

def cleanup_workflow_connections(workflow_id: str):
    """Force cleanup of all browser viewer connections for a workflow"""
    if workflow_id in active_connections:
        connections_to_close = list(active_connections[workflow_id])
        logger.info(f"Force closing {len(connections_to_close)} browser viewer connections", 
                   workflow_id=workflow_id)
        
        for websocket in connections_to_close:
            try:
                # Close with code 1000 (normal closure)
                asyncio.create_task(websocket.close(1000, "Phase transition"))
            except Exception as e:
                logger.warning("Failed to close browser viewer connection", error=str(e))
        
        # Clear the connection set
        active_connections[workflow_id].clear()
        del active_connections[workflow_id]
        logger.info("Browser viewer connections force cleaned", workflow_id=workflow_id)

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

@router.post("/resume/{workflow_id}")
async def resume_workflow_after_login(workflow_id: str):
    """Resume a workflow after manual login completion"""
    try:
        logger.info("🔄 Resume request received", workflow_id=workflow_id)
        
        # Check if there's a saved browser state for this workflow
        from app.mcp.enhanced_playwright_mcp import enhanced_browser_mcp
        from app.mcp.navigate_extract_tool import NavigateExtractTool
        
        # Get the browser manager and check for saved state
        browser_manager = enhanced_browser_mcp.browser_manager
        if not browser_manager:
            raise HTTPException(status_code=404, detail="No active browser session found")
        
        # Check if browser has context with saved state
        if not browser_manager.context:
            raise HTTPException(status_code=404, detail="No persistent browser context found")
        
        # Try to save current state (in case user just logged in)
        try:
            state_file = browser_manager.save_browser_state(workflow_id, "linkedin")  # Assume LinkedIn for now
            logger.info("✅ Current session state saved", state_file=state_file)
        except Exception as save_error:
            logger.warning("Failed to save current state", error=str(save_error))
        
        # Check if this is a campaign workflow that needs to be resumed
        campaign_resumed = False
        if workflow_id.startswith("nav_"):
            try:
                # Try to find and resume related campaign workflow
                from app.agents.campaign_coordinator import get_global_coordinator
                coordinator = get_global_coordinator()
                
                # Look for paused campaigns
                for plan_id, execution_state in coordinator.executing_campaigns.items():
                    if execution_state.get("status") == "paused_for_manual_login":
                        logger.info("🔄 Found paused campaign to resume", plan_id=plan_id)
                        
                        # Resume campaign execution 
                        execution_state["status"] = "executing"
                        execution_state["current_phase"] = "discovery"
                        execution_state["message"] = "Resuming after manual login"
                        coordinator._broadcast_status_update(plan_id, execution_state, force=True)
                        campaign_resumed = True
                        
                        # Continue with enrichment phase
                        logger.info("🔄 Continuing campaign after login", plan_id=plan_id)
                        break
                        
            except Exception as resume_error:
                logger.warning("Failed to resume campaign workflow", error=str(resume_error))
        
        # Broadcast resume notification to connected clients
        await broadcast_to_workflow(workflow_id, {
            "type": "workflow_resumed",
            "data": {
                "workflow_id": workflow_id,
                "status": "resumed_after_login",
                "message": "🔄 Workflow resumed after manual login. Browser state has been saved.",
                "timestamp": "now",
                "instruction": "You can now close this browser session. The saved login will be used in future sessions.",
                "campaign_resumed": campaign_resumed
            }
        })
        
        return JSONResponse({
            "success": True,
            "workflow_id": workflow_id,
            "status": "resumed",
            "message": "✅ Workflow resumed successfully. Login state has been saved for future use.",
            "saved_state": bool(browser_manager.context),
            "instruction": "You can now close the browser. The login session has been saved."
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to resume workflow", error=str(e), workflow_id=workflow_id)
        raise HTTPException(status_code=500, detail=f"Failed to resume workflow: {str(e)}")

@router.get("/status/{workflow_id}")
async def get_workflow_browser_status(workflow_id: str):
    """Get browser status for a workflow"""
    try:
        from app.mcp.enhanced_playwright_mcp import enhanced_browser_mcp
        
        browser_manager = enhanced_browser_mcp.browser_manager if enhanced_browser_mcp else None
        
        status = {
            "workflow_id": workflow_id,
            "browser_active": bool(browser_manager and browser_manager.browser),
            "context_active": bool(browser_manager and browser_manager.context),
            "has_saved_state": False,
            "state_files": []
        }
        
        if browser_manager:
            import os
            # Check for saved state files
            state_dir = browser_manager.state_dir
            if os.path.exists(state_dir):
                state_files = [f for f in os.listdir(state_dir) if workflow_id in f]
                status["has_saved_state"] = len(state_files) > 0
                status["state_files"] = state_files
        
        return JSONResponse(status)
        
    except Exception as e:
        logger.error("Failed to get browser status", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get status: {str(e)}")
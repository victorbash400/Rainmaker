"""
Enrichment Viewer WebSocket API for real-time enrichment process viewing
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict, Set, List
import json
import structlog
import asyncio

logger = structlog.get_logger(__name__)

router = APIRouter()

# Active WebSocket connections organized by workflow_id
active_connections: Dict[str, Set[WebSocket]] = {}

# Cache recent enrichment updates for late-connecting clients
enrichment_update_cache: Dict[str, List[dict]] = {}

async def broadcast_to_workflow(workflow_id: str, data: dict):
    """Broadcast data to all connections watching a specific workflow"""
    # Cache the update for late-connecting clients
    if workflow_id not in enrichment_update_cache:
        enrichment_update_cache[workflow_id] = []
    
    enrichment_update_cache[workflow_id].append(data)
    # Keep only last 50 updates
    if len(enrichment_update_cache[workflow_id]) > 50:
        enrichment_update_cache[workflow_id] = enrichment_update_cache[workflow_id][-50:]
    
    if workflow_id not in active_connections:
        logger.debug("No connections for enrichment workflow", workflow_id=workflow_id)
        return
    
    connections_to_remove = set()
    message = json.dumps(data)
    connection_count = len(active_connections[workflow_id])
    
    logger.debug("Broadcasting enrichment update to connections", 
                workflow_id=workflow_id, 
                connection_count=connection_count,
                data_type=data.get('type', 'unknown'))
    
    for websocket in active_connections[workflow_id].copy():
        try:
            await websocket.send_text(message)
            logger.debug("Successfully sent enrichment update to websocket", workflow_id=workflow_id)
        except Exception as e:
            logger.warning("Failed to send enrichment update to websocket", error=str(e))
            connections_to_remove.add(websocket)
    
    # Clean up dead connections
    for websocket in connections_to_remove:
        active_connections[workflow_id].discard(websocket)
        logger.debug("Removed dead enrichment connection", workflow_id=workflow_id)

def enrichment_viewer_callback(viewer_data: dict):
    """Callback function for enrichment updates - called from enrichment agent"""
    workflow_id = viewer_data.get("workflow_id")
    step = viewer_data.get("step", "Unknown")
    
    print(f"🔥 CALLBACK RECEIVED: {step} for workflow {workflow_id}")
    print(f"    Data keys: {list(viewer_data.keys())}")
    print(f"    Active connections: {list(active_connections.keys())}")
    
    if workflow_id:
        try:
            # Get the current event loop
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Schedule broadcast in event loop
                print(f"📡 SCHEDULING BROADCAST to {len(active_connections.get(workflow_id, []))} connections")
                asyncio.create_task(broadcast_to_workflow(workflow_id, viewer_data))
            else:
                # If no loop is running, run it synchronously
                print(f"📡 RUNNING BROADCAST SYNC to {len(active_connections.get(workflow_id, []))} connections")
                asyncio.run(broadcast_to_workflow(workflow_id, viewer_data))
        except Exception as e:
            print(f"❌ BROADCAST FAILED: {str(e)}")
            logger.warning("Failed to schedule enrichment update broadcast", error=str(e))
    else:
        print("⚠️  NO WORKFLOW_ID in callback data!")

@router.websocket("/ws/{workflow_id}")
async def enrichment_viewer_websocket(websocket: WebSocket, workflow_id: str):
    """WebSocket endpoint for enrichment viewer updates"""
    await websocket.accept()
    
    # Add connection to active connections
    if workflow_id not in active_connections:
        active_connections[workflow_id] = set()
    active_connections[workflow_id].add(websocket)
    
    logger.info("Enrichment viewer connected", workflow_id=workflow_id, 
               total_connections=len(active_connections[workflow_id]))
    
    try:
        # Send initial status
        await websocket.send_text(json.dumps({
            "type": "enrichment_update",
            "workflow_id": workflow_id,
            "step": "Connected",
            "reasoning": "Enrichment viewer connected - ready to show AI analysis",
            "status": "connected",
            "timestamp": "now"
        }))
        
        # Send cached updates to catch up on any missed enrichment data
        if workflow_id in enrichment_update_cache:
            cached_updates = enrichment_update_cache[workflow_id]
            logger.info(f"Sending {len(cached_updates)} cached enrichment updates to new connection", 
                       workflow_id=workflow_id)
            
            for cached_update in cached_updates:
                try:
                    await websocket.send_text(json.dumps(cached_update))
                except Exception as e:
                    logger.warning("Failed to send cached enrichment update", error=str(e))
                    break
        
        # Keep connection alive with ping/pong
        while True:
            try:
                # Wait for message with timeout
                message = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                logger.debug("Received enrichment websocket message", data=message[:100])
                
                try:
                    parsed_message = json.loads(message)
                    if parsed_message.get("type") == "pong":
                        logger.debug("Received pong from enrichment client")
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
                    logger.warning("Failed to send enrichment ping", error=str(ping_error))
                    break
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.warning("Enrichment WebSocket message handling error", error=str(e))
                break
                
    except WebSocketDisconnect:
        logger.info("Enrichment viewer disconnected", workflow_id=workflow_id)
    except Exception as e:
        logger.error("Enrichment WebSocket error", error=str(e), workflow_id=workflow_id)
    finally:
        # Clean up connection
        if workflow_id in active_connections:
            active_connections[workflow_id].discard(websocket)
            if not active_connections[workflow_id]:
                del active_connections[workflow_id]
        
        logger.info("Enrichment viewer cleanup completed", workflow_id=workflow_id)

@router.post("/update")
async def receive_enrichment_update(data: dict):
    """Receive enrichment updates from enrichment agent via HTTP"""
    try:
        workflow_id = data.get("workflow_id")
        if workflow_id:
            await broadcast_to_workflow(workflow_id, {
                "type": "enrichment_update", 
                "data": data
            })
            logger.debug("Enrichment update broadcasted", workflow_id=workflow_id)
        return {"status": "ok"}
    except Exception as e:
        logger.error("Failed to process enrichment update", error=str(e))
        return {"status": "error", "error": str(e)}


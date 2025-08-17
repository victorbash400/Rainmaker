"""
API endpoints for campaign planning with Master Planner Agent
"""

from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, Depends, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from datetime import datetime
import structlog

from app.agents.master_planner import MasterPlannerAgent
from app.agents.planning_models import PlanningPhase, CampaignType
from app.api.deps import get_current_user
from app.db.models import User

logger = structlog.get_logger(__name__)

router = APIRouter()

# Initialize master planner agent
master_planner = MasterPlannerAgent()

# WebSocket connections for real-time planning
active_connections: Dict[str, WebSocket] = {}


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class StartPlanningRequest(BaseModel):
    initial_context: Optional[Dict[str, Any]] = None
    user_first_message: Optional[str] = None


class PlanningResponse(BaseModel):
    conversation_id: str
    current_phase: str
    completion_percentage: float
    assistant_response: str
    is_complete: bool
    clarifications_needed: List[str]
    suggested_responses: List[str]
    campaign_plan: Optional[Dict[str, Any]] = None


class UserMessageRequest(BaseModel):
    conversation_id: str
    message: str


class ExecuteCampaignRequest(BaseModel):
    plan_id: str


class CampaignPlanSummary(BaseModel):
    plan_id: str
    campaign_name: str
    campaign_type: str
    objectives: Dict[str, Any]
    target_profile: Dict[str, Any]
    status: str
    created_at: str


# =============================================================================
# PLANNING CONVERSATION ENDPOINTS
# =============================================================================

@router.post("/planning/start", response_model=PlanningResponse)
async def start_planning_conversation(
    request: StartPlanningRequest,
    current_user: User = Depends(get_current_user)
):
    """Start a new campaign planning conversation"""
    try:
        if request.user_first_message:
            # Start with user's first message
            conversation = await master_planner.start_planning_conversation(
                user_id=str(current_user.id),
                initial_context=request.initial_context
            )
            
            # Process the user's first message
            response = await master_planner.process_user_response(
                conversation_id=conversation.conversation_id,
                user_message=request.user_first_message
            )
            
            return PlanningResponse(**response)
        else:
            # Start with AI greeting (legacy)
            conversation = await master_planner.start_planning_conversation(
                user_id=str(current_user.id),
                initial_context=request.initial_context
            )
        
        return PlanningResponse(
            conversation_id=conversation.conversation_id,
            current_phase=conversation.current_phase.value,
            completion_percentage=conversation.completion_percentage,
            assistant_response=conversation.conversation_history[-1]["content"],
            is_complete=False,
            clarifications_needed=conversation.clarification_needed,
            suggested_responses=conversation.suggested_responses
        )
        
    except Exception as e:
        logger.error("Failed to start planning conversation", error=str(e), user_id=current_user.id)
        raise HTTPException(status_code=500, detail="Failed to start planning conversation")


@router.post("/planning/message", response_model=PlanningResponse)
async def send_planning_message(
    request: UserMessageRequest,
    current_user: User = Depends(get_current_user)
):
    """Send a message in the planning conversation"""
    try:
        response = await master_planner.process_user_response(
            conversation_id=request.conversation_id,
            user_message=request.message
        )
        
        # Broadcast to WebSocket if connected
        if request.conversation_id in active_connections:
            await active_connections[request.conversation_id].send_json({
                "type": "planning_update",
                "data": response
            })
        
        logger.info("About to create PlanningResponse", response_data=response)
        
        try:
            planning_response = PlanningResponse(**response)
            logger.info("PlanningResponse created successfully", conversation_id=request.conversation_id)
            return planning_response
        except Exception as validation_error:
            logger.error("PlanningResponse validation failed", error=str(validation_error), response_data=response)
            raise
        
    except ValueError as e:
        logger.error("ValueError in planning message", error=str(e), conversation_id=request.conversation_id)
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("Failed to process planning message", error=str(e), conversation_id=request.conversation_id)
        raise HTTPException(status_code=500, detail="Failed to process message")


@router.get("/planning/conversation/{conversation_id}")
async def get_planning_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get current state of planning conversation"""
    try:
        if conversation_id not in master_planner.active_conversations:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        conversation = master_planner.active_conversations[conversation_id]
        
        # Verify user ownership
        if conversation.user_id != str(current_user.id):
            raise HTTPException(status_code=403, detail="Not authorized to access this conversation")
        
        return {
            "conversation_id": conversation.conversation_id,
            "current_phase": conversation.current_phase.value,
            "completion_percentage": conversation.completion_percentage,
            "conversation_history": conversation.conversation_history,
            "collected_info": conversation.collected_info,
            "clarifications_needed": conversation.clarification_needed
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get planning conversation", error=str(e), conversation_id=conversation_id)
        raise HTTPException(status_code=500, detail="Failed to get conversation")


# =============================================================================
# CAMPAIGN PLAN MANAGEMENT
# =============================================================================

@router.get("/plans", response_model=List[CampaignPlanSummary])
async def get_campaign_plans(
    current_user: User = Depends(get_current_user)
):
    """Get all campaign plans for the current user"""
    try:
        user_plans = []
        
        for plan in master_planner.active_campaigns.values():
            if plan.user_id == str(current_user.id):
                user_plans.append(CampaignPlanSummary(
                    plan_id=plan.plan_id,
                    campaign_name=plan.campaign_name,
                    campaign_type=plan.execution_strategy.campaign_type.value if hasattr(plan.execution_strategy.campaign_type, 'value') else plan.execution_strategy.campaign_type,
                    objectives=plan.objectives.__dict__,
                    target_profile=plan.target_profile.__dict__,
                    status="active",  # Could be enhanced with real status
                    created_at=plan.created_at.isoformat()
                ))
        
        return user_plans
        
    except Exception as e:
        logger.error("Failed to get campaign plans", error=str(e), user_id=current_user.id)
        raise HTTPException(status_code=500, detail="Failed to get campaign plans")


@router.get("/plans/{plan_id}")
async def get_campaign_plan(
    plan_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get detailed campaign plan"""
    try:
        # First check if plan is in active campaigns
        plan = None
        if plan_id in master_planner.active_campaigns:
            plan = master_planner.active_campaigns[plan_id]
        else:
            # Try to load from the conversational planner's created plans
            from app.agents.conversational_planner import ConversationalPlannerAgent
            if hasattr(ConversationalPlannerAgent, '_created_plans') and plan_id in ConversationalPlannerAgent._created_plans:
                plan = ConversationalPlannerAgent._created_plans[plan_id]
                # Add to active campaigns for future access
                master_planner.active_campaigns[plan_id] = plan
        
        if not plan:
            raise HTTPException(status_code=404, detail="Campaign plan not found")
        
        # Verify user ownership
        if plan.user_id != str(current_user.id):
            raise HTTPException(status_code=403, detail="Not authorized to access this plan")
        
        return {
            "plan_id": plan.plan_id,
            "campaign_name": plan.campaign_name,
            "objectives": plan.objectives.__dict__,
            "target_profile": plan.target_profile.__dict__,
            "execution_strategy": plan.execution_strategy.__dict__,
            "expected_timeline": plan.expected_timeline,
            "resource_requirements": plan.resource_requirements,
            "risk_factors": plan.risk_factors,
            "success_predictions": plan.success_predictions,
            "created_at": plan.created_at.isoformat(),
            "plan_metadata": plan.plan_metadata
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get campaign plan", error=str(e), plan_id=plan_id)
        raise HTTPException(status_code=500, detail="Failed to get campaign plan")


# =============================================================================
# CAMPAIGN EXECUTION
# =============================================================================

@router.post("/plans/{plan_id}/execute")
async def execute_campaign_plan(
    plan_id: str,
    current_user: User = Depends(get_current_user)
):
    """Execute a campaign plan"""
    try:
        # First check if plan is in active campaigns
        plan = None
        if plan_id in master_planner.active_campaigns:
            plan = master_planner.active_campaigns[plan_id]
        else:
            # Try to load from the conversational planner's created plans
            from app.agents.conversational_planner import ConversationalPlannerAgent
            if hasattr(ConversationalPlannerAgent, '_created_plans') and plan_id in ConversationalPlannerAgent._created_plans:
                plan = ConversationalPlannerAgent._created_plans[plan_id]
                # Add to active campaigns for future access
                master_planner.active_campaigns[plan_id] = plan
        
        if not plan:
            raise HTTPException(status_code=404, detail="Campaign plan not found")
        
        # Verify user ownership
        if plan.user_id != str(current_user.id):
            raise HTTPException(status_code=403, detail="Not authorized to execute this plan")
        
        # Execute the campaign
        execution_result = await master_planner.execute_campaign_plan(plan_id)
        
        # Broadcast status update to connected clients
        await broadcast_workflow_status_update(plan_id, {
            "status": "executing",
            "current_phase": "initializing",
            "progress_percentage": 0,
            "metrics": {
                "prospects_discovered": 0,
                "outreach_sent": 0,
                "meetings_scheduled": 0,
                "proposals_generated": 0
            }
        })
        
        return {
            "plan_id": plan_id,
            "execution_started": True,
            "execution_result": execution_result,
            "message": "Campaign execution started successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to execute campaign plan", error=str(e), plan_id=plan_id)
        raise HTTPException(status_code=500, detail="Failed to execute campaign plan")


@router.get("/plans/{plan_id}/status")
async def get_campaign_execution_status(
    plan_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get campaign execution status"""
    try:
        # First check if plan is in active campaigns
        plan = None
        if plan_id in master_planner.active_campaigns:
            plan = master_planner.active_campaigns[plan_id]
        else:
            # Try to load from the conversational planner's created plans
            from app.agents.conversational_planner import ConversationalPlannerAgent
            if hasattr(ConversationalPlannerAgent, '_created_plans') and plan_id in ConversationalPlannerAgent._created_plans:
                plan = ConversationalPlannerAgent._created_plans[plan_id]
                # Add to active campaigns for future access
                master_planner.active_campaigns[plan_id] = plan
        
        if not plan:
            raise HTTPException(status_code=404, detail="Campaign plan not found")
        
        # Verify user ownership
        if plan.user_id != str(current_user.id):
            raise HTTPException(status_code=403, detail="Not authorized to access this plan")
        
        # Get execution status from master planner
        status = master_planner.get_campaign_execution_status(plan_id)
        return status
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get execution status", error=str(e), plan_id=plan_id)
        raise HTTPException(status_code=500, detail="Failed to get execution status")


# =============================================================================
# REAL-TIME PLANNING WEBSOCKET
# =============================================================================

@router.websocket("/planning/ws/{conversation_id}")
async def planning_websocket(websocket: WebSocket, conversation_id: str):
    """WebSocket endpoint for real-time planning updates"""
    await websocket.accept()
    active_connections[conversation_id] = websocket
    
    try:
        while True:
            # Keep connection alive and handle any incoming messages
            data = await websocket.receive_text()
            
            # Echo back for connection testing
            await websocket.send_json({
                "type": "ping_response",
                "timestamp": str(int(datetime.now().timestamp()))
            })
            
    except WebSocketDisconnect:
        logger.info("Planning WebSocket disconnected", conversation_id=conversation_id)
    except Exception as e:
        logger.error("Planning WebSocket error", error=str(e), conversation_id=conversation_id)
    finally:
        if conversation_id in active_connections:
            del active_connections[conversation_id]


# WebSocket connections for workflow status updates
workflow_status_connections: List[WebSocket] = []

@router.websocket("/workflow-status/ws")
async def workflow_status_websocket(websocket: WebSocket):
    """WebSocket endpoint for real-time workflow status updates"""
    await websocket.accept()
    workflow_status_connections.append(websocket)
    
    try:
        # Send initial connection confirmation
        await websocket.send_json({
            "type": "connection_established",
            "message": "Workflow status WebSocket connected",
            "timestamp": str(int(datetime.now().timestamp()))
        })
        
        while True:
            # Keep connection alive and handle any incoming messages
            data = await websocket.receive_text()
            
            # Echo back for connection testing
            await websocket.send_json({
                "type": "ping_response",
                "timestamp": str(int(datetime.now().timestamp()))
            })
            
    except WebSocketDisconnect:
        logger.info("Workflow status WebSocket disconnected")
    except Exception as e:
        logger.error("Workflow status WebSocket error", error=str(e))
    finally:
        if websocket in workflow_status_connections:
            workflow_status_connections.remove(websocket)


async def broadcast_workflow_status_update(plan_id: str, status_data: Dict[str, Any]):
    """Broadcast workflow status update to all connected clients"""
    if not workflow_status_connections:
        return
    
    message = {
        "type": "workflow_status_update",
        "plan_id": plan_id,
        **status_data,
        "timestamp": str(int(datetime.now().timestamp()))
    }
    
    # Remove dead connections
    dead_connections = []
    
    for websocket in workflow_status_connections:
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.warning("Failed to send workflow status update", error=str(e))
            dead_connections.append(websocket)
    
    # Clean up dead connections
    for dead_ws in dead_connections:
        workflow_status_connections.remove(dead_ws)


def workflow_status_callback_wrapper(plan_id: str, status_data: Dict[str, Any]):
    """Wrapper to handle async broadcast from sync context"""
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.create_task(broadcast_workflow_status_update(plan_id, status_data))
        else:
            asyncio.run(broadcast_workflow_status_update(plan_id, status_data))
    except Exception as e:
        logger.warning("Failed to broadcast workflow status update", error=str(e))


# Set up the callback in campaign coordinator
from app.agents.campaign_coordinator import set_workflow_status_callback
set_workflow_status_callback(workflow_status_callback_wrapper)


# =============================================================================
# PLANNING ASSISTANCE ENDPOINTS
# =============================================================================

@router.get("/planning/templates")
async def get_planning_templates():
    """Get campaign planning templates and suggestions"""
    
    templates = {
        "campaign_types": [
            {
                "type": "discovery_focused",
                "name": "Lead Discovery Campaign",
                "description": "Focus on finding new prospects and building pipeline",
                "best_for": ["New market expansion", "Pipeline building", "Market research"],
                "typical_duration": "2-4 weeks",
                "expected_results": "50-200 new prospects"
            },
            {
                "type": "nurturing_focused", 
                "name": "Lead Nurturing Campaign",
                "description": "Warm up existing prospects and move them through pipeline",
                "best_for": ["Existing prospect database", "Cold leads", "Long sales cycles"],
                "typical_duration": "3-6 weeks",
                "expected_results": "20-40% engagement increase"
            },
            {
                "type": "conversion_focused",
                "name": "Conversion Campaign", 
                "description": "Focus on converting qualified prospects to customers",
                "best_for": ["Warm prospects", "Proposal follow-ups", "Meeting scheduling"],
                "typical_duration": "1-3 weeks",
                "expected_results": "10-30% conversion rate"
            },
            {
                "type": "hybrid_campaign",
                "name": "Full-Funnel Campaign",
                "description": "Complete pipeline from discovery to conversion",
                "best_for": ["Comprehensive sales push", "New product launch", "Seasonal campaigns"],
                "typical_duration": "4-8 weeks",
                "expected_results": "End-to-end pipeline coverage"
            }
        ],
        "target_profiles": [
            {
                "name": "High-End Wedding Clients",
                "event_types": ["wedding"],
                "budget_ranges": [(15000, 50000)],
                "prospect_types": ["individual"],
                "key_indicators": ["engagement announcements", "venue searches", "wedding planning queries"]
            },
            {
                "name": "Corporate Event Planners",
                "event_types": ["corporate_event"],
                "budget_ranges": [(5000, 25000)],
                "prospect_types": ["company"],
                "key_indicators": ["company growth", "team events", "corporate celebrations"]
            },
            {
                "name": "Milestone Celebrations",
                "event_types": ["birthday", "anniversary", "graduation"],
                "budget_ranges": [(2000, 10000)],
                "prospect_types": ["individual"],
                "key_indicators": ["milestone ages", "achievement announcements", "celebration planning"]
            }
        ],
        "objective_examples": [
            {
                "goal": "generate_leads",
                "description": "Discover and qualify new prospects",
                "typical_targets": {"prospects": 50, "meetings": 10, "proposals": 5}
            },
            {
                "goal": "increase_bookings", 
                "description": "Convert existing prospects to customers",
                "typical_targets": {"meetings": 15, "proposals": 10, "conversions": 3}
            },
            {
                "goal": "expand_market",
                "description": "Enter new geographic or demographic markets",
                "typical_targets": {"prospects": 100, "market_penetration": "5-10%", "meetings": 20}
            }
        ]
    }
    
    return templates


@router.get("/planning/insights")
async def get_planning_insights(
    current_user: User = Depends(get_current_user)
):
    """Get intelligent insights and recommendations for campaign planning"""
    
    # This could analyze historical data, market trends, etc.
    insights = {
        "market_trends": [
            "Wedding bookings increase 40% in Q2 (April-June)",
            "Corporate events peak in Q1 and Q4", 
            "Birthday parties show steady year-round demand"
        ],
        "optimization_tips": [
            "Email outreach performs 25% better on Tuesday-Thursday",
            "LinkedIn messages have higher response rates in the morning",
            "Follow-up within 24 hours increases conversion by 60%"
        ],
        "seasonal_recommendations": [
            {
                "season": "Current",
                "focus": "Wedding season preparation (March-May)",
                "suggested_campaign": "discovery_focused",
                "target_increase": "30% more wedding prospects"
            }
        ],
        "success_factors": [
            "Personalized outreach increases response rates by 50%",
            "Multi-channel campaigns outperform single-channel by 35%", 
            "Quick follow-up is the #1 factor in conversion success"
        ]
    }
    
    return insights
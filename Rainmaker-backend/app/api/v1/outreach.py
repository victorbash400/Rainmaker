"""
Outreach API endpoints for managing outreach campaigns and replies
"""

import asyncio
from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any, List
import structlog

from app.api.deps import get_current_user
from typing import Optional
from app.core.state import RainmakerState, StateManager, WorkflowStage
from app.core.persistence import persistence_manager
from app.agents.outreach import OutreachAgent
from app.mcp.email_mcp import email_mcp
from app.db.schemas import User

logger = structlog.get_logger(__name__)

router = APIRouter()


@router.post("/{workflow_id}/check-replies")
async def check_for_replies(
    workflow_id: str
    # TODO: Re-enable auth after testing: current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Check for new replies and analyze them with AI
    
    Returns rich response for UI:
    - no_reply_found: No new replies detected
    - reply_found: Reply detected with AI analysis
    """
    logger.info("Checking for replies", workflow_id=workflow_id)
    
    try:
        # Load workflow state
        state = await persistence_manager.load_state(workflow_id)
        if not state:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workflow not found"
            )
        
        # Verify workflow is in AWAITING_REPLY stage
        if state.get("current_stage") != WorkflowStage.AWAITING_REPLY:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Workflow is not awaiting reply. Current stage: {state.get('current_stage')}"
            )
        
        # Get prospect email from state
        prospect_data = state.get("prospect_data")
        if not prospect_data or not prospect_data.email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No prospect email found in workflow state"
            )
        
        # Check for replies using EmailMCP
        replies = email_mcp.check_for_replies(prospect_data.email)
        
        if not replies:
            logger.info("No replies found", workflow_id=workflow_id)
            return {
                "status": "no_reply_found",
                "message": "No new replies detected. Feel free to check again later!"
            }
        
        # Process the most recent reply with OutreachAgent
        logger.info(f"Found {len(replies)} replies", workflow_id=workflow_id)
        latest_reply = replies[0]  # Most recent reply
        
        # Use OutreachAgent to analyze the reply
        outreach_agent = OutreachAgent()
        analyzed_state = await outreach_agent.handle_prospect_reply(state, latest_reply)
        
        # Get analysis results
        conversation_summary = analyzed_state.get("conversation_summary", {})
        intent = conversation_summary.get("last_reply_intent", "UNKNOWN")
        summary = conversation_summary.get("last_reply_summary", "Unable to analyze reply")
        
        # Update workflow state
        if intent == "INTERESTED":
            # Update stage to indicate ready for next step
            analyzed_state = StateManager.update_stage(analyzed_state, WorkflowStage.CONVERSATION)
            
        # Save updated state
        await persistence_manager.save_state(workflow_id, analyzed_state)
        
        logger.info(
            "Reply processed successfully",
            workflow_id=workflow_id,
            intent=intent,
            reply_count=len(replies)
        )
        
        return {
            "status": "reply_found",
            "intent": intent,
            "summary": summary,
            "reply_count": len(replies),
            "message": f"Great! The prospect replied with intent: {intent}",
            "can_proceed": intent == "INTERESTED"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to check for replies", error=str(e), workflow_id=workflow_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check for replies: {str(e)}"
        )


@router.post("/{workflow_id}/proceed-to-proposal")
async def proceed_to_proposal(
    workflow_id: str
    # TODO: Re-enable auth after testing: current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Proceed to proposal generation after positive reply
    """
    logger.info("Proceeding to proposal", workflow_id=workflow_id)
    
    try:
        # Load workflow state
        state = await persistence_manager.load_state(workflow_id)
        if not state:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workflow not found"
            )
        
        # Verify we can proceed
        conversation_summary = state.get("conversation_summary", {})
        intent = conversation_summary.get("last_reply_intent")
        
        if intent != "INTERESTED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot proceed to proposal. Prospect intent: {intent}"
            )
        
        # Update stage to indicate proposal preparation
        state = StateManager.update_stage(state, WorkflowStage.PROPOSAL)
        
        # Save state
        await persistence_manager.save_state(workflow_id, state)
        
        logger.info("Workflow proceeding to proposal stage", workflow_id=workflow_id)
        
        return {
            "status": "success",
            "message": "Workflow proceeding to proposal generation",
            "next_stage": WorkflowStage.PROPOSAL,
            "workflow_complete": True  # For now, since proposal agent isn't built
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to proceed to proposal", error=str(e), workflow_id=workflow_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to proceed to proposal: {str(e)}"
        )


@router.get("/{workflow_id}/status")
async def get_outreach_status(
    workflow_id: str
    # TODO: Re-enable auth after testing: current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get current outreach status for a workflow
    """
    try:
        # Load workflow state
        state = await persistence_manager.load_state(workflow_id)
        if not state:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workflow not found"
            )
        
        # Get latest campaign info
        campaigns = state.get("outreach_campaigns", [])
        latest_campaign = campaigns[-1] if campaigns else None
        
        # Get conversation summary if available
        conversation_summary = state.get("conversation_summary", {})
        
        return {
            "workflow_id": workflow_id,
            "current_stage": state.get("current_stage"),
            "campaign_sent": bool(latest_campaign),
            "campaign_status": latest_campaign.status.value if latest_campaign else None,
            "subject_line": latest_campaign.subject_line if latest_campaign else None,
            "sent_at": latest_campaign.sent_at.isoformat() if latest_campaign and latest_campaign.sent_at else None,
            "reply_intent": conversation_summary.get("last_reply_intent"),
            "reply_summary": conversation_summary.get("last_reply_summary"),
            "can_check_replies": state.get("current_stage") == WorkflowStage.AWAITING_REPLY
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get outreach status", error=str(e), workflow_id=workflow_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get outreach status: {str(e)}"
        )
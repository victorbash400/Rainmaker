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
        state = persistence_manager.load_state(workflow_id)
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
        persistence_manager.save_state(workflow_id, analyzed_state)
        
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
        state = persistence_manager.load_state(workflow_id)
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
        persistence_manager.save_state(workflow_id, state)
        
        logger.info("Workflow proceeding to proposal stage", workflow_id=workflow_id)
        
        # Force sync campaign coordinator to detect the phase change and broadcast
        try:
            from app.agents.campaign_coordinator import get_global_coordinator
            
            # Get the global coordinator instance
            coordinator = get_global_coordinator()
            
            # Find the plan_id for this workflow
            plan_id = None
            for pid, execution_state in coordinator.executing_campaigns.items():
                if execution_state.get("workflow_id") == workflow_id:
                    plan_id = pid
                    break
            
            if plan_id:
                logger.info("🔄 Triggering force sync for campaign coordinator", 
                          plan_id=plan_id, workflow_id=workflow_id)
                await coordinator.force_sync_workflow_state(plan_id)
            else:
                logger.warning("Could not find plan_id for workflow to trigger sync", 
                             workflow_id=workflow_id)
                
        except Exception as e:
            logger.warning("Failed to trigger campaign coordinator sync", 
                         error=str(e), workflow_id=workflow_id)
        
        return {
            "status": "success",
            "message": "Workflow proceeding to proposal generation",
            "next_stage": WorkflowStage.PROPOSAL,
            "workflow_complete": False  # Changed to False so frontend shows ProposalViewer
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
        state = persistence_manager.load_state(workflow_id)
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
        
        # Handle both dict and object formats safely
        campaign_status = None
        subject_line = None
        sent_at = None
        
        if latest_campaign:
            if isinstance(latest_campaign, dict):
                campaign_status = latest_campaign.get("status")
                subject_line = latest_campaign.get("subject_line")
                sent_at = latest_campaign.get("sent_at")
            else:
                try:
                    campaign_status = latest_campaign.status.value if hasattr(latest_campaign, 'status') else None
                    subject_line = latest_campaign.subject_line if hasattr(latest_campaign, 'subject_line') else None
                    sent_at = latest_campaign.sent_at.isoformat() if hasattr(latest_campaign, 'sent_at') and latest_campaign.sent_at else None
                except:
                    pass  # Handle any attribute errors gracefully
        
        return {
            "workflow_id": workflow_id,
            "current_stage": state.get("current_stage"),
            "campaign_sent": bool(latest_campaign),
            "campaign_status": campaign_status,
            "subject_line": subject_line,
            "sent_at": sent_at,
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


@router.post("/{workflow_id}/request-overview")
async def request_overview(
    workflow_id: str
    # TODO: Re-enable auth after testing: current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Send follow-up email requesting event overview details after positive reply
    """
    logger.info("Requesting overview from prospect", workflow_id=workflow_id)
    
    try:
        # Load workflow state
        state = persistence_manager.load_state(workflow_id)
        if not state:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workflow not found"
            )
        
        # Verify workflow is in CONVERSATION stage with positive intent
        conversation_summary = state.get("conversation_summary", {})
        intent = conversation_summary.get("last_reply_intent")
        
        if state.get("current_stage") != WorkflowStage.CONVERSATION:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Workflow not ready for overview request. Current stage: {state.get('current_stage')}"
            )
            
        if intent != "INTERESTED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot request overview. Prospect intent: {intent}"
            )
        
        # Send overview request using OutreachAgent
        outreach_agent = OutreachAgent()
        updated_state = await outreach_agent.send_overview_request(state)
        
        # Update workflow stage to AWAITING_OVERVIEW
        updated_state = StateManager.update_stage(updated_state, WorkflowStage.AWAITING_OVERVIEW)
        
        # Save updated state
        persistence_manager.save_state(workflow_id, updated_state)
        
        logger.info("Overview request sent successfully", workflow_id=workflow_id)
        
        return {
            "status": "success",
            "message": "Overview request email sent successfully",
            "next_stage": WorkflowStage.AWAITING_OVERVIEW,
            "can_check_overview_reply": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to request overview", error=str(e), workflow_id=workflow_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to request overview: {str(e)}"
        )


@router.post("/{workflow_id}/check-overview-reply")
async def check_overview_reply(
    workflow_id: str
    # TODO: Re-enable auth after testing: current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Check for overview response and analyze event details
    """
    logger.info("Checking for overview reply", workflow_id=workflow_id)
    
    try:
        # Load workflow state
        state = persistence_manager.load_state(workflow_id)
        if not state:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workflow not found"
            )
        
        # Verify workflow is in AWAITING_OVERVIEW stage
        if state.get("current_stage") != WorkflowStage.AWAITING_OVERVIEW:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Workflow not awaiting overview reply. Current stage: {state.get('current_stage')}"
            )
        
        # Get prospect email from state
        prospect_data = state.get("prospect_data")
        if not prospect_data or not prospect_data.email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No prospect email found in workflow state"
            )
        
        # Get the time when overview was sent to only check for newer emails
        outreach_campaigns = state.get("outreach_campaigns", [])
        overview_campaign = None
        for campaign in reversed(outreach_campaigns):  # Get most recent overview request
            if isinstance(campaign, dict) and campaign.get("campaign_type") == "overview_request":
                overview_campaign = campaign
                break
        
        # Check for replies using EmailMCP
        if overview_campaign and overview_campaign.get("sent_at"):
            # Only look for emails after the overview was sent
            from datetime import datetime
            try:
                sent_time = datetime.fromisoformat(overview_campaign["sent_at"].replace('Z', '+00:00'))
                since_date = sent_time.strftime("%d-%b-%Y")
                replies = email_mcp.check_for_replies(prospect_data.email, since_date=since_date)
            except:
                # Fallback to recent check
                from datetime import timedelta
                recent_time = datetime.now() - timedelta(minutes=15)
                recent_date = recent_time.strftime("%d-%b-%Y")
                replies = email_mcp.check_for_replies(prospect_data.email, since_date=recent_date)
        else:
            # Fallback to recent check
            from datetime import datetime, timedelta
            recent_time = datetime.now() - timedelta(minutes=15)
            recent_date = recent_time.strftime("%d-%b-%Y")
            replies = email_mcp.check_for_replies(prospect_data.email, since_date=recent_date)
        
        if not replies:
            logger.info("No overview replies found", workflow_id=workflow_id)
            return {
                "status": "no_reply_found",
                "message": "No overview response received yet. Check again later!"
            }
        
        # Process the most recent reply for event details
        logger.info(f"Found {len(replies)} replies for overview", workflow_id=workflow_id)
        latest_reply = replies[0]  # Most recent reply
        
        # Analyze the overview response for event details
        event_analysis = await analyze_event_overview_reply(latest_reply)
        
        # Update state with event overview
        state["event_overview"] = {
            "reply_body": latest_reply.get("body", ""),
            "event_details": event_analysis.get("event_details", {}),
            "analysis_summary": event_analysis.get("summary", ""),
            "has_sufficient_details": event_analysis.get("sufficient_for_proposal", False)
        }
        
        # Update workflow stage based on analysis
        if event_analysis.get("sufficient_for_proposal", False):
            # Move to proposal stage if we have enough details
            updated_state = StateManager.update_stage(state, WorkflowStage.PROPOSAL)
        else:
            # Stay in overview stage for clarification
            updated_state = StateManager.update_stage(state, WorkflowStage.AWAITING_OVERVIEW_REPLY)
        
        # Save updated state
        persistence_manager.save_state(workflow_id, updated_state)
        
        logger.info(
            "Overview reply processed successfully",
            workflow_id=workflow_id,
            has_sufficient_details=event_analysis.get("sufficient_for_proposal", False)
        )
        
        return {
            "status": "overview_received",
            "event_details": event_analysis.get("event_details", {}),
            "analysis_summary": event_analysis.get("summary", ""),
            "has_sufficient_details": event_analysis.get("sufficient_for_proposal", False),
            "can_proceed_to_proposal": event_analysis.get("sufficient_for_proposal", False),
            "message": "Event overview received and analyzed!"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to check overview reply", error=str(e), workflow_id=workflow_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check overview reply: {str(e)}"
        )


async def analyze_event_overview_reply(reply: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze overview reply to extract event details"""
    from app.services.gemini_service import gemini_service
    
    reply_body = reply.get("body", "")
    
    system_prompt = (
        "You are an event planning assistant analyzing a client's event overview response. "
        "Extract key event details and determine if there's sufficient information to create a proposal. "
        "Focus on event type, date, guest count, budget, and specific requirements."
    )
    
    user_message = f"""
    Analyze the following client response about their event needs:
    
    **Client Response:**
    {reply_body}
    
    **Extract the following information:**
    1. Event type and purpose
    2. Date or timeframe
    3. Guest count estimate
    4. Budget range (if mentioned)
    5. Venue preferences
    6. Special requirements
    7. Any specific vision or themes
    
    **Determine if we have enough details to create a proposal**
    
    Return a JSON object with:
    {{
        "event_details": {{
            "event_type": "extracted event type",
            "date_timeframe": "extracted dates",
            "guest_count": "extracted guest count",
            "budget_range": "extracted budget",
            "venue_preferences": "extracted venue info",
            "special_requirements": "extracted requirements",
            "themes_vision": "extracted themes"
        }},
        "summary": "Brief summary of the event overview",
        "sufficient_for_proposal": true/false
    }}
    """
    
    try:
        analysis = await gemini_service.generate_json_response(
            system_prompt=system_prompt,
            user_message=user_message
        )
        return analysis
    except Exception as e:
        logger.error("Failed to analyze event overview", error=str(e))
        return {
            "event_details": {},
            "summary": "Unable to analyze overview response",
            "sufficient_for_proposal": False
        }
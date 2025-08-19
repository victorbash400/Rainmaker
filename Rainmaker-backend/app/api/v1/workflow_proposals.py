"""
Workflow Proposal API endpoints for generating, managing, and sending event proposals
Integration with the outreach workflow system
"""

import asyncio
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any, List, Optional
import structlog

from app.api.deps import get_current_user
from app.core.state import RainmakerState, StateManager, WorkflowStage
from app.core.persistence import persistence_manager
from app.agents.proposal import ProposalAgent
from app.agents.outreach import OutreachAgent
from app.mcp.email_mcp import email_mcp
from app.db.schemas import User

logger = structlog.get_logger(__name__)

router = APIRouter()


@router.post("/{workflow_id}/generate")
async def generate_proposal(
    workflow_id: str
    # TODO: Re-enable auth after testing: current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Generate a professional proposal using AI based on workflow data
    """
    logger.info("Generating proposal", workflow_id=workflow_id)
    
    try:
        # Load workflow state
        state = persistence_manager.load_state(workflow_id)
        if not state:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workflow not found"
            )
        
        # Verify workflow is ready for proposal generation
        if state.get("current_stage") not in [WorkflowStage.PROPOSAL, WorkflowStage.AWAITING_OVERVIEW_REPLY]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Workflow not ready for proposal. Current stage: {state.get('current_stage')}"
            )
        
        # Extract data needed for proposal generation
        proposal_data = await _extract_proposal_data(state)
        
        # Generate proposal using ProposalAgent
        proposal_agent = ProposalAgent()
        proposal_result = await proposal_agent.generate_proposal(proposal_data)
        
        if proposal_result["status"] != "success":
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Proposal generation failed: {proposal_result.get('message', 'Unknown error')}"
            )
        
        # Update state with proposal information
        state["proposal"] = {
            "proposal_id": proposal_result["proposal_id"],
            "client_company": proposal_result["client_company"],
            "event_type": proposal_result["event_type"],
            "total_investment": proposal_result["total_investment"],
            "pdf_file_path": proposal_result["pdf_file_path"],
            "generated_at": proposal_result["generated_at"],
            "valid_until": proposal_result["valid_until"],
            "status": "generated"
        }
        
        # Update workflow stage to proposal generated
        state = StateManager.update_stage(state, WorkflowStage.PROPOSAL)
        
        # Save updated state
        persistence_manager.save_state(workflow_id, state)
        
        logger.info(
            "Proposal generated successfully",
            workflow_id=workflow_id,
            proposal_id=proposal_result["proposal_id"]
        )
        
        return {
            "status": "success",
            "proposal_id": proposal_result["proposal_id"],
            "client_company": proposal_result["client_company"],
            "event_type": proposal_result["event_type"],
            "total_investment": proposal_result["total_investment"],
            "pdf_file_path": proposal_result["pdf_file_path"],
            "message": "Proposal generated successfully",
            "can_review": True,
            "can_send": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to generate proposal", error=str(e), workflow_id=workflow_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate proposal: {str(e)}"
        )


@router.get("/{workflow_id}/status")
async def get_proposal_status(
    workflow_id: str
    # TODO: Re-enable auth after testing: current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get current proposal status for a workflow
    """
    try:
        # Load workflow state
        state = persistence_manager.load_state(workflow_id)
        if not state:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workflow not found"
            )
        
        # Get proposal info
        proposal = state.get("proposal", {})
        
        return {
            "workflow_id": workflow_id,
            "current_stage": state.get("current_stage"),
            "has_proposal": bool(proposal),
            "proposal_id": proposal.get("proposal_id"),
            "client_company": proposal.get("client_company"),
            "event_type": proposal.get("event_type"),
            "total_investment": proposal.get("total_investment"),
            "pdf_file_path": proposal.get("pdf_file_path"),
            "generated_at": proposal.get("generated_at"),
            "valid_until": proposal.get("valid_until"),
            "status": proposal.get("status", "not_generated"),
            "can_generate": state.get("current_stage") in [WorkflowStage.PROPOSAL, WorkflowStage.AWAITING_OVERVIEW_REPLY],
            "can_send": proposal.get("status") == "generated"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get proposal status", error=str(e), workflow_id=workflow_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get proposal status: {str(e)}"
        )


@router.post("/{workflow_id}/send")
async def send_proposal(
    workflow_id: str
    # TODO: Re-enable auth after testing: current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Send the generated proposal to the prospect via email
    """
    logger.info("Sending proposal", workflow_id=workflow_id)
    
    try:
        # Load workflow state
        state = persistence_manager.load_state(workflow_id)
        if not state:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workflow not found"
            )
        
        # Verify proposal exists and is ready to send
        proposal = state.get("proposal", {})
        logger.info("Proposal check", has_proposal=bool(proposal), proposal_status=proposal.get("status") if proposal else None)
        if not proposal or proposal.get("status") != "generated":
            logger.error("Proposal validation failed", has_proposal=bool(proposal), status=proposal.get("status") if proposal else None)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No proposal available to send. Generate a proposal first."
            )
        
        # Get prospect data
        prospect_data = state.get("prospect_data")
        prospect_email = getattr(prospect_data, 'email', '') if prospect_data else ''
        logger.info("Prospect data check", has_prospect_data=bool(prospect_data), prospect_email=prospect_email, prospect_data_type=type(prospect_data).__name__ if prospect_data else None)
        if not prospect_data or not prospect_email:
            logger.error("Prospect data validation failed", has_prospect_data=bool(prospect_data), prospect_email=prospect_email)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No prospect email found in workflow state"
            )
        
        # Send proposal email using OutreachAgent
        outreach_agent = OutreachAgent()
        email_result = await outreach_agent.send_proposal_email(state, proposal)
        
        # Update proposal status
        proposal["status"] = "sent"
        proposal["sent_at"] = email_result.get("sent_at")
        proposal["email_subject"] = email_result.get("subject_line")
        state["proposal"] = proposal
        
        # Update workflow stage to meeting (awaiting meeting response)
        state = StateManager.update_stage(state, WorkflowStage.MEETING)
        
        # Save updated state
        persistence_manager.save_state(workflow_id, state)
        
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
                logger.info("🔄 Triggering force sync for meeting phase transition", 
                          plan_id=plan_id, workflow_id=workflow_id)
                await coordinator.force_sync_workflow_state(plan_id)
            else:
                logger.warning("Could not find plan_id for workflow to trigger meeting sync", 
                             workflow_id=workflow_id)
                
        except Exception as e:
            logger.warning("Failed to trigger campaign coordinator sync for meeting phase", 
                         error=str(e), workflow_id=workflow_id)
        
        logger.info(
            "Proposal sent successfully",
            workflow_id=workflow_id,
            proposal_id=proposal["proposal_id"]
        )
        
        return {
            "status": "success",
            "message": "Proposal sent successfully to prospect",
            "sent_at": proposal["sent_at"],
            "email_subject": proposal["email_subject"],
            "next_stage": WorkflowStage.MEETING,
            "can_check_meeting_response": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to send proposal", error=str(e), workflow_id=workflow_id, error_type=type(e).__name__)
        # Log more details about the error
        import traceback
        logger.error("Full traceback", traceback=traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send proposal: {str(e)}"
        )





@router.post("/{workflow_id}/setup-meeting")
async def setup_meeting(
    workflow_id: str
    # TODO: Re-enable auth after testing: current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Setup a meeting with the prospect (placeholder for future meeting agent)
    """
    logger.info("Setting up meeting", workflow_id=workflow_id)
    
    try:
        # Load workflow state
        state = persistence_manager.load_state(workflow_id)
        if not state:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workflow not found"
            )
        
        # Verify meeting response indicates interest
        meeting_response = state.get("meeting_response", {})
        analysis = meeting_response.get("analysis", {})
        
        if not analysis.get("wants_meeting", False):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Prospect has not indicated interest in a meeting"
            )
        
        # For now, this is a placeholder that marks the workflow as completed
        # In the future, this will integrate with a Meeting Agent
        state["meeting_setup"] = {
            "status": "placeholder_completed",
            "message": "Meeting agent integration coming soon",
            "setup_at": datetime.now().isoformat(),
            "note": "This workflow stage is ready for Meeting Agent implementation"
        }
        
        # Mark workflow as completed
        state = StateManager.update_stage(state, WorkflowStage.COMPLETED)
        
        # Save updated state
        persistence_manager.save_state(workflow_id, state)
        
        logger.info("Meeting setup completed (placeholder)", workflow_id=workflow_id)
        
        return {
            "status": "completed",
            "message": "Workflow completed successfully! Meeting agent integration coming soon.",
            "next_steps": "Future: Integrate with Meeting Agent for automated scheduling",
            "workflow_complete": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to setup meeting", error=str(e), workflow_id=workflow_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to setup meeting: {str(e)}"
        )


async def _extract_proposal_data(state: Dict[str, Any]) -> Dict[str, Any]:
    """Extract data needed for proposal generation from workflow state"""
    
    # Get basic prospect data
    prospect_data = state.get("prospect_data", {})
    
    # Get event overview if available
    event_overview = state.get("event_overview", {})
    event_details = event_overview.get("event_details", {})
    
    # Get conversation summary
    conversation_summary = state.get("conversation_summary", {})
    
    # Extract enriched data
    enriched_data = state.get("enriched_data", {})
    
    # Build proposal data structure
    proposal_data = {
        "client_company": getattr(prospect_data, 'company_name', getattr(prospect_data, 'company', 'Client Company')),
        "prospect_name": getattr(prospect_data, 'name', 'Prospect'),
        "prospect_email": getattr(prospect_data, 'email', ''),
        "industry": enriched_data.get("industry", "Corporate"),
        "location": getattr(prospect_data, 'location', 'TBD'),
        
        # Event details from overview
        "event_type": event_details.get("event_type", "Corporate Event"),
        "date_timeframe": event_details.get("date_timeframe", "TBD"),
        "guest_count": event_details.get("guest_count", "100-150"),
        "budget_range": event_details.get("budget_range", "TBD"),
        "venue_preferences": event_details.get("venue_preferences", "TBD"),
        "special_requirements": event_details.get("special_requirements", []),
        "themes_vision": event_details.get("themes_vision", "Professional and memorable"),
        
        # Conversation context
        "conversation_summary": conversation_summary.get("summary", ""),
        "reply_intent": conversation_summary.get("last_reply_intent", "INTERESTED"),
        
        # Additional context
        "workflow_id": state.get("workflow_id", ""),
        "enrichment_summary": enriched_data.get("summary", ""),
        "company_size": enriched_data.get("company_size", "Medium"),
        "website": enriched_data.get("website", "")
    }
    
    return proposal_data


async def _analyze_meeting_response(reply: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze meeting response to determine prospect interest"""
    from app.services.gemini_service import gemini_service
    
    reply_body = reply.get("body", "")
    
    system_prompt = (
        "You are an event planning assistant analyzing a client's response to a proposal and meeting request. "
        "Determine if the client wants to schedule a meeting and extract any specific requirements or questions."
    )
    
    user_message = f"""
    Analyze the following client response to our proposal and meeting request:
    
    **Client Response:**
    {reply_body}
    
    **Determine:**
    1. Does the client want to schedule a meeting?
    2. What are their main concerns or questions?
    3. What are the next steps?
    
    Return a JSON object with:
    {{
        "wants_meeting": true/false,
        "summary": "Brief summary of their response",
        "concerns": ["concern1", "concern2"],
        "questions": ["question1", "question2"],
        "next_steps": "What should we do next"
    }}
    """
    
    try:
        analysis = await gemini_service.generate_json_response(
            system_prompt=system_prompt,
            user_message=user_message
        )
        return analysis
    except Exception as e:
        logger.error("Failed to analyze meeting response", error=str(e))
        return {
            "wants_meeting": False,
            "summary": "Unable to analyze meeting response",
            "concerns": [],
            "questions": [],
            "next_steps": "Manual review required"
        }
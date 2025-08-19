"""
Meeting Workflow API endpoints for transitioning from proposal to meeting phase
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any
import structlog

from app.api.deps import get_current_user
from app.core.state import WorkflowStage, StateManager
from app.core.persistence import persistence_manager
from app.db.schemas import User

logger = structlog.get_logger(__name__)

router = APIRouter()

@router.post("/{workflow_id}/proceed-to-meeting")
async def proceed_to_meeting_phase(
    workflow_id: str
    # TODO: Re-enable auth after testing: current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Transition workflow from proposal phase to meeting phase
    This is called when the proposal is sent and we need to start meeting scheduling
    """
    logger.info("Proceeding to meeting phase", workflow_id=workflow_id)
    
    try:
        # Load workflow state
        state = persistence_manager.load_state(workflow_id)
        if not state:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workflow not found"
            )
        
        current_stage = state.get("current_stage")
        logger.info("Current workflow stage", workflow_id=workflow_id, current_stage=current_stage)
        
        # Verify workflow is in a valid state to proceed to meeting
        if current_stage not in [WorkflowStage.PROPOSAL, WorkflowStage.MEETING]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot proceed to meeting phase from current stage: {current_stage}"
            )
        
        # Verify proposal was sent
        proposal = state.get("proposal", {})
        if proposal.get("status") != "sent":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Proposal must be sent before proceeding to meeting phase"
            )
        
        # Update workflow stage to meeting
        state = StateManager.update_stage(state, WorkflowStage.MEETING)
        
        # Save updated state
        persistence_manager.save_state(workflow_id, state)
        
        logger.info(
            "Successfully transitioned to meeting phase",
            workflow_id=workflow_id,
            previous_stage=current_stage
        )
        
        return {
            "status": "success", 
            "message": "Workflow transitioned to meeting phase",
            "workflow_id": workflow_id,
            "current_stage": WorkflowStage.MEETING,
            "can_check_meeting_response": True,
            "can_schedule_meeting": False  # Until we receive positive response
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to proceed to meeting phase", 
                    workflow_id=workflow_id, 
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to proceed to meeting phase: {str(e)}"
        )
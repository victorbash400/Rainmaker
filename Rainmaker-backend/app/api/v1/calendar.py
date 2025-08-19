"""
Calendar API endpoints for meeting scheduling and Google Calendar integration
"""
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Dict, List, Any, Optional
import structlog
from datetime import datetime

from app.api.deps import get_db, get_current_user
from app.db.models import User, Campaign, Meeting
from app.db.schemas import MeetingCreate, MeetingResponse, MeetingUpdate
from app.core.persistence import persistence_manager
from app.agents.calendar import CalendarAgent

router = APIRouter()
logger = structlog.get_logger(__name__)
calendar_agent = CalendarAgent()

@router.post("/{workflow_id}/check-meeting-response")
async def check_meeting_response(
    workflow_id: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Check for client email responses to meeting requests
    """
    logger.info("API: Checking meeting response", workflow_id=workflow_id, user_id=current_user.id)
    
    try:
        # Get workflow state
        state = await persistence_manager.load_state(workflow_id)
        if not state:
            raise HTTPException(status_code=404, detail="Workflow not found")
        
        # Check for meeting responses using calendar agent
        response_result = await calendar_agent.check_meeting_response(state)
        
        if response_result["status"] == "error":
            raise HTTPException(status_code=500, detail=response_result["message"])
        
        # If meeting accepted, update workflow state
        if response_result.get("wants_meeting", False):
            state["meeting_response"] = {
                "status": "accepted",
                "preferences": response_result.get("meeting_preferences", {}),
                "response_analysis": response_result.get("response_analysis", ""),
                "received_at": datetime.now().isoformat()
            }
            await persistence_manager.save_state(workflow_id, state)
        
        logger.info("Meeting response check completed", 
                   workflow_id=workflow_id, 
                   status=response_result["status"])
        
        return response_result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to check meeting response", 
                    workflow_id=workflow_id, 
                    error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to check meeting response: {str(e)}")

@router.post("/{workflow_id}/schedule-meeting")
async def schedule_meeting(
    workflow_id: str,
    background_tasks: BackgroundTasks,
    meeting_preferences: Optional[Dict[str, Any]] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Schedule a Google Meet based on client preferences
    """
    logger.info("API: Scheduling meeting", workflow_id=workflow_id, user_id=current_user.id)
    
    try:
        # Get workflow state
        state = await persistence_manager.load_state(workflow_id)
        if not state:
            raise HTTPException(status_code=404, detail="Workflow not found")
        
        # Use meeting preferences from request or from workflow state
        if not meeting_preferences:
            meeting_preferences = state.get("meeting_response", {}).get("preferences", {})
        
        # Schedule the meeting using calendar agent
        schedule_result = await calendar_agent.schedule_google_meet(state, meeting_preferences)
        
        if schedule_result["status"] == "error":
            raise HTTPException(status_code=500, detail=schedule_result["message"])
        
        meeting_details = schedule_result["meeting_details"]
        
        # Create meeting record in database
        meeting_data = MeetingCreate(
            workflow_id=workflow_id,
            prospect_name=meeting_details["prospect_name"],
            prospect_email=meeting_details["prospect_email"],
            prospect_company=meeting_details.get("prospect_company", ""),
            title=meeting_details["title"],
            description=meeting_details["description"],
            scheduled_at=datetime.fromisoformat(meeting_details["start_time"]),
            duration_minutes=int((datetime.fromisoformat(meeting_details["end_time"]) - 
                                datetime.fromisoformat(meeting_details["start_time"])).total_seconds() / 60),
            google_meet_link=meeting_details.get("google_meet_link"),
            calendar_event_id=meeting_details.get("calendar_event_id"),
            status="scheduled"
        )
        
        db_meeting = Meeting(**meeting_data.dict(), user_id=current_user.id)
        db.add(db_meeting)
        db.commit()
        db.refresh(db_meeting)
        
        # Update workflow state
        state["scheduled_meeting"] = {
            "meeting_id": db_meeting.id,
            "status": "scheduled",
            "meeting_details": meeting_details,
            "scheduled_at": datetime.now().isoformat()
        }
        await persistence_manager.save_state(workflow_id, state)
        
        logger.info("Meeting scheduled successfully", 
                   workflow_id=workflow_id,
                   meeting_id=db_meeting.id,
                   meet_link=meeting_details.get("google_meet_link"))

        # Update campaign coordinator status to completed
        try:
            from app.agents.campaign_coordinator import get_global_coordinator
            coordinator = get_global_coordinator()

            # Find the plan_id for this workflow
            plan_id = None
            for pid, execution_state in coordinator.executing_campaigns.items():
                if execution_state.get("workflow_id") == workflow_id:
                    plan_id = pid
                    break
            
            if plan_id:
                logger.info("Marking campaign as completed after meeting schedule", plan_id=plan_id)
                execution_state = coordinator.executing_campaigns[plan_id]
                execution_state["current_phase"] = "completed"
                execution_state["status"] = "completed"
                execution_state["execution_completed_at"] = datetime.now()
                execution_state["metrics"]["meetings_scheduled"] = execution_state["metrics"].get("meetings_scheduled", 0) + 1
                coordinator._broadcast_status_update(plan_id, execution_state, force=True)
            else:
                logger.warning("Could not find plan_id for workflow to mark as completed", workflow_id=workflow_id)

        except Exception as e:
            logger.error("Failed to update campaign coordinator status", error=str(e), workflow_id=workflow_id)
        
        return {
            "status": "success",
            "message": "Meeting scheduled successfully",
            "meeting_id": db_meeting.id,
            "meeting_details": meeting_details,
            "invitation_sent": schedule_result.get("invitation_sent", False)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to schedule meeting", 
                    workflow_id=workflow_id, 
                    error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to schedule meeting: {str(e)}")

@router.get("/{workflow_id}/meetings")
async def get_workflow_meetings(
    workflow_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> List[MeetingResponse]:
    """
    Get all meetings for a specific workflow
    """
    logger.info("API: Getting workflow meetings", workflow_id=workflow_id, user_id=current_user.id)
    
    try:
        meetings = db.query(Meeting).filter(
            Meeting.workflow_id == workflow_id,
            Meeting.user_id == current_user.id
        ).all()
        
        return [MeetingResponse.from_orm(meeting) for meeting in meetings]
        
    except Exception as e:
        logger.error("Failed to get workflow meetings", 
                    workflow_id=workflow_id, 
                    error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get meetings: {str(e)}")

@router.get("/meetings")
async def get_all_meetings(
    limit: int = 50,
    offset: int = 0,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get all meetings for the current user
    """
    logger.info("API: Getting all meetings", user_id=current_user.id, limit=limit, offset=offset)
    
    try:
        query = db.query(Meeting).filter(Meeting.user_id == current_user.id)
        
        if status:
            query = query.filter(Meeting.status == status)
        
        total = query.count()
        meetings = query.offset(offset).limit(limit).all()
        
        return {
            "meetings": [MeetingResponse.from_orm(meeting) for meeting in meetings],
            "total": total,
            "limit": limit,
            "offset": offset
        }
        
    except Exception as e:
        logger.error("Failed to get all meetings", 
                    user_id=current_user.id, 
                    error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get meetings: {str(e)}")

@router.put("/meetings/{meeting_id}")
async def update_meeting(
    meeting_id: int,
    meeting_update: MeetingUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> MeetingResponse:
    """
    Update a meeting
    """
    logger.info("API: Updating meeting", meeting_id=meeting_id, user_id=current_user.id)
    
    try:
        meeting = db.query(Meeting).filter(
            Meeting.id == meeting_id,
            Meeting.user_id == current_user.id
        ).first()
        
        if not meeting:
            raise HTTPException(status_code=404, detail="Meeting not found")
        
        # Update meeting fields
        for field, value in meeting_update.dict(exclude_unset=True).items():
            setattr(meeting, field, value)
        
        meeting.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(meeting)
        
        logger.info("Meeting updated successfully", meeting_id=meeting_id)
        return MeetingResponse.from_orm(meeting)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update meeting", 
                    meeting_id=meeting_id, 
                    error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to update meeting: {str(e)}")

@router.delete("/meetings/{meeting_id}")
async def cancel_meeting(
    meeting_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, str]:
    """
    Cancel a meeting
    """
    logger.info("API: Cancelling meeting", meeting_id=meeting_id, user_id=current_user.id)
    
    try:
        meeting = db.query(Meeting).filter(
            Meeting.id == meeting_id,
            Meeting.user_id == current_user.id
        ).first()
        
        if not meeting:
            raise HTTPException(status_code=404, detail="Meeting not found")
        
        # Update status to cancelled
        meeting.status = "cancelled"
        meeting.updated_at = datetime.utcnow()
        db.commit()
        
        # TODO: Send cancellation email to prospect
        # TODO: Cancel Google Calendar event if exists
        
        logger.info("Meeting cancelled successfully", meeting_id=meeting_id)
        return {"status": "success", "message": "Meeting cancelled successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to cancel meeting", 
                    meeting_id=meeting_id, 
                    error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to cancel meeting: {str(e)}")

@router.post("/google-meet/create")
async def create_google_meet_event(
    event_details: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Create a Google Meet event directly (for manual scheduling)
    """
    logger.info("API: Creating Google Meet event", user_id=current_user.id)
    
    try:
        # This would integrate with actual Google Calendar API
        # For now, return placeholder data
        
        event_id = f"manual_{current_user.id}_{int(datetime.now().timestamp())}"
        meet_link = f"https://meet.google.com/{event_id}"
        
        return {
            "status": "success",
            "event_id": event_id,
            "google_meet_link": meet_link,
            "calendar_link": f"https://calendar.google.com/event?eid={event_id}"
        }
        
    except Exception as e:
        logger.error("Failed to create Google Meet event", 
                    user_id=current_user.id, 
                    error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to create Google Meet event: {str(e)}")

@router.get("/{workflow_id}/status")
async def get_calendar_status(
    workflow_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get calendar/meeting status for a workflow
    """
    logger.info("API: Getting calendar status", workflow_id=workflow_id, user_id=current_user.id)
    
    try:
        # Get workflow state
        state = await persistence_manager.load_state(workflow_id)
        if not state:
            raise HTTPException(status_code=404, detail="Workflow not found")
        
        # Get meeting response status
        meeting_response = state.get("meeting_response", {})
        scheduled_meeting = state.get("scheduled_meeting", {})
        
        # Get meeting records from database
        meetings = db.query(Meeting).filter(
            Meeting.workflow_id == workflow_id,
            Meeting.user_id == current_user.id
        ).all()
        
        return {
            "workflow_id": workflow_id,
            "has_meeting_response": bool(meeting_response),
            "meeting_response_status": meeting_response.get("status", "pending"),
            "has_scheduled_meeting": bool(scheduled_meeting),
            "scheduled_meeting_count": len(meetings),
            "latest_meeting": MeetingResponse.from_orm(meetings[-1]) if meetings else None,
            "can_check_response": True,  # Always allow checking for responses
            "can_schedule_meeting": meeting_response.get("status") == "accepted"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get calendar status", 
                    workflow_id=workflow_id, 
                    error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get calendar status: {str(e)}")
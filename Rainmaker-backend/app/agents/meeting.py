"""
Advanced Meeting Agent powered by GPT-4 with MCP integration.

This agent handles intelligent meeting scheduling, calendar integration,
preparation materials, follow-up automation, and meeting optimization
to maximize conversion rates and client satisfaction.
"""

import asyncio
import json
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta, time
from dataclasses import dataclass, field
from enum import Enum
import structlog

from app.core.state import RainmakerState, MeetingDetails, ProspectData
from app.core.config import settings
from app.services.openai_service import openai_service
from app.mcp.calendar import calendar_mcp
from app.mcp.email import email_mcp
from app.mcp.database import database_mcp
from app.db.models import ProspectStatus

logger = structlog.get_logger(__name__)


class MeetingType(str, Enum):
    """Types of meetings"""
    INITIAL_CONSULTATION = "initial_consultation"
    VENUE_VISIT = "venue_visit"
    PLANNING_SESSION = "planning_session"
    PROPOSAL_REVIEW = "proposal_review"
    CONTRACT_SIGNING = "contract_signing"
    FINAL_WALKTHROUGH = "final_walkthrough"
    FOLLOW_UP = "follow_up"


class MeetingPriority(str, Enum):
    """Meeting priority levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class AvailabilitySlot:
    """Available time slot for meeting"""
    start_time: datetime
    end_time: datetime
    slot_type: str  # "morning", "afternoon", "evening"
    confidence: float  # How good this slot is
    timezone: str
    buffer_before: int = 15  # minutes
    buffer_after: int = 15   # minutes


@dataclass
class MeetingPreparation:
    """Meeting preparation materials and agenda"""
    agenda_items: List[str]
    preparation_materials: List[Dict[str, str]]
    questions_to_ask: List[str]
    documents_to_bring: List[str]
    goals_and_objectives: List[str]
    talking_points: List[str]
    potential_objections: List[Dict[str, str]]
    follow_up_actions: List[str]


@dataclass
class MeetingContext:
    """Context for meeting scheduling and preparation"""
    prospect_data: ProspectData
    meeting_purpose: str
    urgency_level: str
    preferred_duration: int  # minutes
    meeting_type: MeetingType
    location_preference: str = "virtual"  # virtual, in-person, client-location
    stakeholders: List[str] = field(default_factory=list)
    previous_meetings: List[Dict[str, Any]] = field(default_factory=list)
    preparation_time_needed: int = 60  # minutes
    follow_up_required: bool = True


class MeetingAgent:
    """
    Advanced Meeting Agent that handles intelligent scheduling and meeting management.
    
    Provides calendar integration, availability optimization, preparation materials,
    automated reminders, and follow-up management to maximize meeting effectiveness
    and conversion rates.
    """
    
    def __init__(self):
        self.openai_service = openai_service
        self.default_meeting_duration = 60  # minutes
        self.business_hours_start = time(9, 0)   # 9 AM
        self.business_hours_end = time(17, 0)    # 5 PM
        self.timezone = "UTC"  # Should be configured per user
        self.max_scheduling_attempts = 3
        
    async def schedule_meeting(self, state: RainmakerState) -> RainmakerState:
        """
        Main meeting scheduling method that handles end-to-end meeting coordination.
        """
        logger.info("Starting meeting scheduling", workflow_id=state.get("workflow_id"))
        
        try:
            prospect_data = state["prospect_data"]
            conversation_summary = state.get("conversation_summary")
            proposal_data = state.get("proposal_data")
            
            # Build meeting context
            meeting_context = await self._build_meeting_context(
                prospect_data, conversation_summary, proposal_data, state
            )
            
            # Find optimal meeting time
            optimal_slots = await self._find_optimal_meeting_slots(meeting_context)
            
            # Select best slot and schedule meeting
            selected_slot = await self._select_and_schedule_meeting(optimal_slots, meeting_context)
            
            # Prepare meeting materials
            meeting_preparation = await self._prepare_meeting_materials(meeting_context, selected_slot)
            
            # Send meeting invitations and confirmations
            invitation_sent = await self._send_meeting_invitations(selected_slot, meeting_context, meeting_preparation)
            
            # Set up automated reminders
            await self._setup_meeting_reminders(selected_slot, meeting_context)
            
            # Create comprehensive meeting details
            meeting_details = self._create_meeting_details(
                selected_slot, meeting_context, meeting_preparation, invitation_sent
            )
            
            # Store meeting in database
            await self._store_meeting_in_database(meeting_details, prospect_data.id)
            
            # Update state
            state["meeting_details"] = meeting_details
            
            # Update prospect status
            await self._update_prospect_status(prospect_data.id, ProspectStatus.QUALIFIED)
            
            logger.info(
                "Meeting scheduling completed",
                workflow_id=state.get("workflow_id"),
                meeting_type=meeting_context.meeting_type.value,
                scheduled_time=selected_slot.start_time if selected_slot else None
            )
            
            return state
            
        except Exception as e:
            logger.error("Meeting scheduling failed", error=str(e), workflow_id=state.get("workflow_id"))
            raise
    
    async def _build_meeting_context(self, prospect_data: ProspectData,
                                   conversation_summary: Optional[Any],
                                   proposal_data: Optional[Any],
                                   state: RainmakerState) -> MeetingContext:
        """Build comprehensive context for meeting scheduling"""
        
        # Determine meeting type and purpose based on workflow stage
        if proposal_data:
            meeting_type = MeetingType.PROPOSAL_REVIEW
            purpose = "Review and discuss the event proposal in detail"
        elif conversation_summary and conversation_summary.qualification_score > 70:
            meeting_type = MeetingType.INITIAL_CONSULTATION
            purpose = "Initial consultation to understand event requirements and vision"
        else:
            meeting_type = MeetingType.FOLLOW_UP
            purpose = "Follow-up discussion about event planning services"
        
        # Determine urgency based on various factors
        urgency_level = await self._determine_meeting_urgency(
            prospect_data, conversation_summary, proposal_data
        )
        
        # Get previous meetings
        previous_meetings = await self._get_previous_meetings(prospect_data.id)
        
        # Determine stakeholders
        stakeholders = await self._identify_meeting_stakeholders(
            prospect_data, conversation_summary
        )
        
        return MeetingContext(
            prospect_data=prospect_data,
            meeting_purpose=purpose,
            urgency_level=urgency_level,
            preferred_duration=self._determine_meeting_duration(meeting_type, conversation_summary),
            meeting_type=meeting_type,
            location_preference=self._determine_location_preference(prospect_data),
            stakeholders=stakeholders,
            previous_meetings=previous_meetings,
            preparation_time_needed=30 if meeting_type == MeetingType.FOLLOW_UP else 60
        )
    
    async def _determine_meeting_urgency(self, prospect_data: ProspectData,
                                       conversation_summary: Optional[Any],
                                       proposal_data: Optional[Any]) -> str:
        """Determine urgency level for meeting scheduling"""
        
        urgency_factors = []
        
        # High lead score indicates hot prospect
        if prospect_data.lead_score > 85:
            urgency_factors.append("high_lead_score")
        
        # Recent proposal needs follow-up
        if proposal_data:
            urgency_factors.append("proposal_sent")
        
        # High engagement in conversation
        if conversation_summary and conversation_summary.qualification_score > 80:
            urgency_factors.append("highly_qualified")
        
        # Time-sensitive indicators in conversation
        if conversation_summary and conversation_summary.metadata:
            if "urgent" in str(conversation_summary.metadata).lower():
                urgency_factors.append("explicit_urgency")
        
        # Determine overall urgency
        if len(urgency_factors) >= 3 or "explicit_urgency" in urgency_factors:
            return "urgent"
        elif len(urgency_factors) >= 2:
            return "high"
        elif len(urgency_factors) >= 1:
            return "medium"
        else:
            return "low"
    
    def _determine_meeting_duration(self, meeting_type: MeetingType, 
                                  conversation_summary: Optional[Any]) -> int:
        """Determine optimal meeting duration based on type and context"""
        
        duration_map = {
            MeetingType.INITIAL_CONSULTATION: 45,
            MeetingType.VENUE_VISIT: 90,
            MeetingType.PLANNING_SESSION: 60,
            MeetingType.PROPOSAL_REVIEW: 30,
            MeetingType.CONTRACT_SIGNING: 30,
            MeetingType.FINAL_WALKTHROUGH: 120,
            MeetingType.FOLLOW_UP: 30
        }
        
        base_duration = duration_map.get(meeting_type, 60)
        
        # Adjust based on conversation complexity
        if conversation_summary:
            requirements = conversation_summary.extracted_requirements
            if requirements and len(requirements.get("special_requirements", [])) > 3:
                base_duration += 15  # Add time for complex requirements
        
        return base_duration
    
    def _determine_location_preference(self, prospect_data: ProspectData) -> str:
        """Determine meeting location preference"""
        
        # Default to virtual for efficiency
        if prospect_data.prospect_type == "company":
            return "virtual"  # Corporate clients often prefer virtual meetings
        
        # Individual clients might prefer in-person for major events
        return "flexible"  # Offer both options
    
    async def _get_previous_meetings(self, prospect_id: Optional[int]) -> List[Dict[str, Any]]:
        """Get previous meetings with this prospect"""
        if not prospect_id:
            return []
        
        try:
            result = await database_mcp.server.call_tool(
                "execute_query",
                {
                    "query": """
                    SELECT meeting_type, title, scheduled_at, status, notes
                    FROM meetings
                    WHERE prospect_id = ?
                    ORDER BY scheduled_at DESC
                    LIMIT 10
                    """,
                    "parameters": [prospect_id],
                    "fetch_mode": "all"
                }
            )
            
            if not result.isError:
                result_data = json.loads(result.content[0].text)
                return result_data.get("result", [])
                
        except Exception as e:
            logger.warning("Failed to get previous meetings", error=str(e))
        
        return []
    
    async def _identify_meeting_stakeholders(self, prospect_data: ProspectData,
                                           conversation_summary: Optional[Any]) -> List[str]:
        """Identify key stakeholders for the meeting"""
        
        stakeholders = [prospect_data.name]
        
        # Add decision makers from conversation
        if conversation_summary and conversation_summary.extracted_requirements:
            decision_makers = conversation_summary.extracted_requirements.get("decision_makers", [])
            stakeholders.extend(decision_makers)
        
        # For corporate events, likely include additional stakeholders
        if prospect_data.prospect_type == "company":
            stakeholders.append("Event Committee Member")
        
        return list(set(stakeholders))  # Remove duplicates
    
    async def _find_optimal_meeting_slots(self, context: MeetingContext) -> List[AvailabilitySlot]:
        """Find optimal meeting time slots using calendar integration and AI analysis"""
        
        # Get calendar availability
        calendar_availability = await self._get_calendar_availability(context)
        
        # Generate intelligent time suggestions using GPT-4
        suggested_slots = await self._generate_intelligent_time_suggestions(context, calendar_availability)
        
        # Score and rank slots
        ranked_slots = await self._score_and_rank_slots(suggested_slots, context)
        
        return ranked_slots[:5]  # Return top 5 options
    
    async def _get_calendar_availability(self, context: MeetingContext) -> Dict[str, Any]:
        """Get calendar availability using Calendar MCP"""
        
        try:
            # Look for availability in the next 2 weeks
            start_date = datetime.now()
            end_date = start_date + timedelta(days=14)
            
            # Adjust timeline based on urgency
            if context.urgency_level == "urgent":
                end_date = start_date + timedelta(days=3)
            elif context.urgency_level == "high":
                end_date = start_date + timedelta(days=7)
            
            availability_result = await calendar_mcp.server.call_tool(
                "check_availability",
                {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "duration_minutes": context.preferred_duration,
                    "business_hours_only": True
                }
            )
            
            if not availability_result.isError:
                return json.loads(availability_result.content[0].text)
            
        except Exception as e:
            logger.warning("Calendar availability check failed", error=str(e))
        
        # Fallback to generated availability
        return self._generate_fallback_availability(context)
    
    def _generate_fallback_availability(self, context: MeetingContext) -> Dict[str, Any]:
        """Generate fallback availability when calendar check fails"""
        
        available_slots = []
        start_date = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
        
        # Generate slots for next 5 business days
        for day_offset in range(5):
            day_start = start_date + timedelta(days=day_offset)
            
            # Skip weekends
            if day_start.weekday() >= 5:
                continue
            
            # Generate morning and afternoon slots
            morning_slot = day_start.replace(hour=10, minute=0)
            afternoon_slot = day_start.replace(hour=14, minute=0)
            
            available_slots.extend([
                morning_slot.isoformat(),
                afternoon_slot.isoformat()
            ])
        
        return {"available_slots": available_slots}
    
    async def _generate_intelligent_time_suggestions(self, context: MeetingContext,
                                                   calendar_availability: Dict[str, Any]) -> List[AvailabilitySlot]:
        """Use GPT-4 to generate intelligent meeting time suggestions"""
        
        time_suggestion_prompt = f"""
        Suggest optimal meeting times for this event planning prospect:

        PROSPECT CONTEXT:
        - Name: {context.prospect_data.name}
        - Type: {context.prospect_data.prospect_type}
        - Location: {context.prospect_data.location}
        - Meeting Type: {context.meeting_type.value}
        - Duration: {context.preferred_duration} minutes
        - Urgency: {context.urgency_level}

        AVAILABLE SLOTS:
        {json.dumps(calendar_availability.get("available_slots", [])[:10], indent=2)}

        OPTIMIZATION FACTORS:
        1. Business hours and professional scheduling
        2. Meeting type appropriateness (consultation vs review)
        3. Prospect location and likely timezone
        4. Urgency level and response expectations
        5. Professional scheduling best practices

        Select and rank the best 5 time slots with reasoning.
        Return as JSON array with format:
        [{{
            "start_time": "ISO datetime",
            "slot_type": "morning/afternoon/evening",
            "confidence": 0.0-1.0,
            "reasoning": "why this slot is good"
        }}]
        """
        
        try:
            response = await self.openai_service.generate_agent_response(
                system_prompt="You are an expert meeting scheduler for event planning businesses. Optimize for client convenience and conversion rates.",
                user_message=time_suggestion_prompt,
                model="gpt-4"
            )
            
            suggestions_data = json.loads(response)
            availability_slots = []
            
            for suggestion in suggestions_data:
                start_time = datetime.fromisoformat(suggestion["start_time"])
                end_time = start_time + timedelta(minutes=context.preferred_duration)
                
                slot = AvailabilitySlot(
                    start_time=start_time,
                    end_time=end_time,
                    slot_type=suggestion["slot_type"],
                    confidence=suggestion["confidence"],
                    timezone=self.timezone
                )
                
                availability_slots.append(slot)
            
            return availability_slots
            
        except Exception as e:
            logger.warning("Intelligent time suggestion failed", error=str(e))
            return self._create_fallback_slots(context, calendar_availability)
    
    def _create_fallback_slots(self, context: MeetingContext, 
                             calendar_availability: Dict[str, Any]) -> List[AvailabilitySlot]:
        """Create fallback availability slots when AI suggestion fails"""
        
        available_slots = calendar_availability.get("available_slots", [])
        if not available_slots:
            return []
        
        slots = []
        for slot_time_str in available_slots[:5]:
            try:
                start_time = datetime.fromisoformat(slot_time_str)
                end_time = start_time + timedelta(minutes=context.preferred_duration)
                
                # Determine slot type
                hour = start_time.hour
                if hour < 12:
                    slot_type = "morning"
                elif hour < 17:
                    slot_type = "afternoon"
                else:
                    slot_type = "evening"
                
                slot = AvailabilitySlot(
                    start_time=start_time,
                    end_time=end_time,
                    slot_type=slot_type,
                    confidence=0.7,  # Default confidence
                    timezone=self.timezone
                )
                
                slots.append(slot)
                
            except Exception:
                continue
        
        return slots
    
    async def _score_and_rank_slots(self, slots: List[AvailabilitySlot], 
                                  context: MeetingContext) -> List[AvailabilitySlot]:
        """Score and rank availability slots based on multiple factors"""
        
        for slot in slots:
            score_factors = []
            
            # Time of day scoring
            hour = slot.start_time.hour
            if 10 <= hour <= 16:  # Prime business hours
                score_factors.append(0.3)
            elif 9 <= hour <= 17:  # Extended business hours
                score_factors.append(0.2)
            else:
                score_factors.append(0.1)
            
            # Urgency matching
            days_from_now = (slot.start_time - datetime.now()).days
            if context.urgency_level == "urgent" and days_from_now <= 2:
                score_factors.append(0.4)
            elif context.urgency_level == "high" and days_from_now <= 5:
                score_factors.append(0.3)
            elif days_from_now <= 10:
                score_factors.append(0.2)
            
            # Meeting type appropriateness
            if context.meeting_type == MeetingType.INITIAL_CONSULTATION:
                if slot.slot_type in ["morning", "afternoon"]:
                    score_factors.append(0.2)
            
            # Update confidence with calculated score
            slot.confidence = min(sum(score_factors), 1.0)
        
        # Sort by confidence descending
        return sorted(slots, key=lambda s: s.confidence, reverse=True)
    
    async def _select_and_schedule_meeting(self, slots: List[AvailabilitySlot],
                                         context: MeetingContext) -> Optional[AvailabilitySlot]:
        """Select best slot and schedule the meeting"""
        
        if not slots:
            logger.warning("No available slots for meeting scheduling")
            return None
        
        # Select highest confidence slot
        selected_slot = slots[0]
        
        try:
            # Create calendar event
            meeting_result = await calendar_mcp.server.call_tool(
                "create_event",
                {
                    "title": f"{context.meeting_type.value.replace('_', ' ').title()} - {context.prospect_data.name}",
                    "description": context.meeting_purpose,
                    "start_time": selected_slot.start_time.isoformat(),
                    "end_time": selected_slot.end_time.isoformat(),
                    "attendees": [
                        {"email": context.prospect_data.email, "name": context.prospect_data.name}
                    ] if context.prospect_data.email else [],
                    "location": "Virtual Meeting" if context.location_preference == "virtual" else "TBD"
                }
            )
            
            if not meeting_result.isError:
                meeting_data = json.loads(meeting_result.content[0].text)
                # Add calendar event ID to slot
                selected_slot.calendar_event_id = meeting_data.get("event_id")
            
            return selected_slot
            
        except Exception as e:
            logger.error("Failed to schedule meeting in calendar", error=str(e))
            return selected_slot  # Return slot even if calendar creation failed
    
    async def _prepare_meeting_materials(self, context: MeetingContext, 
                                       selected_slot: Optional[AvailabilitySlot]) -> MeetingPreparation:
        """Prepare comprehensive meeting materials using GPT-4"""
        
        preparation_prompt = f"""
        Create comprehensive meeting preparation materials:

        MEETING CONTEXT:
        - Prospect: {context.prospect_data.name} ({context.prospect_data.prospect_type})
        - Type: {context.meeting_type.value}
        - Purpose: {context.meeting_purpose}
        - Duration: {context.preferred_duration} minutes
        - Urgency: {context.urgency_level}
        - Stakeholders: {context.stakeholders}

        PREVIOUS MEETINGS:
        {json.dumps(context.previous_meetings[-3:] if context.previous_meetings else [], indent=2)}

        Create:
        1. AGENDA ITEMS (4-6 key discussion points)
        2. PREPARATION MATERIALS (documents, portfolios, samples to prepare)
        3. QUESTIONS TO ASK (discovery questions specific to their needs)
        4. DOCUMENTS TO BRING (contracts, portfolios, pricing sheets)
        5. GOALS AND OBJECTIVES (what we want to achieve)
        6. KEY TALKING POINTS (value propositions, differentiators)
        7. POTENTIAL OBJECTIONS (common concerns and responses)
        8. FOLLOW-UP ACTIONS (next steps to plan)

        Focus on maximizing conversion and client satisfaction.
        Return as structured JSON.
        """
        
        try:
            response = await self.openai_service.generate_agent_response(
                system_prompt="You are an expert event planning sales manager. Create materials that maximize meeting effectiveness and client conversion.",
                user_message=preparation_prompt,
                model="gpt-4"
            )
            
            prep_data = json.loads(response)
            
            return MeetingPreparation(
                agenda_items=prep_data.get("agenda_items", []),
                preparation_materials=prep_data.get("preparation_materials", []),
                questions_to_ask=prep_data.get("questions_to_ask", []),
                documents_to_bring=prep_data.get("documents_to_bring", []),
                goals_and_objectives=prep_data.get("goals_and_objectives", []),
                talking_points=prep_data.get("talking_points", []),
                potential_objections=prep_data.get("potential_objections", []),
                follow_up_actions=prep_data.get("follow_up_actions", [])
            )
            
        except Exception as e:
            logger.warning("Meeting preparation generation failed", error=str(e))
            return self._create_fallback_preparation(context)
    
    async def _send_meeting_invitations(self, selected_slot: Optional[AvailabilitySlot],
                                       context: MeetingContext,
                                       preparation: MeetingPreparation) -> bool:
        """Send meeting invitations and confirmation emails"""
        
        if not selected_slot or not context.prospect_data.email:
            return False
        
        try:
            # Generate invitation email content
            invitation_content = await self._generate_invitation_email(selected_slot, context, preparation)
            
            # Send invitation email
            email_result = await email_mcp.server.call_tool(
                "send_email",
                {
                    "to_email": context.prospect_data.email,
                    "to_name": context.prospect_data.name,
                    "subject": f"Meeting Invitation: {context.meeting_type.value.replace('_', ' ').title()}",
                    "html_content": invitation_content,
                    "text_content": invitation_content  # Simplified - should strip HTML
                }
            )
            
            return not email_result.isError
            
        except Exception as e:
            logger.error("Failed to send meeting invitation", error=str(e))
            return False
    
    async def _generate_invitation_email(self, selected_slot: AvailabilitySlot,
                                       context: MeetingContext,
                                       preparation: MeetingPreparation) -> str:
        """Generate professional meeting invitation email"""
        
        meeting_date = selected_slot.start_time.strftime("%B %d, %Y")
        meeting_time = selected_slot.start_time.strftime("%I:%M %p")
        
        return f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <h2>Meeting Invitation - {context.meeting_type.value.replace('_', ' ').title()}</h2>
            
            <p>Dear {context.prospect_data.name},</p>
            
            <p>Thank you for your interest in our event planning services! I'm excited to schedule our {context.meeting_type.value.replace('_', ' ')} to discuss your upcoming event.</p>
            
            <div style="background-color: #f8f9fa; padding: 20px; border-radius: 5px; margin: 20px 0;">
                <h3>Meeting Details:</h3>
                <p><strong>Date:</strong> {meeting_date}</p>
                <p><strong>Time:</strong> {meeting_time}</p>
                <p><strong>Duration:</strong> {context.preferred_duration} minutes</p>
                <p><strong>Location:</strong> Virtual Meeting (link to be sent)</p>
            </div>
            
            <h3>What We'll Cover:</h3>
            <ul>
                {"".join(f"<li>{item}</li>" for item in preparation.agenda_items[:4])}
            </ul>
            
            <h3>To Prepare:</h3>
            <p>Please think about your event vision, preferred dates, and any special requirements you'd like to discuss.</p>
            
            <p>If this time doesn't work for you, please let me know your availability and I'll be happy to reschedule.</p>
            
            <p>Looking forward to creating something amazing together!</p>
            
            <p>Best regards,<br>
            [Your Event Planning Team]</p>
        </body>
        </html>
        """
    
    async def _setup_meeting_reminders(self, selected_slot: Optional[AvailabilitySlot],
                                     context: MeetingContext):
        """Set up automated meeting reminders"""
        
        if not selected_slot or not context.prospect_data.email:
            return
        
        # Schedule reminders for:
        # - 1 day before
        # - 2 hours before
        # - Follow-up after meeting
        
        reminder_times = [
            selected_slot.start_time - timedelta(days=1),
            selected_slot.start_time - timedelta(hours=2),
            selected_slot.start_time + timedelta(hours=2)  # Follow-up
        ]
        
        for reminder_time in reminder_times:
            if reminder_time > datetime.now():
                # In a real implementation, this would schedule background tasks
                logger.info(f"Reminder scheduled for {reminder_time}")
    
    def _create_meeting_details(self, selected_slot: Optional[AvailabilitySlot],
                              context: MeetingContext,
                              preparation: MeetingPreparation,
                              invitation_sent: bool) -> MeetingDetails:
        """Create comprehensive meeting details object"""
        
        if not selected_slot:
            # Create placeholder details for failed scheduling
            return MeetingDetails(
                meeting_type=context.meeting_type.value,
                title=f"Meeting with {context.prospect_data.name}",
                description=context.meeting_purpose,
                scheduled_at=None,
                duration_minutes=context.preferred_duration,
                status="failed_to_schedule",
                attendees=[{"name": context.prospect_data.name, "email": context.prospect_data.email}],
                meeting_metadata={
                    "scheduling_failed": True,
                    "urgency_level": context.urgency_level
                }
            )
        
        return MeetingDetails(
            meeting_type=context.meeting_type.value,
            title=f"{context.meeting_type.value.replace('_', ' ').title()} - {context.prospect_data.name}",
            description=context.meeting_purpose,
            scheduled_at=selected_slot.start_time,
            duration_minutes=context.preferred_duration,
            location="Virtual Meeting" if context.location_preference == "virtual" else "TBD",
            meeting_url="https://meet.example.com/meeting-room",  # Would be generated
            calendar_event_id=getattr(selected_slot, 'calendar_event_id', None),
            attendees=[
                {"name": context.prospect_data.name, "email": context.prospect_data.email}
            ],
            agenda="; ".join(preparation.agenda_items),
            status="scheduled" if invitation_sent else "pending_confirmation",
            meeting_metadata={
                "preparation_materials": preparation.preparation_materials,
                "questions_to_ask": preparation.questions_to_ask,
                "goals_and_objectives": preparation.goals_and_objectives,
                "talking_points": preparation.talking_points,
                "potential_objections": preparation.potential_objections,
                "follow_up_actions": preparation.follow_up_actions,
                "urgency_level": context.urgency_level,
                "stakeholders": context.stakeholders,
                "slot_confidence": selected_slot.confidence,
                "scheduling_timestamp": datetime.now().isoformat()
            }
        )
    
    async def _store_meeting_in_database(self, meeting_details: MeetingDetails, prospect_id: Optional[int]):
        """Store meeting details in database"""
        if not prospect_id:
            return
        
        try:
            result = await database_mcp.server.call_tool(
                "execute_query",
                {
                    "query": """
                    INSERT INTO meetings (
                        prospect_id, meeting_type, title, description, 
                        scheduled_at, duration_minutes, location, meeting_url,
                        calendar_event_id, attendees, agenda, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    "parameters": [
                        prospect_id,
                        meeting_details.meeting_type,
                        meeting_details.title,
                        meeting_details.description,
                        meeting_details.scheduled_at.isoformat() if meeting_details.scheduled_at else None,
                        meeting_details.duration_minutes,
                        meeting_details.location,
                        meeting_details.meeting_url,
                        meeting_details.calendar_event_id,
                        json.dumps(meeting_details.attendees),
                        meeting_details.agenda,
                        meeting_details.status
                    ],
                    "fetch_mode": "none"
                }
            )
            
            if not result.isError:
                # Get meeting ID
                id_result = await database_mcp.server.call_tool(
                    "execute_query",
                    {"query": "SELECT LAST_INSERT_ID() as id", "fetch_mode": "one"}
                )
                
                if not id_result.isError:
                    id_data = json.loads(id_result.content[0].text)
                    meeting_details.id = id_data.get("result", {}).get("id")
            
        except Exception as e:
            logger.error("Failed to store meeting in database", error=str(e))
    
    async def _update_prospect_status(self, prospect_id: Optional[int], status: ProspectStatus):
        """Update prospect status after meeting scheduling"""
        if not prospect_id:
            return
        
        try:
            await database_mcp.server.call_tool(
                "execute_query",
                {
                    "query": "UPDATE prospects SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    "parameters": [status.value, prospect_id],
                    "fetch_mode": "none"
                }
            )
        except Exception as e:
            logger.error("Failed to update prospect status", error=str(e))
    
    def _create_fallback_preparation(self, context: MeetingContext) -> MeetingPreparation:
        """Create fallback meeting preparation when generation fails"""
        
        return MeetingPreparation(
            agenda_items=[
                "Introductions and rapport building",
                "Understand event vision and requirements", 
                "Discuss our services and approach",
                "Review timeline and next steps"
            ],
            preparation_materials=[
                {"type": "portfolio", "description": "Event portfolio with similar events"},
                {"type": "pricing", "description": "Service packages and pricing overview"}
            ],
            questions_to_ask=[
                "What's your vision for this event?",
                "What's most important to you for this celebration?",
                "What's your timeline for planning?",
                "What's your approximate budget range?"
            ],
            documents_to_bring=[
                "Company portfolio",
                "Service packages overview",
                "Initial questionnaire"
            ],
            goals_and_objectives=[
                "Understand client needs and preferences",
                "Present our value proposition clearly",
                "Move to proposal stage if qualified"
            ],
            talking_points=[
                "Our experience with similar events",
                "Comprehensive planning approach",
                "Vendor network and relationships"
            ],
            potential_objections=[
                {"objection": "Too expensive", "response": "Let's discuss value and what's included in our comprehensive service"},
                {"objection": "Need to think about it", "response": "I understand. What specific aspects would you like to consider?"}
            ],
            follow_up_actions=[
                "Send proposal within 48 hours",
                "Follow up in 1 week if no response",
                "Schedule venue visits if interested"
            ]
        )
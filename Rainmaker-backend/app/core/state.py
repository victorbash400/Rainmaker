"""
Shared state management for LangGraph agent orchestration.

This module defines the RainmakerState TypedDict and provides utilities for
state validation, serialization, and persistence for workflow recovery.
"""

from typing import TypedDict, List, Optional, Dict, Any, Union
from datetime import datetime
from enum import Enum
import json
import uuid
from pydantic import BaseModel, Field, validator
from app.db.models import ProspectStatus, EventType, CampaignStatus


class WorkflowStage(str, Enum):
    """Workflow stages for agent orchestration"""
    HUNTING = "hunting"
    ENRICHING = "enriching"
    OUTREACH = "outreach"
    CONVERSATION = "conversation"
    PROPOSAL = "proposal"
    MEETING = "meeting"
    COMPLETED = "completed"
    FAILED = "failed"
    PENDING_APPROVAL = "pending_approval"


class AgentError(BaseModel):
    """Error information for agent failures"""
    agent_name: str
    error_type: str  # 'api_failure', 'data_quality', 'rate_limit', 'validation_error'
    error_message: str
    details: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)
    retry_count: int = 0


class ProspectData(BaseModel):
    """Core prospect information"""
    id: Optional[int] = None
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    company_name: Optional[str] = None
    location: Optional[str] = None
    prospect_type: str  # 'individual' or 'company'
    source: str
    status: ProspectStatus = ProspectStatus.DISCOVERED
    lead_score: int = 0
    assigned_to: Optional[str] = None


class HunterResults(BaseModel):
    """Results from prospect hunter agent"""
    search_queries: List[str] = Field(default_factory=list)
    sources_searched: List[str] = Field(default_factory=list)
    prospects_found: int = 0
    confidence_score: float = 0.0
    event_signals: List[str] = Field(default_factory=list)
    social_media_posts: List[Dict[str, Any]] = Field(default_factory=list)
    search_metadata: Dict[str, Any] = Field(default_factory=dict)


class EnrichmentData(BaseModel):
    """Results from enrichment agent"""
    company_data: Dict[str, Any] = Field(default_factory=dict)
    social_profiles: Dict[str, str] = Field(default_factory=dict)
    event_preferences: Dict[str, Any] = Field(default_factory=dict)
    budget_signals: Dict[str, Any] = Field(default_factory=dict)
    contact_info: Dict[str, str] = Field(default_factory=dict)
    confidence_score: float = 0.0
    enrichment_sources: List[str] = Field(default_factory=list)
    last_enriched: datetime = Field(default_factory=datetime.now)


class OutreachCampaign(BaseModel):
    """Outreach campaign information"""
    id: Optional[int] = None
    channel: str  # 'email', 'linkedin', 'phone'
    campaign_type: str
    subject_line: Optional[str] = None
    message_body: str
    personalization_data: Dict[str, Any] = Field(default_factory=dict)
    status: CampaignStatus = CampaignStatus.DRAFT
    sent_at: Optional[datetime] = None
    opened_at: Optional[datetime] = None
    replied_at: Optional[datetime] = None


class ConversationSummary(BaseModel):
    """Summary of conversation with prospect"""
    id: Optional[int] = None
    channel: str
    message_count: int = 0
    last_message_at: Optional[datetime] = None
    extracted_requirements: Dict[str, Any] = Field(default_factory=dict)
    sentiment_score: float = 0.0  # -1.0 to 1.0
    qualification_score: int = 0  # 0-100
    next_action: Optional[str] = None
    conversation_summary: Optional[str] = None


class ProposalData(BaseModel):
    """Proposal generation data"""
    id: Optional[int] = None
    proposal_name: str
    total_price: float
    guest_count: int
    event_date: datetime
    event_type: EventType
    venue_details: Dict[str, Any] = Field(default_factory=dict)
    package_details: Dict[str, Any] = Field(default_factory=dict)
    proposal_pdf_url: Optional[str] = None
    mood_board_url: Optional[str] = None
    status: str = "draft"
    valid_until: datetime


class MeetingDetails(BaseModel):
    """Meeting scheduling details"""
    id: Optional[int] = None
    meeting_type: str
    title: str
    description: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    duration_minutes: int = 60
    location: Optional[str] = None
    meeting_url: Optional[str] = None
    calendar_event_id: Optional[str] = None
    attendees: List[Dict[str, str]] = Field(default_factory=list)
    status: str = "scheduled"


class RainmakerState(TypedDict, total=False):
    """
    Shared state for LangGraph workflow orchestration.
    
    This TypedDict defines all the data structures that flow between agents
    during the prospect-to-deal workflow execution.
    """
    # Workflow metadata
    workflow_id: str
    current_stage: WorkflowStage
    completed_stages: List[WorkflowStage]
    workflow_started_at: datetime
    last_updated_at: datetime
    
    # Core prospect data
    prospect_id: Optional[int]
    prospect_data: ProspectData
    
    # Agent results
    hunter_results: Optional[HunterResults]
    enrichment_data: Optional[EnrichmentData]
    outreach_campaigns: List[OutreachCampaign]
    conversation_summary: Optional[ConversationSummary]
    proposal_data: Optional[ProposalData]
    meeting_details: Optional[MeetingDetails]
    
    # Error handling and recovery
    errors: List[AgentError]
    retry_count: int
    max_retries: int
    human_intervention_needed: bool
    approval_pending: bool
    
    # Human oversight
    assigned_human: Optional[str]
    approval_requests: List[Dict[str, Any]]
    manual_overrides: Dict[str, Any]
    
    # Workflow control
    next_agent: Optional[str]
    skip_stages: List[WorkflowStage]
    priority: int  # 1-10, higher is more urgent
    
    # Performance tracking
    stage_durations: Dict[str, float]  # seconds spent in each stage
    total_duration: Optional[float]
    
    # External service tracking
    api_calls_made: Dict[str, int]  # track API usage per service
    rate_limit_status: Dict[str, Dict[str, Any]]


class StateValidationError(Exception):
    """Raised when state validation fails"""
    pass


class StateManager:
    """
    Utility class for managing RainmakerState operations including
    validation, serialization, and persistence.
    """
    
    @staticmethod
    def create_initial_state(
        prospect_data: ProspectData,
        workflow_id: Optional[str] = None,
        assigned_human: Optional[str] = None
    ) -> RainmakerState:
        """Create a new initial workflow state"""
        if workflow_id is None:
            workflow_id = str(uuid.uuid4())
            
        now = datetime.now()
        
        return RainmakerState(
            workflow_id=workflow_id,
            current_stage=WorkflowStage.HUNTING,
            completed_stages=[],
            workflow_started_at=now,
            last_updated_at=now,
            prospect_id=prospect_data.id,
            prospect_data=prospect_data,
            hunter_results=None,
            enrichment_data=None,
            outreach_campaigns=[],
            conversation_summary=None,
            proposal_data=None,
            meeting_details=None,
            errors=[],
            retry_count=0,
            max_retries=3,
            human_intervention_needed=False,
            approval_pending=False,
            assigned_human=assigned_human,
            approval_requests=[],
            manual_overrides={},
            next_agent=None,
            skip_stages=[],
            priority=5,
            stage_durations={},
            total_duration=None,
            api_calls_made={},
            rate_limit_status={}
        )
    
    @staticmethod
    def validate_state(state: RainmakerState) -> bool:
        """
        Validate state structure and data integrity.
        
        Args:
            state: The state to validate
            
        Returns:
            True if valid
            
        Raises:
            StateValidationError: If validation fails
        """
        try:
            # Check required fields
            required_fields = [
                'workflow_id', 'current_stage', 'completed_stages',
                'workflow_started_at', 'last_updated_at', 'prospect_data'
            ]
            
            for field in required_fields:
                if field not in state:
                    raise StateValidationError(f"Missing required field: {field}")
            
            # Validate workflow_id format
            try:
                uuid.UUID(state['workflow_id'])
            except ValueError:
                raise StateValidationError("Invalid workflow_id format")
            
            # Validate stage progression
            current_stage = state['current_stage']
            completed_stages = state['completed_stages']
            
            if current_stage in completed_stages:
                raise StateValidationError(
                    f"Current stage {current_stage} cannot be in completed stages"
                )
            
            # Validate prospect data
            if not isinstance(state['prospect_data'], (dict, ProspectData)):
                raise StateValidationError("prospect_data must be dict or ProspectData")
            
            # Validate error list
            if 'errors' in state and not isinstance(state['errors'], list):
                raise StateValidationError("errors must be a list")
            
            # Validate retry count
            if 'retry_count' in state and state['retry_count'] < 0:
                raise StateValidationError("retry_count cannot be negative")
            
            return True
            
        except Exception as e:
            if isinstance(e, StateValidationError):
                raise
            raise StateValidationError(f"State validation failed: {str(e)}")
    
    @staticmethod
    def serialize_state(state: RainmakerState) -> str:
        """
        Serialize state to JSON string for persistence.
        
        Args:
            state: The state to serialize
            
        Returns:
            JSON string representation
        """
        def json_serializer(obj):
            """Custom JSON serializer for datetime and Pydantic models"""
            if isinstance(obj, datetime):
                return obj.isoformat()
            elif isinstance(obj, BaseModel):
                return obj.dict()
            elif isinstance(obj, Enum):
                return obj.value
            elif hasattr(obj, '__dict__'):
                return obj.__dict__
            return str(obj)
        
        try:
            return json.dumps(dict(state), default=json_serializer, indent=2)
        except Exception as e:
            raise StateValidationError(f"Failed to serialize state: {str(e)}")
    
    @staticmethod
    def deserialize_state(json_str: str) -> RainmakerState:
        """
        Deserialize JSON string back to RainmakerState.
        
        Args:
            json_str: JSON string to deserialize
            
        Returns:
            RainmakerState object
        """
        try:
            data = json.loads(json_str)
            
            # Convert datetime strings back to datetime objects
            datetime_fields = [
                'workflow_started_at', 'last_updated_at'
            ]
            
            for field in datetime_fields:
                if field in data and isinstance(data[field], str):
                    data[field] = datetime.fromisoformat(data[field])
            
            # Convert nested datetime fields
            if 'enrichment_data' in data and data['enrichment_data']:
                if 'last_enriched' in data['enrichment_data']:
                    data['enrichment_data']['last_enriched'] = datetime.fromisoformat(
                        data['enrichment_data']['last_enriched']
                    )
            
            # Convert error timestamps
            if 'errors' in data:
                for error in data['errors']:
                    if 'timestamp' in error and isinstance(error['timestamp'], str):
                        error['timestamp'] = datetime.fromisoformat(error['timestamp'])
            
            # Convert enum strings back to enums
            if 'current_stage' in data:
                data['current_stage'] = WorkflowStage(data['current_stage'])
            
            if 'completed_stages' in data:
                data['completed_stages'] = [
                    WorkflowStage(stage) for stage in data['completed_stages']
                ]
            
            return RainmakerState(data)
            
        except Exception as e:
            raise StateValidationError(f"Failed to deserialize state: {str(e)}")
    
    @staticmethod
    def update_stage(
        state: RainmakerState,
        new_stage: WorkflowStage,
        track_duration: bool = True
    ) -> RainmakerState:
        """
        Update workflow stage and track timing.
        
        Args:
            state: Current state
            new_stage: New stage to transition to
            track_duration: Whether to track stage duration
            
        Returns:
            Updated state
        """
        now = datetime.now()
        
        # Track duration of previous stage
        if track_duration and 'current_stage' in state:
            current_stage = state['current_stage']
            if 'last_updated_at' in state:
                duration = (now - state['last_updated_at']).total_seconds()
                if 'stage_durations' not in state:
                    state['stage_durations'] = {}
                state['stage_durations'][current_stage.value] = duration
        
        # Move current stage to completed
        if 'current_stage' in state and state['current_stage'] not in state['completed_stages']:
            state['completed_stages'].append(state['current_stage'])
        
        # Update to new stage
        state['current_stage'] = new_stage
        state['last_updated_at'] = now
        
        return state
    
    @staticmethod
    def add_error(
        state: RainmakerState,
        agent_name: str,
        error_type: str,
        error_message: str,
        details: Optional[Dict[str, Any]] = None
    ) -> RainmakerState:
        """
        Add error to state and update retry count.
        
        Args:
            state: Current state
            agent_name: Name of agent that failed
            error_type: Type of error
            error_message: Error description
            details: Additional error details
            
        Returns:
            Updated state
        """
        error = AgentError(
            agent_name=agent_name,
            error_type=error_type,
            error_message=error_message,
            details=details or {},
            retry_count=state.get('retry_count', 0)
        )
        
        if 'errors' not in state:
            state['errors'] = []
        
        state['errors'].append(error)
        state['retry_count'] = state.get('retry_count', 0) + 1
        
        # Check if max retries exceeded
        max_retries = state.get('max_retries', 3)
        if state['retry_count'] >= max_retries:
            state['human_intervention_needed'] = True
            state['current_stage'] = WorkflowStage.FAILED
        
        return state
    
    @staticmethod
    def request_approval(
        state: RainmakerState,
        approval_type: str,
        data: Dict[str, Any],
        reason: str
    ) -> RainmakerState:
        """
        Request human approval and pause workflow.
        
        Args:
            state: Current state
            approval_type: Type of approval needed
            data: Data requiring approval
            reason: Reason for approval request
            
        Returns:
            Updated state
        """
        approval_request = {
            'id': str(uuid.uuid4()),
            'type': approval_type,
            'data': data,
            'reason': reason,
            'requested_at': datetime.now(),
            'status': 'pending'
        }
        
        if 'approval_requests' not in state:
            state['approval_requests'] = []
        
        state['approval_requests'].append(approval_request)
        state['approval_pending'] = True
        state['current_stage'] = WorkflowStage.PENDING_APPROVAL
        
        return state
    
    @staticmethod
    def calculate_progress(state: RainmakerState) -> float:
        """
        Calculate workflow progress as percentage.
        
        Args:
            state: Current state
            
        Returns:
            Progress percentage (0.0 to 100.0)
        """
        all_stages = [
            WorkflowStage.HUNTING,
            WorkflowStage.ENRICHING,
            WorkflowStage.OUTREACH,
            WorkflowStage.CONVERSATION,
            WorkflowStage.PROPOSAL,
            WorkflowStage.MEETING
        ]
        
        completed_count = len([
            stage for stage in state.get('completed_stages', [])
            if stage in all_stages
        ])
        
        # Add partial credit for current stage
        current_stage = state.get('current_stage')
        if current_stage in all_stages and current_stage not in state.get('completed_stages', []):
            completed_count += 0.5
        
        return min(100.0, (completed_count / len(all_stages)) * 100.0)
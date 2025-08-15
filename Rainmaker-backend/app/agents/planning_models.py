"""
Shared models for campaign planning and coordination
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum


class CampaignType(str, Enum):
    """Types of sales campaigns"""
    DISCOVERY_FOCUSED = "discovery_focused"      # Find new prospects
    NURTURING_FOCUSED = "nurturing_focused"     # Warm up existing leads
    CONVERSION_FOCUSED = "conversion_focused"   # Close qualified prospects
    HYBRID_CAMPAIGN = "hybrid_campaign"         # Multi-objective campaign


class PlanningPhase(str, Enum):
    """Phases of planning conversation"""
    INITIAL_ASSESSMENT = "initial_assessment"
    OBJECTIVE_SETTING = "objective_setting"
    TARGET_DEFINITION = "target_definition"
    STRATEGY_CREATION = "strategy_creation"
    EXECUTION_PLANNING = "execution_planning"
    APPROVAL_CONFIRMATION = "approval_confirmation"


@dataclass
class CampaignObjectives:
    """Campaign objectives and KPIs"""
    primary_goal: str  # "generate_leads", "increase_bookings", "expand_market"
    target_prospects: int = 50
    target_meetings: int = 10
    target_proposals: int = 5
    target_conversions: int = 2
    budget_range: Optional[tuple] = None
    timeline_days: int = 30
    geographic_focus: Optional[str] = None
    event_types_focus: List[str] = field(default_factory=list)
    priority_level: str = "medium"  # low/medium/high/urgent


@dataclass
class TargetProfile:
    """Target prospect profile definition"""
    prospect_types: List[str] = field(default_factory=list)  # individual, company
    event_types: List[str] = field(default_factory=list)
    budget_ranges: List[tuple] = field(default_factory=list)
    geographic_regions: List[str] = field(default_factory=list)
    company_sizes: List[str] = field(default_factory=list)  # startup, small, medium, enterprise
    decision_maker_titles: List[str] = field(default_factory=list)
    seasonal_preferences: List[str] = field(default_factory=list)
    exclusions: List[str] = field(default_factory=list)  # What to avoid


@dataclass
class ExecutionStrategy:
    """Comprehensive execution strategy"""
    campaign_type: CampaignType
    agent_sequence: List[str] = field(default_factory=list)
    parallel_agents: List[List[str]] = field(default_factory=list)
    conditional_routing: Dict[str, Any] = field(default_factory=dict)
    approval_gates: List[str] = field(default_factory=list)
    success_metrics: Dict[str, Any] = field(default_factory=dict)
    optimization_triggers: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CampaignPlan:
    """Complete campaign plan"""
    plan_id: str
    created_at: datetime
    user_id: str
    campaign_name: str
    objectives: CampaignObjectives
    target_profile: TargetProfile
    execution_strategy: ExecutionStrategy
    expected_timeline: Dict[str, str]
    resource_requirements: Dict[str, Any]
    risk_factors: List[str]
    success_predictions: Dict[str, float]
    plan_metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PlanningConversation:
    """Planning conversation state"""
    conversation_id: str
    user_id: str
    current_phase: PlanningPhase
    collected_info: Dict[str, Any] = field(default_factory=dict)
    conversation_history: List[Dict[str, str]] = field(default_factory=list)
    clarification_needed: List[str] = field(default_factory=list)
    suggested_responses: List[str] = field(default_factory=list)
    completion_percentage: float = 0.0
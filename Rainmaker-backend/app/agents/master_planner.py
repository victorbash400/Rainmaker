"""
Master Planning Agent - Facade for conversational planning and campaign coordination
"""

import structlog
from typing import Dict, Optional, Any

from .conversational_planner import ConversationalPlannerAgent
from .campaign_coordinator import CampaignCoordinatorAgent
from .planning_models import (
    CampaignPlan, PlanningConversation, PlanningPhase, CampaignType,
    CampaignObjectives, TargetProfile, ExecutionStrategy
)

logger = structlog.get_logger(__name__)


class MasterPlannerAgent:
    """
    Master Planning Agent that acts as a facade for:
    1. Conversational planning (collecting requirements, creating plans)
    2. Campaign coordination (executing plans, orchestrating agents)
    
    Maintains backward compatibility while providing cleaner architecture.
    """
    
    def __init__(self):
        self.conversational_planner = ConversationalPlannerAgent()
        self.campaign_coordinator = CampaignCoordinatorAgent()
        
        # Expose active conversations and campaigns for backward compatibility
        self.active_conversations = self.conversational_planner.active_conversations
        self.active_campaigns = self.campaign_coordinator.active_campaigns
        self.executing_campaigns = self.campaign_coordinator.executing_campaigns
        
    # =============================================================================
    # CONVERSATIONAL PLANNING INTERFACE (delegates to ConversationalPlannerAgent)
    # =============================================================================
    
    async def start_planning_conversation(self, user_id: str, 
                                        initial_context: Optional[Dict[str, Any]] = None) -> PlanningConversation:
        """Start a new planning conversation - delegates to conversational planner"""
        return await self.conversational_planner.start_planning_conversation(user_id, initial_context)
    
    async def process_user_response(self, conversation_id: str, user_message: str) -> Dict[str, Any]:
        """Process user response - delegates to conversational planner"""
        return await self.conversational_planner.process_user_response(conversation_id, user_message)
    
    # =============================================================================
    # CAMPAIGN EXECUTION COORDINATION (delegates to CampaignCoordinatorAgent)
    # =============================================================================
    
    async def execute_campaign_plan(self, plan_id: str) -> Dict[str, Any]:
        """Execute a campaign plan - delegates to campaign coordinator"""
        if plan_id not in self.active_campaigns:
            # Try to load plan from database
            plan = await self._load_campaign_plan_from_db(plan_id)
            if not plan:
                raise ValueError(f"Campaign plan {plan_id} not found")
            
            # Store in active campaigns for future reference
            self.active_campaigns[plan_id] = plan
        else:
            plan = self.active_campaigns[plan_id]
            
        return await self.campaign_coordinator.execute_campaign_plan(plan)
    
    async def _load_campaign_plan_from_db(self, plan_id: str):
        """Load campaign plan from database"""
        try:
            from app.mcp.database import database_mcp
            from .planning_models import CampaignPlan, CampaignObjectives, TargetProfile, ExecutionStrategy, CampaignType
            import json
            from datetime import datetime
            
            result = await database_mcp.call_tool(
                "execute_query",
                {
                    "query": "SELECT * FROM campaign_plans WHERE plan_id = ?",
                    "parameters": [plan_id],
                    "fetch_mode": "one"
                }
            )
            
            if result.isError:
                return None
                
            plan_data = json.loads(result.content[0].text).get("result")
            if not plan_data:
                return None
            
            # Reconstruct the campaign plan from database data
            objectives = CampaignObjectives(**json.loads(plan_data["objectives"]))
            target_profile = TargetProfile(**json.loads(plan_data["target_profile"]))
            
            execution_data = json.loads(plan_data["execution_strategy"])
            execution_data["campaign_type"] = CampaignType(execution_data["campaign_type"])
            execution_strategy = ExecutionStrategy(**execution_data)
            
            plan = CampaignPlan(
                plan_id=plan_data["plan_id"],
                created_at=datetime.fromisoformat(plan_data["created_at"]),
                user_id=plan_data["user_id"],
                campaign_name=plan_data["campaign_name"],
                objectives=objectives,
                target_profile=target_profile,
                execution_strategy=execution_strategy,
                expected_timeline={},
                resource_requirements={},
                risk_factors=[],
                success_predictions={},
                plan_metadata={}
            )
            
            return plan
            
        except Exception as e:
            logger.error("Failed to load campaign plan from database", error=str(e), plan_id=plan_id)
            return None
    
    def get_campaign_execution_status(self, plan_id: str) -> Dict[str, Any]:
        """Get campaign execution status - delegates to campaign coordinator"""
        return self.campaign_coordinator.get_campaign_execution_status(plan_id)

"""
Campaign Coordination Agent - Handles campaign execution and agent orchestration
"""

import json
import structlog
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
from dataclasses import asdict

from app.core.state import RainmakerState, ProspectData, WorkflowStage
from app.mcp.database import database_mcp
from .planning_models import CampaignPlan, CampaignType

logger = structlog.get_logger(__name__)

# Global callback for workflow status updates
workflow_status_callback: Optional[Callable] = None

def set_workflow_status_callback(callback: Callable):
    """Set callback function for workflow status updates"""
    global workflow_status_callback
    workflow_status_callback = callback


class CampaignCoordinatorAgent:
    """
    Coordinates campaign execution by orchestrating other agents.
    Handles agent sequencing, progress tracking, and error recovery.
    """
    
    def __init__(self):
        self.active_campaigns: Dict[str, CampaignPlan] = {}
        self.executing_campaigns: Dict[str, Dict[str, Any]] = {}
        self._last_broadcast_time: Dict[str, float] = {}  # Track last broadcast time per plan
    
    def _broadcast_status_update(self, plan_id: str, execution_state: Dict[str, Any], force: bool = False):
        """Broadcast workflow status update to connected clients with throttling"""
        if not workflow_status_callback:
            return
            
        import time
        current_time = time.time()
        
        # Throttle broadcasts to max once per 2 seconds unless forced
        if not force and plan_id in self._last_broadcast_time:
            if current_time - self._last_broadcast_time[plan_id] < 2.0:
                return
        
        try:
            status_data = {
                "status": execution_state.get("status", "unknown"),
                "current_phase": execution_state.get("current_phase", "unknown"),
                "progress_percentage": self._calculate_progress_percentage(execution_state),
                "metrics": execution_state.get("metrics", {}),
                "workflow_id": execution_state.get("workflow_id", f"campaign_{plan_id}")
            }
            workflow_status_callback(plan_id, status_data)
            self._last_broadcast_time[plan_id] = current_time
            logger.debug("Broadcasted workflow status update", plan_id=plan_id, status=status_data["status"])
        except Exception as e:
            logger.warning("Failed to broadcast workflow status update", error=str(e), plan_id=plan_id)
        
    # =============================================================================
    # CAMPAIGN EXECUTION COORDINATION
    # =============================================================================
    
    async def execute_campaign_plan(self, plan: CampaignPlan) -> Dict[str, Any]:
        """Execute a campaign plan by coordinating agents"""
        
        plan_id = plan.plan_id
        
        # Check if already executing
        if plan_id in self.executing_campaigns:
            current_status = self.executing_campaigns[plan_id]
            if current_status.get("status") == "executing":
                logger.warning("Campaign already executing", plan_id=plan_id)
                return current_status
        
        # Store plan for execution
        self.active_campaigns[plan_id] = plan
        
        logger.info("Starting campaign execution", plan_id=plan_id, campaign_name=plan.campaign_name)
        
        # Create execution state with workflow_id
        workflow_id = f"campaign_{plan.plan_id}_{datetime.now().timestamp()}"
        execution_state = {
            "plan_id": plan_id,
            "workflow_id": workflow_id,
            "campaign_plan": plan,
            "execution_started_at": datetime.now(),
            "current_phase": "initialization",
            "status": "executing",
            "completed_agents": [],
            "active_workflows": [],
            "metrics": {
                "prospects_discovered": 0,
                "outreach_sent": 0,
                "meetings_scheduled": 0,
                "proposals_generated": 0
            }
        }
        
        # Store execution state
        self.executing_campaigns[plan_id] = execution_state
        
        # Broadcast initial status
        self._broadcast_status_update(plan_id, execution_state, force=True)
        
        # Execute based on strategy type
        if plan.execution_strategy.campaign_type == CampaignType.DISCOVERY_FOCUSED:
            result = await self._execute_discovery_campaign(plan, execution_state)
        elif plan.execution_strategy.campaign_type == CampaignType.NURTURING_FOCUSED:
            result = await self._execute_nurturing_campaign(plan, execution_state)
        elif plan.execution_strategy.campaign_type == CampaignType.CONVERSION_FOCUSED:
            result = await self._execute_conversion_campaign(plan, execution_state)
        else:
            result = await self._execute_hybrid_campaign(plan, execution_state)
        
        return result
    
    def get_campaign_execution_status(self, plan_id: str) -> Dict[str, Any]:
        """Get real-time execution status for a campaign"""
        if plan_id in self.executing_campaigns:
            state = self.executing_campaigns[plan_id]
            return {
                "plan_id": plan_id,
                "workflow_id": state.get("workflow_id", f"campaign_{plan_id}_{datetime.now().timestamp()}"),
                "status": state.get("status", "ready"),
                "current_phase": state.get("current_phase", "planning_complete"),
                "progress_percentage": self._calculate_progress_percentage(state),
                "metrics": state.get("metrics", {
                    "prospects_discovered": 0,
                    "outreach_sent": 0,
                    "meetings_scheduled": 0,
                    "proposals_generated": 0
                }),
                "last_updated": state.get("last_updated", datetime.now()).isoformat(),
                "active_agent": state.get("active_agent", "none")
            }
        elif plan_id in self.active_campaigns:
            return {
                "plan_id": plan_id,
                "workflow_id": f"campaign_{plan_id}_{datetime.now().timestamp()}",
                "status": "ready_to_execute",
                "current_phase": "planning_complete",
                "progress_percentage": 0,
                "metrics": {
                    "prospects_discovered": 0,
                    "outreach_sent": 0,
                    "meetings_scheduled": 0,
                    "proposals_generated": 0
                },
                "last_updated": datetime.now().isoformat(),
                "active_agent": "none"
            }
        else:
            raise ValueError("Campaign not found")
    
    # =============================================================================
    # CAMPAIGN EXECUTION STRATEGIES
    # =============================================================================
    
    async def _execute_discovery_campaign(self, plan: CampaignPlan, 
                                        execution_state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute discovery-focused campaign"""
        
        logger.info("🔍 Importing prospect hunter agent", plan_id=plan.plan_id)
        try:
            from app.agents.prospect_hunter import ProspectHunterAgent
            logger.info("✅ Prospect hunter imported successfully")
        except Exception as e:
            logger.error("❌ Failed to import prospect hunter", error=str(e))
            raise
            
        logger.info("📊 Importing enrichment agent", plan_id=plan.plan_id)
        try:
            from app.agents.enrichment import EnrichmentAgent
            logger.info("✅ Enrichment agent imported successfully")
        except Exception as e:
            logger.error("❌ Failed to import enrichment agent", error=str(e))
            raise
            
        logger.info("📧 Importing outreach agent", plan_id=plan.plan_id)  
        try:
            from app.agents.outreach import OutreachAgent
            logger.info("✅ Outreach agent imported successfully")
        except Exception as e:
            logger.error("❌ Failed to import outreach agent", error=str(e))
            raise
        
        hunter_agent = ProspectHunterAgent()
        enrichment_agent = EnrichmentAgent()
        outreach_agent = OutreachAgent()
        
        # Create initial state for prospect hunting
        initial_state: RainmakerState = {
            "workflow_id": execution_state["workflow_id"],
            "current_stage": WorkflowStage.HUNTING,
            "completed_stages": [],
            "workflow_started_at": datetime.now(),
            "last_updated_at": datetime.now(),
            "prospect_id": None,
            "prospect_data": ProspectData(
                name="Campaign Target",
                prospect_type="campaign",
                source="master_planner"
            ),
            "hunter_results": None,
            "enrichment_data": None,
            "outreach_campaigns": [],
            "conversation_summary": None,
            "proposal_data": None,
            "meeting_details": None,
            "errors": [],
            "retry_count": 0,
            "max_retries": 3,
            "human_intervention_needed": False,
            "approval_pending": False,
            "assigned_human": None,
            # Custom fields for campaign execution
            "campaign_plan": plan,
            "target_prospects": plan.objectives.target_prospects,
            "event_types_focus": plan.target_profile.event_types,
            "geographic_focus": plan.target_profile.geographic_regions
        }
        
        try:
            # Phase 1: Prospect Discovery
            execution_state["current_phase"] = "discovery"
            execution_state["active_agent"] = "prospect_hunter"
            execution_state["last_updated"] = datetime.now()
            self._broadcast_status_update(plan.plan_id, execution_state, force=True)
            
            hunter_state = await hunter_agent.hunt_prospects(initial_state)
            
            execution_state["completed_agents"].append("hunter")
            execution_state["active_agent"] = "none"
            execution_state["last_updated"] = datetime.now()
            
            # Get prospects found count from hunter results
            hunter_results = hunter_state.get("hunter_results")
            prospects_found = hunter_results.prospects_found if hunter_results else 0
            execution_state["metrics"]["prospects_discovered"] = prospects_found
            self._broadcast_status_update(plan.plan_id, execution_state)
            
            # Phase 2: Enrichment for discovered prospects
            discovered_ids = hunter_state.get("discovered_prospect_ids", [])
            if discovered_ids:
                execution_state["current_phase"] = "enrichment"
                self._broadcast_status_update(plan.plan_id, execution_state)
                
                for prospect_id in discovered_ids[:10]:  # Process top 10
                    # Get prospect data from database
                    prospect_data = await self._get_prospect_by_id(prospect_id)
                    if prospect_data:
                        enrichment_state = initial_state.copy()
                        enrichment_state["prospect_data"] = prospect_data
                        
                        enriched_state = await enrichment_agent.enrich_prospect(enrichment_state)
                        execution_state["completed_agents"].append(f"enricher_{prospect_id}")
            
            # Phase 3: Outreach to enriched prospects (if enabled in plan)
            if not plan.execution_strategy.approval_gates or "outreach" not in plan.execution_strategy.approval_gates:
                execution_state["current_phase"] = "outreach"
                self._broadcast_status_update(plan.plan_id, execution_state)
                
                for prospect_id in discovered_ids[:5]:  # Outreach to top 5
                    prospect_data = await self._get_prospect_by_id(prospect_id)
                    if prospect_data:
                        outreach_state = initial_state.copy()
                        outreach_state["prospect_data"] = prospect_data
                        
                        # Get enrichment data if available
                        enrichment_data = await self._get_enrichment_data(prospect_id)
                        if enrichment_data:
                            outreach_state["enrichment_data"] = enrichment_data
                        
                        outreach_result = await outreach_agent.execute_outreach(outreach_state)
                        execution_state["completed_agents"].append(f"outreach_{prospect_id}")
                        execution_state["metrics"]["outreach_sent"] += 1
                        self._broadcast_status_update(plan.plan_id, execution_state)
            
            execution_state["current_phase"] = "completed"
            execution_state["status"] = "completed"
            execution_state["execution_completed_at"] = datetime.now()
            self._broadcast_status_update(plan.plan_id, execution_state, force=True)
            
            return {
                "status": "success",
                "execution_state": execution_state,
                "summary": self._generate_execution_summary(execution_state),
                "next_steps": self._suggest_next_steps(plan, execution_state)
            }
            
        except Exception as e:
            logger.error("Discovery campaign execution failed", error=str(e), plan_id=plan.plan_id)
            execution_state["current_phase"] = "failed"
            execution_state["status"] = "error"
            execution_state["error"] = str(e)
            self._broadcast_status_update(plan.plan_id, execution_state)
            return {
                "status": "error",
                "error": str(e),
                "execution_state": execution_state
            }
    
    async def _execute_nurturing_campaign(self, plan: CampaignPlan, 
                                        execution_state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute nurturing-focused campaign for existing prospects"""
        
        execution_state["current_phase"] = "nurturing_in_progress"
        
        return {
            "status": "success",
            "execution_state": execution_state,
            "message": "Nurturing campaign strategy prepared - ready for implementation"
        }
    
    async def _execute_conversion_campaign(self, plan: CampaignPlan, 
                                         execution_state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute conversion-focused campaign for qualified prospects"""
        
        execution_state["current_phase"] = "conversion_in_progress"
        
        return {
            "status": "success", 
            "execution_state": execution_state,
            "message": "Conversion campaign strategy prepared - ready for implementation"
        }
    
    async def _execute_hybrid_campaign(self, plan: CampaignPlan, 
                                     execution_state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute hybrid campaign with multiple objectives"""
        
        execution_state["current_phase"] = "hybrid_in_progress"
        
        return {
            "status": "success",
            "execution_state": execution_state,
            "message": "Hybrid campaign strategy prepared - ready for multi-phase implementation"
        }
    
    # =============================================================================
    # HELPER METHODS
    # =============================================================================
    
    async def _get_prospect_by_id(self, prospect_id: int) -> Optional[ProspectData]:
        """Get prospect data by ID"""
        try:
            result = await database_mcp.call_tool(
                "execute_query",
                {
                    "query": "SELECT * FROM prospects WHERE id = ?",
                    "parameters": [prospect_id],
                    "fetch_mode": "one"
                }
            )
            
            if not result.isError:
                data = json.loads(result.content[0].text)
                prospect_row = data.get("result")
                if prospect_row:
                    return ProspectData(**prospect_row)
                    
        except Exception as e:
            logger.warning("Failed to get prospect by ID", error=str(e))
        
        return None
    
    async def _get_enrichment_data(self, prospect_id: int) -> Optional[Dict[str, Any]]:
        """Get enrichment data for prospect"""
        # Would query enrichment data from database
        # Placeholder implementation
        return None
    
    def _calculate_progress_percentage(self, execution_state: Dict[str, Any]) -> float:
        """Calculate progress percentage based on execution state"""
        phase = execution_state.get("current_phase", "initialization")
        phase_progress = {
            "initialization": 0.1,
            "discovery": 0.3,
            "enrichment": 0.5,
            "outreach": 0.7,
            "conversation": 0.9,
            "completed": 1.0,
            "failed": 0.0
        }
        return phase_progress.get(phase, 0.0)
    
    def _generate_execution_summary(self, execution_state: Dict[str, Any]) -> Dict[str, Any]:
        """Generate summary of campaign execution"""
        return {
            "phase_completed": execution_state["current_phase"],
            "agents_executed": len(execution_state["completed_agents"]),
            "prospects_discovered": execution_state["metrics"]["prospects_discovered"],
            "outreach_sent": execution_state["metrics"]["outreach_sent"],
            "duration_minutes": int((datetime.now() - execution_state["execution_started_at"]).total_seconds() / 60)
        }
    
    def _suggest_next_steps(self, plan: CampaignPlan, execution_state: Dict[str, Any]) -> List[str]:
        """Suggest next steps based on execution results"""
        steps = []
        
        if execution_state["metrics"]["prospects_discovered"] > 0:
            steps.append("Review discovered prospects for quality and relevance")
        
        if execution_state["metrics"]["outreach_sent"] > 0:
            steps.append("Monitor outreach response rates over next 3-5 days")
            steps.append("Prepare follow-up sequences for non-responders")
        
        steps.append("Analyze campaign performance metrics")
        steps.append("Optimize targeting based on initial results")
        
        return steps
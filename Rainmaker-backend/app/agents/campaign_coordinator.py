"""
Campaign Coordination Agent - Handles campaign execution and agent orchestration
"""

import json
import structlog
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
from dataclasses import asdict

from app.core.state import RainmakerState, ProspectData, WorkflowStage, StateManager
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
            logger.info("🔄 Broadcasting workflow status", 
                        plan_id=plan_id, 
                        status=status_data["status"],
                        current_phase=status_data["current_phase"],
                        workflow_id=status_data["workflow_id"])
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
                "prospects_enriched": 0,
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
                    "prospects_enriched": 0, 
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
                    "prospects_enriched": 0,
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
            "approval_requests": [],
            "manual_overrides": {},
            "next_agent": None,
            "skip_stages": [],
            "priority": 5,
            "stage_durations": {},
            "total_duration": None,
            "api_calls_made": {},
            "rate_limit_status": {}
        }
        
        # Store campaign-specific data separately in execution_state (not in workflow state)
        execution_state["campaign_context"] = {
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
            
            # Close any browser viewers before starting enrichment
            try:
                from app.api.v1.browser_viewer import cleanup_workflow_connections
                workflow_id = execution_state.get("workflow_id")
                if workflow_id:
                    cleanup_workflow_connections(workflow_id)
                    logger.info("🔧 Browser viewer connections cleaned up before enrichment")
                else:
                    logger.warning("No workflow_id found in execution state")
            except Exception as e:
                logger.warning("Failed to cleanup browser viewer connections", error=str(e))
            
            # Phase 2: Enrichment - ALWAYS run enrichment (demo mode)
            execution_state["current_phase"] = "enriching"
            execution_state["active_agent"] = "enrichment"
            
            logger.info("🧠 Broadcasting enriching phase to frontend", 
                       current_phase=execution_state["current_phase"],
                       plan_id=plan.plan_id)
            self._broadcast_status_update(plan.plan_id, execution_state, force=True)
            
            logger.info("🧠 Starting enrichment phase (demo mode)")
            
            discovered_ids = hunter_state.get("discovered_prospect_ids", [])
            enriched_count = 0
            
            if discovered_ids:
                # Process discovered prospects
                for prospect_id in discovered_ids[:10]:  # Process top 10
                    # Get prospect data from database
                    prospect_data = await self._get_prospect_by_id(prospect_id)
                    if prospect_data:
                        # Create enrichment state with hunter results passed through
                        enrichment_state = hunter_state.copy()  # Pass hunter results to enrichment
                        enrichment_state["prospect_data"] = prospect_data
                        enrichment_state["current_stage"] = WorkflowStage.ENRICHING
                        
                        logger.info(
                            "🧠 Starting enrichment for discovered prospect",
                            prospect_name=prospect_data.name,
                            prospect_id=prospect_id,
                            workflow_id=enrichment_state["workflow_id"]
                        )
                        
                        enriched_state = await enrichment_agent.enrich_prospect(enrichment_state)
                        
                        if enriched_state.get("enrichment_data"):
                            enriched_count += 1
                            logger.info(
                                "✅ Enrichment completed successfully",
                                prospect_name=prospect_data.name
                            )
                        else:
                            logger.warning(
                                "⚠️ Enrichment failed for prospect",
                                prospect_name=prospect_data.name,
                                errors=enriched_state.get("errors", [])
                            )
                        
                        execution_state["completed_agents"].append(f"enricher_{prospect_id}")
            else:
                # No prospects found - run demo enrichment anyway
                logger.info("🧠 No prospects found, running demo enrichment to test the flow")
                
                # Create demo prospect data with real person
                import os
                test_email = os.getenv("TEST_RECIPIENT_EMAIL", "steve@wittgoff.com")
                demo_prospect = ProspectData(
                    name="Steve Wittgoff",
                    email=test_email,  # Use test email for demo
                    company_name="Wittgoff Real Estate",
                    location="Chicago, IL",
                    prospect_type="individual",
                    source="demo_enrichment"
                )
                
                # Create enrichment state with demo data
                enrichment_state = hunter_state.copy()
                enrichment_state["prospect_data"] = demo_prospect
                enrichment_state["current_stage"] = WorkflowStage.ENRICHING
                
                logger.info(
                    "🧠 Starting demo enrichment",
                    prospect_name=demo_prospect.name,
                    workflow_id=enrichment_state["workflow_id"]
                )
                
                enriched_state = await enrichment_agent.enrich_prospect(enrichment_state)
                
                if enriched_state.get("enrichment_data"):
                    enriched_count = 1
                    # Store enriched prospect for outreach phase
                    execution_state["enriched_prospects"] = [demo_prospect]
                    enrichment_key = str(demo_prospect.id or "demo")
                    execution_state["enrichment_results"] = {
                        enrichment_key: enriched_state["enrichment_data"]
                    }
                    logger.info("✅ Demo enrichment completed successfully", 
                              enrichment_key=enrichment_key,
                              has_enrichment_data=bool(enriched_state.get("enrichment_data")))
                else:
                    logger.warning("⚠️ Demo enrichment failed")
                
                execution_state["completed_agents"].append("enricher_demo")
            
            execution_state["metrics"]["prospects_enriched"] = enriched_count
            execution_state["active_agent"] = "none"
            
            # Keep enriching phase active for a moment so frontend can connect
            execution_state["metrics"]["prospects_enriched"] = enriched_count
            execution_state["active_agent"] = "none"
            
            # Keep broadcasting enriching phase while enrichment is active
            # DON'T broadcast intermediate status - let enrichment complete first
            logger.info("🧠 Enrichment still active - NOT broadcasting intermediate status")
            
            logger.info(
                "📊 Enrichment phase completed",
                prospects_processed=max(len(discovered_ids[:10]), 1),
                successfully_enriched=enriched_count
            )
            
            # Continue to outreach phase after enrichment
            execution_state["current_phase"] = "outreach"
            execution_state["status"] = "executing"
            self._broadcast_status_update(plan.plan_id, execution_state, force=True)
            
            # Execute outreach phase
            await self._execute_outreach_phase(plan, execution_state)
            
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
    
    async def _execute_outreach_phase(self, plan: CampaignPlan, execution_state: Dict[str, Any]):
        """Execute outreach phase using the workflow orchestrator"""
        try:
            logger.info("🚀 Starting outreach phase", plan_id=plan.plan_id)
            
            # Get the first enriched prospect for outreach
            enriched_prospects = execution_state.get("enriched_prospects", [])
            if not enriched_prospects:
                logger.warning("No enriched prospects available for outreach")
                execution_state["current_phase"] = "completed"
                execution_state["status"] = "completed"
                execution_state["execution_completed_at"] = datetime.now()
                self._broadcast_status_update(plan.plan_id, execution_state, force=True)
                return
            
            # Use the workflow orchestrator for outreach
            from app.services.workflow import rainmaker_workflow
            from app.core.state import StateManager
            
            # Create initial state for outreach workflow
            prospect_data = enriched_prospects[0]  # Use first prospect
            initial_state = StateManager.create_initial_state(
                prospect_data=prospect_data,
                workflow_id=execution_state["workflow_id"]
            )
            
            # Add enrichment data if available
            enrichment_data = execution_state.get("enrichment_results", {}).get(str(prospect_data.id or "demo"))
            if enrichment_data:
                initial_state["enrichment_data"] = enrichment_data
                logger.info("✅ Added enrichment data to outreach state", workflow_id=initial_state["workflow_id"])
            else:
                logger.warning("⚠️ No enrichment data found for outreach", 
                             available_keys=list(execution_state.get("enrichment_results", {}).keys()),
                             prospect_id=str(prospect_data.id or "demo"))
            
            # Execute outreach workflow (this will pause at AWAITING_REPLY)
            logger.info("🔄 Executing outreach workflow", workflow_id=initial_state["workflow_id"])
            final_state = await rainmaker_workflow._outreach_node(initial_state)
            
            # Check if workflow paused at AWAITING_REPLY
            if final_state.get("current_stage") == "awaiting_reply":
                logger.info("📧 Outreach sent - workflow paused for reply", workflow_id=initial_state["workflow_id"])
                execution_state["current_phase"] = "awaiting_reply"
                execution_state["outreach_sent"] = True
                execution_state["metrics"]["outreach_sent"] = 1
                self._broadcast_status_update(plan.plan_id, execution_state, force=True)
            else:
                logger.warning("Outreach workflow did not pause as expected")
                execution_state["current_phase"] = "completed"
                execution_state["status"] = "completed"
                execution_state["execution_completed_at"] = datetime.now()
                self._broadcast_status_update(plan.plan_id, execution_state, force=True)
                
        except Exception as e:
            logger.error("Failed to execute outreach phase", error=str(e), plan_id=plan.plan_id)
            execution_state["current_phase"] = "failed"
            execution_state["status"] = "failed"
            execution_state["error"] = str(e)
            self._broadcast_status_update(plan.plan_id, execution_state, force=True)

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
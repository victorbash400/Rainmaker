"""
LangGraph workflow definition with conditional routing for Rainmaker agent orchestration.

This module implements the main workflow that orchestrates all agents using the existing 
MCP servers for external service integrations.
"""

import asyncio
import json
from typing import Dict, List, Any, Optional, Callable, Literal
from datetime import datetime, timedelta
from enum import Enum

import structlog
from langgraph.graph import StateGraph, Graph
from langgraph.prebuilt import ToolNode
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.tools import BaseTool

from app.core.state import (
    RainmakerState, StateManager, WorkflowStage, AgentError,
    ProspectData, HunterResults, EnrichmentData, OutreachCampaign,
    ConversationSummary, ProposalData, MeetingDetails
)
from app.core.config import settings
from app.services.openai_service import OpenAIService
from app.mcp.web_search import web_search_mcp
from app.mcp.enrichment import enrichment_mcp
from app.mcp.email import email_mcp
from app.mcp.enhanced_playwright_mcp import enhanced_browser_mcp
from app.mcp.proposal import proposal_mcp
from app.mcp.calendar import calendar_mcp
from app.mcp.database import database_mcp
from app.db.models import ProspectStatus, CampaignStatus

logger = structlog.get_logger(__name__)


class WorkflowDecision(str, Enum):
    """Workflow routing decisions"""
    CONTINUE = "continue"
    RETRY = "retry"
    SKIP = "skip"
    APPROVE = "approve"
    ESCALATE = "escalate"
    COMPLETE = "complete"


class RainmakerWorkflow:
    """
    LangGraph workflow orchestrator for the Rainmaker agent system.
    
    This class implements the main workflow that routes between different agents
    and handles error recovery, human approval, and state persistence.
    """
    
    def __init__(self):
        self.openai_service = OpenAIService()
        self.llm = ChatOpenAI(
            model="gpt-4",
            temperature=0.1,
            openai_api_key=settings.OPENAI_API_KEY.get_secret_value() if settings.OPENAI_API_KEY else None
        )
        
        # Create the workflow graph
        self.workflow = self._create_workflow()
        self.app = self.workflow.compile()
        
        logger.info("RainmakerWorkflow initialized")
    
    def _create_workflow(self) -> StateGraph:
        """Create the LangGraph workflow definition"""
        
        # Create the state graph
        workflow = StateGraph(RainmakerState)
        
        # Add nodes for each agent
        workflow.add_node("hunter", self._prospect_hunter_node)
        workflow.add_node("enricher", self._enrichment_node)  
        workflow.add_node("outreach", self._outreach_node)
        workflow.add_node("conversation", self._conversation_node)
        workflow.add_node("proposal", self._proposal_node)
        workflow.add_node("meeting", self._meeting_node)
        
        # Add special nodes
        workflow.add_node("approval", self._approval_node)
        workflow.add_node("error_handler", self._error_handler_node)
        workflow.add_node("human_escalation", self._human_escalation_node)
        workflow.add_node("workflow_complete", self._workflow_complete_node)
        
        # Set entry point
        workflow.set_entry_point("hunter")
        
        # Add conditional routing
        workflow.add_conditional_edges(
            "hunter",
            self._route_from_hunter,
            {
                "enricher": "enricher",
                "error_handler": "error_handler",
                "approval": "approval",
                "escalate": "human_escalation"
            }
        )
        
        workflow.add_conditional_edges(
            "enricher", 
            self._route_from_enricher,
            {
                "outreach": "outreach",
                "error_handler": "error_handler", 
                "approval": "approval",
                "escalate": "human_escalation"
            }
        )
        
        workflow.add_conditional_edges(
            "outreach",
            self._route_from_outreach,
            {
                "conversation": "conversation",
                "error_handler": "error_handler",
                "approval": "approval", 
                "escalate": "human_escalation"
            }
        )
        
        workflow.add_conditional_edges(
            "conversation",
            self._route_from_conversation,
            {
                "proposal": "proposal",
                "outreach": "outreach",  # Loop back for follow-ups
                "error_handler": "error_handler",
                "approval": "approval",
                "escalate": "human_escalation"
            }
        )
        
        workflow.add_conditional_edges(
            "proposal",
            self._route_from_proposal, 
            {
                "meeting": "meeting",
                "conversation": "conversation",  # Loop back for revisions
                "error_handler": "error_handler",
                "approval": "approval",
                "escalate": "human_escalation"
            }
        )
        
        workflow.add_conditional_edges(
            "meeting",
            self._route_from_meeting,
            {
                "workflow_complete": "workflow_complete",
                "conversation": "conversation",  # Loop back if needed
                "error_handler": "error_handler", 
                "approval": "approval",
                "escalate": "human_escalation"
            }
        )
        
        # Handle special node routing
        workflow.add_conditional_edges(
            "approval",
            self._route_from_approval,
            {
                "hunter": "hunter",
                "enricher": "enricher", 
                "outreach": "outreach",
                "conversation": "conversation",
                "proposal": "proposal",
                "meeting": "meeting",
                "human_escalation": "human_escalation"
            }
        )
        
        workflow.add_conditional_edges(
            "error_handler",
            self._route_from_error_handler,
            {
                "hunter": "hunter",
                "enricher": "enricher",
                "outreach": "outreach", 
                "conversation": "conversation",
                "proposal": "proposal",
                "meeting": "meeting",
                "human_escalation": "human_escalation",
                "workflow_complete": "workflow_complete"
            }
        )
        
        workflow.add_edge("human_escalation", "workflow_complete")
        workflow.add_finish_edge("workflow_complete")
        
        return workflow
    
    async def _prospect_hunter_node(self, state: RainmakerState) -> RainmakerState:
        """Hunter agent node - discover prospects using web search"""
        logger.info("Starting prospect hunter", workflow_id=state["workflow_id"])
        
        try:
            # Update stage
            state = StateManager.update_stage(state, WorkflowStage.HUNTING)
            
            # Get search parameters from prospect data
            prospect_data = state["prospect_data"]
            search_params = {
                "event_type": getattr(prospect_data, 'event_type', 'all'),
                "location": getattr(prospect_data, 'location', None), 
                "max_results": 50
            }
            
            # Use web search MCP to find prospects
            search_result = await web_search_mcp.server.call_tool(
                "search_prospects", 
                search_params
            )
            
            if search_result.isError:
                raise Exception(f"Web search failed: {search_result.content[0].text}")
            
            # Parse results
            search_data = json.loads(search_result.content[0].text)
            prospects = search_data.get("prospects", [])
            
            # Create hunter results
            hunter_results = HunterResults(
                search_queries=[search_data.get("search_query", "")],
                sources_searched=["web_search"],
                prospects_found=len(prospects),
                confidence_score=sum(p.get("confidence_score", 0) for p in prospects) / max(len(prospects), 1),
                event_signals=[p.get("raw_text", "") for p in prospects[:10]]
            )
            
            state["hunter_results"] = hunter_results
            
            # Store prospects in database via MCP
            for prospect in prospects[:10]:  # Limit to top prospects
                await database_mcp.server.call_tool("create_prospect", {
                    "name": prospect.get("prospect_name", "Unknown"),
                    "email": prospect.get("contact_info", {}).get("email"),
                    "company_name": prospect.get("company_name"),
                    "location": prospect.get("location"),
                    "prospect_type": "individual",
                    "source": "web_search",
                    "status": ProspectStatus.DISCOVERED.value,
                    "lead_score": int(prospect.get("confidence_score", 0) * 100)
                })
            
            logger.info(
                "Prospect hunting completed",
                workflow_id=state["workflow_id"],
                prospects_found=len(prospects)
            )
            
            return state
            
        except Exception as e:
            logger.error("Prospect hunter failed", error=str(e), workflow_id=state["workflow_id"])
            return StateManager.add_error(
                state, "prospect_hunter", "api_failure", str(e)
            )
    
    async def _enrichment_node(self, state: RainmakerState) -> RainmakerState:
        """Enrichment agent node - enrich prospect data"""
        logger.info("Starting prospect enrichment", workflow_id=state["workflow_id"])
        
        try:
            state = StateManager.update_stage(state, WorkflowStage.ENRICHING)
            
            prospect_data = state["prospect_data"]
            
            # Use enrichment MCP to get detailed prospect data
            enrichment_result = await enrichment_mcp.server.call_tool(
                "enrich_prospect",
                {
                    "name": prospect_data.name,
                    "email": prospect_data.email,
                    "company_name": prospect_data.company_name
                }
            )
            
            if enrichment_result.isError:
                raise Exception(f"Enrichment failed: {enrichment_result.content[0].text}")
            
            enrichment_data = json.loads(enrichment_result.content[0].text)
            
            # Create enrichment data object
            enrichment = EnrichmentData(
                company_data=enrichment_data.get("company_data", {}),
                social_profiles=enrichment_data.get("social_profiles", {}),
                event_preferences=enrichment_data.get("event_preferences", {}),
                budget_signals=enrichment_data.get("budget_signals", {}),
                contact_info=enrichment_data.get("contact_info", {}),
                confidence_score=enrichment_data.get("confidence_score", 0.0),
                enrichment_sources=enrichment_data.get("sources", [])
            )
            
            state["enrichment_data"] = enrichment
            
            # Update prospect in database
            if prospect_data.id:
                await database_mcp.server.call_tool("update_prospect", {
                    "prospect_id": prospect_data.id,
                    "enrichment_data": enrichment_data,
                    "status": ProspectStatus.ENRICHED.value
                })
            
            logger.info(
                "Prospect enrichment completed",
                workflow_id=state["workflow_id"],
                confidence_score=enrichment.confidence_score
            )
            
            return state
            
        except Exception as e:
            logger.error("Enrichment failed", error=str(e), workflow_id=state["workflow_id"])
            return StateManager.add_error(
                state, "enricher", "api_failure", str(e)
            )
    
    async def _outreach_node(self, state: RainmakerState) -> RainmakerState:
        """Outreach agent node - create and send personalized outreach"""
        logger.info("Starting outreach campaign", workflow_id=state["workflow_id"])
        
        try:
            state = StateManager.update_stage(state, WorkflowStage.OUTREACH)
            
            prospect_data = state["prospect_data"]
            enrichment_data = state.get("enrichment_data")
            
            # Determine outreach channel based on available contact info
            channel = "email" if prospect_data.email else "linkedin"
            
            # Create personalized message using enrichment data
            message_params = {
                "prospect_name": prospect_data.name,
                "prospect_email": prospect_data.email,
                "company_name": prospect_data.company_name,
                "event_type": getattr(prospect_data, 'event_type', 'event'),
                "enrichment_data": enrichment_data.dict() if enrichment_data else {}
            }
            
            if channel == "email":
                # Use email MCP to send personalized email
                email_result = await email_mcp.server.call_tool(
                    "send_personalized_email",
                    message_params
                )
                
                if email_result.isError:
                    raise Exception(f"Email outreach failed: {email_result.content[0].text}")
                
                email_data = json.loads(email_result.content[0].text)
                
            else:
                # Use enhanced browser MCP for LinkedIn outreach (placeholder)
                # TODO: Implement LinkedIn messaging through enhanced navigation
                email_data = {
                    "subject": f"Event Planning Opportunity - {prospect_data.name}",
                    "message": message_params.get("message", "LinkedIn outreach message"),
                    "status": "scheduled"  # For now, just schedule instead of sending
                }
            
            # Create outreach campaign record
            campaign = OutreachCampaign(
                channel=channel,
                campaign_type="initial_outreach",
                subject_line=email_data.get("subject"),
                message_body=email_data.get("message"),
                personalization_data=message_params,
                status=CampaignStatus.SENT,
                sent_at=datetime.now()
            )
            
            # Add to state
            if "outreach_campaigns" not in state:
                state["outreach_campaigns"] = []
            state["outreach_campaigns"].append(campaign)
            
            # Update prospect status
            if prospect_data.id:
                await database_mcp.server.call_tool("update_prospect", {
                    "prospect_id": prospect_data.id,
                    "status": ProspectStatus.CONTACTED.value
                })
            
            logger.info(
                "Outreach campaign completed", 
                workflow_id=state["workflow_id"],
                channel=channel
            )
            
            return state
            
        except Exception as e:
            logger.error("Outreach failed", error=str(e), workflow_id=state["workflow_id"])
            return StateManager.add_error(
                state, "outreach", "api_failure", str(e)
            )
    
    async def _conversation_node(self, state: RainmakerState) -> RainmakerState:
        """Conversation agent node - handle prospect conversations"""
        logger.info("Starting conversation handling", workflow_id=state["workflow_id"])
        
        try:
            state = StateManager.update_stage(state, WorkflowStage.CONVERSATION)
            
            # For now, simulate conversation handling
            # In a real implementation, this would process incoming messages
            conversation_summary = ConversationSummary(
                channel="email",
                message_count=1,
                last_message_at=datetime.now(),
                extracted_requirements={
                    "event_type": "wedding",
                    "guest_count": 100,
                    "budget_range": "10000-15000",
                    "event_date": (datetime.now() + timedelta(days=180)).isoformat()
                },
                sentiment_score=0.7,
                qualification_score=80,
                next_action="send_proposal",
                conversation_summary="Prospect is interested and provided initial requirements"
            )
            
            state["conversation_summary"] = conversation_summary
            
            logger.info(
                "Conversation handling completed",
                workflow_id=state["workflow_id"],
                qualification_score=conversation_summary.qualification_score
            )
            
            return state
            
        except Exception as e:
            logger.error("Conversation handling failed", error=str(e), workflow_id=state["workflow_id"])
            return StateManager.add_error(
                state, "conversation", "processing_error", str(e)
            )
    
    async def _proposal_node(self, state: RainmakerState) -> RainmakerState:
        """Proposal agent node - generate and send proposals"""
        logger.info("Starting proposal generation", workflow_id=state["workflow_id"])
        
        try:
            state = StateManager.update_stage(state, WorkflowStage.PROPOSAL)
            
            conversation = state.get("conversation_summary")
            if not conversation:
                raise Exception("No conversation data available for proposal")
            
            requirements = conversation.extracted_requirements
            
            # Use proposal MCP to generate proposal
            proposal_params = {
                "prospect_name": state["prospect_data"].name,
                "event_type": requirements.get("event_type", "event"),
                "guest_count": requirements.get("guest_count", 50),
                "budget_range": requirements.get("budget_range", "5000-10000"),
                "event_date": requirements.get("event_date"),
                "requirements": requirements
            }
            
            proposal_result = await proposal_mcp.server.call_tool(
                "generate_proposal",
                proposal_params
            )
            
            if proposal_result.isError:
                raise Exception(f"Proposal generation failed: {proposal_result.content[0].text}")
            
            proposal_data = json.loads(proposal_result.content[0].text)
            
            # Create proposal data object
            proposal = ProposalData(
                proposal_name=f"Proposal for {state['prospect_data'].name}",
                total_price=proposal_data.get("total_price", 0),
                guest_count=requirements.get("guest_count", 50),
                event_date=datetime.fromisoformat(requirements.get("event_date")),
                event_type=requirements.get("event_type", "event"),
                venue_details=proposal_data.get("venue_details", {}),
                package_details=proposal_data.get("package_details", {}),
                proposal_pdf_url=proposal_data.get("pdf_url"),
                mood_board_url=proposal_data.get("mood_board_url"),
                valid_until=datetime.now() + timedelta(days=30)
            )
            
            state["proposal_data"] = proposal
            
            logger.info(
                "Proposal generation completed",
                workflow_id=state["workflow_id"],
                total_price=proposal.total_price
            )
            
            return state
            
        except Exception as e:
            logger.error("Proposal generation failed", error=str(e), workflow_id=state["workflow_id"])
            return StateManager.add_error(
                state, "proposal", "generation_error", str(e)
            )
    
    async def _meeting_node(self, state: RainmakerState) -> RainmakerState:
        """Meeting agent node - schedule meetings"""
        logger.info("Starting meeting scheduling", workflow_id=state["workflow_id"])
        
        try:
            state = StateManager.update_stage(state, WorkflowStage.MEETING)
            
            prospect_data = state["prospect_data"]
            
            # Use calendar MCP to schedule meeting
            meeting_params = {
                "prospect_name": prospect_data.name,
                "prospect_email": prospect_data.email,
                "meeting_type": "consultation",
                "duration_minutes": 60
            }
            
            meeting_result = await calendar_mcp.server.call_tool(
                "schedule_meeting",
                meeting_params
            )
            
            if meeting_result.isError:
                raise Exception(f"Meeting scheduling failed: {meeting_result.content[0].text}")
            
            meeting_data = json.loads(meeting_result.content[0].text)
            
            # Create meeting details object
            meeting = MeetingDetails(
                meeting_type="consultation",
                title=f"Consultation with {prospect_data.name}",
                description="Initial consultation to discuss event requirements",
                scheduled_at=datetime.fromisoformat(meeting_data.get("scheduled_at")) if meeting_data.get("scheduled_at") else None,
                duration_minutes=60,
                meeting_url=meeting_data.get("meeting_url"),
                calendar_event_id=meeting_data.get("calendar_event_id"),
                attendees=[{"name": prospect_data.name, "email": prospect_data.email}],
                status="scheduled"
            )
            
            state["meeting_details"] = meeting
            
            logger.info(
                "Meeting scheduling completed",
                workflow_id=state["workflow_id"],
                scheduled_at=meeting.scheduled_at
            )
            
            return state
            
        except Exception as e:
            logger.error("Meeting scheduling failed", error=str(e), workflow_id=state["workflow_id"])
            return StateManager.add_error(
                state, "meeting", "scheduling_error", str(e)
            )
    
    async def _approval_node(self, state: RainmakerState) -> RainmakerState:
        """Handle human approval requests"""
        logger.info("Processing approval request", workflow_id=state["workflow_id"])
        
        # Set current stage to pending approval
        state = StateManager.update_stage(state, WorkflowStage.PENDING_APPROVAL)
        state["approval_pending"] = True
        
        # In a real implementation, this would wait for human approval
        # For now, we'll simulate approval after a brief pause
        await asyncio.sleep(1)
        
        # Simulate approval granted
        state["approval_pending"] = False
        
        logger.info("Approval granted", workflow_id=state["workflow_id"])
        return state
    
    async def _error_handler_node(self, state: RainmakerState) -> RainmakerState:
        """Handle errors and determine retry strategy"""
        logger.info("Processing error", workflow_id=state["workflow_id"])
        
        errors = state.get("errors", [])
        if not errors:
            return state
        
        latest_error = errors[-1]
        retry_count = state.get("retry_count", 0)
        max_retries = state.get("max_retries", 3)
        
        if retry_count < max_retries:
            logger.info(
                "Retrying after error",
                workflow_id=state["workflow_id"],
                retry_count=retry_count,
                error_type=latest_error.error_type
            )
            # Reset for retry
            state["retry_count"] = retry_count + 1
            return state
        else:
            logger.warning(
                "Max retries exceeded, escalating to human",
                workflow_id=state["workflow_id"],
                max_retries=max_retries
            )
            state["human_intervention_needed"] = True
            return state
    
    async def _human_escalation_node(self, state: RainmakerState) -> RainmakerState:
        """Handle human escalation"""
        logger.info("Escalating to human", workflow_id=state["workflow_id"])
        
        state = StateManager.update_stage(state, WorkflowStage.FAILED)
        state["human_intervention_needed"] = True
        
        # In a real implementation, this would notify humans
        # and pause the workflow until manual intervention
        
        return state
    
    async def _workflow_complete_node(self, state: RainmakerState) -> RainmakerState:
        """Mark workflow as completed"""
        logger.info("Workflow completed", workflow_id=state["workflow_id"])
        
        state = StateManager.update_stage(state, WorkflowStage.COMPLETED)
        
        # Calculate total duration
        if "workflow_started_at" in state:
            total_duration = (datetime.now() - state["workflow_started_at"]).total_seconds()
            state["total_duration"] = total_duration
        
        return state
    
    # Routing functions
    
    def _route_from_hunter(self, state: RainmakerState) -> str:
        """Route from hunter agent based on results"""
        if state.get("errors") and state.get("retry_count", 0) >= state.get("max_retries", 3):
            return "escalate"
        elif state.get("errors"):
            return "error_handler"
        elif not state.get("hunter_results") or state["hunter_results"].prospects_found == 0:
            return "escalate"  # No prospects found
        elif state.get("approval_pending"):
            return "approval"
        else:
            return "enricher"
    
    def _route_from_enricher(self, state: RainmakerState) -> str:
        """Route from enricher agent"""
        if state.get("errors") and state.get("retry_count", 0) >= state.get("max_retries", 3):
            return "escalate"
        elif state.get("errors"):
            return "error_handler"
        elif state.get("approval_pending"):
            return "approval"
        elif not state.get("enrichment_data"):
            return "escalate"  # Enrichment failed
        else:
            return "outreach"
    
    def _route_from_outreach(self, state: RainmakerState) -> str:
        """Route from outreach agent"""
        if state.get("errors") and state.get("retry_count", 0) >= state.get("max_retries", 3):
            return "escalate"
        elif state.get("errors"):
            return "error_handler"
        elif state.get("approval_pending"):
            return "approval"
        else:
            return "conversation"
    
    def _route_from_conversation(self, state: RainmakerState) -> str:
        """Route from conversation agent"""
        if state.get("errors") and state.get("retry_count", 0) >= state.get("max_retries", 3):
            return "escalate"
        elif state.get("errors"):
            return "error_handler"
        elif state.get("approval_pending"):
            return "approval"
        
        conversation = state.get("conversation_summary")
        if conversation and conversation.qualification_score >= 70:
            return "proposal"
        elif conversation and conversation.next_action == "follow_up":
            return "outreach"  # Follow up outreach
        else:
            return "escalate"  # Low qualification score
    
    def _route_from_proposal(self, state: RainmakerState) -> str:
        """Route from proposal agent"""
        if state.get("errors") and state.get("retry_count", 0) >= state.get("max_retries", 3):
            return "escalate"
        elif state.get("errors"):
            return "error_handler"
        elif state.get("approval_pending"):
            return "approval"
        elif state.get("proposal_data"):
            return "meeting"
        else:
            return "conversation"  # Need more info
    
    def _route_from_meeting(self, state: RainmakerState) -> str:
        """Route from meeting agent"""
        if state.get("errors") and state.get("retry_count", 0) >= state.get("max_retries", 3):
            return "escalate"
        elif state.get("errors"):
            return "error_handler"
        elif state.get("approval_pending"):
            return "approval"
        elif state.get("meeting_details"):
            return "workflow_complete"
        else:
            return "conversation"  # Schedule another meeting
    
    def _route_from_approval(self, state: RainmakerState) -> str:
        """Route from approval node"""
        if state.get("approval_pending"):
            return "approval"  # Still waiting
        
        # Return to the stage that requested approval
        current_stage = state.get("current_stage")
        if current_stage == WorkflowStage.HUNTING:
            return "hunter"
        elif current_stage == WorkflowStage.ENRICHING:
            return "enricher"
        elif current_stage == WorkflowStage.OUTREACH:
            return "outreach"
        elif current_stage == WorkflowStage.CONVERSATION:
            return "conversation"
        elif current_stage == WorkflowStage.PROPOSAL:
            return "proposal"
        elif current_stage == WorkflowStage.MEETING:
            return "meeting"
        else:
            return "human_escalation"
    
    def _route_from_error_handler(self, state: RainmakerState) -> str:
        """Route from error handler"""
        if state.get("human_intervention_needed"):
            return "human_escalation"
        
        errors = state.get("errors", [])
        if not errors:
            return "workflow_complete"
        
        # Route back to the failed stage for retry
        latest_error = errors[-1]
        agent_name = latest_error.agent_name
        
        if agent_name == "prospect_hunter":
            return "hunter"
        elif agent_name == "enricher":
            return "enricher"
        elif agent_name == "outreach":
            return "outreach"
        elif agent_name == "conversation":
            return "conversation"
        elif agent_name == "proposal":
            return "proposal"
        elif agent_name == "meeting":
            return "meeting"
        else:
            return "human_escalation"
    
    async def execute_workflow(self, initial_state: RainmakerState) -> RainmakerState:
        """
        Execute the complete workflow for a prospect.
        
        Args:
            initial_state: Initial workflow state
            
        Returns:
            Final workflow state
        """
        logger.info(
            "Starting workflow execution",
            workflow_id=initial_state["workflow_id"],
            prospect_name=initial_state["prospect_data"].name
        )
        
        try:
            # Execute the workflow
            final_state = await self.app.ainvoke(initial_state)
            
            logger.info(
                "Workflow execution completed",
                workflow_id=final_state["workflow_id"],
                final_stage=final_state.get("current_stage")
            )
            
            return final_state
            
        except Exception as e:
            logger.error(
                "Workflow execution failed",
                error=str(e),
                workflow_id=initial_state["workflow_id"]
            )
            
            # Add error to state and return
            error_state = StateManager.add_error(
                initial_state,
                "workflow_orchestrator",
                "execution_error", 
                str(e)
            )
            return error_state


# Global workflow instance
rainmaker_workflow = RainmakerWorkflow()
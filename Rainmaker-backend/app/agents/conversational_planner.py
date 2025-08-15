"""
Conversational Planning Agent - Handles user interaction and plan creation
"""

import json
from typing import Dict, List, Optional, Any
from datetime import datetime
import structlog

from app.services.gemini_service import gemini_service
from app.mcp.database import database_mcp
from .planning_models import (
    CampaignPlan, CampaignObjectives, TargetProfile, ExecutionStrategy, 
    PlanningConversation, PlanningPhase, CampaignType
)

logger = structlog.get_logger(__name__)


class ConversationalPlannerAgent:
    """
    Handles conversational planning sessions with users.
    Collects requirements and creates comprehensive campaign plans.
    """
    
    def __init__(self):
        self.gemini_service = gemini_service
        self.active_conversations: Dict[str, PlanningConversation] = {}
        
    # =============================================================================
    # CONVERSATIONAL PLANNING INTERFACE
    # =============================================================================
    
    async def start_planning_conversation(self, user_id: str, 
                                        initial_context: Optional[Dict[str, Any]] = None) -> PlanningConversation:
        """Start a new planning conversation with the user"""
        
        conversation_id = f"planning_{user_id}_{int(datetime.now().timestamp())}"
        
        conversation = PlanningConversation(
            conversation_id=conversation_id,
            user_id=user_id,
            current_phase=PlanningPhase.INITIAL_ASSESSMENT,
            collected_info=initial_context or {}
        )
        
        self.active_conversations[conversation_id] = conversation
        
        logger.info("Created planning conversation", 
                   conversation_id=conversation_id, 
                   user_id=user_id,
                   total_active=len(self.active_conversations))
        
        # Generate initial assessment questions
        initial_response = await self._generate_initial_assessment(conversation)
        
        # Set initial clarifications for the welcome message
        conversation.clarification_needed = [
            "What types of events should I find prospects for?",
            "Which city or region should I search in?"
        ]
        
        conversation.conversation_history.append({
            "role": "assistant",
            "content": initial_response,
            "timestamp": datetime.now().isoformat()
        })
        
        logger.info("Started planning conversation", 
                   conversation_id=conversation_id, 
                   user_id=user_id,
                   initial_clarifications=conversation.clarification_needed)
        return conversation
    
    async def process_user_response(self, conversation_id: str, 
                                  user_message: str) -> Dict[str, Any]:
        """Process user response and continue planning conversation"""
        
        logger.info("Processing user response", 
                   conversation_id=conversation_id, 
                   active_conversations=list(self.active_conversations.keys()),
                   message_preview=user_message[:50])
        
        if conversation_id not in self.active_conversations:
            logger.error("Planning conversation not found", 
                        conversation_id=conversation_id,
                        available_conversations=list(self.active_conversations.keys()))
            raise ValueError(f"Planning conversation not found: {conversation_id}")
        
        conversation = self.active_conversations[conversation_id]
        
        # Add user message to history
        conversation.conversation_history.append({
            "role": "user", 
            "content": user_message,
            "timestamp": datetime.now().isoformat()
        })
        
        # Analyze user response and extract information
        extracted_info = await self._analyze_user_response(conversation, user_message)
        
        # Merge extracted information with existing data, preserving arrays
        for key, value in extracted_info.items():
            if key in conversation.collected_info:
                # If it's a list, merge the lists and remove duplicates
                if isinstance(conversation.collected_info[key], list) and isinstance(value, list):
                    combined = conversation.collected_info[key] + value
                    conversation.collected_info[key] = list(set(combined))  # Remove duplicates
                else:
                    conversation.collected_info[key] = value
            else:
                conversation.collected_info[key] = value
                
        logger.info("Merged collected information", 
                   conversation_id=conversation.conversation_id,
                   collected_info=conversation.collected_info)
        
        # Determine next phase and questions
        next_phase_info = await self._determine_next_phase(conversation)
        
        # Update conversation state
        try:
            conversation.current_phase = PlanningPhase(next_phase_info.get("next_phase", conversation.current_phase.value))
            conversation.completion_percentage = float(next_phase_info.get("completion_percentage", conversation.completion_percentage))
            conversation.clarification_needed = next_phase_info.get("clarifications_needed", [])
        except Exception as e:
            logger.error("Failed to update conversation state", error=str(e))
        
        # Generate assistant response
        assistant_response = await self._generate_phase_response(conversation, next_phase_info)
        
        conversation.conversation_history.append({
            "role": "assistant",
            "content": assistant_response,
            "timestamp": datetime.now().isoformat()
        })
        
        # Check if planning is complete
        is_complete = self._check_planning_completion(conversation)
        
        response = {
            "conversation_id": conversation_id,
            "current_phase": conversation.current_phase.value,
            "completion_percentage": float(conversation.completion_percentage),
            "assistant_response": str(assistant_response),
            "is_complete": bool(is_complete),
            "clarifications_needed": list(conversation.clarification_needed) if conversation.clarification_needed else [],
            "suggested_responses": list(conversation.suggested_responses) if conversation.suggested_responses else []
        }
        
        # If complete, generate the campaign plan
        if is_complete:
            campaign_plan = await self._create_campaign_plan(conversation)
            response["campaign_plan"] = self._campaign_plan_to_dict(campaign_plan)
        
        return response
    
    # =============================================================================
    # PRIVATE METHODS
    # =============================================================================
    
    async def _generate_initial_assessment(self, conversation: PlanningConversation) -> str:
        """Generate initial assessment questions to start planning"""
        
        initial_prompt = f"""
        You are Rainmaker, a prospect discovery tool for event planning businesses.

        Create a brief greeting that asks ONLY these 2 questions:
        1. What types of events should I find prospects for? (weddings, corporate events, birthdays, etc.)
        2. Which city or region should I search in?

        Keep it short and direct. Do NOT ask about business goals, sales targets, or anything else.
        """
        
        try:
            response = await self.gemini_service.generate_agent_response(
                system_prompt="You find event planning prospects. Ask ONLY about event types and location. 2-3 sentences maximum. No business strategy questions.",
                user_message=initial_prompt
            )
            return response.strip()
            
        except Exception as e:
            logger.error("Failed to generate initial assessment", error=str(e))
            raise
    
    async def _analyze_user_response(self, conversation: PlanningConversation, 
                                   user_message: str) -> Dict[str, Any]:
        """Analyze user response and extract structured information"""
        
        collected_info_str = json.dumps(conversation.collected_info, indent=2)
        
        analysis_prompt = f"""
        Update the prospect discovery information based on this user message:

        USER MESSAGE: "{user_message}"
        
        EXISTING COLLECTED INFO:
        {collected_info_str}

        TASK: Extract new information from the user message and MERGE it with existing info.
        DO NOT LOSE any previously collected information.

        Look for these 4 types of information in the user message:
        1. Event types: ["weddings", "corporate_events", "birthdays", "anniversaries"] 
        2. Geographic locations: cities, regions, countries
        3. Search channels: where to look for prospects
        4. Number of prospects: extract numbers like "4", "about 4", "4 prospects", "four", etc.

        Return COMPLETE JSON with ALL information (existing + new):
        - Keep all previously collected event_types_to_target
        - Keep all previously collected geographic_location_to_search  
        - Keep all previously collected search_channels
        - Keep all previously collected target_prospects or number_of_prospects
        - Add any NEW information from the current message

        Return the MERGED result as JSON only.
        """
        
        try:
            response = await self.gemini_service.generate_agent_response(
                system_prompt="You maintain prospect discovery information. PRESERVE all existing data and ADD new information. NEVER lose previously collected info. Return complete merged JSON only.",
                user_message=analysis_prompt
            )
            
            # Clean the response to ensure it's valid JSON
            response = response.strip()
            if response.startswith('```json'):
                response = response[7:]
            if response.endswith('```'):
                response = response[:-3]
            response = response.strip()
            
            if not response:
                logger.warning("Empty response from analysis")
                return {}
            
            parsed_response = json.loads(response)
            return parsed_response
            
        except json.JSONDecodeError as e:
            logger.warning("Failed to parse JSON from analysis response", error=str(e))
            return {}
        except Exception as e:
            logger.error("Failed to analyze user response", error=str(e))
            raise
    
    async def _determine_next_phase(self, conversation: PlanningConversation) -> Dict[str, Any]:
        """Determine what phase to move to next and what information is still needed"""
        
        collected_info_str = json.dumps(conversation.collected_info, indent=2)
        
        phase_prompt = f"""
        CURRENT PHASE: {conversation.current_phase.value}
        COLLECTED INFO: {collected_info_str}

        You help find EVENT PLANNING PROSPECTS. Check if you have these 4 things:
        1. Event types to target (weddings, corporate, birthdays, etc.)
        2. Geographic location to search  
        3. Search methods/channels (social media, event listings, etc.)
        4. Number of prospects needed

        Calculate completion percentage based on what you have:
        - Have 1 item: completion = 0.25
        - Have 2 items: completion = 0.50  
        - Have 3 items: completion = 0.75
        - Have all 4 items: completion = 0.90, next_phase = "approval_confirmation"

        If missing any: ask ONLY for what's missing with simple questions

        NEVER ask about:
        - Business goals, sales objectives, market expansion
        - Partnerships, revenue targets, KPIs  
        - Company strategies or growth plans

        Return JSON: {{"next_phase": "phase_name", "completion_percentage": 0.0-1.0, "clarifications_needed": ["simple question"], "concerns": []}}
        """
        
        try:
            response = await self.gemini_service.generate_agent_response(
                system_prompt="You manage prospect discovery conversations. Focus ONLY on finding event prospects - NOT advertising or budgets. ALWAYS respond with valid JSON only.",
                user_message=phase_prompt
            )
            
            # Clean the response to ensure it's valid JSON
            response = response.strip()
            if response.startswith('```json'):
                response = response[7:]
            if response.endswith('```'):
                response = response[:-3]
            response = response.strip()
            
            if not response:
                logger.warning("Empty response from phase determination")
                raise ValueError("Empty response from phase determination")
            
            parsed_response = json.loads(response)
            return parsed_response
            
        except json.JSONDecodeError as e:
            logger.error("Failed to parse JSON from phase determination response", error=str(e))
            raise
        except Exception as e:
            logger.error("Failed to determine next phase", error=str(e))
            raise
    
    async def _generate_phase_response(self, conversation: PlanningConversation, 
                                     phase_info: Dict[str, Any]) -> str:
        """Generate appropriate response for current planning phase"""
        
        collected_info_str = json.dumps(conversation.collected_info, indent=2)
        has_sufficient_info = self._check_planning_completion(conversation)
        readiness_context = "READY_TO_PROCEED" if has_sufficient_info else "NEED_MORE_INFO"
        
        clarifications = phase_info.get("clarifications_needed", [])
        
        response_prompt = f"""
        You help find EVENT PLANNING PROSPECTS. Your ONLY job is to get these 4 things:
        1. Event types to target
        2. Geographic location to search  
        3. Search methods/channels
        4. Number of prospects needed

        COLLECTED INFO: {collected_info_str}
        READINESS: {readiness_context}
        MISSING INFO: {clarifications}

        RESPONSE RULES:
        - If READY_TO_PROCEED: Say "Perfect! I have what I need to find [event types] prospects in [location]. Ready to start the search?"
        - If NEED_MORE_INFO: Ask the FIRST question from the MISSING INFO list exactly as provided
        - If in APPROVAL_CONFIRMATION phase with 90%+ completion: ALWAYS say ready to proceed, don't ask for more info
        - NEVER ask about business goals, sales targets, partnerships, revenue, KPIs, market share
        - Keep responses to 1 sentence maximum

        Return just the response text (1 sentence).
        """
        
        try:
            response = await self.gemini_service.generate_agent_response(
                system_prompt="You are a prospect discovery assistant. ONLY ask about: event types, location, search channels. NEVER ask about business goals, sales, or revenue. 1 sentence responses only.",
                user_message=response_prompt
            )
            
            return response.strip()
            
        except Exception as e:
            logger.error("Failed to generate phase response", error=str(e))
            raise
    
    async def _create_campaign_plan(self, conversation: PlanningConversation) -> CampaignPlan:
        """Create comprehensive campaign plan from conversation"""
        
        collected_info_str = json.dumps(conversation.collected_info, indent=2)
        
        plan_creation_prompt = f"""
        Based on: {collected_info_str}

        Create a SHORT campaign plan. Return ONLY this JSON (no extra text):

        {{
          "campaign_name": "Brief descriptive name",
          "objectives": {{"primary_goal": "generate_leads", "target_prospects": 10}},
          "target_profile": {{"event_types": ["event_type"], "geographic_regions": ["location"]}},
          "execution_strategy": {{"campaign_type": "discovery_focused", "agent_sequence": ["hunter"]}},
          "expected_timeline": {{"duration": "1 week"}},
          "resource_requirements": {{"main_tool": "search"}},
          "risk_factors": ["minimal"],
          "success_predictions": {{"probability": 0.8}}
        }}

        Keep it SHORT. Return only JSON.
        """
        
        try:
            response = await self.gemini_service.generate_agent_response(
                system_prompt="Create a SHORT campaign plan. Return ONLY valid JSON, no explanations, no markdown, no extra text. Keep it simple.",
                user_message=plan_creation_prompt
            )
            
            # Clean the response to ensure it's valid JSON
            response = response.strip()
            if response.startswith('```json'):
                response = response[7:]
            if response.endswith('```'):
                response = response[:-3]
            response = response.strip()
            
            if not response:
                logger.error("Empty response from campaign plan creation")
                raise ValueError("Empty response from Gemini")
            
            plan_data = json.loads(response)
            
            # Create structured campaign plan with safe object creation
            objectives_data = plan_data.get("objectives", {})
            if "primary_goal" not in objectives_data:
                objectives_data["primary_goal"] = "generate_leads"
                
            target_profile_data = plan_data.get("target_profile", {})
            execution_strategy_data = plan_data.get("execution_strategy", {})
            if "campaign_type" not in execution_strategy_data:
                execution_strategy_data["campaign_type"] = "discovery_focused"
            
            # Filter data to only include valid fields
            valid_execution_fields = {
                "campaign_type", "agent_sequence", "parallel_agents", 
                "conditional_routing", "approval_gates", "success_metrics", 
                "optimization_triggers"
            }
            execution_strategy_data = {k: v for k, v in execution_strategy_data.items() 
                                     if k in valid_execution_fields}
            
            valid_target_fields = {
                "prospect_types", "event_types", "budget_ranges", "geographic_regions",
                "company_sizes", "decision_maker_titles", "seasonal_preferences", "exclusions"
            }
            target_profile_data = {k: v for k, v in target_profile_data.items() 
                                 if k in valid_target_fields}
            
            valid_objective_fields = {
                "primary_goal", "target_prospects", "target_meetings", "target_proposals",
                "target_conversions", "budget_range", "timeline_days", "geographic_focus",
                "event_types_focus", "priority_level"
            }
            objectives_data = {k: v for k, v in objectives_data.items() 
                             if k in valid_objective_fields}
            
            campaign_plan = CampaignPlan(
                plan_id=f"plan_{conversation.user_id}_{int(datetime.now().timestamp())}",
                created_at=datetime.now(),
                user_id=conversation.user_id,
                campaign_name=plan_data.get("campaign_name", "Event Planning Sales Campaign"),
                objectives=CampaignObjectives(**objectives_data),
                target_profile=TargetProfile(**target_profile_data),
                execution_strategy=ExecutionStrategy(**execution_strategy_data),
                expected_timeline=plan_data.get("timeline", {}),
                resource_requirements=plan_data.get("resource_requirements", {}),
                risk_factors=plan_data.get("risk_factors", []),
                success_predictions=plan_data.get("success_predictions", {}),
                plan_metadata={
                    "conversation_id": conversation.conversation_id,
                    "planning_duration": len(conversation.conversation_history),
                    "completion_score": conversation.completion_percentage,
                    "created_from": "conversational_planning"
                }
            )
            
            # Store plan in database
            await self._store_campaign_plan(campaign_plan)
            
            # Also store in the coordination system for execution
            # We need to access the campaign coordinator to add the plan to active campaigns
            # This ensures the plan is available for execution via the API
            if hasattr(self, 'campaign_coordinator'):
                self.campaign_coordinator.active_campaigns[campaign_plan.plan_id] = campaign_plan
            else:
                # Fallback: store in a class-level registry that can be accessed by the master planner
                if not hasattr(ConversationalPlannerAgent, '_created_plans'):
                    ConversationalPlannerAgent._created_plans = {}
                ConversationalPlannerAgent._created_plans[campaign_plan.plan_id] = campaign_plan
            
            return campaign_plan
            
        except json.JSONDecodeError as e:
            logger.error("Failed to parse JSON from campaign plan creation response", error=str(e))
            raise
        except Exception as e:
            logger.error("Failed to create campaign plan", error=str(e))
            raise
    
    async def _store_campaign_plan(self, plan: CampaignPlan):
        """Store campaign plan in database"""
        try:
            # Properly serialize the objects with enum handling
            objectives_dict = {
                "primary_goal": plan.objectives.primary_goal,
                "target_prospects": plan.objectives.target_prospects,
                "target_meetings": plan.objectives.target_meetings,
                "target_proposals": plan.objectives.target_proposals,
                "target_conversions": plan.objectives.target_conversions,
                "budget_range": plan.objectives.budget_range,
                "timeline_days": plan.objectives.timeline_days,
                "geographic_focus": plan.objectives.geographic_focus,
                "event_types_focus": plan.objectives.event_types_focus,
                "priority_level": plan.objectives.priority_level
            }
            
            target_profile_dict = {
                "prospect_types": plan.target_profile.prospect_types,
                "event_types": plan.target_profile.event_types,
                "budget_ranges": plan.target_profile.budget_ranges,
                "geographic_regions": plan.target_profile.geographic_regions,
                "company_sizes": plan.target_profile.company_sizes,
                "decision_maker_titles": plan.target_profile.decision_maker_titles,
                "seasonal_preferences": plan.target_profile.seasonal_preferences,
                "exclusions": plan.target_profile.exclusions
            }
            
            execution_strategy_dict = {
                "campaign_type": plan.execution_strategy.campaign_type.value if hasattr(plan.execution_strategy.campaign_type, 'value') else str(plan.execution_strategy.campaign_type),
                "agent_sequence": list(plan.execution_strategy.agent_sequence) if plan.execution_strategy.agent_sequence else [],
                "parallel_agents": list(plan.execution_strategy.parallel_agents) if plan.execution_strategy.parallel_agents else [],
                "conditional_routing": dict(plan.execution_strategy.conditional_routing) if plan.execution_strategy.conditional_routing else {},
                "approval_gates": list(plan.execution_strategy.approval_gates) if plan.execution_strategy.approval_gates else [],
                "success_metrics": dict(plan.execution_strategy.success_metrics) if plan.execution_strategy.success_metrics else {},
                "optimization_triggers": dict(plan.execution_strategy.optimization_triggers) if plan.execution_strategy.optimization_triggers else {}
            }
            
            result = await database_mcp.call_tool(
                "execute_query",
                {
                    "query": """
                    INSERT INTO campaign_plans (
                        plan_id, user_id, campaign_name, objectives, 
                        target_profile, execution_strategy, created_at
                    ) VALUES (:plan_id, :user_id, :campaign_name, :objectives, :target_profile, :execution_strategy, :created_at)
                    """,
                    "parameters": {
                        "plan_id": plan.plan_id,
                        "user_id": plan.user_id,
                        "campaign_name": plan.campaign_name,
                        "objectives": json.dumps(objectives_dict),
                        "target_profile": json.dumps(target_profile_dict),
                        "execution_strategy": json.dumps(execution_strategy_dict),
                        "created_at": plan.created_at.isoformat()
                    },
                    "fetch_mode": "none"
                }
            )
            
            if result.isError:
                error_msg = result.content[0].text if result.content else "Unknown database error"
                logger.error("Database insertion failed", error=error_msg, plan_id=plan.plan_id)
                raise RuntimeError(f"Failed to store campaign plan: {error_msg}")
            
            logger.info("Campaign plan stored successfully", plan_id=plan.plan_id)
            
        except Exception as e:
            logger.error("Failed to store campaign plan", error=str(e), plan_id=plan.plan_id)
    
    def _check_planning_completion(self, conversation: PlanningConversation) -> bool:
        """Check if enough information has been gathered to create a campaign plan"""
        
        info = conversation.collected_info
        
        # Check for required information
        has_event_types = (
            "event_types_to_target" in info or 
            "event_types" in info or
            any("event" in str(key).lower() for key in info.keys())
        )
        
        has_geographic_info = (
            "geographic_location_to_search" in info or
            "geographic_location" in info or
            any("location" in str(key).lower() or "geographic" in str(key).lower() for key in info.keys())
        )
        
        has_search_methods = (
            "search_channels" in info or
            "search_methods" in info or
            any("channel" in str(key).lower() or "method" in str(key).lower() for key in info.keys())
        )
        
        has_prospect_count = (
            "target_prospects" in info or
            "number_of_prospects" in info or
            any("prospect" in str(key).lower() and ("number" in str(key).lower() or "count" in str(key).lower()) for key in info.keys())
        )
        
        # COMPREHENSIVE completion criteria - need ALL of these
        comprehensive_requirements_met = (
            has_event_types and 
            has_geographic_info and 
            has_search_methods and
            has_prospect_count
        )
        
        # Only complete if we have ALL required info AND user explicitly confirms
        user_confirmed = self._user_confirmed_to_start(conversation)
        is_complete = comprehensive_requirements_met and user_confirmed
        
        return is_complete

    def _user_confirmed_to_start(self, conversation: PlanningConversation) -> bool:
        """Check if user has explicitly confirmed to start the campaign"""
        
        # Look at the last user message to see if they confirmed
        last_user_messages = [msg for msg in conversation.conversation_history[-3:] 
                             if msg.get("role") == "user"]
        
        if not last_user_messages:
            return False
            
        last_message = last_user_messages[-1].get("content", "").lower()
        
        # Check for confirmation keywords
        confirmation_words = ["yes", "start", "begin", "go", "proceed", "launch", "ready"]
        negative_words = ["no", "not", "wait", "stop", "later"]
        
        has_confirmation = any(word in last_message for word in confirmation_words)
        has_negative = any(word in last_message for word in negative_words)
        
        return has_confirmation and not has_negative

    def _campaign_plan_to_dict(self, campaign_plan: CampaignPlan) -> Dict[str, Any]:
        """Convert CampaignPlan to JSON-serializable dictionary"""
        return {
            "plan_id": campaign_plan.plan_id,
            "created_at": campaign_plan.created_at.isoformat(),
            "user_id": campaign_plan.user_id,
            "campaign_name": campaign_plan.campaign_name,
            "objectives": {
                "primary_goal": campaign_plan.objectives.primary_goal,
                "target_prospects": campaign_plan.objectives.target_prospects,
                "target_meetings": campaign_plan.objectives.target_meetings,
                "target_proposals": campaign_plan.objectives.target_proposals,
                "target_conversions": campaign_plan.objectives.target_conversions,
                "budget_range": campaign_plan.objectives.budget_range,
                "timeline_days": campaign_plan.objectives.timeline_days,
                "geographic_focus": campaign_plan.objectives.geographic_focus,
                "event_types_focus": campaign_plan.objectives.event_types_focus,
                "priority_level": campaign_plan.objectives.priority_level
            },
            "target_profile": {
                "prospect_types": campaign_plan.target_profile.prospect_types,
                "event_types": campaign_plan.target_profile.event_types,
                "budget_ranges": campaign_plan.target_profile.budget_ranges,
                "geographic_regions": campaign_plan.target_profile.geographic_regions,
                "company_sizes": campaign_plan.target_profile.company_sizes,
                "decision_maker_titles": campaign_plan.target_profile.decision_maker_titles,
                "seasonal_preferences": campaign_plan.target_profile.seasonal_preferences,
                "exclusions": campaign_plan.target_profile.exclusions
            },
            "execution_strategy": {
                "campaign_type": campaign_plan.execution_strategy.campaign_type.value if hasattr(campaign_plan.execution_strategy.campaign_type, 'value') else campaign_plan.execution_strategy.campaign_type,
                "agent_sequence": campaign_plan.execution_strategy.agent_sequence,
                "parallel_agents": campaign_plan.execution_strategy.parallel_agents,
                "conditional_routing": campaign_plan.execution_strategy.conditional_routing,
                "approval_gates": campaign_plan.execution_strategy.approval_gates,
                "success_metrics": campaign_plan.execution_strategy.success_metrics,
                "optimization_triggers": campaign_plan.execution_strategy.optimization_triggers
            },
            "expected_timeline": campaign_plan.expected_timeline,
            "resource_requirements": campaign_plan.resource_requirements,
            "risk_factors": campaign_plan.risk_factors,
            "success_predictions": campaign_plan.success_predictions,
            "plan_metadata": campaign_plan.plan_metadata
        }
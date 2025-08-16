"""
Simple Enrichment Agent - Rebuilt for Sonar + Gemini Integration

This agent receives prospect data from LangGraph workflow, uses Sonar API for research,
and Gemini for analysis with real-time reasoning display. No confidence scoring,
no fallbacks - simple and direct.
"""

import asyncio
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
import structlog

from app.core.state import RainmakerState, EnrichmentData, ProspectData, StateManager
from app.services.gemini_service import gemini_service
from app.mcp.web_search import WebSearchMCP, SonarAPIError

logger = structlog.get_logger(__name__)

# Global callback for enrichment viewer updates
enrichment_viewer_callback = None

def set_enrichment_viewer_callback(callback):
    """Set callback function for enrichment viewer updates"""
    global enrichment_viewer_callback
    enrichment_viewer_callback = callback
    logger.info("✅ Enrichment viewer callback set", callback_type=type(callback).__name__)


class EnrichmentAgent:
    """
    Simple enrichment agent with clean Sonar + Gemini integration.
    
    Features:
    - Receives RainmakerState from LangGraph workflow
    - Uses Sonar API directly for web research
    - Uses Gemini for analysis with real-time reasoning
    - No confidence scoring or complex validation
    - No fallback logic - halts on failures
    """
    
    def __init__(self):
        self.web_search = WebSearchMCP()
        
        # Reference to orchestrator for WebSocket broadcasting
        try:
            from app.services.orchestrator import agent_orchestrator
            self.orchestrator = agent_orchestrator
        except ImportError:
            self.orchestrator = None
            logger.warning("Orchestrator not available for WebSocket broadcasting")
        
        logger.info("EnrichmentAgent initialized")
    
    def _send_enrichment_update(self, workflow_id: str, step: str, reasoning: str, 
                               status: str = "active", data: Optional[Dict[str, Any]] = None):
        """Send real-time enrichment update to frontend"""
        if enrichment_viewer_callback:
            try:
                update_data = {
                    "type": "enrichment_update",
                    "workflow_id": workflow_id,
                    "step": step,
                    "reasoning": reasoning,
                    "status": status,
                    "timestamp": datetime.now().isoformat()
                }
                
                if data:
                    update_data["data"] = data
                
                enrichment_viewer_callback(update_data)
                logger.debug("✅ Enrichment update sent", step=step, workflow_id=workflow_id)
            except Exception as e:
                logger.warning("❌ Failed to send enrichment update", error=str(e))
        else:
            logger.debug("⚠️ No enrichment viewer callback set - updates not being sent to frontend")
    
    async def enrich_prospect(self, state: RainmakerState) -> RainmakerState:
        """
        Main enrichment method - simple and direct.
        
        Args:
            state: RainmakerState from workflow
            
        Returns:
            Updated state with enrichment data
        """
        workflow_id = state["workflow_id"]
        prospect_data = state["prospect_data"]
        
        logger.info(
            "Starting prospect enrichment",
            workflow_id=workflow_id,
            prospect_name=prospect_data.name
        )
        
        try:
            # Step 1: Research person
            search_query = f"Find information about {prospect_data.name}"
            if prospect_data.company_name:
                search_query += f" who works at {prospect_data.company_name}"
            if prospect_data.location:
                search_query += f" in {prospect_data.location}"
            search_query += ". Include professional background, role, and any event planning activity."
            
            self._send_enrichment_update(
                workflow_id=workflow_id,
                step="Person Research",
                reasoning=f"🔍 Searching Perplexity Sonar for: '{search_query[:100]}...'",
                status="active"
            )
            
            person_data = await self.web_search.search_person(
                prospect_data.name,
                {
                    "company": prospect_data.company_name,
                    "location": prospect_data.location
                }
            )
            
            # Send detailed results
            person_results = person_data.get("results", [])
            citations_found = len(person_data.get("citations", []))
            self._send_enrichment_update(
                workflow_id=workflow_id,
                step="Person Research Complete",
                reasoning=f"✅ Found {citations_found} sources about {prospect_data.name}. Discovered: {person_results[:2] if person_results else 'Limited public information'}",
                status="complete",
                data={"citations_count": citations_found, "results_preview": person_results[:2]}
            )
            
            # Step 2: Research company (if applicable)
            company_data = {}
            if prospect_data.company_name:
                company_query = f"Find information about {prospect_data.company_name} company"
                if prospect_data.location:
                    company_query += f" in {prospect_data.location}"
                company_query += ". Include company size, industry, recent events, and budget indicators."
                
                self._send_enrichment_update(
                    workflow_id=workflow_id,
                    step="Company Research",
                    reasoning=f"🏢 Analyzing company: '{company_query[:100]}...'",
                    status="active"
                )
                
                company_data = await self.web_search.search_company(
                    prospect_data.company_name,
                    {"location": prospect_data.location}
                )
                
                # Send detailed company results
                company_results = company_data.get("results", [])
                company_citations = len(company_data.get("citations", []))
                self._send_enrichment_update(
                    workflow_id=workflow_id,
                    step="Company Analysis Complete",
                    reasoning=f"✅ Analyzed {prospect_data.company_name}: Found {company_citations} sources. Key insights: {company_results[:1] if company_results else 'Basic company information'}",
                    status="complete",
                    data={"company_citations": company_citations, "company_insights": company_results[:1]}
                )
            
            # Step 3: Research event context
            event_query = f"Find event planning information for {prospect_data.name} planning event planning"
            if prospect_data.location:
                event_query += f" in {prospect_data.location}"
            event_query += ". Include event preferences, timeline, budget signals, and social media activity."
            
            self._send_enrichment_update(
                workflow_id=workflow_id,
                step="Event Context Research",
                reasoning=f"🎉 Searching for event signals: '{event_query[:100]}...'",
                status="active"
            )
            
            event_data = await self.web_search.search_event_context({
                "person": prospect_data.name,
                "event_type": "event planning",
                "location": prospect_data.location
            })
            
            # Send detailed event context results
            event_results = event_data.get("results", [])
            event_citations = len(event_data.get("citations", []))
            self._send_enrichment_update(
                workflow_id=workflow_id,
                step="Event Context Complete",
                reasoning=f"✅ Event research complete: {event_citations} sources analyzed. Event signals: {event_results[:1] if event_results else 'No specific event planning activity detected'}",
                status="complete",
                data={"event_citations": event_citations, "event_signals": event_results[:1]}
            )
            
            # Step 4: Analyze with Gemini
            await self._broadcast_reasoning(
                workflow_id,
                "Analyzing research data with Gemini AI..."
            )
            
            analysis = await self._analyze_with_gemini(
                {
                    "person_data": person_data,
                    "company_data": company_data,
                    "event_data": event_data
                },
                prospect_data,
                workflow_id
            )
            
            # Step 5: Create enrichment data
            await self._broadcast_reasoning(
                workflow_id,
                "Building prospect profile..."
            )
            
            enrichment_data = self._create_enrichment_data(
                analysis, person_data, company_data, event_data, workflow_id
            )
            
            # Update state
            state["enrichment_data"] = enrichment_data
            
            # Send final completion updates synchronously to ensure they complete
            self._send_enrichment_update(
                workflow_id=workflow_id,
                step="AI Analysis Complete",
                reasoning="✅ All enrichment processing finished. Ready for next phase.",
                status="fully_complete"
            )
            
            print("🧠 AI Thinking: Enrichment completed successfully")
            
            # Send final completion signal
            self._send_enrichment_update(
                workflow_id=workflow_id,
                step="Enrichment Complete - All Done", 
                reasoning="✅ All enrichment processing finished. Ready for next phase.",
                status="fully_complete"
            )
            
            logger.info(
                "Prospect enrichment completed",
                workflow_id=workflow_id,
                data_sources=len(enrichment_data.data_sources)
            )
            
            return state
            
        except SonarAPIError as e:
            # Sonar API failure - halt processing
            error_msg = f"Sonar API failed: {str(e)}"
            logger.error(error_msg, workflow_id=workflow_id)
            
            await self._broadcast_reasoning(workflow_id, f"Error: {error_msg}")
            
            return StateManager.add_error(
                state, "enricher", "sonar_api_failure", error_msg,
                {"error_type": "critical", "requires_escalation": True}
            )
            
        except Exception as e:
            # Gemini or other critical failure - halt processing
            error_msg = f"Enrichment failed: {str(e)}"
            logger.error(error_msg, workflow_id=workflow_id, error=str(e))
            
            await self._broadcast_reasoning(workflow_id, f"Error: {error_msg}")
            
            return StateManager.add_error(
                state, "enricher", "enrichment_failure", error_msg,
                {"error_type": "critical", "requires_escalation": True}
            )
    
    async def _analyze_with_gemini(
        self,
        research_data: Dict[str, Any],
        prospect_data: ProspectData,
        workflow_id: str
    ) -> Dict[str, Any]:
        """
        Analyze research data with Gemini - simple and focused.
        """
        await self._broadcast_reasoning(
            workflow_id,
            "Analyzing personal and professional background..."
        )
        
        system_prompt = """
        You are an event planning sales analyst. Analyze research data about a prospect
        to understand their event planning needs and create insights for personalized outreach.
        
        Focus on:
        1. Event planning context and needs
        2. Budget indicators
        3. Timeline and urgency
        4. Personalization opportunities
        
        Be direct and actionable.
        """
        
        # Get actual research content
        person_content = research_data.get('person_data', {}).get('results', ['No data'])
        company_content = research_data.get('company_data', {}).get('results', ['No data'])
        event_content = research_data.get('event_data', {}).get('results', ['No data'])
        
        user_message = f"""
        Analyze this prospect for event planning services:
        
        PROSPECT: {prospect_data.name}
        COMPANY: {prospect_data.company_name or 'Individual'}
        LOCATION: {prospect_data.location}
        
        RESEARCH RESULTS:
        
        PERSON DATA:
        {person_content[0][:500] if person_content and person_content[0] else 'No person data found'}
        
        COMPANY DATA:
        {company_content[0][:500] if company_content and company_content[0] else 'No company data found'}
        
        EVENT DATA:
        {event_content[0][:500] if event_content and event_content[0] else 'No event data found'}
        
        IMPORTANT: You MUST return ONLY valid JSON in this exact format:
        {{
            "personal_info": {{
                "role": "extracted role or title",
                "background": "key background information"
            }},
            "company_info": {{
                "industry": "industry type",
                "size": "company size"
            }},
            "event_context": {{
                "event_type": "corporate events or networking",
                "timeline": "event planning timeline",
                "requirements": "event requirements"
            }},
            "ai_insights": {{
                "budget_indicators": "budget signals",
                "outreach_approach": "recommended approach",
                "personalization": "key details to mention"
            }}
        }}
        
        Return ONLY the JSON, no other text.
        """
        
        await self._broadcast_reasoning(
            workflow_id,
            "Extracting event planning insights and requirements..."
        )
        
        try:
            print(f"🤖 Calling Gemini AI for analysis...")
            print(f"   Analyzing {len(research_data)} research data sources")
            
            # Send detailed analysis start update
            data_summary = []
            if research_data.get('person_data', {}).get('results'):
                data_summary.append(f"personal background research")
            if research_data.get('company_data', {}).get('results'):
                data_summary.append(f"company analysis")
            if research_data.get('event_data', {}).get('results'):
                data_summary.append(f"event planning signals")
            
            self._send_enrichment_update(
                workflow_id=workflow_id,
                step="AI Analysis Starting",
                reasoning=f"🤖 Gemini AI analyzing {prospect_data.name}: {', '.join(data_summary)}. Extracting role, budget indicators, event needs, and personalization opportunities...",
                status="active",
                data={"analysis_scope": data_summary}
            )
            
            response = await gemini_service.generate_agent_response(
                system_prompt=system_prompt,
                user_message=user_message
            )
            
            print(f"✅ Gemini analysis completed")
            
            # Parse the analysis to show what AI discovered
            try:
                # Clean the response to remove invalid control characters
                if isinstance(response, str):
                    # Remove control characters that break JSON parsing
                    import re
                    cleaned_response = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', response)
                    parsed_analysis = json.loads(cleaned_response)
                else:
                    parsed_analysis = response
                
                # Extract key insights for the update
                role = parsed_analysis.get("personal_info", {}).get("role", "Unknown role")
                industry = parsed_analysis.get("company_info", {}).get("industry", "Unknown industry")
                event_type = parsed_analysis.get("event_context", {}).get("event_type", "General events")
                budget_signal = parsed_analysis.get("ai_insights", {}).get("budget_indicators", "Budget unknown")
                
                # Send detailed completion update
                self._send_enrichment_update(
                    workflow_id=workflow_id,
                    step="AI Analysis Complete",
                    reasoning=f"✅ AI Analysis Complete! Identified: {role} in {industry}. Event focus: {event_type}. Budget: {budget_signal[:50]}...",
                    status="complete",
                    data={
                        "role_identified": role,
                        "industry": industry,
                        "event_type": event_type,
                        "budget_signal": budget_signal[:100]
                    }
                )
            except:
                # Fallback if parsing fails
                self._send_enrichment_update(
                    workflow_id=workflow_id,
                    step="AI Analysis Complete",
                    reasoning="✅ Gemini AI analysis completed successfully - extracting insights...",
                    status="complete"
                )
            
            # Clean the response - sometimes Gemini adds extra text
            response = response.strip()
            if response.startswith('```json'):
                response = response.replace('```json', '').replace('```', '').strip()
            
            # Try to find JSON in the response
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            if start_idx != -1 and end_idx != -1:
                json_str = response[start_idx:end_idx]
            else:
                json_str = response
            
            analysis = json.loads(json_str)
            
            await self._broadcast_reasoning(
                workflow_id,
                "Identifying personalization opportunities for outreach..."
            )
            
            return analysis
            
        except json.JSONDecodeError as e:
            # Log the actual response for debugging
            print(f"DEBUG: Gemini response was: '{response}'")
            raise Exception(f"Gemini returned invalid JSON: {str(e)}")
        except Exception as e:
            raise Exception(f"Gemini analysis failed: {str(e)}")
    
    def _create_enrichment_data(
        self,
        analysis: Dict[str, Any],
        person_data: Dict[str, Any],
        company_data: Dict[str, Any],
        event_data: Dict[str, Any],
        workflow_id: str
    ) -> EnrichmentData:
        """
        Create simple enrichment data structure with citations.
        """
        # Collect data sources that returned results
        data_sources = []
        all_citations = []
        
        if person_data.get("results"):
            data_sources.append("sonar_person_search")
            # Add citations with source label
            for citation in person_data.get("citations", []):
                citation["source_type"] = "person_search"
                all_citations.append(citation)
        
        if company_data.get("results"):
            data_sources.append("sonar_company_search")
            # Add citations with source label
            for citation in company_data.get("citations", []):
                citation["source_type"] = "company_search"
                all_citations.append(citation)
        
        if event_data.get("results"):
            data_sources.append("sonar_event_search")
            # Add citations with source label
            for citation in event_data.get("citations", []):
                citation["source_type"] = "event_search"
                all_citations.append(citation)
        
        print(f"📚 Total citations collected: {len(all_citations)}")
        
        # Create detailed final summary
        role = analysis.get("personal_info", {}).get("role", "Unknown")
        industry = analysis.get("company_info", {}).get("industry", "Unknown")
        event_type = analysis.get("event_context", {}).get("event_type", "General events")
        budget_indicators = analysis.get("ai_insights", {}).get("budget_indicators", "Unknown budget")
        outreach_approach = analysis.get("ai_insights", {}).get("outreach_approach", "Standard approach")
        
        # Send comprehensive final update
        self._send_enrichment_update(
            workflow_id=workflow_id,
            step="Enrichment Complete",
            reasoning=f"🎉 Complete! Profile: {role} | Industry: {industry} | Events: {event_type} | Budget: {budget_indicators[:30]}... | Strategy: {outreach_approach[:40]}... | Sources: {len(all_citations)} citations",
            status="complete",
            data={
                "citations_count": len(all_citations),
                "profile_summary": {
                    "role": role,
                    "industry": industry,
                    "event_type": event_type,
                    "budget_indicators": budget_indicators,
                    "outreach_approach": outreach_approach
                },
                "data_sources": data_sources
            }
        )
        
        return EnrichmentData(
            personal_info=analysis.get("personal_info", {}),
            company_info=analysis.get("company_info", {}),
            event_context=analysis.get("event_context", {}),
            ai_insights=analysis.get("ai_insights", {}),
            data_sources=data_sources,
            citations=all_citations,
            last_enriched=datetime.now()
        )
    
    async def _broadcast_reasoning(self, workflow_id: str, reasoning: str):
        """
        Broadcast AI reasoning to frontend via enrichment viewer callback.
        """
        # Always print reasoning for visibility during testing
        print(f"🧠 AI Thinking: {reasoning}")
        
        # Send to enrichment viewer
        self._send_enrichment_update(
            workflow_id=workflow_id,
            step="AI Analysis",
            reasoning=reasoning,
            status="active"
        )
        
        # Also send to orchestrator for general workflow updates (if available)
        if self.orchestrator:
            try:
                await self.orchestrator._broadcast_workflow_event(
                    workflow_id,
                    "enrichment_reasoning",
                    {
                        "reasoning": reasoning,
                        "agent": "enrichment",
                        "timestamp": datetime.now().isoformat()
                    }
                )
            except Exception as e:
                # WebSocket failure is not critical
                logger.warning(
                    "Failed to broadcast reasoning",
                    workflow_id=workflow_id,
                    error=str(e)
                )
    
    async def close(self):
        """Cleanup resources"""
        await self.web_search.close()
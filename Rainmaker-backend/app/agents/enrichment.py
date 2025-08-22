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
from app.services.embedding_service import embedding_service
from app.mcp.web_search import WebSearchMCP, SonarAPIError
from app.db.session import SessionLocal
from sqlalchemy.orm import Session

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
        update_data = {
            "type": "enrichment_update",
            "workflow_id": workflow_id,
            "step": step,
            "reasoning": reasoning,
            "status": status,
            "timestamp": datetime.now().isoformat()
        }
        
        if data:
            # Deep copy and convert any slices to lists
            import copy
            data_copy = copy.deepcopy(data)
            for key, value in data_copy.items():
                if isinstance(value, slice):
                    # This is unlikely, but as a safeguard
                    data_copy[key] = list(range(value.start, value.stop, value.step or 1))
                elif isinstance(value, list):
                    # Ensure list items are serializable (no slices inside)
                    data_copy[key] = [list(v) if isinstance(v, slice) else v for v in value]

            update_data["data"] = data_copy
        
        # Always print for debugging
        print(f"🔄 ENRICHMENT UPDATE: {step} | {reasoning[:100]}...")
        
        if enrichment_viewer_callback:
            try:
                enrichment_viewer_callback(update_data)
                print(f"✅ UPDATE SENT TO FRONTEND via callback for workflow: {workflow_id}")
                logger.debug("✅ Enrichment update sent", step=step, workflow_id=workflow_id)
            except Exception as e:
                print(f"❌ CALLBACK FAILED: {str(e)}")
                logger.warning("❌ Failed to send enrichment update", error=str(e))
        else:
            print("⚠️  NO CALLBACK SET - Updates not reaching frontend!")
            logger.warning("⚠️ No enrichment viewer callback set - updates not being sent to frontend")
    
    async def enrich_prospect(self, state: RainmakerState) -> RainmakerState:
        """
        Enhanced enrichment method with vector storage and semantic search.
        
        Phase 1: Discovery - Use Sonar to gather research data
        Phase 2: Storage - Store all research data with vector embeddings in TiDB
        Phase 3: Analysis - Use semantic search to find relevant insights
        Phase 4: Synthesis - Generate enhanced analysis with deeper insights
        
        Args:
            state: RainmakerState from workflow
            
        Returns:
            Updated state with enrichment data
        """
        workflow_id = state["workflow_id"]
        prospect_data = state["prospect_data"]
        
        logger.info(
            "Starting enhanced prospect enrichment with vector analysis",
            workflow_id=workflow_id,
            prospect_name=prospect_data.name
        )
        
        # Get database session for vector storage
        db = SessionLocal()
        
        try:
            # ENSURE PROSPECT EXISTS IN DATABASE FIRST
            if not prospect_data.id:
                self._send_enrichment_update(
                    workflow_id=workflow_id,
                    step="Creating Prospect Record",
                    reasoning=f"📝 Creating database record for {prospect_data.name}...",
                    status="active"
                )
                
                # Create prospect in database first
                from app.db.models import Prospect, ProspectType
                db_prospect = Prospect(
                    prospect_type=ProspectType.INDIVIDUAL if prospect_data.prospect_type == "individual" else ProspectType.COMPANY,
                    name=prospect_data.name,
                    email=prospect_data.email,
                    phone=prospect_data.phone,
                    company_name=prospect_data.company_name,
                    location=prospect_data.location,
                    source=prospect_data.source,
                    status=prospect_data.status,
                    lead_score=prospect_data.lead_score,
                    assigned_to=prospect_data.assigned_to
                )
                
                db.add(db_prospect)
                db.commit()
                db.refresh(db_prospect)
                
                # Update prospect_data with the database ID
                prospect_data.id = db_prospect.id
                
                logger.info("Created prospect in database", prospect_id=db_prospect.id, name=prospect_data.name)
            
            # PHASE 1: DISCOVERY - Research person with Sonar
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
            
            # Send detailed results with actual citations
            person_results = person_data.get("results", [])
            person_citations = person_data.get("citations", [])
            citations_found = len(person_citations)
            
            # PHASE 2: STORAGE - Store person research with vectors
            self._send_enrichment_update(
                workflow_id=workflow_id,
                step="Storing Person Research Data",
                reasoning=f"💾 Storing {citations_found} research sources with vector embeddings for deep analysis...",
                status="active"
            )
            
            # Store each citation's content with vector embeddings
            person_stored_records = []
            for citation in person_citations:
                if citation.get("url") and person_results:
                    # Use the first result as content for this citation
                    content = person_results[0] if person_results else ""
                    if content:
                        # Create progress callback for real-time updates
                        def progress_callback(message):
                            self._send_enrichment_update(
                                workflow_id=workflow_id,
                                step="Vector Embedding Creation",
                                reasoning=message,
                                status="active"
                            )
                        
                        stored = await embedding_service.store_prospect_research(
                            db=db,
                            prospect_id=prospect_data.id,
                            workflow_id=workflow_id,
                            source_url=citation.get("url", ""),
                            source_title=citation.get("title", ""),
                            source_type="person_search",
                            search_query=search_query,
                            content=content,
                            progress_callback=progress_callback
                        )
                        person_stored_records.extend(stored)
            
            self._send_enrichment_update(
                workflow_id=workflow_id,
                step="Person Research Complete",
                reasoning=f"✅ Found {citations_found} sources about {prospect_data.name}. Stored {len(person_stored_records)} research chunks with vector embeddings.",
                status="complete",
                data={
                    "citations_count": citations_found, 
                    "citations": person_citations,
                    "stored_chunks": len(person_stored_records),
                    "results_preview": person_results[:2]
                }
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
                
                # Store company research with vectors
                company_results = company_data.get("results", [])
                company_citations_array = company_data.get("citations", [])
                company_citations_count = len(company_citations_array)
                
                # Store company research data
                company_stored_records = []
                for citation in company_citations_array:
                    if citation.get("url") and company_results:
                        content = company_results[0] if company_results else ""
                        if content:
                            stored = await embedding_service.store_prospect_research(
                                db=db,
                                prospect_id=prospect_data.id,
                                workflow_id=workflow_id,
                                source_url=citation.get("url", ""),
                                source_title=citation.get("title", ""),
                                source_type="company_search",
                                search_query=company_query,
                                content=content
                            )
                            company_stored_records.extend(stored)
                
                self._send_enrichment_update(
                    workflow_id=workflow_id,
                    step="Company Analysis Complete",
                    reasoning=f"✅ Analyzed {prospect_data.company_name}: Found {company_citations_count} sources. Stored {len(company_stored_records)} company research chunks.",
                    status="complete",
                    data={
                        "company_citations": company_citations_count, 
                        "citations": company_citations_array,
                        "stored_chunks": len(company_stored_records),
                        "company_insights": company_results[:1]
                    }
                )
            else:
                company_stored_records = []
            
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
            
            # Store event research with vectors
            event_results = event_data.get("results", [])
            event_citations_array = event_data.get("citations", [])
            event_citations_count = len(event_citations_array)
            
            # Store event research data
            event_stored_records = []
            for citation in event_citations_array:
                if citation.get("url") and event_results:
                    content = event_results[0] if event_results else ""
                    if content:
                        stored = await embedding_service.store_prospect_research(
                            db=db,
                            prospect_id=prospect_data.id,
                            workflow_id=workflow_id,
                            source_url=citation.get("url", ""),
                            source_title=citation.get("title", ""),
                            source_type="event_search",
                            search_query=event_query,
                            content=content
                        )
                        event_stored_records.extend(stored)
            
            self._send_enrichment_update(
                workflow_id=workflow_id,
                step="Event Context Complete",
                reasoning=f"✅ Event research complete: {event_citations_count} sources analyzed. Stored {len(event_stored_records)} event research chunks.",
                status="complete",
                data={
                    "event_citations": event_citations_count, 
                    "citations": event_citations_array,
                    "stored_chunks": len(event_stored_records),
                    "event_signals": event_results[:1]
                }
            )
            
            # PHASE 3: SEMANTIC ANALYSIS - Use vector search for deep insights
            self._send_enrichment_update(
                workflow_id=workflow_id,
                step="Deep Analysis with Vector Search",
                reasoning=f"🔍 Performing semantic analysis across all {len(person_stored_records + company_stored_records + event_stored_records)} research chunks...",
                status="active"
            )
            
            # Perform targeted semantic searches for key insights
            vector_insights = await self._perform_semantic_analysis(
                db, prospect_data, workflow_id
            )
            
            # Step 4: Enhanced Analysis with Gemini + Vector Insights
            await self._broadcast_reasoning(
                workflow_id,
                "Synthesizing research data with AI analysis and vector insights..."
            )
            
            analysis = await self._analyze_with_gemini_and_vectors(
                {
                    "person_data": person_data,
                    "company_data": company_data,
                    "event_data": event_data,
                    "vector_insights": vector_insights.get("vector_insights", {}),
                    "research_summary": vector_insights.get("research_summary", {})
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
        finally:
            # Always close database session
            db.close()
    
    
    
    
    
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
                
                # Extract key insights for the update with safe string handling
                role = str(parsed_analysis.get("personal_info", {}).get("role", "Unknown role"))
                industry = str(parsed_analysis.get("company_info", {}).get("industry", "Unknown industry"))
                event_type = str(parsed_analysis.get("event_context", {}).get("event_type", "General events"))
                budget_signal = str(parsed_analysis.get("ai_insights", {}).get("budget_indicators", "Budget unknown"))
                
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
        
        # Create detailed final summary with safe string handling
        role = str(analysis.get("personal_info", {}).get("role", "Unknown"))
        industry = str(analysis.get("company_info", {}).get("industry", "Unknown"))
        event_type = str(analysis.get("event_context", {}).get("event_type", "General events"))
        budget_indicators = str(analysis.get("ai_insights", {}).get("budget_indicators", "Unknown budget"))
        outreach_approach = str(analysis.get("ai_insights", {}).get("outreach_approach", "Standard approach"))
        
        # Send comprehensive final update
        self._send_enrichment_update(
            workflow_id=workflow_id,
            step="Enrichment Complete",
            reasoning=f"🎉 Complete! Profile: {role} | Industry: {industry} | Events: {event_type} | Budget: {budget_indicators[:30]}... | Strategy: {outreach_approach[:40]}... | Sources: {len(all_citations)} citations",
            status="complete",
            data={
                "citations_count": len(all_citations),
                "citations": all_citations,  # Add the actual citations array
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
    
    async def _perform_semantic_analysis(
        self,
        db: Session,
        prospect_data: ProspectData,
        workflow_id: str
    ) -> Dict[str, Any]:
        """
        Perform semantic analysis using vector search across all stored research data.
        This creates targeted insights that go beyond surface-level information.
        """
        try:
            prospect_id = prospect_data.id
            
            # Define strategic search queries for deep insights
            search_queries = [
                "recent business investments and partnerships",
                "event planning budget and spending indicators", 
                "corporate event history and preferences",
                "business expansion and growth signals",
                "social media activity and engagement patterns",
                "industry connections and networking activity",
                "recent press coverage and media mentions",
                "company culture and values",
                "decision making process and timeline"
            ]
            
            vector_insights = {}
            
            for i, query in enumerate(search_queries, 1):
                self._send_enrichment_update(
                    workflow_id=workflow_id,
                    step="Semantic Query Processing",
                    reasoning=f"🔍 Query {i}/{len(search_queries)}: Searching for '{query}' across stored research...",
                    status="active"
                )
                
                # Perform semantic search with detailed progress
                results = await embedding_service.search_similar_content(
                    db_session=db,
                    query_text=query,
                    prospect_id=prospect_id,
                    limit=3
                )
                
                # Filter results by similarity threshold manually since search_similar_content doesn't filter
                high_similarity_results = [r for r in results if r['similarity_score'] > 0.6]
                
                # Show what was found
                if high_similarity_results:
                    top_match = high_similarity_results[0]
                    self._send_enrichment_update(
                        workflow_id=workflow_id,
                        step="Semantic Match Found",
                        reasoning=f"✅ Found {len(high_similarity_results)} matches for '{query}' | Top match: '{top_match['content'][:60]}...' (similarity: {top_match['similarity_score']:.2f})",
                        status="active"
                    )
                else:
                    self._send_enrichment_update(
                        workflow_id=workflow_id,
                        step="Semantic Search Complete",
                        reasoning=f"⚠️  No strong matches found for '{query}' (threshold: 0.6)",
                        status="active"
                    )
                
                if high_similarity_results:
                    # Extract key insights from search results
                    insights = []
                    for result in high_similarity_results:
                        insights.append({
                            "content": result["content"][:300] + "..." if len(result["content"]) > 300 else result["content"],
                            "source_type": result["source_type"],
                            "similarity": result["similarity_score"],
                            "source_url": result["source_url"]
                        })
                    
                    vector_insights[query.replace(" ", "_")] = insights
                
                # Small delay between searches
                await asyncio.sleep(0.2)
            
            # Calculate research summary locally
            total_insights = sum(len(v) for v in vector_insights.values())
            insight_categories = len([k for k, v in vector_insights.items() if v])
            
            self._send_enrichment_update(
                workflow_id=workflow_id,
                step="Semantic Analysis Complete", 
                reasoning=f"✅ Completed semantic analysis across {len(search_queries)} query types. Found {insight_categories} insight categories with {total_insights} total insights.",
                status="complete",
                data={
                    "insight_categories": insight_categories,
                    "total_insights": total_insights,
                    "queries_processed": len(search_queries)
                }
            )
            
            return {
                "vector_insights": vector_insights,
                "research_summary": {"total_insights": total_insights, "categories": insight_categories}
            }
            
        except Exception as e:
            logger.error(f"Semantic analysis failed: {str(e)}")
            return {"error": str(e), "vector_insights": {}}
    
    async def _analyze_with_gemini_and_vectors(
        self,
        research_data: Dict[str, Any],
        prospect_data: ProspectData,
        workflow_id: str
    ) -> Dict[str, Any]:
        """
        Enhanced analysis using both traditional research data and vector insights.
        """
        await self._broadcast_reasoning(
            workflow_id,
            "Integrating vector search insights with traditional research analysis..."
        )
        
        # Get vector insights
        vector_insights = research_data.get("vector_insights", {})
        research_summary = research_data.get("research_summary", {})
        
        system_prompt = """
        You are an advanced event planning sales analyst with access to deep research insights.
        Analyze comprehensive prospect data including semantic search insights to create 
        highly personalized outreach recommendations.
        
        Focus on:
        1. Deep business context and recent activity
        2. Specific event planning needs and budget indicators
        3. Decision-making patterns and timeline
        4. Personalization opportunities beyond basic demographics
        5. Strategic approach recommendations
        
        Be specific and actionable with concrete details from the research.
        """
        
        # Build comprehensive research context
        person_content = research_data.get('person_data', {}).get('results', ['No data'])
        company_content = research_data.get('company_data', {}).get('results', ['No data'])
        event_content = research_data.get('event_data', {}).get('results', ['No data'])
        
        # Add vector insights to the analysis
        vector_context = ""
        if vector_insights:
            vector_context = "\n\nDEEP INSIGHTS FROM SEMANTIC ANALYSIS:\n"
            for category, insights in vector_insights.items():
                if insights:
                    vector_context += f"\n{category.replace('_', ' ').title()}:\n"
                    for insight in insights[:2]:  # Top 2 insights per category
                        vector_context += f"- {insight['content'][:200]}... (Source: {insight['source_type']}, Relevance: {insight['similarity']:.2f})\n"
        
        research_stats = f"\nRESEARCH SCOPE: {research_summary.get('total_insights', 0)} insights found across {research_summary.get('categories', 0)} categories"
        
        user_message = f"""
        Analyze this prospect for event planning services:
        
        PROSPECT: {prospect_data.name}
        COMPANY: {prospect_data.company_name or 'Individual'}
        LOCATION: {prospect_data.location}
        
        TRADITIONAL RESEARCH:
        
        PERSON DATA:
        {person_content[0][:500] if person_content and person_content[0] else 'No person data found'}
        
        COMPANY DATA:
        {company_content[0][:500] if company_content and company_content[0] else 'No company data found'}
        
        EVENT DATA:
        {event_content[0][:500] if event_content and event_content[0] else 'No event data found'}
        
        {vector_context}
        
        {research_stats}
        
        IMPORTANT: You MUST return ONLY valid JSON in this exact format:
        {{
            "personal_info": {{
                "role": "extracted role or title",
                "background": "key background information",
                "recent_activity": "recent business activity from deep research"
            }},
            "company_info": {{
                "industry": "industry type",
                "size": "company size",
                "recent_developments": "recent company developments"
            }},
            "event_context": {{
                "event_type": "corporate events or networking",
                "timeline": "event planning timeline",
                "requirements": "event requirements",
                "budget_signals": "specific budget indicators found"
            }},
            "ai_insights": {{
                "key_opportunities": "specific opportunities identified",
                "outreach_approach": "recommended approach based on deep insights",
                "personalization": "specific details to mention in outreach",
                "decision_factors": "key factors that influence their decisions"
            }}
        }}
        
        Return ONLY the JSON, no other text.
        """
        
        try:
            self._send_enrichment_update(
                workflow_id=workflow_id,
                step="Enhanced AI Analysis",
                reasoning=f"🤖 Gemini AI analyzing {prospect_data.name} with {len(vector_insights)} deep insight categories and {research_summary.get('total_insights', 0)} insights...",
                status="active"
            )
            
            response = await gemini_service.generate_agent_response(
                system_prompt=system_prompt,
                user_message=user_message
            )
            
            # Parse and validate the response
            if isinstance(response, str):
                import re
                cleaned_response = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', response)
            else:
                cleaned_response = json.dumps(response)
            
            # Extract JSON from response
            response = cleaned_response.strip()
            if response.startswith('```json'):
                response = response.replace('```json', '').replace('```', '').strip()
            
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            if start_idx != -1 and end_idx != -1:
                json_str = response[start_idx:end_idx]
            else:
                json_str = response
            
            analysis = json.loads(json_str)
            
            # Extract key insights for update with safe string handling
            role = str(analysis.get("personal_info", {}).get("role", "Unknown role"))
            recent_activity = str(analysis.get("personal_info", {}).get("recent_activity", "No recent activity"))
            key_opportunities = str(analysis.get("ai_insights", {}).get("key_opportunities", "Standard opportunities"))
            
            self._send_enrichment_update(
                workflow_id=workflow_id,
                step="Enhanced AI Analysis Complete",
                reasoning=f"✅ Deep Analysis Complete! Role: {role}. Recent activity: {recent_activity[:50]}... Key opportunities: {key_opportunities[:50]}...",
                status="complete",
                data={
                    "analysis_depth": "enhanced_with_vectors",
                    "insights_used": len(vector_insights),
                    "research_insights": research_summary.get("total_insights", 0)
                }
            )
            
            return analysis
            
        except json.JSONDecodeError as e:
            logger.error(f"Enhanced Gemini analysis returned invalid JSON: {str(e)}")
            # Fallback to basic analysis
            return await self._analyze_with_gemini(research_data, prospect_data, workflow_id)
        except Exception as e:
            logger.error(f"Enhanced Gemini analysis failed: {str(e)}")
            # Fallback to basic analysis
            return await self._analyze_with_gemini(research_data, prospect_data, workflow_id)

    async def close(self):
        """Cleanup resources"""
        await self.web_search.close()
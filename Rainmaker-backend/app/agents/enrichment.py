"""
Advanced Enrichment Agent powered by GPT-4 with MCP integration.

This agent performs deep prospect enrichment using multi-source data correlation,
social media analysis, and intelligent data synthesis to create comprehensive
prospect profiles for personalized outreach.
"""

import asyncio
import json
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import structlog

from app.core.state import RainmakerState, EnrichmentData, ProspectData
from app.core.config import settings
from app.services.openai_service import openai_service
from app.mcp.enrichment import enrichment_mcp
from app.mcp.web_search import web_search_mcp
from app.mcp.database import database_mcp
from app.db.models import ProspectStatus

logger = structlog.get_logger(__name__)

try:
    from app.mcp.linkedin import linkedin_mcp
    LINKEDIN_AVAILABLE = True
except ImportError:
    logger.warning("LinkedIn MCP not available - LinkedIn enrichment disabled")
    linkedin_mcp = None
    LINKEDIN_AVAILABLE = False


@dataclass
class EnrichmentSource:
    """Individual data source for enrichment"""
    source_name: str
    data: Dict[str, Any]
    confidence: float  # 0.0 to 1.0
    freshness_score: float  # 0.0 to 1.0 (how recent the data is)
    completeness_score: float  # 0.0 to 1.0 (how complete the data is)
    last_updated: datetime = field(default_factory=datetime.now)


@dataclass
class EventPreferenceSignal:
    """Signal indicating event preferences and planning behavior"""
    signal_type: str  # 'venue_preference', 'budget_indicator', 'style_preference', etc.
    signal_value: str
    confidence: float
    source: str
    context: str = ""


@dataclass
class BudgetAnalysis:
    """Comprehensive budget analysis for prospect"""
    estimated_range: Optional[tuple] = None  # (min, max)
    confidence_level: str = "unknown"  # low/medium/high/unknown
    indicators: List[str] = field(default_factory=list)
    spending_patterns: Dict[str, Any] = field(default_factory=dict)
    budget_category: str = "unknown"  # economy/mid-range/premium/luxury


class EnrichmentAgent:
    """
    Advanced Enrichment Agent that creates comprehensive prospect profiles.
    
    Performs multi-source data gathering, intelligent data correlation,
    and GPT-4 powered analysis to build detailed prospect insights.
    """
    
    def __init__(self):
        self.openai_service = openai_service
        self.max_concurrent_enrichments = 3
        self.cache_duration_hours = 24
        self.min_confidence_threshold = 0.5
        
    async def enrich_prospect(self, state: RainmakerState) -> RainmakerState:
        """
        Main enrichment orchestration method that builds comprehensive prospect profile.
        """
        logger.info("Starting advanced prospect enrichment", workflow_id=state.get("workflow_id"))
        
        try:
            prospect_data = state["prospect_data"]
            
            # Multi-source data gathering
            enrichment_sources = await self._gather_enrichment_data(prospect_data)
            
            # Data correlation and synthesis
            synthesized_data = await self._synthesize_enrichment_data(enrichment_sources, prospect_data)
            
            # Event preference analysis
            event_preferences = await self._analyze_event_preferences(enrichment_sources, prospect_data)
            
            # Budget capacity analysis
            budget_analysis = await self._analyze_budget_capacity(enrichment_sources, prospect_data)
            
            # Social media and online presence analysis
            online_presence = await self._analyze_online_presence(enrichment_sources, prospect_data)
            
            # Final GPT-4 powered profile synthesis
            enriched_profile = await self._synthesize_final_profile(
                synthesized_data, event_preferences, budget_analysis, online_presence, prospect_data
            )
            
            # Create comprehensive enrichment data
            enrichment_data = self._create_enrichment_data(enriched_profile, enrichment_sources)
            
            # Update prospect in database
            await self._update_prospect_with_enrichment(prospect_data, enrichment_data)
            
            # Update state
            state["enrichment_data"] = enrichment_data
            
            logger.info(
                "Prospect enrichment completed",
                workflow_id=state.get("workflow_id"),
                confidence_score=enrichment_data.confidence_score,
                data_sources=len(enrichment_sources)
            )
            
            return state
            
        except Exception as e:
            logger.error("Prospect enrichment failed", error=str(e), workflow_id=state.get("workflow_id"))
            raise
    
    async def _gather_enrichment_data(self, prospect_data: ProspectData) -> List[EnrichmentSource]:
        """Gather enrichment data from multiple sources concurrently"""
        enrichment_tasks = []
        
        # Company/professional data enrichment
        if prospect_data.email or prospect_data.company_name:
            enrichment_tasks.append(self._enrich_from_clearbit(prospect_data))
        
        # Social media and web presence
        enrichment_tasks.append(self._enrich_from_web_search(prospect_data))
        
        # LinkedIn professional data
        if settings.LINKEDIN_API_KEY:
            enrichment_tasks.append(self._enrich_from_linkedin(prospect_data))
        
        # Execute enrichments concurrently
        semaphore = asyncio.Semaphore(self.max_concurrent_enrichments)
        
        async def bounded_enrichment(task):
            async with semaphore:
                return await task
        
        results = await asyncio.gather(
            *[bounded_enrichment(task) for task in enrichment_tasks],
            return_exceptions=True
        )
        
        # Filter and validate results
        enrichment_sources = []
        for result in results:
            if isinstance(result, Exception):
                logger.warning("Enrichment source failed", error=str(result))
                continue
            if isinstance(result, EnrichmentSource) and result.confidence > 0.1:
                enrichment_sources.append(result)
        
        return enrichment_sources
    
    async def _enrich_from_clearbit(self, prospect_data: ProspectData) -> EnrichmentSource:
        """Enrich prospect data using Clearbit API"""
        try:
            # Person enrichment
            person_result = await enrichment_mcp.server.call_tool(
                "enrich_person",
                {
                    "email": prospect_data.email,
                    "name": prospect_data.name,
                    "company": prospect_data.company_name
                }
            )
            
            person_data = {}
            if not person_result.isError:
                person_data = json.loads(person_result.content[0].text)
            
            # Company enrichment if applicable
            company_data = {}
            if prospect_data.company_name:
                company_result = await enrichment_mcp.server.call_tool(
                    "enrich_company",
                    {
                        "company_name": prospect_data.company_name
                    }
                )
                
                if not company_result.isError:
                    company_data = json.loads(company_result.content[0].text)
            
            # Calculate confidence based on data completeness
            confidence = self._calculate_clearbit_confidence(person_data, company_data)
            
            return EnrichmentSource(
                source_name="clearbit",
                data={
                    "person": person_data,
                    "company": company_data
                },
                confidence=confidence,
                freshness_score=0.9,  # Clearbit data is generally fresh
                completeness_score=confidence
            )
            
        except Exception as e:
            logger.error("Clearbit enrichment failed", error=str(e))
            return EnrichmentSource(
                source_name="clearbit",
                data={},
                confidence=0.0,
                freshness_score=0.0,
                completeness_score=0.0
            )
    
    async def _enrich_from_web_search(self, prospect_data: ProspectData) -> EnrichmentSource:
        """Enrich prospect data using web search"""
        try:
            search_queries = self._build_enrichment_search_queries(prospect_data)
            all_search_data = []
            
            for query in search_queries:
                result = await web_search_mcp.server.call_tool(
                    "search_event_signals",
                    {
                        "keywords": query["keywords"],
                        "location": prospect_data.location,
                        "max_results": 10
                    }
                )
                
                if not result.isError:
                    search_data = json.loads(result.content[0].text)
                    all_search_data.extend(search_data.get("results", []))
                
                # Rate limiting
                await asyncio.sleep(0.3)
            
            # Analyze search results for enrichment insights
            enrichment_insights = await self._analyze_search_results_for_insights(all_search_data, prospect_data)
            
            confidence = min(len(all_search_data) / 20.0, 1.0)  # More results = higher confidence
            
            return EnrichmentSource(
                source_name="web_search",
                data={
                    "search_results": all_search_data,
                    "insights": enrichment_insights
                },
                confidence=confidence,
                freshness_score=0.8,
                completeness_score=confidence * 0.7
            )
            
        except Exception as e:
            logger.error("Web search enrichment failed", error=str(e))
            return EnrichmentSource(
                source_name="web_search",
                data={},
                confidence=0.0,
                freshness_score=0.0,
                completeness_score=0.0
            )
    
    async def _enrich_from_linkedin(self, prospect_data: ProspectData) -> EnrichmentSource:
        """Enrich prospect data using LinkedIn"""
        try:
            # Search for LinkedIn profile
            profile_result = await linkedin_mcp.server.call_tool(
                "search_profiles",
                {
                    "name": prospect_data.name,
                    "company": prospect_data.company_name,
                    "location": prospect_data.location
                }
            )
            
            linkedin_data = {}
            if not profile_result.isError:
                linkedin_data = json.loads(profile_result.content[0].text)
            
            # Get recent posts/activity if profile found
            activity_data = {}
            if linkedin_data.get("profiles"):
                profile = linkedin_data["profiles"][0]
                activity_result = await linkedin_mcp.server.call_tool(
                    "get_profile_activity",
                    {"profile_id": profile.get("id")}
                )
                
                if not activity_result.isError:
                    activity_data = json.loads(activity_result.content[0].text)
            
            confidence = 0.8 if linkedin_data.get("profiles") else 0.2
            
            return EnrichmentSource(
                source_name="linkedin",
                data={
                    "profile": linkedin_data,
                    "activity": activity_data
                },
                confidence=confidence,
                freshness_score=0.9,
                completeness_score=confidence
            )
            
        except Exception as e:
            logger.error("LinkedIn enrichment failed", error=str(e))
            return EnrichmentSource(
                source_name="linkedin",
                data={},
                confidence=0.0,
                freshness_score=0.0,
                completeness_score=0.0
            )
    
    def _build_enrichment_search_queries(self, prospect_data: ProspectData) -> List[Dict]:
        """Build search queries for prospect enrichment"""
        queries = []
        
        # Personal/individual searches
        if prospect_data.name and prospect_data.name != "Unknown":
            queries.extend([
                {
                    "keywords": [prospect_data.name, "event planning", "party planning"],
                    "purpose": "event_planning_history"
                },
                {
                    "keywords": [prospect_data.name, "wedding", "engagement"],
                    "purpose": "personal_events"
                },
                {
                    "keywords": [prospect_data.name, "birthday", "anniversary", "celebration"],
                    "purpose": "celebration_history"
                }
            ])
        
        # Company/corporate searches
        if prospect_data.company_name:
            queries.extend([
                {
                    "keywords": [prospect_data.company_name, "corporate events", "company party"],
                    "purpose": "corporate_event_history"
                },
                {
                    "keywords": [prospect_data.company_name, "team building", "company retreat"],
                    "purpose": "corporate_activities"
                }
            ])
        
        # Location-specific searches
        if prospect_data.location:
            queries.append({
                "keywords": [prospect_data.name, prospect_data.location, "local events"],
                "purpose": "local_event_presence"
            })
        
        return queries
    
    async def _analyze_search_results_for_insights(self, search_results: List[Dict], prospect_data: ProspectData) -> Dict[str, Any]:
        """Use GPT-4 to analyze search results for enrichment insights"""
        if not search_results:
            return {}
        
        # Prepare search data for analysis
        search_snippets = []
        for result in search_results[:10]:  # Analyze top 10 results
            search_snippets.append({
                "title": result.get("title", ""),
                "snippet": result.get("snippet", ""),
                "url": result.get("url", "")
            })
        
        analysis_prompt = f"""
        Analyze these search results for prospect "{prospect_data.name}" to extract event planning insights:

        SEARCH RESULTS:
        {json.dumps(search_snippets, indent=2)}

        PROSPECT CONTEXT:
        - Name: {prospect_data.name}
        - Company: {prospect_data.company_name}
        - Location: {prospect_data.location}

        Extract and provide:
        1. Event planning history or experience
        2. Style preferences (formal, casual, modern, traditional, etc.)
        3. Budget indicators (mentions of spending, venue types, etc.)
        4. Social activity level (active on social media, community involvement)
        5. Professional background relevant to events
        6. Personal life stage indicators (married, family, age estimates)
        7. Preferred venues or suppliers mentioned
        8. Event frequency patterns

        Return as structured JSON with confidence scores for each insight.
        """
        
        try:
            response = await self.openai_service.generate_agent_response(
                system_prompt="You are an expert data analyst specializing in prospect research for event planning businesses.",
                user_message=analysis_prompt,
                model="gpt-4"
            )
            
            return json.loads(response)
            
        except Exception as e:
            logger.warning("Search result analysis failed", error=str(e))
            return {}
    
    async def _synthesize_enrichment_data(self, sources: List[EnrichmentSource], prospect_data: ProspectData) -> Dict[str, Any]:
        """Synthesize data from multiple enrichment sources"""
        if not sources:
            return {}
        
        # Prepare source data for GPT-4 analysis
        source_summaries = []
        for source in sources:
            if source.confidence > self.min_confidence_threshold:
                source_summaries.append({
                    "source": source.source_name,
                    "confidence": source.confidence,
                    "key_data": self._extract_key_data_from_source(source),
                    "freshness": source.freshness_score
                })
        
        synthesis_prompt = f"""
        Synthesize enrichment data from multiple sources for prospect "{prospect_data.name}":

        DATA SOURCES:
        {json.dumps(source_summaries, indent=2)}

        SYNTHESIS OBJECTIVES:
        1. Resolve conflicts between sources (weight by confidence and freshness)
        2. Fill data gaps using cross-source inference
        3. Identify the most reliable information for each data point
        4. Flag uncertain or conflicting information
        5. Create a unified prospect profile

        Provide synthesized data with:
        - Consolidated contact information
        - Professional background and role
        - Company information and context
        - Personal demographics (age range, family status, etc.)
        - Event planning experience or involvement
        - Geographic and cultural context
        - Technology usage and digital presence

        Return as structured JSON with confidence scores for each data point.
        """
        
        try:
            response = await self.openai_service.generate_agent_response(
                system_prompt="You are an expert data synthesis analyst. Create accurate, unified prospect profiles from multiple data sources.",
                user_message=synthesis_prompt,
                model="gpt-4"
            )
            
            return json.loads(response)
            
        except Exception as e:
            logger.warning("Data synthesis failed", error=str(e))
            return self._fallback_data_synthesis(sources)
    
    async def _analyze_event_preferences(self, sources: List[EnrichmentSource], prospect_data: ProspectData) -> Dict[str, Any]:
        """Analyze event preferences from enrichment sources"""
        preference_signals = []
        
        # Extract preference signals from each source
        for source in sources:
            if source.source_name == "web_search":
                signals = self._extract_preference_signals_from_web(source.data)
                preference_signals.extend(signals)
            elif source.source_name == "linkedin":
                signals = self._extract_preference_signals_from_linkedin(source.data)
                preference_signals.extend(signals)
            elif source.source_name == "clearbit":
                signals = self._extract_preference_signals_from_clearbit(source.data)
                preference_signals.extend(signals)
        
        if not preference_signals:
            return {"preferences": {}, "confidence": 0.0}
        
        # GPT-4 analysis of preference signals
        preferences_prompt = f"""
        Analyze event preference signals for prospect "{prospect_data.name}":

        PREFERENCE SIGNALS:
        {json.dumps([{
            "type": s.signal_type,
            "value": s.signal_value,
            "confidence": s.confidence,
            "source": s.source,
            "context": s.context
        } for s in preference_signals], indent=2)}

        Determine:
        1. Venue preferences (indoor/outdoor, urban/rural, formal/casual)
        2. Style preferences (modern, traditional, rustic, elegant, etc.)
        3. Event size preferences (intimate, medium, large, massive)
        4. Service level expectations (DIY, partial planning, full service)
        5. Communication preferences (email, phone, text, in-person)
        6. Decision-making style (quick, deliberate, collaborative, independent)
        7. Price sensitivity indicators
        8. Special requirements or considerations

        Return structured preferences with confidence scores.
        """
        
        try:
            response = await self.openai_service.generate_agent_response(
                system_prompt="You are an expert event planning consultant. Analyze client preferences to optimize service delivery.",
                user_message=preferences_prompt,
                model="gpt-4"
            )
            
            return json.loads(response)
            
        except Exception as e:
            logger.warning("Preference analysis failed", error=str(e))
            return self._fallback_preference_analysis(preference_signals)
    
    async def _analyze_budget_capacity(self, sources: List[EnrichmentSource], prospect_data: ProspectData) -> BudgetAnalysis:
        """Analyze budget capacity from enrichment sources"""
        budget_indicators = []
        
        # Extract budget indicators from each source
        for source in sources:
            indicators = self._extract_budget_indicators_from_source(source)
            budget_indicators.extend(indicators)
        
        if not budget_indicators:
            return BudgetAnalysis()
        
        # GPT-4 analysis of budget capacity
        budget_prompt = f"""
        Analyze budget capacity for prospect "{prospect_data.name}":

        BUDGET INDICATORS:
        {json.dumps(budget_indicators, indent=2)}

        PROSPECT CONTEXT:
        - Name: {prospect_data.name}
        - Company: {prospect_data.company_name}
        - Location: {prospect_data.location}
        - Type: {prospect_data.prospect_type}

        Determine:
        1. Estimated budget range for different event types
        2. Budget confidence level (high/medium/low)
        3. Spending patterns and preferences
        4. Price sensitivity indicators
        5. Budget category (economy/mid-range/premium/luxury)
        6. Payment preference indicators
        7. Decision-making authority for budget

        Return structured budget analysis with ranges and confidence.
        """
        
        try:
            response = await self.openai_service.generate_agent_response(
                system_prompt="You are an expert financial analyst specializing in event planning client budget assessment.",
                user_message=budget_prompt,
                model="gpt-4"
            )
            
            budget_data = json.loads(response)
            
            return BudgetAnalysis(
                estimated_range=tuple(budget_data.get("estimated_range", [])) if budget_data.get("estimated_range") else None,
                confidence_level=budget_data.get("confidence_level", "unknown"),
                indicators=budget_data.get("indicators", []),
                spending_patterns=budget_data.get("spending_patterns", {}),
                budget_category=budget_data.get("budget_category", "unknown")
            )
            
        except Exception as e:
            logger.warning("Budget analysis failed", error=str(e))
            return BudgetAnalysis()
    
    async def _analyze_online_presence(self, sources: List[EnrichmentSource], prospect_data: ProspectData) -> Dict[str, Any]:
        """Analyze online presence and digital footprint"""
        online_data = {}
        
        for source in sources:
            if source.source_name == "web_search":
                online_data["web_presence"] = self._analyze_web_presence(source.data)
            elif source.source_name == "linkedin":
                online_data["professional_presence"] = self._analyze_linkedin_presence(source.data)
            elif source.source_name == "clearbit":
                online_data["digital_profile"] = self._analyze_clearbit_digital_data(source.data)
        
        # GPT-4 synthesis of online presence
        presence_prompt = f"""
        Analyze online presence for prospect "{prospect_data.name}":

        ONLINE DATA:
        {json.dumps(online_data, indent=2)}

        Determine:
        1. Digital engagement level (high/medium/low)
        2. Preferred communication channels
        3. Social media activity patterns
        4. Professional visibility
        5. Content sharing preferences
        6. Online influence level
        7. Digital sophistication
        8. Privacy preferences

        Return structured online presence analysis.
        """
        
        try:
            response = await self.openai_service.generate_agent_response(
                system_prompt="You are a digital marketing analyst specializing in online presence assessment.",
                user_message=presence_prompt,
                model="gpt-4"
            )
            
            return json.loads(response)
            
        except Exception as e:
            logger.warning("Online presence analysis failed", error=str(e))
            return {}
    
    async def _synthesize_final_profile(self, synthesized_data: Dict, event_preferences: Dict, 
                                       budget_analysis: BudgetAnalysis, online_presence: Dict,
                                       prospect_data: ProspectData) -> Dict[str, Any]:
        """Create final comprehensive prospect profile using GPT-4"""
        
        profile_data = {
            "basic_info": {
                "name": prospect_data.name,
                "company": prospect_data.company_name,
                "location": prospect_data.location,
                "prospect_type": prospect_data.prospect_type
            },
            "synthesized_data": synthesized_data,
            "event_preferences": event_preferences,
            "budget_analysis": {
                "estimated_range": budget_analysis.estimated_range,
                "confidence_level": budget_analysis.confidence_level,
                "budget_category": budget_analysis.budget_category,
                "indicators": budget_analysis.indicators
            },
            "online_presence": online_presence
        }
        
        synthesis_prompt = f"""
        Create a comprehensive prospect profile for "{prospect_data.name}":

        COMPILED DATA:
        {json.dumps(profile_data, indent=2)}

        Create a unified profile including:
        1. Executive summary of prospect quality and fit
        2. Key strengths for conversion potential
        3. Potential challenges or concerns
        4. Recommended approach strategy
        5. Personalization opportunities
        6. Risk factors to consider
        7. Best contact methods and timing
        8. Tailored value propositions

        Provide actionable insights for sales and marketing teams.
        Return as comprehensive structured JSON profile.
        """
        
        try:
            response = await self.openai_service.generate_agent_response(
                system_prompt="You are an expert sales analyst creating comprehensive prospect profiles for event planning sales teams.",
                user_message=synthesis_prompt,
                model="gpt-4"
            )
            
            return json.loads(response)
            
        except Exception as e:
            logger.warning("Final profile synthesis failed", error=str(e))
            return profile_data  # Return raw data as fallback
    
    def _create_enrichment_data(self, enriched_profile: Dict[str, Any], sources: List[EnrichmentSource]) -> EnrichmentData:
        """Create EnrichmentData object from enriched profile"""
        
        # Calculate overall confidence as weighted average
        total_confidence = sum(s.confidence * s.completeness_score for s in sources)
        total_weight = sum(s.completeness_score for s in sources)
        overall_confidence = total_confidence / total_weight if total_weight > 0 else 0.0
        
        return EnrichmentData(
            company_data=enriched_profile.get("synthesized_data", {}).get("company_info", {}),
            social_profiles=enriched_profile.get("online_presence", {}).get("social_profiles", {}),
            event_preferences=enriched_profile.get("event_preferences", {}),
            budget_signals=enriched_profile.get("budget_analysis", {}),
            contact_info=enriched_profile.get("synthesized_data", {}).get("contact_info", {}),
            confidence_score=overall_confidence,
            enrichment_sources=[s.source_name for s in sources],
            enrichment_metadata={
                "profile_summary": enriched_profile.get("executive_summary", ""),
                "conversion_potential": enriched_profile.get("conversion_potential", {}),
                "recommended_approach": enriched_profile.get("recommended_approach", {}),
                "personalization_opportunities": enriched_profile.get("personalization_opportunities", []),
                "risk_factors": enriched_profile.get("risk_factors", []),
                "enrichment_completed_at": datetime.now().isoformat(),
                "data_freshness_score": sum(s.freshness_score for s in sources) / len(sources) if sources else 0.0
            }
        )
    
    async def _update_prospect_with_enrichment(self, prospect_data: ProspectData, enrichment_data: EnrichmentData):
        """Update prospect record in database with enrichment data"""
        try:
            # Update prospect status and metadata
            update_result = await database_mcp.server.call_tool(
                "execute_query",
                {
                    "query": """
                    UPDATE prospects 
                    SET status = ?, 
                        lead_score = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    "parameters": [
                        ProspectStatus.ENRICHED.value,
                        max(prospect_data.lead_score, int(enrichment_data.confidence_score * 100)),
                        prospect_data.id
                    ],
                    "fetch_mode": "none"
                }
            )
            
            if update_result.isError:
                logger.warning("Failed to update prospect status", prospect_id=prospect_data.id)
            
            logger.info("Prospect updated with enrichment data", prospect_id=prospect_data.id)
            
        except Exception as e:
            logger.error("Failed to update prospect with enrichment", error=str(e), prospect_id=prospect_data.id)
    
    # Helper methods for data extraction and analysis
    
    def _calculate_clearbit_confidence(self, person_data: Dict, company_data: Dict) -> float:
        """Calculate confidence score based on Clearbit data completeness"""
        person_fields = ["name", "email", "location", "employment"]
        company_fields = ["name", "domain", "category", "employees"]
        
        person_score = sum(1 for field in person_fields if person_data.get(field)) / len(person_fields)
        company_score = sum(1 for field in company_fields if company_data.get(field)) / len(company_fields)
        
        return (person_score + company_score) / 2
    
    def _extract_key_data_from_source(self, source: EnrichmentSource) -> Dict[str, Any]:
        """Extract key data points from enrichment source"""
        if source.source_name == "clearbit":
            return {
                "person_info": source.data.get("person", {}),
                "company_info": source.data.get("company", {})
            }
        elif source.source_name == "web_search":
            return {
                "insights": source.data.get("insights", {}),
                "result_count": len(source.data.get("search_results", []))
            }
        elif source.source_name == "linkedin":
            return {
                "profile": source.data.get("profile", {}),
                "activity": source.data.get("activity", {})
            }
        
        return source.data
    
    def _extract_preference_signals_from_web(self, web_data: Dict) -> List[EventPreferenceSignal]:
        """Extract event preference signals from web search data"""
        signals = []
        insights = web_data.get("insights", {})
        
        # Extract venue preferences
        if "venue_preferences" in insights:
            signals.append(EventPreferenceSignal(
                signal_type="venue_preference",
                signal_value=str(insights["venue_preferences"]),
                confidence=0.6,
                source="web_search",
                context="Extracted from search results"
            ))
        
        # Extract style preferences
        if "style_preferences" in insights:
            signals.append(EventPreferenceSignal(
                signal_type="style_preference",
                signal_value=str(insights["style_preferences"]),
                confidence=0.6,
                source="web_search",
                context="Inferred from online activity"
            ))
        
        return signals
    
    def _extract_preference_signals_from_linkedin(self, linkedin_data: Dict) -> List[EventPreferenceSignal]:
        """Extract preference signals from LinkedIn data"""
        signals = []
        
        profile = linkedin_data.get("profile", {})
        if profile.get("industry"):
            signals.append(EventPreferenceSignal(
                signal_type="professional_context",
                signal_value=profile["industry"],
                confidence=0.8,
                source="linkedin",
                context="Professional industry context"
            ))
        
        return signals
    
    def _extract_preference_signals_from_clearbit(self, clearbit_data: Dict) -> List[EventPreferenceSignal]:
        """Extract preference signals from Clearbit data"""
        signals = []
        
        person = clearbit_data.get("person", {})
        company = clearbit_data.get("company", {})
        
        if company.get("category"):
            signals.append(EventPreferenceSignal(
                signal_type="business_context",
                signal_value=company["category"],
                confidence=0.9,
                source="clearbit",
                context="Company industry classification"
            ))
        
        return signals
    
    def _extract_budget_indicators_from_source(self, source: EnrichmentSource) -> List[str]:
        """Extract budget indicators from enrichment source"""
        indicators = []
        
        if source.source_name == "clearbit":
            company = source.data.get("company", {})
            if company.get("employees"):
                indicators.append(f"Company size: {company['employees']} employees")
            if company.get("revenue"):
                indicators.append(f"Company revenue: {company['revenue']}")
        
        elif source.source_name == "web_search":
            insights = source.data.get("insights", {})
            if "budget_indicators" in insights:
                indicators.extend(insights["budget_indicators"])
        
        return indicators
    
    def _analyze_web_presence(self, web_data: Dict) -> Dict[str, Any]:
        """Analyze web presence from search data"""
        search_results = web_data.get("search_results", [])
        
        return {
            "search_result_count": len(search_results),
            "web_visibility": "high" if len(search_results) > 10 else "medium" if len(search_results) > 5 else "low",
            "recent_activity": any("2024" in str(result) for result in search_results)
        }
    
    def _analyze_linkedin_presence(self, linkedin_data: Dict) -> Dict[str, Any]:
        """Analyze LinkedIn professional presence"""
        profile = linkedin_data.get("profile", {})
        
        return {
            "profile_completeness": "high" if len(profile) > 5 else "medium" if len(profile) > 2 else "low",
            "professional_activity": bool(linkedin_data.get("activity"))
        }
    
    def _analyze_clearbit_digital_data(self, clearbit_data: Dict) -> Dict[str, Any]:
        """Analyze digital profile from Clearbit data"""
        person = clearbit_data.get("person", {})
        
        return {
            "email_deliverability": "high" if person.get("email") else "unknown",
            "data_completeness": len(person) / 10.0  # Normalize to 0-1
        }
    
    def _fallback_data_synthesis(self, sources: List[EnrichmentSource]) -> Dict[str, Any]:
        """Fallback data synthesis when GPT-4 analysis fails"""
        synthesized = {"contact_info": {}, "company_info": {}, "personal_info": {}}
        
        for source in sources:
            if source.source_name == "clearbit":
                person = source.data.get("person", {})
                company = source.data.get("company", {})
                
                synthesized["contact_info"].update({
                    "email": person.get("email"),
                    "location": person.get("location")
                })
                synthesized["company_info"].update(company)
        
        return synthesized
    
    def _fallback_preference_analysis(self, signals: List[EventPreferenceSignal]) -> Dict[str, Any]:
        """Fallback preference analysis when GPT-4 fails"""
        preferences = {}
        
        for signal in signals:
            if signal.signal_type not in preferences:
                preferences[signal.signal_type] = []
            preferences[signal.signal_type].append(signal.signal_value)
        
        return {"preferences": preferences, "confidence": 0.5}
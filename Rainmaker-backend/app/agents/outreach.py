"""
Advanced Outreach Agent powered by GPT-4 with MCP integration.

This agent creates highly personalized, multi-channel outreach campaigns
using prospect enrichment data, event-specific templates, and intelligent
A/B testing strategies to maximize response rates.
"""

import asyncio
import json
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import structlog

from app.core.state import RainmakerState, OutreachCampaign, EnrichmentData, ProspectData
from app.core.config import settings
from app.services.openai_service import openai_service
try:
    from app.mcp.email import email_mcp
    EMAIL_AVAILABLE = True
except ImportError:
    email_mcp = None
    EMAIL_AVAILABLE = False
from app.mcp.database import database_mcp
from app.db.models import CampaignStatus, ProspectStatus, EventType

logger = structlog.get_logger(__name__)

try:
    from app.mcp.linkedin import linkedin_mcp
    LINKEDIN_AVAILABLE = True
except ImportError:
    logger.warning("LinkedIn MCP not available - LinkedIn outreach disabled")
    linkedin_mcp = None
    LINKEDIN_AVAILABLE = False


class MessageTone(str, Enum):
    """Message tone options"""
    PROFESSIONAL = "professional"
    WARM = "warm"
    FRIENDLY = "friendly"
    CONSULTATIVE = "consultative"
    URGENT = "urgent"
    CASUAL = "casual"


class OutreachChannel(str, Enum):
    """Available outreach channels"""
    EMAIL = "email"
    LINKEDIN = "linkedin"
    PHONE = "phone"
    SMS = "sms"


@dataclass
class PersonalizationContext:
    """Context for personalizing outreach messages"""
    prospect_data: ProspectData
    enrichment_data: Optional[EnrichmentData] = None
    event_type: Optional[str] = None
    urgency_level: str = "medium"
    previous_interactions: List[Dict] = field(default_factory=list)
    competitor_mentions: List[str] = field(default_factory=list)
    mutual_connections: List[str] = field(default_factory=list)


@dataclass
class MessageVariant:
    """A/B testing message variant"""
    variant_id: str
    subject_line: Optional[str] = None
    message_body: str = ""
    tone: MessageTone = MessageTone.PROFESSIONAL
    length: str = "medium"  # short/medium/long
    call_to_action: str = ""
    personalization_level: str = "medium"  # low/medium/high
    expected_performance: float = 0.5  # 0.0 to 1.0


@dataclass
class CampaignMetrics:
    """Campaign performance metrics"""
    sent_count: int = 0
    opened_count: int = 0
    replied_count: int = 0
    clicked_count: int = 0
    bounced_count: int = 0
    unsubscribed_count: int = 0
    conversion_count: int = 0
    open_rate: float = 0.0
    reply_rate: float = 0.0
    conversion_rate: float = 0.0


class OutreachAgent:
    """
    Advanced Outreach Agent that creates personalized, multi-channel campaigns.
    
    Uses GPT-4 for dynamic message generation, enrichment data for personalization,
    and intelligent channel selection to maximize engagement rates.
    """
    
    def __init__(self):
        self.openai_service = openai_service
        self.ab_test_enabled = True
        self.max_personalization_attempts = 3
        self.channel_priorities = [OutreachChannel.EMAIL, OutreachChannel.LINKEDIN, OutreachChannel.PHONE]
        
    async def execute_outreach(self, state: RainmakerState) -> RainmakerState:
        """
        Main outreach execution method that creates and sends personalized campaigns.
        """
        logger.info("Starting advanced outreach campaign", workflow_id=state.get("workflow_id"))
        
        try:
            prospect_data = state["prospect_data"]
            enrichment_data = state.get("enrichment_data")
            
            # Build personalization context
            personalization_context = await self._build_personalization_context(
                prospect_data, enrichment_data, state
            )
            
            # Determine optimal outreach channel
            selected_channel = await self._select_optimal_channel(personalization_context)
            
            # Generate message variants for A/B testing
            message_variants = await self._generate_message_variants(
                personalization_context, selected_channel
            )
            
            # Select best variant or create A/B test
            selected_variant = await self._select_message_variant(message_variants, personalization_context)
            
            # Create and send campaign
            campaign = await self._create_and_send_campaign(
                selected_variant, selected_channel, personalization_context, state
            )
            
            # Update state with campaign results
            if "outreach_campaigns" not in state:
                state["outreach_campaigns"] = []
            state["outreach_campaigns"].append(campaign)
            
            # Update prospect status
            await self._update_prospect_status(prospect_data.id, ProspectStatus.CONTACTED)
            
            logger.info(
                "Outreach campaign completed",
                workflow_id=state.get("workflow_id"),
                channel=selected_channel.value,
                campaign_id=campaign.id
            )
            
            return state
            
        except Exception as e:
            logger.error("Outreach campaign failed", error=str(e), workflow_id=state.get("workflow_id"))
            raise
    
    async def _build_personalization_context(self, prospect_data: ProspectData, 
                                           enrichment_data: Optional[EnrichmentData],
                                           state: RainmakerState) -> PersonalizationContext:
        """Build comprehensive personalization context"""
        
        # Determine event type from various sources
        event_type = self._determine_event_type(prospect_data, enrichment_data, state)
        
        # Calculate urgency level
        urgency_level = self._calculate_urgency_level(prospect_data, enrichment_data, state)
        
        # Get previous interactions
        previous_interactions = await self._get_previous_interactions(prospect_data.id)
        
        # Find mutual connections (if LinkedIn available)
        mutual_connections = await self._find_mutual_connections(prospect_data)
        
        # Analyze competitor landscape
        competitor_mentions = await self._analyze_competitor_mentions(prospect_data, enrichment_data)
        
        return PersonalizationContext(
            prospect_data=prospect_data,
            enrichment_data=enrichment_data,
            event_type=event_type,
            urgency_level=urgency_level,
            previous_interactions=previous_interactions,
            competitor_mentions=competitor_mentions,
            mutual_connections=mutual_connections
        )
    
    def _determine_event_type(self, prospect_data: ProspectData, 
                            enrichment_data: Optional[EnrichmentData],
                            state: RainmakerState) -> str:
        """Determine the most likely event type for this prospect"""
        
        # Check hunter results for detected event type
        hunter_results = state.get("hunter_results")
        if hunter_results and hasattr(hunter_results, 'search_metadata'):
            event_distribution = hunter_results.search_metadata.get("event_type_distribution", {})
            if event_distribution:
                return max(event_distribution.keys(), key=lambda k: event_distribution[k])
        
        # Check enrichment data for event preferences
        if enrichment_data and enrichment_data.event_preferences:
            detected_events = enrichment_data.event_preferences.get("detected_event_types", [])
            if detected_events:
                return detected_events[0]
        
        # Default based on prospect type
        if prospect_data.prospect_type == "company":
            return "corporate_event"
        else:
            return "wedding"  # Most common individual event type
    
    def _calculate_urgency_level(self, prospect_data: ProspectData,
                               enrichment_data: Optional[EnrichmentData],
                               state: RainmakerState) -> str:
        """Calculate urgency level based on prospect signals"""
        
        urgency_indicators = []
        
        # Check for timeline indicators in enrichment data
        if enrichment_data and enrichment_data.enrichment_metadata:
            timeline = enrichment_data.enrichment_metadata.get("estimated_timeline")
            if timeline == "immediate":
                urgency_indicators.append("high")
            elif timeline == "3-6 months":
                urgency_indicators.append("medium")
            else:
                urgency_indicators.append("low")
        
        # Check prospect lead score
        if prospect_data.lead_score > 80:
            urgency_indicators.append("high")
        elif prospect_data.lead_score > 60:
            urgency_indicators.append("medium")
        else:
            urgency_indicators.append("low")
        
        # Return highest urgency level found
        if "high" in urgency_indicators:
            return "high"
        elif "medium" in urgency_indicators:
            return "medium"
        else:
            return "low"
    
    async def _get_previous_interactions(self, prospect_id: Optional[int]) -> List[Dict]:
        """Get previous campaign interactions for this prospect"""
        if not prospect_id:
            return []
        
        try:
            result = await database_mcp.server.call_tool(
                "execute_query",
                {
                    "query": """
                    SELECT channel, campaign_type, status, sent_at, opened_at, replied_at
                    FROM campaigns 
                    WHERE prospect_id = ? 
                    ORDER BY sent_at DESC 
                    LIMIT 10
                    """,
                    "parameters": [prospect_id],
                    "fetch_mode": "all"
                }
            )
            
            if not result.isError:
                result_data = json.loads(result.content[0].text)
                return result_data.get("result", [])
            
        except Exception as e:
            logger.warning("Failed to get previous interactions", error=str(e))
        
        return []
    
    async def _find_mutual_connections(self, prospect_data: ProspectData) -> List[str]:
        """Find mutual connections on LinkedIn"""
        if not settings.LINKEDIN_API_KEY or not prospect_data.company_name:
            return []
        
        try:
            result = await linkedin_mcp.server.call_tool(
                "find_mutual_connections",
                {
                    "prospect_name": prospect_data.name,
                    "company_name": prospect_data.company_name
                }
            )
            
            if not result.isError:
                connections_data = json.loads(result.content[0].text)
                return connections_data.get("mutual_connections", [])
            
        except Exception as e:
            logger.warning("Failed to find mutual connections", error=str(e))
        
        return []
    
    async def _analyze_competitor_mentions(self, prospect_data: ProspectData,
                                         enrichment_data: Optional[EnrichmentData]) -> List[str]:
        """Analyze for competitor mentions in prospect data"""
        competitor_keywords = [
            "event planner", "wedding planner", "party planner",
            "celebration coordinator", "event coordinator"
        ]
        
        mentions = []
        
        # Check enrichment data for competitor signals
        if enrichment_data and enrichment_data.enrichment_metadata:
            profile_summary = enrichment_data.enrichment_metadata.get("profile_summary", "")
            
            for keyword in competitor_keywords:
                if keyword.lower() in profile_summary.lower():
                    mentions.append(keyword)
        
        return mentions
    
    async def _select_optimal_channel(self, context: PersonalizationContext) -> OutreachChannel:
        """Select the optimal outreach channel based on context"""
        
        channel_scores = {}
        
        # Email scoring
        email_score = 0.5  # Base score
        if context.prospect_data.email:
            email_score += 0.3
        if context.enrichment_data and context.enrichment_data.contact_info.get("email_deliverability") == "high":
            email_score += 0.2
        channel_scores[OutreachChannel.EMAIL] = email_score
        
        # LinkedIn scoring
        linkedin_score = 0.3  # Base score
        if context.prospect_data.prospect_type == "company":
            linkedin_score += 0.3
        if context.mutual_connections:
            linkedin_score += 0.2
        if settings.LINKEDIN_API_KEY:
            linkedin_score += 0.2
        channel_scores[OutreachChannel.LINKEDIN] = linkedin_score
        
        # Phone scoring
        phone_score = 0.2  # Base score
        if context.prospect_data.phone:
            phone_score += 0.3
        if context.urgency_level == "high":
            phone_score += 0.2
        channel_scores[OutreachChannel.PHONE] = phone_score
        
        # Select highest scoring channel
        return max(channel_scores.keys(), key=lambda k: channel_scores[k])
    
    async def _generate_message_variants(self, context: PersonalizationContext, 
                                       channel: OutreachChannel) -> List[MessageVariant]:
        """Generate multiple message variants for A/B testing"""
        
        variants = []
        
        if self.ab_test_enabled:
            # Generate variants with different tones and approaches
            variant_configs = [
                {"tone": MessageTone.PROFESSIONAL, "length": "medium", "personalization": "high"},
                {"tone": MessageTone.WARM, "length": "short", "personalization": "medium"},
                {"tone": MessageTone.CONSULTATIVE, "length": "long", "personalization": "high"}
            ]
            
            for i, config in enumerate(variant_configs):
                variant = await self._generate_single_variant(
                    context, channel, f"variant_{i+1}", config
                )
                variants.append(variant)
        else:
            # Generate single optimized variant
            variant = await self._generate_single_variant(
                context, channel, "primary", 
                {"tone": MessageTone.PROFESSIONAL, "length": "medium", "personalization": "high"}
            )
            variants.append(variant)
        
        return variants
    
    async def _generate_single_variant(self, context: PersonalizationContext,
                                     channel: OutreachChannel, variant_id: str,
                                     config: Dict[str, Any]) -> MessageVariant:
        """Generate a single message variant using GPT-4"""
        
        # Build comprehensive prompt for message generation
        prompt = self._build_message_generation_prompt(context, channel, config)
        
        try:
            response = await self.openai_service.generate_agent_response(
                system_prompt=f"You are an expert event planning sales professional specializing in {channel.value} outreach.",
                user_message=prompt,
                model="gpt-4"
            )
            
            # Parse response into message components
            message_data = self._parse_message_response(response, config)
            
            return MessageVariant(
                variant_id=variant_id,
                subject_line=message_data.get("subject_line"),
                message_body=message_data.get("message_body", ""),
                tone=MessageTone(config.get("tone", "professional")),
                length=config.get("length", "medium"),
                call_to_action=message_data.get("call_to_action", ""),
                personalization_level=config.get("personalization", "medium"),
                expected_performance=message_data.get("expected_performance", 0.5)
            )
            
        except Exception as e:
            logger.error("Message variant generation failed", error=str(e))
            # Return fallback variant
            return self._create_fallback_variant(context, channel, variant_id)
    
    def _build_message_generation_prompt(self, context: PersonalizationContext,
                                       channel: OutreachChannel, config: Dict[str, Any]) -> str:
        """Build comprehensive prompt for GPT-4 message generation"""
        
        prospect = context.prospect_data
        enrichment = context.enrichment_data
        
        # Build prospect profile section
        prospect_profile = f"""
        PROSPECT PROFILE:
        - Name: {prospect.name}
        - Type: {prospect.prospect_type}
        - Company: {prospect.company_name or 'N/A'}
        - Location: {prospect.location or 'N/A'}
        - Lead Score: {prospect.lead_score}/100
        - Event Type: {context.event_type}
        - Urgency Level: {context.urgency_level}
        """
        
        # Add enrichment insights if available
        enrichment_section = ""
        if enrichment and enrichment.enrichment_metadata:
            profile_summary = enrichment.enrichment_metadata.get("profile_summary", "")
            personalization_ops = enrichment.enrichment_metadata.get("personalization_opportunities", [])
            
            if profile_summary:
                enrichment_section += f"- Profile Summary: {profile_summary}\n"
            if personalization_ops:
                enrichment_section += f"- Personalization Opportunities: {', '.join(personalization_ops[:3])}\n"
        
        # Build context section
        context_section = ""
        if context.mutual_connections:
            context_section += f"- Mutual Connections: {', '.join(context.mutual_connections[:2])}\n"
        if context.previous_interactions:
            context_section += f"- Previous Contact Attempts: {len(context.previous_interactions)}\n"
        if context.competitor_mentions:
            context_section += f"- Competitor Awareness: {', '.join(context.competitor_mentions[:2])}\n"
        
        # Build message requirements
        message_requirements = f"""
        MESSAGE REQUIREMENTS:
        - Channel: {channel.value}
        - Tone: {config.get('tone', 'professional')}
        - Length: {config.get('length', 'medium')} (short=50-100 words, medium=100-200, long=200-300)
        - Personalization Level: {config.get('personalization', 'medium')}
        """
        
        # Event-specific guidelines
        event_guidelines = self._get_event_specific_guidelines(context.event_type)
        
        full_prompt = f"""
        Create a highly effective {channel.value} outreach message for this event planning prospect:

        {prospect_profile}

        ENRICHMENT INSIGHTS:
        {enrichment_section}

        ADDITIONAL CONTEXT:
        {context_section}

        {message_requirements}

        EVENT-SPECIFIC GUIDELINES:
        {event_guidelines}

        PERSONALIZATION STRATEGY:
        1. Reference specific details about their situation/business
        2. Show understanding of their event type and requirements
        3. Demonstrate relevant experience and expertise
        4. Create urgency appropriate to their timeline
        5. Include clear, compelling call-to-action

        RESPONSE FORMAT (JSON):
        {{
            "subject_line": "Compelling subject for email/LinkedIn (if applicable)",
            "message_body": "Complete personalized message",
            "call_to_action": "Specific next step request",
            "personalization_notes": "Key personalization elements used",
            "expected_performance": "Estimated response rate (0.0-1.0)"
        }}
        """
        
        return full_prompt
    
    def _get_event_specific_guidelines(self, event_type: str) -> str:
        """Get event-type specific messaging guidelines"""
        
        guidelines = {
            "wedding": """
            - Emphasize emotion, memories, and once-in-a-lifetime experience
            - Mention stress reduction and peace of mind
            - Reference specific wedding elements (venue, flowers, photography)
            - Use warm, celebratory language
            - Highlight experience with similar-sized weddings
            """,
            
            "corporate_event": """
            - Focus on ROI, employee engagement, and business objectives
            - Emphasize professional execution and logistics management
            - Mention team building, networking, or brand visibility benefits
            - Use professional, results-oriented language
            - Highlight corporate client testimonials or case studies
            """,
            
            "birthday": """
            - Emphasize celebration, joy, and making memories
            - Mention unique themes and creative concepts
            - Reference age-appropriate entertainment and activities
            - Use fun, energetic language while maintaining professionalism
            - Highlight experience with milestone birthdays
            """,
            
            "anniversary": """
            - Focus on romance, celebration of love, and special memories
            - Mention intimate settings and meaningful details
            - Reference couples' preferences and shared interests
            - Use warm, romantic language
            - Highlight experience with anniversary celebrations
            """
        }
        
        return guidelines.get(event_type, "Focus on creating memorable experiences and handling all event details professionally.")
    
    def _parse_message_response(self, response: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Parse GPT-4 response into message components"""
        try:
            message_data = json.loads(response)
            return message_data
        except json.JSONDecodeError:
            # Fallback parsing if JSON fails
            logger.warning("Failed to parse JSON response, using fallback")
            return {
                "subject_line": "Let's Make Your Event Unforgettable",
                "message_body": response[:500],  # Use first part of response
                "call_to_action": "Would you be available for a brief call this week?",
                "expected_performance": 0.4
            }
    
    def _create_fallback_variant(self, context: PersonalizationContext,
                               channel: OutreachChannel, variant_id: str) -> MessageVariant:
        """Create fallback message variant when generation fails"""
        
        prospect_name = context.prospect_data.name
        event_type = context.event_type
        
        fallback_messages = {
            OutreachChannel.EMAIL: {
                "subject_line": f"Making Your {event_type.title()} Unforgettable - {prospect_name}",
                "message_body": f"""Hi {prospect_name},

I noticed you're planning a {event_type} and wanted to reach out personally. As an experienced event planner specializing in {event_type}s, I'd love to help make your celebration absolutely perfect.

I have availability for a brief call this week to discuss your vision and how we can bring it to life.

Would Tuesday or Wednesday afternoon work for a 15-minute conversation?

Best regards,
[Your Name]""",
                "call_to_action": "Would Tuesday or Wednesday afternoon work for a 15-minute conversation?"
            },
            
            OutreachChannel.LINKEDIN: {
                "subject_line": f"Re: Your Upcoming {event_type.title()}",
                "message_body": f"""Hi {prospect_name},

I see we might have mutual connections in the event planning space. I specialize in {event_type}s and would love to share some insights that could help with your upcoming celebration.

Are you available for a brief call this week?

Best,
[Your Name]""",
                "call_to_action": "Are you available for a brief call this week?"
            }
        }
        
        channel_message = fallback_messages.get(channel, fallback_messages[OutreachChannel.EMAIL])
        
        return MessageVariant(
            variant_id=variant_id,
            subject_line=channel_message["subject_line"],
            message_body=channel_message["message_body"],
            call_to_action=channel_message["call_to_action"],
            expected_performance=0.3
        )
    
    async def _select_message_variant(self, variants: List[MessageVariant],
                                    context: PersonalizationContext) -> MessageVariant:
        """Select the best message variant or set up A/B test"""
        
        if len(variants) == 1:
            return variants[0]
        
        if self.ab_test_enabled and len(variants) > 1:
            # Use GPT-4 to analyze and rank variants
            ranking_prompt = self._build_variant_ranking_prompt(variants, context)
            
            try:
                response = await self.openai_service.generate_agent_response(
                    system_prompt="You are an expert email marketing analyst specializing in event planning sales optimization.",
                    user_message=ranking_prompt,
                    model="gpt-4"
                )
                
                ranking_data = json.loads(response)
                best_variant_id = ranking_data.get("best_variant", variants[0].variant_id)
                
                # Find and return the best variant
                for variant in variants:
                    if variant.variant_id == best_variant_id:
                        return variant
                
            except Exception as e:
                logger.warning("Variant ranking failed", error=str(e))
        
        # Fallback to highest expected performance
        return max(variants, key=lambda v: v.expected_performance)
    
    def _build_variant_ranking_prompt(self, variants: List[MessageVariant],
                                    context: PersonalizationContext) -> str:
        """Build prompt for GPT-4 variant ranking"""
        
        variants_data = []
        for variant in variants:
            variants_data.append({
                "variant_id": variant.variant_id,
                "subject_line": variant.subject_line,
                "message_body": variant.message_body[:200],  # Truncate for prompt
                "tone": variant.tone.value,
                "length": variant.length,
                "call_to_action": variant.call_to_action
            })
        
        return f"""
        Analyze these message variants for prospect "{context.prospect_data.name}" and select the best one:

        PROSPECT CONTEXT:
        - Type: {context.prospect_data.prospect_type}
        - Event Type: {context.event_type}
        - Urgency: {context.urgency_level}
        - Lead Score: {context.prospect_data.lead_score}/100

        MESSAGE VARIANTS:
        {json.dumps(variants_data, indent=2)}

        EVALUATION CRITERIA:
        1. Personalization effectiveness
        2. Relevance to prospect situation
        3. Compelling call-to-action
        4. Professional tone and clarity
        5. Likely response rate

        Return JSON with:
        - "best_variant": variant_id of the best performing variant
        - "reasoning": Why this variant will perform best
        - "expected_response_rate": Estimated response rate (0.0-1.0)
        """
    
    async def _create_and_send_campaign(self, variant: MessageVariant, channel: OutreachChannel,
                                      context: PersonalizationContext, state: RainmakerState) -> OutreachCampaign:
        """Create campaign record and send the message"""
        
        # Create campaign record
        campaign = OutreachCampaign(
            channel=channel.value,
            campaign_type="initial_outreach",
            subject_line=variant.subject_line,
            message_body=variant.message_body,
            personalization_data={
                "variant_id": variant.variant_id,
                "tone": variant.tone.value,
                "personalization_level": variant.personalization_level,
                "event_type": context.event_type,
                "urgency_level": context.urgency_level
            },
            status=CampaignStatus.DRAFT
        )
        
        # Send the message based on channel
        if channel == OutreachChannel.EMAIL:
            send_result = await self._send_email_campaign(campaign, context)
        elif channel == OutreachChannel.LINKEDIN:
            send_result = await self._send_linkedin_campaign(campaign, context)
        else:
            # For phone/SMS, mark as pending manual action
            campaign.status = CampaignStatus.PENDING_APPROVAL
            send_result = {"success": True, "message": "Campaign queued for manual execution"}
        
        # Update campaign status based on send result
        if send_result.get("success"):
            campaign.status = CampaignStatus.SENT
            campaign.sent_at = datetime.now()
        else:
            campaign.status = CampaignStatus.REJECTED
        
        # Store campaign in database
        await self._store_campaign_in_database(campaign, context.prospect_data.id)
        
        return campaign
    
    async def _send_email_campaign(self, campaign: OutreachCampaign, 
                                 context: PersonalizationContext) -> Dict[str, Any]:
        """Send email campaign using Email MCP"""
        try:
            result = await email_mcp.server.call_tool(
                "send_email",
                {
                    "to_email": context.prospect_data.email,
                    "to_name": context.prospect_data.name,
                    "subject": campaign.subject_line,
                    "html_content": self._format_html_email(campaign.message_body),
                    "text_content": campaign.message_body
                }
            )
            
            if not result.isError:
                send_data = json.loads(result.content[0].text)
                return {"success": True, "message_id": send_data.get("message_id")}
            else:
                return {"success": False, "error": result.content[0].text}
                
        except Exception as e:
            logger.error("Email campaign send failed", error=str(e))
            return {"success": False, "error": str(e)}
    
    async def _send_linkedin_campaign(self, campaign: OutreachCampaign,
                                    context: PersonalizationContext) -> Dict[str, Any]:
        """Send LinkedIn campaign using LinkedIn MCP"""
        try:
            result = await linkedin_mcp.server.call_tool(
                "send_connection_request",
                {
                    "recipient_name": context.prospect_data.name,
                    "company_name": context.prospect_data.company_name,
                    "message": campaign.message_body,
                    "note": campaign.subject_line
                }
            )
            
            if not result.isError:
                send_data = json.loads(result.content[0].text)
                return {"success": True, "request_id": send_data.get("request_id")}
            else:
                return {"success": False, "error": result.content[0].text}
                
        except Exception as e:
            logger.error("LinkedIn campaign send failed", error=str(e))
            return {"success": False, "error": str(e)}
    
    def _format_html_email(self, text_content: str) -> str:
        """Format plain text as HTML email"""
        # Simple HTML formatting
        html_content = text_content.replace('\n\n', '</p><p>')
        html_content = html_content.replace('\n', '<br>')
        
        return f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <p>{html_content}</p>
        </body>
        </html>
        """
    
    async def _store_campaign_in_database(self, campaign: OutreachCampaign, prospect_id: Optional[int]):
        """Store campaign record in database"""
        if not prospect_id:
            logger.warning("Cannot store campaign - no prospect ID")
            return
        
        try:
            result = await database_mcp.server.call_tool(
                "execute_query",
                {
                    "query": """
                    INSERT INTO campaigns (
                        prospect_id, channel, campaign_type, subject_line, 
                        message_body, personalization_data, status, sent_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    "parameters": [
                        prospect_id,
                        campaign.channel,
                        campaign.campaign_type,
                        campaign.subject_line,
                        campaign.message_body,
                        json.dumps(campaign.personalization_data),
                        campaign.status.value,
                        campaign.sent_at.isoformat() if campaign.sent_at else None
                    ],
                    "fetch_mode": "none"
                }
            )
            
            if not result.isError:
                # Get campaign ID
                id_result = await database_mcp.server.call_tool(
                    "execute_query",
                    {"query": "SELECT LAST_INSERT_ID() as id", "fetch_mode": "one"}
                )
                
                if not id_result.isError:
                    id_data = json.loads(id_result.content[0].text)
                    campaign.id = id_data.get("result", {}).get("id")
            
        except Exception as e:
            logger.error("Failed to store campaign in database", error=str(e))
    
    async def _update_prospect_status(self, prospect_id: Optional[int], status: ProspectStatus):
        """Update prospect status after outreach"""
        if not prospect_id:
            return
        
        try:
            await database_mcp.server.call_tool(
                "execute_query",
                {
                    "query": "UPDATE prospects SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    "parameters": [status.value, prospect_id],
                    "fetch_mode": "none"
                }
            )
        except Exception as e:
            logger.error("Failed to update prospect status", error=str(e))
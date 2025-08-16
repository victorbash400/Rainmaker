"""
Advanced Proposal Agent powered by gemini with MCP integration.

This agent generates comprehensive, dynamic event proposals with intelligent pricing,
customized packages, vendor integration, and professional presentation materials
including PDF generation and mood boards.
"""

import asyncio
import json
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta, date
from dataclasses import dataclass, field
from enum import Enum
import structlog

from app.core.state import RainmakerState, ProposalData, ConversationSummary, ProspectData
from app.core.config import settings
from app.services.openai_service import openai_service
from app.mcp.proposal import proposal_mcp
from app.mcp.file_storage import file_storage_mcp
from app.mcp.database import database_mcp
from app.db.models import ProspectStatus 

logger = structlog.get_logger(__name__)


class PricingStrategy(str, Enum):
    """Pricing strategy options"""
    COMPETITIVE = "competitive"
    PREMIUM = "premium"
    VALUE = "value"
    CUSTOM = "custom"


class PackageLevel(str, Enum):
    """Package service levels"""
    ESSENTIAL = "essential"
    PREMIUM = "premium"
    LUXURY = "luxury"
    CUSTOM = "custom"


@dataclass
class VendorService:
    """Individual vendor service"""
    category: str  # photography, catering, flowers, etc.
    vendor_name: str
    service_description: str
    base_price: float
    price_per_guest: Optional[float] = None
    included_in_package: bool = True
    upgrade_options: List[Dict[str, Any]] = field(default_factory=list)
    vendor_rating: float = 5.0
    portfolio_samples: List[str] = field(default_factory=list)


@dataclass
class PackageOption:
    """Complete event package option"""
    package_id: str
    package_name: str
    package_level: PackageLevel
    description: str
    base_price: float
    included_services: List[VendorService]
    optional_services: List[VendorService]
    features: List[str]
    guest_count_range: Tuple[int, int]
    ideal_for: List[str]
    what_makes_special: str


@dataclass
class PricingCalculation:
    """Detailed pricing calculation"""
    base_package_price: float
    guest_count_adjustment: float
    location_adjustment: float
    date_premium: float
    seasonal_adjustment: float
    urgency_premium: float
    complexity_adjustment: float
    discount_applied: float
    total_before_tax: float
    tax_amount: float
    final_total: float
    pricing_notes: List[str] = field(default_factory=list)


@dataclass
class ProposalContent:
    """Complete proposal content structure"""
    executive_summary: str
    event_vision_statement: str
    packages_offered: List[PackageOption]
    recommended_package: PackageOption
    pricing_breakdown: PricingCalculation
    timeline_overview: Dict[str, str]
    vendor_showcase: List[VendorService]
    terms_and_conditions: str
    next_steps: List[str]
    validity_period: date
    unique_value_propositions: List[str]
    frequently_asked_questions: List[Dict[str, str]]


class ProposalAgent:
    """
    Advanced Proposal Agent that generates comprehensive event proposals.
    
    Creates dynamic, personalized proposals with intelligent pricing,
    vendor integration, professional formatting, and compelling presentation
    materials to maximize conversion rates.
    """
    
    def __init__(self):
        self.openai_service = openai_service
        self.base_markup = 0.20  # 20% markup on vendor costs
        self.rush_job_premium = 0.15  # 15% premium for rush jobs
        self.complexity_multipliers = {
            "simple": 1.0,
            "moderate": 1.2,
            "complex": 1.5,
            "highly_complex": 2.0
        }
        
    async def generate_proposal(self, state: RainmakerState) -> RainmakerState:
        """
        Main proposal generation method that creates comprehensive event proposals.
        """
        logger.info("Starting proposal generation", workflow_id=state.get("workflow_id"))
        
        try:
            prospect_data = state["prospect_data"]
            conversation_summary = state.get("conversation_summary")
            enrichment_data = state.get("enrichment_data")
            
            # Extract event requirements
            event_requirements = self._extract_event_requirements(conversation_summary, prospect_data)
            
            # Determine pricing strategy
            pricing_strategy = await self._determine_pricing_strategy(
                prospect_data, enrichment_data, event_requirements
            )
            
            # Generate package options
            package_options = await self._generate_package_options(
                event_requirements, pricing_strategy, prospect_data
            )
            
            # Calculate detailed pricing
            pricing_calculation = await self._calculate_detailed_pricing(
                package_options, event_requirements, pricing_strategy
            )
            
            # Generate proposal content
            proposal_content = await self._generate_proposal_content(
                package_options, pricing_calculation, event_requirements, prospect_data
            )
            
            # Create visual materials
            mood_board_url = await self._generate_mood_board(event_requirements, proposal_content)
            
            # Generate PDF proposal
            proposal_pdf_url = await self._generate_proposal_pdf(proposal_content, prospect_data)
            
            # Create proposal data object
            proposal_data = self._create_proposal_data(
                proposal_content, pricing_calculation, mood_board_url, proposal_pdf_url, prospect_data
            )
            
            # Store proposal in database
            await self._store_proposal_in_database(proposal_data, prospect_data.id)
            
            # Update state
            state["proposal_data"] = proposal_data
            
            # Update prospect status
            await self._update_prospect_status(prospect_data.id, ProspectStatus.QUALIFIED)
            
            logger.info(
                "Proposal generation completed",
                workflow_id=state.get("workflow_id"),
                total_price=proposal_data.total_price,
                package_count=len(package_options)
            )
            
            return state
            
        except Exception as e:
            logger.error("Proposal generation failed", error=str(e), workflow_id=state.get("workflow_id"))
            raise
    
    def _extract_event_requirements(self, conversation_summary: Optional[ConversationSummary], 
                                   prospect_data: ProspectData) -> Dict[str, Any]:
        """Extract and structure event requirements from conversation"""
        
        requirements = {
            "event_type": "wedding",  # default
            "guest_count": 100,      # default
            "budget_range": None,
            "event_date": None,
            "location": prospect_data.location,
            "style_preferences": [],
            "special_requirements": [],
            "venue_type": None,
            "complexity_level": "moderate"
        }
        
        if conversation_summary and conversation_summary.extracted_requirements:
            req = conversation_summary.extracted_requirements
            
            requirements.update({
                "event_type": req.get("event_type") or requirements["event_type"],
                "guest_count": req.get("guest_count") or requirements["guest_count"],
                "budget_range": req.get("budget_range"),
                "event_date": req.get("event_date"),
                "venue_type": req.get("venue_type"),
                "style_preferences": req.get("style_preferences", []),
                "special_requirements": req.get("special_requirements", []),
                "must_haves": req.get("must_haves", []),
                "deal_breakers": req.get("deal_breakers", [])
            })
        
        # Determine complexity level
        complexity_indicators = len(requirements["special_requirements"]) + len(requirements.get("must_haves", []))
        if complexity_indicators > 5:
            requirements["complexity_level"] = "highly_complex"
        elif complexity_indicators > 3:
            requirements["complexity_level"] = "complex"
        elif complexity_indicators > 1:
            requirements["complexity_level"] = "moderate"
        else:
            requirements["complexity_level"] = "simple"
        
        return requirements
    
    async def _determine_pricing_strategy(self, prospect_data: ProspectData,
                                        enrichment_data: Optional[Any],
                                        event_requirements: Dict[str, Any]) -> PricingStrategy:
        """Determine optimal pricing strategy for this prospect"""
        
        strategy_prompt = f"""
        Determine optimal pricing strategy for this event planning prospect:

        PROSPECT PROFILE:
        - Name: {prospect_data.name}
        - Type: {prospect_data.prospect_type}
        - Company: {prospect_data.company_name}
        - Location: {prospect_data.location}
        - Lead Score: {prospect_data.lead_score}/100

        EVENT REQUIREMENTS:
        - Event Type: {event_requirements['event_type']}
        - Guest Count: {event_requirements['guest_count']}
        - Budget Range: {event_requirements.get('budget_range', 'Not specified')}
        - Complexity: {event_requirements['complexity_level']}
        - Special Requirements: {event_requirements['special_requirements']}

        ENRICHMENT INSIGHTS:
        {json.dumps(enrichment_data.budget_signals if enrichment_data else {}, indent=2)}

        Pricing Strategy Options:
        1. COMPETITIVE: Match or beat competitor pricing
        2. PREMIUM: Higher pricing for premium positioning
        3. VALUE: Competitive pricing with added value
        4. CUSTOM: Fully customized pricing approach

        Consider:
        - Budget capacity indicators
        - Event complexity and requirements
        - Competitive landscape
        - Value perception factors
        - Prospect's business/personal context

        Return just the strategy name (competitive/premium/value/custom).
        """
        
        try:
            response = await self.openai_service.generate_agent_response(
                system_prompt="You are a pricing strategist for event planning businesses.",
                user_message=strategy_prompt,
                model="gpt-5-nano"
            )
            
            strategy_name = response.strip().lower()
            return PricingStrategy(strategy_name) if strategy_name in [s.value for s in PricingStrategy] else PricingStrategy.VALUE
            
        except Exception as e:
            logger.warning("Pricing strategy determination failed", error=str(e))
            return PricingStrategy.VALUE
    
    async def _generate_package_options(self, event_requirements: Dict[str, Any],
                                      pricing_strategy: PricingStrategy,
                                      prospect_data: ProspectData) -> List[PackageOption]:
        """Generate customized package options for the event"""
        
        package_generation_prompt = f"""
        Create 3 compelling event planning packages for this prospect:

        EVENT REQUIREMENTS:
        - Type: {event_requirements['event_type']}
        - Guests: {event_requirements['guest_count']}
        - Location: {event_requirements['location']}
        - Style: {event_requirements['style_preferences']}
        - Special Needs: {event_requirements['special_requirements']}
        - Complexity: {event_requirements['complexity_level']}

        PRICING STRATEGY: {pricing_strategy.value}

        Generate packages:
        1. ESSENTIAL: Core services, budget-friendly
        2. PREMIUM: Enhanced services, most popular
        3. LUXURY: Full-service, premium experience

        For each package, provide:
        - Package name and compelling description
        - Base price range appropriate for guest count and event type
        - Included services (venue, catering, decor, coordination, etc.)
        - Key features and benefits
        - What makes this package special
        - Guest count range it works for
        - Ideal client profile

        Consider current market rates for {event_requirements['event_type']} events.
        Essential: $50-150 per guest, Premium: $150-300 per guest, Luxury: $300-500+ per guest

        Return as structured JSON with detailed package specifications.
        """
        
        try:
            response = await self.openai_service.generate_agent_response(
                system_prompt="You are an expert event planning package designer. Create compelling, profitable packages.",
                user_message=package_generation_prompt,
                model="gpt-5-nano"
            )
            
            packages_data = json.loads(response)
            package_options = []
            
            for pkg_data in packages_data:
                # Generate vendor services for this package
                vendor_services = await self._generate_vendor_services(
                    pkg_data, event_requirements
                )
                
                package = PackageOption(
                    package_id=f"pkg_{pkg_data.get('level', 'custom').lower()}",
                    package_name=pkg_data.get("name", "Custom Package"),
                    package_level=PackageLevel(pkg_data.get("level", "premium").lower()),
                    description=pkg_data.get("description", ""),
                    base_price=pkg_data.get("base_price", 10000),
                    included_services=vendor_services["included"],
                    optional_services=vendor_services["optional"],
                    features=pkg_data.get("features", []),
                    guest_count_range=(
                        pkg_data.get("guest_range", {}).get("min", 50),
                        pkg_data.get("guest_range", {}).get("max", 200)
                    ),
                    ideal_for=pkg_data.get("ideal_for", []),
                    what_makes_special=pkg_data.get("what_makes_special", "")
                )
                
                package_options.append(package)
            
            return package_options
            
        except Exception as e:
            logger.warning("Package generation failed", error=str(e))
            return self._create_fallback_packages(event_requirements)
    
    async def _generate_vendor_services(self, package_data: Dict[str, Any],
                                       event_requirements: Dict[str, Any]) -> Dict[str, List[VendorService]]:
        """Generate vendor services for a package"""
        
        event_type = event_requirements["event_type"]
        guest_count = event_requirements["guest_count"]
        
        # Define service categories by event type
        service_categories = {
            "wedding": ["venue", "catering", "photography", "flowers", "music", "transportation"],
            "corporate_event": ["venue", "catering", "av_equipment", "photography", "branding", "entertainment"],
            "birthday": ["venue", "catering", "entertainment", "decorations", "photography", "cake"],
            "anniversary": ["venue", "catering", "flowers", "photography", "music", "special_touches"]
        }
        
        categories = service_categories.get(event_type, service_categories["wedding"])
        
        included_services = []
        optional_services = []
        
        for category in categories:
            service = await self._create_vendor_service(category, package_data, guest_count)
            
            # Determine if included or optional based on package level
            package_level = package_data.get("level", "premium").lower()
            if package_level == "luxury" or (package_level == "premium" and category in ["venue", "catering", "photography"]):
                included_services.append(service)
            else:
                optional_services.append(service)
        
        return {
            "included": included_services,
            "optional": optional_services
        }
    
    async def _create_vendor_service(self, category: str, package_data: Dict[str, Any], 
                                   guest_count: int) -> VendorService:
        """Create a specific vendor service"""
        
        # Service templates with pricing
        service_templates = {
            "venue": {
                "name": "Premium Event Venue",
                "description": "Beautiful venue with full amenities and professional staff",
                "base_price": 3000,
                "price_per_guest": 15
            },
            "catering": {
                "name": "Gourmet Catering Services",
                "description": "Full-service catering with customizable menu options",
                "base_price": 2000,
                "price_per_guest": 85
            },
            "photography": {
                "name": "Professional Event Photography",
                "description": "Full-day photography with edited high-resolution images",
                "base_price": 2500,
                "price_per_guest": 5
            },
            "flowers": {
                "name": "Floral Design & Arrangements",
                "description": "Custom floral designs including centerpieces and ceremony arrangements",
                "base_price": 1500,
                "price_per_guest": 12
            },
            "music": {
                "name": "Professional DJ & Sound",
                "description": "Professional DJ with premium sound system and lighting",
                "base_price": 1200,
                "price_per_guest": 3
            },
            "entertainment": {
                "name": "Live Entertainment",
                "description": "Professional entertainers customized to your event theme",
                "base_price": 1500,
                "price_per_guest": 8
            }
        }
        
        template = service_templates.get(category, {
            "name": f"{category.title()} Service",
            "description": f"Professional {category} service for your event",
            "base_price": 1000,
            "price_per_guest": 10
        })
        
        return VendorService(
            category=category,
            vendor_name=template["name"],
            service_description=template["description"],
            base_price=template["base_price"],
            price_per_guest=template.get("price_per_guest"),
            vendor_rating=4.8,
            portfolio_samples=[f"sample_{category}_1.jpg", f"sample_{category}_2.jpg"]
        )
    
    async def _calculate_detailed_pricing(self, package_options: List[PackageOption],
                                        event_requirements: Dict[str, Any],
                                        pricing_strategy: PricingStrategy) -> PricingCalculation:
        """Calculate detailed pricing with all adjustments and factors"""
        
        # Select recommended package (usually premium)
        recommended_package = next(
            (pkg for pkg in package_options if pkg.package_level == PackageLevel.PREMIUM),
            package_options[0] if package_options else None
        )
        
        if not recommended_package:
            raise Exception("No package available for pricing calculation")
        
        base_price = recommended_package.base_price
        guest_count = event_requirements["guest_count"]
        
        # Calculate various adjustments
        calculations = {
            "base_package_price": base_price,
            "guest_count_adjustment": self._calculate_guest_count_adjustment(base_price, guest_count),
            "location_adjustment": self._calculate_location_adjustment(base_price, event_requirements.get("location")),
            "date_premium": self._calculate_date_premium(base_price, event_requirements.get("event_date")),
            "seasonal_adjustment": self._calculate_seasonal_adjustment(base_price, event_requirements.get("event_date")),
            "urgency_premium": self._calculate_urgency_premium(base_price, event_requirements.get("event_date")),
            "complexity_adjustment": self._calculate_complexity_adjustment(base_price, event_requirements["complexity_level"]),
            "discount_applied": 0.0,  # Could be applied based on strategy
            "tax_amount": 0.0
        }
        
        # Calculate totals
        adjustments_total = sum([
            calculations["guest_count_adjustment"],
            calculations["location_adjustment"], 
            calculations["date_premium"],
            calculations["seasonal_adjustment"],
            calculations["urgency_premium"],
            calculations["complexity_adjustment"]
        ])
        
        total_before_tax = base_price + adjustments_total - calculations["discount_applied"]
        tax_amount = total_before_tax * 0.08  # 8% tax
        final_total = total_before_tax + tax_amount
        
        calculations.update({
            "total_before_tax": total_before_tax,
            "tax_amount": tax_amount,
            "final_total": final_total,
            "pricing_notes": self._generate_pricing_notes(calculations, event_requirements)
        })
        
        return PricingCalculation(**calculations)
    
    async def _generate_proposal_content(self, package_options: List[PackageOption],
                                       pricing_calculation: PricingCalculation,
                                       event_requirements: Dict[str, Any],
                                       prospect_data: ProspectData) -> ProposalContent:
        """Generate comprehensive proposal content using GPT-4"""
        
        content_generation_prompt = f"""
        Create compelling proposal content for this event planning prospect:

        PROSPECT: {prospect_data.name} ({prospect_data.prospect_type})
        EVENT TYPE: {event_requirements['event_type']}
        GUEST COUNT: {event_requirements['guest_count']}
        TOTAL INVESTMENT: ${pricing_calculation.final_total:,.2f}

        PACKAGES OFFERED:
        {json.dumps([{
            "name": pkg.package_name,
            "level": pkg.package_level.value,
            "description": pkg.description,
            "price": pkg.base_price,
            "features": pkg.features[:5]  # Top 5 features
        } for pkg in package_options], indent=2)}

        Create compelling content for:

        1. EXECUTIVE SUMMARY (2-3 sentences)
        - Capture their vision and our expertise
        - Highlight key value propositions

        2. EVENT VISION STATEMENT (1 paragraph)
        - Paint a picture of their perfect event
        - Emotional connection and excitement

        3. TIMELINE OVERVIEW
        - Key milestones from booking to event day
        - Critical planning phases

        4. UNIQUE VALUE PROPOSITIONS (3-5 points)
        - What sets us apart from competitors
        - Why they should choose our services

        5. TERMS AND CONDITIONS (key points)
        - Payment schedule
        - Cancellation policy
        - Change management

        6. NEXT STEPS (3-4 action items)
        - Clear path forward
        - Timeline for decision

        7. FAQ (5 common questions with answers)

        Return as structured JSON with compelling, professional content.
        """
        
        try:
            response = await self.openai_service.generate_agent_response(
                system_prompt="You are an expert proposal writer for event planning businesses. Create compelling, professional content that converts prospects to clients.",
                user_message=content_generation_prompt,
                model="gpt-5-nano"
            )
            
            content_data = json.loads(response)
            
            return ProposalContent(
                executive_summary=content_data.get("executive_summary", ""),
                event_vision_statement=content_data.get("event_vision_statement", ""),
                packages_offered=package_options,
                recommended_package=package_options[1] if len(package_options) > 1 else package_options[0],
                pricing_breakdown=pricing_calculation,
                timeline_overview=content_data.get("timeline_overview", {}),
                vendor_showcase=package_options[0].included_services if package_options else [],
                terms_and_conditions=content_data.get("terms_and_conditions", ""),
                next_steps=content_data.get("next_steps", []),
                validity_period=datetime.now().date() + timedelta(days=30),
                unique_value_propositions=content_data.get("unique_value_propositions", []),
                frequently_asked_questions=content_data.get("faq", [])
            )
            
        except Exception as e:
            logger.warning("Proposal content generation failed", error=str(e))
            return self._create_fallback_proposal_content(package_options, pricing_calculation, prospect_data)
    
    async def _generate_mood_board(self, event_requirements: Dict[str, Any], 
                                 proposal_content: ProposalContent) -> Optional[str]:
        """Generate mood board for the proposal"""
        
        try:
            # Use proposal MCP to create mood board
            mood_board_result = await proposal_mcp.server.call_tool(
                "create_mood_board",
                {
                    "event_type": event_requirements["event_type"],
                    "style_preferences": event_requirements.get("style_preferences", []),
                    "color_palette": ["elegant", "modern"],  # Could be extracted from requirements
                    "guest_count": event_requirements["guest_count"],
                    "venue_type": event_requirements.get("venue_type", "indoor")
                }
            )
            
            if not mood_board_result.isError:
                mood_board_data = json.loads(mood_board_result.content[0].text)
                return mood_board_data.get("mood_board_url")
            
        except Exception as e:
            logger.warning("Mood board generation failed", error=str(e))
        
        return None
    
    async def _generate_proposal_pdf(self, proposal_content: ProposalContent, 
                                   prospect_data: ProspectData) -> Optional[str]:
        """Generate professional PDF proposal"""
        
        try:
            # Prepare proposal data for PDF generation
            pdf_data = {
                "client_name": prospect_data.name,
                "proposal_title": f"{proposal_content.packages_offered[0].package_name if proposal_content.packages_offered else 'Event Planning'} Proposal",
                "executive_summary": proposal_content.executive_summary,
                "event_vision": proposal_content.event_vision_statement,
                "packages": [
                    {
                        "name": pkg.package_name,
                        "description": pkg.description,
                        "price": pkg.base_price,
                        "features": pkg.features
                    }
                    for pkg in proposal_content.packages_offered
                ],
                "pricing_breakdown": {
                    "base_price": proposal_content.pricing_breakdown.base_package_price,
                    "adjustments": proposal_content.pricing_breakdown.guest_count_adjustment + proposal_content.pricing_breakdown.complexity_adjustment,
                    "tax": proposal_content.pricing_breakdown.tax_amount,
                    "total": proposal_content.pricing_breakdown.final_total
                },
                "next_steps": proposal_content.next_steps,
                "terms": proposal_content.terms_and_conditions,
                "validity_date": proposal_content.validity_period.isoformat()
            }
            
            # Generate PDF using proposal MCP
            pdf_result = await proposal_mcp.server.call_tool(
                "generate_proposal_pdf",
                pdf_data
            )
            
            if not pdf_result.isError:
                pdf_data_result = json.loads(pdf_result.content[0].text)
                return pdf_data_result.get("pdf_url")
            
        except Exception as e:
            logger.warning("PDF generation failed", error=str(e))
        
        return None
    
    def _create_proposal_data(self, proposal_content: ProposalContent,
                            pricing_calculation: PricingCalculation,
                            mood_board_url: Optional[str],
                            proposal_pdf_url: Optional[str],
                            prospect_data: ProspectData) -> ProposalData:
        """Create ProposalData object from generated content"""
        
        return ProposalData(
            proposal_name=f"Event Proposal for {prospect_data.name}",
            total_price=pricing_calculation.final_total,
            guest_count=proposal_content.recommended_package.guest_count_range[1],
            event_date=datetime.now() + timedelta(days=90),  # Default future date
            event_type=proposal_content.packages_offered[0].package_name if proposal_content.packages_offered else "Custom Event",
            venue_details={
                "recommended_venues": ["Premium Event Space", "Elegant Garden Venue"],
                "venue_requirements": "Indoor/outdoor flexibility"
            },
            package_details={
                "recommended_package": proposal_content.recommended_package.package_name,
                "included_services": [svc.vendor_name for svc in proposal_content.recommended_package.included_services],
                "optional_services": [svc.vendor_name for svc in proposal_content.recommended_package.optional_services],
                "pricing_breakdown": {
                    "base_price": pricing_calculation.base_package_price,
                    "adjustments": pricing_calculation.guest_count_adjustment,
                    "tax": pricing_calculation.tax_amount,
                    "total": pricing_calculation.final_total
                }
            },
            proposal_pdf_url=proposal_pdf_url,
            mood_board_url=mood_board_url,
            valid_until=proposal_content.validity_period,
            terms_conditions=proposal_content.terms_and_conditions,
            proposal_metadata={
                "packages_count": len(proposal_content.packages_offered),
                "generation_timestamp": datetime.now().isoformat(),
                "pricing_strategy": "value",  # Could be passed from earlier
                "complexity_level": "moderate",  # Could be passed from earlier
                "unique_selling_points": proposal_content.unique_value_propositions,
                "next_steps": proposal_content.next_steps
            }
        )
    
    async def _store_proposal_in_database(self, proposal_data: ProposalData, prospect_id: Optional[int]):
        """Store proposal in database"""
        if not prospect_id:
            return
        
        try:
            result = await database_mcp.server.call_tool(
                "execute_query",
                {
                    "query": """
                    INSERT INTO proposals (
                        prospect_id, proposal_name, total_price, guest_count, 
                        event_date, venue_details, package_details, 
                        proposal_pdf_url, mood_board_url, valid_until, 
                        terms_conditions, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    "parameters": [
                        prospect_id,
                        proposal_data.proposal_name,
                        proposal_data.total_price,
                        proposal_data.guest_count,
                        proposal_data.event_date.isoformat(),
                        json.dumps(proposal_data.venue_details),
                        json.dumps(proposal_data.package_details),
                        proposal_data.proposal_pdf_url,
                        proposal_data.mood_board_url,
                        proposal_data.valid_until.isoformat(),
                        proposal_data.terms_conditions,
                        "draft"
                    ],
                    "fetch_mode": "none"
                }
            )
            
            if not result.isError:
                # Get proposal ID
                id_result = await database_mcp.server.call_tool(
                    "execute_query",
                    {"query": "SELECT LAST_INSERT_ID() as id", "fetch_mode": "one"}
                )
                
                if not id_result.isError:
                    id_data = json.loads(id_result.content[0].text)
                    proposal_data.id = id_data.get("result", {}).get("id")
            
        except Exception as e:
            logger.error("Failed to store proposal in database", error=str(e))
    
    async def _update_prospect_status(self, prospect_id: Optional[int], status: ProspectStatus):
        """Update prospect status after proposal generation"""
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
    
    # Helper methods for pricing calculations
    
    def _calculate_guest_count_adjustment(self, base_price: float, guest_count: int) -> float:
        """Calculate adjustment based on guest count"""
        # Assume base price is for 100 guests
        base_guest_count = 100
        if guest_count > base_guest_count:
            return (guest_count - base_guest_count) * 50  # $50 per additional guest
        elif guest_count < base_guest_count:
            return -(base_guest_count - guest_count) * 30  # $30 discount per fewer guest
        return 0.0
    
    def _calculate_location_adjustment(self, base_price: float, location: Optional[str]) -> float:
        """Calculate adjustment based on location"""
        if not location:
            return 0.0
        
        # High-cost areas get premium
        high_cost_areas = ["new york", "san francisco", "los angeles", "miami", "chicago"]
        location_lower = location.lower()
        
        for area in high_cost_areas:
            if area in location_lower:
                return base_price * 0.15  # 15% premium
        
        return 0.0
    
    def _calculate_date_premium(self, base_price: float, event_date: Optional[str]) -> float:
        """Calculate premium for popular dates"""
        if not event_date:
            return 0.0
        
        try:
            event_datetime = datetime.fromisoformat(event_date)
            
            # Weekend premium
            if event_datetime.weekday() >= 5:  # Saturday or Sunday
                return base_price * 0.10  # 10% weekend premium
            
            # Holiday premium (simplified)
            month = event_datetime.month
            day = event_datetime.day
            
            # December (holiday season)
            if month == 12:
                return base_price * 0.20  # 20% holiday premium
            
            # June (wedding season)
            if month == 6:
                return base_price * 0.15  # 15% wedding season premium
                
        except Exception:
            pass
        
        return 0.0
    
    def _calculate_seasonal_adjustment(self, base_price: float, event_date: Optional[str]) -> float:
        """Calculate seasonal adjustment"""
        if not event_date:
            return 0.0
        
        try:
            event_datetime = datetime.fromisoformat(event_date)
            month = event_datetime.month
            
            # Peak season (May-September)
            if 5 <= month <= 9:
                return base_price * 0.10  # 10% peak season premium
            
            # Off-season discount (January-March)
            if 1 <= month <= 3:
                return -base_price * 0.05  # 5% off-season discount
                
        except Exception:
            pass
        
        return 0.0
    
    def _calculate_urgency_premium(self, base_price: float, event_date: Optional[str]) -> float:
        """Calculate premium for rush jobs"""
        if not event_date:
            return 0.0
        
        try:
            event_datetime = datetime.fromisoformat(event_date)
            days_until_event = (event_datetime - datetime.now()).days
            
            if days_until_event < 30:  # Less than 30 days
                return base_price * self.rush_job_premium
            elif days_until_event < 60:  # Less than 60 days
                return base_price * (self.rush_job_premium / 2)
                
        except Exception:
            pass
        
        return 0.0
    
    def _calculate_complexity_adjustment(self, base_price: float, complexity_level: str) -> float:
        """Calculate adjustment based on event complexity"""
        multiplier = self.complexity_multipliers.get(complexity_level, 1.0)
        return base_price * (multiplier - 1.0)
    
    def _generate_pricing_notes(self, calculations: Dict[str, float], 
                              event_requirements: Dict[str, Any]) -> List[str]:
        """Generate human-readable pricing notes"""
        notes = []
        
        if calculations["guest_count_adjustment"] > 0:
            notes.append(f"Additional guest premium for {event_requirements['guest_count']} guests")
        elif calculations["guest_count_adjustment"] < 0:
            notes.append(f"Small event discount for {event_requirements['guest_count']} guests")
        
        if calculations["location_adjustment"] > 0:
            notes.append(f"Premium location surcharge for {event_requirements.get('location', 'specified area')}")
        
        if calculations["complexity_adjustment"] > 0:
            notes.append(f"Complexity adjustment for {event_requirements['complexity_level']} event requirements")
        
        if calculations["urgency_premium"] > 0:
            notes.append("Rush service premium for short timeline")
        
        return notes
    
    # Fallback methods
    
    def _create_fallback_packages(self, event_requirements: Dict[str, Any]) -> List[PackageOption]:
        """Create fallback packages when generation fails"""
        guest_count = event_requirements["guest_count"]
        
        return [
            PackageOption(
                package_id="essential",
                package_name="Essential Package",
                package_level=PackageLevel.ESSENTIAL,
                description="Core event planning services to make your celebration memorable",
                base_price=guest_count * 75,
                included_services=[],
                optional_services=[],
                features=["Event coordination", "Basic vendor management", "Timeline creation"],
                guest_count_range=(20, 150),
                ideal_for=["Budget-conscious clients", "Simple celebrations"],
                what_makes_special="Affordable professional planning"
            ),
            PackageOption(
                package_id="premium",
                package_name="Premium Package", 
                package_level=PackageLevel.PREMIUM,
                description="Comprehensive event planning with enhanced services and attention to detail",
                base_price=guest_count * 150,
                included_services=[],
                optional_services=[],
                features=["Full event coordination", "Vendor sourcing and management", "Design consultation", "Day-of coordination"],
                guest_count_range=(50, 300),
                ideal_for=["Most celebrations", "Quality-focused clients"],
                what_makes_special="Perfect balance of service and value"
            )
        ]
    
    def _create_fallback_proposal_content(self, package_options: List[PackageOption],
                                        pricing_calculation: PricingCalculation,
                                        prospect_data: ProspectData) -> ProposalContent:
        """Create fallback proposal content when generation fails"""
        
        return ProposalContent(
            executive_summary=f"We're excited to create an unforgettable event for {prospect_data.name}. Our comprehensive planning services will ensure every detail is perfect.",
            event_vision_statement="Your event will be a seamless blend of elegance, joy, and unforgettable moments that reflect your unique style and vision.",
            packages_offered=package_options,
            recommended_package=package_options[0] if package_options else None,
            pricing_breakdown=pricing_calculation,
            timeline_overview={
                "Planning Phase": "8-12 weeks before event",
                "Final Preparations": "2 weeks before event", 
                "Event Day": "Full coordination and management"
            },
            vendor_showcase=[],
            terms_and_conditions="Standard terms and conditions apply. 50% deposit required to secure date.",
            next_steps=[
                "Review this proposal",
                "Schedule consultation call",
                "Finalize contract and deposit",
                "Begin detailed planning"
            ],
            validity_period=datetime.now().date() + timedelta(days=30),
            unique_value_propositions=[
                "Experienced event professionals",
                "Comprehensive vendor network",
                "Attention to every detail"
            ],
            frequently_asked_questions=[
                {"question": "What's included in the planning fee?", "answer": "Full event coordination and management"},
                {"question": "Can we customize the package?", "answer": "Yes, all packages can be tailored to your needs"}
            ]
        )
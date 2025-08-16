"""
Mock prospect data for testing enrichment agent with real event planning contexts.

These are real prospect scenarios that the enrichment agent can research
using the Sonar API to validate functionality.
"""

from app.core.state import ProspectData
from app.db.models import ProspectStatus
from typing import List

# Real, researchable prospects for testing with Perplexity Sonar API
MOCK_PROSPECTS: List[ProspectData] = [
    ProspectData(
        id=1,
        name="Reid Hoffman",
        email="reid@linkedin.com",
        company_name="Greylock Partners",
        location="Palo Alto, CA",
        prospect_type="corporate",
        source="corporate_event_search",
        status=ProspectStatus.DISCOVERED,
        lead_score=95
    ),
    
    ProspectData(
        id=2,
        name="Jessica Chen",
        email="jchen@airbnb.com", 
        company_name="Airbnb",
        location="San Francisco, CA",
        prospect_type="corporate",
        source="corporate_retreat_search",
        status=ProspectStatus.DISCOVERED,
        lead_score=90
    ),
    
    ProspectData(
        id=3,
        name="Brian Chesky",
        email="brian@airbnb.com",
        company_name="Airbnb",
        location="San Francisco, CA",
        prospect_type="corporate",
        source="executive_event_search",
        status=ProspectStatus.DISCOVERED,
        lead_score=98
    ),
    
    ProspectData(
        id=4,
        name="Patrick Collison",
        email="patrick@stripe.com",
        company_name="Stripe",
        location="San Francisco, CA", 
        prospect_type="corporate",
        source="tech_event_search",
        status=ProspectStatus.DISCOVERED,
        lead_score=92
    )
]

# Expected enrichment insights for real prospects
EXPECTED_INSIGHTS = {
    "Reid Hoffman": {
        "event_type": "corporate_networking",
        "expected_timeline": "quarterly events",
        "expected_budget_range": "50000-100000",
        "expected_personalization": ["venture capital networking", "entrepreneur events", "Silicon Valley connections"],
        "expected_data_sources": ["linkedin", "greylock_website", "vc_news", "speaking_events"]
    },
    
    "Jessica Chen": {
        "event_type": "corporate_retreat", 
        "expected_timeline": "annual planning",
        "expected_budget_range": "30000-75000",
        "expected_personalization": ["Airbnb company culture", "remote team building", "travel industry"],
        "expected_data_sources": ["linkedin", "airbnb_careers", "tech_news"]
    },
    
    "Brian Chesky": {
        "event_type": "executive_events",
        "expected_timeline": "ongoing",
        "expected_budget_range": "75000-150000", 
        "expected_personalization": ["CEO-level events", "Airbnb brand events", "hospitality industry"],
        "expected_data_sources": ["linkedin", "airbnb_news", "ceo_interviews", "company_events"]
    },
    
    "Patrick Collison": {
        "event_type": "tech_conferences",
        "expected_timeline": "regular speaking",
        "expected_budget_range": "40000-80000", 
        "expected_personalization": ["fintech events", "Stripe developer conferences", "payment industry"],
        "expected_data_sources": ["linkedin", "stripe_blog", "tech_conferences", "developer_events"]
    }
}

def get_mock_prospect_by_name(name: str) -> ProspectData:
    """Get mock prospect data by name"""
    for prospect in MOCK_PROSPECTS:
        if prospect.name == name:
            return prospect
    raise ValueError(f"Mock prospect '{name}' not found")

def get_all_mock_prospects() -> List[ProspectData]:
    """Get all mock prospects for testing"""
    return MOCK_PROSPECTS.copy()

def get_expected_insights_for_prospect(name: str) -> dict:
    """Get expected enrichment insights for validation"""
    return EXPECTED_INSIGHTS.get(name, {})
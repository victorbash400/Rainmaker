from datetime import datetime
from app.core.state import ProspectData, EnrichmentData
from app.db.models import ProspectStatus

# Mock data for testing the OutreachAgent.
# This simulates the data that would be passed down from the EnrichmentAgent.

mock_prospect_1 = ProspectData(
    id=101,
    name="Jane Doe",
    email="jane.doe@example.com",
    company_name="Innovate Inc.",
    location="San Francisco, CA",
    prospect_type="company",
    source="linkedin_search",
    status=ProspectStatus.ENRICHED,
    lead_score=85
)

mock_enrichment_1 = EnrichmentData(
    personal_info={
        "role": "Marketing Director",
        "background": "10+ years in tech marketing, frequent speaker at industry events.",
        "linkedin": "https://linkedin.com/in/janedoe-example"
    },
    company_info={
        "industry": "SaaS",
        "size": "200-500 employees",
        "recent_news": "Innovate Inc. recently secured $20M in Series B funding."
    },
    event_context={
        "event_type": "Corporate Event",
        "timeline": "Likely planning for Q4 annual sales kickoff.",
        "requirements": "Looking for a modern, tech-enabled venue for ~150 people."
    },
    ai_insights={
        "budget_indicators": "Company is well-funded, likely has a healthy event budget.",
        "outreach_approach": "Congratulate on the recent funding round. Focus on high-tech and branding opportunities for their sales kickoff.",
        "personalization": "Mention her recent talk on 'Future of B2B Marketing' to show you've done your research."
    },
    data_sources=["sonar_person_search", "sonar_company_search"],
    citations=[
        {"title": "Innovate Inc. Raises $20M", "url": "https://techcrunch.com/example-innovate"},
        {"title": "Jane Doe | LinkedIn", "url": "https://linkedin.com/in/janedoe-example"}
    ],
    last_enriched=datetime.now()
)

mock_prospect_2 = ProspectData(
    id=102,
    name="John Smith",
    email="john.smith@example.com",
    location="New York, NY",
    prospect_type="individual",
    source="web_search",
    status=ProspectStatus.ENRICHED,
    lead_score=70
)

mock_enrichment_2 = EnrichmentData(
    personal_info={
        "background": "Recently engaged, posts on social media about wedding planning.",
        "instagram": "https://instagram.com/johnsmith-example"
    },
    company_info={},
    event_context={
        "event_type": "Wedding",
        "timeline": "Appears to be looking at venues for next fall.",
        "requirements": "Expressed interest in rustic, outdoor venues. Guest count seems to be around 100-120."
    },
    ai_insights={
        "budget_indicators": "Mid-range budget based on venue styles discussed.",
        "outreach_approach": "Focus on creating a unique, personalized wedding experience. Use a warm, celebratory tone.",
        "personalization": "Reference a specific venue style he liked on his public social media."
    },
    data_sources=["sonar_event_search"],
    citations=[
        {"title": "John S. | The Knot", "url": "https://www.theknot.com/us/john-smith-example"}
    ],
    last_enriched=datetime.now()
)


# A list containing tuples of (ProspectData, EnrichmentData)
mock_data = [
    (mock_prospect_1, mock_enrichment_1),
    (mock_prospect_2, mock_enrichment_2)
]

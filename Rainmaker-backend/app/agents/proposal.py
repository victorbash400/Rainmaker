"""
Proposal Agent - Generates professional event planning proposals as PDFs
Uses AI to intelligently process raw data and create beautiful, modern proposals
"""
import asyncio
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
import structlog
from jinja2 import Template
from playwright.async_api import async_playwright

# Import Gemini service for AI processing
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

# For standalone testing, create a simple mock gemini service
class MockGeminiService:
    async def generate_json_response(self, system_prompt: str, user_message: str) -> dict:
        """Mock AI response for testing"""
        return {
            "event_type": "Holiday Party",
            "event_vision": "Transform your corporate holiday celebration into an unforgettable experience that brings your team together, recognizes achievements, and creates lasting memories. This 150-person event will blend professional elegance with festive joy, fostering connection and appreciation while reflecting your company's commitment to its people.",
            "guest_count": 150,
            "budget_estimate": 35000,
            "timeline": "8-10 weeks",
            "key_requirements": ["Professional coordination", "Premium catering with dietary options", "Team building activities", "Professional photography", "Live entertainment", "Memorable experience"],
            "special_considerations": ["Dietary accommodations", "Inclusive entertainment", "Networking opportunities", "Recognition ceremony"]
        }

try:
    from services.gemini_service import gemini_service
except ImportError:
    gemini_service = MockGeminiService()

from agents.proposal_template import MODERN_PROPOSAL_TEMPLATE

logger = structlog.get_logger(__name__)

class ProposalAgent:
    """AI agent that generates professional event planning proposals"""
    
    def __init__(self):
        self.output_dir = Path(__file__).parent.parent / "generated" / "proposals"
        
        # Ensure directories exist
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info("ProposalAgent initialized with AI-powered processing")
    
    async def generate_proposal(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a professional proposal from raw outreach data using AI
        
        Args:
            raw_data: Raw data from outreach agent (conversation, prospect info, event details)
            
        Returns:
            Dict with proposal details and PDF file path
        """
        logger.info("Generating AI-powered proposal", client=raw_data.get("client_company"))
        
        try:
            # 1. Use AI to analyze and structure the raw data
            structured_data = await self._ai_process_raw_data(raw_data)
            
            # 2. Generate modern HTML template with AI insights
            html_content = await self._generate_modern_html_proposal(structured_data)
            
            # 3. Convert to high-quality PDF
            pdf_path = await self._convert_to_pdf(html_content, structured_data)
            
            # 4. Prepare response
            result = {
                "status": "success",
                "proposal_id": structured_data["proposal_id"],
                "client_company": structured_data["client_company"],
                "event_type": structured_data["event_type"],
                "total_investment": structured_data["total_investment"],
                "pdf_file_path": str(pdf_path),
                "generated_at": datetime.now().isoformat(),
                "valid_until": (datetime.now() + timedelta(days=14)).isoformat()
            }
            
            logger.info("AI-powered proposal generated successfully", proposal_id=result["proposal_id"])
            return result
            
        except Exception as e:
            logger.error("Failed to generate proposal", error=str(e))
            return {
                "status": "error",
                "message": f"Failed to generate proposal: {str(e)}"
            }
    
    async def _ai_process_raw_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Use AI to intelligently process raw outreach data into structured proposal content"""
        
        # Generate unique proposal ID
        client_name = raw_data.get('client_company', 'CLIENT')
        proposal_id = f"PROP_{client_name.upper().replace(' ', '')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Use Gemini AI to analyze and structure the data
        ai_analysis = await self._get_ai_analysis(raw_data)
        
        # Structure the data for proposal generation
        structured_data = {
            "proposal_id": proposal_id,
            "client_company": client_name,
            "event_type": ai_analysis.get("event_type", "Corporate Event"),
            "event_vision": ai_analysis.get("event_vision", ""),
            "key_requirements": ai_analysis.get("key_requirements", []),
            "guest_count": ai_analysis.get("guest_count", 100),
            "budget_estimate": ai_analysis.get("budget_estimate", 25000),
            "timeline": ai_analysis.get("timeline", "8 weeks"),
            "packages": await self._generate_smart_packages(ai_analysis),
            "total_investment": 0,  # Will be set by packages
            "generated_date": datetime.now().strftime("%B %d, %Y"),
            "valid_until_date": (datetime.now() + timedelta(days=14)).strftime("%B %d, %Y"),
            "contact_info": {
                "name": "Sarah Mitchell",
                "title": "Senior Event Strategist",
                "email": "sarah@rainmaker.events",
                "phone": "(555) 123-4567"
            }
        }
        
        # Set total investment from signature package
        if structured_data["packages"]:
            structured_data["total_investment"] = structured_data["packages"][1]["price"]
        
        return structured_data
    
    async def _get_ai_analysis(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Use Gemini AI to analyze raw outreach data and extract key insights"""
        
        system_prompt = (
            "You are an expert event planning analyst. Analyze the provided raw outreach data "
            "and extract key event requirements and insights. Focus on understanding the client's "
            "vision, requirements, budget indicators, and event scale. Be intelligent about inferring "
            "missing details based on context clues."
        )
        
        user_message = f"""
        Analyze this raw outreach data and provide structured insights:
        
        **Raw Data:**
        {json.dumps(raw_data, indent=2)}
        
        **Instructions:**
        Extract and infer the following information. Use intelligent assumptions based on context:
        - Event type and purpose
        - Expected guest count (infer from company size, event type)
        - Budget estimate (based on event type, guest count, location)
        - Key requirements and client vision
        - Timeline preferences
        - Special considerations
        
        Return ONLY a valid JSON object with these keys:
        {{
            "event_type": "specific event type",
            "event_vision": "compelling vision statement",
            "guest_count": number,
            "budget_estimate": number,
            "timeline": "timeline description",
            "key_requirements": ["requirement1", "requirement2", ...],
            "special_considerations": ["consideration1", "consideration2", ...]
        }}
        """
        
        try:
            analysis = await gemini_service.generate_json_response(
                system_prompt=system_prompt,
                user_message=user_message
            )
            return analysis
        except Exception as e:
            logger.warning(f"AI analysis failed, using fallback: {e}")
            # Fallback to enhanced mock analysis based on input data
            guest_count = raw_data.get("guest_count", 150)
            event_type = raw_data.get("event_type", "Holiday Party")
            
            return {
                "event_type": event_type,
                "event_vision": f"Transform your {event_type.lower()} into an unforgettable experience that brings people together, celebrates achievements, and creates lasting memories. This {guest_count}-person event will blend professionalism with celebration, ensuring every detail reflects your company's values and vision.",
                "guest_count": guest_count,
                "budget_estimate": guest_count * 200,  # Dynamic based on guest count
                "timeline": "8 weeks",
                "key_requirements": ["Professional coordination", "Premium catering", "Team building activities", "Professional photography", "Memorable experience"],
                "special_considerations": ["Dietary accommodations", "Entertainment", "Networking opportunities"]
            }
    
    async def _generate_smart_packages(self, ai_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate intelligent packages based on AI analysis"""
        guest_count = ai_analysis.get("guest_count", 100)
        budget_estimate = ai_analysis.get("budget_estimate", 25000)
        event_type = ai_analysis.get("event_type", "Corporate Event")
        
        # Smart pricing based on guest count and event type
        base_per_person = max(150, budget_estimate * 0.8 / guest_count)
        
        packages = [
            {
                "name": "Essential",
                "price": int(base_per_person * 0.8 * guest_count),
                "per_person": int(base_per_person * 0.8),
                "description": "Perfect foundation for memorable events",
                "features": [
                    "Professional event coordination",
                    "Venue selection & booking",
                    "Standard catering package",
                    "Basic audio/visual setup",
                    "Event timeline management",
                    "Day-of coordination"
                ]
            },
            {
                "name": "Signature",
                "price": int(base_per_person * guest_count),
                "per_person": int(base_per_person),
                "description": "Enhanced experience with premium touches",
                "recommended": True,
                "features": [
                    "Everything in Essential, plus:",
                    "Premium catering with dietary options",
                    "Enhanced decor & ambient lighting",
                    "Professional photography (4 hours)",
                    "Welcome reception setup",
                    "Branded event materials",
                    "Post-event cleanup"
                ]
            },
            {
                "name": "Premium",
                "price": int(base_per_person * 1.3 * guest_count),
                "per_person": int(base_per_person * 1.3),
                "description": "Luxury experience with white-glove service",
                "features": [
                    "Everything in Signature, plus:",
                    "Luxury catering with chef stations",
                    "Custom decor & floral arrangements",
                    "Full photography & videography",
                    "Live entertainment coordination",
                    "VIP guest management",
                    "Custom event app",
                    "24/7 event support"
                ]
            }
        ]
        
        return packages
    
    async def _generate_modern_html_proposal(self, data: Dict[str, Any]) -> str:
        """Generate modern HTML proposal using clean Apple-inspired design"""
        
        template = Template(MODERN_PROPOSAL_TEMPLATE)
        html_content = template.render(**data)
        
        return html_content
    
    async def _convert_to_pdf(self, html_content: str, data: Dict[str, Any]) -> Path:
        """Convert HTML to high-quality PDF using Playwright"""
        pdf_path = self.output_dir / f"{data['proposal_id']}.pdf"
        
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            
            # Set content and wait for any potential loading
            await page.set_content(html_content, wait_until='networkidle')
            
            # Generate PDF with optimized pagination settings
            await page.pdf(
                path=str(pdf_path),
                format='A4',
                print_background=True,
                margin={
                    'top': '0.75in',
                    'bottom': '0.75in',
                    'left': '0.75in',
                    'right': '0.75in'
                },
                prefer_css_page_size=True,
                display_header_footer=False
            )
            
            await browser.close()
        
        logger.info("High-quality PDF proposal generated", file_path=str(pdf_path))
        return pdf_path


# Test function for independent testing
async def test_proposal_agent():
    """Test the AI-powered proposal agent with mock data"""
    
    mock_data = {
        "client_company": "TechFlow Solutions",
        "event_type": "Holiday Party",
        "guest_count": 150,
        "industry": "Technology",
        "location": "San Francisco, CA",
        "conversation_summary": "Client interested in corporate holiday party, emphasized team building and appreciation",
        "budget_indicators": ["mid-range budget", "quality focused", "willing to invest in experience"],
        "special_requirements": [
            "Dietary restrictions accommodations",
            "Professional photography",
            "Live entertainment"
        ]
    }
    
    agent = ProposalAgent()
    result = await agent.generate_proposal(mock_data)
    
    print("\n" + "="*60)
    print("AI-POWERED PROPOSAL AGENT TEST RESULTS")
    print("="*60)
    print(f"Status: {result['status']}")
    
    if result['status'] == 'success':
        print(f"Proposal ID: {result['proposal_id']}")
        print(f"Client: {result['client_company']}")
        print(f"Event Type: {result['event_type']}")
        print(f"Total Investment: ${result['total_investment']:,}")
        print(f"PDF File: {result['pdf_file_path']}")
        print(f"Generated At: {result['generated_at']}")
        print(f"Valid Until: {result['valid_until']}")
        
        # Check if PDF exists
        if os.path.exists(result['pdf_file_path']):
            print("✅ AI-powered PDF proposal created successfully!")
            print(f"📄 Open this file to view: {result['pdf_file_path']}")
        else:
            print("❌ PDF file not found")
    else:
        print(f"❌ Error: {result['message']}")
    
    print("="*60)
    return result


if __name__ == "__main__":
    # Run test when script is executed directly
    asyncio.run(test_proposal_agent())
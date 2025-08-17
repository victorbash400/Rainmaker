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
from app.services.gemini_service import gemini_service
from .proposal_template import MODERN_PROPOSAL_TEMPLATE

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
            # Fallback to basic analysis
            return {
                "event_type": raw_data.get("event_type", "Corporate Event"),
                "event_vision": "Create an exceptional event experience that exceeds expectations.",
                "guest_count": 100,
                "budget_estimate": 25000,
                "timeline": "8 weeks",
                "key_requirements": ["Professional coordination", "Quality catering", "Memorable experience"],
                "special_considerations": ["Client satisfaction", "Attention to detail"]
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
    
    async def _generate_event_vision(self, data: Dict[str, Any]) -> str:
        """Generate AI-powered event vision statement"""
        event_type = data.get("event_type", "corporate event")
        industry = data.get("industry", "business")
        guest_count = data.get("guest_count", 100)
        
        # Mock AI-generated content (in real implementation, use Gemini)
        visions = {
            "holiday_party": f"Transform your workplace into a winter wonderland where colleagues become friends and achievements are celebrated. This {guest_count}-person holiday celebration will blend professional excellence with festive joy, creating lasting memories while strengthening team bonds.",
            
            "product_launch": f"Unveil your innovation with an unforgettable launch event that positions your brand at the forefront of the {industry} industry. This exclusive {guest_count}-guest experience will generate buzz, engage media, and leave attendees excited about your product's potential.",
            
            "corporate_event": f"Elevate your corporate gathering beyond the ordinary with a sophisticated {guest_count}-person event that reflects your company's values and vision. Every detail will be crafted to inspire, connect, and showcase your organization's commitment to excellence.",
            
            "conference": f"Create a dynamic learning environment where industry leaders and professionals converge to share insights and forge valuable connections. This {guest_count}-attendee conference will be a catalyst for innovation and professional growth.",
            
            "gala": f"Host an elegant gala that embodies sophistication and purpose, bringing together {guest_count} distinguished guests for an evening of celebration, networking, and meaningful impact. Every element will reflect the prestige of your organization."
        }
        
        return visions.get(event_type.lower().replace(" ", "_"), visions["corporate_event"])
    
    async def _generate_packages(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate three-tier package options based on budget and requirements"""
        base_budget = data.get("budget_estimate", 25000)
        guest_count = data.get("guest_count", 100)
        
        # Calculate per-person costs
        essential_per_person = max(150, base_budget * 0.7 / guest_count)
        signature_per_person = max(200, base_budget / guest_count)
        premium_per_person = max(300, base_budget * 1.4 / guest_count)
        
        packages = [
            {
                "name": "Essential",
                "price": int(essential_per_person * guest_count),
                "per_person": int(essential_per_person),
                "description": "Perfect foundation for a memorable event",
                "features": [
                    "Professional event coordination",
                    "Venue selection and booking",
                    "Standard catering package",
                    "Basic audio/visual setup",
                    "Event timeline management",
                    "Day-of coordination"
                ]
            },
            {
                "name": "Signature",
                "price": int(signature_per_person * guest_count),
                "per_person": int(signature_per_person),
                "description": "Enhanced experience with premium touches",
                "features": [
                    "Everything in Essential, plus:",
                    "Premium catering with dietary options",
                    "Enhanced decor and ambient lighting",
                    "Professional photography (4 hours)",
                    "Welcome reception setup",
                    "Branded event materials",
                    "Post-event cleanup"
                ],
                "recommended": True
            },
            {
                "name": "Premium",
                "price": int(premium_per_person * guest_count),
                "per_person": int(premium_per_person),
                "description": "Luxury experience with white-glove service",
                "features": [
                    "Everything in Signature, plus:",
                    "Luxury catering with chef stations",
                    "Custom decor and floral arrangements",
                    "Full photography and videography",
                    "Live entertainment coordination",
                    "VIP guest management",
                    "Custom event app",
                    "24/7 event support"
                ]
            }
        ]
        
        return packages
    
    async def _generate_timeline(self, data: Dict[str, Any]) -> List[Dict[str, str]]:
        """Generate event planning timeline"""
        event_date = data.get("event_date", "TBD")
        
        timeline = [
            {
                "phase": "Proposal Acceptance",
                "timeframe": "Week 1",
                "description": "Contract signing, deposit, and initial planning kickoff"
            },
            {
                "phase": "Venue & Vendor Selection", 
                "timeframe": "Weeks 2-3",
                "description": "Finalize venue, catering, and key vendor partnerships"
            },
            {
                "phase": "Design & Details",
                "timeframe": "Weeks 4-6", 
                "description": "Menu selection, decor planning, and timeline refinement"
            },
            {
                "phase": "Final Preparations",
                "timeframe": "Weeks 7-8",
                "description": "Guest confirmations, final headcount, and setup coordination"
            },
            {
                "phase": "Event Execution",
                "timeframe": f"Event Day - {event_date}",
                "description": "Full day-of coordination and flawless event delivery"
            },
            {
                "phase": "Post-Event",
                "timeframe": "Week After",
                "description": "Event wrap-up, final invoicing, and feedback collection"
            }
        ]
        
        return timeline
    
    async def _generate_modern_html_proposal(self, data: Dict[str, Any]) -> str:
        """Generate modern HTML proposal using clean Apple-inspired design"""
        
        template = Template(MODERN_PROPOSAL_TEMPLATE)
        html_content = template.render(**data)
        
        return html_content
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Event Proposal - {{ client_company }}</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            background: white;
        }
        
        .page {
            max-width: 800px;
            margin: 0 auto;
            padding: 40px;
            min-height: 100vh;
        }
        
        /* Cover Page */
        .cover {
            text-align: center;
            padding: 60px 0;
            background: linear-gradient(135deg, #1a1a1a 0%, #333 100%);
            color: white;
            border-radius: 12px;
            margin-bottom: 40px;
        }
        
        .logo {
            width: 60px;
            height: 60px;
            background: white;
            border-radius: 50%;
            margin: 0 auto 30px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            color: #1a1a1a;
            font-size: 24px;
        }
        
        .cover h1 {
            font-size: 2.5rem;
            margin-bottom: 10px;
            font-weight: 300;
        }
        
        .cover .subtitle {
            font-size: 1.2rem;
            opacity: 0.9;
            margin-bottom: 30px;
        }
        
        .cover .details {
            font-size: 1rem;
            opacity: 0.8;
        }
        
        /* Section Styling */
        .section {
            margin: 40px 0;
            padding: 30px;
            background: #fafafa;
            border-radius: 8px;
            border-left: 4px solid #1a1a1a;
        }
        
        .section h2 {
            font-size: 1.8rem;
            margin-bottom: 20px;
            color: #1a1a1a;
        }
        
        .section h3 {
            font-size: 1.3rem;
            margin: 20px 0 10px;
            color: #333;
        }
        
        /* Package Cards */
        .packages {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin: 30px 0;
        }
        
        .package {
            background: white;
            border: 2px solid #e5e7eb;
            border-radius: 12px;
            padding: 25px;
            text-align: center;
            position: relative;
            transition: transform 0.2s ease;
        }
        
        .package:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 20px rgba(0,0,0,0.1);
        }
        
        .package.recommended {
            border-color: #1a1a1a;
            background: #f8f9fa;
        }
        
        .package.recommended::before {
            content: "RECOMMENDED";
            position: absolute;
            top: -10px;
            left: 50%;
            transform: translateX(-50%);
            background: #1a1a1a;
            color: white;
            padding: 5px 15px;
            border-radius: 15px;
            font-size: 0.7rem;
            font-weight: bold;
        }
        
        .package-name {
            font-size: 1.4rem;
            font-weight: bold;
            margin-bottom: 10px;
            color: #1a1a1a;
        }
        
        .package-price {
            font-size: 2rem;
            font-weight: bold;
            color: #1a1a1a;
            margin-bottom: 5px;
        }
        
        .package-per-person {
            color: #666;
            margin-bottom: 15px;
        }
        
        .package-description {
            color: #666;
            margin-bottom: 20px;
            font-style: italic;
        }
        
        .package-features {
            text-align: left;
            list-style: none;
        }
        
        .package-features li {
            margin: 8px 0;
            padding-left: 20px;
            position: relative;
        }
        
        .package-features li::before {
            content: "✓";
            position: absolute;
            left: 0;
            color: #10b981;
            font-weight: bold;
        }
        
        /* Investment Breakdown */
        .investment-table {
            width: 100%;
            border-collapse: collapse;
            background: white;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        
        .investment-table th,
        .investment-table td {
            padding: 15px;
            text-align: left;
            border-bottom: 1px solid #e5e7eb;
        }
        
        .investment-table th {
            background: #1a1a1a;
            color: white;
            font-weight: 600;
        }
        
        .investment-table .total-row {
            background: #f8f9fa;
            font-weight: bold;
            font-size: 1.1rem;
        }
        
        /* Timeline */
        .timeline {
            position: relative;
            padding-left: 30px;
        }
        
        .timeline::before {
            content: '';
            position: absolute;
            left: 15px;
            top: 0;
            bottom: 0;
            width: 2px;
            background: #e5e7eb;
        }
        
        .timeline-item {
            position: relative;
            margin-bottom: 30px;
            padding: 15px 20px;
            background: white;
            border-radius: 8px;
            border: 1px solid #e5e7eb;
        }
        
        .timeline-item::before {
            content: '';
            position: absolute;
            left: -27px;
            top: 20px;
            width: 12px;
            height: 12px;
            background: #1a1a1a;
            border-radius: 50%;
        }
        
        .timeline-phase {
            font-weight: bold;
            color: #1a1a1a;
            margin-bottom: 5px;
        }
        
        .timeline-timeframe {
            color: #666;
            font-size: 0.9rem;
            margin-bottom: 8px;
        }
        
        /* Contact Info */
        .contact-info {
            background: #1a1a1a;
            color: white;
            padding: 30px;
            border-radius: 8px;
            text-align: center;
        }
        
        .contact-info h3 {
            margin-bottom: 20px;
            color: white;
        }
        
        .contact-details {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            text-align: left;
        }
        
        .contact-item {
            color: #ccc;
        }
        
        .contact-item strong {
            color: white;
            display: block;
            margin-bottom: 5px;
        }
        
        /* Print Styles */
        @media print {
            .page {
                padding: 20px;
            }
            
            .section {
                break-inside: avoid;
                margin: 20px 0;
            }
            
            .package {
                break-inside: avoid;
            }
        }
    </style>
</head>
<body>
    <div class="page">
        <!-- Cover Page -->
        <div class="cover">
            <div class="logo">R</div>
            <h1>EVENT PROPOSAL</h1>
            <div class="subtitle">For {{ client_company }}</div>
            <div class="details">
                {{ event_type }} | {{ event_date }}<br>
                {{ guest_count }} Guests | Prepared {{ generated_date }}
            </div>
        </div>
        
        <!-- Executive Summary -->
        <div class="section">
            <h2>Executive Summary</h2>
            <h3>Event Vision</h3>
            <p>{{ event_vision }}</p>
            
            <h3>Event Details</h3>
            <ul>
                <li><strong>Event Type:</strong> {{ event_type }}</li>
                <li><strong>Date:</strong> {{ event_date }}</li>
                <li><strong>Expected Guests:</strong> {{ guest_count }}</li>
                <li><strong>Location:</strong> {{ location | default("To be determined") }}</li>
                <li><strong>Investment Range:</strong> ${{ "{:,}".format(packages[0].price) }} - ${{ "{:,}".format(packages[2].price) }}</li>
            </ul>
        </div>
        
        <!-- Event Packages -->
        <div class="section">
            <h2>Service Packages</h2>
            <p>Choose the package that best fits your vision and budget. Each package includes our signature attention to detail and commitment to excellence.</p>
            
            <div class="packages">
                {% for package in packages %}
                <div class="package {% if package.recommended %}recommended{% endif %}">
                    <div class="package-name">{{ package.name }}</div>
                    <div class="package-price">${{ "{:,}".format(package.price) }}</div>
                    <div class="package-per-person">${{ package.per_person }} per person</div>
                    <div class="package-description">{{ package.description }}</div>
                    <ul class="package-features">
                        {% for feature in package.features %}
                        <li>{{ feature }}</li>
                        {% endfor %}
                    </ul>
                </div>
                {% endfor %}
            </div>
        </div>
        
        <!-- Investment Breakdown -->
        <div class="section">
            <h2>Investment Breakdown</h2>
            <p>Based on our recommended <strong>{{ packages[1].name }}</strong> package:</p>
            
            <table class="investment-table">
                <thead>
                    <tr>
                        <th>Service Category</th>
                        <th>Details</th>
                        <th>Investment</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>Event Coordination</td>
                        <td>Full-service planning and day-of management</td>
                        <td>${{ "{:,}".format((packages[1].price * 0.2) | int) }}</td>
                    </tr>
                    <tr>
                        <td>Venue & Logistics</td>
                        <td>Space rental, setup, and breakdown</td>
                        <td>${{ "{:,}".format((packages[1].price * 0.25) | int) }}</td>
                    </tr>
                    <tr>
                        <td>Catering & Beverages</td>
                        <td>Premium menu with dietary accommodations</td>
                        <td>${{ "{:,}".format((packages[1].price * 0.35) | int) }}</td>
                    </tr>
                    <tr>
                        <td>Audio/Visual & Entertainment</td>
                        <td>Professional AV setup and background music</td>
                        <td>${{ "{:,}".format((packages[1].price * 0.15) | int) }}</td>
                    </tr>
                    <tr>
                        <td>Photography & Documentation</td>
                        <td>Professional event photography (4 hours)</td>
                        <td>${{ "{:,}".format((packages[1].price * 0.05) | int) }}</td>
                    </tr>
                    <tr class="total-row">
                        <td colspan="2"><strong>Total Investment</strong></td>
                        <td><strong>${{ "{:,}".format(packages[1].price) }}</strong></td>
                    </tr>
                </tbody>
            </table>
        </div>
        
        <!-- Timeline -->
        <div class="section">
            <h2>Project Timeline</h2>
            <p>Our proven planning process ensures every detail is perfected before your event day.</p>
            
            <div class="timeline">
                {% for phase in timeline %}
                <div class="timeline-item">
                    <div class="timeline-phase">{{ phase.phase }}</div>
                    <div class="timeline-timeframe">{{ phase.timeframe }}</div>
                    <div class="timeline-description">{{ phase.description }}</div>
                </div>
                {% endfor %}
            </div>
        </div>
        
        <!-- Why Rainmaker -->
        <div class="section">
            <h2>Why Choose Rainmaker</h2>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px;">
                <div>
                    <h3>Experience</h3>
                    <p>500+ successful events delivered across diverse industries and event types.</p>
                </div>
                <div>
                    <h3>Excellence</h3>
                    <p>98% client satisfaction rate with a commitment to exceeding expectations.</p>
                </div>
                <div>
                    <h3>Efficiency</h3>
                    <p>Streamlined processes and vendor relationships ensure seamless execution.</p>
                </div>
            </div>
        </div>
        
        <!-- Next Steps -->
        <div class="section">
            <h2>Next Steps</h2>
            <ol style="padding-left: 20px;">
                <li><strong>Review Proposal:</strong> Take time to review all details and packages</li>
                <li><strong>Schedule Consultation:</strong> Book a call to discuss any questions or customizations</li>
                <li><strong>Contract & Deposit:</strong> Sign agreement and submit 50% deposit to secure your date</li>
                <li><strong>Planning Kickoff:</strong> Begin detailed planning process with your dedicated coordinator</li>
            </ol>
            
            <p style="margin-top: 20px;"><strong>This proposal is valid until {{ valid_until_date }}.</strong></p>
        </div>
        
        <!-- Contact -->
        <div class="contact-info">
            <h3>Ready to Get Started?</h3>
            <div class="contact-details">
                <div class="contact-item">
                    <strong>{{ rainmaker_contact.name }}</strong>
                    {{ rainmaker_contact.title }}
                </div>
                <div class="contact-item">
                    <strong>Email</strong>
                    {{ rainmaker_contact.email }}
                </div>
                <div class="contact-item">
                    <strong>Phone</strong>
                    {{ rainmaker_contact.phone }}
                </div>
                <div class="contact-item">
                    <strong>Proposal ID</strong>
                    {{ proposal_id }}
                </div>
            </div>
        </div>
    </div>
</body>
</html>
"""
        
        template = Template(template_content)
        html_content = template.render(**data)
        
        return html_content
    
    async def _save_proposal_as_pdf(self, html_content: str, data: Dict[str, Any]) -> Dict[str, Path]:
        """Save proposal as both HTML and PDF using Playwright"""
        base_filename = data['proposal_id']
        html_path = self.output_dir / f"{base_filename}.html"
        pdf_path = self.output_dir / f"{base_filename}.pdf"
        
        # Save HTML file
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.info("HTML proposal saved", file_path=str(html_path))
        
        # Convert to PDF using Playwright
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            
            # Set content and wait for any potential loading
            await page.set_content(html_content, wait_until='networkidle')
            
            # Generate PDF with professional settings
            await page.pdf(
                path=str(pdf_path),
                format='A4',
                print_background=True,
                margin={
                    'top': '0.5in',
                    'bottom': '0.5in', 
                    'left': '0.5in',
                    'right': '0.5in'
                }
            )
            
            await browser.close()
        
        logger.info("PDF proposal generated", file_path=str(pdf_path))
        
        return {
            "html_path": html_path,
            "pdf_path": pdf_path
        }


# Test function for independent testing
async def test_proposal_agent():
    """Test the proposal agent with mock data"""
    
    mock_data = {
        "client_company": "TechFlow Solutions",
        "event_type": "Holiday Party", 
        "event_date": "December 15, 2024",
        "guest_count": 150,
        "budget_estimate": 35000,
        "industry": "Technology",
        "location": "San Francisco, CA",
        "special_requirements": [
            "Dietary restrictions accommodations",
            "Professional photography",
            "Live entertainment"
        ]
    }
    
    agent = ProposalAgent()
    result = await agent.generate_proposal(mock_data)
    
    print("\n" + "="*60)
    print("PROPOSAL AGENT TEST RESULTS")
    print("="*60)
    print(f"Status: {result['status']}")
    
    if result['status'] == 'success':
        print(f"Proposal ID: {result['proposal_id']}")
        print(f"Client: {result['client_company']}")
        print(f"Event Type: {result['event_type']}")
        print(f"Total Investment: ${result['total_investment']:,}")
        print(f"PDF File: {result['pdf_file_path']}")
        print(f"HTML File: {result['html_file_path']}")
        print(f"Generated At: {result['generated_at']}")
        print(f"Valid Until: {result['valid_until']}")
        
        # Check if files exist
        pdf_exists = os.path.exists(result['pdf_file_path'])
        html_exists = os.path.exists(result['html_file_path'])
        
        if pdf_exists and html_exists:
            print("✅ Proposal files created successfully!")
            print(f"📄 PDF: {result['pdf_file_path']}")
            print(f"🌐 HTML: {result['html_file_path']}")
        else:
            if not pdf_exists:
                print("❌ PDF file not found")
            if not html_exists:
                print("❌ HTML file not found")
    else:
        print(f"❌ Error: {result['message']}")
    
    print("="*60)
    return result


if __name__ == "__main__":
    # Run test when script is executed directly
    asyncio.run(test_proposal_agent())
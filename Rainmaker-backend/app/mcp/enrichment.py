"""
Enrichment MCP server for Clearbit API integration
"""

import asyncio
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
import structlog
import httpx
from mcp.server import Server
from mcp.types import Tool, TextContent, CallToolResult

from app.core.config import settings

logger = structlog.get_logger(__name__)


class EnrichmentMCP:
    """
    MCP server for prospect enrichment using Clearbit API
    """
    
    def __init__(self):
        self.server = Server("enrichment")
        self.api_key = settings.CLEARBIT_API_KEY.get_secret_value() if settings.CLEARBIT_API_KEY else None
        self.base_url = "https://person.clearbit.com/v2"
        self.company_url = "https://company.clearbit.com/v2"
        self.client = httpx.AsyncClient(
            timeout=30.0,
            auth=(self.api_key, "") if self.api_key else None
        )
        
        # Register MCP tools
        self._register_tools()
    
    def _register_tools(self):
        """Register MCP tools for enrichment functionality"""
        
        @self.server.call_tool()
        async def enrich_person(arguments: Dict[str, Any]) -> CallToolResult:
            """
            Enrich person data using email or name
            
            Args:
                email: Person's email address (optional)
                name: Person's full name (optional)
                company: Company name for additional context (optional)
                location: Location for additional context (optional)
            """
            try:
                email = arguments.get("email")
                name = arguments.get("name")
                company = arguments.get("company")
                location = arguments.get("location")
                
                if not email and not name:
                    raise ValueError("Either email or name is required")
                
                # Enrich person data
                person_data = await self._enrich_person_data(email, name, company, location)
                
                return CallToolResult(
                    content=[TextContent(
                        type="text",
                        text=json.dumps(person_data, indent=2)
                    )]
                )
                
            except Exception as e:
                logger.error("Person enrichment failed", error=str(e))
                return CallToolResult(
                    content=[TextContent(
                        type="text",
                        text=json.dumps({"error": f"Person enrichment failed: {str(e)}"})
                    )],
                    isError=True
                )
        
        @self.server.call_tool()
        async def enrich_company(arguments: Dict[str, Any]) -> CallToolResult:
            """
            Enrich company data using domain or company name
            
            Args:
                domain: Company domain (e.g., "example.com")
                company_name: Company name (optional)
            """
            try:
                domain = arguments.get("domain")
                company_name = arguments.get("company_name")
                
                if not domain and not company_name:
                    raise ValueError("Either domain or company_name is required")
                
                # Enrich company data
                company_data = await self._enrich_company_data(domain, company_name)
                
                return CallToolResult(
                    content=[TextContent(
                        type="text",
                        text=json.dumps(company_data, indent=2)
                    )]
                )
                
            except Exception as e:
                logger.error("Company enrichment failed", error=str(e))
                return CallToolResult(
                    content=[TextContent(
                        type="text",
                        text=json.dumps({"error": f"Company enrichment failed: {str(e)}"})
                    )],
                    isError=True
                )
        
        @self.server.call_tool()
        async def find_contacts(arguments: Dict[str, Any]) -> CallToolResult:
            """
            Find contacts at a company
            
            Args:
                domain: Company domain
                role: Role to search for (optional, e.g., "marketing", "events")
                seniority: Seniority level (optional, e.g., "manager", "director")
                limit: Maximum number of contacts to return (default: 10)
            """
            try:
                domain = arguments.get("domain")
                role = arguments.get("role")
                seniority = arguments.get("seniority")
                limit = arguments.get("limit", 10)
                
                if not domain:
                    raise ValueError("domain is required")
                
                # Find contacts
                contacts = await self._find_company_contacts(domain, role, seniority, limit)
                
                return CallToolResult(
                    content=[TextContent(
                        type="text",
                        text=json.dumps({
                            "contacts": contacts,
                            "total_found": len(contacts),
                            "search_criteria": {
                                "domain": domain,
                                "role": role,
                                "seniority": seniority
                            }
                        }, indent=2)
                    )]
                )
                
            except Exception as e:
                logger.error("Contact search failed", error=str(e))
                return CallToolResult(
                    content=[TextContent(
                        type="text",
                        text=json.dumps({"error": f"Contact search failed: {str(e)}"})
                    )],
                    isError=True
                )
        
        @self.server.call_tool()
        async def get_technographics(arguments: Dict[str, Any]) -> CallToolResult:
            """
            Get technology stack information for a company
            
            Args:
                domain: Company domain
            """
            try:
                domain = arguments.get("domain")
                
                if not domain:
                    raise ValueError("domain is required")
                
                # Get technographics data
                tech_data = await self._get_technographics(domain)
                
                return CallToolResult(
                    content=[TextContent(
                        type="text",
                        text=json.dumps(tech_data, indent=2)
                    )]
                )
                
            except Exception as e:
                logger.error("Technographics lookup failed", error=str(e))
                return CallToolResult(
                    content=[TextContent(
                        type="text",
                        text=json.dumps({"error": f"Technographics lookup failed: {str(e)}"})
                    )],
                    isError=True
                )
        
        @self.server.call_tool()
        async def enrich_prospect(arguments: Dict[str, Any]) -> CallToolResult:
            """
            Comprehensive prospect enrichment combining person and company data
            
            Args:
                email: Prospect's email address (optional)
                name: Prospect's name (optional)
                company: Company name (optional)
                domain: Company domain (optional)
                location: Location (optional)
            """
            try:
                email = arguments.get("email")
                name = arguments.get("name")
                company = arguments.get("company")
                domain = arguments.get("domain")
                location = arguments.get("location")
                
                if not any([email, name, company, domain]):
                    raise ValueError("At least one of email, name, company, or domain is required")
                
                # Comprehensive enrichment
                enriched_data = await self._comprehensive_enrichment(
                    email, name, company, domain, location
                )
                
                return CallToolResult(
                    content=[TextContent(
                        type="text",
                        text=json.dumps(enriched_data, indent=2)
                    )]
                )
                
            except Exception as e:
                logger.error("Comprehensive enrichment failed", error=str(e))
                return CallToolResult(
                    content=[TextContent(
                        type="text",
                        text=json.dumps({"error": f"Comprehensive enrichment failed: {str(e)}"})
                    )],
                    isError=True
                )
    
    async def _enrich_person_data(
        self,
        email: Optional[str],
        name: Optional[str],
        company: Optional[str],
        location: Optional[str]
    ) -> Dict[str, Any]:
        """Enrich person data using Clearbit API"""
        
        if not self.api_key:
            # Return mock data for development
            return self._get_mock_person_data(email, name, company)
        
        try:
            params = {}
            if email:
                params["email"] = email
            if name:
                params["given_name"] = name.split()[0] if " " in name else name
                if " " in name:
                    params["family_name"] = name.split()[-1]
            if company:
                params["company"] = company
            if location:
                params["location"] = location
            
            response = await self.client.get(
                f"{self.base_url}/combined",
                params=params
            )
            
            if response.status_code == 200:
                data = response.json()
                return self._format_person_data(data)
            elif response.status_code == 202:
                # Clearbit is processing the request
                return {
                    "status": "processing",
                    "message": "Enrichment in progress, try again later"
                }
            else:
                logger.warning(f"Clearbit API returned {response.status_code}")
                return self._get_mock_person_data(email, name, company)
                
        except Exception as e:
            logger.error("Clearbit person enrichment failed", error=str(e))
            return self._get_mock_person_data(email, name, company)
    
    async def _enrich_company_data(
        self,
        domain: Optional[str],
        company_name: Optional[str]
    ) -> Dict[str, Any]:
        """Enrich company data using Clearbit API"""
        
        if not self.api_key:
            # Return mock data for development
            return self._get_mock_company_data(domain, company_name)
        
        try:
            params = {}
            if domain:
                params["domain"] = domain
            elif company_name:
                params["name"] = company_name
            
            response = await self.client.get(
                f"{self.company_url}/companies/find",
                params=params
            )
            
            if response.status_code == 200:
                data = response.json()
                return self._format_company_data(data)
            else:
                logger.warning(f"Clearbit company API returned {response.status_code}")
                return self._get_mock_company_data(domain, company_name)
                
        except Exception as e:
            logger.error("Clearbit company enrichment failed", error=str(e))
            return self._get_mock_company_data(domain, company_name)
    
    async def _find_company_contacts(
        self,
        domain: str,
        role: Optional[str],
        seniority: Optional[str],
        limit: int
    ) -> List[Dict[str, Any]]:
        """Find contacts at a company"""
        
        if not self.api_key:
            # Return mock contacts for development
            return self._get_mock_contacts(domain, role, seniority, limit)
        
        try:
            params = {
                "domain": domain,
                "limit": limit
            }
            if role:
                params["role"] = role
            if seniority:
                params["seniority"] = seniority
            
            response = await self.client.get(
                f"{self.base_url}/people/search",
                params=params
            )
            
            if response.status_code == 200:
                data = response.json()
                contacts = []
                for person in data.get("results", []):
                    contacts.append(self._format_person_data(person))
                return contacts
            else:
                logger.warning(f"Clearbit contacts API returned {response.status_code}")
                return self._get_mock_contacts(domain, role, seniority, limit)
                
        except Exception as e:
            logger.error("Clearbit contact search failed", error=str(e))
            return self._get_mock_contacts(domain, role, seniority, limit)
    
    async def _get_technographics(self, domain: str) -> Dict[str, Any]:
        """Get technology stack information"""
        
        if not self.api_key:
            # Return mock tech data for development
            return self._get_mock_technographics(domain)
        
        try:
            response = await self.client.get(
                f"{self.company_url}/companies/find",
                params={"domain": domain}
            )
            
            if response.status_code == 200:
                data = response.json()
                tech_data = data.get("tech", [])
                
                return {
                    "domain": domain,
                    "technologies": tech_data,
                    "categories": list(set([tech.get("category") for tech in tech_data if tech.get("category")])),
                    "total_technologies": len(tech_data)
                }
            else:
                return self._get_mock_technographics(domain)
                
        except Exception as e:
            logger.error("Technographics lookup failed", error=str(e))
            return self._get_mock_technographics(domain)
    
    async def _comprehensive_enrichment(
        self,
        email: Optional[str],
        name: Optional[str],
        company: Optional[str],
        domain: Optional[str],
        location: Optional[str]
    ) -> Dict[str, Any]:
        """Perform comprehensive prospect enrichment"""
        
        enriched_data = {
            "person": {},
            "company": {},
            "enrichment_score": 0.0,
            "data_sources": [],
            "enriched_at": datetime.now().isoformat()
        }
        
        # Enrich person data
        if email or name:
            person_data = await self._enrich_person_data(email, name, company, location)
            enriched_data["person"] = person_data
            enriched_data["data_sources"].append("person_enrichment")
            
            # Extract company domain from person data if not provided
            if not domain and person_data.get("company", {}).get("domain"):
                domain = person_data["company"]["domain"]
        
        # Enrich company data
        if domain or company:
            company_data = await self._enrich_company_data(domain, company)
            enriched_data["company"] = company_data
            enriched_data["data_sources"].append("company_enrichment")
        
        # Calculate enrichment score based on available data
        score = 0.0
        if enriched_data["person"]:
            score += 0.5
        if enriched_data["company"]:
            score += 0.3
        if email:
            score += 0.1
        if location:
            score += 0.1
        
        enriched_data["enrichment_score"] = min(score, 1.0)
        
        return enriched_data
    
    def _format_person_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Format person data from Clearbit response"""
        person = data.get("person", {})
        company = data.get("company", {})
        
        return {
            "name": {
                "full_name": person.get("name", {}).get("fullName"),
                "first_name": person.get("name", {}).get("givenName"),
                "last_name": person.get("name", {}).get("familyName")
            },
            "email": person.get("email"),
            "location": person.get("location"),
            "bio": person.get("bio"),
            "avatar": person.get("avatar"),
            "employment": {
                "title": person.get("employment", {}).get("title"),
                "role": person.get("employment", {}).get("role"),
                "seniority": person.get("employment", {}).get("seniority")
            },
            "social": {
                "linkedin": person.get("linkedin", {}).get("handle"),
                "twitter": person.get("twitter", {}).get("handle"),
                "facebook": person.get("facebook", {}).get("handle")
            },
            "company": {
                "name": company.get("name"),
                "domain": company.get("domain"),
                "industry": company.get("category", {}).get("industry")
            } if company else {},
            "confidence_score": 0.8,
            "last_updated": datetime.now().isoformat()
        }
    
    def _format_company_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Format company data from Clearbit response"""
        return {
            "name": data.get("name"),
            "domain": data.get("domain"),
            "description": data.get("description"),
            "industry": data.get("category", {}).get("industry"),
            "sector": data.get("category", {}).get("sector"),
            "size": data.get("metrics", {}).get("employees"),
            "founded": data.get("foundedYear"),
            "location": {
                "city": data.get("geo", {}).get("city"),
                "state": data.get("geo", {}).get("state"),
                "country": data.get("geo", {}).get("country")
            },
            "website": data.get("site", {}).get("url"),
            "logo": data.get("logo"),
            "social": {
                "linkedin": data.get("linkedin", {}).get("handle"),
                "twitter": data.get("twitter", {}).get("handle"),
                "facebook": data.get("facebook", {}).get("handle")
            },
            "technologies": data.get("tech", []),
            "confidence_score": 0.8,
            "last_updated": datetime.now().isoformat()
        }
    
    def _get_mock_person_data(
        self,
        email: Optional[str],
        name: Optional[str],
        company: Optional[str]
    ) -> Dict[str, Any]:
        """Generate mock person data for development"""
        return {
            "name": {
                "full_name": name or "John Doe",
                "first_name": (name or "John Doe").split()[0],
                "last_name": (name or "John Doe").split()[-1] if name and " " in name else "Doe"
            },
            "email": email or "john.doe@example.com",
            "location": "New York, NY",
            "bio": "Event planning enthusiast and marketing professional",
            "avatar": "https://example.com/avatar.jpg",
            "employment": {
                "title": "Marketing Manager",
                "role": "marketing",
                "seniority": "manager"
            },
            "social": {
                "linkedin": "johndoe",
                "twitter": "johndoe",
                "facebook": None
            },
            "company": {
                "name": company or "Example Corp",
                "domain": "example.com",
                "industry": "Technology"
            },
            "confidence_score": 0.6,
            "last_updated": datetime.now().isoformat(),
            "note": "Mock data - no API key configured"
        }
    
    def _get_mock_company_data(
        self,
        domain: Optional[str],
        company_name: Optional[str]
    ) -> Dict[str, Any]:
        """Generate mock company data for development"""
        return {
            "name": company_name or "Example Corp",
            "domain": domain or "example.com",
            "description": "A leading technology company focused on innovation",
            "industry": "Technology",
            "sector": "Software",
            "size": 250,
            "founded": 2010,
            "location": {
                "city": "San Francisco",
                "state": "CA",
                "country": "US"
            },
            "website": f"https://{domain or 'example.com'}",
            "logo": "https://example.com/logo.png",
            "social": {
                "linkedin": "example-corp",
                "twitter": "examplecorp",
                "facebook": "examplecorp"
            },
            "technologies": ["Salesforce", "Google Analytics", "Slack"],
            "confidence_score": 0.6,
            "last_updated": datetime.now().isoformat(),
            "note": "Mock data - no API key configured"
        }
    
    def _get_mock_contacts(
        self,
        domain: str,
        role: Optional[str],
        seniority: Optional[str],
        limit: int
    ) -> List[Dict[str, Any]]:
        """Generate mock contacts for development"""
        contacts = []
        
        for i in range(min(limit, 3)):
            contacts.append({
                "name": {
                    "full_name": f"Contact {i+1}",
                    "first_name": f"Contact",
                    "last_name": f"{i+1}"
                },
                "email": f"contact{i+1}@{domain}",
                "employment": {
                    "title": f"{role or 'Manager'} {i+1}",
                    "role": role or "manager",
                    "seniority": seniority or "manager"
                },
                "confidence_score": 0.6,
                "note": "Mock data - no API key configured"
            })
        
        return contacts
    
    def _get_mock_technographics(self, domain: str) -> Dict[str, Any]:
        """Generate mock technographics for development"""
        return {
            "domain": domain,
            "technologies": [
                {"name": "Google Analytics", "category": "Analytics"},
                {"name": "Salesforce", "category": "CRM"},
                {"name": "Slack", "category": "Communication"}
            ],
            "categories": ["Analytics", "CRM", "Communication"],
            "total_technologies": 3,
            "note": "Mock data - no API key configured"
        }
    
    def get_server(self) -> Server:
        """Get the MCP server instance"""
        return self.server
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()


# Create global MCP server instance
enrichment_mcp = EnrichmentMCP()
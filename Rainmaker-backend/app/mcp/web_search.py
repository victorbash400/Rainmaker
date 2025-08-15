"""
Web Search MCP server for Sonar/Perplexity API integration
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


class WebSearchMCP:
    """
    MCP server for web search functionality using Sonar/Perplexity API
    """
    
    def __init__(self):
        self.server = Server("web-search")
        self.api_key = settings.SONAR_API_KEY.get_secret_value() if settings.SONAR_API_KEY else None
        self.base_url = "https://api.perplexity.ai"
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers={
                "Authorization": f"Bearer {self.api_key}" if self.api_key else "",
                "Content-Type": "application/json"
            }
        )
        
        # Register MCP tools
        self._register_tools()
    
    def _register_tools(self):
        """Register MCP tools for web search functionality"""
        
        @self.server.call_tool()
        async def search_prospects(arguments: Dict[str, Any]) -> CallToolResult:
            """
            Search for prospect signals based on event type and location
            
            Args:
                event_type: Type of event (wedding, corporate, birthday, etc.)
                location: Geographic location filter (optional)
                date_range: Date range for events (optional)
                max_results: Maximum number of results (default: 20)
            """
            try:
                event_type = arguments.get("event_type", "all")
                location = arguments.get("location")
                date_range = arguments.get("date_range")
                max_results = arguments.get("max_results", 20)
                
                # Build search query
                query = self._build_prospect_search_query(event_type, location, date_range)
                
                # Perform search
                results = await self._perform_search(query, max_results)
                
                # Extract prospect signals
                prospects = []
                for result in results:
                    prospect_signals = self._extract_prospect_signals(result, event_type)
                    prospects.extend(prospect_signals)
                
                # Sort by confidence score
                prospects.sort(key=lambda x: x.get("confidence_score", 0), reverse=True)
                
                return CallToolResult(
                    content=[TextContent(
                        type="text",
                        text=json.dumps({
                            "prospects": prospects[:max_results],
                            "total_found": len(prospects),
                            "search_query": query
                        }, indent=2)
                    )]
                )
                
            except Exception as e:
                logger.error("Prospect search failed", error=str(e))
                return CallToolResult(
                    content=[TextContent(
                        type="text",
                        text=json.dumps({"error": f"Search failed: {str(e)}"})
                    )],
                    isError=True
                )
        
        @self.server.call_tool()
        async def search_company_info(arguments: Dict[str, Any]) -> CallToolResult:
            """
            Search for detailed company information
            
            Args:
                company_name: Name of the company to research
                additional_context: Additional search context (optional)
            """
            try:
                company_name = arguments.get("company_name")
                additional_context = arguments.get("additional_context", "")
                
                if not company_name:
                    raise ValueError("company_name is required")
                
                # Build search query
                query = f"company information {company_name} {additional_context}".strip()
                
                # Perform search
                results = await self._perform_search(query, max_results=10)
                
                # Extract company information
                company_info = {
                    "name": company_name,
                    "description": "",
                    "industry": "",
                    "size": "",
                    "location": "",
                    "website": "",
                    "recent_events": [],
                    "event_history": [],
                    "confidence_score": 0.0,
                    "sources": []
                }
                
                for result in results:
                    info = self._extract_company_info(result, company_name)
                    company_info = self._merge_company_info(company_info, info)
                
                return CallToolResult(
                    content=[TextContent(
                        type="text",
                        text=json.dumps(company_info, indent=2)
                    )]
                )
                
            except Exception as e:
                logger.error("Company search failed", error=str(e))
                return CallToolResult(
                    content=[TextContent(
                        type="text",
                        text=json.dumps({"error": f"Company search failed: {str(e)}"})
                    )],
                    isError=True
                )
        
        @self.server.call_tool()
        async def search_event_signals(arguments: Dict[str, Any]) -> CallToolResult:
            """
            Search for general event planning signals using custom keywords
            
            Args:
                keywords: List of keywords to search for
                location: Geographic location filter (optional)
                max_results: Maximum number of results (default: 50)
            """
            try:
                keywords = arguments.get("keywords", [])
                location = arguments.get("location")
                max_results = arguments.get("max_results", 50)
                
                if not keywords:
                    raise ValueError("keywords list is required")
                
                # Build query from keywords
                query = " OR ".join(f'"{keyword}"' for keyword in keywords)
                if location:
                    query += f" location:{location}"
                
                # Perform search
                results = await self._perform_search(query, max_results)
                
                # Format results
                formatted_results = []
                for result in results:
                    formatted_results.append({
                        "title": result.get("title", ""),
                        "url": result.get("url", ""),
                        "snippet": result.get("snippet", ""),
                        "source": result.get("source", ""),
                        "relevance_score": result.get("relevance_score", 0.0),
                        "timestamp": result.get("timestamp", datetime.now().isoformat())
                    })
                
                return CallToolResult(
                    content=[TextContent(
                        type="text",
                        text=json.dumps({
                            "results": formatted_results,
                            "total_found": len(formatted_results),
                            "keywords": keywords,
                            "location": location
                        }, indent=2)
                    )]
                )
                
            except Exception as e:
                logger.error("Event signals search failed", error=str(e))
                return CallToolResult(
                    content=[TextContent(
                        type="text",
                        text=json.dumps({"error": f"Event signals search failed: {str(e)}"})
                    )],
                    isError=True
                )
    
    async def _perform_search(self, query: str, max_results: int = 20) -> List[Dict[str, Any]]:
        """Perform search using Perplexity Sonar API"""
        
        if not self.api_key:
            logger.warning("No Sonar API key configured, returning mock results")
            return self._get_mock_results(query, max_results)
        
        try:
            # Use Sonar model as shown in the example
            payload = {
                "model": "sonar",
                "messages": [
                    {
                        "role": "user",
                        "content": f"Find people planning events: {query}. Look for social media posts, forum discussions, and announcements where people are actively seeking event planning help or services."
                    }
                ]
            }
            
            response = await self.client.post(
                f"{self.base_url}/chat/completions",
                json=payload
            )
            
            if response.status_code != 200:
                logger.warning(f"Sonar API request failed: {response.status_code}")
                return self._get_mock_results(query, max_results)
            
            data = response.json()
            return self._parse_sonar_response(data, query)[:max_results]
            
        except Exception as e:
            logger.error("Sonar API request failed", error=str(e))
            return self._get_mock_results(query, max_results)
    
    def _build_prospect_search_query(
        self,
        event_type: str,
        location: Optional[str] = None,
        date_range: Optional[str] = None
    ) -> str:
        """Build search query for prospect discovery"""
        
        event_keywords = {
            "wedding": ["getting married", "wedding planning", "bride to be", "engagement announcement"],
            "corporate": ["company event", "corporate retreat", "team building", "conference"],
            "birthday": ["birthday party", "birthday celebration", "milestone birthday"],
            "anniversary": ["anniversary celebration", "wedding anniversary", "milestone anniversary"]
        }
        
        if event_type == "all":
            keywords = []
            for event_keywords_list in event_keywords.values():
                keywords.extend(event_keywords_list[:2])  # Top 2 from each type
        elif event_type in event_keywords:
            keywords = event_keywords[event_type]
        else:
            keywords = [f"{event_type} event", f"{event_type} planning"]
        
        query_parts = []
        query_parts.append("(" + " OR ".join(f'"{kw}"' for kw in keywords[:5]) + ")")
        
        if location:
            query_parts.append(f"location:{location}")
        
        if date_range:
            query_parts.append(f"date:{date_range}")
        
        query_parts.append("recent")
        
        return " ".join(query_parts)
    
    def _extract_prospect_signals(self, result: Dict[str, Any], event_type: str) -> List[Dict[str, Any]]:
        """Extract prospect signals from Sonar search result"""
        signals = []
        
        text = f"{result.get('title', '')} {result.get('snippet', '')}".lower()
        
        # Expanded prospect indicators for better signal detection
        prospect_indicators = {
            "wedding": [
                "getting married", "wedding planning", "bride to be", "groom to be",
                "engagement", "planning our wedding", "wedding venue", "wedding planner",
                "need help with wedding", "looking for wedding services"
            ],
            "corporate": [
                "company event", "corporate retreat", "team building", "office party",
                "conference planning", "business meeting", "corporate celebration",
                "need event coordinator", "planning company"
            ],
            "birthday": [
                "birthday party", "birthday celebration", "planning birthday",
                "milestone birthday", "sweet sixteen", "surprise party",
                "birthday venue", "party planning"
            ]
        }
        
        # Get indicators for this event type
        indicators = prospect_indicators.get(event_type, ["planning", "event", "celebration"])
        
        # Check if any indicators match
        for indicator in indicators:
            if indicator in text:
                # Extract more sophisticated prospect data
                signal = {
                    "prospect_name": self._extract_name_from_text(text),
                    "event_type": event_type,
                    "event_date": self._extract_date_from_text(text),
                    "location": self._extract_location_from_text(text),
                    "contact_info": self._extract_contact_from_text(text),
                    "confidence_score": min(result.get("relevance_score", 0.5) * 0.9, 1.0),
                    "source_url": result.get("url", ""),
                    "raw_text": result.get("snippet", ""),
                    "evidence": f"Found '{indicator}' in content",
                    "search_context": result.get("title", "")
                }
                signals.append(signal)
                break  # Only one signal per result to avoid duplicates
        
        return signals
    
    def _extract_company_info(self, result: Dict[str, Any], company_name: str) -> Dict[str, Any]:
        """Extract company information from search result"""
        return {
            "description": result.get("snippet", ""),
            "website": result.get("url", "") if company_name.lower() in result.get("url", "").lower() else "",
            "confidence_score": result.get("relevance_score", 0.5),
            "sources": [result.get("url", "")]
        }
    
    def _merge_company_info(self, existing: Dict[str, Any], new_info: Dict[str, Any]) -> Dict[str, Any]:
        """Merge company information from multiple sources"""
        for key, value in new_info.items():
            if key == "sources":
                existing.setdefault("sources", []).extend(value)
            elif value and not existing.get(key):
                existing[key] = value
        
        existing["confidence_score"] = max(
            existing.get("confidence_score", 0),
            new_info.get("confidence_score", 0)
        )
        
        return existing
    
    def _parse_sonar_response(self, response_data: Dict[str, Any], query: str) -> List[Dict[str, Any]]:
        """Parse Sonar API response into search results"""
        results = []
        
        if "choices" in response_data and response_data["choices"]:
            content = response_data["choices"][0].get("message", {}).get("content", "")
            search_results = response_data.get("search_results", [])
            
            # Use search_results from Sonar API
            for i, search_result in enumerate(search_results[:10]):
                result = {
                    "title": search_result.get("title", f"Result {i+1}"),
                    "url": search_result.get("url", ""),
                    "snippet": content[i*50:(i+1)*100] if content else f"Found via Sonar search for: {query}",
                    "source": "sonar",
                    "relevance_score": 1.0 - (i * 0.1),
                    "timestamp": search_result.get("date", datetime.now().isoformat()),
                    "last_updated": search_result.get("last_updated", datetime.now().isoformat())
                }
                results.append(result)
            
            # If no search_results but we have content, create a result from the content
            if not search_results and content:
                result = {
                    "title": f"Sonar Search: {query[:50]}...",
                    "url": "",
                    "snippet": content[:300],
                    "source": "sonar", 
                    "relevance_score": 0.8,
                    "timestamp": datetime.now().isoformat()
                }
                results.append(result)
        
        return results
    
    def _get_mock_results(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        """Generate mock search results for development"""
        mock_results = [
            {
                "title": "Wedding Planning in New York - Sarah & John",
                "url": "https://example.com/wedding1",
                "snippet": "Sarah and John are planning their dream wedding in New York for next summer. Looking for the perfect venue and catering services.",
                "source": "mock",
                "relevance_score": 0.9,
                "timestamp": datetime.now().isoformat()
            },
            {
                "title": "Corporate Event Planning - Tech Company Retreat",
                "url": "https://example.com/corporate1",
                "snippet": "TechCorp is organizing their annual company retreat for 200 employees. Seeking event planning services for team building activities.",
                "source": "mock",
                "relevance_score": 0.8,
                "timestamp": datetime.now().isoformat()
            },
            {
                "title": "Birthday Party Planning - 30th Birthday Celebration",
                "url": "https://example.com/birthday1",
                "snippet": "Planning an amazing 30th birthday party for my best friend. Need help with venue, catering, and entertainment.",
                "source": "mock",
                "relevance_score": 0.7,
                "timestamp": datetime.now().isoformat()
            }
        ]
        
        return mock_results[:max_results]
    
    def _extract_name_from_text(self, text: str) -> str:
        """Extract potential names from text"""
        import re
        
        name_patterns = [
            r"i'm ([A-Z][a-z]+)",
            r"my name is ([A-Z][a-z]+)",
            r"([A-Z][a-z]+) and ([A-Z][a-z]+) are",
        ]
        
        for pattern in name_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        
        return "Unknown"
    
    def _extract_date_from_text(self, text: str) -> Optional[str]:
        """Extract potential dates from text"""
        import re
        
        date_patterns = [
            r"(next \w+)",
            r"(in \w+ \d{4})",
            r"(\w+ \d{1,2}, \d{4})",
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        
        return None
    
    def _extract_location_from_text(self, text: str) -> Optional[str]:
        """Extract potential locations from text"""
        import re
        
        location_patterns = [
            r"in ([A-Z][a-z]+ [A-Z][a-z]+)",
            r"in ([A-Z][a-z]+)",
            r"at ([A-Z][a-z]+ [A-Z][a-z]+)",
        ]
        
        for pattern in location_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        
        return None
    
    def _extract_contact_from_text(self, text: str) -> Optional[str]:
        """Extract potential contact information from text"""
        import re
        
        # Look for email patterns
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        email_match = re.search(email_pattern, text)
        if email_match:
            return email_match.group(0)
        
        # Look for phone patterns
        phone_patterns = [
            r'\b(\d{3}[-.\s]?\d{3}[-.\s]?\d{4})\b',
            r'\b(\(\d{3}\)\s*\d{3}[-.\s]?\d{4})\b'
        ]
        
        for pattern in phone_patterns:
            phone_match = re.search(pattern, text)
            if phone_match:
                return phone_match.group(1)
        
        return None
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> CallToolResult:
        """Call a specific MCP tool by name"""
        if tool_name == "search_prospects":
            return await self._search_prospects_tool(arguments)
        elif tool_name == "search_company_info":
            return await self._search_company_info_tool(arguments)
        elif tool_name == "search_event_signals":
            return await self._search_event_signals_tool(arguments)
        else:
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=json.dumps({"error": f"Unknown tool: {tool_name}"})
                )],
                isError=True
            )
    
    async def _search_prospects_tool(self, arguments: Dict[str, Any]) -> CallToolResult:
        """Execute the search prospects tool"""
        try:
            event_type = arguments.get("event_type", "all")
            location = arguments.get("location")
            date_range = arguments.get("date_range")
            max_results = arguments.get("max_results", 20)
            
            # Build search query
            query = self._build_prospect_search_query(event_type, location, date_range)
            
            # Perform search
            results = await self._perform_search(query, max_results)
            
            # Extract prospect signals
            prospects = []
            for result in results:
                prospect_signals = self._extract_prospect_signals(result, event_type)
                prospects.extend(prospect_signals)
            
            # Sort by confidence score
            prospects.sort(key=lambda x: x.get("confidence_score", 0), reverse=True)
            
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=json.dumps({
                        "prospects": prospects[:max_results],
                        "total_found": len(prospects),
                        "search_query": query
                    }, indent=2)
                )]
            )
            
        except Exception as e:
            logger.error("Prospect search failed", error=str(e))
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=json.dumps({"error": f"Search failed: {str(e)}"})
                )],
                isError=True
            )
    
    async def _search_company_info_tool(self, arguments: Dict[str, Any]) -> CallToolResult:
        """Execute the search company info tool (placeholder)"""
        return CallToolResult(
            content=[TextContent(
                type="text",
                text=json.dumps({"message": "Company info search not implemented yet"})
            )]
        )
    
    async def _search_event_signals_tool(self, arguments: Dict[str, Any]) -> CallToolResult:
        """Execute the search event signals tool (placeholder)"""
        return CallToolResult(
            content=[TextContent(
                type="text",
                text=json.dumps({"message": "Event signals search not implemented yet"})
            )]
        )
    
    def get_server(self) -> Server:
        """Get the MCP server instance"""
        return self.server
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()


# Create global MCP server instance
web_search_mcp = WebSearchMCP()
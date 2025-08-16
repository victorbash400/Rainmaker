"""
Clean Perplexity Sonar API integration for prospect research.

This module provides a simple, direct interface to Perplexity's Sonar API
without hardcoded patterns or fallback logic.
"""

import asyncio
import httpx
from typing import Dict, List, Any, Optional
import structlog
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

logger = structlog.get_logger(__name__)


class SonarAPIError(Exception):
    """Raised when Perplexity Sonar API calls fail"""
    pass


class WebSearchMCP:
    """Clean Perplexity Sonar API integration for web search"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or self._get_api_key()
        self.base_url = "https://api.perplexity.ai/chat/completions"
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
        )
    
    def _get_api_key(self) -> str:
        """Get Perplexity Sonar API key from .env file"""
        api_key = os.getenv("SONAR_API_KEY")
        if not api_key:
            raise SonarAPIError("SONAR_API_KEY not found in .env file")
        return api_key
    
    async def search_person(self, name: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Search for information about a specific person using Perplexity Sonar.
        
        Args:
            name: Full name of the person
            context: Additional context (company, location, etc.)
            
        Returns:
            Search results from Perplexity Sonar API
        """
        try:
            # Build search query
            query = f"Find information about {name}"
            if context:
                if context.get("company"):
                    query += f" who works at {context['company']}"
                if context.get("location"):
                    query += f" in {context['location']}"
            
            query += ". Include professional background, role, and any event planning activity."
            
            print(f"🔍 Calling Perplexity Sonar API...")
            print(f"   Query: {query}")
            
            payload = {
                "model": "sonar",
                "messages": [
                    {"role": "user", "content": query}
                ]
            }
            
            response = await self.client.post(self.base_url, json=payload)
            
            print(f"✅ Perplexity responded with {response.status_code}")
            
            if response.status_code != 200:
                raise SonarAPIError(f"Perplexity API returned {response.status_code}: {response.text}")
            
            data = response.json()
            
            # Extract citations from search_results
            search_results = data.get("search_results", [])
            citations = []
            for result in search_results:
                citations.append({
                    "title": result.get("title", ""),
                    "url": result.get("url", ""),
                    "date": result.get("date", ""),
                    "last_updated": result.get("last_updated", "")
                })
            
            print(f"📚 Found {len(citations)} citations from person search")
            
            return {
                "query": query,
                "results": [data.get("choices", [{}])[0].get("message", {}).get("content", "")],
                "search_results": search_results,
                "citations": citations,
                "source_count": len(citations),
                "timestamp": datetime.now().isoformat()
            }
            
        except httpx.TimeoutException:
            raise SonarAPIError("Perplexity API request timed out")
        except Exception as e:
            raise SonarAPIError(f"Failed to search person: {str(e)}")
    
    async def search_company(self, company_name: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Search for information about a company using Perplexity Sonar.
        
        Args:
            company_name: Name of the company
            context: Additional context (location, industry, etc.)
            
        Returns:
            Search results from Perplexity Sonar API
        """
        try:
            # Build search query
            query = f"Find information about {company_name} company"
            if context:
                if context.get("location"):
                    query += f" in {context['location']}"
                if context.get("industry"):
                    query += f" in {context['industry']} industry"
            
            query += ". Include company size, industry, recent events, and budget indicators."
            
            print(f"🔍 Calling Perplexity Sonar API for company...")
            print(f"   Query: {query}")
            
            payload = {
                "model": "sonar",
                "messages": [
                    {"role": "user", "content": query}
                ]
            }
            
            response = await self.client.post(self.base_url, json=payload)
            
            print(f"✅ Perplexity responded with {response.status_code}")
            
            if response.status_code != 200:
                raise SonarAPIError(f"Perplexity API returned {response.status_code}: {response.text}")
            
            data = response.json()
            
            # Extract citations from search_results
            search_results = data.get("search_results", [])
            citations = []
            for result in search_results:
                citations.append({
                    "title": result.get("title", ""),
                    "url": result.get("url", ""),
                    "date": result.get("date", ""),
                    "last_updated": result.get("last_updated", "")
                })
            
            print(f"📚 Found {len(citations)} citations from company search")
            
            return {
                "query": query,
                "results": [data.get("choices", [{}])[0].get("message", {}).get("content", "")],
                "search_results": search_results,
                "citations": citations,
                "source_count": len(citations),
                "timestamp": datetime.now().isoformat()
            }
            
        except httpx.TimeoutException:
            raise SonarAPIError("Perplexity API request timed out")
        except Exception as e:
            raise SonarAPIError(f"Failed to search company: {str(e)}")
    
    async def search_event_context(self, search_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Search for event planning context and history using Perplexity Sonar.
        
        Args:
            search_params: Parameters including person, event_type, location, etc.
            
        Returns:
            Search results from Perplexity Sonar API
        """
        try:
            # Build search query
            query = "Find event planning information for"
            
            if search_params.get("person"):
                query += f" {search_params['person']}"
            
            if search_params.get("event_type"):
                query += f" planning {search_params['event_type']}"
            
            if search_params.get("location"):
                query += f" in {search_params['location']}"
            
            query += ". Include event preferences, timeline, budget signals, and social media activity."
            
            print(f"🔍 Calling Perplexity Sonar API for event context...")
            print(f"   Query: {query}")
            
            payload = {
                "model": "sonar",
                "messages": [
                    {"role": "user", "content": query}
                ]
            }
            
            response = await self.client.post(self.base_url, json=payload)
            
            print(f"✅ Perplexity responded with {response.status_code}")
            
            if response.status_code != 200:
                raise SonarAPIError(f"Perplexity API returned {response.status_code}: {response.text}")
            
            data = response.json()
            
            # Extract citations from search_results
            search_results = data.get("search_results", [])
            citations = []
            for result in search_results:
                citations.append({
                    "title": result.get("title", ""),
                    "url": result.get("url", ""),
                    "date": result.get("date", ""),
                    "last_updated": result.get("last_updated", "")
                })
            
            print(f"📚 Found {len(citations)} citations from event context search")
            
            return {
                "query": query,
                "results": [data.get("choices", [{}])[0].get("message", {}).get("content", "")],
                "search_results": search_results,
                "citations": citations,
                "source_count": len(citations),
                "search_type": "event_context",
                "timestamp": datetime.now().isoformat()
            }
            
        except httpx.TimeoutException:
            raise SonarAPIError("Perplexity API request timed out")
        except Exception as e:
            raise SonarAPIError(f"Failed to search event context: {str(e)}")
    
    async def search_prospects(self, search_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Legacy method for compatibility with existing workflow.
        Maps to appropriate search method based on parameters.
        """
        try:
            if search_params.get("prospect_name"):
                return await self.search_person(
                    search_params["prospect_name"],
                    {
                        "company": search_params.get("company"),
                        "location": search_params.get("location")
                    }
                )
            elif search_params.get("company"):
                return await self.search_company(
                    search_params["company"],
                    {"location": search_params.get("location")}
                )
            else:
                return await self.search_event_context(search_params)
                
        except Exception as e:
            raise SonarAPIError(f"Failed to search prospects: {str(e)}")
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()


# Create global instance for backward compatibility
web_search_mcp = type('WebSearchMCPWrapper', (), {
    'server': type('ServerWrapper', (), {
        'call_tool': lambda tool_name, params: WebSearchMCP().search_prospects(params)
    })()
})()
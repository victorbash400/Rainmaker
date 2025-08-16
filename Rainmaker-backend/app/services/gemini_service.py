"""
Google Gemini API integration service with error handling, rate limiting, and cost monitoring
"""

import asyncio
import time
import json
import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
import structlog 
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from google.cloud import aiplatform
from google.auth import default
import vertexai
from vertexai.generative_models import GenerativeModel

from app.core.config import settings

logger = structlog.get_logger(__name__)


@dataclass
class TokenUsage:
    """Token usage tracking for cost monitoring"""
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost: float
    timestamp: datetime


class GeminiService:
    """
    Google Gemini API client with comprehensive error handling, rate limiting, and monitoring
    """
    
    def __init__(self):
        # Set up Google Cloud credentials
        import platform
        if platform.system() == "Windows":
            credentials_path = r"C:\Users\Victo\Desktop\Rainmaker\Rainmaker-backend\ascendant-woods-462020-n0-78d818c9658e.json"
        else:
            credentials_path = "/mnt/c/Users/Victo/Desktop/Rainmaker/Rainmaker-backend/ascendant-woods-462020-n0-78d818c9658e.json"
        
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path
        
        # Initialize Vertex AI
        credentials, project = default()
        self.project_id = project or "ascendant-woods-462020-n0"
        
        # Try multiple regions - some models may not be available in all regions
        self.location = "us-east1"  # Changed from us-central1
        
        vertexai.init(
            project=self.project_id,
            location=self.location,
            credentials=credentials
        )
        
        self.token_usage_history: List[TokenUsage] = []
        self._request_times: List[datetime] = []
        
    
    async def generate_agent_response(
        self,
        system_prompt: str,
        user_message: str,
        context: Optional[Dict[str, Any]] = None,
        model: str = "gemini-1.5-flash"
    ) -> str:
        """
        Generate a response for AI agents using Vertex AI Gemini
        
        Args:
            system_prompt: System instructions for the agent
            user_message: User input or task description
            context: Additional context data
            model: Gemini model to use
            
        Returns:
            Generated response text
        """
        try:
            # Check rate limits before making request
            await self._check_rate_limits()
            
            # Combine system prompt and user message
            full_prompt = f"System Instructions: {system_prompt}\n\n"
            
            # Add context if provided
            if context:
                context_str = "\n".join([f"{k}: {v}" for k, v in context.items()])
                full_prompt += f"Additional context:\n{context_str}\n\n"
            
            full_prompt += f"User Message: {user_message}"
            
            # Make the API call using Vertex AI
            start_time = time.time()
            
            # Use actual available Gemini models in Vertex AI (2025)
            try:
                model_instance = GenerativeModel("gemini-2.5-flash")  # Best price-performance
            except Exception:
                try:
                    model_instance = GenerativeModel("gemini-2.0-flash")
                except Exception:
                    try:
                        model_instance = GenerativeModel("gemini-2.5-pro")
                    except Exception:
                        model_instance = GenerativeModel("gemini-2.0-flash-lite")
            response = await asyncio.to_thread(
                model_instance.generate_content,
                full_prompt,
                generation_config={
                    "temperature": 0.7,
                    "max_output_tokens": 8192,  # Much higher limit
                }
            )
            
            # Track usage and performance
            await self._track_usage(response, time.time() - start_time)
            
            logger.info(
                "Vertex AI Gemini generation successful",
                model=model,
                response_time=time.time() - start_time
            )
            
            return response.text if response.text else ""
            
        except Exception as e:
            logger.error(
                "Vertex AI Gemini generation failed",
                error=str(e),
                model=model
            )
            raise GeminiServiceError(f"Generation failed: {str(e)}") from e
    
    async def generate_personalized_message(
        self,
        template_type: str,
        prospect_data: Dict[str, Any],
        event_requirements: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate personalized outreach messages for prospects
        
        Args:
            template_type: Type of message (wedding, corporate, birthday, etc.)
            prospect_data: Information about the prospect
            event_requirements: Event details if available
            
        Returns:
            Personalized message text
        """
        system_prompt = f"""
        You are an expert event planning sales professional. Generate a personalized outreach message for a {template_type} event.
        
        Guidelines:
        - Be warm and professional
        - Reference specific details about the prospect
        - Highlight relevant experience with {template_type} events
        - Include a clear call-to-action
        - Keep the message concise (under 200 words)
        - Avoid being overly salesy
        """
        
        user_message = f"""
        Create a personalized outreach message for:
        
        Prospect Information:
        {self._format_prospect_data(prospect_data)}
        
        Event Requirements:
        {self._format_event_requirements(event_requirements) if event_requirements else "Not yet specified"}
        """
        
        return await self.generate_agent_response(
            system_prompt=system_prompt,
            user_message=user_message
        )
    
    async def generate_json_response(
        self,
        system_prompt: str,
        user_message: str,
        context: Optional[Dict[str, Any]] = None,
        model: str = "gemini-1.5-flash"
    ) -> Dict[str, Any]:
        """
        Generate a JSON response using Gemini
        
        Args:
            system_prompt: System instructions for the agent
            user_message: User input or task description
            context: Additional context data
            model: Gemini model to use
            
        Returns:
            Parsed JSON response
        """
        response_text = await self.generate_agent_response(
            system_prompt=system_prompt,
            user_message=user_message,
            context=context,
            model=model
        )
        
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            logger.warning("Failed to parse JSON response", response=response_text)
            # Try to extract JSON from response if it's wrapped in markdown code blocks
            import re
            
            # First try to extract from ```json blocks
            json_block_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_text, re.DOTALL)
            if json_block_match:
                try:
                    return json.loads(json_block_match.group(1))
                except json.JSONDecodeError:
                    pass
            
            # Fallback to finding any JSON object
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except json.JSONDecodeError:
                    pass
            return {}

    async def extract_requirements_from_conversation(
        self,
        conversation_history: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """
        Extract structured event requirements from conversation history
        
        Args:
            conversation_history: List of messages with 'role' and 'content'
            
        Returns:
            Structured requirements dictionary
        """
        system_prompt = """
        You are an expert at extracting structured event planning requirements from conversations.
        
        Extract the following information if mentioned:
        - event_type: (wedding, corporate_event, birthday, anniversary, etc.)
        - event_date: (specific date or timeframe)
        - guest_count: (number or range)
        - budget_range: (min and max if mentioned)
        - location_preference: (city, venue type, etc.)
        - special_requirements: (dietary, accessibility, themes, etc.)
        - style_preferences: (formal, casual, modern, traditional, etc.)
        
        Return the information as a JSON object. Use null for missing information.
        """
        
        conversation_text = "\n".join([
            f"{msg['role']}: {msg['content']}" 
            for msg in conversation_history
        ])
        
        user_message = f"""
        Extract event requirements from this conversation:
        
        {conversation_text}
        """
        
        return await self.generate_json_response(
            system_prompt=system_prompt,
            user_message=user_message
        )
    
    async def _check_rate_limits(self):
        """Check and enforce rate limits"""
        now = datetime.now()
        
        # Clean old request times (older than 1 minute)
        self._request_times = [
            req_time for req_time in self._request_times 
            if now - req_time < timedelta(minutes=1)
        ]
        
        # Gemini has different rate limits - being conservative
        if len(self._request_times) >= 50:  # Conservative limit for Gemini
            sleep_time = 60 - (now - min(self._request_times)).total_seconds()
            if sleep_time > 0:
                logger.warning(
                    "Rate limit approaching, sleeping",
                    sleep_time=sleep_time,
                    current_requests=len(self._request_times)
                )
                await asyncio.sleep(sleep_time)
        
        # Record this request
        self._request_times.append(now)
    
    async def _track_usage(self, response, response_time: float):
        """Track token usage and costs"""
        try:
            # Gemini pricing is much lower than GPT-4
            # Approximate cost calculation for Gemini Flash
            prompt_tokens = getattr(response.usage_metadata, 'prompt_token_count', 0) if hasattr(response, 'usage_metadata') else 0
            completion_tokens = getattr(response.usage_metadata, 'candidates_token_count', 0) if hasattr(response, 'usage_metadata') else 0
            total_tokens = prompt_tokens + completion_tokens
            
            # Gemini Flash pricing (approximate)
            cost_per_1k_prompt = 0.00015  # Much cheaper than GPT-4
            cost_per_1k_completion = 0.0006
            
            estimated_cost = (
                (prompt_tokens / 1000) * cost_per_1k_prompt +
                (completion_tokens / 1000) * cost_per_1k_completion
            )
            
            usage = TokenUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                estimated_cost=estimated_cost,
                timestamp=datetime.now()
            )
            
            self.token_usage_history.append(usage)
            
            # Keep only last 1000 usage records
            if len(self.token_usage_history) > 1000:
                self.token_usage_history = self.token_usage_history[-1000:]
            
            logger.info(
                "Token usage tracked",
                prompt_tokens=usage.prompt_tokens,
                completion_tokens=usage.completion_tokens,
                estimated_cost=usage.estimated_cost,
                response_time=response_time
            )
        except Exception as e:
            logger.warning("Failed to track usage", error=str(e))
    
    def get_usage_stats(self, hours: int = 24) -> Dict[str, Any]:
        """
        Get usage statistics for the specified time period
        
        Args:
            hours: Number of hours to look back
            
        Returns:
            Usage statistics dictionary
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_usage = [
            usage for usage in self.token_usage_history 
            if usage.timestamp > cutoff_time
        ]
        
        if not recent_usage:
            return {
                "total_requests": 0,
                "total_tokens": 0,
                "total_cost": 0.0,
                "average_tokens_per_request": 0,
                "time_period_hours": hours
            }
        
        total_tokens = sum(usage.total_tokens for usage in recent_usage)
        total_cost = sum(usage.estimated_cost for usage in recent_usage)
        
        return {
            "total_requests": len(recent_usage),
            "total_tokens": total_tokens,
            "total_cost": round(total_cost, 6),  # Gemini costs are much smaller
            "average_tokens_per_request": round(total_tokens / len(recent_usage), 2),
            "time_period_hours": hours
        }
    
    def _format_prospect_data(self, prospect_data: Dict[str, Any]) -> str:
        """Format prospect data for prompts"""
        formatted = []
        for key, value in prospect_data.items():
            if value:
                formatted.append(f"- {key.replace('_', ' ').title()}: {value}")
        return "\n".join(formatted) if formatted else "No prospect data available"
    
    def _format_event_requirements(self, requirements: Dict[str, Any]) -> str:
        """Format event requirements for prompts"""
        formatted = []
        for key, value in requirements.items():
            if value:
                formatted.append(f"- {key.replace('_', ' ').title()}: {value}")
        return "\n".join(formatted) if formatted else "No requirements specified"


class GeminiServiceError(Exception):
    """Custom exception for Gemini service errors"""
    pass


# Global service instance
gemini_service = GeminiService()
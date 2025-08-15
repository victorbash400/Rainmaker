"""
OpenAI API integration service with error handling, rate limiting, and cost monitoring
"""

import asyncio
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
import structlog
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion
from openai.types.chat.chat_completion_message_param import ChatCompletionMessageParam

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


@dataclass
class RateLimitInfo:
    """Rate limiting information"""
    requests_per_minute: int
    tokens_per_minute: int
    current_requests: int
    current_tokens: int
    reset_time: datetime


class OpenAIService:
    """
    OpenAI API client with comprehensive error handling, rate limiting, and monitoring
    """
    
    def __init__(self):
        # Clean the API key to remove any leading '=' characters
        api_key = settings.OPENAI_API_KEY.get_secret_value().lstrip('=')
        self.client = AsyncOpenAI(api_key=api_key)
        self.token_usage_history: List[TokenUsage] = []
        self.rate_limit_info = RateLimitInfo(
            requests_per_minute=3500,  # Conservative limit
            tokens_per_minute=90000,   # Conservative limit
            current_requests=0,
            current_tokens=0,
            reset_time=datetime.now() + timedelta(minutes=1)
        )
        self._request_times: List[datetime] = []
        self._token_usage_minute: List[int] = []
        
    async def chat_completion(
        self,
        messages: List[ChatCompletionMessageParam],
        model: str = "gpt-4",
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[str] = None,
        **kwargs
    ) -> ChatCompletion:
        """
        Create a chat completion with error handling and rate limiting
        
        Args:
            messages: List of chat messages
            model: OpenAI model to use
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional parameters for OpenAI API
            
        Returns:
            ChatCompletion response
            
        Raises:
            OpenAIServiceError: For API errors, rate limits, etc.
        """
        try:
            # Check rate limits before making request
            await self._check_rate_limits()
            
            # Make the API call
            start_time = time.time()
            call_params = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                **kwargs
            }
            
            if max_tokens:
                call_params["max_tokens"] = max_tokens
            if tools:
                call_params["tools"] = tools
            if tool_choice:
                call_params["tool_choice"] = tool_choice
                
            response = await self.client.chat.completions.create(**call_params)
            
            # Track usage and performance
            await self._track_usage(response, time.time() - start_time)
            
            logger.info(
                "OpenAI chat completion successful",
                model=model,
                tokens_used=response.usage.total_tokens if response.usage else 0,
                response_time=time.time() - start_time
            )
            
            return response
            
        except Exception as e:
            logger.error(
                "OpenAI chat completion failed",
                error=str(e),
                model=model,
                message_count=len(messages)
            )
            raise OpenAIServiceError(f"Chat completion failed: {str(e)}") from e
    
    async def generate_agent_response(
        self,
        system_prompt: str,
        user_message: str,
        context: Optional[Dict[str, Any]] = None,
        model: str = "gpt-4"
    ) -> str:
        """
        Generate a response for AI agents with standardized prompting
        
        Args:
            system_prompt: System instructions for the agent
            user_message: User input or task description
            context: Additional context data
            model: OpenAI model to use
            
        Returns:
            Generated response text
        """
        messages: List[ChatCompletionMessageParam] = [
            {"role": "system", "content": system_prompt}
        ]
        
        # Add context if provided
        if context:
            context_str = "\n".join([f"{k}: {v}" for k, v in context.items()])
            messages.append({
                "role": "system", 
                "content": f"Additional context:\n{context_str}"
            })
        
        messages.append({"role": "user", "content": user_message})
        
        response = await self.chat_completion(
            messages=messages,
            model=model,
            temperature=0.7
        )
        
        return response.choices[0].message.content or ""
    
    async def generate_agent_response_with_tools(
        self,
        system_prompt: str,
        user_message: str,
        tools: List[Dict[str, Any]],
        tool_handlers: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
        model: str = "gpt-4",
        max_tool_calls: int = 5
    ) -> str:
        """
        Generate agent response with MCP tool calling capability
        
        Args:
            system_prompt: System instructions for the agent
            user_message: User input or task description  
            tools: List of OpenAI function definitions
            tool_handlers: Dict mapping tool names to handler objects
            context: Additional context data
            model: OpenAI model to use
            max_tool_calls: Maximum number of tool call iterations
            
        Returns:
            Generated response text after tool execution
        """
        messages: List[ChatCompletionMessageParam] = [
            {"role": "system", "content": system_prompt}
        ]
        
        # Add context if provided
        if context:
            context_str = "\n".join([f"{k}: {v}" for k, v in context.items()])
            messages.append({
                "role": "system", 
                "content": f"Additional context:\n{context_str}"
            })
        
        messages.append({"role": "user", "content": user_message})
        
        # Tool calling loop
        for iteration in range(max_tool_calls):
            response = await self.chat_completion(
                messages=messages,
                model=model,
                temperature=0.7,
                tools=tools,
                tool_choice="auto"
            )
            
            message = response.choices[0].message
            
            # If no tool calls, return the response
            if not message.tool_calls:
                return message.content or ""
            
            # Add assistant message to conversation
            messages.append({
                "role": "assistant",
                "content": message.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function", 
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    } for tc in message.tool_calls
                ]
            })
            
            # Execute tool calls
            for tool_call in message.tool_calls:
                tool_name = tool_call.function.name
                
                if tool_name in tool_handlers:
                    try:
                        import json
                        tool_args = json.loads(tool_call.function.arguments)
                        handler = tool_handlers[tool_name]
                        
                        # Execute the MCP tool
                        result = await handler.call_tool(tool_name, tool_args)
                        
                        # Format result
                        if hasattr(result, 'content') and result.content:
                            tool_result = result.content[0].text if result.content else "No result"
                        else:
                            tool_result = str(result)
                            
                        messages.append({
                            "role": "tool",
                            "content": tool_result,
                            "tool_call_id": tool_call.id
                        })
                        
                    except Exception as e:
                        logger.error(f"Tool execution failed: {tool_name}", error=str(e))
                        messages.append({
                            "role": "tool", 
                            "content": f"Error executing {tool_name}: {str(e)}",
                            "tool_call_id": tool_call.id
                        })
                else:
                    messages.append({
                        "role": "tool",
                        "content": f"Unknown tool: {tool_name}",
                        "tool_call_id": tool_call.id
                    })
        
        # Final response after tool calls
        final_response = await self.chat_completion(
            messages=messages,
            model=model,
            temperature=0.7
        )
        
        return final_response.choices[0].message.content or ""
    
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
            user_message=user_message,
            model="gpt-4"
        )
    
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
        
        response = await self.generate_agent_response(
            system_prompt=system_prompt,
            user_message=user_message,
            model="gpt-4"
        )
        
        try:
            import json
            return json.loads(response)
        except json.JSONDecodeError:
            logger.warning("Failed to parse requirements JSON", response=response)
            return {}
    
    async def _check_rate_limits(self):
        """Check and enforce rate limits"""
        now = datetime.now()
        
        # Clean old request times (older than 1 minute)
        self._request_times = [
            req_time for req_time in self._request_times 
            if now - req_time < timedelta(minutes=1)
        ]
        
        # Check if we're approaching rate limits
        if len(self._request_times) >= self.rate_limit_info.requests_per_minute * 0.9:
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
    
    async def _track_usage(self, response: ChatCompletion, response_time: float):
        """Track token usage and costs"""
        if not response.usage:
            return
            
        # Estimate cost based on model pricing (approximate)
        model = response.model
        cost_per_1k_prompt = 0.03 if "gpt-4" in model else 0.0015
        cost_per_1k_completion = 0.06 if "gpt-4" in model else 0.002
        
        estimated_cost = (
            (response.usage.prompt_tokens / 1000) * cost_per_1k_prompt +
            (response.usage.completion_tokens / 1000) * cost_per_1k_completion
        )
        
        usage = TokenUsage(
            prompt_tokens=response.usage.prompt_tokens,
            completion_tokens=response.usage.completion_tokens,
            total_tokens=response.usage.total_tokens,
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
            "total_cost": round(total_cost, 4),
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


class OpenAIServiceError(Exception):
    """Custom exception for OpenAI service errors"""
    pass


# Global service instance
openai_service = OpenAIService()
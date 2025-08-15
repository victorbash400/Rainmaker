"""
Unit tests for OpenAI service
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
import json

from app.services.openai_service import OpenAIService, OpenAIServiceError, TokenUsage


@pytest.fixture
def openai_service():
    """Create OpenAI service instance for testing"""
    return OpenAIService()


@pytest.fixture
def mock_openai_response():
    """Mock OpenAI API response"""
    response = MagicMock()
    response.choices = [MagicMock()]
    response.choices[0].message.content = "Test response"
    response.usage = MagicMock()
    response.usage.prompt_tokens = 50
    response.usage.completion_tokens = 25
    response.usage.total_tokens = 75
    response.model = "gpt-4"
    return response


class TestOpenAIService:
    """Test cases for OpenAI service"""
    
    @pytest.mark.asyncio
    async def test_chat_completion_success(self, openai_service, mock_openai_response):
        """Test successful chat completion"""
        with patch.object(openai_service.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_openai_response
            
            messages = [{"role": "user", "content": "Hello"}]
            response = await openai_service.chat_completion(messages)
            
            assert response == mock_openai_response
            mock_create.assert_called_once()
            
            # Check that usage was tracked
            assert len(openai_service.token_usage_history) == 1
            usage = openai_service.token_usage_history[0]
            assert usage.total_tokens == 75
            assert usage.estimated_cost > 0
    
    @pytest.mark.asyncio
    async def test_chat_completion_error_handling(self, openai_service):
        """Test error handling in chat completion"""
        with patch.object(openai_service.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.side_effect = Exception("API Error")
            
            messages = [{"role": "user", "content": "Hello"}]
            
            with pytest.raises(OpenAIServiceError) as exc_info:
                await openai_service.chat_completion(messages)
            
            assert "Chat completion failed" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_generate_agent_response(self, openai_service, mock_openai_response):
        """Test agent response generation"""
        with patch.object(openai_service, 'chat_completion', new_callable=AsyncMock) as mock_chat:
            mock_chat.return_value = mock_openai_response
            
            response = await openai_service.generate_agent_response(
                system_prompt="You are a helpful assistant",
                user_message="Hello",
                context={"user_id": "123"}
            )
            
            assert response == "Test response"
            mock_chat.assert_called_once()
            
            # Check that context was included in messages
            call_args = mock_chat.call_args[1]
            messages = call_args['messages']
            assert len(messages) == 3  # system, context, user
            assert "user_id: 123" in messages[1]['content']
    
    @pytest.mark.asyncio
    async def test_generate_personalized_message(self, openai_service, mock_openai_response):
        """Test personalized message generation"""
        with patch.object(openai_service, 'generate_agent_response', new_callable=AsyncMock) as mock_generate:
            mock_generate.return_value = "Personalized wedding message"
            
            prospect_data = {
                "name": "John Doe",
                "event_type": "wedding",
                "location": "New York"
            }
            
            response = await openai_service.generate_personalized_message(
                template_type="wedding",
                prospect_data=prospect_data
            )
            
            assert response == "Personalized wedding message"
            mock_generate.assert_called_once()
            
            # Check that prospect data was formatted in the call
            call_args = mock_generate.call_args[1]
            assert "John Doe" in call_args['user_message']
            assert "wedding" in call_args['system_prompt']
    
    @pytest.mark.asyncio
    async def test_extract_requirements_from_conversation(self, openai_service):
        """Test requirements extraction from conversation"""
        mock_requirements = {
            "event_type": "wedding",
            "guest_count": 150,
            "budget_range": {"min": 10000, "max": 15000}
        }
        
        with patch.object(openai_service, 'generate_agent_response', new_callable=AsyncMock) as mock_generate:
            mock_generate.return_value = json.dumps(mock_requirements)
            
            conversation = [
                {"role": "user", "content": "I'm planning a wedding for 150 guests"},
                {"role": "assistant", "content": "What's your budget range?"},
                {"role": "user", "content": "Between $10,000 and $15,000"}
            ]
            
            requirements = await openai_service.extract_requirements_from_conversation(conversation)
            
            assert requirements == mock_requirements
            mock_generate.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_extract_requirements_invalid_json(self, openai_service):
        """Test requirements extraction with invalid JSON response"""
        with patch.object(openai_service, 'generate_agent_response', new_callable=AsyncMock) as mock_generate:
            mock_generate.return_value = "Invalid JSON response"
            
            conversation = [{"role": "user", "content": "Hello"}]
            requirements = await openai_service.extract_requirements_from_conversation(conversation)
            
            assert requirements == {}
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self, openai_service):
        """Test rate limiting functionality"""
        # Fill up the request history to trigger rate limiting
        now = datetime.now()
        # Create enough recent requests to trigger rate limiting (90% of 3500 = 3150)
        openai_service._request_times = [now - timedelta(seconds=1)] * 3150
        
        with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            await openai_service._check_rate_limits()
            # Should sleep when approaching rate limit
            mock_sleep.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_rate_limiting_no_sleep_needed(self, openai_service):
        """Test rate limiting when no sleep is needed"""
        # Only a few requests, should not trigger rate limiting
        now = datetime.now()
        openai_service._request_times = [now - timedelta(seconds=1)] * 10
        
        with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            await openai_service._check_rate_limits()
            # Should not sleep when well under rate limit
            mock_sleep.assert_not_called()
    
    def test_usage_tracking(self, openai_service, mock_openai_response):
        """Test token usage tracking"""
        # Test tracking usage
        import asyncio
        asyncio.run(openai_service._track_usage(mock_openai_response, 1.5))
        
        assert len(openai_service.token_usage_history) == 1
        usage = openai_service.token_usage_history[0]
        assert usage.prompt_tokens == 50
        assert usage.completion_tokens == 25
        assert usage.total_tokens == 75
        assert usage.estimated_cost > 0
    
    def test_get_usage_stats(self, openai_service):
        """Test usage statistics calculation"""
        # Add some mock usage data
        now = datetime.now()
        openai_service.token_usage_history = [
            TokenUsage(50, 25, 75, 0.01, now - timedelta(hours=1)),
            TokenUsage(60, 30, 90, 0.012, now - timedelta(hours=2)),
            TokenUsage(40, 20, 60, 0.008, now - timedelta(hours=25))  # Outside 24h window
        ]
        
        stats = openai_service.get_usage_stats(hours=24)
        
        assert stats['total_requests'] == 2  # Only 2 within 24 hours
        assert stats['total_tokens'] == 165  # 75 + 90
        assert stats['total_cost'] == 0.022  # 0.01 + 0.012
        assert stats['average_tokens_per_request'] == 82.5  # 165 / 2
    
    def test_get_usage_stats_empty(self, openai_service):
        """Test usage statistics with no data"""
        stats = openai_service.get_usage_stats(hours=24)
        
        assert stats['total_requests'] == 0
        assert stats['total_tokens'] == 0
        assert stats['total_cost'] == 0.0
        assert stats['average_tokens_per_request'] == 0
    
    def test_format_prospect_data(self, openai_service):
        """Test prospect data formatting"""
        prospect_data = {
            "name": "John Doe",
            "email": "john@example.com",
            "company_name": "",  # Empty value should be skipped
            "location": "New York"
        }
        
        formatted = openai_service._format_prospect_data(prospect_data)
        
        assert "Name: John Doe" in formatted
        assert "Email: john@example.com" in formatted
        assert "Location: New York" in formatted
        assert "Company Name" not in formatted  # Empty value skipped
    
    def test_format_event_requirements(self, openai_service):
        """Test event requirements formatting"""
        requirements = {
            "event_type": "wedding",
            "guest_count": 150,
            "budget_range": None,  # None value should be skipped
            "location_preference": "outdoor"
        }
        
        formatted = openai_service._format_event_requirements(requirements)
        
        assert "Event Type: wedding" in formatted
        assert "Guest Count: 150" in formatted
        assert "Location Preference: outdoor" in formatted
        assert "Budget Range" not in formatted  # None value skipped


class TestTokenUsage:
    """Test cases for TokenUsage dataclass"""
    
    def test_token_usage_creation(self):
        """Test TokenUsage dataclass creation"""
        now = datetime.now()
        usage = TokenUsage(
            prompt_tokens=50,
            completion_tokens=25,
            total_tokens=75,
            estimated_cost=0.01,
            timestamp=now
        )
        
        assert usage.prompt_tokens == 50
        assert usage.completion_tokens == 25
        assert usage.total_tokens == 75
        assert usage.estimated_cost == 0.01
        assert usage.timestamp == now


@pytest.mark.asyncio
async def test_openai_service_integration():
    """Integration test for OpenAI service (requires API key)"""
    # This test requires a real API key and should be run separately
    # or skipped in CI/CD environments
    pytest.skip("Integration test - requires real OpenAI API key")
    
    service = OpenAIService()
    
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Say hello in exactly 3 words."}
    ]
    
    response = await service.chat_completion(messages, model="gpt-3.5-turbo")
    
    assert response.choices[0].message.content
    assert len(service.token_usage_history) == 1
"""
Unit tests for state management operations.

Tests the core state management functionality including validation,
serialization, stage transitions, error handling, and utility functions.
"""

import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from app.core.state import (
    RainmakerState, StateManager, WorkflowStage, AgentError, ProspectData,
    HunterResults, EnrichmentData, OutreachCampaign, ConversationSummary,
    ProposalData, MeetingDetails, StateValidationError
)
from app.db.models import ProspectStatus, EventType, CampaignStatus


class TestProspectData:
    """Test ProspectData model"""
    
    def test_prospect_data_creation(self):
        """Test creating ProspectData instance"""
        prospect = ProspectData(
            name="John Smith",
            email="john@example.com",
            phone="555-0123",
            company_name="Smith Events",
            location="New York, NY",
            prospect_type="individual",
            source="web_search",
            status=ProspectStatus.DISCOVERED,
            lead_score=85
        )
        
        assert prospect.name == "John Smith"
        assert prospect.email == "john@example.com"
        assert prospect.prospect_type == "individual"
        assert prospect.status == ProspectStatus.DISCOVERED
        assert prospect.lead_score == 85
    
    def test_prospect_data_defaults(self):
        """Test ProspectData with default values"""
        prospect = ProspectData(
            name="Jane Doe",
            prospect_type="company",
            source="linkedin",
            status=ProspectStatus.DISCOVERED
        )
        
        assert prospect.email is None
        assert prospect.phone is None
        assert prospect.lead_score == 0
        assert prospect.assigned_to is None


class TestAgentError:
    """Test AgentError model"""
    
    def test_agent_error_creation(self):
        """Test creating AgentError instance"""
        error = AgentError(
            agent_name="prospect_hunter",
            error_type="api_failure",
            error_message="Rate limit exceeded",
            details={"status_code": 429, "retry_after": 60},
            retry_count=2
        )
        
        assert error.agent_name == "prospect_hunter"
        assert error.error_type == "api_failure"
        assert error.error_message == "Rate limit exceeded"
        assert error.details["status_code"] == 429
        assert error.retry_count == 2
        assert isinstance(error.timestamp, datetime)
    
    def test_agent_error_defaults(self):
        """Test AgentError with default values"""
        error = AgentError(
            agent_name="test_agent",
            error_type="test_error",
            error_message="Test message"
        )
        
        assert error.details == {}
        assert error.retry_count == 0
        assert isinstance(error.timestamp, datetime)


class TestHunterResults:
    """Test HunterResults model"""
    
    def test_hunter_results_creation(self):
        """Test creating HunterResults instance"""
        results = HunterResults(
            search_queries=["wedding NYC", "event planning"],
            sources_searched=["google", "linkedin"],
            prospects_found=25,
            confidence_score=0.85,
            event_signals=["getting married", "planning celebration"],
            social_media_posts=[
                {"platform": "twitter", "content": "Planning my wedding!"}
            ]
        )
        
        assert len(results.search_queries) == 2
        assert results.prospects_found == 25
        assert results.confidence_score == 0.85
        assert "getting married" in results.event_signals
    
    def test_hunter_results_defaults(self):
        """Test HunterResults with default values"""
        results = HunterResults()
        
        assert results.search_queries == []
        assert results.sources_searched == []
        assert results.prospects_found == 0
        assert results.confidence_score == 0.0
        assert results.event_signals == []


class TestStateManager:
    """Test StateManager utility class"""
    
    @pytest.fixture
    def sample_prospect_data(self):
        """Sample prospect data for testing"""
        return ProspectData(
            name="Test Prospect",
            email="test@example.com",
            prospect_type="individual",
            source="test",
            status=ProspectStatus.DISCOVERED
        )
    
    def test_create_initial_state(self, sample_prospect_data):
        """Test creating initial workflow state"""
        state = StateManager.create_initial_state(
            prospect_data=sample_prospect_data,
            workflow_id="test-workflow-123",
            assigned_human="manager@example.com"
        )
        
        assert state["workflow_id"] == "test-workflow-123"
        assert state["current_stage"] == WorkflowStage.HUNTING
        assert len(state["completed_stages"]) == 0
        assert state["prospect_data"] == sample_prospect_data
        assert state["assigned_human"] == "manager@example.com"
        assert state["retry_count"] == 0
        assert state["max_retries"] == 3
        assert state["human_intervention_needed"] is False
        assert state["approval_pending"] is False
        assert isinstance(state["workflow_started_at"], datetime)
    
    def test_create_initial_state_with_auto_id(self, sample_prospect_data):
        """Test creating initial state with auto-generated workflow ID"""
        state = StateManager.create_initial_state(prospect_data=sample_prospect_data)
        
        assert "workflow_id" in state
        assert len(state["workflow_id"]) == 36  # UUID length
        assert "-" in state["workflow_id"]  # UUID format
    
    def test_validate_state_success(self, sample_prospect_data):
        """Test successful state validation"""
        state = StateManager.create_initial_state(prospect_data=sample_prospect_data)
        
        # Should not raise exception
        assert StateManager.validate_state(state) is True
    
    def test_validate_state_missing_required_field(self, sample_prospect_data):
        """Test state validation with missing required field"""
        state = StateManager.create_initial_state(prospect_data=sample_prospect_data)
        del state["workflow_id"]
        
        with pytest.raises(StateValidationError, match="Missing required field: workflow_id"):
            StateManager.validate_state(state)
    
    def test_validate_state_invalid_workflow_id(self, sample_prospect_data):
        """Test state validation with invalid workflow ID"""
        state = StateManager.create_initial_state(prospect_data=sample_prospect_data)
        state["workflow_id"] = "invalid-id"
        
        with pytest.raises(StateValidationError, match="Invalid workflow_id format"):
            StateManager.validate_state(state)
    
    def test_validate_state_current_stage_in_completed(self, sample_prospect_data):
        """Test state validation with current stage in completed stages"""
        state = StateManager.create_initial_state(prospect_data=sample_prospect_data)
        state["completed_stages"] = [WorkflowStage.HUNTING]
        # Current stage is still HUNTING
        
        with pytest.raises(StateValidationError, match="Current stage .* cannot be in completed stages"):
            StateManager.validate_state(state)
    
    def test_validate_state_negative_retry_count(self, sample_prospect_data):
        """Test state validation with negative retry count"""
        state = StateManager.create_initial_state(prospect_data=sample_prospect_data)
        state["retry_count"] = -1
        
        with pytest.raises(StateValidationError, match="retry_count cannot be negative"):
            StateManager.validate_state(state)
    
    def test_serialize_state(self, sample_prospect_data):
        """Test state serialization to JSON"""
        state = StateManager.create_initial_state(prospect_data=sample_prospect_data)
        
        # Add some complex data
        state["hunter_results"] = HunterResults(
            search_queries=["test query"],
            prospects_found=5,
            confidence_score=0.8
        )
        
        serialized = StateManager.serialize_state(state)
        
        assert isinstance(serialized, str)
        
        # Should be valid JSON
        parsed = json.loads(serialized)
        assert parsed["workflow_id"] == state["workflow_id"]
        assert parsed["current_stage"] == WorkflowStage.HUNTING.value
    
    def test_deserialize_state(self, sample_prospect_data):
        """Test state deserialization from JSON"""
        original_state = StateManager.create_initial_state(prospect_data=sample_prospect_data)
        
        # Serialize then deserialize
        serialized = StateManager.serialize_state(original_state)
        deserialized = StateManager.deserialize_state(serialized)
        
        assert deserialized["workflow_id"] == original_state["workflow_id"]
        assert deserialized["current_stage"] == original_state["current_stage"]
        assert isinstance(deserialized["workflow_started_at"], datetime)
        assert isinstance(deserialized["prospect_data"], (dict, ProspectData))
    
    def test_deserialize_state_invalid_json(self):
        """Test deserializing invalid JSON"""
        invalid_json = "invalid json string"
        
        with pytest.raises(StateValidationError, match="Failed to deserialize state"):
            StateManager.deserialize_state(invalid_json)
    
    def test_update_stage(self, sample_prospect_data):
        """Test updating workflow stage"""
        state = StateManager.create_initial_state(prospect_data=sample_prospect_data)
        original_time = state["last_updated_at"]
        
        # Update to next stage
        updated_state = StateManager.update_stage(
            state, 
            WorkflowStage.ENRICHING,
            track_duration=True
        )
        
        assert updated_state["current_stage"] == WorkflowStage.ENRICHING
        assert WorkflowStage.HUNTING in updated_state["completed_stages"]
        assert updated_state["last_updated_at"] > original_time
        assert "stage_durations" in updated_state
        assert WorkflowStage.HUNTING.value in updated_state["stage_durations"]
    
    def test_update_stage_no_duration_tracking(self, sample_prospect_data):
        """Test updating stage without duration tracking"""
        state = StateManager.create_initial_state(prospect_data=sample_prospect_data)
        
        updated_state = StateManager.update_stage(
            state,
            WorkflowStage.ENRICHING,
            track_duration=False
        )
        
        assert updated_state["current_stage"] == WorkflowStage.ENRICHING
        assert WorkflowStage.HUNTING in updated_state["completed_stages"]
        # Duration should not be tracked
        assert "stage_durations" not in updated_state or \
               WorkflowStage.HUNTING.value not in updated_state.get("stage_durations", {})
    
    def test_add_error(self, sample_prospect_data):
        """Test adding error to state"""
        state = StateManager.create_initial_state(prospect_data=sample_prospect_data)
        
        updated_state = StateManager.add_error(
            state,
            agent_name="test_agent",
            error_type="api_failure",
            error_message="Test error",
            details={"code": 500}
        )
        
        assert len(updated_state["errors"]) == 1
        assert updated_state["retry_count"] == 1
        
        error = updated_state["errors"][0]
        assert error.agent_name == "test_agent"
        assert error.error_type == "api_failure"
        assert error.error_message == "Test error"
        assert error.details["code"] == 500
    
    def test_add_error_max_retries_exceeded(self, sample_prospect_data):
        """Test adding error when max retries exceeded"""
        state = StateManager.create_initial_state(prospect_data=sample_prospect_data)
        state["retry_count"] = 2  # One less than max_retries (3)
        
        updated_state = StateManager.add_error(
            state,
            agent_name="test_agent",
            error_type="api_failure",
            error_message="Final error"
        )
        
        assert updated_state["retry_count"] == 3
        assert updated_state["human_intervention_needed"] is True
        assert updated_state["current_stage"] == WorkflowStage.FAILED
    
    def test_request_approval(self, sample_prospect_data):
        """Test requesting approval"""
        state = StateManager.create_initial_state(prospect_data=sample_prospect_data)
        
        updated_state = StateManager.request_approval(
            state,
            approval_type="proposal_review",
            data={"amount": 15000},
            reason="High value proposal requires approval"
        )
        
        assert updated_state["approval_pending"] is True
        assert updated_state["current_stage"] == WorkflowStage.PENDING_APPROVAL
        assert len(updated_state["approval_requests"]) == 1
        
        approval_request = updated_state["approval_requests"][0]
        assert approval_request["type"] == "proposal_review"
        assert approval_request["data"]["amount"] == 15000
        assert approval_request["reason"] == "High value proposal requires approval"
        assert approval_request["status"] == "pending"
    
    def test_calculate_progress_initial(self, sample_prospect_data):
        """Test progress calculation for initial state"""
        state = StateManager.create_initial_state(prospect_data=sample_prospect_data)
        
        progress = StateManager.calculate_progress(state)
        
        # Should have some progress for being in HUNTING stage
        assert 0 < progress < 100
    
    def test_calculate_progress_partial_completion(self, sample_prospect_data):
        """Test progress calculation with partial completion"""
        state = StateManager.create_initial_state(prospect_data=sample_prospect_data)
        state["completed_stages"] = [WorkflowStage.HUNTING, WorkflowStage.ENRICHING]
        state["current_stage"] = WorkflowStage.OUTREACH
        
        progress = StateManager.calculate_progress(state)
        
        # Should have significant progress
        assert 30 < progress < 70
    
    def test_calculate_progress_completed(self, sample_prospect_data):
        """Test progress calculation for completed workflow"""
        state = StateManager.create_initial_state(prospect_data=sample_prospect_data)
        state["completed_stages"] = [
            WorkflowStage.HUNTING, WorkflowStage.ENRICHING, WorkflowStage.OUTREACH,
            WorkflowStage.CONVERSATION, WorkflowStage.PROPOSAL, WorkflowStage.MEETING
        ]
        state["current_stage"] = WorkflowStage.COMPLETED
        
        progress = StateManager.calculate_progress(state)
        
        assert progress == 100.0
    
    def test_calculate_progress_failed_workflow(self, sample_prospect_data):
        """Test progress calculation for failed workflow"""
        state = StateManager.create_initial_state(prospect_data=sample_prospect_data)
        state["completed_stages"] = [WorkflowStage.HUNTING]
        state["current_stage"] = WorkflowStage.FAILED
        
        progress = StateManager.calculate_progress(state)
        
        # Should still show some progress based on completed stages
        assert progress > 0
        assert progress < 100


class TestWorkflowStage:
    """Test WorkflowStage enum"""
    
    def test_workflow_stage_values(self):
        """Test workflow stage enum values"""
        assert WorkflowStage.HUNTING.value == "hunting"
        assert WorkflowStage.ENRICHING.value == "enriching"
        assert WorkflowStage.OUTREACH.value == "outreach"
        assert WorkflowStage.CONVERSATION.value == "conversation"
        assert WorkflowStage.PROPOSAL.value == "proposal"
        assert WorkflowStage.MEETING.value == "meeting"
        assert WorkflowStage.COMPLETED.value == "completed"
        assert WorkflowStage.FAILED.value == "failed"
        assert WorkflowStage.PENDING_APPROVAL.value == "pending_approval"
    
    def test_workflow_stage_string_representation(self):
        """Test workflow stage string representations"""
        assert str(WorkflowStage.HUNTING) == "hunting"
        assert str(WorkflowStage.COMPLETED) == "completed"
    
    def test_workflow_stage_equality(self):
        """Test workflow stage equality comparisons"""
        assert WorkflowStage.HUNTING == WorkflowStage.HUNTING
        assert WorkflowStage.HUNTING != WorkflowStage.ENRICHING
        assert WorkflowStage.HUNTING.value == "hunting"


class TestComplexStateOperations:
    """Test complex state operations and edge cases"""
    
    @pytest.fixture
    def complex_state(self):
        """Create a complex state with multiple data types"""
        prospect = ProspectData(
            name="Complex Prospect",
            email="complex@example.com",
            prospect_type="company",
            source="integration_test",
            status=ProspectStatus.ENRICHED
        )
        
        state = StateManager.create_initial_state(prospect)
        
        # Add complex nested data
        state["hunter_results"] = HunterResults(
            search_queries=["complex query", "another query"],
            prospects_found=10,
            confidence_score=0.9,
            event_signals=["signal1", "signal2"],
            social_media_posts=[
                {"platform": "linkedin", "content": "Professional post"},
                {"platform": "twitter", "content": "Casual tweet"}
            ]
        )
        
        state["enrichment_data"] = EnrichmentData(
            company_data={
                "industry": "Technology",
                "size": "50-100",
                "revenue": "$10M-50M"
            },
            social_profiles={
                "linkedin": "https://linkedin.com/company/example",
                "twitter": "@examplecorp"
            },
            event_preferences={
                "preferred_venues": ["outdoor", "modern"],
                "budget_range": "high",
                "event_types": ["corporate", "team_building"]
            },
            confidence_score=0.85
        )
        
        state["outreach_campaigns"] = [
            OutreachCampaign(
                channel="email",
                campaign_type="initial_outreach",
                subject_line="Partnership Opportunity",
                message_body="Hello, we'd love to discuss...",
                status=CampaignStatus.SENT,
                sent_at=datetime.now()
            )
        ]
        
        return state
    
    def test_complex_state_serialization(self, complex_state):
        """Test serialization of complex nested state"""
        serialized = StateManager.serialize_state(complex_state)
        
        assert isinstance(serialized, str)
        
        # Should be valid JSON
        parsed = json.loads(serialized)
        
        # Verify nested structures
        assert "hunter_results" in parsed
        assert "enrichment_data" in parsed
        assert "outreach_campaigns" in parsed
        
        # Verify nested data integrity
        assert parsed["hunter_results"]["prospects_found"] == 10
        assert parsed["enrichment_data"]["confidence_score"] == 0.85
        assert len(parsed["outreach_campaigns"]) == 1
    
    def test_complex_state_deserialization(self, complex_state):
        """Test deserialization of complex nested state"""
        serialized = StateManager.serialize_state(complex_state)
        deserialized = StateManager.deserialize_state(serialized)
        
        # Verify structure is preserved
        assert deserialized["workflow_id"] == complex_state["workflow_id"]
        assert "hunter_results" in deserialized
        assert "enrichment_data" in deserialized
        assert "outreach_campaigns" in deserialized

        # Verify Pydantic models are correctly deserialized
        assert isinstance(deserialized["hunter_results"], HunterResults)
        assert isinstance(deserialized["enrichment_data"], EnrichmentData)
        assert isinstance(deserialized["outreach_campaigns"][0], OutreachCampaign)
    
    def test_state_with_errors_and_approvals(self, complex_state):
        """Test state with multiple errors and approval requests"""
        # Add multiple errors
        complex_state = StateManager.add_error(
            complex_state,
            "agent1", "error1", "First error"
        )
        complex_state = StateManager.add_error(
            complex_state,
            "agent2", "error2", "Second error"
        )
        
        # Add approval request
        complex_state = StateManager.request_approval(
            complex_state,
            "test_approval",
            {"data": "test"},
            "Test approval needed"
        )
        
        # Verify state integrity
        assert len(complex_state["errors"]) == 2
        assert len(complex_state["approval_requests"]) == 1
        assert complex_state["retry_count"] == 2
        assert complex_state["approval_pending"] is True
        
        # Test serialization/deserialization with errors
        serialized = StateManager.serialize_state(complex_state)
        deserialized = StateManager.deserialize_state(serialized)
        
        assert len(deserialized["errors"]) == 2
        assert len(deserialized["approval_requests"]) == 1
    
    def test_state_validation_with_complex_data(self, complex_state):
        """Test state validation with complex nested data"""
        # Should validate successfully
        assert StateManager.validate_state(complex_state) is True
        
        # Test with invalid nested data
        complex_state["errors"] = "not a list"  # Should be list
        
        with pytest.raises(StateValidationError, match="errors must be a list"):
            StateManager.validate_state(complex_state)
    
    def test_stage_transitions_with_complex_state(self, complex_state):
        """Test stage transitions maintain data integrity"""
        original_hunter_results = complex_state["hunter_results"]
        
        # Update stage
        updated_state = StateManager.update_stage(
            complex_state,
            WorkflowStage.OUTREACH,
            track_duration=True
        )
        
        # Verify data is preserved
        assert updated_state["hunter_results"] == original_hunter_results
        assert updated_state["current_stage"] == WorkflowStage.OUTREACH
        assert WorkflowStage.ENRICHING in updated_state["completed_stages"]  # Previous stage
        
        # Verify duration tracking
        assert "stage_durations" in updated_state
    
    def test_progress_calculation_edge_cases(self):
        """Test progress calculation edge cases"""
        prospect = ProspectData(
            name="Edge Case",
            prospect_type="individual",
            source="test",
            status=ProspectStatus.DISCOVERED
        )
        
        # Empty state
        state = StateManager.create_initial_state(prospect)
        state["completed_stages"] = []
        state["current_stage"] = WorkflowStage.HUNTING
        
        progress = StateManager.calculate_progress(state)
        assert progress > 0  # Should have some progress
        
        # Invalid stage (should handle gracefully)
        state["current_stage"] = "invalid_stage"
        progress = StateManager.calculate_progress(state)
        assert 0 <= progress <= 100
        
        # No current stage
        del state["current_stage"]
        progress = StateManager.calculate_progress(state)
        assert 0 <= progress <= 100
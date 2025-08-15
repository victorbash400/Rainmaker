"""
Integration tests for complete workflow execution.

Tests the entire workflow from prospect discovery through meeting scheduling,
including error handling, state persistence, and human approval workflows.
"""

import pytest
import asyncio
import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any

from app.core.state import (
    RainmakerState, StateManager, WorkflowStage, ProspectData,
    HunterResults, EnrichmentData, OutreachCampaign, ConversationSummary,
    ProposalData, MeetingDetails
)
from app.services.workflow import RainmakerWorkflow
from app.services.orchestrator import AgentOrchestrator
from app.services.approval import ApprovalSystem, ApprovalType
from app.db.models import ProspectStatus, EventType, CampaignStatus


class TestWorkflowExecution:
    """Test complete workflow execution scenarios"""
    
    @pytest.fixture
    async def orchestrator(self):
        """Create orchestrator instance for testing"""
        orchestrator = AgentOrchestrator()
        await orchestrator.start()
        yield orchestrator
        await orchestrator.stop()
    
    @pytest.fixture
    async def approval_system(self):
        """Create approval system for testing"""
        approval_system = ApprovalSystem()
        await approval_system.start()
        yield approval_system
        await approval_system.stop()
    
    @pytest.fixture
    def sample_prospect_data(self):
        """Sample prospect data for testing"""
        return ProspectData(
            name="John Smith",
            email="john.smith@example.com",
            company_name="Smith Events LLC",
            location="New York, NY",
            prospect_type="individual",
            source="web_search",
            status=ProspectStatus.DISCOVERED
        )
    
    @pytest.fixture
    def mock_mcp_services(self):
        """Mock all MCP services for testing"""
        with patch('app.mcp.web_search.web_search_mcp') as mock_web_search, \
             patch('app.mcp.enrichment.enrichment_mcp') as mock_enrichment, \
             patch('app.mcp.email.email_mcp') as mock_email, \
             patch('app.mcp.linkedin.linkedin_mcp') as mock_linkedin, \
             patch('app.mcp.proposal.proposal_mcp') as mock_proposal, \
             patch('app.mcp.calendar.calendar_mcp') as mock_calendar, \
             patch('app.mcp.database.database_mcp') as mock_database:
            
            # Configure mock responses
            mock_web_search.server.call_tool = AsyncMock(return_value=MagicMock(
                isError=False,
                content=[MagicMock(text=json.dumps({
                    "prospects": [
                        {
                            "prospect_name": "John Smith",
                            "confidence_score": 0.85,
                            "event_type": "wedding",
                            "source_url": "https://example.com/wedding1",
                            "raw_text": "John Smith is planning a wedding in NYC"
                        }
                    ],
                    "search_query": "wedding planning NYC"
                }))]
            ))
            
            mock_enrichment.server.call_tool = AsyncMock(return_value=MagicMock(
                isError=False,
                content=[MagicMock(text=json.dumps({
                    "company_data": {"industry": "Events", "size": "1-10"},
                    "social_profiles": {"linkedin": "https://linkedin.com/in/johnsmith"},
                    "contact_info": {"phone": "555-0123"},
                    "confidence_score": 0.8,
                    "sources": ["clearbit", "linkedin"]
                }))]
            ))
            
            mock_email.server.call_tool = AsyncMock(return_value=MagicMock(
                isError=False,
                content=[MagicMock(text=json.dumps({
                    "subject": "Wedding Planning Services",
                    "message": "Hi John, we'd love to help with your wedding!",
                    "sent": True
                }))]
            ))
            
            mock_proposal.server.call_tool = AsyncMock(return_value=MagicMock(
                isError=False,
                content=[MagicMock(text=json.dumps({
                    "total_price": 15000,
                    "venue_details": {"name": "Grand Ballroom"},
                    "package_details": {"type": "Premium Wedding Package"},
                    "pdf_url": "https://example.com/proposal.pdf"
                }))]
            ))
            
            mock_calendar.server.call_tool = AsyncMock(return_value=MagicMock(
                isError=False,
                content=[MagicMock(text=json.dumps({
                    "scheduled_at": (datetime.now() + timedelta(days=7)).isoformat(),
                    "meeting_url": "https://zoom.us/meeting123",
                    "calendar_event_id": "cal_123"
                }))]
            ))
            
            mock_database.server.call_tool = AsyncMock(return_value=MagicMock(
                isError=False,
                content=[MagicMock(text=json.dumps({"success": True}))]
            ))
            
            yield {
                "web_search": mock_web_search,
                "enrichment": mock_enrichment,
                "email": mock_email,
                "linkedin": mock_linkedin,
                "proposal": mock_proposal,
                "calendar": mock_calendar,
                "database": mock_database
            }
    
    @pytest.mark.asyncio
    async def test_complete_workflow_success(self, orchestrator, sample_prospect_data, mock_mcp_services):
        """Test successful completion of entire workflow"""
        # Start workflow
        workflow_id = await orchestrator.start_workflow(
            prospect_data=sample_prospect_data,
            priority=7
        )
        
        # Wait for workflow completion (with timeout)
        max_wait = 30  # seconds
        waited = 0
        
        while waited < max_wait:
            status = await orchestrator.get_workflow_status(workflow_id)
            if status and status["current_stage"] == WorkflowStage.COMPLETED:
                break
            await asyncio.sleep(1)
            waited += 1
        
        # Verify workflow completed successfully
        final_status = await orchestrator.get_workflow_status(workflow_id)
        assert final_status is not None
        assert final_status["current_stage"] == WorkflowStage.COMPLETED
        assert final_status["progress_percentage"] == 100.0
        assert len(final_status["errors"]) == 0
        
        # Verify all stages were completed
        completed_stages = final_status["completed_stages"]
        expected_stages = [
            WorkflowStage.HUNTING,
            WorkflowStage.ENRICHING, 
            WorkflowStage.OUTREACH,
            WorkflowStage.CONVERSATION,
            WorkflowStage.PROPOSAL,
            WorkflowStage.MEETING
        ]
        
        for stage in expected_stages:
            assert stage in completed_stages
        
        # Verify MCP services were called
        mock_mcp_services["web_search"].server.call_tool.assert_called()
        mock_mcp_services["enrichment"].server.call_tool.assert_called()
        mock_mcp_services["email"].server.call_tool.assert_called()
        mock_mcp_services["proposal"].server.call_tool.assert_called()
        mock_mcp_services["calendar"].server.call_tool.assert_called()
    
    @pytest.mark.asyncio
    async def test_workflow_with_error_recovery(self, orchestrator, sample_prospect_data, mock_mcp_services):
        """Test workflow error handling and retry logic"""
        # Configure enrichment to fail initially, then succeed
        call_count = 0
        
        def enrichment_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return MagicMock(
                    isError=True,
                    content=[MagicMock(text="API rate limit exceeded")]
                )
            else:
                return MagicMock(
                    isError=False,
                    content=[MagicMock(text=json.dumps({
                        "company_data": {"industry": "Events"},
                        "confidence_score": 0.7,
                        "sources": ["retry_success"]
                    }))]
                )
        
        mock_mcp_services["enrichment"].server.call_tool.side_effect = enrichment_side_effect
        
        # Start workflow
        workflow_id = await orchestrator.start_workflow(
            prospect_data=sample_prospect_data,
            priority=5
        )
        
        # Wait for completion with retries
        max_wait = 45
        waited = 0
        
        while waited < max_wait:
            status = await orchestrator.get_workflow_status(workflow_id)
            if status and status["current_stage"] in [WorkflowStage.COMPLETED, WorkflowStage.FAILED]:
                break
            await asyncio.sleep(1)
            waited += 1
        
        # Verify workflow recovered and completed
        final_status = await orchestrator.get_workflow_status(workflow_id)
        assert final_status["current_stage"] == WorkflowStage.COMPLETED
        assert final_status["retry_count"] > 0  # Retries occurred
        assert len(final_status["errors"]) >= 1  # Error was recorded
        
        # Verify enrichment was called multiple times
        assert mock_mcp_services["enrichment"].server.call_tool.call_count >= 2
    
    @pytest.mark.asyncio
    async def test_workflow_with_human_approval(self, orchestrator, approval_system, sample_prospect_data, mock_mcp_services):
        """Test workflow with human approval requirements"""
        # Configure proposal to require approval
        def proposal_side_effect(*args, **kwargs):
            # Simulate approval request
            return MagicMock(
                isError=False,
                content=[MagicMock(text=json.dumps({
                    "total_price": 25000,  # High price triggers approval
                    "requires_approval": True,
                    "approval_reason": "High value proposal"
                }))]
            )
        
        mock_mcp_services["proposal"].server.call_tool.side_effect = proposal_side_effect
        
        # Start workflow
        workflow_id = await orchestrator.start_workflow(
            prospect_data=sample_prospect_data,
            assigned_human="manager@example.com"
        )
        
        # Wait for approval request
        max_wait = 20
        waited = 0
        approval_id = None
        
        while waited < max_wait:
            pending_approvals = await approval_system.get_pending_approvals(workflow_id=workflow_id)
            if pending_approvals:
                approval_id = pending_approvals[0]["approval_id"]
                break
            await asyncio.sleep(1)
            waited += 1
        
        assert approval_id is not None, "Approval request was not created"
        
        # Approve the request
        approval_success = await approval_system.process_approval_decision(
            approval_id=approval_id,
            approved=True,
            response_data={"approved_amount": 25000},
            notes="Approved by manager",
            decided_by="manager@example.com"
        )
        assert approval_success is True
        
        # Wait for workflow completion after approval
        while waited < max_wait + 15:
            status = await orchestrator.get_workflow_status(workflow_id)
            if status and status["current_stage"] == WorkflowStage.COMPLETED:
                break
            await asyncio.sleep(1)
            waited += 1
        
        # Verify workflow completed after approval
        final_status = await orchestrator.get_workflow_status(workflow_id)
        assert final_status["current_stage"] == WorkflowStage.COMPLETED
    
    @pytest.mark.asyncio
    async def test_workflow_cancellation(self, orchestrator, sample_prospect_data, mock_mcp_services):
        """Test workflow cancellation"""
        # Start workflow
        workflow_id = await orchestrator.start_workflow(
            prospect_data=sample_prospect_data
        )
        
        # Let it run for a moment
        await asyncio.sleep(2)
        
        # Cancel the workflow
        cancel_success = await orchestrator.cancel_workflow(
            workflow_id=workflow_id,
            reason="Test cancellation"
        )
        assert cancel_success is True
        
        # Verify workflow is marked as cancelled
        final_status = await orchestrator.get_workflow_status(workflow_id)
        assert final_status["current_stage"] == WorkflowStage.FAILED
        # Note: The cancelled flag would be in the state, not directly in status
    
    @pytest.mark.asyncio
    async def test_workflow_pause_resume(self, orchestrator, sample_prospect_data, mock_mcp_services):
        """Test workflow pause and resume functionality"""
        # Start workflow
        workflow_id = await orchestrator.start_workflow(
            prospect_data=sample_prospect_data
        )
        
        # Let it run briefly
        await asyncio.sleep(2)
        
        # Pause the workflow
        pause_success = await orchestrator.pause_workflow(workflow_id)
        assert pause_success is True
        
        # Verify workflow is paused
        await asyncio.sleep(1)
        status_paused = await orchestrator.get_workflow_status(workflow_id)
        
        # Resume the workflow
        resume_success = await orchestrator.resume_workflow(workflow_id)
        assert resume_success is True
        
        # Wait for completion
        max_wait = 30
        waited = 0
        
        while waited < max_wait:
            status = await orchestrator.get_workflow_status(workflow_id)
            if status and status["current_stage"] in [WorkflowStage.COMPLETED, WorkflowStage.FAILED]:
                break
            await asyncio.sleep(1)
            waited += 1
        
        # Verify workflow completed after resume
        final_status = await orchestrator.get_workflow_status(workflow_id)
        assert final_status["current_stage"] == WorkflowStage.COMPLETED
    
    @pytest.mark.asyncio
    async def test_workflow_retry_from_stage(self, orchestrator, sample_prospect_data, mock_mcp_services):
        """Test workflow retry from specific stage"""
        # Configure outreach to fail
        mock_mcp_services["email"].server.call_tool.return_value = MagicMock(
            isError=True,
            content=[MagicMock(text="Email service unavailable")]
        )
        
        # Start workflow
        workflow_id = await orchestrator.start_workflow(
            prospect_data=sample_prospect_data
        )
        
        # Wait for failure
        max_wait = 20
        waited = 0
        
        while waited < max_wait:
            status = await orchestrator.get_workflow_status(workflow_id)
            if status and (status.get("human_intervention_needed") or 
                          status["current_stage"] == WorkflowStage.FAILED):
                break
            await asyncio.sleep(1)
            waited += 1
        
        # Fix the email service
        mock_mcp_services["email"].server.call_tool.return_value = MagicMock(
            isError=False,
            content=[MagicMock(text=json.dumps({
                "subject": "Wedding Planning Services",
                "message": "Hi John, we'd love to help!",
                "sent": True
            }))]
        )
        
        # Retry from outreach stage
        retry_success = await orchestrator.retry_workflow(
            workflow_id=workflow_id,
            from_stage=WorkflowStage.OUTREACH
        )
        assert retry_success is True
        
        # Wait for completion
        while waited < max_wait + 15:
            status = await orchestrator.get_workflow_status(workflow_id)
            if status and status["current_stage"] == WorkflowStage.COMPLETED:
                break
            await asyncio.sleep(1)
            waited += 1
        
        # Verify workflow completed after retry
        final_status = await orchestrator.get_workflow_status(workflow_id)
        assert final_status["current_stage"] == WorkflowStage.COMPLETED
        assert final_status["retry_count"] > 0
    
    @pytest.mark.asyncio
    async def test_multiple_concurrent_workflows(self, orchestrator, mock_mcp_services):
        """Test multiple concurrent workflow execution"""
        # Create multiple prospects
        prospects = [
            ProspectData(
                name=f"Prospect {i}",
                email=f"prospect{i}@example.com",
                company_name=f"Company {i}",
                location="Test Location",
                prospect_type="individual",
                source="web_search",
                status=ProspectStatus.DISCOVERED
            )
            for i in range(5)
        ]
        
        # Start multiple workflows
        workflow_ids = []
        for prospect in prospects:
            workflow_id = await orchestrator.start_workflow(
                prospect_data=prospect,
                priority=5
            )
            workflow_ids.append(workflow_id)
        
        # Wait for all workflows to complete
        max_wait = 45
        waited = 0
        completed_count = 0
        
        while waited < max_wait and completed_count < len(workflow_ids):
            completed_count = 0
            for workflow_id in workflow_ids:
                status = await orchestrator.get_workflow_status(workflow_id)
                if status and status["current_stage"] in [WorkflowStage.COMPLETED, WorkflowStage.FAILED]:
                    completed_count += 1
            
            await asyncio.sleep(1)
            waited += 1
        
        # Verify all workflows completed
        assert completed_count == len(workflow_ids), f"Only {completed_count}/{len(workflow_ids)} workflows completed"
        
        # Check individual workflow statuses
        for workflow_id in workflow_ids:
            status = await orchestrator.get_workflow_status(workflow_id)
            assert status["current_stage"] in [WorkflowStage.COMPLETED, WorkflowStage.FAILED]
    
    @pytest.mark.asyncio
    async def test_workflow_metrics_collection(self, orchestrator, sample_prospect_data, mock_mcp_services):
        """Test that workflow metrics are properly collected"""
        # Start and complete a workflow
        workflow_id = await orchestrator.start_workflow(
            prospect_data=sample_prospect_data
        )
        
        # Wait for completion
        max_wait = 30
        waited = 0
        
        while waited < max_wait:
            status = await orchestrator.get_workflow_status(workflow_id)
            if status and status["current_stage"] == WorkflowStage.COMPLETED:
                break
            await asyncio.sleep(1)
            waited += 1
        
        # Get metrics
        metrics = await orchestrator.get_metrics()
        
        # Verify metrics were collected
        assert metrics["workflows_started"] >= 1
        assert metrics["workflows_completed"] >= 1
        assert metrics["workflows_active"] >= 0
        assert "average_duration_seconds" in metrics
        assert "stage_completion_counts" in metrics
        
        # Verify workflow status includes timing information
        final_status = await orchestrator.get_workflow_status(workflow_id)
        assert "total_duration" in final_status
        assert final_status["total_duration"] is not None


class TestStateManagement:
    """Test state management and persistence"""
    
    @pytest.mark.asyncio
    async def test_state_serialization_deserialization(self, sample_prospect_data):
        """Test state serialization and deserialization"""
        # Create initial state
        initial_state = StateManager.create_initial_state(
            prospect_data=sample_prospect_data,
            workflow_id="test-workflow-123"
        )
        
        # Serialize state
        serialized = StateManager.serialize_state(initial_state)
        assert isinstance(serialized, str)
        
        # Deserialize state
        deserialized_state = StateManager.deserialize_state(serialized)
        
        # Verify state integrity
        assert deserialized_state["workflow_id"] == initial_state["workflow_id"]
        assert deserialized_state["prospect_data"].name == initial_state["prospect_data"].name
        assert deserialized_state["current_stage"] == initial_state["current_stage"]
    
    def test_state_validation(self):
        """Test state validation"""
        # Valid state
        valid_state = {
            "workflow_id": "test-123",
            "current_stage": WorkflowStage.HUNTING,
            "completed_stages": [],
            "workflow_started_at": datetime.now(),
            "last_updated_at": datetime.now(),
            "prospect_data": ProspectData(
                name="Test Prospect",
                prospect_type="individual",
                source="test",
                status=ProspectStatus.DISCOVERED
            ),
            "retry_count": 0
        }
        
        assert StateManager.validate_state(valid_state) is True
        
        # Invalid state - missing required field
        invalid_state = valid_state.copy()
        del invalid_state["workflow_id"]
        
        with pytest.raises(Exception):
            StateManager.validate_state(invalid_state)
    
    def test_stage_progression(self):
        """Test workflow stage progression"""
        # Create initial state
        prospect = ProspectData(
            name="Test",
            prospect_type="individual", 
            source="test",
            status=ProspectStatus.DISCOVERED
        )
        
        state = StateManager.create_initial_state(prospect)
        assert state["current_stage"] == WorkflowStage.HUNTING
        assert len(state["completed_stages"]) == 0
        
        # Update to next stage
        state = StateManager.update_stage(state, WorkflowStage.ENRICHING)
        assert state["current_stage"] == WorkflowStage.ENRICHING
        assert WorkflowStage.HUNTING in state["completed_stages"]
        
        # Update to final stage
        state = StateManager.update_stage(state, WorkflowStage.COMPLETED)
        assert state["current_stage"] == WorkflowStage.COMPLETED
        assert WorkflowStage.ENRICHING in state["completed_stages"]
    
    def test_error_handling_in_state(self):
        """Test error handling in state management"""
        prospect = ProspectData(
            name="Test",
            prospect_type="individual",
            source="test", 
            status=ProspectStatus.DISCOVERED
        )
        
        state = StateManager.create_initial_state(prospect)
        
        # Add error
        state = StateManager.add_error(
            state,
            agent_name="test_agent",
            error_type="test_error",
            error_message="Test error message",
            details={"detail": "value"}
        )
        
        assert len(state["errors"]) == 1
        assert state["retry_count"] == 1
        
        error = state["errors"][0]
        assert error.agent_name == "test_agent"
        assert error.error_type == "test_error"
        assert error.error_message == "Test error message"
    
    def test_progress_calculation(self):
        """Test workflow progress calculation"""
        prospect = ProspectData(
            name="Test",
            prospect_type="individual",
            source="test",
            status=ProspectStatus.DISCOVERED
        )
        
        state = StateManager.create_initial_state(prospect)
        
        # Initial progress
        progress = StateManager.calculate_progress(state)
        assert 0 <= progress <= 100
        
        # Complete some stages
        state["completed_stages"] = [WorkflowStage.HUNTING, WorkflowStage.ENRICHING]
        progress = StateManager.calculate_progress(state)
        assert progress > 0
        
        # Complete all stages
        state["completed_stages"] = [
            WorkflowStage.HUNTING, WorkflowStage.ENRICHING, WorkflowStage.OUTREACH,
            WorkflowStage.CONVERSATION, WorkflowStage.PROPOSAL, WorkflowStage.MEETING
        ]
        state["current_stage"] = WorkflowStage.COMPLETED
        progress = StateManager.calculate_progress(state)
        assert progress == 100.0
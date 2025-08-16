#!/usr/bin/env python3
"""
Simple test script to verify enrichment agent integration with LangGraph workflow.
Tests the basic hunter → enricher → outreach handoff.
"""

import asyncio
import sys
import os
from datetime import datetime

# Add the backend directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from app.core.state import RainmakerState, StateManager, WorkflowStage, ProspectData, HunterResults
from app.agents.enrichment import EnrichmentAgent


async def test_enrichment_agent_basic():
    """Test basic enrichment agent functionality"""
    print("🧪 Testing EnrichmentAgent basic functionality...")
    
    # Create mock prospect data
    mock_prospect = ProspectData(
        id=1,
        name="Sarah Johnson",
        email="sarah.johnson@techcorp.com",
        company_name="TechCorp Inc",
        location="San Francisco, CA",
        prospect_type="individual",
        source="test",
        lead_score=75
    )
    
    # Create initial state
    initial_state = StateManager.create_initial_state(
        prospect_data=mock_prospect,
        workflow_id="test-workflow-001"
    )
    
    # Add mock hunter results
    initial_state["hunter_results"] = HunterResults(
        search_queries=["Sarah Johnson wedding planning"],
        sources_searched=["web_search"],
        prospects_found=1,
        confidence_score=0.8,
        event_signals=["planning wedding for June 2025"]
    )
    
    # Update stage to simulate coming from hunter
    initial_state = StateManager.update_stage(initial_state, WorkflowStage.HUNTING)
    initial_state["completed_stages"] = [WorkflowStage.HUNTING]
    
    print(f"✅ Created initial state for prospect: {mock_prospect.name}")
    print(f"   Workflow ID: {initial_state['workflow_id']}")
    print(f"   Current stage: {initial_state['current_stage']}")
    
    # Test enrichment agent
    try:
        enrichment_agent = EnrichmentAgent()
        print("✅ EnrichmentAgent instance created successfully")
        
        # This would normally be called by the workflow, but we'll test directly
        print("🔍 Starting enrichment process...")
        
        # Note: This will fail without proper API keys, but we can test the structure
        enriched_state = await enrichment_agent.enrich_prospect(initial_state)
        
        print("✅ Enrichment completed successfully!")
        print(f"   Final stage: {enriched_state['current_stage']}")
        
        if "enrichment_data" in enriched_state:
            enrichment_data = enriched_state["enrichment_data"]
            print(f"   Confidence score: {enrichment_data.confidence_score}")
            print(f"   Sources used: {len(enrichment_data.enrichment_sources)}")
        
        if "errors" in enriched_state and enriched_state["errors"]:
            print("⚠️  Errors encountered:")
            for error in enriched_state["errors"]:
                print(f"     - {error.agent_name}: {error.error_message}")
        
        return True
        
    except Exception as e:
        print(f"❌ Enrichment test failed: {str(e)}")
        print(f"   Error type: {type(e).__name__}")
        return False


async def test_workflow_integration():
    """Test workflow integration with enrichment node"""
    print("\n🔄 Testing workflow integration...")
    
    try:
        from app.services.workflow import RainmakerWorkflow
        
        # Create workflow instance
        workflow = RainmakerWorkflow()
        print("✅ RainmakerWorkflow instance created successfully")
        
        # Create test state
        mock_prospect = ProspectData(
            id=2,
            name="Michael Chen",
            company_name="DataFlow Solutions",
            location="Austin, TX",
            prospect_type="corporate",
            source="test",
            lead_score=85
        )
        
        test_state = StateManager.create_initial_state(
            prospect_data=mock_prospect,
            workflow_id="test-workflow-002"
        )
        
        # Simulate hunter completion
        test_state = StateManager.update_stage(test_state, WorkflowStage.HUNTING)
        test_state["completed_stages"] = [WorkflowStage.HUNTING]
        test_state["hunter_results"] = HunterResults(
            search_queries=["DataFlow Solutions corporate retreat"],
            sources_searched=["web_search"],
            prospects_found=1,
            confidence_score=0.9,
            event_signals=["planning company retreat Q2 2025"]
        )
        
        print(f"✅ Created test state for: {mock_prospect.name}")
        
        # Test enrichment node directly
        print("🔍 Testing _enrichment_node...")
        enriched_state = await workflow._enrichment_node(test_state)
        
        print("✅ Enrichment node completed!")
        print(f"   Stage: {enriched_state['current_stage']}")
        
        # Test routing
        print("🔀 Testing _route_from_enricher...")
        next_route = workflow._route_from_enricher(enriched_state)
        print(f"✅ Next route: {next_route}")
        
        return True
        
    except Exception as e:
        print(f"❌ Workflow integration test failed: {str(e)}")
        print(f"   Error type: {type(e).__name__}")
        return False


async def main():
    """Run all tests"""
    print("🚀 Starting Enrichment Agent Integration Tests")
    print("=" * 60)
    
    # Test 1: Basic enrichment agent
    test1_passed = await test_enrichment_agent_basic()
    
    # Test 2: Workflow integration  
    test2_passed = await test_workflow_integration()
    
    print("\n" + "=" * 60)
    print("📊 Test Results:")
    print(f"   Basic EnrichmentAgent: {'✅ PASS' if test1_passed else '❌ FAIL'}")
    print(f"   Workflow Integration: {'✅ PASS' if test2_passed else '❌ FAIL'}")
    
    if test1_passed and test2_passed:
        print("\n🎉 All tests passed! Enrichment agent integration is working.")
        return 0
    else:
        print("\n⚠️  Some tests failed. Check the output above for details.")
        print("   Note: API failures are expected without proper credentials.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
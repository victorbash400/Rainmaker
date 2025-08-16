#!/usr/bin/env python3
"""
Minimal test script to verify enrichment agent without workflow dependencies.
"""

import asyncio
import sys
import os

# Add the backend directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))


async def test_enrichment_agent_only():
    """Test enrichment agent without workflow dependencies"""
    print("🧪 Testing EnrichmentAgent in isolation...")
    
    try:
        # Test basic imports
        from app.core.state import RainmakerState, StateManager, WorkflowStage, ProspectData, EnrichmentData
        print("✅ Successfully imported state management")
        
        from app.services.gemini_service import gemini_service
        print("✅ Successfully imported Gemini service")
        
        from app.mcp.web_search import web_search_mcp
        from app.mcp.database import database_mcp
        print("✅ Successfully imported MCP services")
        
        # Test enrichment agent import without orchestrator dependency
        from app.agents.enrichment import ResearchStep, ResearchPlan
        print("✅ Successfully imported enrichment classes")
        
        # Test creating research objects
        step = ResearchStep(
            step_id="test_step",
            step_type="search",
            description="Test LinkedIn search for prospect",
            reasoning="Need to understand their professional background"
        )
        print("✅ Successfully created ResearchStep")
        
        plan = ResearchPlan(
            prospect_id="test_prospect",
            steps=[step],
            estimated_duration=300,
            reasoning="Comprehensive research plan for event planning prospect"
        )
        print("✅ Successfully created ResearchPlan")
        
        # Test creating prospect data
        prospect = ProspectData(
            id=1,
            name="Test Prospect",
            email="test@example.com",
            company_name="Test Company",
            location="Test City",
            prospect_type="individual",
            source="test",
            lead_score=80
        )
        print("✅ Successfully created ProspectData")
        
        # Test creating initial state
        state = StateManager.create_initial_state(
            prospect_data=prospect,
            workflow_id="test-001"
        )
        print("✅ Successfully created initial state")
        
        # Test state management
        state = StateManager.update_stage(state, WorkflowStage.ENRICHING)
        print("✅ Successfully updated workflow stage")
        
        print(f"   Current stage: {state['current_stage']}")
        print(f"   Prospect: {state['prospect_data'].name}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        print(f"   Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return False


async def test_enrichment_agent_creation():
    """Test creating enrichment agent instance"""
    print("\n🤖 Testing EnrichmentAgent creation...")
    
    try:
        # Import without orchestrator dependency by mocking it
        import sys
        from unittest.mock import MagicMock
        
        # Mock the orchestrator module
        mock_orchestrator = MagicMock()
        sys.modules['app.services.orchestrator'] = MagicMock()
        sys.modules['app.services.orchestrator'].agent_orchestrator = mock_orchestrator
        
        # Now import the enrichment agent
        from app.agents.enrichment import EnrichmentAgent
        print("✅ Successfully imported EnrichmentAgent")
        
        # Create instance
        agent = EnrichmentAgent()
        print("✅ Successfully created EnrichmentAgent instance")
        
        # Test that it has required methods
        required_methods = [
            'enrich_prospect',
            '_create_research_plan',
            '_execute_research_step',
            '_analyze_research_data'
        ]
        
        for method in required_methods:
            if hasattr(agent, method):
                print(f"✅ Agent has {method} method")
            else:
                print(f"❌ Agent missing {method} method")
                return False
        
        # Test that it has required attributes
        if hasattr(agent, 'gemini_service'):
            print("✅ Agent has gemini_service")
        else:
            print("❌ Agent missing gemini_service")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Agent creation test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run minimal tests"""
    print("🚀 Starting Minimal Enrichment Agent Tests")
    print("=" * 60)
    
    test1_passed = await test_enrichment_agent_only()
    test2_passed = await test_enrichment_agent_creation()
    
    print("\n" + "=" * 60)
    print("📊 Test Results:")
    print(f"   Basic Components: {'✅ PASS' if test1_passed else '❌ FAIL'}")
    print(f"   Agent Creation: {'✅ PASS' if test2_passed else '❌ FAIL'}")
    
    if test1_passed and test2_passed:
        print("\n🎉 Minimal tests passed! Core enrichment agent is working.")
        return 0
    else:
        print("\n⚠️  Some tests failed. Check the output above for details.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
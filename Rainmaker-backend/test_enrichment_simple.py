#!/usr/bin/env python3
"""
Simple test script to verify enrichment agent basic structure without complex dependencies.
"""

import asyncio
import sys
import os
from datetime import datetime

# Add the backend directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))


async def test_enrichment_agent_import():
    """Test that we can import the enrichment agent"""
    print("🧪 Testing EnrichmentAgent import...")
    
    try:
        from app.agents.enrichment import EnrichmentAgent, ResearchStep, ResearchPlan
        print("✅ Successfully imported EnrichmentAgent and related classes")
        
        # Test creating an instance
        agent = EnrichmentAgent()
        print("✅ Successfully created EnrichmentAgent instance")
        
        # Test creating research step
        step = ResearchStep(
            step_id="test_step",
            step_type="search",
            description="Test search step",
            reasoning="Testing the structure"
        )
        print("✅ Successfully created ResearchStep instance")
        
        # Test creating research plan
        plan = ResearchPlan(
            prospect_id="test_prospect",
            steps=[step],
            estimated_duration=300,
            reasoning="Test plan"
        )
        print("✅ Successfully created ResearchPlan instance")
        
        return True
        
    except Exception as e:
        print(f"❌ Import test failed: {str(e)}")
        print(f"   Error type: {type(e).__name__}")
        return False


async def test_state_management():
    """Test state management imports"""
    print("\n🔧 Testing state management...")
    
    try:
        from app.core.state import WorkflowStage, StateManager
        print("✅ Successfully imported state management classes")
        
        # Test enum values
        print(f"   Available stages: {[stage.value for stage in WorkflowStage]}")
        
        return True
        
    except Exception as e:
        print(f"❌ State management test failed: {str(e)}")
        return False


async def test_gemini_service():
    """Test Gemini service import"""
    print("\n🤖 Testing Gemini service...")
    
    try:
        from app.services.gemini_service import gemini_service, GeminiServiceError
        print("✅ Successfully imported Gemini service")
        
        # Test that service has required methods
        if hasattr(gemini_service, 'generate_agent_response'):
            print("✅ Gemini service has generate_agent_response method")
        else:
            print("❌ Gemini service missing generate_agent_response method")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Gemini service test failed: {str(e)}")
        return False


async def test_mcp_imports():
    """Test MCP imports"""
    print("\n🔌 Testing MCP imports...")
    
    try:
        from app.mcp.web_search import web_search_mcp
        print("✅ Successfully imported web_search_mcp")
        
        from app.mcp.database import database_mcp
        print("✅ Successfully imported database_mcp")
        
        return True
        
    except Exception as e:
        print(f"❌ MCP import test failed: {str(e)}")
        return False


async def test_basic_structure():
    """Test the basic structure without external dependencies"""
    print("\n🏗️  Testing basic enrichment structure...")
    
    try:
        from app.agents.enrichment import EnrichmentAgent
        
        agent = EnrichmentAgent()
        
        # Check that agent has required methods
        required_methods = [
            'enrich_prospect',
            '_create_research_plan',
            '_execute_research_step',
            '_analyze_research_data',
            '_create_enrichment_data',
            '_broadcast_reasoning',
            '_broadcast_search_progress'
        ]
        
        missing_methods = []
        for method in required_methods:
            if not hasattr(agent, method):
                missing_methods.append(method)
        
        if missing_methods:
            print(f"❌ Missing methods: {missing_methods}")
            return False
        else:
            print("✅ All required methods present")
        
        # Check that agent has required attributes
        if hasattr(agent, 'gemini_service'):
            print("✅ Agent has gemini_service attribute")
        else:
            print("❌ Agent missing gemini_service attribute")
            return False
        
        if hasattr(agent, 'orchestrator'):
            print("✅ Agent has orchestrator attribute")
        else:
            print("❌ Agent missing orchestrator attribute")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Structure test failed: {str(e)}")
        return False


async def main():
    """Run all tests"""
    print("🚀 Starting Simple Enrichment Agent Tests")
    print("=" * 60)
    
    tests = [
        ("Import Test", test_enrichment_agent_import),
        ("State Management", test_state_management),
        ("Gemini Service", test_gemini_service),
        ("MCP Imports", test_mcp_imports),
        ("Basic Structure", test_basic_structure)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            results[test_name] = await test_func()
        except Exception as e:
            print(f"❌ {test_name} crashed: {str(e)}")
            results[test_name] = False
    
    print("\n" + "=" * 60)
    print("📊 Test Results:")
    
    all_passed = True
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"   {test_name}: {status}")
        if not passed:
            all_passed = False
    
    if all_passed:
        print("\n🎉 All tests passed! Basic enrichment agent structure is working.")
        return 0
    else:
        print("\n⚠️  Some tests failed. Check the output above for details.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
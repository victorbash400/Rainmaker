#!/usr/bin/env python3
"""
Simple integration test between Prospect Hunter and Enrichment Agent
"""

import asyncio
import sys
import os
from datetime import datetime

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

async def test_simple_integration():
    """Test basic integration without full MCP stack"""
    
    print("🔗 Simple Hunter → Enrichment Integration Test")
    print("=" * 50)
    
    try:
        # Import core components
        from app.core.state import StateManager, WorkflowStage, ProspectData
        from app.agents.enrichment import EnrichmentAgent
        
        print("✅ Core imports successful")
        
        # Create a mock prospect (simulating what prospect hunter would find)
        mock_prospect = ProspectData(
            name="Test Prospect",
            email="test@example.com",
            company_name="Test Company",
            location="San Francisco, CA",
            prospect_type="individual",
            source="integration_test"
        )
        
        print(f"👤 Created mock prospect: {mock_prospect.name}")
        
        # Create initial state (simulating what prospect hunter would create)
        initial_state = StateManager.create_initial_state(mock_prospect)
        
        # Add mock hunter results (simulating successful prospect hunting)
        from app.core.state import HunterResults
        hunter_results = HunterResults(
            search_queries=["test query"],
            sources_searched=["test_source"],
            prospects_found=1,
            confidence_score=0.8,
            event_signals=["planning a wedding"]
        )
        
        initial_state["hunter_results"] = hunter_results
        initial_state["current_stage"] = WorkflowStage.ENRICHING
        
        print("📊 Created mock hunter results")
        print(f"   • Prospects found: {hunter_results.prospects_found}")
        print(f"   • Confidence: {hunter_results.confidence_score}")
        
        # Initialize enrichment agent
        enrichment_agent = EnrichmentAgent()
        print("🧠 Enrichment agent initialized")
        
        print("\n🚀 Testing enrichment with hunter data...")
        
        # Test that enrichment agent can receive and process the state
        enriched_state = await enrichment_agent.enrich_prospect(initial_state)
        
        print("\n" + "=" * 50)
        
        # Check results
        if enriched_state.get("enrichment_data"):
            print("🎉 INTEGRATION TEST SUCCESSFUL!")
            print("=" * 50)
            
            enrichment_data = enriched_state["enrichment_data"]
            
            print(f"\n📊 Enrichment Results:")
            print(f"   • Data Sources: {len(enrichment_data.data_sources)}")
            print(f"   • Citations: {len(enrichment_data.citations)}")
            print(f"   • Personal Info Fields: {len(enrichment_data.personal_info)}")
            print(f"   • Company Info Fields: {len(enrichment_data.company_info)}")
            print(f"   • Event Context Fields: {len(enrichment_data.event_context)}")
            print(f"   • AI Insights Fields: {len(enrichment_data.ai_insights)}")
            
            print(f"\n🔗 Data Flow Verification:")
            print(f"   • Hunter Results Present: {'✅' if enriched_state.get('hunter_results') else '❌'}")
            print(f"   • Prospect Data Present: {'✅' if enriched_state.get('prospect_data') else '❌'}")
            print(f"   • Enrichment Data Created: {'✅' if enriched_state.get('enrichment_data') else '❌'}")
            
            # Verify that enrichment agent received hunter data
            if enriched_state.get("hunter_results"):
                hunter_data = enriched_state["hunter_results"]
                print(f"   • Hunter Confidence Passed: {hunter_data.confidence_score}")
                print(f"   • Event Signals Passed: {len(hunter_data.event_signals)} signals")
            
            print(f"\n✅ SUCCESS: Enrichment agent successfully received and processed prospect hunter data!")
            return True
        else:
            print("❌ INTEGRATION TEST FAILED!")
            print("=" * 50)
            print("Enrichment agent did not produce enrichment data")
            
            if enriched_state.get("errors"):
                print("\nErrors:")
                for error in enriched_state["errors"]:
                    print(f"   • {error.agent_name}: {error.error_message}")
            
            return False
        
    except Exception as e:
        print(f"\n❌ Integration test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_simple_integration())
    if not success:
        sys.exit(1)
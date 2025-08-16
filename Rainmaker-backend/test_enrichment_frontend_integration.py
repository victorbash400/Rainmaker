#!/usr/bin/env python3
"""
Test enrichment agent frontend integration
"""

import asyncio
import sys
import os

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

async def test_enrichment_frontend_integration():
    """Test that enrichment agent can send updates to frontend"""
    
    print("🔗 Testing Enrichment → Frontend Integration")
    print("=" * 50)
    
    try:
        # Set up the enrichment viewer callback
        from app.api.v1.enrichment_viewer import setup_enrichment_viewer
        from app.agents.enrichment import set_enrichment_viewer_callback, EnrichmentAgent
        from app.api.v1.enrichment_viewer import enrichment_viewer_callback
        from app.core.state import StateManager, ProspectData
        
        print("🔧 Setting up enrichment viewer callback...")
        setup_enrichment_viewer()
        set_enrichment_viewer_callback(enrichment_viewer_callback)
        print("✅ Enrichment viewer callback configured")
        
        # Create a test prospect
        prospect = ProspectData(
            name="Frontend Test Prospect",
            email="test@frontend.com",
            company_name="Frontend Test Co",
            location="San Francisco, CA",
            prospect_type="individual",
            source="frontend_test"
        )
        
        # Create initial state
        state = StateManager.create_initial_state(prospect)
        print(f"✅ Test state created: {state['workflow_id'][:8]}...")
        
        # Create enrichment agent
        agent = EnrichmentAgent()
        print("✅ Enrichment agent initialized")
        
        print("\n🚀 Testing enrichment with frontend updates...")
        print("   - Should send real-time updates via callback")
        print("   - Updates will be logged to console")
        print()
        
        # Mock the callback to capture updates
        captured_updates = []
        
        def mock_callback(update_data):
            captured_updates.append(update_data)
            print(f"📡 Frontend Update: {update_data['step']} - {update_data['reasoning']}")
        
        # Set the mock callback
        set_enrichment_viewer_callback(mock_callback)
        
        # Run enrichment
        enriched_state = await agent.enrich_prospect(state)
        
        print("\n" + "=" * 50)
        
        if enriched_state.get("enrichment_data") and len(captured_updates) > 0:
            print("🎉 FRONTEND INTEGRATION SUCCESSFUL!")
            print("=" * 50)
            
            print(f"\n📡 Frontend Updates Captured: {len(captured_updates)}")
            for i, update in enumerate(captured_updates, 1):
                print(f"   {i}. {update['step']}: {update['reasoning'][:60]}...")
            
            print(f"\n📊 Enrichment Results:")
            enrichment_data = enriched_state["enrichment_data"]
            print(f"   • Data Sources: {len(enrichment_data.data_sources)}")
            print(f"   • Citations: {len(enrichment_data.citations)}")
            
            print(f"\n✅ SUCCESS: Enrichment agent successfully sends real-time updates to frontend!")
            print(f"   → {len(captured_updates)} updates were captured")
            print(f"   → Updates include AI reasoning and progress steps")
            
            return True
        else:
            print("❌ FRONTEND INTEGRATION FAILED!")
            print("=" * 50)
            if not enriched_state.get("enrichment_data"):
                print("• No enrichment data produced")
            if len(captured_updates) == 0:
                print("• No frontend updates captured")
            return False
        
    except Exception as e:
        print(f"\n❌ Frontend integration test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_enrichment_frontend_integration())
    if not success:
        sys.exit(1)
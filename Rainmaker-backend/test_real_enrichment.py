#!/usr/bin/env python3
"""
Real enrichment test - makes actual Perplexity Sonar + Gemini API calls
"""

import asyncio
import sys
import os

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

async def test_real_enrichment():
    """Test real enrichment with actual API calls"""
    
    print("🚀 REAL Enrichment Test - Reid Hoffman")
    print("=" * 50)
    
    try:
        from app.agents.enrichment import EnrichmentAgent
        from app.core.state import StateManager
        from app.test_data.mock_prospects import get_mock_prospect_by_name
        
        # Get real prospect
        prospect = get_mock_prospect_by_name('Reid Hoffman')
        print(f"🎯 Target: {prospect.name}")
        print(f"   Company: {prospect.company_name}")
        print(f"   Location: {prospect.location}")
        
        # Create workflow state
        state = StateManager.create_initial_state(prospect)
        print(f"✅ Workflow created: {state['workflow_id'][:8]}...")
        
        # Initialize agent
        agent = EnrichmentAgent()
        print("✅ Agent initialized")
        
        print("\n🔍 Starting REAL enrichment with live APIs...")
        print("   - Will call Perplexity Sonar API")
        print("   - Will use Gemini for analysis")
        print("   - Will show real-time reasoning")
        print()
        
        # Do the actual enrichment
        enriched_state = await agent.enrich_prospect(state)
        
        print("\n" + "=" * 50)
        
        # Check if enrichment was successful
        if 'enrichment_data' in enriched_state and enriched_state['enrichment_data']:
            enrichment_data = enriched_state['enrichment_data']
            
            print("🎉 ENRICHMENT COMPLETED!")
            print("=" * 50)
            
            print(f"\n📊 Data Sources Used: {len(enrichment_data.data_sources)}")
            for source in enrichment_data.data_sources:
                print(f"   ✅ {source}")
            
            print(f"\n👤 Personal Info:")
            for key, value in enrichment_data.personal_info.items():
                print(f"   • {key}: {value}")
            
            print(f"\n🏢 Company Info:")
            for key, value in enrichment_data.company_info.items():
                print(f"   • {key}: {value}")
            
            print(f"\n🎉 Event Context:")
            for key, value in enrichment_data.event_context.items():
                print(f"   • {key}: {value}")
            
            print(f"\n🧠 AI Insights:")
            for key, value in enrichment_data.ai_insights.items():
                print(f"   • {key}: {value}")
            
            print(f"\n📚 Citations ({len(enrichment_data.citations)} sources):")
            for i, citation in enumerate(enrichment_data.citations[:5], 1):  # Show first 5
                print(f"   {i}. {citation.get('title', 'No title')}")
                print(f"      URL: {citation.get('url', 'No URL')}")
                print(f"      Source: {citation.get('source_type', 'Unknown')}")
                if citation.get('date'):
                    print(f"      Date: {citation.get('date')}")
                print()
            
            if len(enrichment_data.citations) > 5:
                print(f"   ... and {len(enrichment_data.citations) - 5} more citations")
            
            print(f"\n⏰ Enriched at: {enrichment_data.last_enriched}")
            
            print("\n✅ SUCCESS: Real enrichment completed with live API data and citations!")
        else:
            print("❌ ENRICHMENT FAILED!")
            print("=" * 50)
            print("Enrichment did not produce data. Check error logs above.")
            if 'errors' in enriched_state:
                print("\nErrors:")
                for error in enriched_state['errors']:
                    print(f"   • {error.agent_name}: {error.error_message}")
            return False
        
        return True
        
    except Exception as e:
        print(f"\n❌ Enrichment failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_real_enrichment())
    if not success:
        sys.exit(1)
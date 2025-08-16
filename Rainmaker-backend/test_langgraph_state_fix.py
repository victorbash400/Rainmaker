#!/usr/bin/env python3
"""
Test script to verify the LangGraph state fix with actual problematic data
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.state import StateManager, RainmakerState, ProspectData, WorkflowStage
from app.core.persistence import StatePersistence
from datetime import datetime
import json

def test_langgraph_state_fix():
    """Test that the state cleaning fixes LangGraph compatibility issues"""
    
    print("🧪 Testing LangGraph state compatibility fix...")
    
    # Create a state similar to what campaign coordinator creates
    base_state = StateManager.create_initial_state(
        prospect_data=ProspectData(
            name="Steve Wittgoff",
            email="steve@wittgoff.com",
            company_name="Wittgoff Real Estate",
            prospect_type="individual",
            source="demo"
        )
    )
    
    # Add custom fields that would cause LangGraph to fail
    problematic_state = base_state.copy()
    problematic_state["campaign_plan"] = {
        "plan_id": "test_plan",
        "campaign_name": "Test Campaign",
        "objectives": {"target_prospects": 50}
    }
    problematic_state["target_prospects"] = 50
    problematic_state["event_types_focus"] = ["wedding", "corporate"]
    problematic_state["geographic_focus"] = ["Chicago", "IL"]
    problematic_state["custom_data"] = {"some": "data"}
    
    print("✅ Created problematic state with custom fields")
    print(f"   Original state has {len(problematic_state)} fields")
    
    # Test state cleaning
    try:
        clean_state = StateManager.clean_state_for_persistence(problematic_state)
        print("✅ State cleaning successful")
        print(f"   Clean state has {len(clean_state)} fields")
        
        # Verify custom fields were removed
        custom_fields = [key for key in clean_state.keys() if key not in [
            'workflow_id', 'current_stage', 'completed_stages', 'workflow_started_at',
            'last_updated_at', 'prospect_id', 'prospect_data', 'hunter_results',
            'enrichment_data', 'outreach_campaigns', 'conversation_summary',
            'proposal_data', 'meeting_details', 'errors', 'retry_count',
            'max_retries', 'human_intervention_needed', 'approval_pending',
            'assigned_human', 'approval_requests', 'manual_overrides',
            'next_agent', 'skip_stages', 'priority', 'stage_durations',
            'total_duration', 'api_calls_made', 'rate_limit_status'
        ]]
        
        if custom_fields:
            print(f"❌ Custom fields still present: {custom_fields}")
            return False
        else:
            print("✅ All custom fields removed successfully")
        
    except Exception as e:
        print(f"❌ State cleaning failed: {e}")
        return False
    
    # Test serialization of clean state
    try:
        serialized = StateManager.serialize_state(clean_state)
        print("✅ Serialization of clean state successful")
    except Exception as e:
        print(f"❌ Serialization failed: {e}")
        return False
    
    # Test deserialization
    try:
        deserialized = StateManager.deserialize_state(serialized)
        print("✅ Deserialization successful")
    except Exception as e:
        print(f"❌ Deserialization failed: {e}")
        return False
    
    # Test persistence layer
    try:
        persistence = StatePersistence()
        workflow_id = problematic_state["workflow_id"]
        
        # This should now work without errors
        save_result = await persistence.save_state(workflow_id, problematic_state)
        if save_result:
            print("✅ Persistence save successful")
        else:
            print("❌ Persistence save failed")
            return False
        
        # Test loading
        loaded_state = await persistence.load_state(workflow_id)
        if loaded_state:
            print("✅ Persistence load successful")
            print(f"   Loaded state has {len(loaded_state)} fields")
        else:
            print("❌ Persistence load failed")
            return False
        
    except Exception as e:
        print(f"❌ Persistence test failed: {e}")
        return False
    
    # Test state validation
    try:
        StateManager.validate_state(clean_state)
        print("✅ State validation successful")
    except Exception as e:
        print(f"❌ State validation failed: {e}")
        return False
    
    print("🎉 All tests passed! LangGraph state compatibility fix is working.")
    return True

async def run_async_test():
    """Run the async test"""
    return test_langgraph_state_fix()

if __name__ == "__main__":
    import asyncio
    success = asyncio.run(run_async_test())
    sys.exit(0 if success else 1)
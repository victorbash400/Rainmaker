#!/usr/bin/env python3
"""
Simple test for state cleaning without database dependencies
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.state import StateManager, RainmakerState, ProspectData, WorkflowStage
from datetime import datetime

def test_state_cleaning():
    """Test state cleaning functionality"""
    
    print("🧪 Testing state cleaning functionality...")
    
    # Create base state
    base_state = StateManager.create_initial_state(
        prospect_data=ProspectData(
            name="Test Prospect",
            prospect_type="individual",
            source="test"
        )
    )
    
    # Add problematic custom fields (like campaign coordinator does)
    problematic_state = base_state.copy()
    problematic_state["campaign_plan"] = {"plan_id": "test"}
    problematic_state["target_prospects"] = 50
    problematic_state["event_types_focus"] = ["wedding"]
    problematic_state["geographic_focus"] = ["Chicago"]
    problematic_state["some_other_custom_field"] = "value"
    
    print(f"✅ Created state with {len(problematic_state)} fields")
    print(f"   Custom fields: {[k for k in problematic_state.keys() if k not in base_state.keys()]}")
    
    # Test cleaning
    try:
        clean_state = StateManager.clean_state_for_persistence(problematic_state)
        print(f"✅ Cleaned state has {len(clean_state)} fields")
        
        # Verify only valid fields remain
        valid_fields = {
            'workflow_id', 'current_stage', 'completed_stages', 'workflow_started_at',
            'last_updated_at', 'prospect_id', 'prospect_data', 'hunter_results',
            'enrichment_data', 'outreach_campaigns', 'conversation_summary',
            'proposal_data', 'meeting_details', 'errors', 'retry_count',
            'max_retries', 'human_intervention_needed', 'approval_pending',
            'assigned_human', 'approval_requests', 'manual_overrides',
            'next_agent', 'skip_stages', 'priority', 'stage_durations',
            'total_duration', 'api_calls_made', 'rate_limit_status'
        }
        
        invalid_fields = [k for k in clean_state.keys() if k not in valid_fields]
        if invalid_fields:
            print(f"❌ Invalid fields still present: {invalid_fields}")
            return False
        else:
            print("✅ All invalid fields removed")
        
        # Test serialization
        serialized = StateManager.serialize_state(clean_state)
        print("✅ Serialization successful")
        
        # Test deserialization
        deserialized = StateManager.deserialize_state(serialized)
        print("✅ Deserialization successful")
        
        # Test validation
        StateManager.validate_state(deserialized)
        print("✅ Validation successful")
        
        print("🎉 State cleaning test passed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_state_cleaning()
    sys.exit(0 if success else 1)
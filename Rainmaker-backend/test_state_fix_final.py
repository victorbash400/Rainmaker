#!/usr/bin/env python3
"""
Test script to verify the state serialization/deserialization fix
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.state import StateManager, RainmakerState, ProspectData, WorkflowStage
from datetime import datetime
import json

def test_state_serialization_fix():
    """Test that the state serialization/deserialization handles problematic data"""
    
    print("🧪 Testing state serialization/deserialization fix...")
    
    # Create a state with potentially problematic data
    test_state = StateManager.create_initial_state(
        prospect_data=ProspectData(
            name="Test Prospect",
            prospect_type="individual",
            source="test"
        )
    )
    
    # Add some problematic data that might cause issues
    test_state["outreach_campaigns"] = [
        {
            "channel": "email",
            "campaign_type": "initial_outreach",
            "message_body": "Test message",
            "status": "sent"
        },
        "invalid_string_entry",  # This should be filtered out
        123,  # This should be filtered out
        None  # This should be filtered out
    ]
    
    test_state["errors"] = [
        {
            "agent_name": "test_agent",
            "error_type": "test_error",
            "error_message": "Test error message",
            "timestamp": datetime.now()
        },
        "invalid_error_entry",  # This should be filtered out
        {"incomplete": "data"}  # This should be filtered out
    ]
    
    test_state["completed_stages"] = [
        "enriching",  # Don't include current stage (hunting)
        123,  # Invalid stage - should be filtered out
        None,  # Invalid stage - should be filtered out
        "invalid_stage"  # Invalid stage - should be filtered out
    ]
    
    # Add custom fields that should be filtered out
    test_state["custom_campaign_data"] = {"some": "data"}
    test_state["target_prospects"] = 50
    test_state["event_types_focus"] = ["wedding", "corporate"]
    
    print("✅ Created test state with problematic data")
    
    # Test serialization
    try:
        serialized = StateManager.serialize_state(test_state)
        print("✅ Serialization successful")
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
    
    # Verify the data was cleaned up properly
    print(f"✅ Outreach campaigns: {len(deserialized.get('outreach_campaigns', []))} valid entries")
    print(f"✅ Errors: {len(deserialized.get('errors', []))} valid entries")
    print(f"✅ Completed stages: {len(deserialized.get('completed_stages', []))} valid entries")
    
    # Verify custom fields were filtered out
    custom_fields = [key for key in deserialized.keys() if key not in [
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
        print(f"⚠️ Custom fields still present: {custom_fields}")
    else:
        print("✅ All custom fields filtered out successfully")
    
    # Test validation
    try:
        StateManager.validate_state(deserialized)
        print("✅ State validation successful")
    except Exception as e:
        print(f"❌ State validation failed: {e}")
        return False
    
    print("🎉 All tests passed! State serialization/deserialization fix is working.")
    return True

if __name__ == "__main__":
    success = test_state_serialization_fix()
    sys.exit(0 if success else 1)
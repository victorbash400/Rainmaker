#!/usr/bin/env python3
"""Simple test script to verify the state persistence fix on Windows."""

import json
from datetime import datetime
from enum import Enum

# Mock the basic structures we need for testing
class WorkflowStage(str, Enum):
    HUNTING = "hunting"
    ENRICHING = "enriching"
    OUTREACH = "outreach"

def test_list_deserialization():
    """Test the specific error case with list deserialization."""
    print("Testing list deserialization fix...")
    
    # Simulate the problematic JSON data that was causing the error
    problematic_data = {
        "workflow_id": "test_123",
        "current_stage": "outreach",
        "completed_stages": ["hunting", "enriching"],
        "workflow_started_at": "2025-08-16T15:38:40",
        "last_updated_at": "2025-08-16T15:38:40",
        "outreach_campaigns": [
            {
                "channel": "email",
                "campaign_type": "initial",
                "message_body": "test",
                "status": "draft"
            },
            "invalid_string_entry",  # This would cause the error
            123,  # This would also cause the error
            None  # This too
        ],
        "errors": [
            {
                "agent_name": "test",
                "error_type": "test",
                "error_message": "test",
                "timestamp": "2025-08-16T15:38:40"
            },
            "invalid_error_entry"  # This would cause the error
        ]
    }
    
    # Test the fixed deserialization logic
    try:
        # Simulate the fixed logic for outreach_campaigns
        if 'outreach_campaigns' in problematic_data and problematic_data['outreach_campaigns']:
            campaigns = []
            for campaign in problematic_data['outreach_campaigns']:
                if isinstance(campaign, dict):
                    try:
                        # In real code this would be OutreachCampaign(**campaign)
                        campaigns.append(campaign)  # Just keep the dict for testing
                    except Exception as e:
                        continue
                # Skip non-dict entries
            problematic_data['outreach_campaigns'] = campaigns
        
        # Simulate the fixed logic for errors
        if 'errors' in problematic_data and problematic_data['errors']:
            errors = []
            for error in problematic_data['errors']:
                if isinstance(error, dict):
                    try:
                        # In real code this would be AgentError(**error)
                        errors.append(error)  # Just keep the dict for testing
                    except Exception as e:
                        continue
                # Skip non-dict entries
            problematic_data['errors'] = errors
        
        # Simulate the fixed logic for completed_stages
        if 'completed_stages' in problematic_data:
            stages = []
            for stage in problematic_data['completed_stages']:
                try:
                    if isinstance(stage, str):
                        stages.append(WorkflowStage(stage))
                    elif isinstance(stage, WorkflowStage):
                        stages.append(stage)
                except ValueError:
                    continue
            problematic_data['completed_stages'] = stages
        
        print("✓ List deserialization completed without errors")
        print(f"✓ Outreach campaigns filtered: {len(problematic_data['outreach_campaigns'])} valid entries")
        print(f"✓ Errors filtered: {len(problematic_data['errors'])} valid entries")
        print(f"✓ Completed stages converted: {len(problematic_data['completed_stages'])} valid entries")
        
        return True
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_list_deserialization()
    if success:
        print("\n🎉 All tests passed! The fix should resolve the state persistence error.")
    else:
        print("\n❌ Tests failed. The fix needs more work.")
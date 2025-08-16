#!/usr/bin/env python3
"""Test script to verify the state persistence fix."""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.state import StateManager, ProspectData, WorkflowStage
from app.db.models import ProspectStatus

def test_state_serialization():
    """Test that state serialization/deserialization works without errors."""
    print("Testing state serialization/deserialization...")
    
    # Create test prospect data
    prospect_data = ProspectData(
        name="Steve Wittgoff",
        email="test@example.com",
        company_name="Wittgoff Real Estate",
        prospect_type="individual",
        source="test",
        status=ProspectStatus.DISCOVERED
    )
    
    # Create initial state
    state = StateManager.create_initial_state(
        prospect_data=prospect_data,
        workflow_id="test_workflow_123"
    )
    
    # Add some test data to outreach campaigns to simulate the error
    from app.core.state import OutreachCampaign
    from app.db.models import CampaignStatus
    
    campaign = OutreachCampaign(
        channel="email",
        campaign_type="initial_outreach",
        message_body="Test message",
        status=CampaignStatus.DRAFT
    )
    
    state['outreach_campaigns'] = [campaign]
    state['current_stage'] = WorkflowStage.OUTREACH
    
    try:
        # Test serialization
        serialized = StateManager.serialize_state(state)
        print("✓ Serialization successful")
        
        # Test deserialization
        deserialized = StateManager.deserialize_state(serialized)
        print("✓ Deserialization successful")
        
        # Verify data integrity
        assert deserialized['workflow_id'] == state['workflow_id']
        assert deserialized['current_stage'] == state['current_stage']
        assert len(deserialized['outreach_campaigns']) == 1
        
        print("✓ Data integrity verified")
        print("All tests passed! State persistence fix is working.")
        return True
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_state_serialization()
    sys.exit(0 if success else 1)
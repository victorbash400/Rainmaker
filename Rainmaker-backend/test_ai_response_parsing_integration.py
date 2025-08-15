"""
Integration test for AI response parsing with actual Gemini service
"""

import asyncio
import json
from app.mcp.simple_gemini_interface import SimpleGeminiInterface


async def test_real_ai_response_parsing():
    """Test AI response parsing with a real (but simple) scenario"""
    interface = SimpleGeminiInterface()
    
    # Mock page elements that would come from DOM extractor
    page_elements = {
        "page_info": {"title": "Google Search"},
        "interactive_elements": [
            {
                "selector": "input[name='q']",
                "text_content": "",
                "tag_name": "input",
                "attributes": {"name": "q", "placeholder": "Search"}
            },
            {
                "selector": "input[value='Google Search']",
                "text_content": "Google Search",
                "tag_name": "input",
                "attributes": {"type": "submit", "value": "Google Search"}
            }
        ],
        "form_elements": [
            {
                "selector": "input[name='q']",
                "tag_name": "input",
                "attributes": {"name": "q", "type": "text", "placeholder": "Search"},
                "labels": ["Search"]
            }
        ],
        "content_elements": [
            {
                "text_content": "Google",
                "tag_name": "h1",
                "content_type": "heading"
            }
        ],
        "navigation_elements": []
    }
    
    task_goal = "search for wedding planners in Switzerland"
    current_url = "https://www.google.com"
    
    try:
        # Get AI response
        result = await interface.get_next_action(page_elements, task_goal, current_url)
        
        print(f"AI Response: {json.dumps(result, indent=2)}")
        
        # Validate the response structure
        assert "action" in result
        assert "reasoning" in result
        assert "confidence" in result
        assert "success" in result
        
        # The AI should suggest typing in the search box
        if result["success"]:
            assert result["action"] in ["type", "click", "extract", "wait", "navigate", "complete"]
            
            if result["action"] == "type":
                assert "selector" in result
                assert "text" in result
                assert "search" in result["text"].lower() or "wedding" in result["text"].lower()
            
            print("✓ AI response parsing integration test passed")
            return True
        else:
            print(f"AI response failed: {result.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"Integration test failed: {str(e)}")
        return False


def test_response_validation_comprehensive():
    """Test comprehensive response validation"""
    interface = SimpleGeminiInterface()
    
    # Test various response formats
    test_cases = [
        # Valid JSON response
        {
            "response": '{"action": "type", "selector": "input[name=\'q\']", "text": "wedding planners", "reasoning": "Entering search query", "confidence": 0.9}',
            "expected_action": "type",
            "should_succeed": True
        },
        # JSON with markdown
        {
            "response": '```json\n{"action": "click", "selector": "#search-btn", "reasoning": "Clicking search", "confidence": 0.8}\n```',
            "expected_action": "click", 
            "should_succeed": True
        },
        # Text response
        {
            "response": "I should click on the search button to submit the query",
            "expected_action": "click",
            "should_succeed": True
        },
        # Invalid action type
        {
            "response": '{"action": "invalid", "selector": "#btn", "reasoning": "Invalid action", "confidence": 0.5}',
            "expected_action": "error",
            "should_succeed": False
        },
        # Missing required parameters
        {
            "response": '{"action": "type", "text": "search query", "reasoning": "Missing selector", "confidence": 0.7}',
            "expected_action": "error",
            "should_succeed": False
        }
    ]
    
    all_passed = True
    
    for i, test_case in enumerate(test_cases):
        print(f"\nTesting case {i+1}: {test_case['response'][:50]}...")
        
        result = interface._parse_action_response(test_case["response"])
        
        if result["action"] != test_case["expected_action"]:
            print(f"❌ Expected action '{test_case['expected_action']}', got '{result['action']}'")
            all_passed = False
        elif result["success"] != test_case["should_succeed"]:
            print(f"❌ Expected success={test_case['should_succeed']}, got success={result['success']}")
            all_passed = False
        else:
            print(f"✓ Case {i+1} passed")
    
    return all_passed


async def main():
    """Run all integration tests"""
    print("Running AI response parsing integration tests...\n")
    
    # Test comprehensive validation
    validation_passed = test_response_validation_comprehensive()
    
    if validation_passed:
        print("\n✓ All validation tests passed")
    else:
        print("\n❌ Some validation tests failed")
    
    # Test with real AI (if available)
    print("\nTesting with real AI service...")
    ai_test_passed = await test_real_ai_response_parsing()
    
    if validation_passed and ai_test_passed:
        print("\n🎉 All integration tests passed!")
        return True
    else:
        print("\n❌ Some integration tests failed")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
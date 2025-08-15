#!/usr/bin/env python3
"""
Test script for login pause functionality
This script tests the AI navigation login detection and pause mechanism
"""

import asyncio
import sys
import os

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from Rainmaker_backend.app.mcp.navigate_extract_tool import NavigateExtractTool
from Rainmaker_backend.app.mcp.browser_manager import BrowserManager


def browser_viewer_callback(data):
    """Mock callback for browser viewer updates"""
    print(f"📸 Browser Update: {data.get('step', 'Unknown')} - {data.get('details', '')}")
    if data.get('reasoning'):
        print(f"🤖 AI Reasoning: {data['reasoning']}")


async def test_login_pause():
    """Test the login pause functionality"""
    print("🚀 Testing Login Pause Functionality")
    print("=" * 50)
    
    # Create browser manager with mock callback
    browser_manager = BrowserManager(browser_viewer_callback=browser_viewer_callback)
    browser_manager.workflow_id = "test_login_pause"
    
    # Create navigation tool
    nav_tool = NavigateExtractTool(browser_manager)
    
    # Test with LinkedIn (should trigger login pause)
    print("🔍 Testing LinkedIn navigation (should pause for login)...")
    
    result = await nav_tool.navigate_and_extract({
        "url": "https://www.linkedin.com/search/results/companies/?keywords=event%20planning",
        "extraction_goal": "find event planning companies",
        "headless": False  # Keep visible for manual login
    })
    
    print("\n📊 Test Results:")
    print("-" * 30)
    
    if result.isError:
        print("❌ Test failed with error")
        if result.content:
            print(f"Error: {result.content[0].text}")
    else:
        print("✅ Test completed successfully")
        if result.content:
            import json
            try:
                result_data = json.loads(result.content[0].text)
                print(f"Success: {result_data.get('success', False)}")
                print(f"Steps taken: {result_data.get('steps_taken', 0)}")
                print(f"URL: {result_data.get('url', 'Unknown')}")
                
                # Check if login pause was triggered
                steps = result_data.get('navigation_steps', [])
                login_steps = [step for step in steps if 'login' in str(step).lower()]
                
                if login_steps:
                    print(f"🔐 Login pause steps detected: {len(login_steps)}")
                    for step in login_steps[:3]:  # Show first 3 login-related steps
                        print(f"  - {step}")
                else:
                    print("⚠️ No login pause steps detected")
                    
            except json.JSONDecodeError:
                print("Could not parse result JSON")
    
    # Cleanup
    browser_manager.close()
    print("\n🏁 Test completed")


if __name__ == "__main__":
    print("Starting LinkedIn login pause test...")
    print("This will open a browser window and navigate to LinkedIn.")
    print("When login is required, the AI should pause and wait for manual login.")
    print("Complete the login manually, then observe if AI resumes navigation.")
    print("\nPress Ctrl+C to cancel or Enter to continue...")
    
    try:
        input()
        asyncio.run(test_login_pause())
    except KeyboardInterrupt:
        print("\n❌ Test cancelled by user")
    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")
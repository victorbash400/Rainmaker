"""
Test script for the enhanced AI navigation tool
"""
import asyncio
import json
from app.mcp.enhanced_playwright_mcp import enhanced_browser_mcp

async def test_event_planners():
    """Test AI navigation for event planning professionals"""
    print("🤖 Testing AI Navigation: Event Planning Professionals")
    print("=" * 60)
    
    try:
        result = await enhanced_browser_mcp.call_tool('navigate_and_extract', {
            'url': 'https://www.google.com',
            'extraction_goal': 'find people who plan events and gatherings, extract their profiles and contact information from social media or professional networks',
            'headless': False
        })
        
        print(f"✅ Success: {not result.isError}")
        
        if result.isError:
            print(f"❌ Error: {result.content[0].text[:500]}")
            return
        
        # Parse results
        data = json.loads(result.content[0].text)
        
        print(f"🎯 Steps taken: {data.get('steps_taken', 0)}")
        print(f"📊 Extracted items: {len(data.get('extracted_data', []))}")
        print(f"🌐 Sites visited: {len(set(step.get('url', '') for step in data.get('navigation_steps', [])))}")
        
        # Show navigation progression
        print("\n📋 Navigation Steps:")
        for i, step in enumerate(data.get('navigation_steps', [])[:10]):  # Show first 10 steps
            ai_action = step.get('ai_action', {})
            action = ai_action.get('action', 'unknown')
            reasoning = ai_action.get('reasoning', 'No reasoning')[:100] + "..."
            url = step.get('url', '')
            
            # Show domain only for cleaner output
            if url:
                from urllib.parse import urlparse
                domain = urlparse(url).netloc or url[:30]
            else:
                domain = "unknown"
            
            print(f"  {i+1}. {action.upper()} on {domain}")
            print(f"     💭 {reasoning}")
            
            if step.get('execution_result', {}).get('success'):
                attempt = step.get('execution_result', {}).get('attempt', 1)
                success_note = f"Success (attempt {attempt})" if attempt > 1 else "Success"
                print(f"     ✅ {success_note}")
            elif 'execution_result' in step:
                error = step['execution_result'].get('error', 'Unknown error')
                print(f"     ❌ Failed: {error[:80]}...")
            print()
        
        # Show extracted data
        print("📇 Extracted Data:")
        if not data.get('extracted_data'):
            print("  No data extracted yet")
        else:
            for i, item in enumerate(data.get('extracted_data', [])[:5]):  # Show first 5 items
                print(f"  📋 Dataset {i+1}:")
                if isinstance(item, dict) and 'extracted_data' in item:
                    item = item['extracted_data']
                
                # Pretty print the data
                if isinstance(item, dict):
                    for key, value in item.items():
                        if isinstance(value, list) and len(value) > 0:
                            print(f"    📊 {key}: {len(value)} items")
                            for j, v in enumerate(value[:3]):  # Show first 3 items in lists
                                if isinstance(v, dict):
                                    name = v.get('name', v.get('title', 'Unnamed'))
                                    contact = v.get('email', v.get('phone', v.get('linkedin', 'No contact')))
                                    print(f"      {j+1}. {name} - {contact}")
                                else:
                                    print(f"      {j+1}. {str(v)[:80]}")
                        else:
                            print(f"    📄 {key}: {str(value)[:100]}")
                else:
                    print(f"    📄 {str(item)[:300]}")
                print()
        
    except KeyboardInterrupt:
        print("\n⚠️  Test interrupted by user")
    except Exception as e:
        print(f"💥 Exception: {str(e)}")

if __name__ == "__main__":
    print("🚀 Starting AI Navigation Test")
    print("🎯 Goal: Find event planning professionals on social media/professional networks")
    print("🤖 AI has complete freedom to choose the best sites and strategies")
    print("Press Ctrl+C to stop at any time\n")
    
    asyncio.run(test_event_planners())
    
    print("\n✨ Test completed!")
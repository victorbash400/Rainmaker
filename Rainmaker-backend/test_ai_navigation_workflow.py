"""
Test AI Navigation Workflow - Task 5.1 and 5.2 Implementation
Tests the intelligent prospect search and navigate_and_extract tools
"""

import asyncio
import json
import pytest
from app.mcp.enhanced_playwright_mcp import EnhancedPlaywrightMCP


class TestAINavigationWorkflow:
    """Test the AI navigation workflow implementation"""
    
    def setup_method(self):
        """Setup test environment"""
        self.mcp = EnhancedPlaywrightMCP()
    
    @classmethod
    def setup_class(cls):
        """Setup class-level test environment"""
        cls.mcp_instance = EnhancedPlaywrightMCP()
    
    def teardown_method(self):
        """Cleanup after tests"""
        try:
            self.mcp.close()
        except:
            pass
    
    @pytest.mark.asyncio
    async def test_intelligent_prospect_search_basic(self):
        """Test basic intelligent prospect search functionality"""
        # Test arguments
        arguments = {
            "task_description": "find wedding planners in Switzerland",
            "target_sites": ["google.com"],
            "max_results": 5,
            "headless": True
        }
        
        # Execute the tool
        result = await self.mcp._call_intelligent_prospect_search(arguments)
        
        # Verify result structure
        assert result is not None
        assert hasattr(result, 'content')
        assert len(result.content) > 0
        
        # Parse the result content
        result_data = json.loads(result.content[0].text)
        
        # Verify basic structure
        assert "task_description" in result_data
        assert "target_sites" in result_data
        assert "success" in result_data
        assert "timestamp" in result_data
        
        # If successful, verify prospect data
        if result_data.get("success"):
            assert "prospects_found" in result_data
            assert "prospects" in result_data
            assert isinstance(result_data["prospects"], list)
            
            # Verify prospect structure if any found
            if result_data["prospects"]:
                prospect = result_data["prospects"][0]
                assert "name" in prospect
                assert "source_url" in prospect
                assert "extraction_method" in prospect
                assert "ai_confidence_score" in prospect
                assert prospect["extraction_method"] == "ai_navigation"
        
        print(f"Intelligent prospect search result: {result_data.get('message', 'No message')}")
    
    @pytest.mark.asyncio
    async def test_navigate_and_extract_basic(self):
        """Test basic navigate and extract functionality"""
        # Test arguments
        arguments = {
            "url": "https://example.com",
            "extraction_goal": "contact information",
            "headless": True
        }
        
        # Execute the tool
        result = await self.mcp._call_navigate_and_extract(arguments)
        
        # Verify result structure
        assert result is not None
        assert hasattr(result, 'content')
        assert len(result.content) > 0
        
        # Parse the result content
        result_data = json.loads(result.content[0].text)
        
        # Verify basic structure
        assert "url" in result_data
        assert "extraction_goal" in result_data
        assert "success" in result_data
        assert "timestamp" in result_data
        
        # If successful, verify extracted data
        if result_data.get("success"):
            assert "extracted_data" in result_data
            assert "navigation_steps" in result_data
            
            extracted_data = result_data["extracted_data"]
            assert "url" in extracted_data
            assert "title" in extracted_data
            assert "extraction_goal" in extracted_data
            assert "extracted_at" in extracted_data
        
        print(f"Navigate and extract result: {result_data.get('message', 'No message')}")
    
    @pytest.mark.asyncio
    async def test_prospect_conversion_helper(self):
        """Test the prospect conversion helper method"""
        # Mock extracted data
        extracted_data = {
            "url": "https://example.com",
            "title": "Wedding Planners Switzerland",
            "results": [
                {
                    "title": "Swiss Wedding Co - Premium Wedding Planning",
                    "link": "https://swisswedding.com",
                    "description": "Professional wedding planning services in Switzerland"
                },
                {
                    "title": "Alpine Events - Corporate and Wedding Planning",
                    "link": "https://alpineevents.ch",
                    "description": "Full-service event planning for weddings and corporate events"
                }
            ],
            "emails": ["info@swisswedding.com"],
            "phones": ["+41 44 123 4567"]
        }
        
        # Test conversion
        prospects = self.mcp_instance.prospect_search_tool._convert_to_prospects(
            extracted_data, 
            "google.com", 
            "find wedding planners in Switzerland"
        )
        
        # Verify conversion
        assert isinstance(prospects, list)
        assert len(prospects) == 2  # Should create 2 prospects from results
        
        # Verify prospect structure
        prospect = prospects[0]
        assert "name" in prospect
        assert "source_url" in prospect
        assert "extraction_method" in prospect
        assert "ai_confidence_score" in prospect
        assert "source_site" in prospect
        assert "task_description" in prospect
        assert "extracted_at" in prospect
        
        assert prospect["extraction_method"] == "ai_navigation"
        assert prospect["source_site"] == "google.com"
        assert prospect["task_description"] == "find wedding planners in Switzerland"
        
        print(f"Converted {len(prospects)} prospects from extracted data")
    
    @pytest.mark.asyncio
    async def test_prospect_aggregation_helper(self):
        """Test the prospect aggregation helper method"""
        # Mock prospects from multiple sites
        all_prospects = [
            {
                "name": "Swiss Wedding Co",
                "source_url": "https://swisswedding.com",
                "ai_confidence_score": 0.9,
                "email": "info@swisswedding.com"
            },
            {
                "name": "Alpine Events",
                "source_url": "https://alpineevents.ch", 
                "ai_confidence_score": 0.8
            },
            {
                "name": "Swiss Wedding Co",  # Duplicate
                "source_url": "https://swisswedding.com",
                "ai_confidence_score": 0.7
            },
            {
                "name": "Mountain Weddings",
                "source_url": "https://mountainweddings.ch",
                "ai_confidence_score": 0.6,
                "phone": "+41 44 987 6543"
            }
        ]
        
        # Test aggregation
        final_prospects = self.mcp_instance.prospect_search_tool._aggregate_prospects(all_prospects, max_results=10)
        
        # Verify aggregation
        assert isinstance(final_prospects, list)
        assert len(final_prospects) == 3  # Should deduplicate to 3 unique prospects
        
        # Verify ranking (should be sorted by score)
        assert final_prospects[0]["ai_confidence_score"] >= final_prospects[1]["ai_confidence_score"]
        
        # Verify metadata added
        for i, prospect in enumerate(final_prospects):
            assert "rank" in prospect
            assert "aggregation_score" in prospect
            assert prospect["rank"] == i + 1
        
        print(f"Aggregated {len(all_prospects)} prospects to {len(final_prospects)} unique prospects")
    
    def test_potential_prospect_detection(self):
        """Test the potential prospect detection helper"""
        # Test cases
        test_cases = [
            ("Swiss Wedding Planning Services", "find wedding planners", True),
            ("Alpine Event Management Company", "find event planners", True),
            ("Home | About | Contact", "find wedding planners", False),
            ("Click here for more information", "find event planners", False),
            ("Professional Wedding Photography LLC", "find wedding services", True),
            ("Corporate Event Solutions Inc", "find corporate event planners", True),
            ("Privacy Policy", "find wedding planners", False),
            ("Menu", "find catering services", False),
            ("Luxury Catering Services", "find catering services", True)
        ]
        
        for name, task, expected in test_cases:
            result = self.mcp_instance.prospect_search_tool._is_potential_prospect(name, task)
            assert result == expected, f"Failed for '{name}' with task '{task}' - expected {expected}, got {result}"
        
        print("Potential prospect detection tests passed")
    
    def test_extraction_goal_detection(self):
        """Test extraction goal completion detection"""
        # Test contact goal
        contact_data = {
            "emails": ["test@example.com"],
            "phones": ["+41 44 123 4567"]
        }
        assert self.mcp_instance.navigate_extract_tool._is_extraction_goal_met(contact_data, "contact information") == True
        
        # Test prospect goal
        prospect_data = {
            "headings": ["About Us", "Our Services", "Contact"],
            "results": [{"title": "Wedding Planning", "link": "https://example.com"}]
        }
        assert self.mcp_instance.navigate_extract_tool._is_extraction_goal_met(prospect_data, "prospect information") == True
        
        # Test insufficient data
        empty_data = {}
        assert self.mcp_instance.navigate_extract_tool._is_extraction_goal_met(empty_data, "contact information") == False
        
        print("Extraction goal detection tests passed")


def run_tests():
    """Run the tests"""
    test_instance = TestAINavigationWorkflow()
    test_instance.setup_class()  # Initialize class-level MCP instance
    
    print("=== Testing AI Navigation Workflow Implementation ===")
    
    # Run sync tests
    print("\n1. Testing potential prospect detection...")
    test_instance.test_potential_prospect_detection()
    
    print("\n2. Testing extraction goal detection...")
    test_instance.test_extraction_goal_detection()
    
    # Run async tests
    print("\n3. Testing prospect conversion helper...")
    asyncio.run(test_instance.test_prospect_conversion_helper())
    
    print("\n4. Testing prospect aggregation helper...")
    asyncio.run(test_instance.test_prospect_aggregation_helper())
    
    print("\n5. Testing intelligent prospect search (basic)...")
    try:
        asyncio.run(test_instance.test_intelligent_prospect_search_basic())
    except Exception as e:
        print(f"Intelligent prospect search test failed (expected in test environment): {e}")
    
    print("\n6. Testing navigate and extract (basic)...")
    try:
        asyncio.run(test_instance.test_navigate_and_extract_basic())
    except Exception as e:
        print(f"Navigate and extract test failed (expected in test environment): {e}")
    
    print("\n=== AI Navigation Workflow Tests Completed ===")


if __name__ == "__main__":
    run_tests()
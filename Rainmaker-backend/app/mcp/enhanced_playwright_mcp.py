"""
Enhanced Playwright MCP Server - Main Entry Point
Coordinates AI-powered navigation tools using modular components
"""

import asyncio
import json
from typing import Dict, Any, Optional, Callable
import structlog
from mcp.server import Server
from mcp.types import Tool, TextContent, CallToolResult

from .browser_manager import BrowserManager
from .prospect_search_tool import ProspectSearchTool
from .navigate_extract_tool import NavigateExtractTool

logger = structlog.get_logger(__name__)

# Global browser viewer callback
browser_viewer_callback: Optional[Callable] = None

def set_browser_viewer_callback(callback: Callable):
    """Set callback function for browser viewer updates"""
    global browser_viewer_callback
    browser_viewer_callback = callback
    
    # Update callback in existing browser manager instance
    if hasattr(enhanced_browser_mcp, 'browser_manager'):
        enhanced_browser_mcp.browser_manager.browser_viewer_callback = callback
        logger.info("✅ Enhanced browser viewer callback updated in browser manager")
    
    logger.info("✅ Enhanced browser viewer callback set successfully", callback_type=type(callback).__name__)

def set_workflow_id(workflow_id: str):
    """Set workflow ID for browser viewer updates"""
    if hasattr(enhanced_browser_mcp, 'browser_manager'):
        enhanced_browser_mcp.browser_manager.workflow_id = workflow_id
        logger.info("✅ Workflow ID set in browser manager", workflow_id=workflow_id)


class EnhancedPlaywrightMCP:
    """
    Enhanced MCP server for AI-powered web navigation
    Coordinates browser management and AI navigation tools
    """
    
    def __init__(self):
        self.server = Server("enhanced_browser")
        
        # Initialize components
        self.browser_manager = BrowserManager(browser_viewer_callback)
        self.prospect_search_tool = ProspectSearchTool(self.browser_manager)
        self.navigate_extract_tool = NavigateExtractTool(self.browser_manager)
        
        # Register MCP tools
        self._register_tools()
    
    def _register_tools(self):
        """Register MCP tools"""
        
        @self.server.call_tool()
        async def test_browser(arguments: Dict[str, Any]) -> CallToolResult:
            """
            Test browser functionality with a simple search
            
            Args:
                test_query: Query to test with (default: "tomato")
                headless: Whether to run browser in headless mode (default: False for visibility)
            """
            return await self._call_test_browser(arguments)
        
        @self.server.call_tool()
        async def intelligent_prospect_search(arguments: Dict[str, Any]) -> CallToolResult:
            """
            AI-powered prospect search across multiple websites
            
            Args:
                task_description: Natural language description of the search task
                target_sites: List of websites to search (default: ["google.com"])
                max_results: Maximum number of prospects to find (default: 10)
                headless: Whether to run browser in headless mode (default: False)
            """
            return await self.prospect_search_tool.intelligent_prospect_search(arguments)
        
        @self.server.call_tool()
        async def navigate_and_extract(arguments: Dict[str, Any]) -> CallToolResult:
            """
            Navigate to a URL and extract data using AI analysis
            
            Args:
                url: URL to navigate to
                extraction_goal: What data to extract (e.g., "contact information", "event details")
                headless: Whether to run browser in headless mode (default: False)
            """
            return await self.navigate_extract_tool.navigate_and_extract(arguments)
        
        @self.server.call_tool()
        async def fill_search_form(arguments: Dict[str, Any]) -> CallToolResult:
            """
            Fill and submit search forms using AI analysis
            
            Args:
                page_url: URL of the page with the form
                search_terms: Dictionary of search terms to use
                headless: Whether to run browser in headless mode (default: False)
            """
            return await self._call_fill_search_form(arguments)
    
    async def _call_test_browser(self, arguments: Dict[str, Any]) -> CallToolResult:
        """Test browser functionality using sync playwright"""
        test_query = arguments.get("test_query", "tomato")
        headless = arguments.get("headless", False)
        
        def sync_browser_test():
            """Run sync browser test"""
            page = None
            try:
                logger.info("Starting sync browser test", test_query=test_query, headless=headless)
                
                # Create page
                page = self.browser_manager.create_page(headless=headless)
                
                # Capture: Browser launched
                self.browser_manager._capture_browser_step(page, "Browser Launched", "Initializing browser with stealth mode")
                
                # Navigate to Google
                logger.info("Navigating to Google")
                page.goto("https://www.google.com", wait_until="domcontentloaded", timeout=30000)
                page.wait_for_load_state("networkidle", timeout=10000)
                logger.info("Successfully navigated to Google")
                
                # Capture: Google loaded
                self.browser_manager._capture_browser_step(page, "Google Loaded", "Navigated to Google search page")
                
                # Search for test query
                logger.info("Filling search input", query=test_query)
                
                # Try multiple selectors for Google search input
                search_selectors = [
                    'input[name="q"]',
                    'textarea[name="q"]',
                    '[data-ved] input',
                    'input[type="text"]',
                    'textarea[aria-label*="Search"]'
                ]
                
                search_filled = False
                for selector in search_selectors:
                    try:
                        page.wait_for_selector(selector, timeout=5000)
                        page.fill(selector, test_query)
                        search_filled = True
                        logger.info("Search input filled successfully", selector=selector)
                        break
                    except Exception as e:
                        logger.debug("Selector failed, trying next", selector=selector, error=str(e))
                        continue
                
                if not search_filled:
                    raise Exception("Could not find Google search input field")
                
                logger.info("Search input filled, pressing Enter")
                
                # Capture: Search entered
                self.browser_manager._capture_browser_step(page, "Search Query Entered", f"Searching for: {test_query}")
                
                # Press Enter on the active search field
                page.keyboard.press('Enter')
                logger.info("Enter pressed, waiting for results")
                
                page.wait_for_load_state('networkidle', timeout=30000)
                logger.info("Page loaded, getting title")
                
                # Capture: Results loaded
                self.browser_manager._capture_browser_step(page, "Search Results", "Search completed successfully")
                
                # Get page title to confirm results
                title = page.title()
                logger.info("Got page title", title=title)
                
                # Brief pause if not headless to see results
                if not headless:
                    logger.info("Pausing to show results (headed mode)")
                    import time
                    time.sleep(3)
                
                logger.info("Browser test completed successfully")
                
                return {
                    "test_query": test_query,
                    "success": True,
                    "page_title": title,
                    "message": f"Successfully searched for '{test_query}' - page title: {title}",
                    "headless_mode": headless,
                    "timestamp": "2024-01-01T00:00:00Z"
                }
                
            except Exception as e:
                logger.error("Browser test failed", error=str(e), error_type=type(e).__name__)
                return {
                    "test_query": test_query,
                    "success": False,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "message": f"Browser test failed: {str(e)}",
                    "headless_mode": headless,
                    "timestamp": "2024-01-01T00:00:00Z"
                }
            finally:
                if page:
                    try:
                        logger.info("Closing page")
                        page.close()
                        logger.info("Page closed successfully")
                    except Exception as e:
                        logger.warning("Failed to close page", error=str(e))
        
        try:
            # Run sync browser test in thread pool
            result = await asyncio.get_event_loop().run_in_executor(
                self.browser_manager._executor, sync_browser_test
            )
            
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=json.dumps(result, indent=2)
                )],
                isError=not result.get("success", False)
            )
            
        except Exception as e:
            logger.error("Thread execution failed", error=str(e))
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=json.dumps({
                        "test_query": test_query,
                        "success": False,
                        "error": str(e),
                        "error_type": type(e).__name__,
                        "message": f"Thread execution failed: {str(e)}",
                        "headless_mode": headless,
                        "timestamp": "2024-01-01T00:00:00Z"
                    }, indent=2)
                )],
                isError=True
            )
    
    async def _call_fill_search_form(self, arguments: Dict[str, Any]) -> CallToolResult:
        """Fill and submit search forms using AI analysis (placeholder)"""
        page_url = arguments.get("page_url", "")
        search_terms = arguments.get("search_terms", {})
        headless = arguments.get("headless", False)
        
        # For now, return a placeholder response
        # This would be implemented similar to the other tools
        return CallToolResult(
            content=[TextContent(
                type="text",
                text=json.dumps({
                    "page_url": page_url,
                    "search_terms": search_terms,
                    "success": False,
                    "message": "Form filling tool not yet implemented",
                    "timestamp": "2024-01-01T00:00:00Z"
                }, indent=2)
            )],
            isError=True
        )
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> CallToolResult:
        """Call a specific MCP tool by name"""
        try:
            if tool_name == "test_browser":
                return await self._call_test_browser(arguments)
            elif tool_name == "intelligent_prospect_search":
                return await self.prospect_search_tool.intelligent_prospect_search(arguments)
            elif tool_name == "navigate_and_extract":
                return await self.navigate_extract_tool.navigate_and_extract(arguments)
            elif tool_name == "fill_search_form":
                return await self._call_fill_search_form(arguments)
            else:
                return CallToolResult(
                    content=[TextContent(
                        type="text",
                        text=json.dumps({"error": f"Unknown tool: {tool_name}"})
                    )],
                    isError=True
                )
        except Exception as e:
            logger.error("Error calling tool", tool_name=tool_name, error=str(e))
            return CallToolResult(
                content=[TextContent(
                    type="text", 
                    text=json.dumps({"error": f"Tool execution failed: {str(e)}"})
                )],
                isError=True
            )
    
    def get_server(self) -> Server:
        """Get the MCP server instance"""
        return self.server
    
    def close(self):
        """Close browser and cleanup"""
        self.browser_manager.close()


# Create global enhanced MCP server instance
enhanced_browser_mcp = EnhancedPlaywrightMCP()

# Maintain backward compatibility
simple_browser_mcp = enhanced_browser_mcp
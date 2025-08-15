"""
Enhanced Playwright MCP Server with AI-powered navigation capabilities
DEPRECATED: Use enhanced_playwright_mcp.py for new implementations
This file maintains backward compatibility
"""

# Import the new modular implementation
from .enhanced_playwright_mcp import (
    EnhancedPlaywrightMCP,
    enhanced_browser_mcp,
    set_browser_viewer_callback
)

# Maintain backward compatibility
SimpleBrowserMCP = EnhancedPlaywrightMCP
simple_browser_mcp = enhanced_browser_mcp

# Re-export for backward compatibility
__all__ = [
    'SimpleBrowserMCP',
    'simple_browser_mcp', 
    'enhanced_browser_mcp',
    'set_browser_viewer_callback'
]
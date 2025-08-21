"""
Browser Manager for Playwright MCP
Handles browser lifecycle and basic operations
"""

import base64
import os
from typing import Dict, Any, Optional
from datetime import datetime
import structlog
from playwright.sync_api import sync_playwright, Browser, Page, BrowserContext
from concurrent.futures import ThreadPoolExecutor

logger = structlog.get_logger(__name__)

try:
    from playwright_stealth import stealth_sync
    STEALTH_AVAILABLE = True
except ImportError:
    STEALTH_AVAILABLE = False
    logger.warning("playwright_stealth not available")


class BrowserManager:
    """
    Manages browser lifecycle and basic operations
    """
    
    def __init__(self, browser_viewer_callback=None):
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.playwright = None
        self._executor = ThreadPoolExecutor(max_workers=1)
        self.workflow_id: Optional[str] = None
        self.browser_viewer_callback = browser_viewer_callback
        self.state_dir = os.path.join(os.getcwd(), "browser_states")
        os.makedirs(self.state_dir, exist_ok=True)
    
    def _capture_browser_step(self, page: Page, step_name: str, details: str = ""):
        """Capture browser state and send to frontend via callback"""
        try:
            screenshot_base64 = None
            
            # Capture screenshot with increased timeout for font loading
            try:
                # Wait a bit for fonts and other resources to load
                try:
                    page.wait_for_timeout(500)  # Brief wait for fonts
                except:
                    pass
                
                screenshot_bytes = page.screenshot(full_page=False, timeout=10000)  # Increased from 3000ms to 10000ms
                screenshot_base64 = base64.b64encode(screenshot_bytes).decode('utf-8')
                logger.debug("Screenshot captured successfully", step=step_name)
            except Exception as screenshot_error:
                logger.warning("Failed to capture screenshot", step=step_name, error=str(screenshot_error))
            
            # Get page info
            try:
                title = page.title()
                url = page.url
            except Exception as page_error:
                logger.debug("Failed to get page info", error=str(page_error))
                title = "Loading..."
                url = "about:blank"
            
            # Extract reasoning from details if it follows the "action - reasoning" format
            reasoning = None
            if " - " in details:
                parts = details.split(" - ", 1)
                if len(parts) == 2:
                    reasoning = parts[1]
            
            # Create viewer update
            viewer_data = {
                "workflow_id": self.workflow_id,
                "step": step_name,
                "details": details,
                "url": url,
                "title": title,
                "screenshot": screenshot_base64,
                "timestamp": datetime.now().isoformat(),
                "status": "active"
            }
            
            # Add reasoning if extracted
            if reasoning:
                viewer_data["reasoning"] = reasoning
            
            # Send to frontend via callback
            logger.debug("Checking callback availability", has_callback=bool(self.browser_viewer_callback))
            if self.browser_viewer_callback:
                try:
                    logger.debug("Calling browser viewer callback", step=step_name, workflow_id=self.workflow_id)
                    self.browser_viewer_callback(viewer_data)
                    logger.info("✅ Browser step sent to frontend", step=step_name, url=url[:50] if url else "unknown")
                except Exception as e:
                    logger.warning("❌ Failed to send browser update via callback", error=str(e))
            else:
                logger.warning("⚠️ No browser viewer callback set - screenshots not being sent to frontend")
                    
        except Exception as e:
            logger.warning("Failed to capture browser step", step=step_name, error=str(e))
    
    def get_state_file_path(self, workflow_id: str, site_name: str = "default") -> str:
        """Get the file path for storing browser state"""
        return os.path.join(self.state_dir, f"{workflow_id}_{site_name}_state.json")
    
    def save_browser_state(self, workflow_id: str, site_name: str = "default"):
        """Save current browser context state (cookies, localStorage, etc.)"""
        if not self.context:
            logger.warning("No context to save state from")
            return
            
        try:
            state_file = self.get_state_file_path(workflow_id, site_name)
            state = self.context.storage_state(path=state_file)
            logger.info("Browser state saved", state_file=state_file, cookies_count=len(state.get("cookies", [])))
            return state_file
        except Exception as e:
            logger.error("Failed to save browser state", error=str(e))
            return None
    
    def load_browser_state(self, workflow_id: str, site_name: str = "default") -> bool:
        """Load browser context state if it exists"""
        state_file = self.get_state_file_path(workflow_id, site_name)
        
        if not os.path.exists(state_file):
            logger.info("No saved browser state found", state_file=state_file)
            return False
            
        try:
            if self.context:
                logger.info("Loading existing browser state", state_file=state_file)
                # Can't load state into existing context, need to create new one
                return False
            
            logger.info("Browser state file found", state_file=state_file)
            return True
        except Exception as e:
            logger.error("Failed to check browser state", error=str(e))
            return False
    
    def create_persistent_context(self, workflow_id: str, site_name: str = "default", headless: bool = False):
        """Create a persistent browser context that can save/load state"""
        self._ensure_browser_sync(headless=headless)
        
        state_file = self.get_state_file_path(workflow_id, site_name)
        
        context_options = {
            'viewport': {'width': 1280, 'height': 720},
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        # Load existing state if available
        if os.path.exists(state_file):
            try:
                context_options['storage_state'] = state_file
                logger.info("Creating context with saved state", state_file=state_file)
            except Exception as e:
                logger.warning("Failed to load state, creating fresh context", error=str(e))
        else:
            logger.info("Creating fresh browser context", workflow_id=workflow_id)
        
        self.context = self.browser.new_context(**context_options)
        
        if STEALTH_AVAILABLE:
            try:
                # Apply stealth to the context
                logger.info("Persistent context created with stealth")
            except Exception as stealth_error:
                logger.warning("Stealth failed on context", error=str(stealth_error))
        
        return self.context
    
    def _ensure_browser_sync(self, headless: bool = False):
        """Ensure browser is initialized using sync API"""
        try:
            logger.info("=== SYNC BROWSER INITIALIZATION START ===")
            
            logger.info("Browser state check", 
                       browser_exists=self.browser is not None,
                       browser_connected=self.browser.is_connected() if self.browser else False,
                       playwright_exists=self.playwright is not None)
            
            if not self.browser or not self.browser.is_connected():
                if not self.playwright:
                    logger.info("Starting sync Playwright instance...")
                    self.playwright = sync_playwright().start()
                    logger.info("Sync Playwright instance started successfully")
                
                logger.info("About to launch sync browser", headless=headless)
                
                self.browser = self.playwright.chromium.launch(
                    headless=headless,
                    slow_mo=500,  # Human-like timing
                    args=[
                        '--no-sandbox', 
                        '--disable-dev-shm-usage',
                        '--disable-gpu',
                        '--disable-infobars',
                        '--disable-blink-features=AutomationControlled',
                        '--no-first-run',
                        '--disable-default-apps',
                        '--disable-web-security',
                        '--disable-features=VizDisplayCompositor',
                        '--disable-font-subpixel-positioning',  # Faster font rendering
                        '--disable-background-timer-throttling',  # Prevent delayed font loading
                        '--disable-renderer-backgrounding',  # Keep renderer active
                        '--disable-backgrounding-occluded-windows'  # Prevent font loading delays
                    ]
                )
                logger.info("Sync browser launched successfully", 
                           browser_connected=self.browser.is_connected())
            else:
                logger.info("Browser already initialized and connected")
            
            logger.info("=== SYNC BROWSER INITIALIZATION COMPLETED ===")
                
        except Exception as e:
            logger.error("=== SYNC BROWSER INITIALIZATION FAILED ===")
            logger.error("Final error details", 
                        error=str(e), 
                        error_type=type(e).__name__)
            
            # Cleanup on failure
            try:
                if self.browser:
                    logger.info("Cleaning up browser")
                    self.browser.close()
                if self.playwright:
                    logger.info("Cleaning up playwright")
                    self.playwright.stop()
                    self.playwright = None
                    self.browser = None
            except Exception as cleanup_error:
                logger.error("Cleanup failed", cleanup_error=str(cleanup_error))
            raise
    
    def create_page(self, headless: bool = False, workflow_id: str = None, site_name: str = "default") -> Page:
        """Create a new page with stealth mode and optional persistence"""
        if workflow_id and not self.context:
            # Use persistent context if workflow_id provided
            self.create_persistent_context(workflow_id, site_name, headless)
            page = self.context.new_page()
        elif self.context:
            # Use existing context
            page = self.context.new_page()
        else:
            # Fallback to regular page creation
            self._ensure_browser_sync(headless=headless)
            page = self.browser.new_page(viewport={'width': 1280, 'height': 720})
        
        if STEALTH_AVAILABLE:
            try:
                stealth_sync(page)
                logger.info("New page created with stealth", 
                          persistent=bool(self.context),
                          workflow_id=workflow_id)
            except Exception as stealth_error:
                logger.warning("Stealth failed, continuing without it", error=str(stealth_error))
                logger.info("New page created (no stealth)", 
                          persistent=bool(self.context),
                          workflow_id=workflow_id)
        else:
            logger.info("New page created (stealth not available)", 
                      persistent=bool(self.context),
                      workflow_id=workflow_id)
        
        return page
    
    def close(self):
        """Close browser and cleanup"""
        if self.context:
            try:
                self.context.close()
                self.context = None
            except Exception as e:
                logger.warning("Failed to close context", error=str(e))
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
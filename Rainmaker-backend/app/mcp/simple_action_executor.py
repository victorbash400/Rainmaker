"""
Simple Action Executor for AI-powered web navigation
Executes basic actions: click, type, extract based on AI instructions
"""

import json
import re
from typing import Dict, Any, Optional, List
from datetime import datetime
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError
import structlog

logger = structlog.get_logger(__name__)


class SimpleActionExecutor:
    """
    Execute basic actions: click, type, extract
    Focuses on reliable execution of AI-determined actions
    """
    
    def __init__(self):
        # Default timeouts for different operations
        self.timeouts = {
            "click": 5000,
            "type": 3000,
            "wait": 10000,
            "extract": 5000
        }
        
        # Common selectors for different types of elements
        self.common_selectors = {
            "search_inputs": [
                'input[type="search"]',
                'input[name*="search"]',
                'input[placeholder*="search"]',
                'input[name="q"]',
                'textarea[name="q"]',
                '[role="searchbox"]'
            ],
            "submit_buttons": [
                'button[type="submit"]',
                'input[type="submit"]',
                'button:has-text("Search")',
                'button:has-text("Go")',
                'button:has-text("Submit")',
                '[role="button"]:has-text("Search")'
            ]
        }
    
    async def execute_action(self, page: Page, action: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute single action from AI
        
        Args:
            page: Playwright page object
            action: Action dictionary from AI with format:
                   {"action": "click", "selector": "#btn", "text": "optional"}
        
        Returns:
            Dict with execution result and status
        """
        try:
            action_type = action.get("action", "").lower()
            logger.info("Executing AI action", action=action_type, selector=action.get("selector"))
            
            # Route to appropriate action handler
            if action_type == "click":
                return await self._click_element(page, action)
            elif action_type == "type":
                return await self._type_text(page, action)
            elif action_type == "extract":
                return await self._extract_data(page, action)
            elif action_type == "wait":
                return await self._wait_for_condition(page, action)
            elif action_type == "navigate":
                return await self._navigate_to_url(page, action)
            elif action_type == "complete":
                return await self._complete_task(page, action)
            else:
                return {
                    "success": False,
                    "error": f"Unknown action type: {action_type}",
                    "action": action_type,
                    "timestamp": datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error("Action execution failed", error=str(e), action=action.get("action"))
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "action": action.get("action", "unknown"),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _click_element(self, page: Page, action: Dict[str, Any]) -> Dict[str, Any]:
        """
        Click on an element using the provided selector
        
        Args:
            page: Playwright page object
            action: Action dict with selector
            
        Returns:
            Execution result
        """
        try:
            selector = action.get("selector", "")
            if not selector:
                return {
                    "success": False,
                    "error": "No selector provided for click action",
                    "action": "click"
                }
            
            logger.info("Attempting to click element", selector=selector)
            
            # Wait for element to be available
            try:
                page.wait_for_selector(selector, timeout=self.timeouts["click"])
            except PlaywrightTimeoutError:
                # Try alternative selectors if the main one fails
                alternative_result = await self._try_alternative_click_selectors(page, selector)
                if alternative_result:
                    return alternative_result
                
                return {
                    "success": False,
                    "error": f"Element not found: {selector}",
                    "action": "click",
                    "selector": selector,
                    "timeout": self.timeouts["click"]
                }
            
            # Check if element is visible and enabled
            element = page.locator(selector)
            if not await element.is_visible():
                return {
                    "success": False,
                    "error": f"Element not visible: {selector}",
                    "action": "click",
                    "selector": selector
                }
            
            if not await element.is_enabled():
                return {
                    "success": False,
                    "error": f"Element not enabled: {selector}",
                    "action": "click",
                    "selector": selector
                }
            
            # Perform the click
            await element.click(timeout=self.timeouts["click"])
            
            # Wait a moment for any page changes
            try:
                page.wait_for_load_state("domcontentloaded", timeout=3000)
            except PlaywrightTimeoutError:
                # Page might not change, that's okay
                pass
            
            logger.info("Click executed successfully", selector=selector)
            
            return {
                "success": True,
                "action": "click",
                "selector": selector,
                "message": f"Successfully clicked element: {selector}",
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error("Click action failed", selector=selector, error=str(e))
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "action": "click",
                "selector": selector,
                "timestamp": datetime.now().isoformat()
            }
    
    async def _type_text(self, page: Page, action: Dict[str, Any]) -> Dict[str, Any]:
        """
        Type text into an input field
        
        Args:
            page: Playwright page object
            action: Action dict with selector and text
            
        Returns:
            Execution result
        """
        try:
            selector = action.get("selector", "")
            text = action.get("text", "")
            
            if not selector:
                return {
                    "success": False,
                    "error": "No selector provided for type action",
                    "action": "type"
                }
            
            if not text:
                return {
                    "success": False,
                    "error": "No text provided for type action",
                    "action": "type",
                    "selector": selector
                }
            
            logger.info("Attempting to type text", selector=selector, text=text[:50])
            
            # Wait for element to be available
            try:
                page.wait_for_selector(selector, timeout=self.timeouts["type"])
            except PlaywrightTimeoutError:
                # Try alternative input selectors
                alternative_result = await self._try_alternative_input_selectors(page, text)
                if alternative_result:
                    return alternative_result
                
                return {
                    "success": False,
                    "error": f"Input element not found: {selector}",
                    "action": "type",
                    "selector": selector,
                    "text": text
                }
            
            # Check if element is visible and enabled
            element = page.locator(selector)
            if not await element.is_visible():
                return {
                    "success": False,
                    "error": f"Input element not visible: {selector}",
                    "action": "type",
                    "selector": selector
                }
            
            if not await element.is_enabled():
                return {
                    "success": False,
                    "error": f"Input element not enabled: {selector}",
                    "action": "type",
                    "selector": selector
                }
            
            # Clear existing content and type new text
            await element.clear()
            await element.fill(text)
            
            # Verify text was entered
            current_value = await element.input_value()
            if current_value != text:
                logger.warning("Text verification failed", 
                             expected=text, actual=current_value, selector=selector)
            
            logger.info("Text typed successfully", selector=selector, text=text[:50])
            
            return {
                "success": True,
                "action": "type",
                "selector": selector,
                "text": text,
                "message": f"Successfully typed text into: {selector}",
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error("Type action failed", selector=selector, text=text[:50], error=str(e))
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "action": "type",
                "selector": selector,
                "text": text,
                "timestamp": datetime.now().isoformat()
            }
    
    async def _extract_data(self, page: Page, action: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract data from the current page
        
        Args:
            page: Playwright page object
            action: Action dict with data_type specification
            
        Returns:
            Execution result with extracted data
        """
        try:
            data_type = action.get("data_type", "general")
            logger.info("Extracting data from page", data_type=data_type, url=page.url)
            
            extracted_data = {
                "url": page.url,
                "title": page.title(),
                "data_type": data_type,
                "extracted_at": datetime.now().isoformat()
            }
            
            # Route to specific extraction method based on data type
            if data_type == "contact_info":
                contact_data = await self._extract_contact_information(page)
                extracted_data.update(contact_data)
            elif data_type == "search_results":
                results_data = await self._extract_search_results(page)
                extracted_data.update(results_data)
            elif data_type == "prospect_info":
                prospect_data = await self._extract_prospect_information(page)
                extracted_data.update(prospect_data)
            else:
                # General data extraction
                general_data = await self._extract_general_data(page)
                extracted_data.update(general_data)
            
            logger.info("Data extraction completed", 
                       data_type=data_type, 
                       items_found=len(extracted_data.get("items", [])))
            
            return {
                "success": True,
                "action": "extract",
                "data_type": data_type,
                "extracted_data": extracted_data,
                "message": f"Successfully extracted {data_type} data",
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error("Data extraction failed", data_type=data_type, error=str(e))
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "action": "extract",
                "data_type": data_type,
                "timestamp": datetime.now().isoformat()
            }
    
    async def _wait_for_condition(self, page: Page, action: Dict[str, Any]) -> Dict[str, Any]:
        """
        Wait for a specific condition to be met
        
        Args:
            page: Playwright page object
            action: Action dict with condition specification
            
        Returns:
            Execution result
        """
        try:
            condition = action.get("condition", "page_load")
            timeout = action.get("timeout", self.timeouts["wait"])
            
            logger.info("Waiting for condition", condition=condition, timeout=timeout)
            
            if condition == "page_load":
                page.wait_for_load_state("domcontentloaded", timeout=timeout)
            elif condition == "network_idle":
                page.wait_for_load_state("networkidle", timeout=timeout)
            elif condition.startswith("selector:"):
                selector = condition.replace("selector:", "")
                page.wait_for_selector(selector, timeout=timeout)
            else:
                # Default to page load
                page.wait_for_load_state("domcontentloaded", timeout=timeout)
            
            return {
                "success": True,
                "action": "wait",
                "condition": condition,
                "message": f"Successfully waited for condition: {condition}",
                "timestamp": datetime.now().isoformat()
            }
            
        except PlaywrightTimeoutError:
            return {
                "success": False,
                "error": f"Timeout waiting for condition: {condition}",
                "action": "wait",
                "condition": condition,
                "timeout": timeout,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error("Wait action failed", condition=condition, error=str(e))
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "action": "wait",
                "condition": condition,
                "timestamp": datetime.now().isoformat()
            }
    
    async def _navigate_to_url(self, page: Page, action: Dict[str, Any]) -> Dict[str, Any]:
        """
        Navigate to a specific URL
        
        Args:
            page: Playwright page object
            action: Action dict with URL
            
        Returns:
            Execution result
        """
        try:
            url = action.get("url", "")
            if not url:
                return {
                    "success": False,
                    "error": "No URL provided for navigate action",
                    "action": "navigate"
                }
            
            logger.info("Navigating to URL", url=url)
            
            # Navigate to the URL
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            
            # Wait for page to be ready
            page.wait_for_load_state("networkidle", timeout=10000)
            
            current_url = page.url
            title = page.title()
            
            logger.info("Navigation completed", url=current_url, title=title)
            
            return {
                "success": True,
                "action": "navigate",
                "url": url,
                "current_url": current_url,
                "title": title,
                "message": f"Successfully navigated to: {url}",
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error("Navigation failed", url=url, error=str(e))
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "action": "navigate",
                "url": url,
                "timestamp": datetime.now().isoformat()
            }
    
    async def _complete_task(self, page: Page, action: Dict[str, Any]) -> Dict[str, Any]:
        """
        Mark task as complete with final results
        
        Args:
            page: Playwright page object
            action: Action dict with result data
            
        Returns:
            Execution result
        """
        try:
            result = action.get("result", {})
            reasoning = action.get("reasoning", "Task completed")
            
            logger.info("Task completion", reasoning=reasoning)
            
            # Add current page context to results
            completion_data = {
                "final_url": page.url,
                "final_title": page.title(),
                "completion_time": datetime.now().isoformat(),
                "reasoning": reasoning,
                "result": result
            }
            
            return {
                "success": True,
                "action": "complete",
                "completion_data": completion_data,
                "message": f"Task completed: {reasoning}",
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error("Task completion failed", error=str(e))
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "action": "complete",
                "timestamp": datetime.now().isoformat()
            }
    
    async def _try_alternative_click_selectors(self, page: Page, original_selector: str) -> Optional[Dict[str, Any]]:
        """
        Try alternative selectors when the original click selector fails
        
        Args:
            page: Playwright page object
            original_selector: The selector that failed
            
        Returns:
            Execution result if alternative found, None otherwise
        """
        try:
            # Generate alternative selectors based on the original
            alternatives = self._generate_alternative_selectors(original_selector)
            
            for alt_selector in alternatives:
                try:
                    page.wait_for_selector(alt_selector, timeout=2000)
                    element = page.locator(alt_selector)
                    
                    if await element.is_visible() and await element.is_enabled():
                        await element.click()
                        logger.info("Alternative click selector worked", 
                                   original=original_selector, alternative=alt_selector)
                        
                        return {
                            "success": True,
                            "action": "click",
                            "selector": alt_selector,
                            "original_selector": original_selector,
                            "message": f"Successfully clicked using alternative selector: {alt_selector}",
                            "timestamp": datetime.now().isoformat()
                        }
                except:
                    continue
            
            return None
            
        except Exception as e:
            logger.debug("Alternative click selectors failed", error=str(e))
            return None
    
    async def _try_alternative_input_selectors(self, page: Page, text: str) -> Optional[Dict[str, Any]]:
        """
        Try common input selectors when the original input selector fails
        
        Args:
            page: Playwright page object
            text: Text to type
            
        Returns:
            Execution result if alternative found, None otherwise
        """
        try:
            # Try common search input selectors
            for selector in self.common_selectors["search_inputs"]:
                try:
                    page.wait_for_selector(selector, timeout=2000)
                    element = page.locator(selector)
                    
                    if await element.is_visible() and await element.is_enabled():
                        await element.clear()
                        await element.fill(text)
                        logger.info("Alternative input selector worked", 
                                   selector=selector, text=text[:50])
                        
                        return {
                            "success": True,
                            "action": "type",
                            "selector": selector,
                            "text": text,
                            "message": f"Successfully typed using alternative selector: {selector}",
                            "timestamp": datetime.now().isoformat()
                        }
                except:
                    continue
            
            return None
            
        except Exception as e:
            logger.debug("Alternative input selectors failed", error=str(e))
            return None
    
    def _generate_alternative_selectors(self, original_selector: str) -> List[str]:
        """
        Generate alternative selectors based on the original
        
        Args:
            original_selector: The original selector that failed
            
        Returns:
            List of alternative selectors to try
        """
        alternatives = []
        
        # If it's an ID selector, try class-based alternatives
        if original_selector.startswith('#'):
            element_id = original_selector[1:]
            alternatives.extend([
                f'[id="{element_id}"]',
                f'*[id*="{element_id}"]',
                f'.{element_id}',  # Sometimes IDs are used as classes
            ])
        
        # If it's a class selector, try ID and attribute alternatives
        elif original_selector.startswith('.'):
            class_name = original_selector[1:]
            alternatives.extend([
                f'[class*="{class_name}"]',
                f'#{class_name}',  # Sometimes classes are used as IDs
                f'*[class~="{class_name}"]'
            ])
        
        # If it's an attribute selector, try variations
        elif '[' in original_selector and ']' in original_selector:
            # Try without quotes, with different quotes, etc.
            if '"' in original_selector:
                alternatives.append(original_selector.replace('"', "'"))
            if '=' in original_selector:
                # Try contains instead of exact match
                attr_part = original_selector.split('=')[0] + '*='
                value_part = original_selector.split('=')[1]
                alternatives.append(attr_part + value_part)
        
        # Add some common fallback patterns
        alternatives.extend([
            'button[type="submit"]',
            'input[type="submit"]',
            '[role="button"]',
            'a[href]',
            'button',
            'input'
        ])
        
        return alternatives[:5]  # Limit to first 5 alternatives
    
    async def _extract_contact_information(self, page: Page) -> Dict[str, Any]:
        """
        Extract contact information from the current page
        
        Args:
            page: Playwright page object
            
        Returns:
            Dict with extracted contact information
        """
        try:
            contact_data = {
                "emails": [],
                "phones": [],
                "addresses": [],
                "social_links": []
            }
            
            # Get page text for pattern matching
            page_text = page.inner_text()
            
            # Extract email addresses
            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            emails = re.findall(email_pattern, page_text)
            contact_data["emails"] = list(set(emails))[:10]  # Unique emails, max 10
            
            # Extract phone numbers (various formats)
            phone_patterns = [
                r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',  # US format
                r'\b\(\d{3}\)\s?\d{3}[-.]?\d{4}\b',  # (123) 456-7890
                r'\b\+\d{1,3}[-.\s]?\d{1,4}[-.\s]?\d{1,4}[-.\s]?\d{1,9}\b'  # International
            ]
            
            phones = []
            for pattern in phone_patterns:
                phones.extend(re.findall(pattern, page_text))
            contact_data["phones"] = list(set(phones))[:10]
            
            # Extract social media links
            social_patterns = {
                "linkedin": r'https?://(?:www\.)?linkedin\.com/[^\s]+',
                "facebook": r'https?://(?:www\.)?facebook\.com/[^\s]+',
                "twitter": r'https?://(?:www\.)?twitter\.com/[^\s]+',
                "instagram": r'https?://(?:www\.)?instagram\.com/[^\s]+'
            }
            
            for platform, pattern in social_patterns.items():
                links = re.findall(pattern, page_text)
                for link in links[:3]:  # Max 3 per platform
                    contact_data["social_links"].append({
                        "platform": platform,
                        "url": link
                    })
            
            return contact_data
            
        except Exception as e:
            logger.error("Contact information extraction failed", error=str(e))
            return {"emails": [], "phones": [], "addresses": [], "social_links": []}
    
    async def _extract_search_results(self, page: Page) -> Dict[str, Any]:
        """
        Extract search results from the current page
        
        Args:
            page: Playwright page object
            
        Returns:
            Dict with extracted search results
        """
        try:
            results_data = {
                "results": [],
                "total_found": 0,
                "page_number": 1
            }
            
            # Common search result selectors for different sites
            result_selectors = [
                'div[data-result-index]',  # Google
                '.g',  # Google results
                '.result',  # Generic results
                '[data-testid="result"]',  # Some modern sites
                '.search-result',  # Generic search results
                'article',  # Article-based results
                '.listing'  # Directory listings
            ]
            
            results_found = []
            
            for selector in result_selectors:
                try:
                    elements = page.query_selector_all(selector)
                    if elements and len(elements) > 2:  # Found meaningful results
                        for i, element in enumerate(elements[:20]):  # Max 20 results
                            try:
                                # Extract title
                                title_elem = element.query_selector('h1, h2, h3, h4, a[href]')
                                title = title_elem.inner_text().strip() if title_elem else ""
                                
                                # Extract link
                                link_elem = element.query_selector('a[href]')
                                link = link_elem.get_attribute('href') if link_elem else ""
                                
                                # Extract description/snippet
                                desc_elem = element.query_selector('p, .description, .snippet')
                                description = desc_elem.inner_text().strip() if desc_elem else ""
                                
                                if title and len(title) > 5:  # Valid result
                                    results_found.append({
                                        "title": title[:200],
                                        "link": link,
                                        "description": description[:300],
                                        "position": i + 1
                                    })
                                    
                            except Exception as e:
                                logger.debug("Failed to extract individual result", error=str(e))
                                continue
                        
                        if results_found:
                            break  # Found results with this selector
                            
                except Exception as e:
                    logger.debug("Selector failed for search results", selector=selector, error=str(e))
                    continue
            
            results_data["results"] = results_found
            results_data["total_found"] = len(results_found)
            
            return results_data
            
        except Exception as e:
            logger.error("Search results extraction failed", error=str(e))
            return {"results": [], "total_found": 0, "page_number": 1}
    
    async def _extract_prospect_information(self, page: Page) -> Dict[str, Any]:
        """
        Extract prospect information from the current page
        
        Args:
            page: Playwright page object
            
        Returns:
            Dict with extracted prospect information
        """
        try:
            prospect_data = {
                "prospects": [],
                "business_info": {},
                "event_signals": []
            }
            
            # Get page content
            page_text = page.inner_text()
            title = page.title()
            
            # Look for event-related keywords
            event_keywords = [
                "wedding", "birthday", "anniversary", "celebration", "party",
                "corporate", "conference", "meeting", "event", "planning",
                "venue", "catering", "photography", "music", "decoration",
                "planner", "coordinator", "organizer"
            ]
            
            found_keywords = []
            for keyword in event_keywords:
                if keyword.lower() in page_text.lower():
                    found_keywords.append(keyword)
            
            prospect_data["event_signals"] = found_keywords
            
            # Extract business information
            business_info = {}
            
            # Look for business name in title or headings
            headings = page.query_selector_all('h1, h2, h3')
            for heading in headings[:5]:
                text = heading.inner_text().strip()
                if len(text) > 5 and len(text) < 100:
                    business_info["potential_business_name"] = text
                    break
            
            # Extract contact info
            contact_info = await self._extract_contact_information(page)
            business_info.update(contact_info)
            
            # Create prospect entry if we found relevant information
            if found_keywords and (contact_info["emails"] or contact_info["phones"]):
                prospect = {
                    "source_url": page.url,
                    "business_name": business_info.get("potential_business_name", title),
                    "event_types": found_keywords,
                    "contact_info": contact_info,
                    "extraction_confidence": min(0.9, len(found_keywords) * 0.2 + 0.3),
                    "extracted_at": datetime.now().isoformat()
                }
                prospect_data["prospects"].append(prospect)
            
            prospect_data["business_info"] = business_info
            
            return prospect_data
            
        except Exception as e:
            logger.error("Prospect information extraction failed", error=str(e))
            return {"prospects": [], "business_info": {}, "event_signals": []}
    
    async def _extract_general_data(self, page: Page) -> Dict[str, Any]:
        """
        Extract general data from the current page
        
        Args:
            page: Playwright page object
            
        Returns:
            Dict with general extracted data
        """
        try:
            general_data = {
                "headings": [],
                "links": [],
                "images": [],
                "forms": []
            }
            
            # Extract headings
            headings = page.query_selector_all('h1, h2, h3, h4, h5, h6')
            for heading in headings[:10]:
                text = heading.inner_text().strip()
                if text and len(text) > 3:
                    general_data["headings"].append({
                        "level": heading.tag_name.lower(),
                        "text": text[:200]
                    })
            
            # Extract important links
            links = page.query_selector_all('a[href]')
            for link in links[:20]:
                href = link.get_attribute('href')
                text = link.inner_text().strip()
                if href and text and len(text) > 3:
                    general_data["links"].append({
                        "text": text[:100],
                        "href": href
                    })
            
            # Extract form information
            forms = page.query_selector_all('form')
            for form in forms[:5]:
                form_info = {
                    "action": form.get_attribute('action') or "",
                    "method": form.get_attribute('method') or "get",
                    "inputs": []
                }
                
                inputs = form.query_selector_all('input, select, textarea')
                for input_elem in inputs[:10]:
                    input_info = {
                        "type": input_elem.get_attribute('type') or "text",
                        "name": input_elem.get_attribute('name') or "",
                        "placeholder": input_elem.get_attribute('placeholder') or ""
                    }
                    form_info["inputs"].append(input_info)
                
                general_data["forms"].append(form_info)
            
            return general_data
            
        except Exception as e:
            logger.error("General data extraction failed", error=str(e))
            return {"headings": [], "links": [], "images": [], "forms": []} 
   
    # Form Interaction Capabilities (Task 4.2)
    
    async def fill_search_form(self, page: Page, search_terms: Dict[str, str], task_context: str = "") -> Dict[str, Any]:
        """
        Intelligently fill search forms based on AI instructions and task context
        
        Args:
            page: Playwright page object
            search_terms: Dictionary of search terms to use
            task_context: Context about what we're searching for
            
        Returns:
            Dict with form filling result
        """
        try:
            logger.info("Filling search form", search_terms=search_terms, context=task_context)
            
            # Detect search forms on the page
            search_form = await self._detect_search_form(page)
            if not search_form:
                return {
                    "success": False,
                    "error": "No search form detected on page",
                    "action": "fill_search_form",
                    "timestamp": datetime.now().isoformat()
                }
            
            # Fill the form intelligently
            fill_result = await self._intelligent_form_fill(page, search_form, search_terms, task_context)
            
            if not fill_result["success"]:
                return fill_result
            
            # Submit the form
            submit_result = await self._submit_search_form(page, search_form)
            
            # Combine results
            return {
                "success": submit_result["success"],
                "action": "fill_search_form",
                "form_filled": fill_result,
                "form_submitted": submit_result,
                "message": "Search form filled and submitted successfully" if submit_result["success"] else "Form filled but submission failed",
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error("Search form filling failed", error=str(e))
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "action": "fill_search_form",
                "timestamp": datetime.now().isoformat()
            }
    
    async def _detect_search_form(self, page: Page) -> Optional[Dict[str, Any]]:
        """
        Detect search forms on the current page
        
        Args:
            page: Playwright page object
            
        Returns:
            Dict with search form information or None if not found
        """
        try:
            # Look for forms with search-related attributes
            search_form_selectors = [
                'form[role="search"]',
                'form[class*="search"]',
                'form[id*="search"]',
                'form:has(input[type="search"])',
                'form:has(input[name*="search"])',
                'form:has(input[placeholder*="search"])',
                'form:has(input[name="q"])',
                'form'  # Fallback to any form
            ]
            
            for selector in search_form_selectors:
                try:
                    forms = page.query_selector_all(selector)
                    for form in forms:
                        # Analyze form to see if it's likely a search form
                        form_info = await self._analyze_form_for_search(form)
                        if form_info["is_search_form"]:
                            logger.info("Search form detected", selector=selector, confidence=form_info["confidence"])
                            return form_info
                except Exception as e:
                    logger.debug("Form selector failed", selector=selector, error=str(e))
                    continue
            
            return None
            
        except Exception as e:
            logger.error("Search form detection failed", error=str(e))
            return None
    
    async def _analyze_form_for_search(self, form_element) -> Dict[str, Any]:
        """
        Analyze a form element to determine if it's a search form
        
        Args:
            form_element: Playwright element handle for the form
            
        Returns:
            Dict with analysis results
        """
        try:
            form_info = {
                "is_search_form": False,
                "confidence": 0.0,
                "search_inputs": [],
                "submit_buttons": [],
                "form_element": form_element
            }
            
            # Get form attributes
            form_action = form_element.get_attribute('action') or ""
            form_class = form_element.get_attribute('class') or ""
            form_id = form_element.get_attribute('id') or ""
            
            confidence_score = 0.0
            
            # Check form attributes for search indicators
            search_indicators = ['search', 'query', 'find', 'lookup']
            for indicator in search_indicators:
                if indicator in form_action.lower():
                    confidence_score += 0.3
                if indicator in form_class.lower():
                    confidence_score += 0.2
                if indicator in form_id.lower():
                    confidence_score += 0.2
            
            # Find input elements in the form
            inputs = form_element.query_selector_all('input, textarea, select')
            search_inputs = []
            
            for input_elem in inputs:
                input_type = input_elem.get_attribute('type') or 'text'
                input_name = input_elem.get_attribute('name') or ''
                input_placeholder = input_elem.get_attribute('placeholder') or ''
                input_id = input_elem.get_attribute('id') or ''
                
                # Check if this input is likely for search
                input_confidence = 0.0
                
                if input_type == 'search':
                    input_confidence = 0.9
                elif input_type in ['text', 'email', 'tel']:
                    # Check name, placeholder, and id for search indicators
                    all_text = (input_name + ' ' + input_placeholder + ' ' + input_id).lower()
                    for indicator in search_indicators:
                        if indicator in all_text:
                            input_confidence = max(input_confidence, 0.7)
                    
                    # Special case for Google-style search
                    if input_name == 'q':
                        input_confidence = 0.8
                
                if input_confidence > 0.3:
                    search_inputs.append({
                        "element": input_elem,
                        "type": input_type,
                        "name": input_name,
                        "placeholder": input_placeholder,
                        "confidence": input_confidence,
                        "selector": await self._generate_element_selector(input_elem)
                    })
                    confidence_score += input_confidence * 0.5
            
            # Find submit buttons
            submit_buttons = []
            buttons = form_element.query_selector_all('button, input[type="submit"], input[type="button"]')
            
            for button in buttons:
                button_text = button.inner_text().strip().lower()
                button_value = button.get_attribute('value') or ''
                button_type = button.get_attribute('type') or ''
                
                # Check if button is likely for search submission
                button_confidence = 0.0
                
                if button_type == 'submit':
                    button_confidence = 0.6
                
                search_button_terms = ['search', 'find', 'go', 'submit', 'lookup']
                for term in search_button_terms:
                    if term in button_text or term in button_value.lower():
                        button_confidence = max(button_confidence, 0.8)
                
                if button_confidence > 0.3:
                    submit_buttons.append({
                        "element": button,
                        "text": button_text,
                        "type": button_type,
                        "confidence": button_confidence,
                        "selector": await self._generate_element_selector(button)
                    })
                    confidence_score += button_confidence * 0.3
            
            # Determine if this is a search form
            form_info["confidence"] = min(1.0, confidence_score)
            form_info["is_search_form"] = confidence_score > 0.5
            form_info["search_inputs"] = search_inputs
            form_info["submit_buttons"] = submit_buttons
            
            return form_info
            
        except Exception as e:
            logger.error("Form analysis failed", error=str(e))
            return {
                "is_search_form": False,
                "confidence": 0.0,
                "search_inputs": [],
                "submit_buttons": [],
                "form_element": form_element
            }
    
    async def _intelligent_form_fill(self, page: Page, form_info: Dict[str, Any], 
                                   search_terms: Dict[str, str], task_context: str) -> Dict[str, Any]:
        """
        Intelligently fill form fields based on AI analysis
        
        Args:
            page: Playwright page object
            form_info: Information about the detected form
            search_terms: Search terms to use
            task_context: Context about the search task
            
        Returns:
            Dict with form filling results
        """
        try:
            filled_fields = []
            
            # Get the primary search query
            primary_query = search_terms.get("query", "") or search_terms.get("search", "") or task_context
            
            # Fill search inputs
            for input_info in form_info["search_inputs"]:
                try:
                    input_element = input_info["element"]
                    input_name = input_info["name"]
                    input_placeholder = input_info["placeholder"]
                    
                    # Determine what to fill based on input characteristics
                    fill_text = self._determine_input_fill_text(
                        input_name, input_placeholder, search_terms, primary_query, task_context
                    )
                    
                    if fill_text:
                        # Clear and fill the input
                        await input_element.clear()
                        await input_element.fill(fill_text)
                        
                        # Verify the text was entered
                        current_value = await input_element.input_value()
                        
                        filled_fields.append({
                            "name": input_name,
                            "placeholder": input_placeholder,
                            "filled_text": fill_text,
                            "verified": current_value == fill_text,
                            "selector": input_info["selector"]
                        })
                        
                        logger.info("Form field filled", name=input_name, text=fill_text[:50])
                    
                except Exception as e:
                    logger.warning("Failed to fill form field", name=input_info.get("name"), error=str(e))
                    continue
            
            return {
                "success": len(filled_fields) > 0,
                "filled_fields": filled_fields,
                "message": f"Successfully filled {len(filled_fields)} form fields",
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error("Intelligent form filling failed", error=str(e))
            return {
                "success": False,
                "error": str(e),
                "filled_fields": [],
                "timestamp": datetime.now().isoformat()
            }
    
    def _determine_input_fill_text(self, input_name: str, input_placeholder: str, 
                                 search_terms: Dict[str, str], primary_query: str, task_context: str) -> str:
        """
        Determine what text to fill in a specific input field
        
        Args:
            input_name: Name attribute of the input
            input_placeholder: Placeholder text of the input
            search_terms: Available search terms
            primary_query: Primary search query
            task_context: Task context
            
        Returns:
            Text to fill in the input field
        """
        input_name_lower = input_name.lower()
        placeholder_lower = input_placeholder.lower()
        
        # Check for specific field types
        if any(term in input_name_lower for term in ['email', 'mail']):
            return search_terms.get("email", "")
        
        if any(term in input_name_lower for term in ['phone', 'tel', 'mobile']):
            return search_terms.get("phone", "")
        
        if any(term in input_name_lower for term in ['location', 'city', 'address', 'zip']):
            return search_terms.get("location", "") or search_terms.get("city", "")
        
        if any(term in input_name_lower for term in ['name', 'first', 'last']):
            return search_terms.get("name", "")
        
        # For search fields, use the primary query or specific search terms
        if any(term in input_name_lower for term in ['search', 'query', 'q', 'find']):
            return primary_query or search_terms.get("query", "")
        
        # Check placeholder for hints
        if any(term in placeholder_lower for term in ['search', 'find', 'enter']):
            return primary_query or search_terms.get("query", "")
        
        # Default to primary query for text inputs
        return primary_query
    
    async def _submit_search_form(self, page: Page, form_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Submit the search form using the most appropriate method
        
        Args:
            page: Playwright page object
            form_info: Information about the form
            
        Returns:
            Dict with submission results
        """
        try:
            # Try to click submit button first
            if form_info["submit_buttons"]:
                # Use the button with highest confidence
                best_button = max(form_info["submit_buttons"], key=lambda b: b["confidence"])
                
                try:
                    button_element = best_button["element"]
                    await button_element.click()
                    
                    # Wait for page to change
                    page.wait_for_load_state("domcontentloaded", timeout=10000)
                    
                    logger.info("Form submitted via button click", button_text=best_button["text"])
                    
                    return {
                        "success": True,
                        "method": "button_click",
                        "button_text": best_button["text"],
                        "message": "Form submitted successfully via button click",
                        "timestamp": datetime.now().isoformat()
                    }
                    
                except Exception as e:
                    logger.warning("Button click submission failed", error=str(e))
            
            # Fallback: try pressing Enter on search input
            if form_info["search_inputs"]:
                try:
                    primary_input = form_info["search_inputs"][0]["element"]
                    await primary_input.press("Enter")
                    
                    # Wait for page to change
                    page.wait_for_load_state("domcontentloaded", timeout=10000)
                    
                    logger.info("Form submitted via Enter key")
                    
                    return {
                        "success": True,
                        "method": "enter_key",
                        "message": "Form submitted successfully via Enter key",
                        "timestamp": datetime.now().isoformat()
                    }
                    
                except Exception as e:
                    logger.warning("Enter key submission failed", error=str(e))
            
            # Fallback: try form.submit()
            try:
                form_element = form_info["form_element"]
                await form_element.evaluate("form => form.submit()")
                
                # Wait for page to change
                page.wait_for_load_state("domcontentloaded", timeout=10000)
                
                logger.info("Form submitted via JavaScript")
                
                return {
                    "success": True,
                    "method": "javascript_submit",
                    "message": "Form submitted successfully via JavaScript",
                    "timestamp": datetime.now().isoformat()
                }
                
            except Exception as e:
                logger.warning("JavaScript submission failed", error=str(e))
            
            return {
                "success": False,
                "error": "All form submission methods failed",
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error("Form submission failed", error=str(e))
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "timestamp": datetime.now().isoformat()
            }
    
    async def _generate_element_selector(self, element) -> str:
        """
        Generate a CSS selector for a Playwright element
        
        Args:
            element: Playwright element handle
            
        Returns:
            CSS selector string
        """
        try:
            # Try to get a reliable selector
            element_id = element.get_attribute('id')
            if element_id:
                return f"#{element_id}"
            
            element_name = element.get_attribute('name')
            if element_name:
                return f'[name="{element_name}"]'
            
            element_class = element.get_attribute('class')
            if element_class:
                classes = element_class.split()
                if classes:
                    return f".{classes[0]}"
            
            # Fallback to tag name
            tag_name = element.tag_name.lower()
            return tag_name
            
        except Exception as e:
            logger.debug("Failed to generate element selector", error=str(e))
            return "unknown"
    
    async def extract_search_results_data(self, page: Page, extraction_config: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Extract data from search results with intelligent parsing
        
        Args:
            page: Playwright page object
            extraction_config: Configuration for what data to extract
            
        Returns:
            Dict with extracted search results data
        """
        try:
            logger.info("Extracting search results data", url=page.url)
            
            # Use the existing search results extraction method
            search_results = await self._extract_search_results(page)
            
            # Enhance with prospect-specific analysis if configured
            if extraction_config and extraction_config.get("extract_prospects", False):
                prospect_data = await self._extract_prospect_information(page)
                search_results["prospect_analysis"] = prospect_data
            
            # Add metadata
            search_results["extraction_metadata"] = {
                "page_url": page.url,
                "page_title": page.title(),
                "extracted_at": datetime.now().isoformat(),
                "extraction_method": "intelligent_search_results"
            }
            
            logger.info("Search results extraction completed", 
                       results_count=search_results.get("total_found", 0))
            
            return {
                "success": True,
                "action": "extract_search_results",
                "extracted_data": search_results,
                "message": f"Successfully extracted {search_results.get('total_found', 0)} search results",
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error("Search results data extraction failed", error=str(e))
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "action": "extract_search_results",
                "timestamp": datetime.now().isoformat()
            }
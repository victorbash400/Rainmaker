"""
Navigate and Extract Tool - Pure AI-Driven Navigation
Uses Gemini AI to read pages, make decisions, and extract data without any hardcoded logic

TEMPORARY MODIFICATIONS FOR DEMO/TESTING:
- max_steps reduced from 20 to 5 (line ~25)
- Navigation timeouts reduced from 30s/10s to 15s/5s (lines ~49-50, ~666)
TODO: Revert these changes for production use
"""

import json
import re
import asyncio
from typing import Dict, Any, Set, List
from datetime import datetime
import structlog
from mcp.types import CallToolResult, TextContent
from urllib.parse import urlparse

logger = structlog.get_logger(__name__)


class NavigateExtractTool:
    """Pure AI-driven navigation and extraction tool - AI decides everything"""
    
    def __init__(self, browser_manager):
        self.browser_manager = browser_manager
        # TEMPORARY: Reduced from 20 to 5 steps for faster testing/demo
        # TODO: Remove this limit or make it configurable for production
        self.max_steps = 5  # Was: 20

    async def navigate_and_extract(self, arguments: Dict[str, Any]) -> CallToolResult:
        """Navigate to URL and extract data using pure AI decision making"""
        url = arguments.get("url", "")
        extraction_goal = arguments.get("extraction_goal", "general data")
        headless = arguments.get("headless", False)
        
        if not url:
            return CallToolResult(
                content=[TextContent(type="text", text=json.dumps({"success": False, "error": "URL is required"}))],
                isError=True
            )
        
        def sync_navigate_extract():
            page = None
            try:
                logger.info("Starting AI navigation", url=url, goal=extraction_goal)
                
                page = self.browser_manager.create_page(headless=headless)
                self.browser_manager._capture_browser_step(page, "Navigation Started", f"AI navigating to {url}")
                
                # TEMPORARY: Reduced timeouts for faster testing
                # TODO: Increase these for production (was 30000 and 10000)
                page.goto(url, wait_until="domcontentloaded", timeout=15000)  # Was: 30000
                page.wait_for_load_state("networkidle", timeout=5000)  # Was: 10000
                
                self.browser_manager._capture_browser_step(page, "Page Loaded", f"Loaded {url}")
                
                return self._ai_navigation_loop(page, extraction_goal)
                
            except Exception as e:
                logger.error("Navigation failed", error=str(e))
                return {"success": False, "error": str(e), "url": url, "extraction_goal": extraction_goal}
            finally:
                if page:
                    try:
                        page.close()
                    except:
                        pass
        
        try:
            result = await asyncio.get_event_loop().run_in_executor(self.browser_manager._executor, sync_navigate_extract)
            return CallToolResult(
                content=[TextContent(type="text", text=json.dumps(result, indent=2))],
                isError=not result.get("success", False)
            )
        except Exception as e:
            return CallToolResult(
                content=[TextContent(type="text", text=json.dumps({"success": False, "error": str(e)}))],
                isError=True
            )

    def _ai_navigation_loop(self, page, extraction_goal: str) -> Dict[str, Any]:
        """Pure AI-driven navigation loop with improved history tracking"""
        
        # Initialize comprehensive tracking
        navigation_history = {
            "steps": [],
            "extracted_companies": [],
            "visited_domains": set(),
            "failed_selectors": set(),
            "blocked_urls": set(),
            "search_queries": [],
            "successful_extractions": 0,
            "consecutive_failures": 0
        }
        
        for step in range(self.max_steps):
            try:
                logger.info("AI step", step=step + 1, url=page.url)
                
                # Extract current page structure
                try:
                    page_elements = self._extract_page_structure(page)
                except Exception as e:
                    logger.error("Page structure extraction failed", error=str(e))
                    page_elements = {
                        "url": page.url,
                        "title": "Error extracting page",
                        "body_text": "Failed to extract page content",
                        "interactive_elements": [],
                        "input_elements": []
                    }
                
                # Update domain tracking
                from urllib.parse import urlparse
                current_domain = urlparse(page.url).netloc
                navigation_history["visited_domains"].add(current_domain)
                
                # Detect login/auth pages
                page_text_lower = page_elements.get('body_text', '').lower()
                is_blocked = self._detect_blocking_page(page.url, page_text_lower, page_elements.get('title', ''))
                
                if is_blocked:
                    navigation_history["blocked_urls"].add(page.url)
                    logger.info("Blocking page detected", url=page.url)
                    self.browser_manager._capture_browser_step(page, f"Blocked Page Detected Step {step + 1}", f"Login/auth required at {page.url}")
                
                # Build comprehensive context for AI
                context = self._build_navigation_context(
                    navigation_history, 
                    current_domain, 
                    is_blocked,
                    step,
                    extraction_goal
                )
                
                # Get AI decision with full context
                ai_action = self._get_ai_action(
                    page_elements, 
                    context, 
                    page.url,
                    navigation_history
                )
                
                # Ensure AI response is valid
                if not isinstance(ai_action, dict):
                    logger.error("Invalid AI response", response_type=type(ai_action))
                    ai_action = {"action": "error", "reasoning": "Invalid AI response"}
                
                logger.info("AI decided", action=ai_action.get("action"), reasoning=ai_action.get("reasoning", "")[:300])
                
                # Capture screenshot and send update with AI reasoning
                self.browser_manager._capture_browser_step(
                    page, 
                    f"AI Step {step + 1}", 
                    f"Action: {ai_action.get('action')} - Reasoning: {ai_action.get('reasoning', '')}"
                )
                
                # Record step
                step_record = {
                    "step": step + 1,
                    "url": page.url,
                    "domain": current_domain,
                    "action": ai_action.get("action"),
                    "reasoning": ai_action.get("reasoning", "")
                }
                
                # Execute action and update history
                if ai_action.get("action") == "complete":
                    navigation_history["steps"].append(step_record)
                    self.browser_manager._capture_browser_step(page, f"Complete Action Step {step + 1}", "Task completed")
                    break
                
                elif ai_action.get("action") == "extract":
                    result = self._execute_action(page, ai_action)
                    step_record["result"] = result
                    
                    if result.get("success"):
                        extracted = result.get("extracted_data", {})
                        if extracted:
                            navigation_history["extracted_companies"].append(extracted)
                            navigation_history["successful_extractions"] += 1
                            navigation_history["consecutive_failures"] = 0
                            logger.info("Extraction successful", company=extracted.get("company_name", "Unknown"))
                            
                            # Capture screenshot for successful extraction
                            self.browser_manager._capture_browser_step(
                                page, 
                                f"Extraction Step {step + 1}", 
                                f"Extracted: {extracted.get('company_name', 'Unknown')} - Data: {json.dumps(extracted, indent=2)[:200]}"
                            )
                    else:
                        navigation_history["consecutive_failures"] += 1
                        self.browser_manager._capture_browser_step(page, f"Extraction Failed Step {step + 1}", f"Error: {result.get('error', 'Unknown')}")
                    
                    navigation_history["steps"].append(step_record)
                
                elif ai_action.get("action") == "type":
                    # Track search queries
                    search_text = ai_action.get("text", "")
                    if search_text:
                        navigation_history["search_queries"].append({
                            "query": search_text,
                            "step": step + 1,
                            "url": page.url
                        })
                    
                    result = self._execute_action(page, ai_action)
                    step_record["result"] = result
                    
                    if result.get("success"):
                        navigation_history["consecutive_failures"] = 0
                        self.browser_manager._capture_browser_step(page, f"Type Action Step {step + 1}", f"Typed '{search_text}' into {ai_action.get('selector')} successfully")
                    else:
                        navigation_history["consecutive_failures"] += 1
                        navigation_history["failed_selectors"].add(ai_action.get("selector", ""))
                        self.browser_manager._capture_browser_step(page, f"Type Failed Step {step + 1}", f"Error: {result.get('error', 'Unknown')}")
                    
                    navigation_history["steps"].append(step_record)
                
                elif ai_action.get("action") in ["click", "navigate", "wait"]:
                    result = self._execute_action(page, ai_action)
                    step_record["result"] = result
                    
                    if result.get("success"):
                        navigation_history["consecutive_failures"] = 0
                        if ai_action.get("action") == "navigate":
                            # Give page time to load
                            try:
                                page.wait_for_load_state("domcontentloaded", timeout=5000)
                                self.browser_manager._capture_browser_step(page, f"Navigate Success Step {step + 1}", f"Navigated to {ai_action.get('url')} and loaded")
                            except:
                                self.browser_manager._capture_browser_step(page, f"Navigate Partial Step {step + 1}", f"Navigated to {ai_action.get('url')} but load wait failed")
                        elif ai_action.get("action") == "click":
                            self.browser_manager._capture_browser_step(page, f"Click Success Step {step + 1}", f"Clicked {ai_action.get('selector')} successfully")
                        elif ai_action.get("action") == "wait":
                            self.browser_manager._capture_browser_step(page, f"Wait Success Step {step + 1}", "Wait completed")
                    else:
                        navigation_history["consecutive_failures"] += 1
                        if ai_action.get("action") == "click":
                            navigation_history["failed_selectors"].add(ai_action.get("selector", ""))
                        self.browser_manager._capture_browser_step(page, f"{ai_action.get('action').capitalize()} Failed Step {step + 1}", f"Error: {result.get('error', 'Unknown')}")
                    
                    navigation_history["steps"].append(step_record)
                
                else:
                    step_record["result"] = {"success": False, "error": f"Unknown action: {ai_action.get('action')}"}
                    navigation_history["steps"].append(step_record)
                    self.browser_manager._capture_browser_step(page, f"Unknown Action Step {step + 1}", f"Unknown action: {ai_action.get('action')}")
                    if ai_action.get("action") == "error":
                        break
                
                # Emergency stop conditions
                if navigation_history["consecutive_failures"] >= 5:
                    logger.warning("Too many consecutive failures, stopping")
                    self.browser_manager._capture_browser_step(page, "Emergency Stop", "Too many consecutive failures")
                    break
                
                if len(navigation_history["extracted_companies"]) >= 10:
                    logger.info("Reached extraction limit, completing")
                    self.browser_manager._capture_browser_step(page, "Extraction Limit Reached", "Reached maximum extractions")
                    break
                
            except Exception as e:
                logger.error("Step failed", step=step + 1, error=str(e))
                navigation_history["steps"].append({
                    "step": step + 1,
                    "error": str(e)
                })
                navigation_history["consecutive_failures"] += 1
                self.browser_manager._capture_browser_step(page, f"Step Failed {step + 1}", f"Error: {str(e)[:200]}")
                
                if navigation_history["consecutive_failures"] >= 3:
                    break
        
        # Build final result
        result = {
            "success": len(navigation_history["extracted_companies"]) > 0,
            "url": page.url,
            "extraction_goal": extraction_goal,
            "steps_taken": len(navigation_history["steps"]),
            "extracted_data": navigation_history["extracted_companies"],
            "domains_visited": list(navigation_history["visited_domains"]),
            "search_queries": navigation_history["search_queries"],
            "navigation_steps": navigation_history["steps"][-10:]  # Last 10 steps for brevity
        }
        
        self.browser_manager._capture_browser_step(
            page, 
            "Complete", 
            f"Extracted {len(navigation_history['extracted_companies'])} companies in {len(navigation_history['steps'])} steps"
        )
        
        return result

    def _detect_blocking_page(self, url: str, page_text: str, title: str) -> bool:
        """Detect if current page is blocking (login, auth, etc)"""
        url_lower = url.lower()
        title_lower = title.lower()
        
        # Skip detection for search engines
        if any(se in url_lower for se in ['google.com', 'bing.com', 'yahoo.com', 'duckduckgo.com']):
            return False
        
        # Login/auth indicators
        blocking_keywords = [
            'sign in', 'log in', 'login', 'sign up', 'signup', 
            'create account', 'register', 'authenticate', 'password'
        ]
        
        blocking_url_patterns = ['login', 'signin', 'auth', 'register', 'signup']
        
        # Check for blocking indicators
        has_blocking_text = any(kw in page_text for kw in blocking_keywords)
        has_blocking_url = any(pattern in url_lower for pattern in blocking_url_patterns)
        has_blocking_title = any(kw in title_lower for kw in blocking_keywords)
        
        return has_blocking_text or has_blocking_url or has_blocking_title

    def _build_navigation_context(self, history: Dict, current_domain: str, is_blocked: bool, 
                                 step: int, goal: str) -> str:
        """Build comprehensive context for AI decision making"""
        
        # Calculate statistics
        total_searches = len(history["search_queries"])
        total_extractions = history["successful_extractions"]
        domains_count = len(history["visited_domains"])
        
        # Build search history summary
        search_summary = ""
        if history["search_queries"]:
            recent_searches = history["search_queries"][-3:]
            search_terms = [s["query"] for s in recent_searches]
            search_summary = f"Recent searches: {', '.join(search_terms)}"
        
        # Build extraction summary
        extraction_summary = ""
        if history["extracted_companies"]:
            company_names = [c.get("company_name", "Unknown") for c in history["extracted_companies"][-3:]]
            extraction_summary = f"Already extracted: {', '.join(company_names)}"
        
        # Domain visit frequency
        domain_visits = {}
        for step_record in history["steps"]:
            domain = step_record.get("domain", "")
            if domain:
                domain_visits[domain] = domain_visits.get(domain, 0) + 1
        
        # Current domain status
        current_visits = domain_visits.get(current_domain, 0)
        domain_warning = ""
        if current_visits >= 2:
            domain_warning = f"⚠️ VISITED {current_domain} {current_visits} TIMES! "
        
        # Blocking status
        blocking_warning = ""
        if is_blocked:
            blocking_warning = f"🔐 LOGIN/AUTH REQUIRED on {current_domain}! MUST navigate away! "
            history["blocked_urls"].add(current_domain)
        
        # Failed attempts summary
        failed_summary = ""
        if history["failed_selectors"]:
            failed_summary = f"Failed selectors: {len(history['failed_selectors'])} "
        if history["blocked_urls"]:
            blocked_domains = [urlparse(u).netloc for u in history["blocked_urls"]]
            failed_summary += f"Blocked sites: {', '.join(set(blocked_domains))} "
        
        # Progress indicator
        if step >= 10 and total_extractions == 0:
            progress_warning = "🚨 NO PROGRESS! Change strategy completely! "
        elif history["consecutive_failures"] >= 3:
            progress_warning = "🚨 MULTIPLE FAILURES! Try different approach! "
        else:
            progress_warning = ""
        
        # Build final context
        context = f"""NAVIGATION STATUS:
Step {step + 1}/{self.max_steps}
Goal: {goal}

PROGRESS:
- Domains visited: {domains_count}
- Searches performed: {total_searches}
- Companies extracted: {total_extractions}
- Consecutive failures: {history['consecutive_failures']}

{search_summary}
{extraction_summary}
{failed_summary}

CURRENT SITUATION:
{domain_warning}{blocking_warning}{progress_warning}

DECISION PRIORITY:
1. If blocked/login page → Navigate to Google or try different site
2. If on Google without search → Type search query immediately  
3. If already searched this term → Use completely different keywords
4. If extracted from this site → Move to new site
5. If multiple failures → Change strategy completely
6. If good data available → Extract it now"""
        
        return context

    def _extract_page_structure(self, page) -> Dict[str, Any]:
        """Extract comprehensive page structure for AI analysis"""
        try:
            # Get page text
            body_text = page.inner_text('body')[:4000]
            
            # Extract clickable elements with better selectors
            interactive_elements = []
            clickable = page.query_selector_all('button, a, input[type="submit"], [role="button"], [onclick]')
            
            for i, elem in enumerate(clickable[:20]):  # Increase limit for better coverage
                try:
                    if not elem:
                        continue
                    
                    text = elem.inner_text().strip()[:100]
                    tag = elem.tag_name.lower()
                    elem_id = elem.get_attribute('id')
                    elem_name = elem.get_attribute('name')
                    elem_class = elem.get_attribute('class')
                    href = elem.get_attribute('href') if tag == 'a' else None
                    elem_type = elem.get_attribute('type')
                    
                    # Build reliable selector
                    if elem_id:
                        selector = f"#{elem_id}"
                    elif elem_name:
                        selector = f"{tag}[name='{elem_name}']"
                    elif href:
                        # Clean href for selector
                        clean_href = href.replace('"', '\\"')
                        selector = f"a[href='{clean_href}']"
                    elif text and len(text) > 2:
                        # Text-based selector
                        clean_text = text.replace('"', '\\"').replace('\n', ' ')[:30]
                        selector = f"{tag}:has-text('{clean_text}')"
                    elif elem_class:
                        first_class = elem_class.split()[0]
                        selector = f"{tag}.{first_class}:nth-of-type({i+1})"
                    else:
                        selector = f"{tag}:nth-of-type({i+1})"
                    
                    interactive_elements.append({
                        "text": text,
                        "tag": tag,
                        "selector": selector,
                        "href": href[:100] if href else None,
                        "type": elem_type
                    })
                except:
                    continue
            
            # Extract input elements
            input_elements = []
            inputs = page.query_selector_all('input, textarea, select')
            
            for i, elem in enumerate(inputs[:15]):
                try:
                    tag = elem.tag_name.lower()
                    input_type = elem.get_attribute('type') or 'text'
                    placeholder = elem.get_attribute('placeholder') or ''
                    name = elem.get_attribute('name') or ''
                    elem_id = elem.get_attribute('id')
                    value = elem.get_attribute('value') or ''
                    
                    # Build selector
                    if elem_id:
                        selector = f"#{elem_id}"
                    elif name:
                        selector = f"{tag}[name='{name}']"
                    else:
                        selector = f"{tag}[type='{input_type}']:nth-of-type({i+1})"
                    
                    # Mark search inputs
                    is_search = name in ['q', 'query', 'search'] or 'search' in placeholder.lower()
                    
                    input_elements.append({
                        "tag": tag,
                        "type": input_type,
                        "placeholder": placeholder,
                        "selector": selector,
                        "name": name,
                        "has_value": bool(value),
                        "is_search": is_search
                    })
                except:
                    continue
            
            return {
                "url": page.url,
                "title": page.title(),
                "body_text": body_text,
                "interactive_elements": interactive_elements,
                "input_elements": input_elements,
                "element_counts": {
                    "links": len([e for e in interactive_elements if e["tag"] == "a"]),
                    "buttons": len([e for e in interactive_elements if e["tag"] == "button"]),
                    "inputs": len(input_elements)
                }
            }
            
        except Exception as e:
            logger.error("Page extraction failed", error=str(e))
            return {
                "url": page.url,
                "title": "Error",
                "body_text": "",
                "interactive_elements": [],
                "input_elements": [],
                "element_counts": {}
            }

    def _get_ai_action(self, page_elements: Dict[str, Any], context: str, 
                       current_url: str, history: Dict) -> Dict[str, Any]:
        """Get AI decision with improved prompting"""
        try:
            # Build element summary
            element_summary = f"""
AVAILABLE ELEMENTS:
- Links: {page_elements.get('element_counts', {}).get('links', 0)}
- Buttons: {page_elements.get('element_counts', {}).get('buttons', 0)}
- Inputs: {page_elements.get('element_counts', {}).get('inputs', 0)}
"""
            
            # List clickable elements
            clickable_list = "\nCLICKABLE ELEMENTS:\n"
            for elem in page_elements.get('interactive_elements', [])[:10]:
                clickable_list += f"- [{elem['tag']}] '{elem['text'][:50]}' → {elem['selector']}\n"
            
            # List input elements
            input_list = "\nINPUT ELEMENTS:\n"
            for elem in page_elements.get('input_elements', [])[:10]:
                search_marker = " [SEARCH]" if elem.get('is_search') else ""
                input_list += f"- {elem['tag']} type={elem['type']} → {elem['selector']}{search_marker}\n"
            
            # Previous search terms for reference
            search_history = ""
            if history.get("search_queries"):
                terms = [q["query"] for q in history["search_queries"]]
                search_history = f"\nSEARCH HISTORY (DO NOT REPEAT): {', '.join(terms)}\n"
            
            # Extracted companies for reference
            extracted_list = ""
            if history.get("extracted_companies"):
                companies = [c.get("company_name", "Unknown") for c in history["extracted_companies"]]
                extracted_list = f"\nALREADY EXTRACTED: {', '.join(companies)}\n"
            
            prompt = f"""CURRENT PAGE: {current_url}
TITLE: {page_elements.get('title', 'Unknown')}

{context}

{search_history}
{extracted_list}

PAGE CONTENT (first 2000 chars):
{page_elements.get('body_text', '')[:2000]}

{element_summary}
{clickable_list}
{input_list}

DECISION RULES:
1. NEVER repeat a search query - check SEARCH HISTORY above
2. NEVER stay on login/auth pages - navigate away immediately
3. NEVER visit the same domain more than 2 times
4. ALWAYS extract data when you find company contact info
5. ALWAYS use textarea[name='q'] for Google search, not input
6. PREFER navigating directly to company sites over clicking search results

ALTERNATIVE SEARCH TERMS (if needed):
- "wedding planners Kenya", "party organizers Nairobi", "event coordinators Kenya"
- "conference organizers Kenya", "meeting planners Nairobi", "corporate events Nairobi"
- "event services Kenya", "event venues Kenya", "catering services Kenya"

Choose ONE action:
- extract: Found company data to extract
- type: Enter text in input/textarea
- click: Click an element
- navigate: Go to specific URL
- wait: Wait for page load
- complete: Finished task

Respond with JSON only:
{{"action": "type", "selector": "textarea[name='q']", "text": "search query", "reasoning": "why"}}
{{"action": "extract", "data_type": "company_details", "reasoning": "found XYZ company data"}}
{{"action": "navigate", "url": "https://example.com", "reasoning": "going to company site"}}
{{"action": "click", "selector": "#button", "reasoning": "clicking contact link"}}
{{"action": "complete", "reasoning": "extracted N companies successfully"}}

IMPORTANT: Return ONLY valid JSON, no other text."""
            
            # Call Gemini
            from app.services.gemini_service import gemini_service
            import concurrent.futures
            
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    self._call_gemini_sync,
                    "You are a web navigation AI. Analyze pages and decide the next action. Always respond with valid JSON only.",
                    prompt
                )
                response = future.result(timeout=30)
            
            # Parse response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                action_data = json.loads(json_match.group(0))
                
                # Ensure required fields
                if "action" not in action_data:
                    action_data["action"] = "wait"
                if "reasoning" not in action_data:
                    action_data["reasoning"] = "AI decision"
                
                return action_data
            else:
                logger.warning("No JSON in AI response", response_preview=response[:200])
                return {"action": "wait", "reasoning": "Could not parse AI response"}
                
        except Exception as e:
            logger.error("AI action failed", error=str(e))
            return {"action": "error", "error": str(e), "reasoning": f"AI failed: {str(e)}"}

    def _execute_action(self, page, action: Dict[str, Any]) -> Dict[str, Any]:
        """Execute AI decision with improved error handling"""
        try:
            action_type = action.get("action", "")
            
            if action_type == "click":
                selector = action.get("selector", "")
                if not selector:
                    return {"success": False, "error": "No selector provided"}
                
                try:
                    page.wait_for_selector(selector, timeout=5000)
                    page.click(selector)
                    page.wait_for_load_state("domcontentloaded", timeout=5000)
                    return {"success": True, "action": "click", "selector": selector}
                except Exception as e:
                    return {"success": False, "error": f"Click failed: {str(e)}"}
            
            elif action_type == "type":
                selector = action.get("selector", "")
                text = action.get("text", "")
                
                if not selector or not text:
                    return {"success": False, "error": "Missing selector or text"}
                
                try:
                    page.wait_for_selector(selector, timeout=5000)
                    page.fill(selector, text)
                    page.keyboard.press('Enter')
                    page.wait_for_load_state('networkidle', timeout=10000)
                    return {"success": True, "action": "type", "selector": selector, "text": text}
                except Exception as e:
                    return {"success": False, "error": f"Type failed: {str(e)}"}
            
            elif action_type == "navigate":
                url = action.get("url", "")
                if not url:
                    return {"success": False, "error": "No URL provided"}
                
                try:
                    # TEMPORARY: Reduced timeout for faster testing
                    page.goto(url, wait_until="domcontentloaded", timeout=15000)  # Was: 30000
                    return {"success": True, "action": "navigate", "url": url}
                except Exception as e:
                    return {"success": False, "error": f"Navigation failed: {str(e)}"}
            
            elif action_type == "extract":
                try:
                    page_text = page.inner_text('body')[:3000]
                    
                    # Extract contact information using AI
                    extraction_prompt = f"""Extract company contact details from this text:

{page_text}

Look for:
- Company name
- Email addresses
- Phone numbers
- LinkedIn profiles
- Website URLs
- Physical addresses

Return ONLY JSON:
{{"extracted_data": {{"company_name": "...", "email": "...", "phone": "...", "linkedin": "...", "website": "...", "address": "..."}}}}"""
                    
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(
                            self._call_gemini_sync,
                            "Extract company contact information and return as JSON.",
                            extraction_prompt
                        )
                        response = future.result(timeout=30)
                    
                    json_match = re.search(r'\{.*\}', response, re.DOTALL)
                    if json_match:
                        result = json.loads(json_match.group(0))
                        extracted = result.get("extracted_data", {})
                        
                        #  Clean up extracted data
                        cleaned = {}
                        for key, value in extracted.items():
                            if value and value not in ["...", "null", "None", "N/A"]:
                                cleaned[key] = value
                        
                        if cleaned:
                            return {"success": True, "action": "extract", "extracted_data": cleaned}
                        else:
                            return {"success": False, "error": "No valid data extracted"}
                    else:
                        return {"success": False, "error": "Failed to parse extraction"}
                        
                except Exception as e:
                    return {"success": False, "error": f"Extraction failed: {str(e)}"}
            
            elif action_type == "wait":
                try:
                    page.wait_for_load_state("domcontentloaded", timeout=5000)
                    return {"success": True, "action": "wait"}
                except:
                    return {"success": True, "action": "wait"}
            
            elif action_type == "complete":
                return {"success": True, "action": "complete"}
            
            else:
                return {"success": False, "error": f"Unknown action: {action_type}"}
                
        except Exception as e:
            return {"success": False, "error": f"Action execution failed: {str(e)}"}

    def _call_gemini_sync(self, system_prompt: str, user_message: str) -> str:
        """Synchronous wrapper for Gemini API calls"""
        from app.services.gemini_service import gemini_service
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(
                gemini_service.generate_agent_response(
                    system_prompt=system_prompt,
                    user_message=user_message
                )
            )
        finally:
            loop.close()
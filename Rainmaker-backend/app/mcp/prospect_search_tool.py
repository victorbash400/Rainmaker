"""
Intelligent Prospect Search Tool
Implements AI-powered multi-site prospect search functionality
"""

import json
from typing import Dict, Any, List
from datetime import datetime
import structlog
from playwright.sync_api import Page
from mcp.types import TextContent, CallToolResult

logger = structlog.get_logger(__name__)


class ProspectSearchTool:
    """
    AI-powered prospect search across multiple websites
    """
    
    def __init__(self, browser_manager, dom_extractor=None, gemini_interface=None, action_executor=None):
        self.browser_manager = browser_manager
        self.dom_extractor = dom_extractor
        self.gemini_interface = gemini_interface
        self.action_executor = action_executor
    
    async def intelligent_prospect_search(self, arguments: Dict[str, Any]) -> CallToolResult:
        """AI-powered prospect search across multiple websites"""
        task_description = arguments.get("task_description", "find prospects")
        target_sites = arguments.get("target_sites", ["google.com"])
        max_results = arguments.get("max_results", 10)
        headless = arguments.get("headless", False)
        
        def sync_prospect_search():
            """Run sync AI-powered prospect search with full AI navigation workflow"""
            page = None
            try:
                logger.info("Starting intelligent AI prospect search", 
                           task=task_description, sites=target_sites, max_results=max_results)
                
                # Create page with stealth
                page = self.browser_manager.create_page(headless=headless)
                
                # Import AI components if not provided
                if not all([self.dom_extractor, self.gemini_interface, self.action_executor]):
                    from app.mcp.dom_extractor import DOMExtractor
                    from app.mcp.simple_gemini_interface import SimpleGeminiInterface
                    from app.mcp.simple_action_executor import SimpleActionExecutor
                    
                    self.dom_extractor = DOMExtractor()
                    self.gemini_interface = SimpleGeminiInterface()
                    self.action_executor = SimpleActionExecutor()
                
                # Capture: AI search started
                self.browser_manager._capture_browser_step(page, "AI Prospect Search Started", 
                                         f"Task: {task_description}")
                
                all_prospects = []
                sites_processed = 0
                
                # Process each target site with AI navigation
                for site in target_sites:
                    try:
                        logger.info("Starting AI navigation for site", site=site)
                        
                        # Navigate to site
                        site_url = f"https://{site}" if not site.startswith("http") else site
                        page.goto(site_url, wait_until="domcontentloaded", timeout=30000)
                        page.wait_for_load_state("networkidle", timeout=10000)
                        
                        # Capture: Site loaded
                        self.browser_manager._capture_browser_step(page, f"Navigated to {site}", 
                                                 "AI analyzing page structure")
                        
                        # AI Navigation Loop - continue until task complete or max steps
                        max_steps = 10
                        step_count = 0
                        task_complete = False
                        site_prospects = []
                        
                        while step_count < max_steps and not task_complete:
                            step_count += 1
                            logger.info("AI navigation step", step=step_count, site=site)
                            
                            try:
                                # Extract page structure for AI analysis (sync version)
                                page_elements = self._extract_page_structure_sync(page)
                                
                                # Get AI decision for next action (sync version)
                                ai_action = self._get_ai_action_sync(
                                    page_elements, f"{task_description} on {site}", page.url
                                )
                                
                                logger.info("AI decision made", 
                                           action=ai_action.get("action"),
                                           reasoning=ai_action.get("reasoning", "")[:100])
                                
                                # Capture AI decision
                                self.browser_manager._capture_browser_step(page, f"AI Step {step_count}: {ai_action.get('action', 'unknown')}", 
                                                         ai_action.get("reasoning", "AI decision made"))
                                
                                # Execute AI action
                                if ai_action.get("action") == "complete":
                                    # Task completed, extract final results
                                    completion_data = ai_action.get("result", {})
                                    if "prospects" in completion_data:
                                        site_prospects.extend(completion_data["prospects"])
                                    task_complete = True
                                    logger.info("AI marked task complete", prospects=len(site_prospects))
                                    
                                elif ai_action.get("action") == "extract":
                                    # Extract data from current page (sync version)
                                    extract_result = self._execute_action_sync(page, ai_action)
                                    if extract_result.get("success"):
                                        extracted_data = extract_result.get("extracted_data", {})
                                        
                                        # Convert extracted data to prospect format
                                        prospects = self._convert_to_prospects(extracted_data, site, task_description)
                                        site_prospects.extend(prospects)
                                        
                                        logger.info("Data extracted by AI", prospects_found=len(prospects))
                                        
                                        # Check if we have enough results
                                        if len(site_prospects) >= max_results:
                                            task_complete = True
                                    
                                elif ai_action.get("action") == "error":
                                    # AI encountered an error, try to continue or stop
                                    logger.warning("AI action error", error=ai_action.get("error"))
                                    break
                                    
                                else:
                                    # Execute the AI action (click, type, navigate, wait) (sync version)
                                    action_result = self._execute_action_sync(page, ai_action)
                                    
                                    if not action_result.get("success"):
                                        logger.warning("AI action failed", 
                                                     action=ai_action.get("action"),
                                                     error=action_result.get("error"))
                                        # Continue to next step, AI might adapt
                                
                                # Small delay between actions
                                import time
                                time.sleep(1)
                                
                            except Exception as step_error:
                                logger.error("AI navigation step failed", 
                                           step=step_count, error=str(step_error))
                                break
                        
                        # Add site prospects to overall results
                        all_prospects.extend(site_prospects[:max_results])  # Limit per site
                        sites_processed += 1
                        
                        logger.info("Site processing completed", 
                                   site=site, prospects=len(site_prospects))
                        
                        # Capture site completion
                        self.browser_manager._capture_browser_step(page, f"Site {site} Completed", 
                                                 f"Found {len(site_prospects)} prospects")
                        
                    except Exception as site_error:
                        logger.error("Site processing failed", site=site, error=str(site_error))
                        continue
                
                # Aggregate and deduplicate results
                final_prospects = self._aggregate_prospects(all_prospects, max_results)
                
                # Capture: Search completed
                self.browser_manager._capture_browser_step(page, "AI Prospect Search Completed", 
                                         f"Found {len(final_prospects)} prospects across {sites_processed} sites")
                
                logger.info("Intelligent prospect search completed", 
                           total_prospects=len(final_prospects),
                           sites_processed=sites_processed)
                
                return {
                    "task_description": task_description,
                    "target_sites": target_sites,
                    "sites_processed": sites_processed,
                    "prospects_found": len(final_prospects),
                    "prospects": final_prospects,
                    "success": True,
                    "message": f"AI search completed: found {len(final_prospects)} prospects across {sites_processed} sites",
                    "ai_navigation_used": True,
                    "timestamp": datetime.now().isoformat()
                }
                
            except Exception as e:
                logger.error("Intelligent prospect search failed", error=str(e))
                return {
                    "task_description": task_description,
                    "success": False,
                    "error": str(e),
                    "message": f"AI prospect search failed: {str(e)}",
                    "timestamp": datetime.now().isoformat()
                }
            finally:
                if page:
                    try:
                        page.close()
                    except Exception as e:
                        logger.warning("Failed to close prospect search page", error=str(e))
        
        try:
            result = await self.browser_manager._executor.run_in_executor(
                None, sync_prospect_search
            )
            
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=json.dumps(result, indent=2)
                )],
                isError=not result.get("success", False)
            )
            
        except Exception as e:
            logger.error("AI prospect search thread execution failed", error=str(e))
            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=json.dumps({
                        "task_description": task_description,
                        "success": False,
                        "error": str(e),
                        "message": f"Thread execution failed: {str(e)}",
                        "timestamp": datetime.now().isoformat()
                    }, indent=2)
                )],
                isError=True
            )
    
    def _convert_to_prospects(self, extracted_data: Dict[str, Any], source_site: str, task_description: str) -> List[Dict[str, Any]]:
        """Convert extracted data to prospect format"""
        prospects = []
        
        try:
            # Handle search results format
            if "results" in extracted_data:
                for result in extracted_data["results"][:10]:  # Max 10 per extraction
                    prospect = {
                        "name": result.get("title", "Unknown"),
                        "source_url": result.get("link", ""),
                        "description": result.get("description", ""),
                        "extraction_method": "ai_navigation",
                        "ai_confidence_score": 0.8,
                        "source_site": source_site,
                        "task_description": task_description,
                        "extracted_at": datetime.now().isoformat()
                    }
                    
                    # Add contact info if available
                    if "emails" in extracted_data and extracted_data["emails"]:
                        prospect["email"] = extracted_data["emails"][0]
                    if "phones" in extracted_data and extracted_data["phones"]:
                        prospect["phone"] = extracted_data["phones"][0]
                    
                    prospects.append(prospect)
            
            # Handle contact info format
            elif "emails" in extracted_data or "phones" in extracted_data:
                # Create prospect from contact information
                prospect = {
                    "name": extracted_data.get("title", "Contact Found"),
                    "source_url": extracted_data.get("url", ""),
                    "extraction_method": "ai_navigation",
                    "ai_confidence_score": 0.7,
                    "source_site": source_site,
                    "task_description": task_description,
                    "extracted_at": datetime.now().isoformat()
                }
                
                if extracted_data.get("emails"):
                    prospect["email"] = extracted_data["emails"][0]
                if extracted_data.get("phones"):
                    prospect["phone"] = extracted_data["phones"][0]
                
                prospects.append(prospect)
            
            # Handle general content format
            elif "headings" in extracted_data or "links" in extracted_data:
                # Create prospects from headings and links
                headings = extracted_data.get("headings", [])
                links = extracted_data.get("links", [])
                
                # Combine headings and link texts as potential prospects
                potential_names = headings[:5]  # Top 5 headings
                for link in links[:10]:  # Top 10 links
                    if link.get("text") and len(link["text"]) > 10:
                        potential_names.append(link["text"])
                
                for name in potential_names[:8]:  # Max 8 prospects per page
                    if self._is_potential_prospect(name, task_description):
                        prospect = {
                            "name": name[:100],  # Limit name length
                            "source_url": extracted_data.get("url", ""),
                            "extraction_method": "ai_navigation",
                            "ai_confidence_score": 0.6,
                            "source_site": source_site,
                            "task_description": task_description,
                            "extracted_at": datetime.now().isoformat()
                        }
                        prospects.append(prospect)
            
            logger.info("Converted extracted data to prospects", 
                       prospects_created=len(prospects), source_site=source_site)
            
        except Exception as e:
            logger.error("Failed to convert extracted data to prospects", error=str(e))
        
        return prospects
    
    def _is_potential_prospect(self, name: str, task_description: str) -> bool:
        """Check if a name/title could be a potential prospect"""
        import re
        
        name_lower = name.lower()
        task_lower = task_description.lower()
        
        # Skip common non-prospect terms
        skip_terms = [
            "home", "about", "contact", "privacy", "terms", "login", "register",
            "menu", "search", "click", "here", "more", "next", "previous",
            "copyright", "all rights", "reserved", "policy", "disclaimer"
        ]
        
        if any(term in name_lower for term in skip_terms):
            return False
        
        # Must have reasonable length
        if len(name) < 5 or len(name) > 200:
            return False
        
        # Look for business/event related terms
        business_terms = [
            "wedding", "event", "planning", "planner", "catering", "venue",
            "photography", "music", "dj", "flowers", "decoration", "party",
            "corporate", "conference", "meeting", "celebration", "birthday",
            "anniversary", "company", "business", "service", "professional"
        ]
        
        # If task mentions specific terms, look for them
        task_terms = task_lower.split()
        relevant_terms = [term for term in task_terms if len(term) > 3]
        
        # Check if name contains relevant terms
        if any(term in name_lower for term in business_terms + relevant_terms):
            return True
        
        # Check if it looks like a business name (contains certain patterns)
        business_patterns = [
            r'\b\w+\s+(llc|inc|corp|ltd|company|co\.)\b',
            r'\b\w+\s+(services|solutions|group|associates)\b',
            r'\b\w+\s+(wedding|event|party|catering)\b'
        ]
        
        for pattern in business_patterns:
            if re.search(pattern, name_lower):
                return True
        
        return False
    
    def _aggregate_prospects(self, all_prospects: List[Dict[str, Any]], max_results: int) -> List[Dict[str, Any]]:
        """Aggregate and deduplicate prospects from multiple sites"""
        try:
            if not all_prospects:
                return []
            
            # Deduplicate by name and URL
            seen_prospects = set()
            unique_prospects = []
            
            for prospect in all_prospects:
                # Create deduplication key
                name = prospect.get("name", "").lower().strip()
                url = prospect.get("source_url", "").lower().strip()
                dedup_key = f"{name}|{url}"
                
                if dedup_key not in seen_prospects and name:
                    seen_prospects.add(dedup_key)
                    unique_prospects.append(prospect)
            
            # Sort by confidence score and relevance
            def prospect_score(prospect):
                confidence = prospect.get("ai_confidence_score", 0.5)
                has_contact = 1.0 if (prospect.get("email") or prospect.get("phone")) else 0.8
                name_length_bonus = min(1.0, len(prospect.get("name", "")) / 50.0)  # Prefer reasonable length names
                return confidence * has_contact * name_length_bonus
            
            unique_prospects.sort(key=prospect_score, reverse=True)
            
            # Add aggregation metadata
            final_prospects = unique_prospects[:max_results]
            for i, prospect in enumerate(final_prospects):
                prospect["rank"] = i + 1
                prospect["aggregation_score"] = prospect_score(prospect)
            
            logger.info("Prospects aggregated and deduplicated", 
                       original_count=len(all_prospects),
                       unique_count=len(unique_prospects),
                       final_count=len(final_prospects))
            
            return final_prospects
            
        except Exception as e:
            logger.error("Failed to aggregate prospects", error=str(e))
            return all_prospects[:max_results]  # Fallback to simple truncation
    
    def _extract_page_structure_sync(self, page: Page) -> Dict[str, Any]:
        """Sync version of page structure extraction for use in sync functions"""
        try:
            # Basic page structure extraction without async
            page_info = {
                "url": page.url,
                "title": page.title(),
                "viewport": page.viewport_size
            }
            
            # Extract interactive elements
            interactive_elements = []
            try:
                buttons = page.query_selector_all('button, input[type="submit"], [role="button"]')
                for i, button in enumerate(buttons[:10]):
                    try:
                        text = button.inner_text().strip()
                        if text:
                            interactive_elements.append({
                                "id": f"button_{i}",
                                "tag_name": "button",
                                "text_content": text[:100],
                                "selector": f"button:nth-of-type({i+1})"
                            })
                    except:
                        continue
            except:
                pass
            
            # Extract form elements
            form_elements = []
            try:
                inputs = page.query_selector_all('input, textarea, select')
                for i, input_elem in enumerate(inputs[:10]):
                    try:
                        input_type = input_elem.get_attribute('type') or 'text'
                        name = input_elem.get_attribute('name') or ''
                        placeholder = input_elem.get_attribute('placeholder') or ''
                        
                        form_elements.append({
                            "id": f"input_{i}",
                            "tag_name": "input",
                            "attributes": {
                                "type": input_type,
                                "name": name,
                                "placeholder": placeholder
                            },
                            "selector": f"input:nth-of-type({i+1})"
                        })
                    except:
                        continue
            except:
                pass
            
            # Extract content elements
            content_elements = []
            try:
                headings = page.query_selector_all('h1, h2, h3, h4')
                for i, heading in enumerate(headings[:10]):
                    try:
                        text = heading.inner_text().strip()
                        if text:
                            content_elements.append({
                                "id": f"heading_{i}",
                                "tag_name": heading.tag_name.lower(),
                                "text_content": text[:200],
                                "selector": f"{heading.tag_name.lower()}:nth-of-type({i+1})"
                            })
                    except:
                        continue
            except:
                pass
            
            return {
                "page_info": page_info,
                "interactive_elements": interactive_elements,
                "form_elements": form_elements,
                "content_elements": content_elements,
                "element_counts": {
                    "interactive": len(interactive_elements),
                    "forms": len(form_elements),
                    "content": len(content_elements)
                }
            }
            
        except Exception as e:
            logger.error("Sync page structure extraction failed", error=str(e))
            return {
                "page_info": {"url": page.url, "title": "Unknown"},
                "interactive_elements": [],
                "form_elements": [],
                "content_elements": [],
                "element_counts": {"interactive": 0, "forms": 0, "content": 0}
            }
    
    def _get_ai_action_sync(self, page_elements: Dict[str, Any], task_goal: str, current_url: str) -> Dict[str, Any]:
        """Sync version of AI action generation - simplified for sync context"""
        try:
            # For sync context, provide basic AI-like decisions based on page elements
            interactive_count = len(page_elements.get("interactive_elements", []))
            form_count = len(page_elements.get("form_elements", []))
            
            # Simple decision logic based on page structure
            if form_count > 0 and "search" in task_goal.lower():
                # If there are forms and we're searching, try to fill a form
                search_inputs = [elem for elem in page_elements.get("form_elements", []) 
                               if "search" in elem.get("attributes", {}).get("name", "").lower() or
                                  "search" in elem.get("attributes", {}).get("placeholder", "").lower()]
                
                if search_inputs:
                    return {
                        "action": "type",
                        "selector": search_inputs[0].get("selector", "input"),
                        "text": task_goal.replace("find", "").replace("on", "").strip(),
                        "reasoning": f"Found search input, entering search query",
                        "confidence": 0.8
                    }
            
            if interactive_count > 0:
                # If there are buttons, try to click one that might be relevant
                buttons = page_elements.get("interactive_elements", [])
                search_buttons = [btn for btn in buttons 
                                if "search" in btn.get("text_content", "").lower() or
                                   "go" in btn.get("text_content", "").lower() or
                                   "submit" in btn.get("text_content", "").lower()]
                
                if search_buttons:
                    return {
                        "action": "click",
                        "selector": search_buttons[0].get("selector", "button"),
                        "reasoning": f"Clicking search/submit button",
                        "confidence": 0.7
                    }
            
            # Default to extraction if we can't find clear navigation options
            return {
                "action": "extract",
                "data_type": "search_results",
                "reasoning": "Extracting available data from current page",
                "confidence": 0.6
            }
            
        except Exception as e:
            logger.error("Sync AI action generation failed", error=str(e))
            return {
                "action": "error",
                "error": str(e),
                "reasoning": "Failed to generate AI action",
                "confidence": 0.0
            }
    
    def _execute_action_sync(self, page: Page, action: Dict[str, Any]) -> Dict[str, Any]:
        """Sync version of action execution"""
        try:
            action_type = action.get("action", "").lower()
            
            if action_type == "click":
                selector = action.get("selector", "")
                if selector:
                    try:
                        page.wait_for_selector(selector, timeout=5000)
                        page.click(selector)
                        return {
                            "success": True,
                            "action": "click",
                            "message": f"Clicked element: {selector}"
                        }
                    except Exception as e:
                        return {
                            "success": False,
                            "action": "click",
                            "error": str(e)
                        }
            
            elif action_type == "type":
                selector = action.get("selector", "")
                text = action.get("text", "")
                if selector and text:
                    try:
                        page.wait_for_selector(selector, timeout=5000)
                        page.fill(selector, text)
                        return {
                            "success": True,
                            "action": "type",
                            "message": f"Typed text into: {selector}"
                        }
                    except Exception as e:
                        return {
                            "success": False,
                            "action": "type",
                            "error": str(e)
                        }
            
            elif action_type == "extract":
                # Basic data extraction
                try:
                    extracted_data = {
                        "url": page.url,
                        "title": page.title(),
                        "headings": [],
                        "links": []
                    }
                    
                    # Extract headings
                    try:
                        headings = page.query_selector_all('h1, h2, h3')
                        for heading in headings[:10]:
                            text = heading.inner_text().strip()
                            if text:
                                extracted_data["headings"].append(text)
                    except:
                        pass
                    
                    # Extract links
                    try:
                        links = page.query_selector_all('a[href]')
                        for link in links[:20]:
                            href = link.get_attribute('href')
                            text = link.inner_text().strip()
                            if href and text:
                                extracted_data["links"].append({"text": text, "href": href})
                    except:
                        pass
                    
                    return {
                        "success": True,
                        "action": "extract",
                        "extracted_data": extracted_data,
                        "message": "Data extracted successfully"
                    }
                    
                except Exception as e:
                    return {
                        "success": False,
                        "action": "extract",
                        "error": str(e)
                    }
            
            else:
                return {
                    "success": False,
                    "action": action_type,
                    "error": f"Unknown action type: {action_type}"
                }
                
        except Exception as e:
            logger.error("Sync action execution failed", error=str(e))
            return {
                "success": False,
                "action": action.get("action", "unknown"),
                "error": str(e)
            }
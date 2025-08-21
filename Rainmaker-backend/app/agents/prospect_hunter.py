"""
Simple Prospect Hunter Agent - Test playwright functionality through MCP server
"""

import json
import structlog
from typing import Dict, List, Any
from dataclasses import dataclass

from app.core.state import RainmakerState, ProspectData
from app.mcp.playwright_scraper import simple_browser_mcp
from app.mcp.enhanced_playwright_mcp import enhanced_browser_mcp, set_workflow_id

logger = structlog.get_logger(__name__)


@dataclass
class HuntingResults:
    """Simple results from prospect hunting test"""
    prospects_found: int
    discovered_prospect_ids: List[int]
    confidence_score: float
    search_summary: str


class ProspectHunterAgent:
    """Simple prospect hunter that tests playwright MCP server by searching for tomato"""
    
    def __init__(self):
        pass
        
    async def hunt_prospects(self, state: RainmakerState, session_id: str = None) -> RainmakerState:
        """Hunt for prospects using enhanced AI navigation"""
        workflow_id = state.get("workflow_id")
        logger.info("Starting prospect hunting with AI navigation", workflow_id=workflow_id)
        
        try:
            # Extract campaign targeting information from planner data structure
            # Try multiple field names to handle different data structures from planner
            event_types = (
                state.get("event_types_focus", []) or 
                state.get("event_types", []) or 
                state.get("event_types_to_target", []) or
                ["events"]  # fallback
            )
            
            # Extract geographic information from various possible fields
            geographic_focus = state.get("geographic_focus", [])
            geographic_location = state.get("geographic_location_to_search", [])
            geographic_regions = state.get("geographic_regions", [])
            
            # Combine all location data
            location = []
            if isinstance(geographic_focus, list):
                location.extend(geographic_focus)
            elif geographic_focus:
                location.append(geographic_focus)
                
            if isinstance(geographic_location, list):
                location.extend(geographic_location)
            elif geographic_location:
                location.append(geographic_location)
                
            if isinstance(geographic_regions, list):
                location.extend(geographic_regions)
            elif geographic_regions:
                location.append(geographic_regions)
            
            # Remove duplicates and empty values
            location = list(set([loc for loc in location if loc and loc.strip()]))
            if not location:
                location = [""]  # fallback
            
            # Extract target profile information
            target_profile = state.get("target_profile", {})
            
            logger.info("Hunting prospects with planner data", 
                       event_types=event_types, 
                       location=location,
                       target_profile=target_profile,
                       state_keys=list(state.keys()))
            
            # Build search goal from campaign parameters
            search_goal = self._build_search_goal(event_types, location, target_profile)
            
            # Use enhanced AI navigation to find prospects
            prospects_data = await self._hunt_with_ai_navigation(workflow_id, search_goal, session_id)
            
            # Process and structure the results
            prospects_found = len(prospects_data.get("contacts", []))
            
            if prospects_found > 0:
                logger.info("Prospect hunting successful", prospects_found=prospects_found)
                search_summary = f"AI hunting SUCCESSFUL - found {prospects_found} prospects: {prospects_data.get('summary', '')}"
                confidence_score = min(0.9, 0.5 + (prospects_found * 0.1))  # Higher confidence with more prospects
            else:
                logger.warning("No prospects found")
                search_summary = "AI hunting completed but no prospects found"
                confidence_score = 0.2
            
            # Update state with results
            state["hunter_results"] = HuntingResults(
                prospects_found=prospects_found,
                discovered_prospect_ids=list(range(prospects_found)),  # Mock IDs for now
                confidence_score=confidence_score,
                search_summary=search_summary
            )
            
            # Store detailed prospect data for enrichment agent
            state["raw_prospect_data"] = prospects_data
            state["current_stage"] = "hunting_completed"
            state["completed_stages"].append("hunting")
            
            logger.info("Prospect hunting completed", 
                       success=prospects_found > 0,
                       prospects_found=prospects_found)
            
            # Check if workflow was paused for manual login - if so, DON'T close browser
            paused_for_login = prospects_data.get("paused_for_login", False)
            
            if paused_for_login:
                logger.info("🔐 Browser session kept open for manual login - NOT closing browser", 
                           workflow_id=workflow_id,
                           resume_endpoint=prospects_data.get("resume_endpoint"))
                # Set workflow to PAUSED state
                from app.core.state import WorkflowStage
                state["current_stage"] = WorkflowStage.PAUSED
                state["login_pause_info"] = {
                    "paused_for_login": True,
                    "workflow_id": prospects_data.get("workflow_id"),
                    "site_name": prospects_data.get("site_name"),
                    "resume_endpoint": prospects_data.get("resume_endpoint"),
                    "message": prospects_data.get("message")
                }
            else:
                # Browser is intentionally not closed here if the workflow is not paused.
                # The browser context is managed by the orchestrator/workflow runner,
                # which will handle the cleanup after the entire workflow is complete.
                # This prevents premature closing of the browser if other agents need it.
                logger.info("Browser session intentionally left open for workflow completion.")
            
            return state
            
        except Exception as e:
            logger.error("Prospect hunting failed", error=str(e))
            state["errors"].append({
                "agent": "prospect_hunter",
                "error": str(e),
                "stage": "hunting"
            })
            return state
    
    def _build_search_goal(self, event_types: List[str], location: List[str], target_profile: Dict[str, Any]) -> str:
        """Build AI search goal from campaign parameters"""
        # Extract target details from target_profile
        industries = target_profile.get("industries", [])
        company_sizes = target_profile.get("company_sizes", [])
        job_titles = target_profile.get("job_titles", [])
        
        # Build location string from the provided location data
        location_str = ", ".join([loc for loc in location if loc and loc != "unknown" and loc.strip()])
        
        # Build industry/event context from the provided event types
        event_context = " or ".join([evt for evt in event_types if evt and evt != "unknown" and evt.strip()])
        if not event_context:
            event_context = "event"
        
        # Build professional context
        professional_context = ""
        if job_titles:
            professional_context += f"with titles like {', '.join(job_titles[:3])}"
        if industries:
            professional_context += f" in {', '.join(industries[:3])} industries"
        if company_sizes:
            professional_context += f" at {', '.join(company_sizes[:2])} companies"
        
        # Construct search goal - finding people/companies that NEED event planning services
        search_goal = f"Find individuals or organizations on LinkedIn and other social media who are planning a {event_context}"
        
        if location_str:
            search_goal += f" in {location_str}"
        
        if professional_context:
            search_goal += f" {professional_context}"
        
        search_goal += ". Extract their names, contact information (email, phone, LinkedIn), company details, and any details about the upcoming event."
        
        return search_goal
    
    async def _hunt_with_ai_navigation(self, workflow_id: str, search_goal: str, session_id: str = None) -> Dict[str, Any]:
        """Use enhanced AI navigation to hunt prospects"""
        try:
            logger.info("Starting AI navigation hunt", search_goal=search_goal[:100])
            
            # Set workflow ID for screenshot tracking
            set_workflow_id(workflow_id)
            
            # Call enhanced AI navigation
            result = await enhanced_browser_mcp.call_tool('navigate_and_extract', {
                'url': 'https://www.linkedin.com',
                'extraction_goal': search_goal,
                'headless': False,  # Keep visible for now
                'session_id': session_id
            })
            
            if result.isError:
                error_text = result.content[0].text if result.content else "{}"
                logger.error("AI navigation failed", error=error_text)
                
                # Check if this error is actually a pause-for-login event
                try:
                    error_data = json.loads(error_text)
                    if error_data.get("paused_for_login"):
                        logger.info("AI navigation paused for login, propagating pause state.")
                        # Return the full data from the pause event
                        return error_data
                except json.JSONDecodeError:
                    # Not a JSON error, so it's a genuine failure
                    pass
                
                # If it's not a pause event, return a standard failure dictionary
                return {"contacts": [], "summary": "Navigation failed", "success": False}
            
            # Parse AI navigation results
            navigation_data = json.loads(result.content[0].text)
            
            # Debug: Check for Gordon Ramsay demo mode
            if navigation_data.get("demo_mode"):
                print(f"🎭 DEMO MODE DETECTED: Gordon Ramsay data returned")
                print(f"    Extracted data: {navigation_data.get('extracted_data', [])}")
            
            # Extract contact information from navigation results
            contacts = self._extract_contacts_from_navigation_data(navigation_data)
            
            # Debug: Show contact extraction results  
            print(f"👥 EXTRACTED CONTACTS: {len(contacts)} contacts found")
            for i, contact in enumerate(contacts):
                print(f"    Contact {i+1}: {contact.get('name', 'Unknown')} - {contact.get('company', 'No company')}")
            
            return {
                "contacts": contacts,
                "navigation_summary": navigation_data.get("navigation_steps", []),
                "sites_visited": len(set(step.get('url', '') for step in navigation_data.get('navigation_steps', []))),
                "success": navigation_data.get("success", False),
                "summary": f"Visited {len(set(step.get('url', '') for step in navigation_data.get('navigation_steps', [])))} sites, found {len(contacts)} contacts",
                # Propagate pause information from navigation results
                "paused_for_login": navigation_data.get("paused_for_login", False),
                "workflow_id": navigation_data.get("workflow_id"),
                "site_name": navigation_data.get("site_name"),
                "resume_endpoint": navigation_data.get("resume_endpoint"),
                "message": navigation_data.get("message")
            }
            
        except Exception as e:
            logger.error("AI navigation hunt failed", error=str(e))
            return {"contacts": [], "summary": f"Hunt failed: {str(e)}", "success": False}
    
    def _extract_contacts_from_navigation_data(self, navigation_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract structured contact information from AI navigation results"""
        contacts = []
        
        try:
            extracted_data = navigation_data.get("extracted_data", [])
            
            for data_item in extracted_data:
                # Handle nested extracted_data structure
                if isinstance(data_item, dict) and 'extracted_data' in data_item:
                    data_item = data_item['extracted_data']
                
                if isinstance(data_item, dict):
                    # First try to treat the item itself as a direct contact (for Gordon Ramsay demo)
                    if any(key in data_item for key in ['name', 'email', 'phone', 'company_name']):
                        contact = self._normalize_contact_data(data_item)
                        if contact:
                            contacts.append(contact)
                            continue
                    
                    # Look for contact lists
                    for key, value in data_item.items():
                        if isinstance(value, list) and len(value) > 0:
                            # Check if this looks like a contact list
                            for item in value:
                                if isinstance(item, dict):
                                    contact = self._normalize_contact_data(item)
                                    if contact:
                                        contacts.append(contact)
                                elif isinstance(item, str) and any(indicator in item.lower() for indicator in ['email', 'phone', '@', '.com']):
                                    # Raw contact string
                                    contact = self._parse_contact_string(item)
                                    if contact:
                                        contacts.append(contact)
        
        except Exception as e:
            logger.error("Failed to extract contacts", error=str(e))
        
        return contacts
    
    def _normalize_contact_data(self, raw_contact: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize contact data to standard format"""
        contact = {}
        
        # Extract name
        name = raw_contact.get('name') or raw_contact.get('title') or raw_contact.get('business_name', '')
        if name:
            contact['name'] = name
        
        # Extract email
        email = raw_contact.get('email') or raw_contact.get('contact_email', '')
        if email:
            contact['email'] = email
        
        # Extract phone
        phone = raw_contact.get('phone') or raw_contact.get('telephone') or raw_contact.get('contact_phone', '')
        if phone:
            contact['phone'] = phone
        
        # Extract LinkedIn
        linkedin = raw_contact.get('linkedin') or raw_contact.get('linkedin_url', '')
        if linkedin:
            contact['linkedin'] = linkedin
        
        # Extract company
        company = raw_contact.get('company') or raw_contact.get('company_name') or raw_contact.get('business_name') or raw_contact.get('organization', '')
        if company:
            contact['company'] = company
        
        # Extract location
        location = raw_contact.get('location') or raw_contact.get('address') or raw_contact.get('city', '')
        if location:
            contact['location'] = location
        
        # Extract website
        website = raw_contact.get('website') or raw_contact.get('url', '')
        if website:
            contact['website'] = website
        
        # Only return contact if it has at least name and one contact method
        if contact.get('name') and (contact.get('email') or contact.get('phone') or contact.get('linkedin')):
            return contact
        
        return None
    
    def _parse_contact_string(self, contact_str: str) -> Dict[str, Any]:
        """Parse contact information from a raw string"""
        import re
        
        contact = {}
        
        # Extract email
        email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', contact_str)
        if email_match:
            contact['email'] = email_match.group(0)
        
        # Extract phone (basic patterns)
        phone_match = re.search(r'[\+]?[\d\s\-\(\)]{10,}', contact_str)
        if phone_match:
            contact['phone'] = phone_match.group(0).strip()
        
        # Use remaining text as name (simple heuristic)
        name = contact_str
        if email_match:
            name = name.replace(email_match.group(0), '')
        if phone_match:
            name = name.replace(phone_match.group(0), '')
        
        name = name.strip(' -,')
        if name:
            contact['name'] = name
        
        # Only return if we have name and contact info
        if contact.get('name') and (contact.get('email') or contact.get('phone')):
            return contact
        
        return None
    
    async def _test_playwright_mcp_tomato_search(self, workflow_id: str) -> str:
        """Test playwright MCP server by searching for tomato with headed browser"""
        try:
            logger.info("Testing Playwright MCP server with tomato search (headed browser)")
            
            # Set workflow ID in MCP server for browser viewer
            simple_browser_mcp.workflow_id = workflow_id
            
            # Use the MCP server to test browser functionality with headed browser
            result = await simple_browser_mcp.call_tool(
                "test_browser",
                {
                    "test_query": "tomato",
                    "headless": False  # Use headed browser to see what's happening
                }
            )
            
            logger.info("MCP call completed", is_error=result.isError)
            
            if result.isError:
                error_content = result.content[0].text if result.content else "Unknown error"
                logger.error("Tomato search failed - MCP returned error", error_content=error_content)
                
                # Try to parse error details
                try:
                    error_data = json.loads(error_content)
                    error_type = error_data.get("error_type", "Unknown")
                    error_message = error_data.get("error", "Unknown error")
                    logger.error("Detailed error info", error_type=error_type, error_message=error_message)
                except:
                    logger.error("Could not parse error details", raw_error=error_content)
                
                return ""
            
            # Parse the successful result
            try:
                result_data = json.loads(result.content[0].text)
                logger.info("Parsed MCP result", success=result_data.get("success"), has_title=bool(result_data.get("page_title")))
                
                if result_data.get("success"):
                    message = result_data.get("message", "")
                    page_title = result_data.get("page_title", "")
                    headless_mode = result_data.get("headless_mode", "unknown")
                    
                    logger.info("Tomato search successful via MCP", 
                              message=message, 
                              page_title=page_title,
                              headless_mode=headless_mode)
                    return message
                else:
                    error_msg = result_data.get("error", "Unknown error")
                    error_type = result_data.get("error_type", "Unknown")
                    logger.error("Tomato search failed via MCP", error=error_msg, error_type=error_type)
                    return ""
                    
            except json.JSONDecodeError as e:
                logger.error("Failed to parse MCP result JSON", error=str(e), raw_content=result.content[0].text if result.content else "No content")
                return ""
                
        except Exception as e:
            logger.error("Tomato search failed with exception", 
                        error=str(e), 
                        error_type=type(e).__name__)
            return ""
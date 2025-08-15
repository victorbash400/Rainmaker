"""
Simple Gemini AI Interface for AI-powered web navigation
Sends DOM + task to AI, gets back actionable instructions
"""

import json
import re
from typing import Dict, Any, Optional, List
import structlog
from app.services.gemini_service import gemini_service, GeminiServiceError

logger = structlog.get_logger(__name__)


class SimpleGeminiInterface:
    """
    Simple AI interface: send DOM + task, get action
    Focuses on fast, reliable decision making for web navigation
    """
    
    def __init__(self):
        self.gemini_service = gemini_service
        
        # Valid actions the AI can return
        self.valid_actions = {
            "click": ["selector"],
            "type": ["selector", "text"],
            "extract": ["data_type"],
            "wait": ["condition"],
            "navigate": ["url"],
            "complete": ["result"]
        }
    
    async def get_next_action(self, page_elements: Dict[str, Any], task_goal: str, current_url: str = "") -> Dict[str, Any]:
        """
        Send page elements and task to AI, get back single action to take
        
        Args:
            page_elements: Structured page data from DOM extractor
            task_goal: Natural language description of what to accomplish
            current_url: Current page URL for context
            
        Returns:
            Dict with action details: {"action": "click", "selector": "#search-btn", "reasoning": "..."}
        """
        try:
            logger.info("Getting next action from AI", task=task_goal, url=current_url)
            
            # Build simple prompt for AI
            prompt = self._build_simple_prompt(page_elements, task_goal, current_url)
            
            # Get AI response
            system_prompt = self._get_system_prompt()
            response = await self.gemini_service.generate_agent_response(
                system_prompt=system_prompt,
                user_message=prompt
            )
            
            # Parse AI response into actionable instruction
            action_result = self._parse_action_response(response)
            
            logger.info("AI action generated", 
                       action=action_result.get("action"),
                       confidence=action_result.get("confidence", 0))
            
            return action_result
            
        except Exception as e:
            logger.error("Failed to get AI action", error=str(e), task=task_goal)
            return {
                "action": "error",
                "error": str(e),
                "reasoning": f"AI decision failed: {str(e)}",
                "confidence": 0.0,
                "success": False
            }
    
    def _build_simple_prompt(self, page_elements: Dict[str, Any], task_goal: str, current_url: str) -> str:
        """
        Build simple prompt: here's the page, here's the goal, what should I do?
        
        Args:
            page_elements: Page structure from DOM extractor
            task_goal: What we're trying to accomplish
            current_url: Current page URL
            
        Returns:
            Formatted prompt string for AI
        """
        try:
            # Get page info
            page_info = page_elements.get("page_info", {})
            page_title = page_info.get("title", "Unknown Page")
            
            # Build element summary for AI
            element_summary = self._build_element_summary(page_elements)
            
            prompt = f"""
CURRENT SITUATION:
- Page: {page_title}
- URL: {current_url}
- Task Goal: {task_goal}

AVAILABLE PAGE ELEMENTS:
{element_summary}

INSTRUCTIONS:
Analyze the page elements and determine the single best next action to accomplish the task goal.
Focus on elements that are most likely to help achieve the goal.

Respond with a JSON object containing:
- action: one of [click, type, extract, wait, navigate, complete]
- selector: CSS selector for the element (for click/type actions)
- text: text to type (for type actions)
- data_type: what to extract (for extract actions)
- url: URL to navigate to (for navigate actions)
- result: final result data (for complete actions)
- reasoning: brief explanation of why this action was chosen
- confidence: confidence score 0.0-1.0

Example responses:
{{"action": "type", "selector": "input[name='q']", "text": "wedding planners Switzerland", "reasoning": "Found search input, entering search query", "confidence": 0.9}}
{{"action": "click", "selector": "#search-button", "reasoning": "Clicking search button to submit query", "confidence": 0.8}}
{{"action": "extract", "data_type": "contact_info", "reasoning": "Page contains prospect contact information", "confidence": 0.7}}
{{"action": "complete", "result": {{"prospects": []}}, "reasoning": "Task completed successfully", "confidence": 1.0}}
"""
            
            return prompt.strip()
            
        except Exception as e:
            logger.error("Failed to build prompt", error=str(e))
            return f"Task: {task_goal}\nError building prompt: {str(e)}"
    
    def _build_element_summary(self, page_elements: Dict[str, Any]) -> str:
        """
        Build a concise summary of page elements for AI analysis
        
        Args:
            page_elements: Page structure from DOM extractor
            
        Returns:
            Formatted element summary string
        """
        try:
            summary_parts = []
            
            # Interactive elements (buttons, links)
            interactive = page_elements.get("interactive_elements", [])
            if interactive:
                summary_parts.append("INTERACTIVE ELEMENTS:")
                for elem in interactive[:10]:  # Limit to top 10
                    selector = elem.get("selector", "unknown")
                    text = elem.get("text_content", "").strip()[:50]
                    tag = elem.get("tag_name", "")
                    
                    if text:
                        summary_parts.append(f"  - {tag} '{text}' (selector: {selector})")
                    else:
                        attrs = elem.get("attributes", {})
                        desc = attrs.get("aria-label") or attrs.get("title") or attrs.get("alt") or "no text"
                        summary_parts.append(f"  - {tag} [{desc}] (selector: {selector})")
            
            # Form elements (inputs, selects)
            forms = page_elements.get("form_elements", [])
            if forms:
                summary_parts.append("\nFORM ELEMENTS:")
                for elem in forms[:8]:  # Limit to top 8
                    selector = elem.get("selector", "unknown")
                    tag = elem.get("tag_name", "")
                    attrs = elem.get("attributes", {})
                    
                    # Build description
                    desc_parts = []
                    if attrs.get("placeholder"):
                        desc_parts.append(f"placeholder: {attrs['placeholder']}")
                    if attrs.get("name"):
                        desc_parts.append(f"name: {attrs['name']}")
                    if attrs.get("type"):
                        desc_parts.append(f"type: {attrs['type']}")
                    
                    labels = elem.get("labels", [])
                    if labels:
                        desc_parts.append(f"label: {labels[0]}")
                    
                    desc = ", ".join(desc_parts) if desc_parts else "no description"
                    summary_parts.append(f"  - {tag} [{desc}] (selector: {selector})")
            
            # Content elements (headings, important text)
            content = page_elements.get("content_elements", [])
            if content:
                summary_parts.append("\nIMPORTANT CONTENT:")
                for elem in content[:5]:  # Limit to top 5
                    text = elem.get("text_content", "").strip()[:100]
                    tag = elem.get("tag_name", "")
                    content_type = elem.get("content_type", "general")
                    
                    if text and len(text) > 10:
                        summary_parts.append(f"  - {tag} ({content_type}): {text}")
            
            # Navigation elements
            navigation = page_elements.get("navigation_elements", [])
            if navigation:
                summary_parts.append("\nNAVIGATION:")
                for elem in navigation[:5]:  # Limit to top 5
                    text = elem.get("text_content", "").strip()[:50]
                    selector = elem.get("selector", "unknown")
                    if text:
                        summary_parts.append(f"  - {text} (selector: {selector})")
            
            return "\n".join(summary_parts) if summary_parts else "No relevant elements found"
            
        except Exception as e:
            logger.error("Failed to build element summary", error=str(e))
            return f"Error building element summary: {str(e)}"
    
    def _get_system_prompt(self) -> str:
        """
        Get the system prompt that defines AI behavior for web navigation
        
        Returns:
            System prompt string
        """
        return """
You are an expert web navigation AI assistant. Your job is to analyze web pages and determine the best single action to take to accomplish a given task.

CORE PRINCIPLES:
1. Take ONE action at a time - never suggest multiple actions
2. Be specific with selectors - use the exact selector provided
3. Focus on the most likely path to success
4. Prioritize visible, interactive elements
5. For search tasks, look for search inputs and submit buttons
6. For extraction tasks, identify when you've found the target data
7. Use "complete" action when the task goal has been achieved

ACTION TYPES:
- click: Click on buttons, links, or interactive elements
- type: Enter text into input fields
- extract: Extract data from the current page
- wait: Wait for page changes or loading
- navigate: Go to a different URL
- complete: Mark task as finished with results

RESPONSE FORMAT:
Always respond with valid JSON containing action, reasoning, and confidence.
Be concise but clear in your reasoning.
Use confidence scores to indicate how certain you are about the action.

SEARCH STRATEGY:
1. Find search input field
2. Type search query
3. Click search/submit button
4. Extract results from results page
5. Complete with extracted data

EXTRACTION STRATEGY:
1. Identify relevant content on page
2. Use extract action with appropriate data_type
3. Complete with structured results
"""
    
    def _parse_action_response(self, response: str) -> Dict[str, Any]:
        """
        Parse AI response into actionable instruction
        
        Args:
            response: Raw AI response text
            
        Returns:
            Parsed action dictionary
        """
        try:
            # Clean up response text
            response = response.strip()
            
            if not response:
                return {
                    "action": "error",
                    "error": "Empty AI response",
                    "reasoning": "AI returned empty response",
                    "confidence": 0.0,
                    "success": False
                }
            
            # Try to extract JSON from response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                try:
                    action_data = json.loads(json_str)
                    logger.debug("Successfully parsed JSON response", action=action_data.get("action"))
                except json.JSONDecodeError as json_error:
                    # Try to fix common JSON issues
                    try:
                        json_str = self._fix_json_format(json_str)
                        action_data = json.loads(json_str)
                        logger.debug("Successfully parsed JSON after fixing format", action=action_data.get("action"))
                    except json.JSONDecodeError:
                        logger.warning("JSON parsing failed even after format fixing", 
                                     json_str=json_str[:200], error=str(json_error))
                        # Fall back to text parsing
                        action_data = self._parse_text_response(response)
            else:
                # No JSON found, try to parse as text
                logger.debug("No JSON found in response, parsing as text")
                action_data = self._parse_text_response(response)
            
            # Sanitize parameters
            action_data = self._sanitize_action_parameters(action_data)
            
            # Validate completeness
            action_data = self._validate_response_completeness(action_data)
            
            # Validate and enhance the action
            validated_action = self._validate_action(action_data)
            
            # Add parsing metadata
            validated_action["response_length"] = len(response)
            validated_action["parsing_method"] = "json" if json_match else "text"
            
            return validated_action
            
        except Exception as e:
            logger.error("Failed to parse AI response", error=str(e), response=response[:200])
            return self._handle_malformed_response(response, e)
    
    def _fix_json_format(self, json_str: str) -> str:
        """
        Attempt to fix common JSON formatting issues
        
        Args:
            json_str: Potentially malformed JSON string
            
        Returns:
            Fixed JSON string
        """
        # Remove common markdown formatting
        json_str = re.sub(r'```json\s*', '', json_str)
        json_str = re.sub(r'```\s*$', '', json_str)
        
        # Fix trailing commas before closing braces/brackets
        json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)
        
        # Fix multiple trailing commas
        json_str = re.sub(r',+(\s*[}\]])', r'\1', json_str)
        
        return json_str.strip()
    
    def _parse_text_response(self, response: str) -> Dict[str, Any]:
        """
        Parse non-JSON text response into action format
        
        Args:
            response: Text response from AI
            
        Returns:
            Action dictionary parsed from text
        """
        response_lower = response.lower()
        
        # Try to identify action type
        if "click" in response_lower:
            action_type = "click"
            # Try to extract selector from text
            selector = self._extract_selector_from_text(response)
            action_data = {
                "action": action_type,
                "selector": selector or "unknown",
                "reasoning": response[:200],
                "confidence": 0.3,
                "success": True,
                "parsed_from_text": True
            }
        elif "type" in response_lower or "enter" in response_lower:
            action_type = "type"
            selector = self._extract_selector_from_text(response)
            text = self._extract_text_from_response(response)
            action_data = {
                "action": action_type,
                "selector": selector or "unknown",
                "text": text or "",
                "reasoning": response[:200],
                "confidence": 0.3,
                "success": True,
                "parsed_from_text": True
            }
        elif "extract" in response_lower:
            action_type = "extract"
            action_data = {
                "action": action_type,
                "data_type": "general",
                "reasoning": response[:200],
                "confidence": 0.3,
                "success": True,
                "parsed_from_text": True
            }
        elif "complete" in response_lower or "done" in response_lower:
            action_type = "complete"
            action_data = {
                "action": action_type,
                "result": {},
                "reasoning": response[:200],
                "confidence": 0.3,
                "success": True,
                "parsed_from_text": True
            }
        elif "wait" in response_lower:
            action_type = "wait"
            action_data = {
                "action": action_type,
                "condition": "page_load",
                "reasoning": response[:200],
                "confidence": 0.3,
                "success": True,
                "parsed_from_text": True
            }
        elif "navigate" in response_lower or "go to" in response_lower:
            action_type = "navigate"
            url = self._extract_url_from_text(response)
            action_data = {
                "action": action_type,
                "url": url or "unknown",
                "reasoning": response[:200],
                "confidence": 0.3,
                "success": True,
                "parsed_from_text": True
            }
        else:
            action_type = "error"
            action_data = {
                "action": action_type,
                "error": "Could not parse text response",
                "reasoning": response[:200],
                "confidence": 0.0,
                "success": False,
                "parsed_from_text": True
            }
        
        return action_data
    
    def _extract_selector_from_text(self, text: str) -> Optional[str]:
        """Extract CSS selector from text response"""
        # Look for common selector patterns in text
        selector_patterns = [
            r'#[\w-]+',  # ID selectors
            r'\.[\w-]+',  # Class selectors
            r'\[[\w-]+="[^"]*"\]',  # Attribute selectors
            r'input\[name="[^"]*"\]',  # Input name selectors
            r'button\[type="[^"]*"\]'  # Button type selectors
        ]
        
        for pattern in selector_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(0)
        
        return None
    
    def _extract_text_from_response(self, response: str) -> Optional[str]:
        """Extract text to type from response"""
        # Look for quoted text that might be the text to type
        quoted_text = re.search(r'"([^"]+)"', response)
        if quoted_text:
            return quoted_text.group(1)
        
        # Look for text after "type" or "enter"
        type_match = re.search(r'(?:type|enter)\s+(.+?)(?:\s|$)', response, re.IGNORECASE)
        if type_match:
            return type_match.group(1).strip()
        
        return None
    
    def _extract_url_from_text(self, text: str) -> Optional[str]:
        """Extract URL from text response"""
        # Look for URL patterns
        url_pattern = r'https?://[^\s]+'
        match = re.search(url_pattern, text)
        if match:
            return match.group(0)
        
        return None
    
    def _validate_action(self, action_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate AI-returned action and add missing fields
        
        Args:
            action_data: Raw action data from AI
            
        Returns:
            Validated and enhanced action data
        """
        try:
            # Ensure required fields exist
            action_type = action_data.get("action", "error")
            
            # Validate action type
            if action_type not in self.valid_actions:
                logger.warning("Invalid action type", action=action_type, valid_actions=list(self.valid_actions.keys()))
                return {
                    "action": "error",
                    "error": f"Invalid action type: {action_type}",
                    "reasoning": f"AI suggested invalid action: {action_type}. Valid actions: {list(self.valid_actions.keys())}",
                    "confidence": 0.0,
                    "success": False,
                    "validation_error": "invalid_action_type"
                }
            
            # Validate required parameters for action type
            required_params = self.valid_actions[action_type]
            missing_params = []
            
            for param in required_params:
                if param not in action_data or not action_data[param]:
                    missing_params.append(param)
            
            if missing_params:
                logger.warning("Missing required parameters", 
                             action=action_type, missing=missing_params, required=required_params)
                return {
                    "action": "error",
                    "error": f"Missing required parameters: {missing_params}",
                    "reasoning": f"AI action '{action_type}' missing required parameters: {', '.join(missing_params)}",
                    "confidence": 0.0,
                    "success": False,
                    "validation_error": "missing_parameters",
                    "missing_parameters": missing_params
                }
            
            # Add default fields if missing
            validated_action = {
                "action": action_type,
                "reasoning": action_data.get("reasoning", "No reasoning provided"),
                "confidence": float(action_data.get("confidence", 0.5)),
                "success": True,
                "timestamp": action_data.get("timestamp", ""),
                "validation_passed": True
            }
            
            # Copy action-specific parameters
            for param in required_params:
                validated_action[param] = action_data[param]
            
            # Copy optional parameters
            optional_fields = ["text", "data_type", "url", "result", "condition"]
            for field in optional_fields:
                if field in action_data:
                    validated_action[field] = action_data[field]
            
            # Copy validation metadata if present
            metadata_fields = ["completeness_score", "completeness_warnings", "parsed_from_text"]
            for field in metadata_fields:
                if field in action_data:
                    validated_action[field] = action_data[field]
            
            # Validate selector format if present
            if "selector" in validated_action:
                selector = validated_action["selector"]
                if not self._is_valid_selector(selector):
                    logger.warning("Potentially invalid selector", selector=selector)
                    validated_action["selector_warning"] = "Selector may be invalid"
                    validated_action["confidence"] = max(0.0, validated_action["confidence"] - 0.2)
            
            # Validate URL format if present
            if "url" in validated_action:
                url = validated_action["url"]
                if not self._is_valid_url(url):
                    logger.warning("Potentially invalid URL", url=url)
                    validated_action["url_warning"] = "URL may be invalid"
                    validated_action["confidence"] = max(0.0, validated_action["confidence"] - 0.1)
            
            # Clamp confidence to valid range
            validated_action["confidence"] = max(0.0, min(1.0, validated_action["confidence"]))
            
            # Add final validation score
            validation_score = 1.0
            if "selector_warning" in validated_action:
                validation_score -= 0.2
            if "url_warning" in validated_action:
                validation_score -= 0.1
            if validated_action.get("completeness_score", 1.0) < 0.8:
                validation_score -= 0.1
            
            validated_action["validation_score"] = max(0.0, validation_score)
            
            return validated_action
            
        except Exception as e:
            logger.error("Failed to validate action", error=str(e), action_data=action_data)
            return {
                "action": "error",
                "error": f"Action validation failed: {str(e)}",
                "reasoning": "Could not validate AI action due to internal error",
                "confidence": 0.0,
                "success": False,
                "validation_error": "validation_exception",
                "exception_type": type(e).__name__
            }
    
    def _is_valid_url(self, url: str) -> bool:
        """
        Basic validation of URL format
        
        Args:
            url: URL string to validate
            
        Returns:
            True if URL appears to be valid
        """
        if not url or not isinstance(url, str):
            return False
        
        url = url.strip()
        
        # Basic URL patterns
        url_patterns = [
            r'^https?://[^\s/$.?#].[^\s]*$',  # HTTP/HTTPS URLs
            r'^//[^\s/$.?#].[^\s]*$',  # Protocol-relative URLs
            r'^/[^\s]*$',  # Absolute paths
            r'^[a-zA-Z0-9][a-zA-Z0-9-]*[a-zA-Z0-9]*\.[a-zA-Z]{2,}$'  # Domain names
        ]
        
        return any(re.match(pattern, url) for pattern in url_patterns)
    
    def _is_valid_selector(self, selector: str) -> bool:
        """
        Basic validation of CSS selector format
        
        Args:
            selector: CSS selector string
            
        Returns:
            True if selector appears to be valid
        """
        if not selector or not isinstance(selector, str):
            return False
        
        # Check for common selector patterns
        valid_patterns = [
            r'^#[\w-]+$',  # ID selector
            r'^\.[\w-]+$',  # Class selector
            r'^\w+$',  # Tag selector
            r'^\[[\w-]+(="[^"]*")?\]$',  # Attribute selector
            r'^[\w-]+\[[\w-]+(="[^"]*")?\]$',  # Tag with attribute
            r'^[\w\s\[\]="\'#\.\-:()]+$'  # General selector pattern
        ]
        
        # Clean selector for validation
        selector = selector.strip()
        
        # Check if it matches any valid pattern
        for pattern in valid_patterns:
            if re.match(pattern, selector):
                return True
        
        # Additional checks for complex selectors
        # Allow descendant selectors (space separated)
        if ' ' in selector:
            parts = selector.split()
            return all(self._is_simple_selector_valid(part) for part in parts if part)
        
        # Allow child selectors (> separated)
        if '>' in selector:
            parts = [part.strip() for part in selector.split('>')]
            return all(self._is_simple_selector_valid(part) for part in parts if part)
        
        # Allow comma-separated selectors
        if ',' in selector:
            parts = [part.strip() for part in selector.split(',')]
            return all(self._is_simple_selector_valid(part) for part in parts if part)
        
        return False
    
    def _is_simple_selector_valid(self, selector: str) -> bool:
        """
        Validate a simple (non-compound) CSS selector
        
        Args:
            selector: Simple CSS selector string
            
        Returns:
            True if selector appears to be valid
        """
        if not selector:
            return False
        
        # Basic patterns for simple selectors
        simple_patterns = [
            r'^#[\w-]+$',  # ID
            r'^\.[\w-]+$',  # Class
            r'^\w+$',  # Tag
            r'^\[[\w-]+(="[^"]*")?\]$',  # Attribute
            r'^[\w-]+\[[\w-]+(="[^"]*")?\]$',  # Tag with attribute
            r'^[\w-]+\.[\w-]+$',  # Tag with class
            r'^[\w-]+#[\w-]+$',  # Tag with ID
            r'^[\w-]+:[\w-]+(\([^)]*\))?$'  # Pseudo-selectors
        ]
        
        return any(re.match(pattern, selector.strip()) for pattern in simple_patterns)


    def _handle_malformed_response(self, response: str, error: Exception) -> Dict[str, Any]:
        """
        Handle cases where AI response cannot be parsed at all
        
        Args:
            response: Original AI response
            error: Exception that occurred during parsing
            
        Returns:
            Error action with diagnostic information
        """
        logger.error("Completely malformed AI response", 
                    error=str(error), 
                    response_length=len(response),
                    response_preview=response[:100])
        
        # Try to extract any useful information from the response
        response_lower = response.lower()
        suggested_action = "wait"  # Default safe action
        
        # Look for action keywords in the response
        if any(word in response_lower for word in ["click", "press", "button"]):
            suggested_action = "click"
        elif any(word in response_lower for word in ["type", "enter", "input", "search"]):
            suggested_action = "type"
        elif any(word in response_lower for word in ["extract", "get", "find", "collect"]):
            suggested_action = "extract"
        elif any(word in response_lower for word in ["complete", "done", "finished"]):
            suggested_action = "complete"
        elif any(word in response_lower for word in ["navigate", "go to", "visit"]):
            suggested_action = "navigate"
        
        return {
            "action": "error",
            "error": f"Malformed AI response: {str(error)}",
            "reasoning": f"Could not parse AI response. Suggested fallback: {suggested_action}",
            "confidence": 0.0,
            "success": False,
            "raw_response": response[:500],
            "suggested_fallback": suggested_action,
            "parse_error_type": type(error).__name__
        }
    
    def _validate_response_completeness(self, action_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate that AI response contains all necessary information
        
        Args:
            action_data: Parsed action data
            
        Returns:
            Enhanced action data with completeness validation
        """
        completeness_score = 1.0
        warnings = []
        
        # Check for reasoning
        if not action_data.get("reasoning") or len(action_data.get("reasoning", "")) < 10:
            completeness_score -= 0.2
            warnings.append("Missing or insufficient reasoning")
        
        # Check for confidence score
        if "confidence" not in action_data:
            completeness_score -= 0.1
            warnings.append("Missing confidence score")
            action_data["confidence"] = 0.5  # Default
        
        # Action-specific completeness checks
        action_type = action_data.get("action")
        
        if action_type == "type" and not action_data.get("text"):
            completeness_score -= 0.3
            warnings.append("Type action missing text to type")
        
        if action_type in ["click", "type"] and not action_data.get("selector"):
            completeness_score -= 0.4
            warnings.append(f"{action_type} action missing selector")
        
        if action_type == "extract" and not action_data.get("data_type"):
            completeness_score -= 0.2
            warnings.append("Extract action missing data_type")
        
        if action_type == "navigate" and not action_data.get("url"):
            completeness_score -= 0.3
            warnings.append("Navigate action missing URL")
        
        # Add completeness information to action
        action_data["completeness_score"] = max(0.0, completeness_score)
        if warnings:
            action_data["completeness_warnings"] = warnings
        
        return action_data
    
    def _sanitize_action_parameters(self, action_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize and clean action parameters to prevent issues
        
        Args:
            action_data: Raw action data
            
        Returns:
            Sanitized action data
        """
        # Clean selector
        if "selector" in action_data:
            selector = action_data["selector"]
            if isinstance(selector, str):
                # Remove extra whitespace
                selector = selector.strip()
                # Remove quotes if they wrap the entire selector
                if (selector.startswith('"') and selector.endswith('"')) or \
                   (selector.startswith("'") and selector.endswith("'")):
                    selector = selector[1:-1]
                action_data["selector"] = selector
        
        # Clean text input
        if "text" in action_data:
            text = action_data["text"]
            if isinstance(text, str):
                # Remove excessive whitespace but preserve intentional spaces
                text = re.sub(r'\s+', ' ', text.strip())
                action_data["text"] = text
        
        # Clean URL
        if "url" in action_data:
            url = action_data["url"]
            if isinstance(url, str):
                url = url.strip()
                # Add protocol if missing
                if url and not url.startswith(('http://', 'https://', '//')):
                    if url.startswith('www.'):
                        url = 'https://' + url
                    elif '.' in url and not url.startswith('/'):
                        url = 'https://' + url
                action_data["url"] = url
        
        # Ensure confidence is a float
        if "confidence" in action_data:
            try:
                confidence = float(action_data["confidence"])
                action_data["confidence"] = max(0.0, min(1.0, confidence))
            except (ValueError, TypeError):
                action_data["confidence"] = 0.5
        
        # Clean reasoning
        if "reasoning" in action_data:
            reasoning = action_data["reasoning"]
            if isinstance(reasoning, str):
                # Limit reasoning length (increased for better context)
                reasoning = reasoning.strip()[:1500]
                action_data["reasoning"] = reasoning
        
        return action_data


class SimpleGeminiInterfaceError(Exception):
    """Custom exception for Simple Gemini Interface errors"""
    pass
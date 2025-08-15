"""
DOM Extractor for AI-powered web navigation
Extracts page structure as structured text for AI analysis
"""

import json
import re
from typing import Dict, Any, List, Optional
from playwright.sync_api import Page, ElementHandle
import structlog

logger = structlog.get_logger(__name__)


class DOMExtractor:
    """
    Extracts page structure as structured text for AI analysis
    Focuses on interactive elements, forms, and content for prospect hunting
    """
    
    def __init__(self):
        # Element selectors for different types of page elements
        self.element_selectors = {
            'interactive': 'button, a, input, select, textarea, [onclick], [role="button"], [tabindex]',
            'forms': 'form, input, select, textarea, [role="textbox"], [role="combobox"]',
            'content': 'h1, h2, h3, h4, h5, h6, p, span, div[class*="content"], [role="heading"]',
            'navigation': 'nav, [role="navigation"], .nav, .menu, [class*="nav"], [class*="menu"]',
            'search': 'input[type="search"], input[name*="search"], input[placeholder*="search"], [role="searchbox"]',
            'contact': '[href*="mailto"], [href*="tel"], [class*="contact"], [class*="phone"], [class*="email"]'
        }
        
        # Attributes to extract for context
        self.important_attributes = [
            'id', 'class', 'name', 'type', 'placeholder', 'aria-label', 
            'title', 'alt', 'href', 'onclick', 'role', 'data-*'
        ]
    
    async def extract_page_structure(self, page: Page) -> Dict[str, Any]:
        """
        Extract complete page structure for AI analysis
        
        Args:
            page: Playwright page object
            
        Returns:
            Dict containing structured page data for AI consumption
        """
        try:
            logger.info("Starting page structure extraction")
            
            # Get basic page information
            page_info = {
                "url": page.url,
                "title": page.title(),
                "viewport": page.viewport_size,
                "extracted_at": page.evaluate("() => new Date().toISOString()")
            }
            
            # Extract different types of elements
            interactive_elements = await self.extract_interactive_elements(page)
            form_elements = await self.extract_form_elements(page)
            content_elements = await self.extract_content_elements(page)
            navigation_elements = await self.extract_navigation_elements(page)
            
            # Build complete page structure
            page_structure = {
                "page_info": page_info,
                "interactive_elements": interactive_elements,
                "form_elements": form_elements,
                "content_elements": content_elements,
                "navigation_elements": navigation_elements,
                "element_counts": {
                    "interactive": len(interactive_elements),
                    "forms": len(form_elements),
                    "content": len(content_elements),
                    "navigation": len(navigation_elements)
                }
            }
            
            logger.info("Page structure extraction completed", 
                       interactive=len(interactive_elements),
                       forms=len(form_elements),
                       content=len(content_elements))
            
            return page_structure
            
        except Exception as e:
            logger.error("Failed to extract page structure", error=str(e))
            raise
    
    async def extract_interactive_elements(self, page: Page) -> List[Dict[str, Any]]:
        """
        Extract interactive elements (buttons, links, inputs) with context
        
        Args:
            page: Playwright page object
            
        Returns:
            List of interactive element data
        """
        try:
            elements = []
            
            # Get all interactive elements
            interactive_handles = page.query_selector_all(self.element_selectors['interactive'])
            
            for i, handle in enumerate(interactive_handles[:50]):  # Limit to first 50 for performance
                try:
                    element_data = await self._extract_element_data(handle, f"interactive_{i}")
                    if element_data and self._is_element_visible(element_data):
                        # Add context for this element
                        element_data["context"] = await self._build_element_context(handle)
                        elements.append(element_data)
                        
                except Exception as e:
                    logger.debug("Failed to extract interactive element", index=i, error=str(e))
                    continue
            
            logger.info("Interactive elements extracted", count=len(elements))
            return elements
            
        except Exception as e:
            logger.error("Failed to extract interactive elements", error=str(e))
            return []
    
    async def extract_form_elements(self, page: Page) -> List[Dict[str, Any]]:
        """
        Extract form elements with labels and context for intelligent form filling
        
        Args:
            page: Playwright page object
            
        Returns:
            List of form element data with context
        """
        try:
            elements = []
            
            # Get all form-related elements
            form_handles = page.query_selector_all(self.element_selectors['forms'])
            
            for i, handle in enumerate(form_handles[:30]):  # Limit to first 30
                try:
                    element_data = await self._extract_element_data(handle, f"form_{i}")
                    if element_data and self._is_form_element_relevant(element_data):
                        # Add form-specific context
                        element_data["form_context"] = await self._build_form_context(handle)
                        element_data["labels"] = await self._find_element_labels(handle)
                        elements.append(element_data)
                        
                except Exception as e:
                    logger.debug("Failed to extract form element", index=i, error=str(e))
                    continue
            
            logger.info("Form elements extracted", count=len(elements))
            return elements
            
        except Exception as e:
            logger.error("Failed to extract form elements", error=str(e))
            return []
    
    async def extract_content_elements(self, page: Page) -> List[Dict[str, Any]]:
        """
        Extract content elements for prospect information analysis
        
        Args:
            page: Playwright page object
            
        Returns:
            List of content element data
        """
        try:
            elements = []
            
            # Get content elements
            content_handles = page.query_selector_all(self.element_selectors['content'])
            
            for i, handle in enumerate(content_handles[:40]):  # Limit to first 40
                try:
                    element_data = await self._extract_element_data(handle, f"content_{i}")
                    if element_data and self._is_content_relevant(element_data):
                        # Add content analysis
                        element_data["content_type"] = self._analyze_content_type(element_data)
                        elements.append(element_data)
                        
                except Exception as e:
                    logger.debug("Failed to extract content element", index=i, error=str(e))
                    continue
            
            logger.info("Content elements extracted", count=len(elements))
            return elements
            
        except Exception as e:
            logger.error("Failed to extract content elements", error=str(e))
            return []
    
    async def extract_navigation_elements(self, page: Page) -> List[Dict[str, Any]]:
        """
        Extract navigation elements for site structure understanding
        
        Args:
            page: Playwright page object
            
        Returns:
            List of navigation element data
        """
        try:
            elements = []
            
            # Get navigation elements
            nav_handles = page.query_selector_all(self.element_selectors['navigation'])
            
            for i, handle in enumerate(nav_handles[:20]):  # Limit to first 20
                try:
                    element_data = await self._extract_element_data(handle, f"nav_{i}")
                    if element_data:
                        elements.append(element_data)
                        
                except Exception as e:
                    logger.debug("Failed to extract navigation element", index=i, error=str(e))
                    continue
            
            logger.info("Navigation elements extracted", count=len(elements))
            return elements
            
        except Exception as e:
            logger.error("Failed to extract navigation elements", error=str(e))
            return []
    
    async def _extract_element_data(self, handle: ElementHandle, element_id: str) -> Optional[Dict[str, Any]]:
        """
        Extract data from a single element handle
        
        Args:
            handle: Playwright element handle
            element_id: Unique identifier for this element
            
        Returns:
            Element data dictionary or None if extraction fails
        """
        try:
            # Get basic element information
            tag_name = await handle.evaluate("el => el.tagName.toLowerCase()")
            text_content = await handle.evaluate("el => el.textContent?.trim() || ''")
            inner_text = await handle.evaluate("el => el.innerText?.trim() || ''")
            
            # Get attributes
            attributes = {}
            for attr in self.important_attributes:
                try:
                    if attr == 'data-*':
                        # Get all data attributes
                        data_attrs = await handle.evaluate("""
                            el => {
                                const attrs = {};
                                for (let attr of el.attributes) {
                                    if (attr.name.startsWith('data-')) {
                                        attrs[attr.name] = attr.value;
                                    }
                                }
                                return attrs;
                            }
                        """)
                        attributes.update(data_attrs)
                    else:
                        value = await handle.get_attribute(attr)
                        if value:
                            attributes[attr] = value
                except Exception:
                    continue
            
            # Get element position and visibility
            bounding_box = await handle.bounding_box()
            is_visible = await handle.is_visible()
            is_enabled = await handle.is_enabled() if tag_name in ['input', 'button', 'select', 'textarea'] else True
            
            element_data = {
                "id": element_id,
                "tag_name": tag_name,
                "text_content": text_content[:200],  # Limit text length
                "inner_text": inner_text[:200],
                "attributes": attributes,
                "bounding_box": bounding_box,
                "is_visible": is_visible,
                "is_enabled": is_enabled,
                "selector": await self._generate_selector(handle)
            }
            
            return element_data
            
        except Exception as e:
            logger.debug("Failed to extract element data", element_id=element_id, error=str(e))
            return None
    
    async def _build_element_context(self, handle: ElementHandle) -> Dict[str, Any]:
        """
        Build context information for an element (surrounding text, parent info, etc.)
        
        Args:
            handle: Playwright element handle
            
        Returns:
            Context information dictionary
        """
        try:
            context = {}
            
            # Get parent element info
            parent_info = await handle.evaluate("""
                el => {
                    const parent = el.parentElement;
                    if (parent) {
                        return {
                            tag_name: parent.tagName.toLowerCase(),
                            class_name: parent.className,
                            id: parent.id,
                            text_content: parent.textContent?.trim().substring(0, 100) || ''
                        };
                    }
                    return null;
                }
            """)
            if parent_info:
                context["parent"] = parent_info
            
            # Get surrounding text (siblings)
            surrounding_text = await handle.evaluate("""
                el => {
                    const siblings = Array.from(el.parentElement?.children || []);
                    const index = siblings.indexOf(el);
                    const before = siblings.slice(Math.max(0, index - 2), index)
                        .map(s => s.textContent?.trim()).filter(t => t).join(' ');
                    const after = siblings.slice(index + 1, index + 3)
                        .map(s => s.textContent?.trim()).filter(t => t).join(' ');
                    return { before: before.substring(0, 100), after: after.substring(0, 100) };
                }
            """)
            context["surrounding_text"] = surrounding_text
            
            return context
            
        except Exception as e:
            logger.debug("Failed to build element context", error=str(e))
            return {}
    
    async def _build_form_context(self, handle: ElementHandle) -> Dict[str, Any]:
        """
        Build form-specific context for intelligent form filling
        
        Args:
            handle: Playwright element handle
            
        Returns:
            Form context dictionary
        """
        try:
            form_context = {}
            
            # Find the parent form
            form_info = await handle.evaluate("""
                el => {
                    const form = el.closest('form');
                    if (form) {
                        return {
                            action: form.action,
                            method: form.method,
                            id: form.id,
                            class_name: form.className
                        };
                    }
                    return null;
                }
            """)
            if form_info:
                form_context["form"] = form_info
            
            # Get field type and purpose hints
            field_hints = await handle.evaluate("""
                el => {
                    const hints = [];
                    const name = el.name || '';
                    const id = el.id || '';
                    const placeholder = el.placeholder || '';
                    const className = el.className || '';
                    
                    // Analyze field purpose based on attributes
                    const searchTerms = ['search', 'query', 'find', 'lookup'];
                    const emailTerms = ['email', 'mail'];
                    const nameTerms = ['name', 'first', 'last', 'full'];
                    const phoneTerms = ['phone', 'tel', 'mobile'];
                    const locationTerms = ['location', 'address', 'city', 'state', 'zip'];
                    
                    const allText = (name + ' ' + id + ' ' + placeholder + ' ' + className).toLowerCase();
                    
                    if (searchTerms.some(term => allText.includes(term))) hints.push('search');
                    if (emailTerms.some(term => allText.includes(term))) hints.push('email');
                    if (nameTerms.some(term => allText.includes(term))) hints.push('name');
                    if (phoneTerms.some(term => allText.includes(term))) hints.push('phone');
                    if (locationTerms.some(term => allText.includes(term))) hints.push('location');
                    
                    return hints;
                }
            """)
            form_context["field_hints"] = field_hints
            
            return form_context
            
        except Exception as e:
            logger.debug("Failed to build form context", error=str(e))
            return {}
    
    async def _find_element_labels(self, handle: ElementHandle) -> List[str]:
        """
        Find labels associated with a form element
        
        Args:
            handle: Playwright element handle
            
        Returns:
            List of label texts
        """
        try:
            labels = await handle.evaluate("""
                el => {
                    const labels = [];
                    
                    // Find label by 'for' attribute
                    if (el.id) {
                        const labelFor = document.querySelector(`label[for="${el.id}"]`);
                        if (labelFor) labels.push(labelFor.textContent?.trim());
                    }
                    
                    // Find parent label
                    const parentLabel = el.closest('label');
                    if (parentLabel) {
                        labels.push(parentLabel.textContent?.trim());
                    }
                    
                    // Find aria-label
                    if (el.getAttribute('aria-label')) {
                        labels.push(el.getAttribute('aria-label'));
                    }
                    
                    // Find aria-labelledby
                    const labelledBy = el.getAttribute('aria-labelledby');
                    if (labelledBy) {
                        const labelElement = document.getElementById(labelledBy);
                        if (labelElement) labels.push(labelElement.textContent?.trim());
                    }
                    
                    return labels.filter(l => l && l.length > 0);
                }
            """)
            
            return labels or []
            
        except Exception as e:
            logger.debug("Failed to find element labels", error=str(e))
            return []
    
    async def _generate_selector(self, handle: ElementHandle) -> str:
        """
        Generate a reliable CSS selector for the element
        
        Args:
            handle: Playwright element handle
            
        Returns:
            CSS selector string
        """
        try:
            selector = await handle.evaluate("""
                el => {
                    // Try ID first
                    if (el.id) return `#${el.id}`;
                    
                    // Try name attribute
                    if (el.name) return `[name="${el.name}"]`;
                    
                    // Try unique class combination
                    if (el.className) {
                        const classes = el.className.split(' ').filter(c => c.trim());
                        if (classes.length > 0) {
                            return '.' + classes.join('.');
                        }
                    }
                    
                    // Try data attributes
                    for (let attr of el.attributes) {
                        if (attr.name.startsWith('data-') && attr.value) {
                            return `[${attr.name}="${attr.value}"]`;
                        }
                    }
                    
                    // Fallback to tag name with position
                    const siblings = Array.from(el.parentElement?.children || []);
                    const sameTagSiblings = siblings.filter(s => s.tagName === el.tagName);
                    if (sameTagSiblings.length === 1) {
                        return el.tagName.toLowerCase();
                    } else {
                        const index = sameTagSiblings.indexOf(el) + 1;
                        return `${el.tagName.toLowerCase()}:nth-of-type(${index})`;
                    }
                }
            """)
            
            return selector or "unknown"
            
        except Exception as e:
            logger.debug("Failed to generate selector", error=str(e))
            return "unknown"
    
    def _is_element_visible(self, element_data: Dict[str, Any]) -> bool:
        """
        Check if element is visible and relevant for interaction
        
        Args:
            element_data: Element data dictionary
            
        Returns:
            True if element should be included in AI analysis
        """
        # Must be visible
        if not element_data.get("is_visible", False):
            return False
        
        # Must have reasonable size
        bbox = element_data.get("bounding_box")
        if bbox and (bbox["width"] < 10 or bbox["height"] < 10):
            return False
        
        # Must have some content or meaningful attributes
        text = element_data.get("text_content", "").strip()
        attrs = element_data.get("attributes", {})
        
        if not text and not any(attrs.get(attr) for attr in ["placeholder", "aria-label", "title", "alt"]):
            return False
        
        return True
    
    def _is_form_element_relevant(self, element_data: Dict[str, Any]) -> bool:
        """
        Check if form element is relevant for prospect hunting
        
        Args:
            element_data: Element data dictionary
            
        Returns:
            True if form element is relevant
        """
        tag_name = element_data.get("tag_name", "")
        attrs = element_data.get("attributes", {})
        
        # Skip hidden inputs (except search)
        if tag_name == "input" and attrs.get("type") == "hidden":
            return False
        
        # Skip submit buttons without meaningful text
        if tag_name == "input" and attrs.get("type") in ["submit", "button"]:
            text = element_data.get("text_content", "").strip()
            value = attrs.get("value", "").strip()
            if not text and not value:
                return False
        
        return True
    
    def _is_content_relevant(self, element_data: Dict[str, Any]) -> bool:
        """
        Check if content element contains relevant information
        
        Args:
            element_data: Element data dictionary
            
        Returns:
            True if content is relevant for prospect analysis
        """
        text = element_data.get("text_content", "").strip()
        
        # Must have meaningful text content
        if len(text) < 3:
            return False
        
        # Skip common UI text
        skip_patterns = [
            r"^(click|tap|press|select|choose|go|back|next|previous|home|menu)$",
            r"^(yes|no|ok|cancel|close|open|save|delete|edit|update)$",
            r"^\d+$",  # Just numbers
            r"^[^\w\s]+$"  # Just symbols
        ]
        
        for pattern in skip_patterns:
            if re.match(pattern, text.lower()):
                return False
        
        return True
    
    def _analyze_content_type(self, element_data: Dict[str, Any]) -> str:
        """
        Analyze the type of content for better AI understanding
        
        Args:
            element_data: Element data dictionary
            
        Returns:
            Content type classification
        """
        text = element_data.get("text_content", "").lower()
        tag_name = element_data.get("tag_name", "")
        
        # Heading classification
        if tag_name in ["h1", "h2", "h3", "h4", "h5", "h6"]:
            return "heading"
        
        # Contact information patterns
        if re.search(r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b', text):
            return "contact_email"
        
        if re.search(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', text):
            return "contact_phone"
        
        # Event-related keywords
        event_keywords = [
            "wedding", "birthday", "anniversary", "celebration", "party",
            "corporate", "conference", "meeting", "event", "planning",
            "venue", "catering", "photography", "music", "decoration"
        ]
        
        if any(keyword in text for keyword in event_keywords):
            return "event_related"
        
        # Business information
        business_keywords = [
            "company", "business", "service", "professional", "experience",
            "about", "contact", "location", "hours", "price", "cost"
        ]
        
        if any(keyword in text for keyword in business_keywords):
            return "business_info"
        
        return "general_content" 
   
    async def build_element_context(self, element: Dict[str, Any], surrounding_text: str = "") -> Dict[str, Any]:
        """
        Build comprehensive context for an element to help AI understand its purpose
        
        Args:
            element: Element data dictionary
            surrounding_text: Additional surrounding text context
            
        Returns:
            Enhanced element data with context
        """
        try:
            # Start with the original element data
            enhanced_element = element.copy()
            
            # Add surrounding text if provided
            if surrounding_text:
                enhanced_element["surrounding_text"] = surrounding_text[:200]
            
            # Analyze element purpose based on attributes and content
            purpose_analysis = self._analyze_element_purpose(element)
            enhanced_element["purpose_analysis"] = purpose_analysis
            
            # Add interaction hints for AI
            interaction_hints = self._generate_interaction_hints(element)
            enhanced_element["interaction_hints"] = interaction_hints
            
            # Add relevance score for task prioritization
            relevance_score = self._calculate_relevance_score(element)
            enhanced_element["relevance_score"] = relevance_score
            
            return enhanced_element
            
        except Exception as e:
            logger.debug("Failed to build element context", error=str(e))
            return element
    
    def _analyze_element_purpose(self, element: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze the likely purpose of an element for AI understanding
        
        Args:
            element: Element data dictionary
            
        Returns:
            Purpose analysis dictionary
        """
        tag_name = element.get("tag_name", "")
        attrs = element.get("attributes", {})
        text = element.get("text_content", "").lower()
        
        purpose = {
            "primary_function": "unknown",
            "interaction_type": "none",
            "data_type": "unknown",
            "confidence": 0.0
        }
        
        # Analyze based on tag name and attributes
        if tag_name == "input":
            input_type = attrs.get("type", "text").lower()
            purpose["primary_function"] = "input"
            purpose["interaction_type"] = "type"
            
            if input_type in ["search", "text"] and any(term in (attrs.get("name", "") + attrs.get("placeholder", "")).lower() 
                                                      for term in ["search", "query", "find"]):
                purpose["data_type"] = "search_query"
                purpose["confidence"] = 0.9
            elif input_type == "email" or "email" in (attrs.get("name", "") + attrs.get("placeholder", "")).lower():
                purpose["data_type"] = "email"
                purpose["confidence"] = 0.9
            elif input_type == "tel" or any(term in (attrs.get("name", "") + attrs.get("placeholder", "")).lower() 
                                           for term in ["phone", "tel", "mobile"]):
                purpose["data_type"] = "phone"
                purpose["confidence"] = 0.8
            else:
                purpose["data_type"] = input_type
                purpose["confidence"] = 0.6
                
        elif tag_name == "button" or (tag_name == "input" and attrs.get("type") in ["submit", "button"]):
            purpose["primary_function"] = "action"
            purpose["interaction_type"] = "click"
            
            if any(term in text for term in ["search", "find", "go", "submit"]):
                purpose["data_type"] = "search_submit"
                purpose["confidence"] = 0.9
            elif any(term in text for term in ["next", "more", "continue"]):
                purpose["data_type"] = "navigation"
                purpose["confidence"] = 0.8
            else:
                purpose["data_type"] = "general_action"
                purpose["confidence"] = 0.6
                
        elif tag_name == "a":
            purpose["primary_function"] = "navigation"
            purpose["interaction_type"] = "click"
            href = attrs.get("href", "")
            
            if "mailto:" in href:
                purpose["data_type"] = "email_link"
                purpose["confidence"] = 0.9
            elif "tel:" in href:
                purpose["data_type"] = "phone_link"
                purpose["confidence"] = 0.9
            elif any(term in text for term in ["contact", "about", "service"]):
                purpose["data_type"] = "info_link"
                purpose["confidence"] = 0.8
            else:
                purpose["data_type"] = "general_link"
                purpose["confidence"] = 0.6
                
        elif tag_name == "select":
            purpose["primary_function"] = "selection"
            purpose["interaction_type"] = "select"
            purpose["data_type"] = "dropdown"
            purpose["confidence"] = 0.8
            
        return purpose
    
    def _generate_interaction_hints(self, element: Dict[str, Any]) -> List[str]:
        """
        Generate hints for AI on how to interact with this element
        
        Args:
            element: Element data dictionary
            
        Returns:
            List of interaction hints
        """
        hints = []
        tag_name = element.get("tag_name", "")
        attrs = element.get("attributes", {})
        purpose = element.get("purpose_analysis", {})
        
        # Basic interaction hints based on element type
        if tag_name == "input":
            input_type = attrs.get("type", "text")
            if input_type in ["text", "search", "email", "tel"]:
                hints.append("type_text")
                
                # Specific hints based on purpose
                if purpose.get("data_type") == "search_query":
                    hints.append("enter_search_terms")
                elif purpose.get("data_type") == "email":
                    hints.append("enter_email_address")
                elif purpose.get("data_type") == "phone":
                    hints.append("enter_phone_number")
                    
        elif tag_name == "button" or (tag_name == "input" and attrs.get("type") in ["submit", "button"]):
            hints.append("click")
            
            if purpose.get("data_type") == "search_submit":
                hints.append("submit_search")
            elif purpose.get("data_type") == "navigation":
                hints.append("navigate_forward")
                
        elif tag_name == "a":
            hints.append("click")
            hints.append("navigate")
            
        elif tag_name == "select":
            hints.append("select_option")
            
        # Add context-specific hints
        text = element.get("text_content", "").lower()
        if "next" in text or "more" in text:
            hints.append("pagination")
        if "contact" in text:
            hints.append("contact_info")
        if any(term in text for term in ["wedding", "event", "party", "celebration"]):
            hints.append("event_related")
            
        return hints
    
    def _calculate_relevance_score(self, element: Dict[str, Any]) -> float:
        """
        Calculate relevance score for task prioritization
        
        Args:
            element: Element data dictionary
            
        Returns:
            Relevance score (0.0 to 1.0)
        """
        score = 0.0
        
        # Base score from purpose confidence
        purpose = element.get("purpose_analysis", {})
        score += purpose.get("confidence", 0.0) * 0.3
        
        # Boost for search-related elements
        if purpose.get("data_type") in ["search_query", "search_submit"]:
            score += 0.4
        
        # Boost for contact information
        if purpose.get("data_type") in ["email", "phone", "email_link", "phone_link"]:
            score += 0.3
        
        # Boost for navigation elements
        if purpose.get("data_type") in ["navigation", "info_link"]:
            score += 0.2
        
        # Boost for visible and enabled elements
        if element.get("is_visible", False):
            score += 0.1
        if element.get("is_enabled", False):
            score += 0.1
        
        # Boost for elements with good text content
        text = element.get("text_content", "").strip()
        if len(text) > 3:
            score += 0.1
        
        # Event planning relevance boost
        text_lower = text.lower()
        event_keywords = ["wedding", "event", "party", "celebration", "planning", "venue", "catering"]
        if any(keyword in text_lower for keyword in event_keywords):
            score += 0.2
        
        return min(score, 1.0)  # Cap at 1.0
    
    async def create_ai_prompt_data(self, page_structure: Dict[str, Any], task_goal: str) -> str:
        """
        Create structured JSON output optimized for AI consumption
        
        Args:
            page_structure: Complete page structure from extract_page_structure
            task_goal: The goal/task the AI should accomplish
            
        Returns:
            JSON string formatted for AI analysis
        """
        try:
            # Prioritize elements by relevance score
            all_elements = []
            
            # Add interactive elements
            for element in page_structure.get("interactive_elements", []):
                element["category"] = "interactive"
                all_elements.append(element)
            
            # Add form elements
            for element in page_structure.get("form_elements", []):
                element["category"] = "form"
                all_elements.append(element)
            
            # Add high-relevance content elements
            for element in page_structure.get("content_elements", []):
                if element.get("relevance_score", 0) > 0.5:
                    element["category"] = "content"
                    all_elements.append(element)
            
            # Sort by relevance score
            all_elements.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
            
            # Limit to top elements for AI processing
            top_elements = all_elements[:25]
            
            # Create AI-optimized structure
            ai_data = {
                "task_goal": task_goal,
                "page_info": {
                    "url": page_structure["page_info"]["url"],
                    "title": page_structure["page_info"]["title"]
                },
                "prioritized_elements": [
                    {
                        "id": elem["id"],
                        "category": elem["category"],
                        "tag_name": elem["tag_name"],
                        "text": elem.get("text_content", "")[:100],  # Limit text for AI
                        "selector": elem["selector"],
                        "purpose": elem.get("purpose_analysis", {}),
                        "interaction_hints": elem.get("interaction_hints", []),
                        "relevance_score": elem.get("relevance_score", 0),
                        "attributes": {k: v for k, v in elem.get("attributes", {}).items() 
                                     if k in ["id", "name", "type", "placeholder", "aria-label", "href"]},
                        "labels": elem.get("labels", []),
                        "is_visible": elem.get("is_visible", False),
                        "is_enabled": elem.get("is_enabled", False)
                    }
                    for elem in top_elements
                ],
                "page_summary": {
                    "total_interactive": len(page_structure.get("interactive_elements", [])),
                    "total_forms": len(page_structure.get("form_elements", [])),
                    "total_content": len(page_structure.get("content_elements", [])),
                    "high_relevance_elements": len([e for e in all_elements if e.get("relevance_score", 0) > 0.7])
                }
            }
            
            return json.dumps(ai_data, indent=2)
            
        except Exception as e:
            logger.error("Failed to create AI prompt data", error=str(e))
            return json.dumps({"error": "Failed to create AI prompt data", "task_goal": task_goal})
    
    def prioritize_elements_by_task(self, elements: List[Dict[str, Any]], task_type: str) -> List[Dict[str, Any]]:
        """
        Prioritize elements based on specific task requirements
        
        Args:
            elements: List of element data dictionaries
            task_type: Type of task ("search", "contact", "navigation", "extraction")
            
        Returns:
            Prioritized list of elements
        """
        try:
            # Create scoring weights based on task type
            task_weights = {
                "search": {
                    "search_query": 1.0,
                    "search_submit": 0.9,
                    "dropdown": 0.6,
                    "general_action": 0.3
                },
                "contact": {
                    "email": 1.0,
                    "phone": 1.0,
                    "email_link": 0.9,
                    "phone_link": 0.9,
                    "contact_info": 0.8,
                    "info_link": 0.6
                },
                "navigation": {
                    "navigation": 1.0,
                    "general_link": 0.8,
                    "info_link": 0.7,
                    "general_action": 0.5
                },
                "extraction": {
                    "event_related": 1.0,
                    "business_info": 0.9,
                    "contact_email": 0.8,
                    "contact_phone": 0.8,
                    "general_content": 0.4
                }
            }
            
            weights = task_weights.get(task_type, {})
            
            # Calculate task-specific scores
            for element in elements:
                base_score = element.get("relevance_score", 0)
                purpose = element.get("purpose_analysis", {})
                data_type = purpose.get("data_type", "unknown")
                
                # Apply task-specific weight
                task_weight = weights.get(data_type, 0.1)
                element["task_relevance_score"] = base_score * task_weight
            
            # Sort by task relevance
            elements.sort(key=lambda x: x.get("task_relevance_score", 0), reverse=True)
            
            return elements
            
        except Exception as e:
            logger.error("Failed to prioritize elements by task", task_type=task_type, error=str(e))
            return elements
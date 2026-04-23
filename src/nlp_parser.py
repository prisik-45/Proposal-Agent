"""
NLP Parser to extract proposal parameters from natural language input.
Approach B: One-shot input with natural language understanding.
"""

import re
from typing import Dict, Optional


def extract_proposal_params(user_input: str) -> Dict:
    """
    Extract proposal parameters from natural language input.
    Handles flexible, conversational input.
    
    Example inputs:
    - "Create proposal for TechCorp to build AI agent, 60 days, ₹40,000-60,000, includes AI model development • API integration • 3 months support"
    - "Proposal for ABC Company, website development, 45 days, budget 25k-35k, full development with domain and SEO"
    - "Build e-commerce site for ShopHub in 75 days, ₹30,000 to ₹50,000, includes payments and inventory"
    """
    
    params = {
        "client_business_name": None,
        "client_requirements": None,
        "timeline_days": None,
        "price_min": None,
        "price_max": None,
        "includes_text": None,
        "scope_of_work_max_words": None,
    }
    
    # Convert to lowercase for pattern matching
    text_lower = user_input.lower()
    text_original = user_input
    
    # ========== Extract Client Business Name ==========
    # Patterns: "for {company}", "company {name}", "business {name}", "client {name}"
    business_patterns = [
        r'for\s+([A-Za-z\s&\-\.]+?)(?:\s+to\s+|,\s+)',
        r'(?:company|business|client|organization)\s+([A-Za-z\s&\-\.]+?)(?:\s+to|,|$)',
    ]
    
    for pattern in business_patterns:
        match = re.search(pattern, text_lower)
        if match:
            params["client_business_name"] = match.group(1).strip()
            break
    
    # ========== Extract Requirements ==========
    # Look for action keywords followed by what needs to be done
    # Strategy: Extract text after "build/create/develop" and before timeline/budget indicators
    
    # First, try to find explicit service types
    service_keywords = [
        'website', 'web application', 'app', 'application', 'platform', 'system',
        'dashboard', 'solution', 'agent', 'chatbot', 'ai automation', 'ai', 'automation',
        'social media management', 'mobile app', 'ecommerce', 'e-commerce'
    ]
    
    # Check if any service keyword is explicitly mentioned
    for service in service_keywords:
        if service in text_lower:
            params["client_requirements"] = service
            break
    
    # If not found explicitly, try pattern-based extraction
    if not params["client_requirements"]:
        pattern = r'(?:build|develop|create|design|manage|set.?up)\s+(?:an?\s+)?([^,\d]+?)(?:\s+in\s+\d+|\s+for\s+\d+|,)'
        match = re.search(pattern, text_lower)
        if match:
            req = match.group(1).strip()
            req = re.sub(r'\b(?:a|an|the)\b', '', req).strip()
            if req and len(req) > 2:
                params["client_requirements"] = req
    
    # ========== Extract Timeline (Days) ==========
    timeline_patterns = [
        r'(\d+)\s*(?:days?|d)(?:\s|,|$)',
        r'timeline\s*:?\s*(\d+)\s*days?',
        r'(?:in|within|over)\s+(\d+)\s*days?',
    ]
    
    for pattern in timeline_patterns:
        match = re.search(pattern, text_lower)
        if match:
            params["timeline_days"] = int(match.group(1))
            break
    
    # ========== Extract Budget Range ==========
    # Patterns: "₹X,XXX-Y,YYY", "X,000-Y,000", "budget X to Y", "X thousand to Y thousand"
    budget_patterns = [
        r'[₹$]?(\d+(?:,\d+)*)\s*-\s*[₹$]?(\d+(?:,\d+)*)',
        r'(?:₹|budget|price|cost)\s+[₹$]?(\d+(?:,\d+)*)\s*(?:to|-)\s*[₹$]?(\d+(?:,\d+)*)',
    ]
    
    for pattern in budget_patterns:
        match = re.search(pattern, text_lower)
        if match:
            min_price = match.group(1).replace(',', '')
            max_price = match.group(2).replace(',', '')
            params["price_min"] = min_price
            params["price_max"] = max_price
            break
    
    # ========== Extract Includes/Deliverables ==========
    # Patterns: "includes X • Y • Z", "with X, Y, Z", "contains X, Y, Z"
    includes_patterns = [
        r'(?:includes?|contains?|with|deliverables?|involves?)\s*(?::)?\s*(.+?)(?:,\s*(?:timeline|days|budget|word limit|scope)|$)',
    ]
    
    for pattern in includes_patterns:
        match = re.search(pattern, text_original)
        if match:
            includes_text = match.group(1).strip()
            # Clean up formatting
            includes_text = re.sub(r'\s+•\s+', ' • ', includes_text)
            includes_text = re.sub(r',\s+', ' • ', includes_text)
            # Remove word limit info if present
            includes_text = re.sub(r',?\s*(?:word\s+)?limit.*$', '', includes_text)
            params["includes_text"] = includes_text.strip()
            break
    
    # ========== Extract Word Limits ==========
    # Patterns: "200 words", "max 300 words", "word limit 250", "scope 200w"
    word_limit_patterns = [
        r'(?:scope|section)\s*(?:of\s+work)?\s*(?:limit|max|max\s+word)?\s*(?:to\s+)?(\d+)\s*w(?:ords?)?',
        r'(\d+)\s*words?\s+(?:max|only|limit|for\s+scope)',
        r'word\s+limit\s*:?\s*(\d+)',
    ]
    
    for pattern in word_limit_patterns:
        match = re.search(pattern, text_lower)
        if match:
            params["scope_of_work_max_words"] = int(match.group(1))
            break
    
    return params


def validate_extracted_params(params: Dict) -> tuple[bool, Optional[str]]:
    """
    Validate extracted parameters.
    Returns: (is_valid, error_message)
    """
    required = ["client_business_name", "client_requirements", "timeline_days", "price_min", "price_max", "includes_text"]
    
    missing = [key for key in required if not params.get(key)]
    
    if missing:
        return False, f"Missing required fields: {', '.join(missing)}"
    
    # Validate timeline
    try:
        if params["timeline_days"] < 1 or params["timeline_days"] > 365:
            return False, "Timeline must be between 1 and 365 days"
    except (ValueError, TypeError):
        return False, "Timeline must be a valid number"
    
    # Validate prices
    try:
        min_price = int(params["price_min"].replace(",", ""))
        max_price = int(params["price_max"].replace(",", ""))
        if min_price <= 0 or max_price <= 0:
            return False, "Prices must be positive values"
        if min_price > max_price:
            return False, "Minimum price cannot be greater than maximum price"
    except (ValueError, TypeError):
        return False, "Prices must be valid numbers"
    
    # Validate word limits if provided
    if params.get("scope_of_work_max_words"):
        if params["scope_of_work_max_words"] < 50 or params["scope_of_work_max_words"] > 1000:
            return False, "Word limit must be between 50 and 1000 words"
    
    return True, None


def format_extracted_params(params: Dict) -> Dict:
    """
    Format extracted parameters for consistency.
    """
    # Ensure price_min and price_max have proper formatting
    if params.get("price_min"):
        # Remove any non-digit characters except comma
        price_min = re.sub(r'[^\d,]', '', str(params["price_min"]))
        params["price_min"] = price_min if price_min else "0"
    
    if params.get("price_max"):
        price_max = re.sub(r'[^\d,]', '', str(params["price_max"]))
        params["price_max"] = price_max if price_max else "0"
    
    # Clean up includes text
    if params.get("includes_text"):
        includes = params["includes_text"]
        # Standardize bullet separator
        includes = re.sub(r'\s*[-–—]\s*', ' • ', includes)
        includes = re.sub(r'\s*[,]\s*', ' • ', includes)
        includes = re.sub(r'\s+•\s+', ' • ', includes)
        params["includes_text"] = includes
    
    return params

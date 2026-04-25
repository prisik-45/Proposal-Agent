"""
NLP Parser to extract proposal parameters from natural language input.
Approach B: One-shot input with natural language understanding.
"""

import re
from typing import Dict, Optional, Tuple


def _normalize_number_with_unit(value: str, unit: Optional[str]) -> int:
    value = value.strip().replace(',', '').replace(' ', '')
    try:
        amount = float(value)
    except ValueError:
        return 0

    if not unit:
        return int(round(amount))

    unit = unit.lower()
    if unit in ('k', 'thousand'):
        return int(round(amount * 1_000))
    if unit in ('m', 'million'):
        return int(round(amount * 1_000_000))
    if unit in ('lakh', 'lakhs'):
        return int(round(amount * 100_000))
    if unit in ('cr', 'crore'):
        return int(round(amount * 10_000_000))
    return int(round(amount))


def extract_timeline_days(user_input: str) -> Optional[int]:
    text = user_input.lower()
    patterns = [
        (r'(?:timeline|duration)\s*(?:is|:)?\s*(\d+(?:\.\d+)?)\s*(?:months?|mos?)', 30),
        (r'(?:timeline|duration)\s*(?:is|:)?\s*(\d+(?:\.\d+)?)\s*(?:weeks?|w)', 7),
        (r'(?:timeline|duration)\s*(?:is|:)?\s*(\d+(?:\.\d+)?)\s*(?:days?|d)', 1),
        (r'(?:in|within|over)\s+(\d+(?:\.\d+)?)\s*(?:months?|mos?)', 30),
        (r'(?:in|within|over)\s+(\d+(?:\.\d+)?)\s*(?:weeks?|w)', 7),
        (r'(?:in|within|over)\s+(\d+(?:\.\d+)?)\s*(?:days?|d)', 1),
        (r'(\d+(?:\.\d+)?)\s*(?:days?|d)(?!\s*(?:support|maintenance))', 1),
    ]

    for pattern, multiplier in patterns:
        match = re.search(pattern, text)
        if match:
            value = float(match.group(1))
            return int(round(value * multiplier))
    return None


def extract_budget_range(user_input: str) -> Optional[tuple[int, int]]:
    text = user_input.lower()
    pattern = re.compile(
        r'(?:₹|inr|rs\.?|budget|price|cost)?\s*([0-9]+(?:[\.,][0-9]+)?)\s*(k|m|lakh|lakhs|cr|crore)?\s*(?:to|-)\s*(?:₹|inr|rs\.?|budget|price|cost)?\s*([0-9]+(?:[\.,][0-9]+)?)\s*(k|m|lakh|lakhs|cr|crore)?'
    )
    match = pattern.search(text)
    if match:
        min_raw, min_unit, max_raw, max_unit = match.group(1), match.group(2), match.group(3), match.group(4)
        min_price = _normalize_number_with_unit(min_raw, min_unit)
        max_price = _normalize_number_with_unit(max_raw, max_unit)
        if min_price and max_price:
            if min_price > max_price:
                min_price, max_price = max_price, min_price
            return min_price, max_price
    return None


def extract_technology_stack_text(user_input: str) -> Optional[str]:
    patterns = [
        r'(?:technology stack|tech stack)\s*(?:should be|is|:)?\s*(.+?)(?:,\s*(?:timeline|days|budget|includes?|deliverables?|scope|word limit)|$)',
        r'(?:use|using|built with|build with)\s+(.+?)(?:\s+(?:technology|tech|stack))?(?:,\s*(?:timeline|days|budget|includes?|deliverables?|scope|word limit)|$)',
    ]

    for pattern in patterns:
        match = re.search(pattern, user_input, re.IGNORECASE)
        if match:
            value = match.group(1).strip(" .,")
            value = re.sub(r'\s+for\s+(?:the\s+)?(?:technology\s+stack|tech\s+stack|technology|tech)$', '', value, flags=re.IGNORECASE)
            if value and len(value) > 2:
                return value
    return None


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
        "technology_stack_text": None,
        "scope_of_work_max_words": None,
    }
    
    # Convert to lowercase for pattern matching
    text_lower = user_input.lower()
    text_original = user_input
    
    # ========== Extract Client Business Name ==========
    # Patterns: "client name is {company}", "for {company}", "company {name}"
    business_patterns = [
        r'(?:client\s*(?:business\s*)?name|business\s*name)\s*(?:is|as|:)?\s*([A-Za-z0-9\s&\-\.]+?)(?:\s*,|\s+then\b|\s+and\b|$)',
        r'for\s+([A-Za-z0-9\s&\-\.]+?)(?:\s+to\s+|,\s+)',
        r'(?:company|business|client|organization)\s+([A-Za-z0-9\s&\-\.]+?)(?:\s+to|,|$)',
    ]
    
    for pattern in business_patterns:
        match = re.search(pattern, text_original, re.IGNORECASE)
        if match:
            params["client_business_name"] = match.group(1).strip()
            break
    
    # ========== Extract Requirements ==========
    # Look for action keywords followed by what needs to be done
    # Strategy: Extract text after "build/create/develop" and before timeline/budget indicators
    
    # First, infer the primary requirement from the main request, not from includes.
    main_text = re.split(
        r',\s*(?:timeline|budget|includes?|deliverables?|with)\b',
        text_lower,
        maxsplit=1,
    )[0]
    if "social media" in main_text:
        params["client_requirements"] = "social media management"
    elif "website" in main_text or "web development" in main_text or "web app" in main_text:
        params["client_requirements"] = "website"
    elif "ai automation" in main_text or "automation" in main_text or "ai agent" in main_text or "chatbot" in main_text:
        params["client_requirements"] = "ai automation"

    # Then try explicit service types from the main request only.
    service_keywords = [
        'social media management',
        'website', 'web application', 'app', 'application', 'platform', 'system',
        'dashboard', 'solution', 'agent', 'chatbot', 'ai automation', 'automation',
        'mobile app', 'ecommerce', 'e-commerce'
    ]
    
    if not params["client_requirements"]:
        for service in service_keywords:
            if service in main_text:
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
        r'(?:timeline|duration)\s*(?:is|:)?\s*(\d+)\s*days?',
        r'(?:in|within|over)\s+(\d+)\s*days?',
        r'(\d+)\s*(?:days?|d)(?!\s*(?:support|maintenance))(?:\s|,|$)',
    ]
    
    for pattern in timeline_patterns:
        match = re.search(pattern, text_lower)
        if match:
            params["timeline_days"] = int(match.group(1))
            break

    if params["timeline_days"] is None:
        params["timeline_days"] = extract_timeline_days(user_input)

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

    if params["price_min"] is None or params["price_max"] is None:
        parsed_budget = extract_budget_range(user_input)
        if parsed_budget:
            params["price_min"], params["price_max"] = map(str, parsed_budget)

    params["technology_stack_text"] = extract_technology_stack_text(user_input)
    
    # ========== Extract Includes/Deliverables ==========
    # Patterns: "includes X • Y • Z", "with X, Y, Z", "contains X, Y, Z"
    includes_patterns = [
        r'(?:includes?|contains?|with|deliverables?|involves?)\s*(?::)?\s*(.+?)(?:,\s*(?:use|using|built with|build with|timeline|days|budget|word limit|scope|technology|tech stack)|$)',
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

    if params.get("technology_stack_text"):
        technology_stack = str(params["technology_stack_text"]).strip(" .,")
        technology_stack = re.sub(r'\s*[,]\s*', ', ', technology_stack)
        params["technology_stack_text"] = technology_stack
    
    return params

def _normalize_number_with_unit(value: str, unit: Optional[str]) -> int:
    value = value.strip().replace(',', '').replace(' ', '')
    try:
        amount = float(value)
    except ValueError:
        return 0

    if not unit:
        return int(round(amount))

    unit = unit.lower()
    if unit in ('k', 'thousand'):
        return int(round(amount * 1_000))
    if unit in ('m', 'million'):
        return int(round(amount * 1_000_000))
    if unit in ('lakh', 'lakhs'):
        return int(round(amount * 100_000))
    if unit in ('cr', 'crore'):
        return int(round(amount * 10_000_000))
    return int(round(amount))


def extract_timeline_days(user_input: str) -> Optional[int]:
    text = user_input.lower()

    patterns = [
        (r'(?:timeline|duration)\s*(?:is|:)?\s*(\d+(?:\.\d+)?)\s*(?:months?|mos?)', 30),
        (r'(?:timeline|duration)\s*(?:is|:)?\s*(\d+(?:\.\d+)?)\s*(?:weeks?|w)', 7),
        (r'(?:timeline|duration)\s*(?:is|:)?\s*(\d+(?:\.\d+)?)\s*(?:days?|d)', 1),
        (r'(?:in|within|over)\s+(\d+(?:\.\d+)?)\s*(?:months?|mos?)', 30),
        (r'(?:in|within|over)\s+(\d+(?:\.\d+)?)\s*(?:weeks?|w)', 7),
        (r'(?:in|within|over)\s+(\d+(?:\.\d+)?)\s*(?:days?|d)', 1),
        (r'(\d+(?:\.\d+)?)\s*(?:days?|d)(?!\s*(?:support|maintenance))', 1),
    ]

    for pattern, multiplier in patterns:
        match = re.search(pattern, text)
        if match:
            value = float(match.group(1))
            return int(round(value * multiplier))
    return None


def extract_budget_range(user_input: str) -> Optional[Tuple[int, int]]:
    text = user_input.lower()

    pattern = re.compile(
        r'(?:₹|inr|rs\.?|budget|price|cost)?\s*([0-9]+(?:[\.,][0-9]+)?)\s*(k|m|lakh|lakhs|cr|crore)?\s*(?:to|-)\s*(?:₹|inr|rs\.?|budget|price|cost)?\s*([0-9]+(?:[\.,][0-9]+)?)\s*(k|m|lakh|lakhs|cr|crore)?'
    )
    match = pattern.search(text)
    if match:
        min_raw, min_unit, max_raw, max_unit = match.group(1), match.group(2), match.group(3), match.group(4)
        min_price = _normalize_number_with_unit(min_raw, min_unit)
        max_price = _normalize_number_with_unit(max_raw, max_unit)
        if min_price and max_price:
            if min_price > max_price:
                min_price, max_price = max_price, min_price
            return min_price, max_price
    return None


def extract_update_fields(user_input: str) -> Dict[str, any]:
    updates: Dict[str, any] = {}

    timeline = extract_timeline_days(user_input)
    if timeline is not None:
        updates["timeline_days"] = timeline

    budget_range = extract_budget_range(user_input)
    if budget_range:
        updates["price_min"], updates["price_max"] = map(str, budget_range)

    technology_stack = extract_technology_stack_text(user_input)
    if technology_stack:
        updates["technology_stack_text"] = technology_stack

    # Try parsing includes if the user explicitly changes deliverables or scope
    includes_pattern = r'(?:includes?|contains?|with|deliverables?|involves?)\s*(?::)?\s*(.+?)(?:\.|$)'
    match = re.search(includes_pattern, user_input, re.IGNORECASE)
    if match:
        includes_text = match.group(1).strip()
        includes_text = re.sub(r'\s+•\s+', ' • ', includes_text)
        updates["includes_text"] = re.sub(r'\s*[,]+\s*', ' • ', includes_text)

    return updates

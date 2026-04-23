"""
Conversation Manager for understanding user modifications
Uses LLM to interpret natural language changes and update proposal state
"""

import json
import re
from typing import Dict, List, Any, Tuple, Optional
from groq import Groq

# Initialize Groq client
client = Groq()


class ConversationManager:
    """
    Manages conversational proposal modifications.
    Understands natural language changes and identifies what to modify.
    """
    
    MODIFICATION_KEYWORDS = [
        "change", "update", "modify", "increase", "decrease", "add", "remove",
        "make it", "set to", "use", "replace", "swap", "edit", "alter"
    ]
    
    FIELD_MAPPING = {
        "timeline": ["timeline", "days", "duration", "weeks", "months"],
        "price_min": ["minimum", "min price", "starting", "from"],
        "price_max": ["maximum", "max price", "up to", "budget", "end"],
        "client_business_name": ["client", "company", "business", "name"],
        "client_requirements": ["requirements", "needed", "want", "features", "scope"],
        "includes_text": ["includes", "deliverables", "provides", "package"]
    }
    
    def __init__(self):
        """Initialize conversation manager"""
        self.model = "mixtral-8x7b-32768"  # or use the configured model
    
    def understand_modification(
        self,
        user_message: str,
        current_state: Dict[str, Any],
        conversation_context: Optional[List[Dict[str, Any]]] = None
    ) -> Tuple[bool, Dict[str, Any], str]:
        """
        Understand if user is making modifications and extract what changed.
        
        Args:
            user_message: User's input
            current_state: Current proposal state
            conversation_context: Previous turns for context
        
        Returns:
            Tuple of (is_modification, extracted_changes, explanation)
        """
        # Check if it's a modification (simple keyword check)
        is_modification = self._is_modification(user_message)
        
        if not is_modification:
            # Might still be a modification, use LLM to understand
            return self._llm_understand_intent(
                user_message, 
                current_state, 
                conversation_context
            )
        
        # Extract specific changes
        changes = self._extract_changes(user_message, current_state)
        explanation = self._generate_explanation(changes)
        
        return (True, changes, explanation)
    
    def _is_modification(self, message: str) -> bool:
        """Check if message contains modification keywords"""
        message_lower = message.lower()
        return any(keyword in message_lower for keyword in self.MODIFICATION_KEYWORDS)
    
    def _extract_changes(
        self,
        user_message: str,
        current_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Extract specific field changes from user message"""
        changes = {}
        message_lower = user_message.lower()
        
        # Use regex patterns to find specific changes
        
        # Timeline changes (e.g., "60 days", "3 months", "90 days")
        timeline_patterns = [
            r'(\d+)\s*(?:days?|d)',
            r'(\d+)\s*(?:weeks?|w)',
            r'(\d+)\s*(?:months?|m)',
        ]
        
        for pattern in timeline_patterns:
            match = re.search(pattern, message_lower)
            if match:
                value = int(match.group(1))
                # Convert to days
                if "week" in pattern or "w" in pattern:
                    value *= 7
                elif "month" in pattern or "m" in pattern:
                    value *= 30
                changes["timeline_days"] = value
                break
        
        # Price changes (e.g., "₹40k", "40000", "40k to 60k")
        price_patterns = [
            r'₹\s*(\d+)k?\s*(?:to|-)\s*₹?\s*(\d+)k?',  # Range
            r'(\d+)k?\s*(?:to|-)\s*(\d+)k?',  # Range without currency
            r'(?:min|from|start).*?₹?\s*(\d+)k?',  # Min price
            r'(?:max|to|up to|budget).*?₹?\s*(\d+)k?',  # Max price
        ]
        
        for pattern in price_patterns:
            match = re.search(pattern, message_lower)
            if match:
                if "to" in pattern or "-" in pattern:
                    min_val = int(match.group(1))
                    max_val = int(match.group(2))
                    if "k" in match.group(0):
                        min_val *= 1000
                        max_val *= 1000
                    changes["price_min"] = str(min_val)
                    changes["price_max"] = str(max_val)
                break
        
        # Client name (e.g., "for TechCorp", "company is ABC")
        client_patterns = [
            r'(?:for|client|company|business)\s+([A-Za-z0-9\s]+)(?:\s+(?:to|build|create))?',
        ]
        
        for pattern in client_patterns:
            match = re.search(pattern, message_lower)
            if match:
                client_name = match.group(1).strip()
                # Filter out common keywords
                if client_name and len(client_name) > 2 and not any(
                    keyword in client_name.lower() 
                    for keyword in ["to", "build", "create", "make"]
                ):
                    changes["client_business_name"] = client_name
                break
        
        return changes
    
    def _generate_explanation(self, changes: Dict[str, Any]) -> str:
        """Generate human-readable explanation of changes"""
        if not changes:
            return "No specific changes detected."
        
        explanations = []
        
        if "timeline_days" in changes:
            explanations.append(f"⏱️ Timeline updated to {changes['timeline_days']} days")
        
        if "price_min" in changes or "price_max" in changes:
            min_val = changes.get("price_min", "N/A")
            max_val = changes.get("price_max", "N/A")
            explanations.append(f"💰 Budget updated to ₹{min_val} - ₹{max_val}")
        
        if "client_business_name" in changes:
            explanations.append(f"🏢 Client changed to {changes['client_business_name']}")
        
        if "client_requirements" in changes:
            explanations.append(f"📋 Requirements updated")
        
        if "includes_text" in changes:
            explanations.append(f"📦 Deliverables updated")
        
        return " | ".join(explanations)
    
    def _llm_understand_intent(
        self,
        user_message: str,
        current_state: Dict[str, Any],
        conversation_context: Optional[List[Dict[str, Any]]] = None
    ) -> Tuple[bool, Dict[str, Any], str]:
        """
        Use LLM to understand user intent when simple extraction fails.
        """
        # Build context for LLM
        context_text = json.dumps(current_state, indent=2)
        
        conversation_text = ""
        if conversation_context:
            for turn in conversation_context[-3:]:  # Last 3 turns
                conversation_text += f"User: {turn.get('user_message')}\n"
                conversation_text += f"Assistant: {turn.get('assistant_response')}\n\n"
        
        prompt = f"""You are a proposal modification understanding assistant.

Current Proposal State:
{context_text}

Previous Conversation:
{conversation_text}

User's Latest Message: "{user_message}"

Determine:
1. Is the user modifying the proposal? (yes/no)
2. What fields are they changing? (extract: timeline_days, price_min, price_max, etc.)
3. What are the new values?

Respond in JSON format:
{{
    "is_modification": true/false,
    "changes": {{
        "field_name": "new_value"
    }},
    "explanation": "brief explanation"
}}
"""
        
        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that understands proposal modification requests."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=500
            )
            
            response_text = response.choices[0].message.content
            
            # Extract JSON from response
            try:
                json_start = response_text.find("{")
                json_end = response_text.rfind("}") + 1
                json_str = response_text[json_start:json_end]
                result = json.loads(json_str)
                
                return (
                    result.get("is_modification", False),
                    result.get("changes", {}),
                    result.get("explanation", "Modified")
                )
            except (json.JSONDecodeError, ValueError):
                # If JSON parsing fails, return empty
                return (False, {}, "Could not parse modification")
        
        except Exception as e:
            print(f"LLM error: {e}")
            return (False, {}, f"Error understanding: {str(e)}")
    
    def generate_conversational_response(
        self,
        user_message: str,
        is_modification: bool,
        changes: Dict[str, Any],
        current_state: Dict[str, Any],
        explanation: str
    ) -> str:
        """
        Generate a conversational response acknowledging the modification.
        """
        if not is_modification:
            return explanation
        
        # Generate friendly response
        responses = [
            f"✅ Got it! {explanation}",
            f"📝 Understood. {explanation}",
            f"💡 Perfect! {explanation}",
            f"🔄 Updating... {explanation}",
        ]
        
        return responses[0]  # Simple selection


# Global instance
_manager = None


def get_manager() -> ConversationManager:
    """Get or create ConversationManager instance"""
    global _manager
    if _manager is None:
        _manager = ConversationManager()
    return _manager

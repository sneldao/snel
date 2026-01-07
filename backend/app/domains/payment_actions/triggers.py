"""Natural language trigger matching for payment actions."""
import logging
from typing import List, Tuple, Optional
from difflib import SequenceMatcher
from .models import PaymentAction

logger = logging.getLogger(__name__)


class TriggerMatch:
    """Result of trigger matching."""
    
    def __init__(
        self,
        action: PaymentAction,
        trigger: str,
        confidence: float,  # 0.0-1.0
    ):
        self.action = action
        self.trigger = trigger
        self.confidence = confidence
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            "action_id": self.action.id,
            "action_name": self.action.name,
            "trigger": self.trigger,
            "confidence": round(self.confidence, 2),
        }


class TriggerMatcher:
    """
    Match user input against payment action triggers.
    
    CLEAN: Single responsibility - trigger matching only
    MODULAR: Pluggable matching algorithms
    PERFORMANT: Fast string similarity matching
    """
    
    def __init__(self):
        """Initialize trigger matcher."""
        self.min_confidence = 0.6  # Require 60% similarity
    
    async def find_matching_actions(
        self,
        user_input: str,
        actions: List[PaymentAction],
        threshold: float = 0.6,
    ) -> List[TriggerMatch]:
        """
        Find payment actions matching user input via triggers.
        
        Args:
            user_input: User's natural language input
            actions: List of available payment actions
            threshold: Minimum confidence score (0.0-1.0)
        
        Returns:
            List of TriggerMatch sorted by confidence (descending)
        """
        matches = []
        user_input_lower = user_input.lower().strip()
        
        for action in actions:
            # Only check enabled actions with triggers
            if not action.is_enabled or not action.triggers:
                continue
            
            # Check each trigger
            for trigger in action.triggers:
                confidence = self._calculate_similarity(user_input_lower, trigger.lower())
                
                if confidence >= threshold:
                    matches.append(TriggerMatch(
                        action=action,
                        trigger=trigger,
                        confidence=confidence,
                    ))
                    logger.debug(f"Matched trigger '{trigger}' for action {action.name}: {confidence:.2f}")
        
        # Sort by confidence (highest first), then by action name
        matches.sort(key=lambda m: (-m.confidence, m.action.name))
        
        return matches
    
    async def find_best_match(
        self,
        user_input: str,
        actions: List[PaymentAction],
        threshold: float = 0.6,
    ) -> Optional[TriggerMatch]:
        """
        Find the single best matching action.
        
        Args:
            user_input: User's natural language input
            actions: List of available payment actions
            threshold: Minimum confidence score
        
        Returns:
            Best TriggerMatch or None if no good match found
        """
        matches = await self.find_matching_actions(user_input, actions, threshold)
        return matches[0] if matches else None
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate similarity between two strings (0.0-1.0).
        
        Uses SequenceMatcher for word-level similarity.
        Handles:
        - Exact matches (1.0)
        - Substring matches (high confidence)
        - Fuzzy matches (lower confidence)
        """
        # Exact match
        if text1 == text2:
            return 1.0
        
        # Substring match (bonus for containing key phrase)
        if text2 in text1 or text1 in text2:
            return 0.9
        
        # Split by words and check for word overlap
        words1 = set(text1.split())
        words2 = set(text2.split())
        
        if words1 and words2:
            word_overlap = len(words1 & words2) / max(len(words1), len(words2))
            # If any word matches, give higher confidence
            if word_overlap > 0.3:
                return min(0.8, 0.5 + word_overlap * 0.3)
        
        # Use SequenceMatcher for character-level similarity
        similarity = SequenceMatcher(None, text1, text2).ratio()
        
        return similarity


class TriggerAnalyzer:
    """
    Analyze and suggest triggers for actions.
    
    Helps users find the right triggers for their actions.
    """
    
    async def suggest_triggers(
        self,
        action_name: str,
        action_type: str,
        recipient: str = None,
        amount: str = None,
    ) -> List[str]:
        """
        Suggest natural language triggers for an action.
        
        Args:
            action_name: Name of the action (e.g., "Weekly Rent")
            action_type: Type of action (send, recurring, template, shortcut)
            recipient: Optional recipient name/label
            amount: Optional amount
        
        Returns:
            List of suggested trigger phrases
        """
        suggestions = []
        name_lower = action_name.lower()
        
        # From action name
        suggestions.append(name_lower)
        
        # Word variations
        words = name_lower.split()
        if len(words) > 1:
            suggestions.extend(words)
        
        # Common patterns for recurring payments
        if action_type == "recurring":
            for word in words:
                suggestions.extend([
                    f"time for {word}",
                    f"pay {word}",
                    f"send {word}",
                    f"time {word}",
                ])
        
        # For shortcuts
        elif action_type == "shortcut":
            for word in words:
                suggestions.extend([
                    f"i'll {word}",
                    f"need {word}",
                    f"{word} please",
                    f"do {word}",
                ])
        
        # Recipient-based (if available)
        if recipient:
            recipient_lower = recipient.lower()
            suggestions.append(f"pay {recipient_lower}")
            suggestions.append(f"send to {recipient_lower}")
        
        # Amount-based (if available)
        if amount:
            suggestions.append(f"send {amount}")
            suggestions.append(f"transfer {amount}")
        
        # Remove duplicates, preserve order
        seen = set()
        unique = []
        for s in suggestions:
            if s not in seen:
                seen.add(s)
                unique.append(s)
        
        return unique[:8]  # Return top 8 suggestions


# Singleton instances
_matcher_instance: Optional[TriggerMatcher] = None
_analyzer_instance: Optional[TriggerAnalyzer] = None


async def get_trigger_matcher() -> TriggerMatcher:
    """Get or create singleton trigger matcher."""
    global _matcher_instance
    if _matcher_instance is None:
        _matcher_instance = TriggerMatcher()
    return _matcher_instance


async def get_trigger_analyzer() -> TriggerAnalyzer:
    """Get or create singleton trigger analyzer."""
    global _analyzer_instance
    if _analyzer_instance is None:
        _analyzer_instance = TriggerAnalyzer()
    return _analyzer_instance

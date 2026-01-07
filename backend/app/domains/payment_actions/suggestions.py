"""Smart suggestion engine for payment actions based on usage patterns."""
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from .models import PaymentAction

logger = logging.getLogger(__name__)


class ActionSuggestion:
    """Suggestion for a payment action."""
    
    def __init__(
        self,
        action: PaymentAction,
        reason: str,  # Why this action is suggested
        score: float,  # 0.0-1.0 relevance score
    ):
        self.action = action
        self.reason = reason
        self.score = score
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            "action_id": self.action.id,
            "action_name": self.action.name,
            "reason": self.reason,
            "score": round(self.score, 2),
            "last_used": self.action.last_used.isoformat() if self.action.last_used else None,
            "usage_count": self.action.usage_count,
        }


class SuggestionEngine:
    """
    Suggest payment actions based on usage patterns.
    
    MODULAR: Pluggable scoring algorithms
    PERFORMANT: O(n) analysis without external ML
    ORGANIZED: Single engine for all suggestion logic
    """
    
    def __init__(self):
        """Initialize suggestion engine."""
        # Scoring weights
        self.weight_recent = 0.4  # Recency matters most
        self.weight_frequent = 0.4  # Frequency matters too
        self.weight_pinned = 0.2  # Pinned actions get slight boost
    
    async def suggest_actions(
        self,
        actions: List[PaymentAction],
        context: Optional[Dict[str, Any]] = None,
        limit: int = 3,
    ) -> List[ActionSuggestion]:
        """
        Suggest payment actions based on usage patterns.
        
        Scoring factors:
        - Recency: Recently used actions more relevant
        - Frequency: Frequently used actions more likely to repeat
        - Pinned: User-pinned actions indicate preference
        - Type: Recurring payments high priority
        
        Args:
            actions: List of user's payment actions
            context: Optional context (time of day, day of week, etc.)
            limit: Number of suggestions to return
        
        Returns:
            Sorted list of ActionSuggestion
        """
        if not actions:
            return []
        
        suggestions = []
        now = datetime.utcnow()
        
        for action in actions:
            if not action.is_enabled:
                continue
            
            score = 0.0
            reason = ""
            
            # Score by recency
            if action.last_used:
                days_ago = (now - action.last_used).days
                recency_score = self._score_recency(days_ago)
                score += recency_score * self.weight_recent
                
                if days_ago == 0:
                    reason += "Used today. "
                elif days_ago == 1:
                    reason += "Used yesterday. "
                elif days_ago < 7:
                    reason += "Recently used. "
            else:
                # Never used - low recency score
                reason += "Available. "
            
            # Score by frequency
            if action.usage_count > 0:
                frequency_score = self._score_frequency(action.usage_count)
                score += frequency_score * self.weight_frequent
                
                if action.usage_count >= 10:
                    reason += "Frequently used. "
                elif action.usage_count >= 3:
                    reason += "Regularly used. "
            
            # Boost pinned actions
            if action.is_pinned:
                score += 0.1 * self.weight_pinned
                reason += "Your favorite. "
            
            # Boost recurring payments
            if action.action_type.value == "recurring":
                score += 0.1
                reason += "Recurring payment. "
            
            # Apply context-based boosting
            if context:
                context_boost = self._score_context(action, context)
                score += context_boost
            
            # Normalize score to 0.0-1.0
            score = min(1.0, max(0.0, score))
            
            if score > 0:
                suggestions.append(ActionSuggestion(
                    action=action,
                    reason=reason.strip(),
                    score=score,
                ))
        
        # Sort by score (highest first)
        suggestions.sort(key=lambda s: -s.score)
        
        return suggestions[:limit]
    
    async def suggest_based_on_time(
        self,
        actions: List[PaymentAction],
        hour: int = None,
        day_of_week: int = None,
        limit: int = 3,
    ) -> List[ActionSuggestion]:
        """
        Suggest actions based on time of day and day of week.
        
        For example:
        - Friday afternoons → suggest weekend transfers
        - Monday mornings → suggest weekly recurring payments
        - Evenings → suggest personal transfers
        
        Args:
            actions: List of user's payment actions
            hour: Hour of day (0-23), defaults to current
            day_of_week: Day of week (0=Mon, 6=Sun), defaults to current
            limit: Number of suggestions
        
        Returns:
            Sorted list of ActionSuggestion
        """
        if hour is None:
            hour = datetime.utcnow().hour
        if day_of_week is None:
            day_of_week = datetime.utcnow().weekday()
        
        context = {
            "hour": hour,
            "day_of_week": day_of_week,
            "is_evening": hour >= 18,
            "is_weekend": day_of_week >= 5,
            "is_monday": day_of_week == 0,
            "is_friday": day_of_week == 4,
        }
        
        return await self.suggest_actions(actions, context, limit)
    
    async def suggest_overdue_recurring(
        self,
        actions: List[PaymentAction],
        limit: int = 5,
    ) -> List[ActionSuggestion]:
        """
        Suggest recurring payments that are due or overdue.
        
        Args:
            actions: List of user's payment actions
            limit: Number of suggestions
        
        Returns:
            List of recurring actions that should be executed soon
        """
        suggestions = []
        now = datetime.utcnow()
        
        for action in actions:
            if not action.is_enabled or not action.schedule:
                continue
            
            if action.action_type.value != "recurring":
                continue
            
            # Check if action should run based on schedule
            days_overdue = self._days_overdue(action, now)
            
            if days_overdue >= 0:  # Action is due or overdue
                suggestion = ActionSuggestion(
                    action=action,
                    reason=f"Due {days_overdue} days ago" if days_overdue > 0 else "Due today",
                    score=min(1.0, 0.5 + days_overdue * 0.1),  # Higher score if more overdue
                )
                suggestions.append(suggestion)
        
        # Sort by overdue days (most overdue first)
        suggestions.sort(key=lambda s: -s.score)
        
        return suggestions[:limit]
    
    def _score_recency(self, days_ago: int) -> float:
        """Score action by recency (0.0-1.0)."""
        if days_ago < 1:
            return 1.0
        elif days_ago < 7:
            return 0.8
        elif days_ago < 30:
            return 0.5
        else:
            return 0.2
    
    def _score_frequency(self, usage_count: int) -> float:
        """Score action by frequency of use (0.0-1.0)."""
        if usage_count >= 20:
            return 1.0
        elif usage_count >= 10:
            return 0.8
        elif usage_count >= 5:
            return 0.6
        elif usage_count >= 2:
            return 0.4
        else:
            return 0.2
    
    def _score_context(
        self,
        action: PaymentAction,
        context: Dict[str, Any],
    ) -> float:
        """Apply context-based scoring."""
        score = 0.0
        
        # Recurring payments more relevant on weekdays
        if action.action_type.value == "recurring" and not context.get("is_weekend"):
            score += 0.1
        
        # Personal transfers more relevant in evenings
        if action.action_type.value == "shortcut" and context.get("is_evening"):
            score += 0.1
        
        # Check schedule alignment
        if action.schedule and action.schedule.day_of_week is not None:
            if action.schedule.day_of_week == context.get("day_of_week"):
                score += 0.2  # Action scheduled for today
        
        return score
    
    def _days_overdue(self, action: PaymentAction, now: datetime) -> int:
        """
        Calculate days overdue for a recurring action.
        
        Returns:
            Days overdue (negative if not yet due, 0 if due today)
        """
        if not action.schedule or not action.last_used:
            return 0
        
        frequency = action.schedule.frequency.value
        
        # Map frequency to days
        interval_days = {
            "daily": 1,
            "weekly": 7,
            "monthly": 30,
        }.get(frequency, 30)
        
        days_since = (now - action.last_used).days
        days_overdue = days_since - interval_days
        
        return max(0, days_overdue)


# Singleton instance
_engine_instance: Optional[SuggestionEngine] = None


async def get_suggestion_engine() -> SuggestionEngine:
    """Get or create singleton suggestion engine."""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = SuggestionEngine()
    return _engine_instance

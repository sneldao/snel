"""Recurring payment scheduler for automated execution."""
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from enum import Enum

from .models import PaymentAction, PaymentActionFrequency
from .executor import ExecutionStatus

logger = logging.getLogger(__name__)


class ScheduleStatus(Enum):
    """Status of scheduled payment check."""
    NOT_DUE = "not_due"
    DUE = "due"
    OVERDUE = "overdue"
    SKIPPED = "skipped"


class ScheduleInfo:
    """Information about scheduled payment."""
    
    def __init__(
        self,
        action: PaymentAction,
        status: ScheduleStatus,
        next_due: Optional[datetime] = None,
        last_executed: Optional[datetime] = None,
        days_until_due: Optional[int] = None,
    ):
        self.action = action
        self.status = status
        self.next_due = next_due
        self.last_executed = last_executed
        self.days_until_due = days_until_due
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            "action_id": self.action.id,
            "action_name": self.action.name,
            "status": self.status.value,
            "next_due": self.next_due.isoformat() if self.next_due else None,
            "last_executed": self.last_executed.isoformat() if self.last_executed else None,
            "days_until_due": self.days_until_due,
            "amount": self.action.amount,
            "token": self.action.token,
        }


class RecurringScheduler:
    """
    Manage recurring payment scheduling.
    
    CLEAN: Single responsibility - schedule management
    MODULAR: Works with PaymentAction, ready for cron integration
    PERFORMANT: O(n) scan without database queries
    """
    
    async def get_due_actions(
        self,
        actions: List[PaymentAction],
        now: Optional[datetime] = None,
    ) -> List[ScheduleInfo]:
        """
        Get actions that are due or overdue for execution.
        
        Args:
            actions: List of payment actions to check
            now: Reference time (defaults to now)
        
        Returns:
            List of ScheduleInfo for due/overdue actions, sorted by urgency
        """
        if now is None:
            now = datetime.utcnow()
        
        due_actions = []
        
        for action in actions:
            if not action.is_enabled or not action.schedule:
                continue
            
            if action.action_type.value != "recurring":
                continue
            
            status_info = await self._get_schedule_status(action, now)
            
            # Include due and overdue actions
            if status_info.status in [ScheduleStatus.DUE, ScheduleStatus.OVERDUE]:
                due_actions.append(status_info)
        
        # Sort by urgency: overdue first, then by days
        due_actions.sort(key=lambda s: (
            s.status != ScheduleStatus.OVERDUE,  # Overdue first
            s.days_until_due or 0,  # Then by days until due
        ))
        
        return due_actions
    
    async def get_schedule_info(
        self,
        action: PaymentAction,
        now: Optional[datetime] = None,
    ) -> ScheduleInfo:
        """
        Get detailed schedule information for an action.
        
        Args:
            action: Payment action to check
            now: Reference time
        
        Returns:
            ScheduleInfo with detailed timing
        """
        if now is None:
            now = datetime.utcnow()
        
        if not action.schedule:
            return ScheduleInfo(
                action=action,
                status=ScheduleStatus.SKIPPED,
                last_executed=action.last_used,
            )
        
        return await self._get_schedule_status(action, now)
    
    async def get_upcoming_actions(
        self,
        actions: List[PaymentAction],
        days_ahead: int = 7,
        now: Optional[datetime] = None,
    ) -> List[ScheduleInfo]:
        """
        Get actions scheduled to run in the next N days.
        
        Args:
            actions: List of payment actions
            days_ahead: Number of days to look ahead
            now: Reference time
        
        Returns:
            List of ScheduleInfo for upcoming actions
        """
        if now is None:
            now = datetime.utcnow()
        
        upcoming = []
        cutoff = now + timedelta(days=days_ahead)
        
        for action in actions:
            if not action.is_enabled or not action.schedule:
                continue
            
            if action.action_type.value != "recurring":
                continue
            
            status_info = await self._get_schedule_status(action, now)
            
            # Include actions that are due within the timeframe
            if status_info.next_due and status_info.next_due <= cutoff:
                upcoming.append(status_info)
        
        # Sort by next due date
        upcoming.sort(key=lambda s: s.next_due or now)
        
        return upcoming
    
    async def _get_schedule_status(
        self,
        action: PaymentAction,
        now: datetime,
    ) -> ScheduleInfo:
        """
        Calculate schedule status for an action.
        
        Determines if action is due, overdue, or when it will be due next.
        """
        if not action.schedule:
            return ScheduleInfo(action=action, status=ScheduleStatus.SKIPPED)
        
        frequency = action.schedule.frequency
        last_used = action.last_used
        
        # Calculate next due date based on frequency
        if frequency == PaymentActionFrequency.DAILY:
            interval = timedelta(days=1)
        elif frequency == PaymentActionFrequency.WEEKLY:
            interval = timedelta(weeks=1)
            # Check day of week if specified
            if action.schedule.day_of_week is not None:
                target_dow = action.schedule.day_of_week
                current_dow = now.weekday()
                
                # If today is target day and not yet executed today, due now
                if current_dow == target_dow and (not last_used or last_used.date() < now.date()):
                    next_due = now.replace(hour=0, minute=0, second=0, microsecond=0)
                    days_until = 0
                    return ScheduleInfo(
                        action=action,
                        status=ScheduleStatus.DUE,
                        next_due=next_due,
                        last_executed=last_used,
                        days_until_due=days_until,
                    )
        elif frequency == PaymentActionFrequency.MONTHLY:
            interval = timedelta(days=30)
            # Check day of month if specified
            if action.schedule.day_of_month is not None:
                target_dom = action.schedule.day_of_month
                current_dom = now.day
                
                # If today is target day and not yet executed today, due now
                if current_dom == target_dom and (not last_used or last_used.date() < now.date()):
                    next_due = now.replace(hour=0, minute=0, second=0, microsecond=0)
                    days_until = 0
                    return ScheduleInfo(
                        action=action,
                        status=ScheduleStatus.DUE,
                        next_due=next_due,
                        last_executed=last_used,
                        days_until_due=days_until,
                    )
        else:
            return ScheduleInfo(action=action, status=ScheduleStatus.SKIPPED)
        
        # Calculate if due based on last execution + interval
        if not last_used:
            # Never executed - always due
            return ScheduleInfo(
                action=action,
                status=ScheduleStatus.DUE,
                next_due=now,
                last_executed=None,
                days_until_due=0,
            )
        
        next_due = last_used + interval
        days_until = (next_due - now).days
        
        if days_until <= 0:
            # Due or overdue
            status = ScheduleStatus.OVERDUE if days_until < 0 else ScheduleStatus.DUE
            return ScheduleInfo(
                action=action,
                status=status,
                next_due=next_due,
                last_executed=last_used,
                days_until_due=max(0, days_until),
            )
        else:
            # Not yet due
            return ScheduleInfo(
                action=action,
                status=ScheduleStatus.NOT_DUE,
                next_due=next_due,
                last_executed=last_used,
                days_until_due=days_until,
            )
    
    def get_schedule_description(self, action: PaymentAction) -> str:
        """
        Get human-readable description of schedule.
        
        Examples:
        - "Daily at midnight"
        - "Every Monday"
        - "30th of every month"
        """
        if not action.schedule:
            return "No schedule"
        
        frequency = action.schedule.frequency.value
        
        if frequency == "daily":
            return "Every day"
        elif frequency == "weekly":
            if action.schedule.day_of_week is not None:
                days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
                day_name = days[action.schedule.day_of_week]
                return f"Every {day_name}"
            return "Every week"
        elif frequency == "monthly":
            if action.schedule.day_of_month is not None:
                return f"On the {action.schedule.day_of_month}th of every month"
            return "Every month"
        
        return "Unknown schedule"


# Singleton instance
_scheduler_instance: Optional[RecurringScheduler] = None


async def get_recurring_scheduler() -> RecurringScheduler:
    """Get or create singleton recurring scheduler."""
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = RecurringScheduler()
    return _scheduler_instance

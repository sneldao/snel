"""
Keeper job for automatic recurring payment execution.

Runs periodically (e.g., every hour) to:
1. Find all due recurring payment actions
2. Validate they're enabled and executable
3. Execute them automatically
4. Track execution history

Can be run as:
- Background task in main app
- Separate service/worker process
- Scheduled job (APScheduler, Celery, etc.)
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from decimal import Decimal

from app.domains.payment_actions.service import get_payment_action_service
from app.domains.payment_actions.executor import get_payment_executor
from app.domains.payment_actions.models import PaymentAction, PaymentActionType, PaymentActionFrequency


logger = logging.getLogger(__name__)


class RecurringPaymentKeeper:
    """
    Manages automatic execution of recurring payment actions.
    
    Keeps payments on schedule by:
    - Checking all recurring actions daily
    - Identifying due payments
    - Executing them automatically
    - Recording results for audit trail
    """
    
    def __init__(self):
        self.service = None
        self.executor = None
        self.execution_log = {}  # In-memory, upgrade to DB later
    
    async def _init_services(self):
        """Lazy initialize services."""
        if self.service is None:
            self.service = await get_payment_action_service()
        if self.executor is None:
            self.executor = await get_payment_executor()
    
    async def run_check(self) -> Dict[str, Any]:
        """
        Run a keeper check to execute due recurring payments.
        
        Returns:
            Summary of check execution
        """
        try:
            await self._init_services()
            
            start_time = datetime.utcnow()
            logger.info("Starting recurring payment keeper check...")
            
            # Get all payment actions (could optimize to only recurring)
            all_wallets = await self.service.get_all_wallets()
            logger.info(f"Checking recurring payments for {len(all_wallets)} wallets")
            
            total_checked = 0
            total_executed = 0
            total_failed = 0
            
            # Check each wallet's actions
            for wallet_address in all_wallets:
                try:
                    actions = await self.service.get_actions(wallet_address, enabled_only=True)
                    
                    # Filter to recurring actions
                    recurring_actions = [
                        a for a in actions
                        if a.action_type == PaymentActionType.RECURRING and a.schedule
                    ]
                    
                    for action in recurring_actions:
                        total_checked += 1
                        
                        # Check if action is due
                        if self._is_due(action):
                            logger.info(f"Executing due recurring action: {action.id} ({action.name})")
                            
                            try:
                                # Execute the action
                                result = await self.executor.execute_action(action, wallet_address)
                                
                                if result.status.value in ["submitted", "completed"]:
                                    total_executed += 1
                                    
                                    # Mark as used
                                    await self.service.mark_used(wallet_address, action.id)
                                    
                                    # Record execution
                                    self._log_execution(
                                        action.id,
                                        wallet_address,
                                        "success",
                                        result.ticket_id,
                                    )
                                    
                                    logger.info(f"✓ Executed {action.name} (ticket: {result.ticket_id})")
                                
                                else:
                                    total_failed += 1
                                    self._log_execution(
                                        action.id,
                                        wallet_address,
                                        "failed",
                                        error=result.error_message,
                                    )
                                    logger.warning(f"✗ Failed to execute {action.name}: {result.error_message}")
                            
                            except Exception as e:
                                total_failed += 1
                                self._log_execution(
                                    action.id,
                                    wallet_address,
                                    "error",
                                    error=str(e),
                                )
                                logger.error(f"Error executing action {action.id}: {e}")
                
                except Exception as e:
                    logger.error(f"Error checking wallet {wallet_address}: {e}")
            
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()
            
            summary = {
                "timestamp": start_time.isoformat(),
                "duration_seconds": duration,
                "wallets_checked": len(all_wallets),
                "actions_checked": total_checked,
                "actions_executed": total_executed,
                "actions_failed": total_failed,
                "success_rate": (total_executed / total_checked * 100) if total_checked > 0 else 0,
            }
            
            logger.info(f"Keeper check completed: {summary}")
            return summary
        
        except Exception as e:
            logger.exception("Keeper check failed")
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e),
                "status": "failed",
            }
    
    def _is_due(self, action: PaymentAction) -> bool:
        """
        Check if a recurring action is due for execution.
        
        Args:
            action: Payment action to check
        
        Returns:
            True if action should be executed now
        """
        if not action.schedule:
            return False
        
        schedule = action.schedule
        now = datetime.utcnow()
        last_used = action.last_used
        
        # First execution: always execute
        if last_used is None:
            return True
        
        # Daily: execute every 24 hours
        if schedule.frequency == PaymentActionFrequency.DAILY:
            return (now - last_used) >= timedelta(days=1)
        
        # Weekly: execute on specified day if enough time has passed
        if schedule.frequency == PaymentActionFrequency.WEEKLY:
            target_day = schedule.day_of_week
            if target_day is None:
                target_day = last_used.weekday()  # Use original day if not specified
            
            # Check if enough time passed and it's the right day
            days_since = (now - last_used).days
            current_weekday = now.weekday()
            
            if days_since >= 7 and current_weekday == target_day:
                return True
            
            # Also execute if overdue (>14 days) and roughly right day
            if days_since >= 14:
                return True
        
        # Monthly: execute on specified day if enough time has passed
        if schedule.frequency == PaymentActionFrequency.MONTHLY:
            target_day = schedule.day_of_month or last_used.day
            
            # Check if enough time passed and it's the right day
            days_since = (now - last_used).days
            
            if days_since >= 28 and now.day == target_day:
                return True
            
            # Also execute if significantly overdue (>35 days)
            if days_since >= 35:
                return True
        
        return False
    
    def _log_execution(
        self,
        action_id: str,
        wallet_address: str,
        status: str,
        ticket_id: Optional[str] = None,
        error: Optional[str] = None,
    ):
        """Log recurring payment execution for audit."""
        record = {
            "action_id": action_id,
            "wallet_address": wallet_address,
            "status": status,
            "ticket_id": ticket_id,
            "error": error,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        key = f"{action_id}_{datetime.utcnow().timestamp()}"
        self.execution_log[key] = record
        
        logger.debug(f"Logged execution: {record}")
    
    def get_execution_log(self, action_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get execution history for an action."""
        records = [
            r for r in self.execution_log.values()
            if r.get("action_id") == action_id
        ]
        return sorted(records, key=lambda x: x["timestamp"], reverse=True)[:limit]


# Singleton instance
_keeper_instance: Optional[RecurringPaymentKeeper] = None


async def get_recurring_payment_keeper() -> RecurringPaymentKeeper:
    """Get or create singleton keeper instance."""
    global _keeper_instance
    if _keeper_instance is None:
        _keeper_instance = RecurringPaymentKeeper()
    return _keeper_instance

#!/usr/bin/env python
"""
Recurring payment keeper job runner.

Usage:
    # Run once
    python scripts/run_keeper.py

    # Run every hour (with APScheduler)
    python scripts/run_keeper.py --scheduler hourly
    
    # Run every 6 hours
    python scripts/run_keeper.py --scheduler 6h
"""
import asyncio
import logging
import argparse
from datetime import datetime, timedelta

# Setup path
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Run the keeper check."""
    from app.domains.payment_actions.keeper import get_recurring_payment_keeper
    
    logger.info("=" * 60)
    logger.info("RECURRING PAYMENT KEEPER - Starting check")
    logger.info("=" * 60)
    
    keeper = await get_recurring_payment_keeper()
    result = await keeper.run_check()
    
    logger.info("=" * 60)
    logger.info(f"Keeper check completed at {datetime.utcnow().isoformat()}")
    logger.info(f"Summary: {result}")
    logger.info("=" * 60)
    
    return result


async def run_scheduler(interval: str):
    """Run keeper on a schedule using APScheduler."""
    try:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
    except ImportError:
        logger.error("APScheduler not installed. Install with: pip install apscheduler")
        return
    
    scheduler = AsyncIOScheduler()
    
    # Parse interval
    if interval == "hourly":
        trigger_kwargs = {"hours": 1}
    elif interval == "6h":
        trigger_kwargs = {"hours": 6}
    elif interval == "12h":
        trigger_kwargs = {"hours": 12}
    elif interval == "daily":
        trigger_kwargs = {"days": 1}
    else:
        logger.error(f"Unknown interval: {interval}")
        return
    
    # Schedule the job
    scheduler.add_job(
        main,
        "interval",
        **trigger_kwargs,
        id="recurring_payment_keeper",
        name="Recurring Payment Keeper",
        misfire_grace_time=300,  # 5 minutes grace period
    )
    
    logger.info(f"Scheduled keeper to run every {interval}")
    logger.info("Scheduler running (press Ctrl+C to stop)...")
    
    scheduler.start()
    
    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        logger.info("Shutting down scheduler...")
        scheduler.shutdown()
        logger.info("Scheduler stopped")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Recurring payment keeper job runner")
    parser.add_argument(
        "--scheduler",
        type=str,
        choices=["hourly", "6h", "12h", "daily"],
        default=None,
        help="Run on schedule (e.g., 'hourly', '6h'). If not provided, runs once."
    )
    
    args = parser.parse_args()
    
    if args.scheduler:
        logger.info(f"Running keeper on schedule: {args.scheduler}")
        asyncio.run(run_scheduler(args.scheduler))
    else:
        logger.info("Running keeper check once...")
        result = asyncio.run(main())
        
        # Exit with appropriate code
        exit_code = 0 if result.get("error") is None else 1
        sys.exit(exit_code)

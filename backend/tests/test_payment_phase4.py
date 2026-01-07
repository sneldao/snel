"""Test Phase 4: Natural language triggers, suggestions, and scheduling."""
import pytest
from datetime import datetime, timedelta

from app.domains.payment_actions.models import (
    PaymentAction,
    PaymentActionType,
    PaymentActionSchedule,
    PaymentActionFrequency,
)
from app.domains.payment_actions.triggers import (
    TriggerMatcher,
    TriggerAnalyzer,
)
from app.domains.payment_actions.suggestions import SuggestionEngine
from app.domains.payment_actions.scheduler import RecurringScheduler


# ============================================================================
# TRIGGER MATCHING TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_trigger_matcher_exact_match():
    """Test exact trigger matching."""
    matcher = TriggerMatcher()
    
    action = PaymentAction(
        id="action_1",
        wallet_address="0x1234",
        name="Coffee Fund",
        action_type=PaymentActionType.SHORTCUT,
        recipient_address="0xcafe",
        amount="0.05",
        token="MNEE",
        chain_id=236,
        created_at=datetime.utcnow(),
        triggers=["coffee", "espresso", "latte"],
        is_enabled=True,
    )
    
    # Exact match
    matches = await matcher.find_matching_actions("coffee", [action])
    assert len(matches) == 1
    assert matches[0].confidence == 1.0
    print(f"✓ Exact match: confidence={matches[0].confidence}")
    
    # Case insensitive
    matches = await matcher.find_matching_actions("COFFEE", [action])
    assert len(matches) == 1
    assert matches[0].confidence == 1.0
    print(f"✓ Case insensitive match")


@pytest.mark.asyncio
async def test_trigger_matcher_substring():
    """Test substring matching."""
    matcher = TriggerMatcher()
    
    action = PaymentAction(
        id="action_rent",
        wallet_address="0x1234",
        name="Weekly Rent",
        action_type=PaymentActionType.RECURRING,
        recipient_address="0xlandlord",
        amount="2.0",
        token="MNEE",
        chain_id=236,
        created_at=datetime.utcnow(),
        triggers=["weekly rent", "rent payment", "pay rent"],
        is_enabled=True,
    )
    
    # Substring match
    matches = await matcher.find_matching_actions("time for rent", [action])
    assert len(matches) >= 1
    assert matches[0].confidence >= 0.6
    print(f"✓ Substring match: {matches[0].confidence:.2f}")
    
    # Partial word match
    matches = await matcher.find_matching_actions("rent", [action])
    assert len(matches) >= 1
    print(f"✓ Partial match found {len(matches)} action(s)")


@pytest.mark.asyncio
async def test_trigger_matcher_multiple_actions():
    """Test matching against multiple actions."""
    matcher = TriggerMatcher()
    
    actions = [
        PaymentAction(
            id="action_1",
            wallet_address="0x1234",
            name="Coffee",
            action_type=PaymentActionType.SHORTCUT,
            recipient_address="0xcafe",
            amount="0.05",
            token="MNEE",
            chain_id=236,
            created_at=datetime.utcnow(),
            triggers=["coffee", "espresso"],
            is_enabled=True,
        ),
        PaymentAction(
            id="action_2",
            wallet_address="0x1234",
            name="Lunch",
            action_type=PaymentActionType.SHORTCUT,
            recipient_address="0xrestaurant",
            amount="0.10",
            token="MNEE",
            chain_id=236,
            created_at=datetime.utcnow(),
            triggers=["lunch", "food"],
            is_enabled=True,
        ),
    ]
    
    # Match against multiple
    matches = await matcher.find_matching_actions("coffee break", actions)
    assert len(matches) >= 1
    assert matches[0].action.name == "Coffee"
    print(f"✓ Matched best action: {matches[0].action.name}")
    
    # Best match should be first
    best = await matcher.find_best_match("lunch time", actions)
    assert best is not None
    assert best.action.name == "Lunch"
    print(f"✓ Best match: {best.action.name} (confidence={best.confidence:.2f})")


@pytest.mark.asyncio
async def test_trigger_analyzer_suggestions():
    """Test trigger suggestions."""
    analyzer = TriggerAnalyzer()
    
    # Suggest triggers for a recurring payment
    suggestions = await analyzer.suggest_triggers(
        action_name="Weekly Rent",
        action_type="recurring",
        recipient="Landlord",
        amount="2.0",
    )
    
    assert len(suggestions) > 0
    assert "weekly rent" in suggestions
    print(f"✓ Generated {len(suggestions)} suggestions: {suggestions[:3]}")
    
    # Suggest for shortcut
    suggestions = await analyzer.suggest_triggers(
        action_name="Coffee Fund",
        action_type="shortcut",
    )
    
    assert "coffee fund" in suggestions
    assert len(suggestions) > 2
    print(f"✓ Shortcut suggestions: {suggestions[:3]}")


# ============================================================================
# SUGGESTION ENGINE TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_suggestion_engine_by_usage():
    """Test suggestions based on usage patterns."""
    engine = SuggestionEngine()
    now = datetime.utcnow()
    
    actions = [
        PaymentAction(
            id="action_frequent",
            wallet_address="0x1234",
            name="Frequent Payment",
            action_type=PaymentActionType.SEND,
            recipient_address="0xrecipient",
            amount="1.0",
            token="MNEE",
            chain_id=236,
            created_at=now - timedelta(days=30),
            last_used=now - timedelta(days=1),  # Used yesterday
            usage_count=15,  # Frequently used
            is_enabled=True,
            is_pinned=True,
        ),
        PaymentAction(
            id="action_rare",
            wallet_address="0x1234",
            name="Rare Payment",
            action_type=PaymentActionType.SEND,
            recipient_address="0xother",
            amount="0.5",
            token="MNEE",
            chain_id=236,
            created_at=now - timedelta(days=30),
            last_used=now - timedelta(days=30),  # Used month ago
            usage_count=1,  # Rarely used
            is_enabled=True,
        ),
    ]
    
    suggestions = await engine.suggest_actions(actions, limit=2)
    
    assert len(suggestions) >= 1
    assert suggestions[0].action.name == "Frequent Payment"
    print(f"✓ Top suggestion: {suggestions[0].action.name} (score={suggestions[0].score:.2f})")
    print(f"  Reason: {suggestions[0].reason}")


@pytest.mark.asyncio
async def test_suggestion_engine_by_time():
    """Test suggestions based on time context."""
    engine = SuggestionEngine()
    
    actions = [
        PaymentAction(
            id="action_recurring",
            wallet_address="0x1234",
            name="Weekly Payment",
            action_type=PaymentActionType.RECURRING,
            recipient_address="0x1",
            amount="1.0",
            token="MNEE",
            chain_id=236,
            created_at=datetime.utcnow(),
            usage_count=5,
            is_enabled=True,
        ),
        PaymentAction(
            id="action_shortcut",
            wallet_address="0x1234",
            name="Personal Transfer",
            action_type=PaymentActionType.SHORTCUT,
            recipient_address="0x2",
            amount="0.5",
            token="MNEE",
            chain_id=236,
            created_at=datetime.utcnow(),
            usage_count=3,
            is_enabled=True,
        ),
    ]
    
    # Test evening suggestion (shortcut more relevant)
    suggestions = await engine.suggest_based_on_time(
        actions,
        hour=20,  # 8 PM
        day_of_week=3,  # Wednesday
    )
    
    assert len(suggestions) > 0
    print(f"✓ Evening suggestions: {[s.action.name for s in suggestions]}")


@pytest.mark.asyncio
async def test_suggestion_engine_overdue_recurring():
    """Test overdue recurring payment suggestions."""
    engine = SuggestionEngine()
    now = datetime.utcnow()
    
    actions = [
        PaymentAction(
            id="action_due",
            wallet_address="0x1234",
            name="Weekly Payment",
            action_type=PaymentActionType.RECURRING,
            recipient_address="0x1",
            amount="1.0",
            token="MNEE",
            chain_id=236,
            created_at=now - timedelta(days=30),
            last_used=now - timedelta(days=8),  # 8 days ago
            usage_count=5,
            is_enabled=True,
            schedule=PaymentActionSchedule(
                frequency=PaymentActionFrequency.WEEKLY,
            ),
        ),
        PaymentAction(
            id="action_not_due",
            wallet_address="0x1234",
            name="Monthly Payment",
            action_type=PaymentActionType.RECURRING,
            recipient_address="0x2",
            amount="2.0",
            token="MNEE",
            chain_id=236,
            created_at=now - timedelta(days=30),
            last_used=now - timedelta(days=5),  # 5 days ago
            usage_count=2,
            is_enabled=True,
            schedule=PaymentActionSchedule(
                frequency=PaymentActionFrequency.MONTHLY,
            ),
        ),
    ]
    
    overdue = await engine.suggest_overdue_recurring(actions)
    
    assert len(overdue) >= 1
    assert overdue[0].action.name == "Weekly Payment"
    print(f"✓ Found {len(overdue)} overdue payment(s): {overdue[0].action.name}")


# ============================================================================
# RECURRING SCHEDULER TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_scheduler_daily_payment():
    """Test daily payment scheduling."""
    scheduler = RecurringScheduler()
    now = datetime.utcnow()
    
    # Create a daily action
    action = PaymentAction(
        id="action_daily",
        wallet_address="0x1234",
        name="Daily Payment",
        action_type=PaymentActionType.RECURRING,
        recipient_address="0xrecipient",
        amount="0.1",
        token="MNEE",
        chain_id=236,
        created_at=now - timedelta(days=5),
        last_used=now - timedelta(days=2),  # 2 days ago
        usage_count=5,
        is_enabled=True,
        schedule=PaymentActionSchedule(
            frequency=PaymentActionFrequency.DAILY,
        ),
    )
    
    info = await scheduler.get_schedule_info(action, now)
    assert info.status.value in ["due", "overdue"]
    print(f"✓ Daily payment status: {info.status.value}")
    print(f"  Description: {scheduler.get_schedule_description(action)}")


@pytest.mark.asyncio
async def test_scheduler_weekly_payment():
    """Test weekly payment scheduling with day of week."""
    scheduler = RecurringScheduler()
    now = datetime.utcnow()
    
    # Create a weekly action (Monday)
    monday_dow = 0
    
    action = PaymentAction(
        id="action_weekly",
        wallet_address="0x1234",
        name="Weekly Payment",
        action_type=PaymentActionType.RECURRING,
        recipient_address="0xrecipient",
        amount="1.0",
        token="MNEE",
        chain_id=236,
        created_at=now - timedelta(days=30),
        last_used=now - timedelta(days=8),
        usage_count=4,
        is_enabled=True,
        schedule=PaymentActionSchedule(
            frequency=PaymentActionFrequency.WEEKLY,
            day_of_week=monday_dow,
        ),
    )
    
    info = await scheduler.get_schedule_info(action, now)
    assert info.status.value in ["due", "overdue", "not_due"]
    assert info.days_until_due is not None
    print(f"✓ Weekly payment status: {info.status.value}")
    print(f"  Days until due: {info.days_until_due}")
    print(f"  Description: {scheduler.get_schedule_description(action)}")


@pytest.mark.asyncio
async def test_scheduler_monthly_payment():
    """Test monthly payment scheduling."""
    scheduler = RecurringScheduler()
    now = datetime.utcnow()
    
    # Create a monthly action (15th)
    action = PaymentAction(
        id="action_monthly",
        wallet_address="0x1234",
        name="Monthly Payment",
        action_type=PaymentActionType.RECURRING,
        recipient_address="0xrecipient",
        amount="5.0",
        token="MNEE",
        chain_id=236,
        created_at=now - timedelta(days=60),
        last_used=now - timedelta(days=35),
        usage_count=2,
        is_enabled=True,
        schedule=PaymentActionSchedule(
            frequency=PaymentActionFrequency.MONTHLY,
            day_of_month=15,
        ),
    )
    
    info = await scheduler.get_schedule_info(action, now)
    assert info.status.value in ["due", "overdue", "not_due"]
    print(f"✓ Monthly payment status: {info.status.value}")
    print(f"  Description: {scheduler.get_schedule_description(action)}")


@pytest.mark.asyncio
async def test_scheduler_due_actions():
    """Test getting all due actions."""
    scheduler = RecurringScheduler()
    now = datetime.utcnow()
    
    actions = [
        PaymentAction(
            id="action_1",
            wallet_address="0x1234",
            name="Due Action",
            action_type=PaymentActionType.RECURRING,
            recipient_address="0x1",
            amount="1.0",
            token="MNEE",
            chain_id=236,
            created_at=now - timedelta(days=10),
            last_used=now - timedelta(days=10),  # 10 days ago
            usage_count=5,
            is_enabled=True,
            schedule=PaymentActionSchedule(
                frequency=PaymentActionFrequency.DAILY,
            ),
        ),
        PaymentAction(
            id="action_2",
            wallet_address="0x1234",
            name="Not Due Action",
            action_type=PaymentActionType.RECURRING,
            recipient_address="0x2",
            amount="2.0",
            token="MNEE",
            chain_id=236,
            created_at=now - timedelta(days=5),
            last_used=now - timedelta(hours=1),  # 1 hour ago
            usage_count=2,
            is_enabled=True,
            schedule=PaymentActionSchedule(
                frequency=PaymentActionFrequency.WEEKLY,
            ),
        ),
    ]
    
    due_actions = await scheduler.get_due_actions(actions, now)
    assert len(due_actions) >= 1
    assert due_actions[0].action.name == "Due Action"
    print(f"✓ Found {len(due_actions)} due action(s)")


@pytest.mark.asyncio
async def test_scheduler_upcoming_actions():
    """Test getting upcoming actions."""
    scheduler = RecurringScheduler()
    now = datetime.utcnow()
    
    actions = [
        PaymentAction(
            id="action_1",
            wallet_address="0x1234",
            name="Action 1",
            action_type=PaymentActionType.RECURRING,
            recipient_address="0x1",
            amount="1.0",
            token="MNEE",
            chain_id=236,
            created_at=now - timedelta(days=30),
            last_used=now - timedelta(days=7),
            usage_count=4,
            is_enabled=True,
            schedule=PaymentActionSchedule(
                frequency=PaymentActionFrequency.WEEKLY,
            ),
        ),
    ]
    
    upcoming = await scheduler.get_upcoming_actions(actions, days_ahead=7, now=now)
    print(f"✓ Found {len(upcoming)} upcoming action(s)")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_trigger_matcher_exact_match())
    asyncio.run(test_trigger_analyzer_suggestions())
    asyncio.run(test_suggestion_engine_by_usage())
    asyncio.run(test_scheduler_daily_payment())

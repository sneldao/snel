"""Test payment actions with persistent storage backends."""
import asyncio
import pytest
from app.domains.payment_actions.models import (
    PaymentAction,
    PaymentActionType,
    CreatePaymentActionRequest,
)
from app.domains.payment_actions.storage import InMemoryStorageBackend, RedisStorageBackend
from app.domains.payment_actions.service import PaymentActionService
import redis.asyncio as redis


@pytest.mark.asyncio
async def test_in_memory_storage():
    """Test in-memory backend."""
    print("\n=== Testing In-Memory Backend ===")
    backend = InMemoryStorageBackend()
    service = PaymentActionService(backend=backend)
    
    wallet = "0x1234567890abcdef1234567890abcdef"
    
    # Create action
    request = CreatePaymentActionRequest(
        name="Weekly Rent",
        action_type=PaymentActionType.RECURRING,
        recipient_address="0xrecipient",
        amount="1.5",
        token="MNEE",
        chain_id=236,
        is_pinned=True,
    )
    
    action = await service.create_action(wallet, request)
    print(f"✓ Created action: {action.id} ({action.name})")
    
    # Retrieve action
    retrieved = await service.get_action(wallet, action.id)
    assert retrieved is not None
    print(f"✓ Retrieved action: {retrieved.name}")
    
    # Mark as used
    used = await service.mark_used(wallet, action.id)
    assert used.usage_count == 1
    print(f"✓ Marked used: usage_count={used.usage_count}")
    
    # List quick actions
    quick = await service.get_quick_actions(wallet)
    assert len(quick) == 1
    print(f"✓ Quick actions: {len(quick)}")
    
    # Delete action
    deleted = await service.delete_action(wallet, action.id)
    assert deleted is True
    print(f"✓ Deleted action")
    
    # Verify deletion
    gone = await service.get_action(wallet, action.id)
    assert gone is None
    print(f"✓ Verified deletion")


@pytest.mark.asyncio
async def test_redis_storage():
    """Test Redis backend."""
    print("\n=== Testing Redis Backend ===")
    
    try:
        # Try to connect to Redis
        redis_client = await redis.from_url(
            "redis://localhost:6379",
            db=1,  # Use separate DB for testing
            decode_responses=True,
        )
        
        # Test connection
        await redis_client.ping()
        print("✓ Connected to Redis")
        
        backend = RedisStorageBackend(redis_client)
        service = PaymentActionService(backend=backend)
        
        wallet = "0xredistest1234567890abcdef"
        
        # Create action
        request = CreatePaymentActionRequest(
            name="Coffee Fund",
            action_type=PaymentActionType.SHORTCUT,
            recipient_address="0xcoffee",
            amount="0.05",
            token="MNEE",
            chain_id=236,
            triggers=["coffee", "espresso"],
            is_pinned=True,
        )
        
        action = await service.create_action(wallet, request)
        print(f"✓ Created action in Redis: {action.id}")
        
        # Retrieve from Redis
        retrieved = await service.get_action(wallet, action.id)
        assert retrieved is not None
        assert retrieved.name == "Coffee Fund"
        print(f"✓ Retrieved from Redis: {retrieved.name}")
        
        # Update action
        from app.domains.payment_actions.models import UpdatePaymentActionRequest
        update = UpdatePaymentActionRequest(
            amount="0.10",
            is_pinned=False,
        )
        updated = await service.update_action(wallet, action.id, update)
        assert updated.amount == "0.10"
        assert updated.is_pinned is False
        print(f"✓ Updated action: amount={updated.amount}, pinned={updated.is_pinned}")
        
        # List actions
        actions = await service.get_actions(wallet)
        assert len(actions) >= 1
        print(f"✓ Listed {len(actions)} actions from Redis")
        
        # Cleanup
        await service.delete_action(wallet, action.id)
        await redis_client.close()
        print(f"✓ Cleaned up and closed Redis connection")
        
    except redis.ConnectionError:
        print("⚠ Redis not available (skipping Redis tests)")
        print("  Start Redis with: redis-server")


@pytest.mark.asyncio
async def test_multiple_actions():
    """Test managing multiple payment actions."""
    print("\n=== Testing Multiple Actions ===")
    backend = InMemoryStorageBackend()
    service = PaymentActionService(backend=backend)
    
    wallet = "0xmultitest1234567890abcdef"
    
    # Create multiple actions
    actions_data = [
        ("Rent", PaymentActionType.RECURRING, "0xlandlord", "2.0", True),
        ("Coffee", PaymentActionType.SHORTCUT, "0xcafe", "0.05", True),
        ("Savings", PaymentActionType.SEND, "0xvault", "0.5", False),
        ("Charity", PaymentActionType.TEMPLATE, "0xnpo", "0.1", True),
    ]
    
    created_ids = []
    for name, action_type, recipient, amount, pinned in actions_data:
        request = CreatePaymentActionRequest(
            name=name,
            action_type=action_type,
            recipient_address=recipient,
            amount=amount,
            token="MNEE",
            chain_id=236,
            is_pinned=pinned,
        )
        action = await service.create_action(wallet, request)
        created_ids.append(action.id)
        print(f"✓ Created: {name} (pinned={pinned})")
    
    # Get quick actions (pinned only)
    quick = await service.get_quick_actions(wallet)
    assert len(quick) == 3  # 3 pinned actions
    print(f"✓ Quick actions: {len(quick)} pinned out of {len(created_ids)} total")
    
    # Filter by type
    recurring = await service.get_actions(wallet, action_type=PaymentActionType.RECURRING)
    assert len(recurring) == 1
    print(f"✓ Recurring actions: {len(recurring)}")
    
    # Mark several as used
    for i, action_id in enumerate(created_ids[:2]):
        for _ in range(i + 1):
            await service.mark_used(wallet, action_id)
    
    # Verify usage counts
    actions = await service.get_actions(wallet)
    used_counts = {a.name: a.usage_count for a in actions}
    print(f"✓ Usage counts: {used_counts}")
    
    # Delete one
    deleted = await service.delete_action(wallet, created_ids[2])
    assert deleted is True
    
    remaining = await service.get_actions(wallet)
    assert len(remaining) == 3
    print(f"✓ After delete: {len(remaining)} actions remain")


async def main():
    """Run all tests."""
    print("🧪 Payment Actions Storage Tests")
    print("=" * 40)
    
    await test_in_memory_storage()
    await test_redis_storage()
    await test_multiple_actions()
    
    print("\n" + "=" * 40)
    print("✅ All tests completed!")


if __name__ == "__main__":
    asyncio.run(main())

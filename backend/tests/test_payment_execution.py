"""Test payment action execution with MNEE."""
import pytest
from decimal import Decimal
from datetime import datetime

from app.domains.payment_actions.models import (
    PaymentAction,
    PaymentActionType,
    PaymentActionSchedule,
    PaymentActionFrequency,
)
from app.domains.payment_actions.executor import (
    PaymentExecutor,
    ExecutionStatus,
)
from app.domains.payment_actions.transaction_history import (
    PaymentTransaction,
    TransactionStatus,
    TransactionHistoryService,
)


@pytest.mark.asyncio
async def test_payment_executor_validation():
    """Test payment action validation before execution."""
    executor = PaymentExecutor()
    
    # Create valid action
    valid_action = PaymentAction(
        id="action_test123",
        wallet_address="0x1234567890abcdef",
        name="Test Payment",
        action_type=PaymentActionType.SEND,
        recipient_address="0xrecipient",
        amount="1.0",
        token="MNEE",
        chain_id=236,  # 1Sat Ordinals (supported)
        created_at=datetime.utcnow(),
        is_enabled=True,
    )
    
    wallet = "0x1234567890abcdef"
    
    # Validate valid action
    validation = await executor.validate_action_for_execution(valid_action, wallet)
    assert validation["valid"] is True
    assert len(validation["errors"]) == 0
    print(f"✓ Valid action passed validation")
    
    # Create disabled action
    disabled_action = valid_action.model_copy(update={"is_enabled": False})
    validation = await executor.validate_action_for_execution(disabled_action, wallet)
    assert validation["valid"] is False
    assert "disabled" in validation["errors"][0].lower()
    print(f"✓ Disabled action caught: {validation['errors']}")
    
    # Create template (can't execute)
    template_action = valid_action.model_copy(update={"action_type": PaymentActionType.TEMPLATE})
    validation = await executor.validate_action_for_execution(template_action, wallet)
    assert validation["valid"] is False
    assert "template" in validation["errors"][0].lower()
    print(f"✓ Template blocked: {validation['errors']}")
    
    # Create unsupported chain
    unsupported_action = valid_action.model_copy(update={"chain_id": 999})
    validation = await executor.validate_action_for_execution(unsupported_action, wallet)
    assert validation["valid"] is False
    assert "not supported" in validation["errors"][0].lower()
    print(f"✓ Unsupported chain blocked: {validation['errors']}")


@pytest.mark.asyncio
async def test_payment_executor_without_signing():
    """Test execution flow without wallet signing (should return awaiting_signature)."""
    executor = PaymentExecutor()
    
    action = PaymentAction(
        id="action_nosign",
        wallet_address="0x1234567890abcdef",
        name="No Sign Test",
        action_type=PaymentActionType.SEND,
        recipient_address="0xrecipient",
        amount="0.5",
        token="MNEE",
        chain_id=236,
        created_at=datetime.utcnow(),
        is_enabled=True,
    )
    
    # Execute without signing function - should await signature
    result = await executor.execute_action(action, "0x1234567890abcdef")
    
    assert result.status == ExecutionStatus.AWAITING_SIGNATURE
    assert result.error_message is None
    assert result.metadata["transaction"] is not None
    print(f"✓ Execution awaiting signature: {result.status.value}")
    print(f"✓ Transaction metadata prepared")


@pytest.mark.asyncio
async def test_transaction_history_service():
    """Test transaction history recording and retrieval."""
    service = TransactionHistoryService()
    
    wallet = "0x1234567890abcdef"
    
    # Create a transaction record
    now = datetime.utcnow()
    txn = PaymentTransaction(
        id="txn_001",
        wallet_address=wallet,
        action_id="action_test",
        action_name="Test Payment",
        status=TransactionStatus.PENDING,
        ticket_id="ticket-123-456",
        from_address=wallet,
        to_address="0xrecipient",
        amount="1.0",
        token="MNEE",
        fee="0.01",
        chain_id=236,
        created_at=now,
        updated_at=now,
    )
    
    # Record it
    recorded = await service.record_transaction(wallet, txn)
    assert recorded.id == txn.id
    print(f"✓ Transaction recorded: {txn.id}")
    
    # Retrieve it
    retrieved = await service.get_transaction(wallet, txn.id)
    assert retrieved is not None
    assert retrieved.amount == "1.0"
    print(f"✓ Transaction retrieved: {retrieved.amount} {retrieved.token}")
    
    # Get by ticket ID
    by_ticket = await service.get_transaction_by_ticket(wallet, "ticket-123-456")
    assert by_ticket is not None
    assert by_ticket.id == txn.id
    print(f"✓ Found transaction by ticket: {by_ticket.ticket_id}")
    
    # Create more transactions
    for i in range(2, 5):
        now = datetime.utcnow()
        t = PaymentTransaction(
            id=f"txn_{i:03d}",
            wallet_address=wallet,
            action_id="action_recurring",
            action_name="Recurring",
            status=TransactionStatus.CONFIRMED,
            ticket_id=f"ticket-{i}",
            from_address=wallet,
            to_address="0xrecipient",
            amount="0.5",
            token="MNEE",
            chain_id=236,
            created_at=now,
            updated_at=now,
        )
        await service.record_transaction(wallet, t)
    
    # List all
    all_txns = await service.get_transactions(wallet)
    assert len(all_txns) >= 4
    print(f"✓ Listed {len(all_txns)} transactions")
    
    # Filter by status
    confirmed = await service.get_transactions(wallet, status=TransactionStatus.CONFIRMED)
    assert len(confirmed) == 3
    print(f"✓ Filtered to {len(confirmed)} confirmed transactions")
    
    # Update status
    updated = await service.update_transaction_status(
        wallet,
        txn.id,
        TransactionStatus.CONFIRMED,
        transaction_hash="0xabcd1234",
    )
    assert updated.status == TransactionStatus.CONFIRMED
    assert updated.transaction_hash == "0xabcd1234"
    assert updated.confirmed_at is not None
    print(f"✓ Transaction status updated: {updated.status.value}")
    print(f"✓ Confirmed at: {updated.confirmed_at}")


@pytest.mark.asyncio
async def test_execution_result_serialization():
    """Test ExecutionResult to_dict serialization."""
    from app.domains.payment_actions.executor import ExecutionResult
    
    result = ExecutionResult(
        status=ExecutionStatus.SUBMITTED,
        action_id="action_123",
        wallet_address="0x1234",
        ticket_id="ticket-abc-def",
        metadata={
            "amount": "1.5",
            "fee": "0.01",
        },
    )
    
    data = result.to_dict()
    assert data["status"] == "submitted"
    assert data["ticket_id"] == "ticket-abc-def"
    assert data["metadata"]["amount"] == "1.5"
    assert "timestamp" in data
    print(f"✓ ExecutionResult serialized: {data['status']} with ticket {data['ticket_id']}")


def test_execution_status_enum():
    """Test ExecutionStatus enum values."""
    assert ExecutionStatus.QUEUED.value == "queued"
    assert ExecutionStatus.SUBMITTED.value == "submitted"
    assert ExecutionStatus.COMPLETED.value == "completed"
    assert ExecutionStatus.FAILED.value == "failed"
    print(f"✓ ExecutionStatus enums: {[s.value for s in ExecutionStatus]}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_payment_executor_validation())
    asyncio.run(test_payment_executor_without_signing())
    asyncio.run(test_transaction_history_service())
    asyncio.run(test_execution_result_serialization())
    test_execution_status_enum()

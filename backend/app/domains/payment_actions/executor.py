"""Payment execution service - handles real MNEE transfers for payment actions."""
import logging
from decimal import Decimal
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum

from app.protocols.mnee_adapter import MNEEAdapter
from app.models.token import token_registry
from .models import PaymentAction, PaymentActionType


logger = logging.getLogger(__name__)


class ExecutionStatus(Enum):
    """Payment execution status."""
    QUEUED = "queued"
    BUILDING = "building"
    AWAITING_SIGNATURE = "awaiting_signature"
    SUBMITTED = "submitted"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ExecutionResult:
    """Result of payment execution attempt."""
    
    def __init__(
        self,
        status: ExecutionStatus,
        action_id: str,
        wallet_address: str,
        ticket_id: Optional[str] = None,
        transaction_hash: Optional[str] = None,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.status = status
        self.action_id = action_id
        self.wallet_address = wallet_address
        self.ticket_id = ticket_id
        self.transaction_hash = transaction_hash
        self.error_message = error_message
        self.metadata = metadata or {}
        self.timestamp = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "status": self.status.value,
            "action_id": self.action_id,
            "ticket_id": self.ticket_id,
            "transaction_hash": self.transaction_hash,
            "error_message": self.error_message,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }


class PaymentExecutor:
    """
    Executes real payment actions via MNEE protocol.
    
    CLEAN: Single responsibility - payment execution only
    MODULAR: Works with any PaymentAction, delegates to MNEEAdapter
    PERFORMANT: Async operations, ticket-based tracking
    """
    
    def __init__(self):
        """Initialize executor with MNEE adapter."""
        self.mnee_adapter = MNEEAdapter()
    
    async def execute_action(
        self,
        action: PaymentAction,
        from_wallet: str,
        signing_function=None,  # Optional: async function that signs rawtx
    ) -> ExecutionResult:
        """
        Execute a payment action.
        
        Flow:
        1. Validate action and wallet
        2. Get quote from MNEE adapter
        3. Build transaction
        4. Await signature (if signing_function provided)
        5. Submit to MNEE API
        6. Return ticket for tracking
        
        Args:
            action: PaymentAction to execute
            from_wallet: Wallet executing the action
            signing_function: Optional async function(rawtx) -> signed_rawtx
        
        Returns:
            ExecutionResult with status and ticket_id
        """
        try:
            # Validate action can be executed
            if not action.is_enabled:
                return ExecutionResult(
                    status=ExecutionStatus.FAILED,
                    action_id=action.id,
                    wallet_address=from_wallet,
                    error_message="Action is disabled",
                )
            
            if action.action_type == PaymentActionType.TEMPLATE:
                return ExecutionResult(
                    status=ExecutionStatus.FAILED,
                    action_id=action.id,
                    wallet_address=from_wallet,
                    error_message="Templates cannot be executed directly",
                )
            
            # Validate chain is supported by MNEE
            if not self.mnee_adapter.is_supported(action.chain_id):
                return ExecutionResult(
                    status=ExecutionStatus.FAILED,
                    action_id=action.id,
                    wallet_address=from_wallet,
                    error_message=f"Chain {action.chain_id} not supported by MNEE",
                )
            
            logger.info(f"Executing payment action {action.id}: {action.name}")
            
            # Step 1: Get token information
            token_info = token_registry.get_token(action.token.lower())
            if not token_info:
                return ExecutionResult(
                    status=ExecutionStatus.FAILED,
                    action_id=action.id,
                    wallet_address=from_wallet,
                    error_message=f"Token {action.token} not found",
                )
            
            # Step 2: Get quote (validates amounts, calculates fees)
            quote = await self.mnee_adapter.get_quote(
                from_token=token_info,
                to_token=token_info,  # Same token (MNEE to MNEE)
                amount=Decimal(action.amount),
                chain_id=action.chain_id,
                wallet_address=from_wallet,
            )
            
            if not quote.get("success"):
                return ExecutionResult(
                    status=ExecutionStatus.FAILED,
                    action_id=action.id,
                    wallet_address=from_wallet,
                    error_message=f"Failed to get quote: {quote.get('error', 'Unknown error')}",
                )
            
            logger.info(f"Got quote for {action.name}: {quote.get('estimated_fee_mnee')} MNEE fee")
            
            # Step 3: Build transaction
            txn_result = await self.mnee_adapter.build_transaction(
                quote=quote,
                chain_id=action.chain_id,
                from_address=from_wallet,
                to_address=action.recipient_address,
            )
            
            logger.info(f"Built transaction for {action.name}")
            
            # Step 4: If signing function provided, get signature
            rawtx = None
            if signing_function:
                try:
                    logger.info(f"Awaiting signature for {action.name}")
                    rawtx = await signing_function(txn_result)
                except Exception as e:
                    logger.error(f"Signing failed: {str(e)}")
                    return ExecutionResult(
                        status=ExecutionStatus.FAILED,
                        action_id=action.id,
                        wallet_address=from_wallet,
                        error_message=f"Signing failed: {str(e)}",
                    )
            else:
                # Without signing function, we can't execute
                return ExecutionResult(
                    status=ExecutionStatus.AWAITING_SIGNATURE,
                    action_id=action.id,
                    wallet_address=from_wallet,
                    metadata={
                        "transaction": txn_result,
                        "quote": quote,
                    },
                )
            
            # Step 5: Submit to MNEE API
            try:
                logger.info(f"Submitting transaction for {action.name}")
                ticket_id = await self.mnee_adapter.transfer(rawtx)
                
                logger.info(f"Payment action {action.id} submitted with ticket: {ticket_id}")
                
                return ExecutionResult(
                    status=ExecutionStatus.SUBMITTED,
                    action_id=action.id,
                    wallet_address=from_wallet,
                    ticket_id=ticket_id,
                    metadata={
                        "amount": action.amount,
                        "token": action.token,
                        "recipient": action.recipient_address,
                        "fee_mnee": quote.get("estimated_fee_mnee"),
                    },
                )
            
            except Exception as e:
                logger.error(f"Transfer submission failed: {str(e)}")
                return ExecutionResult(
                    status=ExecutionStatus.FAILED,
                    action_id=action.id,
                    wallet_address=from_wallet,
                    error_message=f"Transfer submission failed: {str(e)}",
                )
        
        except Exception as e:
            logger.error(f"Payment execution error: {str(e)}")
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                action_id=action.id,
                wallet_address=from_wallet,
                error_message=str(e),
            )
    
    async def get_execution_status(self, ticket_id: str) -> Dict[str, Any]:
        """
        Get status of submitted payment via MNEE ticket.
        
        Args:
            ticket_id: MNEE ticket ID from execution
        
        Returns:
            Ticket status from MNEE API
        """
        try:
            ticket = await self.mnee_adapter.get_ticket(ticket_id)
            return {
                "ticket_id": ticket_id,
                "status": ticket.get("status"),
                "tx_id": ticket.get("tx_id"),
                "created_at": ticket.get("createdAt"),
                "updated_at": ticket.get("updatedAt"),
                "errors": ticket.get("errors"),
                "raw": ticket,
            }
        except Exception as e:
            logger.error(f"Error getting ticket status: {str(e)}")
            return {
                "ticket_id": ticket_id,
                "error": str(e),
            }
    
    async def validate_action_for_execution(
        self,
        action: PaymentAction,
        from_wallet: str,
    ) -> Dict[str, Any]:
        """
        Validate that an action can be executed.
        
        Returns validation details and any warnings.
        """
        warnings = []
        errors = []
        
        # Check enabled
        if not action.is_enabled:
            errors.append("Action is disabled")
        
        # Check type
        if action.action_type == PaymentActionType.TEMPLATE:
            errors.append("Templates cannot be executed directly")
        
        # Check chain support
        if not self.mnee_adapter.is_supported(action.chain_id):
            errors.append(f"Chain {action.chain_id} not supported by MNEE")
        
        # Check token
        token_info = token_registry.get_token(action.token.lower())
        if not token_info:
            errors.append(f"Token {action.token} not found")
        
        # Check amount format
        try:
            amount = Decimal(action.amount)
            if amount <= 0:
                errors.append("Amount must be greater than 0")
        except Exception:
            errors.append("Invalid amount format")
        
        # Check addresses
        if not action.recipient_address or not action.recipient_address.startswith("0x"):
            warnings.append("Recipient address may be invalid")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "action_id": action.id,
            "action_name": action.name,
        }


# Singleton instance
_executor_instance: Optional[PaymentExecutor] = None


async def get_payment_executor() -> PaymentExecutor:
    """Get or create singleton executor instance."""
    global _executor_instance
    if _executor_instance is None:
        _executor_instance = PaymentExecutor()
    return _executor_instance

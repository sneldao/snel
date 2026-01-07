"""Webhook service - handles webhook execution and event processing for payment actions."""
import logging
import json
from typing import Dict, Any, Optional
from decimal import Decimal
from datetime import datetime

from app.models.unified_models import UnifiedCommand
from app.domains.payment_actions.webhooks import (
    WebhookRequest,
    WebhookResponse,
    WebhookEventType,
    WebhookPayloadExecuteAction,
    WebhookPayloadExecuteBatch,
    WebhookValidator,
    WebhookExecutionRecord,
)
from app.domains.payment_actions.service import get_payment_action_service
from app.domains.payment_actions.executor import get_payment_executor
from app.domains.payment_actions.models import PaymentAction, PaymentActionType


logger = logging.getLogger(__name__)


class WebhookService:
    """
    Service for handling webhook requests from AI agents.
    
    Provides:
    - Signature validation for secure agent communication
    - Execute payment action endpoint
    - Batch payment execution
    - Execution history and audit trail
    """
    
    def __init__(self):
        self.service = None
        self.executor = None
        self.execution_history = {}  # In-memory, upgrade to DB later
    
    async def _init_services(self):
        """Lazy initialize services."""
        if self.service is None:
            self.service = await get_payment_action_service()
        if self.executor is None:
            self.executor = await get_payment_executor()
    
    async def handle_webhook(
        self,
        request: WebhookRequest,
        agent_secret: Optional[str] = None,  # Secret for signature verification
    ) -> WebhookResponse:
        """
        Handle incoming webhook request.
        
        Args:
            request: Webhook request with event payload
            agent_secret: Shared secret for HMAC verification (optional for dev)
        
        Returns:
            WebhookResponse with result or error
        """
        try:
            await self._init_services()
            
            # Verify signature if secret provided
            if agent_secret:
                payload_json = json.dumps(request.payload, sort_keys=True)
                if not WebhookValidator.verify_signature(
                    payload_json,
                    request.signature,
                    agent_secret
                ):
                    logger.warning(f"Invalid signature for webhook {request.request_id}")
                    return WebhookResponse(
                        success=False,
                        request_id=request.request_id,
                        message="Signature verification failed",
                        error="Unauthorized: Invalid signature",
                    )
            
            # Route to handler based on event type
            if request.event_type == WebhookEventType.EXECUTE_ACTION:
                return await self._handle_execute_action(request)
            
            elif request.event_type == WebhookEventType.EXECUTE_BATCH:
                return await self._handle_execute_batch(request)
            
            elif request.event_type == WebhookEventType.CREATE_ACTION:
                return await self._handle_create_action(request)
            
            else:
                return WebhookResponse(
                    success=False,
                    request_id=request.request_id,
                    message="Unknown event type",
                    error=f"Event type {request.event_type} not supported",
                )
        
        except Exception as e:
            logger.exception(f"Webhook processing error for {request.request_id}")
            return WebhookResponse(
                success=False,
                request_id=request.request_id,
                message="Webhook processing failed",
                error=str(e),
            )
    
    async def _handle_execute_action(self, request: WebhookRequest) -> WebhookResponse:
        """Handle execute_action webhook event."""
        try:
            payload = WebhookPayloadExecuteAction(**request.payload)
            
            # Get the payment action
            action = await self.service.get_action(payload.wallet_address, payload.action_id)
            if not action:
                return WebhookResponse(
                    success=False,
                    request_id=request.request_id,
                    message="Action not found",
                    error=f"Action {payload.action_id} not found",
                )
            
            # Apply overrides if provided
            if payload.override_amount:
                action.amount = payload.override_amount
            if payload.override_recipient:
                action.recipient_address = payload.override_recipient
            
            # Validate action
            validation = await self.executor.validate_action_for_execution(
                action,
                payload.wallet_address
            )
            
            if not validation["valid"]:
                error_msg = "; ".join(validation["errors"])
                record = WebhookExecutionRecord(
                    request_id=request.request_id,
                    event_type=request.event_type,
                    wallet_address=payload.wallet_address,
                    action_id=payload.action_id,
                    status="failed",
                    error=error_msg,
                    metadata=request.payload,
                )
                self._record_execution(record)
                
                return WebhookResponse(
                    success=False,
                    request_id=request.request_id,
                    message="Action validation failed",
                    error=error_msg,
                )
            
            # Execute action
            result = await self.executor.execute_action(action, payload.wallet_address)
            
            # Record execution
            record = WebhookExecutionRecord(
                request_id=request.request_id,
                event_type=request.event_type,
                wallet_address=payload.wallet_address,
                action_id=payload.action_id,
                ticket_id=result.ticket_id if result.status.value == "submitted" else None,
                status=result.status.value,
                error=result.error_message,
                metadata=result.metadata,
            )
            self._record_execution(record)
            
            # Mark action as used
            await self.service.mark_used(payload.wallet_address, payload.action_id)
            
            return WebhookResponse(
                success=result.status.value in ["submitted", "awaiting_signature"],
                request_id=request.request_id,
                message=f"Action {action.name} executed",
                result={
                    "action_id": action.id,
                    "status": result.status.value,
                    "ticket_id": result.ticket_id,
                    "amount": action.amount,
                    "token": action.token,
                    "recipient": action.recipient_address,
                    "metadata": result.metadata,
                },
            )
        
        except Exception as e:
            logger.exception(f"Execute action webhook error")
            record = WebhookExecutionRecord(
                request_id=request.request_id,
                event_type=request.event_type,
                wallet_address=request.payload.get("wallet_address", "unknown"),
                action_id=request.payload.get("action_id"),
                status="failed",
                error=str(e),
                metadata=request.payload,
            )
            self._record_execution(record)
            
            return WebhookResponse(
                success=False,
                request_id=request.request_id,
                message="Action execution failed",
                error=str(e),
            )
    
    async def _handle_execute_batch(self, request: WebhookRequest) -> WebhookResponse:
        """Handle execute_batch webhook event for batch payments."""
        try:
            payload = WebhookPayloadExecuteBatch(**request.payload)
            
            # Validate recipients
            if not payload.recipients or len(payload.recipients) == 0:
                return WebhookResponse(
                    success=False,
                    request_id=request.request_id,
                    message="No recipients provided",
                    error="Recipients list is empty",
                )
            
            # Calculate splits based on amounts or percentages
            total_amount = Decimal(payload.metadata.get("total_amount", payload.metadata.get("amount", 0)))
            splits = self._calculate_splits(payload.recipients, total_amount)
            
            if not splits or len(splits) == 0:
                return WebhookResponse(
                    success=False,
                    request_id=request.request_id,
                    message="Failed to calculate payment splits",
                    error="Invalid recipient amounts/percentages",
                )
            
            # Execute batch payments (could be sequential or parallel)
            execution_results = []
            for recipient in splits:
                try:
                    # Create a temporary action for this recipient
                    temp_action = PaymentAction(
                        id=f"batch_{request.request_id}_{recipient['address'][:8]}",
                        wallet_address=payload.wallet_address,
                        name=f"Batch payment to {recipient.get('label', recipient['address'][:6])}",
                        action_type=PaymentActionType.SEND,
                        recipient_address=recipient["address"],
                        amount=str(recipient["amount"]),
                        token=payload.token,
                        chain_id=payload.chain_id,
                    )
                    
                    # Execute
                    result = await self.executor.execute_action(temp_action, payload.wallet_address)
                    execution_results.append({
                        "recipient": recipient["address"],
                        "amount": str(recipient["amount"]),
                        "status": result.status.value,
                        "ticket_id": result.ticket_id,
                    })
                
                except Exception as e:
                    logger.error(f"Batch payment to {recipient['address']} failed: {e}")
                    execution_results.append({
                        "recipient": recipient["address"],
                        "amount": str(recipient["amount"]),
                        "status": "failed",
                        "error": str(e),
                    })
            
            # Record execution
            record = WebhookExecutionRecord(
                request_id=request.request_id,
                event_type=request.event_type,
                wallet_address=payload.wallet_address,
                status="submitted" if any(r["status"] == "submitted" for r in execution_results) else "failed",
                metadata={
                    "batch_results": execution_results,
                    "total_recipients": len(payload.recipients),
                },
            )
            self._record_execution(record)
            
            all_submitted = all(r.get("status") in ["submitted", "awaiting_signature"] for r in execution_results)
            
            return WebhookResponse(
                success=all_submitted,
                request_id=request.request_id,
                message=f"Batch payment processed ({len(execution_results)} recipients)",
                result={
                    "total_recipients": len(execution_results),
                    "successful": len([r for r in execution_results if r["status"] in ["submitted", "awaiting_signature"]]),
                    "results": execution_results,
                },
            )
        
        except Exception as e:
            logger.exception("Batch execute webhook error")
            record = WebhookExecutionRecord(
                request_id=request.request_id,
                event_type=request.event_type,
                wallet_address=request.payload.get("wallet_address", "unknown"),
                status="failed",
                error=str(e),
                metadata=request.payload,
            )
            self._record_execution(record)
            
            return WebhookResponse(
                success=False,
                request_id=request.request_id,
                message="Batch execution failed",
                error=str(e),
            )
    
    async def _handle_create_action(self, request: WebhookRequest) -> WebhookResponse:
        """Handle create_action webhook event."""
        try:
            from app.domains.payment_actions.models import CreatePaymentActionRequest
            
            req = CreatePaymentActionRequest(**request.payload)
            wallet = request.payload.get("wallet_address")
            
            if not wallet:
                return WebhookResponse(
                    success=False,
                    request_id=request.request_id,
                    message="Wallet address required",
                    error="wallet_address not provided",
                )
            
            # Create action
            action = await self.service.create_action(wallet, req)
            
            # Record execution
            record = WebhookExecutionRecord(
                request_id=request.request_id,
                event_type=request.event_type,
                wallet_address=wallet,
                action_id=action.id,
                status="completed",
                metadata={"action": action.dict()},
            )
            self._record_execution(record)
            
            return WebhookResponse(
                success=True,
                request_id=request.request_id,
                message=f"Action {action.name} created",
                result={
                    "action_id": action.id,
                    "name": action.name,
                    "type": action.action_type.value,
                },
            )
        
        except Exception as e:
            logger.exception("Create action webhook error")
            record = WebhookExecutionRecord(
                request_id=request.request_id,
                event_type=request.event_type,
                wallet_address=request.payload.get("wallet_address", "unknown"),
                status="failed",
                error=str(e),
                metadata=request.payload,
            )
            self._record_execution(record)
            
            return WebhookResponse(
                success=False,
                request_id=request.request_id,
                message="Action creation failed",
                error=str(e),
            )
    
    def _calculate_splits(self, recipients: list, total_amount: Decimal) -> list:
        """
        Calculate actual amounts for each recipient based on amounts or percentages.
        
        Args:
            recipients: List of recipient dicts with address and amount/percentage
            total_amount: Total amount to distribute
        
        Returns:
            List of dicts with calculated amounts
        """
        splits = []
        total_percentage = 0
        amount_based = []
        percentage_based = []
        
        # Separate amount-based from percentage-based
        for recipient in recipients:
            if recipient.get("amount"):
                amount_based.append(recipient)
            elif recipient.get("percentage"):
                percentage_based.append(recipient)
                total_percentage += recipient["percentage"]
        
        # Validate percentages don't exceed 100
        if total_percentage > 100:
            logger.error(f"Total percentages ({total_percentage}) exceed 100%")
            return []
        
        # Process amount-based recipients
        remaining = total_amount
        for recipient in amount_based:
            amount = Decimal(str(recipient["amount"]))
            splits.append({
                "address": recipient["address"],
                "amount": amount,
                "label": recipient.get("label"),
            })
            remaining -= amount
        
        # Process percentage-based recipients
        remaining_percentage = 100 - total_percentage
        for recipient in percentage_based:
            percentage = recipient["percentage"]
            amount = (total_amount * Decimal(str(percentage))) / Decimal(100)
            splits.append({
                "address": recipient["address"],
                "amount": amount,
                "label": recipient.get("label"),
            })
        
        return splits
    
    def _record_execution(self, record: WebhookExecutionRecord):
        """Record webhook execution for audit trail."""
        self.execution_history[record.request_id] = record.to_dict()
        logger.info(f"Webhook execution recorded: {record.request_id} - {record.status}")
    
    def get_execution_history(self, wallet_address: str, limit: int = 100) -> list:
        """Get execution history for a wallet."""
        records = [
            r for r in self.execution_history.values()
            if r.get("wallet_address") == wallet_address
        ]
        return sorted(records, key=lambda x: x["created_at"], reverse=True)[:limit]


# Singleton instance
_webhook_service: Optional[WebhookService] = None


async def get_webhook_service() -> WebhookService:
    """Get or create singleton webhook service."""
    global _webhook_service
    if _webhook_service is None:
        _webhook_service = WebhookService()
    return _webhook_service

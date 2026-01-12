"""Chat command processor for payment action management and execution."""
import json
import logging
from typing import Dict, Any, Optional
from app.models.unified_models import UnifiedCommand, UnifiedResponse, AgentType
from app.domains.payment_actions.models import (
    CreatePaymentActionRequest,
    UpdatePaymentActionRequest,
    PaymentActionType,
)
from app.domains.payment_actions.service import get_payment_action_service
from app.domains.payment_actions.executor import get_payment_executor

from .base_processor import BaseProcessor

logger = logging.getLogger(__name__)


class PaymentActionProcessor(BaseProcessor):
    """Process chat commands for payment action CRUD operations and execution."""
    
    def __init__(self, settings, protocol_registry, gmp_service, price_service, transaction_flow_service=None, **kwargs):
        """Initialize processor with shared dependencies."""
        super().__init__(settings, protocol_registry, gmp_service, price_service, transaction_flow_service, **kwargs)
        self.service = None
        self.executor = None
    
    async def _init_service(self):
        """Lazy initialize service and executor."""
        if self.service is None:
            self.service = await get_payment_action_service()
        if self.executor is None:
            self.executor = await get_payment_executor()
    
    async def process(self, command: UnifiedCommand) -> UnifiedResponse:
        """Process payment action commands."""
        await self._init_service()
        
        wallet_address = command.wallet_address
        if not wallet_address:
            return UnifiedResponse(
                content="Error: Wallet address required for payment actions",
                agent_type=AgentType.ERROR,
                status="error",
            )
        
        # Parse command intent
        text = command.command.lower()
        
        # CREATE action
        if any(phrase in text for phrase in [
            "create payment action",
            "new payment template",
            "make a shortcut",
            "create shortcut",
        ]):
            return await self._handle_create(command, wallet_address)
        
        # LIST actions
        elif any(phrase in text for phrase in [
            "show my payment actions",
            "show my templates",
            "list payment actions",
            "my shortcuts",
        ]):
            return await self._handle_list(wallet_address)
        
        # UPDATE action
        elif any(phrase in text for phrase in [
            "update payment action",
            "modify payment action",
            "edit payment action",
        ]):
            return await self._handle_update(command, wallet_address)
        
        # DELETE action
        elif any(phrase in text for phrase in [
            "delete payment action",
            "remove payment action",
            "remove shortcut",
        ]):
            return await self._handle_delete(command, wallet_address)
        
        # GET quick actions (for UI)
        elif "quick actions" in text:
            return await self._handle_quick_actions(wallet_address)
        
        # EXECUTE action
        elif any(phrase in text for phrase in [
            "use action",
            "execute action",
            "run payment",
            "make payment",
            "send with",
        ]):
            return await self._handle_execute(command, wallet_address)
        
        # CHECK execution status
        elif any(phrase in text for phrase in [
            "check payment status",
            "payment status",
            "ticket status",
            "transaction status",
        ]):
            return await self._handle_status(command, wallet_address)
        
        # VALIDATE before execution
        elif any(phrase in text for phrase in [
            "validate action",
            "check if i can",
            "can i execute",
        ]):
            return await self._handle_validate(command, wallet_address)
        
        # GUIDED SEND flow (just "send" or "pay")
        elif text.strip() in ["send", "pay"]:
            return await self._handle_send_guided(wallet_address)
        
        return UnifiedResponse(
            content="Unknown payment action command",
            agent_type=AgentType.ERROR,
            status="error",
        )
    
    async def _handle_send_guided(
        self,
        wallet_address: str,
    ) -> UnifiedResponse:
        """Handle guided send/pay flow - collects recipient and amount interactively."""
        return UnifiedResponse(
            content={
                "message": "Let's set up a payment! I'll guide you through it.",
                "step": "recipient",
                "prompt": "Who are you sending to? (Wallet address or ENS name, e.g., 'vitalik.eth' or '0x1234...')",
                "help": "You can use an Ethereum address (0x...) or an ENS name like 'user.eth'",
            },
            agent_type=AgentType.DEFAULT,
            status="success",
            awaiting_confirmation=True,
            metadata={
                "flow": "guided_send",
                "step_number": 1,
                "total_steps": 4,
            },
        )
    
    async def _handle_create(
        self,
        command: UnifiedCommand,
        wallet_address: str,
    ) -> UnifiedResponse:
        """Handle action creation flow initiation."""
        # Guide user through chat flow
        return UnifiedResponse(
            content={
                "message": "Let's create a payment action! I'll guide you through it.",
                "step": "name",
                "prompt": "What would you like to call this action? (e.g., 'Weekly Rent', 'Coffee Fund')",
            },
            agent_type=AgentType.DEFAULT,
            status="success",
            awaiting_confirmation=True,
        )
    
    async def _handle_list(
        self,
        wallet_address: str,
    ) -> UnifiedResponse:
        """List user's payment actions."""
        try:
            actions = await self.service.get_actions(
                wallet_address,
                enabled_only=True,
            )
            
            if not actions:
                return UnifiedResponse(
                    content="You haven't created any payment actions yet. Say 'create payment action' to start!",
                    agent_type=AgentType.DEFAULT,
                    status="success",
                )
            
            # Format actions for display
            action_list = []
            for action in actions:
                action_list.append({
                    "name": action.name,
                    "type": action.action_type.value,
                    "amount": action.amount,
                    "token": action.token,
                    "recipient": action.recipient_address[:10] + "...",
                    "usage_count": action.usage_count,
                    "last_used": action.last_used.isoformat() if action.last_used else "Never",
                })
            
            return UnifiedResponse(
                content={
                    "message": f"You have {len(actions)} payment action(s):",
                    "actions": action_list,
                },
                agent_type=AgentType.DEFAULT,
                status="success",
            )
        
        except Exception as e:
            logger.error(f"Error listing actions: {e}")
            return UnifiedResponse(
                content=f"Error retrieving payment actions: {str(e)}",
                agent_type=AgentType.ERROR,
                status="error",
            )
    
    async def _handle_update(
        self,
        command: UnifiedCommand,
        wallet_address: str,
    ) -> UnifiedResponse:
        """Handle action update flow."""
        return UnifiedResponse(
            content={
                "message": "Which action would you like to update?",
                "step": "select_action",
            },
            agent_type=AgentType.DEFAULT,
            status="success",
            awaiting_confirmation=True,
        )
    
    async def _handle_delete(
        self,
        command: UnifiedCommand,
        wallet_address: str,
    ) -> UnifiedResponse:
        """Handle action deletion."""
        return UnifiedResponse(
            content={
                "message": "Which action would you like to delete?",
                "step": "select_action_to_delete",
            },
            agent_type=AgentType.DEFAULT,
            status="success",
            awaiting_confirmation=True,
        )
    
    async def _handle_quick_actions(
        self,
        wallet_address: str,
    ) -> UnifiedResponse:
        """Get quick actions for UI rendering."""
        try:
            actions = await self.service.get_quick_actions(wallet_address)
            
            action_data = [
                {
                    "id": a.id,
                    "name": a.name,
                    "type": a.action_type.value,
                    "amount": a.amount,
                    "token": a.token,
                    "recipient": a.recipient_address,
                    "chain_id": a.chain_id,
                }
                for a in actions
            ]
            
            return UnifiedResponse(
                content={
                    "actions": action_data,
                },
                agent_type=AgentType.DEFAULT,
                status="success",
                metadata={
                    "action_type": "get_quick_actions",
                },
            )
        
        except Exception as e:
            logger.error(f"Error getting quick actions: {e}")
            return UnifiedResponse(
                content=[],
                agent_type=AgentType.DEFAULT,
                status="success",
                metadata={"error": str(e)},
            )
    
    async def _handle_execute(
        self,
        command: UnifiedCommand,
        wallet_address: str,
    ) -> UnifiedResponse:
        """Handle payment action execution."""
        try:
            # Extract action ID or name from command
            command_text = command.command.lower()
            action_id = None
            
            # Try to find action ID in command
            for word in command.command.split():
                if word.startswith("action_"):
                    action_id = word
                    break
            
            if not action_id:
                return UnifiedResponse(
                    content="Please specify which action to execute. Say 'use action {name}' or 'execute action {id}'.",
                    agent_type=AgentType.DEFAULT,
                    status="success",
                    awaiting_confirmation=True,
                )
            
            # Get the action
            action = await self.service.get_action(wallet_address, action_id)
            if not action:
                return UnifiedResponse(
                    content=f"Action '{action_id}' not found.",
                    agent_type=AgentType.ERROR,
                    status="error",
                )
            
            # Validate action can be executed
            validation = await self.executor.validate_action_for_execution(
                action,
                wallet_address,
            )
            
            if not validation["valid"]:
                error_msg = "\n".join(f"- {err}" for err in validation["errors"])
                return UnifiedResponse(
                    content={
                        "message": f"Cannot execute action '{action.name}':",
                        "errors": validation["errors"],
                    },
                    agent_type=AgentType.ERROR,
                    status="error",
                )
            
            # Execute action (without signing for now - would need wallet integration)
            result = await self.executor.execute_action(action, wallet_address)
            
            if result.status.value == "awaiting_signature":
                return UnifiedResponse(
                    content={
                        "message": f"Ready to execute '{action.name}'",
                        "action_id": action.id,
                        "amount": action.amount,
                        "token": action.token,
                        "recipient": action.recipient_address,
                        "status": "awaiting_signature",
                        "note": "This requires wallet signature",
                    },
                    agent_type=AgentType.TRANSFER,
                    status="success",
                    awaiting_confirmation=True,
                )
            
            elif result.status.value == "submitted":
                # Mark action as used
                await self.service.mark_used(wallet_address, action_id)
                
                return UnifiedResponse(
                    content={
                        "message": f"Payment '{action.name}' submitted successfully!",
                        "ticket_id": result.ticket_id,
                        "amount": result.metadata.get("amount"),
                        "token": result.metadata.get("token"),
                        "fee": result.metadata.get("fee_mnee"),
                        "status": "submitted",
                        "next_step": f"Check status with ticket: {result.ticket_id}",
                    },
                    agent_type=AgentType.TRANSFER,
                    status="success",
                    metadata={
                        "ticket_id": result.ticket_id,
                        "action_id": action_id,
                    },
                )
            
            else:
                return UnifiedResponse(
                    content={
                        "message": f"Failed to execute '{action.name}'",
                        "error": result.error_message,
                    },
                    agent_type=AgentType.ERROR,
                    status="error",
                )
        
        except Exception as e:
            logger.error(f"Error executing action: {e}")
            return UnifiedResponse(
                content=f"Error executing payment action: {str(e)}",
                agent_type=AgentType.ERROR,
                status="error",
            )
    
    async def _handle_status(
        self,
        command: UnifiedCommand,
        wallet_address: str,
    ) -> UnifiedResponse:
        """Handle checking payment execution status."""
        try:
            # Extract ticket ID from command
            ticket_id = None
            for word in command.command.split():
                if len(word) > 20 and "-" in word:  # UUID-like format
                    ticket_id = word
                    break
            
            if not ticket_id:
                return UnifiedResponse(
                    content="Please provide a ticket ID. Format: 'check payment status {ticket_id}'",
                    agent_type=AgentType.DEFAULT,
                    status="success",
                )
            
            # Get status from MNEE API
            status_data = await self.executor.get_execution_status(ticket_id)
            
            if "error" in status_data:
                return UnifiedResponse(
                    content={
                        "message": "Could not retrieve payment status",
                        "error": status_data["error"],
                        "ticket_id": ticket_id,
                    },
                    agent_type=AgentType.ERROR,
                    status="error",
                )
            
            return UnifiedResponse(
                content={
                    "message": f"Payment Status: {status_data['status']}",
                    "ticket_id": ticket_id,
                    "tx_id": status_data.get("tx_id"),
                    "status": status_data["status"],
                    "created_at": status_data.get("created_at"),
                    "updated_at": status_data.get("updated_at"),
                },
                agent_type=AgentType.DEFAULT,
                status="success",
                metadata=status_data,
            )
        
        except Exception as e:
            logger.error(f"Error checking status: {e}")
            return UnifiedResponse(
                content=f"Error checking payment status: {str(e)}",
                agent_type=AgentType.ERROR,
                status="error",
            )
    
    async def _handle_validate(
        self,
        command: UnifiedCommand,
        wallet_address: str,
    ) -> UnifiedResponse:
        """Handle validation of action before execution."""
        try:
            # Extract action ID from command
            action_id = None
            for word in command.command.split():
                if word.startswith("action_"):
                    action_id = word
                    break
            
            if not action_id:
                return UnifiedResponse(
                    content="Please specify which action to validate.",
                    agent_type=AgentType.DEFAULT,
                    status="success",
                )
            
            # Get the action
            action = await self.service.get_action(wallet_address, action_id)
            if not action:
                return UnifiedResponse(
                    content=f"Action '{action_id}' not found.",
                    agent_type=AgentType.ERROR,
                    status="error",
                )
            
            # Validate
            validation = await self.executor.validate_action_for_execution(
                action,
                wallet_address,
            )
            
            return UnifiedResponse(
                content={
                    "action_name": validation["action_name"],
                    "valid": validation["valid"],
                    "errors": validation["errors"],
                    "warnings": validation["warnings"],
                },
                agent_type=AgentType.DEFAULT,
                status="success",
            )
        
        except Exception as e:
            logger.error(f"Error validating action: {e}")
            return UnifiedResponse(
                content=f"Error validating action: {str(e)}",
                agent_type=AgentType.ERROR,
                status="error",
            )


# Singleton instance
_processor_instance: Optional[PaymentActionProcessor] = None


def get_payment_action_processor() -> PaymentActionProcessor:
    """Get or create singleton processor instance."""
    global _processor_instance
    if _processor_instance is None:
        _processor_instance = PaymentActionProcessor()
    return _processor_instance

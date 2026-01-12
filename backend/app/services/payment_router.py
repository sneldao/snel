"""
Unified Payment Router
Routes payments to the correct protocol adapter based on network and token.

Principles:
- DRY: Single routing logic for all payments
- MODULAR: Adapters are independent
- CLEAN: Unified interface for prepare/submit flow
"""

import logging
from typing import Dict, Any, Optional, Literal
from pydantic import BaseModel

from app.protocols.x402_adapter import X402Adapter, X402PaymentRequirements, STABLECOIN_CONTRACTS as X402_CONTRACTS
from app.protocols.mnee_adapter import MNEEAdapter
from app.protocols.registry import protocol_registry

logger = logging.getLogger(__name__)

class PaymentRoute(BaseModel):
    protocol: Literal["x402", "mnee"]
    network: str
    asset: str
    adapter_class: Any

class PaymentPreparationResult(BaseModel):
    """Unified response for payment preparation step."""
    action_type: Literal["sign_typed_data", "approve_allowance", "ready_to_execute"]
    protocol: str
    
    # For x402 (EIP-712)
    typed_data: Optional[Dict[str, Any]] = None
    
    # For MNEE (Relayer)
    relayer_address: Optional[str] = None
    amount_atomic: Optional[str] = None
    token_address: Optional[str] = None
    allowance_sufficient: Optional[bool] = None
    
    # Shared
    metadata: Dict[str, Any]

class PaymentRouter:
    """Routes payment requests to the appropriate protocol adapter."""
    
    def get_route(self, network: str, token_symbol: str = "USDC") -> PaymentRoute:
        """Determine the correct protocol based on network and token."""
        
        # Cronos Networks -> X402 (USDC only)
        if network in ["cronos-mainnet", "cronos-testnet"] and token_symbol == "USDC":
            return PaymentRoute(
                protocol="x402",
                network=network,
                asset=token_symbol,
                adapter_class=X402Adapter
            )
            
        # Ethereum Mainnet -> MNEE
        if network == "ethereum-mainnet" and token_symbol == "MNEE":
            return PaymentRoute(
                protocol="mnee",
                network=network,
                asset=token_symbol,
                adapter_class=MNEEAdapter
            )
            
        raise ValueError(f"No payment protocol found for {token_symbol} on {network}")

    async def prepare_payment(
        self, 
        network: str, 
        user_address: str, 
        recipient_address: str, 
        amount: float,
        token_symbol: str
    ) -> PaymentPreparationResult:
        """
        Step 1: Prepare payment action (EIP-712 payload OR Allowance check).
        """
        route = self.get_route(network, token_symbol)
        
        if route.protocol == "x402":
            adapter = X402Adapter(network)
            
            # Create requirements
            payment_requirements = X402PaymentRequirements(
                scheme="exact",
                network=network,
                payTo=recipient_address,
                asset=X402_CONTRACTS[network],
                maxAmountRequired=str(int(amount * 1_000_000)),
                maxTimeoutSeconds=300
            )
            
            # Generate payload
            payload = await adapter.create_unsigned_payment_payload(
                payment_requirements=payment_requirements,
                amount_usdc=amount
            )
            
            # Inject sender
            payload["message"]["from"] = user_address
            
            return PaymentPreparationResult(
                action_type="sign_typed_data",
                protocol="x402",
                typed_data={
                    "domain": payload["domain"],
                    "types": payload["types"],
                    "primaryType": payload["primaryType"],
                    "message": payload["message"]
                },
                metadata=payload["metadata"]
            )
            
        elif route.protocol == "mnee":
            adapter = MNEEAdapter() # Uses env vars
            relayer_address = adapter.get_relayer_address()
            
            if not relayer_address:
                raise ValueError("MNEE Relayer not configured")
                
            allowance_atomic = await adapter.check_allowance(user_address, relayer_address)
            amount_atomic = int(amount * 100000) # 5 decimals
            
            is_sufficient = allowance_atomic >= amount_atomic
            
            return PaymentPreparationResult(
                action_type="approve_allowance" if not is_sufficient else "ready_to_execute",
                protocol="mnee",
                relayer_address=relayer_address,
                amount_atomic=str(amount_atomic),
                token_address="0x8ccedbAe4916b79da7F3F612EfB2EB93A2bFD6cF", # MNEE
                allowance_sufficient=is_sufficient,
                metadata={
                    "network": network,
                    "scheme": "relayer",
                    "asset": "MNEE",
                    "user_address": user_address,
                    "recipient_address": recipient_address,
                    "amount": amount
                }
            )
            
        raise ValueError("Unsupported protocol")

    async def submit_payment(
        self,
        protocol: str,
        submission_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Step 2: Execute the payment (Submit signature OR Trigger Relayer).
        """
        if protocol == "x402":
            # Extract data
            signature = submission_data.get("signature")
            user_address = submission_data.get("user_address")
            message = submission_data.get("message")
            metadata = submission_data.get("metadata")
            
            adapter = X402Adapter(metadata["network"])
            
            # Construct header
            header_base64 = adapter.construct_payment_header_from_signature(
                signature=signature,
                user_address=user_address,
                metadata=metadata,
                message=message
            )
            
            # Reconstruct requirements
            payment_requirements = X402PaymentRequirements(
                scheme=metadata["scheme"],
                network=metadata["network"],
                payTo=message["to"],
                asset=metadata["asset"],
                maxAmountRequired=metadata.get("amount_atomic"),
                maxTimeoutSeconds=300
            )
            
            result = await adapter.settle_payment(header_base64, payment_requirements)
            return result.__dict__
            
        elif protocol == "mnee":
            # Extract data
            metadata = submission_data.get("metadata")
            user_address = metadata.get("user_address")
            recipient_address = metadata.get("recipient_address")
            amount = metadata.get("amount")
            
            adapter = MNEEAdapter()
            amount_atomic = int(amount * 100000)
            
            tx_hash = await adapter.execute_relayed_transfer(
                user_address=user_address,
                recipient_address=recipient_address,
                amount_atomic=amount_atomic
            )
            
            return {
                "success": True,
                "txHash": tx_hash,
                "protocol": "mnee"
            }
            
        raise ValueError(f"Unknown protocol: {protocol}")

payment_router = PaymentRouter()
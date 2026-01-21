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

from app.protocols.x402_adapter import X402Adapter, X402PaymentRequirements
from app.protocols.mnee_adapter import MNEEAdapter
from app.protocols.registry import protocol_registry
from app.config.tokens import COMMON_TOKENS, get_token_info
from app.config.chains import CHAINS, get_chain_id_by_name

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
        """
        Determine the correct protocol based on network and token.
        
        Routes:
        - Ethereum MNEE → X402 protocol (chain- and token-agnostic)
        - Ethereum MNEE → MNEE Relayer (legacy, for backwards compatibility)
        - Cronos USDC → X402 protocol
        """
        
        # Ethereum Mainnet + MNEE -> X402 (recommended) or MNEE Relayer
        if network == "ethereum-mainnet" and token_symbol == "MNEE":
            # Use MNEE Relayer/Native protocol for Ethereum Mainnet
            return PaymentRoute(
                protocol="mnee",
                network=network,
                asset=token_symbol,
                adapter_class=MNEEAdapter
            )
        
        # Cronos Networks -> X402 (USDC)
        if network in ["cronos-mainnet", "cronos-testnet"]:
            # Validate token support on Cronos
            if token_symbol != "USDC":
                 raise ValueError(f"Token {token_symbol} not supported on {network} (Only USDC supported)")

            return PaymentRoute(
                protocol="x402",
                network=network,
                asset=token_symbol,
                adapter_class=X402Adapter
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
            chain_id = adapter.chain_id
            
            # Get token decimals from central config
            token_info = COMMON_TOKENS.get(chain_id, {}).get(token_symbol.lower())
            if not token_info:
                raise ValueError(f"Token {token_symbol} not found for chain {chain_id}")
            
            decimals = token_info.get("decimals", 6)
            amount_atomic = str(int(amount * (10 ** decimals)))
            
            # Create requirements
            payment_requirements = X402PaymentRequirements(
                scheme="exact",
                network=network,
                payTo=recipient_address,
                asset=token_info["address"],
                maxAmountRequired=amount_atomic,
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
            
            # Get MNEE info from config
            mnee_info = COMMON_TOKENS[1]["mnee"]
            decimals = mnee_info["decimals"] # 5
            
            allowance_atomic = await adapter.check_allowance(user_address, relayer_address)
            amount_atomic = int(amount * (10 ** decimals))
            
            is_sufficient = allowance_atomic >= amount_atomic
            
            return PaymentPreparationResult(
                action_type="approve_allowance" if not is_sufficient else "ready_to_execute",
                protocol="mnee",
                relayer_address=relayer_address,
                amount_atomic=str(amount_atomic),
                token_address=mnee_info["address"],
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
            
            mnee_info = COMMON_TOKENS[1]["mnee"]
            amount_atomic = int(amount * (10 ** mnee_info["decimals"]))
            
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
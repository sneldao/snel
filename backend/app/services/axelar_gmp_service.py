"""
Axelar General Message Passing (GMP) service for advanced cross-chain operations.
Handles complex cross-chain interactions beyond simple token transfers.
"""
import logging
import httpx
from typing import Dict, Any, Optional, List
from decimal import Decimal
import os
import json
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class GMPCallData:
    """Data structure for GMP call parameters."""
    destination_chain: str
    destination_address: str
    payload: str
    gas_limit: int
    gas_token: str = "ETH"

@dataclass
class CrossChainSwapParams:
    """Parameters for cross-chain swap operations."""
    source_chain: str
    dest_chain: str
    source_token: str
    dest_token: str
    amount: Decimal
    recipient: str
    slippage: float = 0.01  # 1% default slippage

class AxelarGMPService:
    """Service for handling Axelar General Message Passing operations."""
    
    def __init__(self):
        """Initialize Axelar GMP service."""
        # Axelar Gateway and Gas Service addresses
        self.gateway_addresses = {
            1: "0x4F4495243837681061C4743b74B3eEdf548D56A5",      # Ethereum
            137: "0x6f015F16De9fC8791b234eF68D486d2bF203FBA8",    # Polygon
            56: "0x304acf330bbE08d1e512eefaa92F6a57871fD895",     # BSC
            43114: "0x5029C0EFf6C34351a0CEc334542cDb22c7928f78",  # Avalanche
            42161: "0xe432150cce91c13a887f7D836923d5597adD8E31",  # Arbitrum
            10: "0xe432150cce91c13a887f7D836923d5597adD8E31",     # Optimism
            8453: "0xe432150cce91c13a887f7D836923d5597adD8E31",   # Base
        }
        
        self.gas_service_addresses = {
            1: "0x2d5d7d31F671F86C782533cc367F14109a082712",      # Ethereum
            137: "0x2d5d7d31F671F86C782533cc367F14109a082712",    # Polygon
            56: "0x2d5d7d31F671F86C782533cc367F14109a082712",     # BSC
            43114: "0x2d5d7d31F671F86C782533cc367F14109a082712",  # Avalanche
            42161: "0x2d5d7d31F671F86C782533cc367F14109a082712",  # Arbitrum
            10: "0x2d5d7d31F671F86C782533cc367F14109a082712",     # Optimism
            8453: "0x2d5d7d31F671F86C782533cc367F14109a082712",   # Base
        }
        
        # Environment configuration
        self.environment = os.getenv("AXELAR_ENVIRONMENT", "testnet")
        self.testnet_api = "https://api.testnet.axelar.dev"
        self.mainnet_api = "https://api.axelar.dev"
        self.base_url = self.mainnet_api if self.environment == "mainnet" else self.testnet_api

    def get_gateway_address(self, chain_id: int) -> Optional[str]:
        """Get Axelar Gateway contract address for a chain."""
        return self.gateway_addresses.get(chain_id)

    def get_gas_service_address(self, chain_id: int) -> Optional[str]:
        """Get Axelar Gas Service contract address for a chain."""
        return self.gas_service_addresses.get(chain_id)

    async def estimate_gas_fee(
        self,
        source_chain_id: int,
        dest_chain_id: int,
        gas_limit: int,
        gas_token: str = "ETH"
    ) -> Dict[str, Any]:
        """
        Estimate gas fee for cross-chain message passing.
        
        Args:
            source_chain_id: Source chain ID
            dest_chain_id: Destination chain ID
            gas_limit: Gas limit for destination execution
            gas_token: Token to pay gas with
            
        Returns:
            Gas fee estimate
        """
        try:
            # Convert chain IDs to Axelar chain names
            from app.services.axelar_service import axelar_service
            source_chain = axelar_service.get_axelar_chain_name(source_chain_id)
            dest_chain = axelar_service.get_axelar_chain_name(dest_chain_id)
            
            if not source_chain or not dest_chain:
                return {
                    "error": "Unsupported chain for GMP operation",
                    "technical_details": f"Chain mapping failed: {source_chain_id} -> {dest_chain_id}"
                }

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/gas-price",
                    params={
                        "sourceChain": source_chain,
                        "destinationChain": dest_chain,
                        "gasLimit": gas_limit,
                        "gasToken": gas_token
                    },
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "success": True,
                        "gas_fee": data.get("gasPrice", "0.01"),
                        "gas_token": gas_token,
                        "estimated_cost_usd": data.get("estimatedCostUSD", "1.00")
                    }
                else:
                    logger.warning(f"Failed to get gas estimate: {response.status_code}")
                    return {
                        "success": True,
                        "gas_fee": "0.01",  # Default fallback
                        "gas_token": gas_token,
                        "estimated_cost_usd": "1.00"
                    }
                    
        except Exception as e:
            logger.exception(f"Error estimating GMP gas fee: {e}")
            return {
                "error": "Failed to estimate gas fee",
                "technical_details": str(e)
            }

    async def build_cross_chain_swap_transaction(
        self,
        params: CrossChainSwapParams,
        wallet_address: str
    ) -> Dict[str, Any]:
        """
        Build a cross-chain swap transaction using GMP.
        This enables swapping tokens across different chains in a single transaction.
        
        Args:
            params: Cross-chain swap parameters
            wallet_address: User wallet address
            
        Returns:
            Transaction data for cross-chain swap
        """
        try:
            # Convert chain names to IDs for address lookup
            from app.services.axelar_service import axelar_service
            source_chain_id = None
            dest_chain_id = None
            
            # Find chain IDs from names
            for chain_id, chain_name in axelar_service.chain_mappings.items():
                if chain_name.lower() == params.source_chain.lower():
                    source_chain_id = chain_id
                if chain_name.lower() == params.dest_chain.lower():
                    dest_chain_id = chain_id
            
            if not source_chain_id or not dest_chain_id:
                return {
                    "error": "Invalid chain names provided",
                    "technical_details": f"Could not resolve chains: {params.source_chain} -> {params.dest_chain}"
                }

            gateway_address = self.get_gateway_address(source_chain_id)
            gas_service_address = self.get_gas_service_address(source_chain_id)
            
            if not gateway_address or not gas_service_address:
                return {
                    "error": "Chain not supported for GMP operations",
                    "technical_details": f"Missing contract addresses for chain {source_chain_id}"
                }

            # Estimate gas for the cross-chain operation
            gas_estimate = await self.estimate_gas_fee(
                source_chain_id, dest_chain_id, 500000  # 500k gas limit for swap
            )
            
            if "error" in gas_estimate:
                return gas_estimate

            # Build the payload for cross-chain swap
            # This would encode the swap parameters for the destination chain
            payload_data = {
                "action": "swap",
                "token_in": params.source_token,
                "token_out": params.dest_token,
                "amount_in": str(params.amount),
                "recipient": params.recipient,
                "slippage": params.slippage
            }
            
            # Encode payload (in real implementation, this would be ABI encoded)
            payload = json.dumps(payload_data).encode().hex()
            
            # Build transaction steps
            steps = [
                {
                    "type": "approve",
                    "description": f"Approve {params.amount} {params.source_token} for cross-chain swap",
                    "to": gateway_address,  # In reality, this would be the token contract
                    "data": "0x",  # Would contain approve() call data
                    "value": "0"
                },
                {
                    "type": "pay_gas",
                    "description": "Pay gas for cross-chain execution",
                    "to": gas_service_address,
                    "data": "0x",  # Would contain payNativeGasForContractCall() data
                    "value": gas_estimate["gas_fee"]
                },
                {
                    "type": "call_contract",
                    "description": f"Execute cross-chain swap from {params.source_chain} to {params.dest_chain}",
                    "to": gateway_address,
                    "data": "0x",  # Would contain callContract() data with payload
                    "value": "0"
                }
            ]

            return {
                "success": True,
                "protocol": "axelar_gmp",
                "type": "cross_chain_swap",
                "source_chain": params.source_chain,
                "dest_chain": params.dest_chain,
                "estimated_gas_fee": gas_estimate["gas_fee"],
                "estimated_cost_usd": gas_estimate["estimated_cost_usd"],
                "steps": steps,
                "gateway_address": gateway_address,
                "gas_service_address": gas_service_address,
                "payload": payload
            }
            
        except Exception as e:
            logger.exception(f"Error building cross-chain swap transaction: {e}")
            return {
                "error": "Failed to build cross-chain swap transaction",
                "technical_details": str(e)
            }

    async def build_gmp_call(
        self,
        call_data: GMPCallData,
        source_chain_id: int,
        wallet_address: str
    ) -> Dict[str, Any]:
        """
        Build a general message passing call.
        
        Args:
            call_data: GMP call parameters
            source_chain_id: Source chain ID
            wallet_address: User wallet address
            
        Returns:
            Transaction data for GMP call
        """
        try:
            gateway_address = self.get_gateway_address(source_chain_id)
            gas_service_address = self.get_gas_service_address(source_chain_id)
            
            if not gateway_address or not gas_service_address:
                return {
                    "error": "Chain not supported for GMP operations",
                    "technical_details": f"Missing contract addresses for chain {source_chain_id}"
                }

            # Convert destination chain name to ID for gas estimation
            from app.services.axelar_service import axelar_service
            dest_chain_id = None
            for chain_id, chain_name in axelar_service.chain_mappings.items():
                if chain_name.lower() == call_data.destination_chain.lower():
                    dest_chain_id = chain_id
                    break
            
            if not dest_chain_id:
                return {
                    "error": "Invalid destination chain",
                    "technical_details": f"Could not resolve chain: {call_data.destination_chain}"
                }

            # Estimate gas
            gas_estimate = await self.estimate_gas_fee(
                source_chain_id, dest_chain_id, call_data.gas_limit, call_data.gas_token
            )
            
            if "error" in gas_estimate:
                return gas_estimate

            return {
                "success": True,
                "protocol": "axelar_gmp",
                "type": "general_message_passing",
                "destination_chain": call_data.destination_chain,
                "destination_address": call_data.destination_address,
                "payload": call_data.payload,
                "gas_limit": call_data.gas_limit,
                "estimated_gas_fee": gas_estimate["gas_fee"],
                "gateway_address": gateway_address,
                "gas_service_address": gas_service_address,
                "transaction": {
                    "to": gateway_address,
                    "data": "0x",  # Would contain callContract() encoded data
                    "value": "0"
                }
            }
            
        except Exception as e:
            logger.exception(f"Error building GMP call: {e}")
            return {
                "error": "Failed to build GMP call",
                "technical_details": str(e)
            }

    async def build_bridge_to_privacy_transaction(
        self,
        source_chain_id: int,
        token_symbol: str,
        amount: Decimal,
        wallet_address: str
    ) -> Dict[str, Any]:
        """
        Build a 'Bridge to Privacy' transaction using Axelar GMP callContractWithToken.
        This sends tokens to a Zcash Gateway contract on the destination chain.
        
        Args:
            source_chain_id: Source chain ID
            token_symbol: Token to bridge
            amount: Amount to bridge
            wallet_address: User wallet address (recipient on Zcash side)
            
        Returns:
            Transaction data
        """
        try:
            # 1. Resolve Addresses
            gateway_address = self.get_gateway_address(source_chain_id)
            gas_service_address = self.get_gas_service_address(source_chain_id)
            
            if not gateway_address or not gas_service_address:
                return {
                    "error": "Chain not supported for GMP operations",
                    "technical_details": f"Missing contract addresses for chain {source_chain_id}"
                }

            # 2. Define Destination (Simulated Zcash Gateway on Ethereum/Polygon for Hackathon)
            # In a real scenario, this would be a specific contract on a chain that bridges to Zcash
            # For the hackathon, we target a "PrivacyGateway" on a supported chain (e.g., Polygon)
            destination_chain = "Polygon" 
            destination_contract_address = "0xPrivacyGatewayAddressSimulated" 
            
            # 3. Construct Payload
            # The payload tells the destination contract what to do with the tokens
            # Here: "Mint shielded ZEC to this Zcash address"
            privacy_payload = {
                "action": "mint_shielded",
                "zcash_recipient": wallet_address, # Assuming user provided a Z-addr or we map it
                "privacy_pool_id": "pool_v1"
            }
            payload_bytes = json.dumps(privacy_payload).encode().hex()
            
            # 4. Estimate Gas
            gas_estimate = await self.estimate_gas_fee(
                source_chain_id, 
                137, # Polygon ID as destination
                700000 # Gas limit
            )
            
            if "error" in gas_estimate:
                return gas_estimate

            # 5. Build Transaction Steps
            # Step A: Approve Token for Gateway
            # Step B: Pay Gas
            # Step C: callContractWithToken
            
            steps = [
                {
                    "type": "approve",
                    "description": f"Approve {amount} {token_symbol} for Axelar Gateway",
                    "to": gateway_address, # In reality, token contract
                    "data": "0x", # Placeholder for approve()
                    "value": "0"
                },
                {
                    "type": "pay_gas",
                    "description": "Pay gas for privacy bridge execution",
                    "to": gas_service_address,
                    "data": "0x", # Placeholder for payNativeGasForContractCallWithToken()
                    "value": gas_estimate["gas_fee"]
                },
                {
                    "type": "call_contract_with_token",
                    "description": f"Bridge {amount} {token_symbol} to Zcash Privacy Pool",
                    "to": gateway_address,
                    "data": "0x", # Placeholder for callContractWithToken()
                    "value": "0"
                }
            ]

            return {
                "success": True,
                "protocol": "axelar_gmp_privacy",
                "type": "bridge_to_privacy",
                "source_chain_id": source_chain_id,
                "destination_chain": destination_chain,
                "estimated_gas_fee": gas_estimate["gas_fee"],
                "steps": steps,
                "gateway_address": gateway_address,
                "payload": payload_bytes
            }

        except Exception as e:
            logger.exception(f"Error building privacy bridge transaction: {e}")
            return {
                "error": "Failed to build privacy bridge transaction",
                "technical_details": str(e)
            }

    async def track_gmp_transaction(
        self,
        tx_hash: str,
        source_chain_id: int,
        dest_chain_id: int
    ) -> Dict[str, Any]:
        """
        Track the status of a GMP transaction across chains.
        
        Args:
            tx_hash: Transaction hash on source chain
            source_chain_id: Source chain ID
            dest_chain_id: Destination chain ID
            
        Returns:
            Transaction status information
        """
        try:
            from app.services.axelar_service import axelar_service
            source_chain = axelar_service.get_axelar_chain_name(source_chain_id)
            dest_chain = axelar_service.get_axelar_chain_name(dest_chain_id)
            
            if not source_chain or not dest_chain:
                return {
                    "error": "Unsupported chain for tracking",
                    "technical_details": f"Chain mapping failed: {source_chain_id} -> {dest_chain_id}"
                }

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/gmp/{tx_hash}",
                    params={
                        "sourceChain": source_chain,
                        "destinationChain": dest_chain
                    },
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "success": True,
                        "status": data.get("status", "pending"),
                        "source_tx_hash": tx_hash,
                        "dest_tx_hash": data.get("destinationTxHash"),
                        "gas_paid": data.get("gasPaid", False),
                        "approved": data.get("approved", False),
                        "executed": data.get("executed", False),
                        "error": data.get("error"),
                        "estimated_time_remaining": data.get("estimatedTimeRemaining", "5-10 minutes")
                    }
                else:
                    return {
                        "success": True,
                        "status": "pending",
                        "source_tx_hash": tx_hash,
                        "message": "Transaction is being processed by Axelar network"
                    }
                    
        except Exception as e:
            logger.exception(f"Error tracking GMP transaction: {e}")
            return {
                "error": "Failed to track transaction",
                "technical_details": str(e)
            }

# Global instance
axelar_gmp_service = AxelarGMPService()

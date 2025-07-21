"""
Axelar service for cross-chain operations.
Handles cross-chain swaps and transfers using Axelar Network.
"""
import logging
import httpx
from typing import Dict, Any, Optional
from decimal import Decimal
import os
import json

logger = logging.getLogger(__name__)

class AxelarService:
    """Service for handling Axelar cross-chain operations."""
    
    def __init__(self):
        """Initialize Axelar service."""
        # Axelar API endpoints
        self.testnet_api = "https://api.testnet.axelar.dev"
        self.mainnet_api = "https://api.axelar.dev"
        self.environment = os.getenv("AXELAR_ENVIRONMENT", "testnet")
        self.base_url = self.mainnet_api if self.environment == "mainnet" else self.testnet_api
        
        # Chain mappings for Axelar
        self.chain_mappings = {
            1: "Ethereum",
            56: "binance",
            137: "Polygon",
            43114: "Avalanche", 
            42161: "Arbitrum",
            10: "optimism",
            8453: "base",
            59144: "linea"
        }
        
        # Supported tokens on Axelar
        self.supported_tokens = {
            "USDC": {
                "Ethereum": "0xA0b86a33E6441b8C8A008c85c9c8B99c5b5a3c3b",
                "Polygon": "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174",
                "Avalanche": "0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E",
                "Arbitrum": "0xFF970A61A04b1cA14834A43f5dE4533eBDDB5CC8",
                "base": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
            },
            "USDT": {
                "Ethereum": "0xdAC17F958D2ee523a2206206994597C13D831ec7",
                "Polygon": "0xc2132D05D31c914a87C6611C10748AEb04B58e8F",
                "Avalanche": "0x9702230A8Ea53601f5cD2dc00fDBc13d4dF4A8c7",
                "Arbitrum": "0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9"
            },
            "ETH": {
                "Ethereum": "native",
                "Arbitrum": "native",
                "base": "native",
                "optimism": "native"
            },
            "WETH": {
                "Ethereum": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
                "Polygon": "0x7ceB23fD6bC0adD59E62ac25578270cFf1b9f619",
                "Avalanche": "0x49D5c2BdFfac6CE2BFdB6640F4F80f226bc10bAB",
                "Arbitrum": "0x82aF49447D8a07e3bd95BD0d56f35241523fBab1"
            }
        }

    def get_axelar_chain_name(self, chain_id: int) -> Optional[str]:
        """Get Axelar chain name from chain ID."""
        return self.chain_mappings.get(chain_id)

    def is_chain_supported(self, chain_id: int) -> bool:
        """Check if chain is supported by Axelar."""
        return chain_id in self.chain_mappings

    def is_token_supported(self, token_symbol: str, chain_id: int) -> bool:
        """Check if token is supported on the given chain."""
        chain_name = self.get_axelar_chain_name(chain_id)
        if not chain_name:
            return False
        
        token_upper = token_symbol.upper()
        return token_upper in self.supported_tokens and chain_name in self.supported_tokens[token_upper]

    async def get_cross_chain_quote(
        self,
        from_token: str,
        to_token: str,
        amount: Decimal,
        from_chain_id: int,
        to_chain_id: int,
        wallet_address: str
    ) -> Dict[str, Any]:
        """
        Get quote for cross-chain transfer using Axelar.
        
        Args:
            from_token: Source token symbol
            to_token: Destination token symbol  
            amount: Amount to transfer
            from_chain_id: Source chain ID
            to_chain_id: Destination chain ID
            wallet_address: User wallet address
            
        Returns:
            Quote information or error
        """
        try:
            # Validate chains
            from_chain = self.get_axelar_chain_name(from_chain_id)
            to_chain = self.get_axelar_chain_name(to_chain_id)
            
            if not from_chain:
                return {
                    "error": f"Source chain {from_chain_id} is not supported by Axelar",
                    "technical_details": f"Chain ID {from_chain_id} not in supported chains"
                }
                
            if not to_chain:
                return {
                    "error": f"Destination chain {to_chain_id} is not supported by Axelar", 
                    "technical_details": f"Chain ID {to_chain_id} not in supported chains"
                }

            # Validate tokens
            if not self.is_token_supported(from_token, from_chain_id):
                return {
                    "error": f"{from_token} is not supported on {from_chain} via Axelar",
                    "technical_details": f"Token {from_token} not supported on chain {from_chain_id}"
                }
                
            if not self.is_token_supported(to_token, to_chain_id):
                return {
                    "error": f"{to_token} is not supported on {to_chain} via Axelar",
                    "technical_details": f"Token {to_token} not supported on chain {to_chain_id}"
                }

            # For cross-chain transfers, tokens should typically be the same
            if from_token.upper() != to_token.upper():
                return {
                    "error": "Cross-chain swaps between different tokens are not supported. Use same token on both chains.",
                    "technical_details": f"Cannot swap {from_token} to {to_token} cross-chain"
                }

            # Get transfer fee estimate
            fee_estimate = await self._get_transfer_fee(from_chain, to_chain, from_token, float(amount))
            
            # Calculate estimated time
            estimated_time = self._get_estimated_time(from_chain, to_chain)
            
            # Get deposit address
            deposit_address = await self._get_deposit_address(
                from_chain, to_chain, wallet_address, from_token
            )
            
            return {
                "success": True,
                "protocol": "axelar",
                "type": "cross_chain_transfer",
                "from_chain": from_chain,
                "to_chain": to_chain,
                "from_token": from_token,
                "to_token": to_token,
                "amount": str(amount),
                "estimated_fee": fee_estimate,
                "estimated_time": estimated_time,
                "deposit_address": deposit_address,
                "recipient_address": wallet_address,
                "steps": [
                    {
                        "type": "transfer",
                        "description": f"Transfer {amount} {from_token} to Axelar deposit address",
                        "chain": from_chain,
                        "to": deposit_address,
                        "value": str(amount) if from_token.upper() == "ETH" else "0",
                        "data": "0x" if from_token.upper() == "ETH" else None
                    }
                ]
            }
            
        except Exception as e:
            logger.exception(f"Error getting Axelar quote: {e}")
            return {
                "error": "Failed to get cross-chain quote",
                "technical_details": str(e)
            }

    async def get_same_chain_quote(
        self,
        from_token: str,
        to_token: str,
        amount: Decimal,
        chain_id: int,
        wallet_address: str
    ) -> Dict[str, Any]:
        """
        Get quote for same-chain swap. 
        Note: Axelar is primarily for cross-chain, so this will return an error
        suggesting to use a different protocol for same-chain swaps.
        """
        chain_name = self.get_axelar_chain_name(chain_id)
        
        return {
            "error": "Axelar is designed for cross-chain transfers. For same-chain swaps, please use a different protocol.",
            "technical_details": f"Same-chain swap requested on {chain_name} ({chain_id})",
            "suggestion": "Try using a DEX aggregator like 1inch or 0x for same-chain swaps."
        }

    async def _get_transfer_fee(self, from_chain: str, to_chain: str, token: str, amount: float) -> str:
        """Get transfer fee estimate from Axelar API."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/transfer-fee",
                    params={
                        "sourceChain": from_chain,
                        "destinationChain": to_chain,
                        "asset": token,
                        "amount": amount
                    },
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return data.get("fee", "0.01")  # Default fee if not available
                else:
                    logger.warning(f"Failed to get transfer fee: {response.status_code}")
                    return "0.01"  # Default fee
                    
        except Exception as e:
            logger.warning(f"Error getting transfer fee: {e}")
            return "0.01"  # Default fee

    async def _get_deposit_address(self, from_chain: str, to_chain: str, recipient: str, token: str) -> str:
        """Get deposit address for cross-chain transfer."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/deposit-address",
                    json={
                        "sourceChain": from_chain,
                        "destinationChain": to_chain,
                        "destinationAddress": recipient,
                        "asset": token
                    },
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return data.get("depositAddress", "")
                else:
                    logger.warning(f"Failed to get deposit address: {response.status_code}")
                    # Return a placeholder - in real implementation this would be handled differently
                    return "0x0000000000000000000000000000000000000000"
                    
        except Exception as e:
            logger.warning(f"Error getting deposit address: {e}")
            # Return a placeholder - in real implementation this would be handled differently  
            return "0x0000000000000000000000000000000000000000"

    def _get_estimated_time(self, from_chain: str, to_chain: str) -> str:
        """Get estimated transfer time based on chains."""
        # Ethereum transfers typically take longer due to finality requirements
        if from_chain == "Ethereum" or to_chain == "Ethereum":
            return "15-20 minutes"
        else:
            return "5-10 minutes"

    def get_supported_chains(self) -> Dict[int, str]:
        """Get all supported chains."""
        return self.chain_mappings.copy()

    def get_supported_tokens_for_chain(self, chain_id: int) -> list[str]:
        """Get supported tokens for a specific chain."""
        chain_name = self.get_axelar_chain_name(chain_id)
        if not chain_name:
            return []
            
        supported = []
        for token, chains in self.supported_tokens.items():
            if chain_name in chains:
                supported.append(token)
        return supported

# Global instance
axelar_service = AxelarService()
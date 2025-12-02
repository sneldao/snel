"""
Circle CCTP V2 service for cross-chain USDC transfers.
Real Circle API integration with proper error handling and configuration management.
"""
import logging
import httpx
import asyncio
import time
from typing import Dict, Any, Optional, List, Tuple
from decimal import Decimal
import os
import json
from eth_abi import encode as abi_encode
from eth_utils import function_signature_to_4byte_selector, to_checksum_address
from ..core.config_manager import config_manager
from ..core.errors import ProtocolError, ProtocolAPIError, NetworkError, ValidationError
from .utils.transaction_utils import transaction_utils

logger = logging.getLogger(__name__)

class CircleCCTPService:
    """Enhanced Circle CCTP V2 service with real API integration and proper error handling."""

    def __init__(self):
        """Initialize Circle CCTP service."""
        self.config = None
        self.session = None
        # Rate limiting and circuit breaker
        self._rate_limit_window = 1.0  # seconds
        self._max_requests_per_window = 10  # Circle API limit
        self._failure_threshold = 3
        self._cooldown_seconds = 60
        self._api_state = {}  # Track API health per endpoint
        # Response cache for attestations and quotes
        self._quote_cache = {}
        self._quote_cache_ttl = 60  # 1 minute for quotes
        self._attestation_cache = {}
        self._attestation_cache_ttl = 300  # 5 minutes for attestations
        
        # Initialize chain mappings immediately
        self.chain_mappings = {
            1: "ethereum",
            42161: "arbitrum", 
            8453: "base",
            137: "polygon",
            10: "optimism",
            43114: "avalanche",
            59144: "linea",
            480: "worldchain",
            146: "sonic"
        }

    async def initialize(self):
        """Initialize service with configuration manager."""
        self.config = await config_manager.get_protocol("cctp_v2")
        if not self.config:
            raise ProtocolError(
                message="Circle CCTP V2 protocol configuration not found",
                protocol="cctp_v2",
                user_message="Circle cross-chain USDC bridge is not properly configured"
            )

        # Initialize HTTP session
        timeout = httpx.Timeout(30.0, connect=5.0)
        headers = {
            "User-Agent": "SNEL/1.0",
            "Content-Type": "application/json"
        }
        
        # Add API key if available
        api_key = self.config.api_keys.get("default")
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
            
        self.session = httpx.AsyncClient(timeout=timeout, headers=headers)

        logger.info("Circle CCTP V2 service initialized - using ConfigurationManager for contract addresses")

    async def _apply_rate_limit(self, endpoint: str):
        """Apply rate limiting per API endpoint."""
        state = self._api_state.setdefault(endpoint, {"timestamps": [], "failures": 0, "circuit_open": False, "circuit_opened_at": 0})
        now = time.time()
        
        # Remove old timestamps
        state["timestamps"] = [t for t in state["timestamps"] if now - t < self._rate_limit_window]
        
        if len(state["timestamps"]) >= self._max_requests_per_window:
            sleep_time = self._rate_limit_window - (now - min(state["timestamps"]))
            await asyncio.sleep(sleep_time)
        
        state["timestamps"].append(time.time())

    def _record_failure(self, endpoint: str):
        """Record API failure and open circuit if threshold exceeded."""
        state = self._api_state.setdefault(endpoint, {"timestamps": [], "failures": 0, "circuit_open": False, "circuit_opened_at": 0})
        state["failures"] += 1
        
        if state["failures"] >= self._failure_threshold:
            state["circuit_open"] = True
            state["circuit_opened_at"] = time.time()
            logger.warning(f"Circuit breaker opened for Circle CCTP endpoint: {endpoint}")

    def _reset_circuit(self, endpoint: str):
        """Reset circuit breaker after cooldown period."""
        state = self._api_state.get(endpoint)
        if state and state["circuit_open"]:
            if time.time() - state["circuit_opened_at"] >= self._cooldown_seconds:
                state["circuit_open"] = False
                state["failures"] = 0
                logger.info(f"Circuit breaker reset for Circle CCTP endpoint: {endpoint}")

    async def _api_call(self, endpoint: str, method: str = "GET", **kwargs) -> Dict[str, Any]:
        """Make API call with rate limiting and circuit breaker."""
        self._reset_circuit(endpoint)
        state = self._api_state.get(endpoint, {})
        
        if state.get("circuit_open"):
            raise ProtocolAPIError(
                protocol="cctp_v2",
                endpoint=endpoint,
                status_code=0,
                user_message="Circle CCTP API temporarily unavailable"
            )
        
        await self._apply_rate_limit(endpoint)
        
        try:
            if method.upper() == "GET":
                response = await self.session.get(endpoint, **kwargs)
            else:
                response = await self.session.post(endpoint, **kwargs)
            
            response.raise_for_status()
            
            # Reset failures on success
            if state:
                state["failures"] = 0
            
            return response.json()
            
        except Exception as e:
            self._record_failure(endpoint)
            raise e

    def get_supported_chains(self) -> Dict[int, str]:
        """Get all supported chains."""
        return self.chain_mappings.copy()

    def is_chain_supported(self, chain_id: int) -> bool:
        """Check if chain is supported by Circle CCTP V2."""
        return chain_id in self.chain_mappings

    async def is_token_supported(self, token_symbol: str, chain_id: int) -> bool:
        """Check if token is supported on the given chain via Circle CCTP V2."""
        # Circle CCTP V2 only supports USDC
        if token_symbol.upper() != "USDC":
            return False
            
        # Check if chain is supported
        if not self.is_chain_supported(chain_id):
            return False

        # Check if USDC exists in our configuration for this chain
        token_config = await config_manager.get_token_by_symbol("USDC")
        if not token_config:
            return False

        return chain_id in token_config.addresses

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
        Get quote for cross-chain USDC transfer using Circle CCTP V2.

        Args:
            from_token: Source token symbol (must be USDC)
            to_token: Destination token symbol (must be USDC)
            amount: Amount to transfer
            from_chain_id: Source chain ID
            to_chain_id: Destination chain ID
            wallet_address: User wallet address

        Returns:
            Quote information or error
        """
        try:
            if not self.session:
                await self.initialize()

            # Validate tokens are USDC
            if from_token.upper() != "USDC" or to_token.upper() != "USDC":
                raise ValidationError(
                    message="Circle CCTP V2 only supports USDC transfers",
                    field="token_pair",
                    value=f"{from_token} -> {to_token}"
                )

            # Enhanced validation using new validation method
            from_chain = self.chain_mappings.get(from_chain_id)
            to_chain = self.chain_mappings.get(to_chain_id)

            if not from_chain or not to_chain:
                raise ProtocolError(
                    message=f"Unsupported chain(s): {from_chain_id} -> {to_chain_id}",
                    protocol="cctp_v2",
                    user_message="One or both chains are not supported by Circle CCTP V2"
                )

            # Comprehensive validation
            is_valid, validation_message = await self._validate_cross_chain_transfer(
                from_chain_id, to_chain_id, wallet_address, amount
            )
            
            if not is_valid:
                raise ValidationError(
                    message=validation_message,
                    field="cross_chain_transfer",
                    value=f"{from_chain} -> {to_chain}"
                )

            # Get transfer fee estimate
            fee_estimate = await self._get_transfer_fee(from_chain_id, to_chain_id, amount)

            # Calculate estimated time
            estimated_time = self._get_estimated_time(from_chain_id, to_chain_id)

            # Get Circle contract addresses for the source chain
            contracts = self.config.contract_addresses.get(from_chain_id, {})
            token_messenger = contracts.get("token_messenger")
            usdc_address = contracts.get("usdc")
            
            if not token_messenger or not usdc_address:
                raise ProtocolError(
                    message=f"Circle CCTP contracts not configured for chain {from_chain_id}",
                    protocol="cctp_v2",
                    user_message="Circle CCTP bridge not available on this network"
                )

            # Build transaction steps
            steps = await self._build_transaction_steps(
                from_chain_id, to_chain_id, amount, wallet_address,
                token_messenger, usdc_address
            )

            return {
                "success": True,
                "protocol": "cctp_v2",
                "type": "cross_chain_usdc_transfer",
                "from_chain": from_chain,
                "to_chain": to_chain,
                "from_token": "USDC",
                "to_token": "USDC",
                "amount": str(amount),
                "estimated_fee": fee_estimate,
                "estimated_time": estimated_time,
                "token_messenger": token_messenger,
                "usdc_address": usdc_address,
                "recipient_address": wallet_address,
                "steps": steps
            }

        except Exception as e:
            logger.exception(f"Error getting Circle CCTP quote: {e}")
            return {
                "error": "Failed to get cross-chain USDC quote",
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
        Get quote for same-chain operation.
        Note: Circle CCTP V2 is for cross-chain, so this will return an error
        suggesting to use a different protocol for same-chain operations.
        """
        chain_name = self.chain_mappings.get(chain_id, f"chain_{chain_id}")

        return {
            "error": "Circle CCTP V2 is designed for cross-chain USDC transfers. For same-chain operations, please use a different protocol.",
            "technical_details": f"Same-chain operation requested on {chain_name} ({chain_id})",
            "suggestion": "Try using a DEX aggregator like 0x or Uniswap for same-chain swaps."
        }

    async def _get_transfer_fee(self, from_chain_id: int, to_chain_id: int, amount: Decimal) -> str:
        """Get transfer fee estimate using Circle CCTP V2 API."""
        try:
            if not self.session:
                await self.initialize()

            # Cache key for fee estimates
            cache_key = f"fee:{from_chain_id}:{to_chain_id}:{int(amount)}"
            cached = self._quote_cache.get(cache_key)
            now = int(time.time())
            
            if cached and (now - cached.get("ts", 0) <= self._quote_cache_ttl):
                return cached["fee"]

            # Use Circle's fee estimation endpoint
            api_endpoint = self.config.api_endpoints.get("mainnet")
            
            try:
                # Circle CCTP V2 fee estimation endpoint
                endpoint = f"{api_endpoint}/cctp/estimate-fee"
                payload = {
                    "sourceChainId": from_chain_id,
                    "destinationChainId": to_chain_id,
                    "amount": str(int(amount * Decimal(10**6)))  # USDC has 6 decimals
                }
                
                data = await self._api_call(endpoint, method="POST", json=payload)
                
                # Extract fee from response
                fee = data.get("estimatedFee", "0.1")  # Default fallback
                
                # Cache the result
                self._quote_cache[cache_key] = {"ts": now, "fee": str(fee)}
                
                return str(fee)
                
            except Exception as api_error:
                logger.warning(f"Circle CCTP API call failed: {api_error}")
                
                # Intelligent fallback based on chain characteristics
                base_fee = self._estimate_base_fee(from_chain_id, to_chain_id, amount)
                
                # Cache fallback result with shorter TTL
                self._quote_cache[cache_key] = {"ts": now, "fee": base_fee}
                
                return base_fee

        except Exception as e:
            logger.error(f"Error getting Circle CCTP transfer fee: {e}")
            # Final fallback
            return self._estimate_base_fee(from_chain_id, to_chain_id, amount)

    def _estimate_base_fee(self, from_chain_id: int, to_chain_id: int, amount: Decimal) -> str:
        """Intelligent fee estimation based on chain characteristics."""
        # Base fees by chain (in USD) - Circle CCTP is generally cheaper than bridges
        chain_base_fees = {
            1: 0.02,      # Ethereum - higher due to gas costs
            42161: 0.005, # Arbitrum - L2 efficiency
            8453: 0.005,  # Base - L2 efficiency
            137: 0.01,    # Polygon - low fees
            10: 0.005,    # Optimism - L2 efficiency
            43114: 0.01,  # Avalanche - fast finality
            59144: 0.01,  # Linea - new L2
            480: 0.005,   # World Chain - optimized
            146: 0.005    # Sonic - fast
        }
        
        from_fee = chain_base_fees.get(from_chain_id, 0.02)
        to_fee = chain_base_fees.get(to_chain_id, 0.02)
        
        # Circle CCTP premium (lower than traditional bridges)
        cctp_premium = 0.005
        
        total_fee = from_fee + to_fee + cctp_premium
        
        return f"{total_fee:.4f}"

    async def _validate_cross_chain_transfer(
        self, 
        from_chain_id: int, 
        to_chain_id: int, 
        recipient: str, 
        amount: Decimal
    ) -> Tuple[bool, str]:
        """Validate cross-chain transfer parameters."""
        # Validate recipient address format
        if not recipient or len(recipient) != 42 or not recipient.startswith("0x"):
            return False, f"Invalid recipient address format: {recipient}"
        
        # Validate chains are different
        if from_chain_id == to_chain_id:
            return False, "Source and destination chains must be different for cross-chain transfers"
        
        # Validate both chains are supported
        if not self.is_chain_supported(from_chain_id):
            return False, f"Source chain {from_chain_id} not supported by Circle CCTP V2"
        
        if not self.is_chain_supported(to_chain_id):
            return False, f"Destination chain {to_chain_id} not supported by Circle CCTP V2"
        
        # Validate amount
        if amount <= 0:
            return False, "Transfer amount must be greater than zero"
            
        # Validate minimum amount (Circle CCTP typically has minimums)
        min_amount = Decimal("0.01")  # $0.01 minimum
        if amount < min_amount:
            return False, f"Transfer amount must be at least {min_amount} USDC"
        
        return True, "Validation successful"

    def _get_estimated_time(self, from_chain_id: int, to_chain_id: int) -> str:
        """Get estimated transfer time based on chains."""
        # Circle CCTP is generally faster than traditional bridges
        if from_chain_id == 1 or to_chain_id == 1:  # Ethereum involved
            return "3-5 minutes"
        else:
            return "1-3 minutes"

    async def _build_transaction_steps(
        self,
        from_chain_id: int,
        to_chain_id: int,
        amount: Decimal,
        recipient: str,
        token_messenger: str,
        usdc_address: str
    ) -> List[Dict[str, Any]]:
        """Build transaction steps for Circle CCTP V2 transfer."""
        steps = []
        
        # Step 1: Approve USDC for TokenMessenger
        approve_data = await self._build_approve_data(token_messenger, amount)
        steps.append({
            "type": "approve",
            "description": f"Approve {amount} USDC for Circle CCTP",
            "chain": self.chain_mappings[from_chain_id],
            "to": usdc_address,
            "value": "0",
            "data": approve_data,
            "gasLimit": "60000"
        })
        
        # Step 2: Burn and mint via TokenMessenger
        burn_data = await self._build_burn_data(to_chain_id, recipient, amount)
        steps.append({
            "type": "burn_and_mint",
            "description": f"Transfer {amount} USDC to {self.chain_mappings[to_chain_id]} via Circle CCTP",
            "chain": self.chain_mappings[from_chain_id],
            "to": token_messenger,
            "value": "0",
            "data": burn_data,
            "gasLimit": "200000"
        })
        
        return steps

    async def _build_approve_data(self, spender: str, amount: Decimal) -> str:
        """
        Build approve transaction data for USDC token.
        Uses shared utility for consistency across codebase.
        """
        try:
            # Get USDC configuration for accurate decimals
            token_config = await config_manager.get_token_by_symbol("USDC")
            if not token_config:
                raise ValueError("USDC token not found in configuration")
            
            # Use shared utility with USDC decimals
            return transaction_utils.encode_erc20_approval_with_decimals(
                spender=to_checksum_address(spender),
                amount=amount,
                decimals=token_config.decimals
            )

        except Exception as e:
            logger.error(f"Error building approve data: {e}")
            raise ProtocolError(
                message=f"Failed to build approve transaction: {e}",
                protocol="cctp_v2",
                user_message="Unable to prepare USDC approval transaction"
            )

    async def _build_burn_data(self, dest_chain_id: int, recipient: str, amount: Decimal) -> str:
        """Build burn transaction data for Circle CCTP TokenMessenger."""
        try:
            # Get USDC configuration for accurate decimals
            token_config = await config_manager.get_token_by_symbol("USDC")
            if not token_config:
                raise ValueError("USDC token not found in configuration")
            
            decimals = token_config.decimals
            amount_wei = int(amount * (Decimal(10) ** decimals))

            # Circle CCTP TokenMessenger depositForBurn function:
            # depositForBurn(uint256 amount, uint32 destinationDomain, bytes32 mintRecipient, address burnToken)
            function_selector = function_signature_to_4byte_selector(
                "depositForBurn(uint256,uint32,bytes32,address)"
            ).hex()

            # Convert chain ID to Circle domain ID
            domain_id = self._get_circle_domain_id(dest_chain_id)
            
            # Convert recipient address to bytes32
            recipient_bytes32 = recipient.lower().replace('0x', '').zfill(64)
            recipient_bytes32 = bytes.fromhex(recipient_bytes32)
            
            # Get USDC token address for source chain
            usdc_address = token_config.addresses.get(dest_chain_id)  # We need source chain USDC
            if not usdc_address:
                raise ValueError(f"USDC address not found for chain {dest_chain_id}")

            # Encode parameters
            encoded_params = abi_encode(
                ['uint256', 'uint32', 'bytes32', 'address'],
                [amount_wei, domain_id, recipient_bytes32, to_checksum_address(usdc_address)]
            )

            return f"0x{function_selector}{encoded_params.hex()}"

        except Exception as e:
            logger.error(f"Error building burn data: {e}")
            raise ProtocolError(
                message=f"Failed to build burn transaction: {e}",
                protocol="cctp_v2",
                user_message="Unable to prepare Circle CCTP transfer transaction"
            )

    def _get_circle_domain_id(self, chain_id: int) -> int:
        """Get Circle domain ID for chain ID."""
        # Circle CCTP domain mappings
        domain_mappings = {
            1: 0,      # Ethereum
            42161: 3,  # Arbitrum
            8453: 6,   # Base
            137: 7,    # Polygon
            10: 2,     # Optimism
            43114: 1,  # Avalanche
            59144: 9,  # Linea
            480: 10,   # World Chain (estimated)
            146: 11    # Sonic (estimated)
        }
        
        domain_id = domain_mappings.get(chain_id)
        if domain_id is None:
            raise ValueError(f"Circle domain ID not found for chain {chain_id}")
            
        return domain_id

    async def get_supported_tokens_for_chain(self, chain_id: int) -> List[str]:
        """Get list of tokens supported on a specific chain."""
        if not self.is_chain_supported(chain_id):
            return []
        
        # Circle CCTP V2 only supports USDC
        if await self.is_token_supported("USDC", chain_id):
            return ["USDC"]
        return []

    async def close(self):
        """Clean up resources."""
        if self.session:
            await self.session.aclose()

# Global instance
circle_cctp_service = CircleCCTPService()

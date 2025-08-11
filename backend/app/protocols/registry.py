"""
Protocol registry for managing multiple swap protocols.
"""
from typing import Dict, List, Optional, Any
import logging
from app.models.token import TokenInfo, token_registry
from app.services.token_service import token_service
from .brian_adapter import BrianAdapter
from .zerox_adapter import ZeroXAdapter
from .axelar_adapter import AxelarAdapter
from .uniswap_adapter import UniswapAdapter

logger = logging.getLogger(__name__)

class ProtocolRegistry:
    """Registry for managing multiple swap protocols."""

    def __init__(self):
        """Initialize available protocols."""
        self.protocols: Dict[str, Any] = {}
        self._initialize_protocols()

    async def close(self):
        """Close all protocol clients."""
        for protocol in self.protocols.values():
            if hasattr(protocol, 'close'):
                await protocol.close()

    def _initialize_protocols(self):
        """Initialize supported protocols."""
        try:
            self.protocols["axelar"] = AxelarAdapter()
            logger.info("Initialized Axelar protocol adapter")
        except Exception as e:
            logger.error(f"Failed to initialize Axelar protocol adapter: {e}")

        try:
            self.protocols["0x"] = ZeroXAdapter()
            logger.info("Initialized 0x protocol adapter")
        except Exception as e:
            logger.error(f"Failed to initialize 0x protocol adapter: {e}")

        try:
            self.protocols["brian"] = BrianAdapter()
            logger.info("Initialized Brian protocol adapter")
        except Exception as e:
            logger.error(f"Failed to initialize Brian protocol adapter: {e}")

        try:
            self.protocols["uniswap"] = UniswapAdapter()
            logger.info("Initialized Uniswap protocol adapter")
        except Exception as e:
            logger.error(f"Failed to initialize Uniswap protocol adapter: {e}")

    def get_protocol(self, protocol_id: str) -> Optional[Any]:
        """Get a specific protocol by ID."""
        return self.protocols.get(protocol_id)

    def get_supported_protocols(self, chain_id: int) -> List[Any]:
        """Get list of protocols that support the given chain."""
        return [
            protocol for protocol in self.protocols.values()
            if protocol.is_supported(chain_id)
        ]

    def get_preferred_protocol(self, chain_id: int, is_cross_chain: bool = False) -> Optional[Any]:
        """Get the preferred protocol for a given chain."""
        # For cross-chain operations, prefer Axelar
        if is_cross_chain:
            axelar = self.get_protocol("axelar")
            if axelar and axelar.is_supported(chain_id):
                return axelar

        # For same-chain operations, prefer Brian if available
        brian = self.get_protocol("brian")
        if brian and brian.is_supported(chain_id):
            return brian

        # Fall back to 0x for other chains
        zerox = self.get_protocol("0x")
        if zerox and zerox.is_supported(chain_id):
            return zerox

        # No supported protocols
        return None

    def get_cross_chain_protocol(self, from_chain_id: int, to_chain_id: int) -> Optional[Any]:
        """Get the best protocol for cross-chain operations."""
        # Axelar is designed for cross-chain
        axelar = self.get_protocol("axelar")
        if axelar and axelar.is_supported(from_chain_id) and axelar.is_supported(to_chain_id):
            return axelar
        
        # No cross-chain protocols available
        return None

    async def resolve_token(self, chain_id: int, token_identifier: str) -> Optional[TokenInfo]:
        """
        Resolve token identifier to token info with fallback to token service.

        Args:
            chain_id: Chain ID
            token_identifier: Token identifier (symbol, address, etc.)

        Returns:
            TokenInfo if found, None otherwise
        """
        # First try manual registry for common tokens (fast path)
        token = token_registry.get_token(token_identifier)
        if token and token.is_supported_on_chain(chain_id):
            return token

        # If it looks like an address, try by address in registry
        if token_identifier.startswith("0x") and len(token_identifier) >= 40:
            token = token_registry.get_token_by_address(chain_id, token_identifier)
            if token:
                return token

        # Fallback to scalable token service
        try:
            token_info = await token_service.get_token_info(chain_id, token_identifier)
            if token_info:
                # Convert token service response to TokenInfo for compatibility
                return TokenInfo(
                    id=token_identifier.lower(),
                    name=token_info.get("name", token_identifier.upper()),
                    symbol=token_info.get("symbol", token_identifier.upper()),
                    decimals=token_info.get("metadata", {}).get("decimals", 18),
                    type="erc20" if token_info.get("address") else "native",
                    verified=token_info.get("metadata", {}).get("verified", False),
                    addresses={chain_id: token_info.get("address", "")} if token_info.get("address") else {}
                )
        except Exception as e:
            logger.warning(f"Token service lookup failed for {token_identifier}: {e}")

        # Not found
        return None

    async def get_quote(
        self,
        from_token: str,
        to_token: str,
        amount: str,
        from_chain: int,
        to_chain: int,
        user_address: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get quote from the best available protocol.
        
        Args:
            from_token: Source token symbol
            to_token: Destination token symbol
            amount: Amount to swap
            from_chain: Source chain ID
            to_chain: Destination chain ID
            user_address: User wallet address
            
        Returns:
            Quote response with success flag and protocol info
        """
        # Determine if this is cross-chain
        is_cross_chain = from_chain != to_chain
        
        # Get protocols in priority order
        protocols_to_try = []
        
        if is_cross_chain:
            # For cross-chain, prioritize Axelar
            axelar = self.get_protocol("axelar")
            if axelar and axelar.is_supported(from_chain) and axelar.is_supported(to_chain):
                protocols_to_try.append(("axelar", axelar))
        else:
            # For same-chain, try 0x first (best rates), then Uniswap (reliable), then Brian
            zerox = self.get_protocol("0x")
            if zerox and zerox.is_supported(from_chain):
                protocols_to_try.append(("0x", zerox))

            uniswap = self.get_protocol("uniswap")
            if uniswap and uniswap.is_supported(from_chain):
                protocols_to_try.append(("uniswap", uniswap))

            brian = self.get_protocol("brian")
            if brian and brian.is_supported(from_chain):
                protocols_to_try.append(("brian", brian))
        
        # Try each protocol in order
        for protocol_name, protocol in protocols_to_try:
            try:
                logger.info(f"Trying {protocol_name} protocol for quote")
                
                # Resolve tokens
                from_token_info = await self.resolve_token(from_chain, from_token)
                to_token_info = await self.resolve_token(to_chain, to_token)
                
                if not from_token_info or not to_token_info:
                    logger.warning(f"Could not resolve tokens for {protocol_name}: {from_token} -> {to_token}")
                    continue
                
                # Get quote from protocol
                from decimal import Decimal
                quote = await protocol.get_quote(
                    from_token=from_token_info,
                    to_token=to_token_info,
                    amount=Decimal(amount),
                    chain_id=from_chain,
                    wallet_address=user_address,
                    to_chain_id=to_chain if is_cross_chain else None
                )
                
                if quote and quote.get("success", False):
                    # Add protocol info to quote
                    quote["protocol"] = protocol_name
                    logger.info(f"Successfully got quote from {protocol_name}")

                    # Build transaction if protocol supports it
                    if hasattr(protocol, 'build_transaction'):
                        try:
                            transaction = await protocol.build_transaction(quote, from_chain)
                            if transaction and not transaction.get("error"):
                                quote["transaction"] = transaction
                                logger.info(f"Successfully built transaction for {protocol_name}")
                            else:
                                logger.warning(f"Failed to build transaction for {protocol_name}: {transaction}")
                        except Exception as e:
                            logger.error(f"Error building transaction for {protocol_name}: {e}")

                    return quote
                else:
                    logger.warning(f"{protocol_name} returned unsuccessful quote: {quote}")
                    
            except Exception as e:
                logger.error(f"Error getting quote from {protocol_name}: {e}")
                continue
        
        # No protocols succeeded
        logger.error("No protocols could provide a quote")
        return {
            "success": False,
            "error": "No supported protocols available for this swap",
            "protocol": "none"
        }


# Global instance
protocol_registry = ProtocolRegistry()
"""
Uniswap V3 protocol adapter for same-chain swaps.
"""
import logging
from typing import Dict, Any, List
from decimal import Decimal
import httpx

from app.models.token import TokenInfo

logger = logging.getLogger(__name__)

class UniswapAdapter:
    """Uniswap V3 protocol adapter."""
    
    # Uniswap V3 Router addresses by chain
    ROUTER_ADDRESSES = {
        1: "0xE592427A0AEce92De3Edee1F18E0157C05861564",      # Ethereum
        8453: "0x2626664c2603336E57B271c5C0b26F421741e481",    # Base
        42161: "0xE592427A0AEce92De3Edee1F18E0157C05861564",   # Arbitrum
        10: "0xE592427A0AEce92De3Edee1F18E0157C05861564",      # Optimism
        137: "0xE592427A0AEce92De3Edee1F18E0157C05861564",     # Polygon
    }
    
    # Common token addresses by chain
    TOKEN_ADDRESSES = {
        8453: {  # Base
            "USDC": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
            "WETH": "0x4200000000000000000000000000000000000006",
            "ETH": "0x4200000000000000000000000000000000000006",  # Same as WETH
            "DAI": "0x50c5725949A6F0c72E6C4a641F24049A917DB0Cb",
            "USDT": "0xfde4C96c8593536E31F229EA8f37b2ADa2699bb2",
        }
    }

    def __init__(self):
        """Initialize the Uniswap protocol adapter."""
        self.http_client = None

    @property
    def protocol_id(self) -> str:
        return "uniswap"

    @property
    def name(self) -> str:
        return "Uniswap V3"

    @property
    def supported_chains(self) -> List[int]:
        """List of supported chain IDs."""
        return list(self.ROUTER_ADDRESSES.keys())

    def is_supported(self, chain_id: int) -> bool:
        """Check if this protocol supports the given chain."""
        return chain_id in self.supported_chains

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self.http_client is None or self.http_client.is_closed:
            self.http_client = httpx.AsyncClient(timeout=30.0)
        return self.http_client

    async def close(self):
        """Close HTTP client."""
        if self.http_client and not self.http_client.is_closed:
            await self.http_client.aclose()

    def _get_token_address(self, token_symbol: str, chain_id: int) -> str:
        """Get token address for a given symbol and chain."""
        chain_tokens = self.TOKEN_ADDRESSES.get(chain_id, {})
        return chain_tokens.get(token_symbol.upper(), "")

    async def get_quote(
        self,
        from_token: TokenInfo,
        to_token: TokenInfo,
        amount: Decimal,
        chain_id: int,
        wallet_address: str,
        to_chain_id: int = None,
    ) -> Dict[str, Any]:
        """Get swap quote from Uniswap V3."""
        try:
            if not self.is_supported(chain_id):
                raise ValueError(f"Chain {chain_id} not supported by Uniswap adapter")

            # Uniswap only supports same-chain swaps
            if to_chain_id is not None and to_chain_id != chain_id:
                raise ValueError("Uniswap only supports same-chain swaps")

            # Get token addresses
            from_address = self._get_token_address(from_token.symbol, chain_id)
            to_address = self._get_token_address(to_token.symbol, chain_id)

            if not from_address or not to_address:
                raise ValueError(f"Token addresses not found for {from_token.symbol} or {to_token.symbol} on chain {chain_id}")

            # Convert amount to wei (assuming 6 decimals for USDC, 18 for others)
            decimals = 6 if from_token.symbol.upper() == "USDC" else 18
            amount_wei = int(amount * (10 ** decimals))

            # For now, return a mock quote since we don't have a price oracle
            # In production, you'd query Uniswap's quoter contract or use a price API
            estimated_output = amount * Decimal("0.95")  # Mock 5% slippage
            output_decimals = 6 if to_token.symbol.upper() == "USDC" else 18
            amount_out_wei = int(estimated_output * (10 ** output_decimals))

            return {
                "success": True,
                "from_token": from_token.symbol,
                "to_token": to_token.symbol,
                "from_amount": str(amount),
                "to_amount": str(estimated_output),
                "from_address": from_address,
                "to_address": to_address,
                "amount_in_wei": str(amount_wei),
                "amount_out_wei": str(amount_out_wei),
                "router_address": self.ROUTER_ADDRESSES[chain_id],
                "estimated_gas": "200000",
                "protocol": "uniswap",
                "chain_id": chain_id
            }

        except Exception as e:
            logger.exception(f"Error getting Uniswap quote: {e}")
            return {
                "success": False,
                "error": f"Failed to get Uniswap quote: {str(e)}",
                "protocol": "uniswap"
            }

    async def build_transaction(
        self,
        quote: Dict[str, Any],
        chain_id: int,
    ) -> Dict[str, Any]:
        """Build transaction from Uniswap quote."""
        try:
            if not quote.get("success", False):
                raise ValueError("Invalid quote")

            # Build a proper Uniswap V3 exactInputSingle transaction
            # Function selector for exactInputSingle(ExactInputSingleParams)
            function_selector = "0x414bf389"

            # Encode the parameters for exactInputSingle
            # struct ExactInputSingleParams {
            #     address tokenIn;
            #     address tokenOut;
            #     uint24 fee;
            #     address recipient;
            #     uint256 deadline;
            #     uint256 amountIn;
            #     uint256 amountOutMinimum;
            #     uint160 sqrtPriceLimitX96;
            # }

            # Use 3000 (0.3%) fee tier which is most common
            fee = "0bb8"  # 3000 in hex

            # Set deadline to 20 minutes from now (in seconds)
            import time
            deadline = hex(int(time.time()) + 1200)[2:].zfill(64)

            # Encode the transaction data (simplified)
            token_in = quote['from_address'][2:].zfill(64)
            token_out = quote['to_address'][2:].zfill(64)
            fee_hex = fee.zfill(64)
            recipient = "55A5705453Ee82c742274154136Fce8149597058".zfill(64)  # wallet address
            amount_in = hex(int(quote['amount_in_wei']))[2:].zfill(64)
            amount_out_min = hex(int(int(quote['amount_out_wei']) * 0.95))[2:].zfill(64)  # 5% slippage
            sqrt_price_limit = "0".zfill(64)  # No price limit

            transaction_data = (
                function_selector +
                token_in +
                token_out +
                fee_hex +
                recipient +
                deadline +
                amount_in +
                amount_out_min +
                sqrt_price_limit
            )

            return {
                "to": quote["router_address"],
                "data": transaction_data,
                "value": "0",
                "gasLimit": quote.get("estimated_gas", "200000"),
                "chainId": chain_id
            }

        except Exception as e:
            logger.exception(f"Error building Uniswap transaction: {e}")
            return {
                "error": f"Failed to build transaction: {str(e)}",
                "technical_details": str(e)
            }

# Create instance
uniswap_adapter = UniswapAdapter()

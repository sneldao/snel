from typing import Dict, Any, Optional, Tuple, List, Union
import logging
from app.agents.swap_agent import SwapAgent
from app.services.token_service import TokenService
from app.models.commands import SwapCommand
from app.config.chains import is_native_token, get_native_token_address
from eth_utils import is_address
import os
import httpx
import json

# Import Kyber implementation
from src.dowse.tools.best_route.kyber import (
    get_quote as get_kyber_quote,
    Quote as KyberQuote,
    KyberSwapError,
    NoRouteFoundError as KyberNoRouteFoundError,
    InsufficientLiquidityError as KyberInsufficientLiquidityError,
    InvalidTokenError as KyberInvalidTokenError,
    BuildTransactionError as KyberBuildTransactionError
)
from src.dowse.tools.best_route.kyber import get_chain_from_chain_id as get_kyber_chain_name

# Import Uniswap implementation
from src.dowse.tools.best_route.uniswap import (
    get_quote as get_uniswap_quote,
    Quote as UniswapQuote,
    UniswapError,
    NoRouteFoundError as UniswapNoRouteFoundError,
    InsufficientLiquidityError as UniswapInsufficientLiquidityError,
    InvalidTokenError as UniswapInvalidTokenError,
    BuildTransactionError as UniswapBuildTransactionError
)
from src.dowse.tools.best_route.uniswap import get_router_address as get_uniswap_router_address

# Define TransferFromFailedError since it's not in the Dowse implementation
class TransferFromFailedError(Exception):
    """Raised when the token transfer fails, likely due to insufficient balance or allowance"""
    pass

# Define generic error classes for the get_quote function
class NoRouteFoundError(Exception):
    """Raised when no swap route is found across all aggregators"""
    pass

class InsufficientLiquidityError(Exception):
    """Raised when there's insufficient liquidity for the swap across all aggregators"""
    pass

class InvalidTokenError(Exception):
    """Raised when token is not supported or invalid across all aggregators"""
    pass

# Define router addresses by chain for Kyber
KYBER_ROUTER_ADDRESSES = {
    1: "0x6131B5fae19EA4f9D964eAc0408E4408b66337b5",  # Ethereum
    137: "0x6131B5fae19EA4f9D964eAc0408E4408b66337b5",  # Polygon
    42161: "0x6131B5fae19EA4f9D964eAc0408E4408b66337b5",  # Arbitrum
    10: "0x6131B5fae19EA4f9D964eAc0408E4408b66337b5",  # Optimism
    8453: "0x6131B5fae19EA4f9D964eAc0408E4408b66337b5",  # Base
    534352: "0x6131B5fae19EA4f9D964eAc0408E4408b66337b5",  # Scroll
}

def get_router_address(chain_id: int, aggregator: str = "kyber") -> Optional[str]:
    """Get the router address for a specific chain and aggregator."""
    if aggregator.lower() == "uniswap":
        return get_uniswap_router_address(chain_id)
    else:
        return KYBER_ROUTER_ADDRESSES.get(chain_id)

# Import the transaction executor
from app.services.transaction_executor import transaction_executor

logger = logging.getLogger(__name__)

# Token decimals mapping
TOKEN_DECIMALS = {
    "ETH": 18,
    "WETH": 18,
    "USDC": 6,
    "USDT": 6,
    "DAI": 18,
    "NURI": 18,
}

class SwapService:
    """Service for handling all swap operations."""
    
    def __init__(self, token_service: TokenService, swap_agent: SwapAgent):
        """
        Initialize the swap service.
        
        Args:
            token_service: Service for token lookups
            swap_agent: Agent for parsing swap commands
        """
        self.token_service = token_service
        self.swap_agent = swap_agent
    
    async def process_swap_command(self, command: str, chain_id: int, wallet_address: str, skip_approval: bool = False) -> Dict[str, Any]:
        """
        Process a swap command and return transaction data.
        
        Args:
            command: The swap command
            chain_id: Chain ID
            wallet_address: Wallet address
            skip_approval: Whether to skip the approval check
            
        Returns:
            Transaction data
            
        Raises:
            NoRouteFoundError: If no route is found
            InsufficientLiquidityError: If there's insufficient liquidity
            InvalidTokenError: If a token is invalid
            TransferFromFailedError: If token transfer fails
            ValueError: For other errors
        """
        logger.info(f"Processing swap command: {command}")
        
        # Check if this is an approved command (after token approval)
        if command.startswith("approved:"):
            # Extract the original command
            original_command = command.replace("approved:", "").strip()
            logger.info(f"Processing approved command. Original command: {original_command}")
            
            # Parse the original command
            swap_command = await self.parse_swap_command(original_command, chain_id)
            
            if not swap_command:
                logger.error(f"Failed to parse approved command: {original_command}")
                raise ValueError("Failed to parse swap command")
        else:
            # Parse the swap command
            swap_command = await self.parse_swap_command(command, chain_id)
            
            if not swap_command:
                logger.error(f"Failed to parse swap command: {command}")
                raise ValueError("Failed to parse swap command")
        
        # Log the parsed swap command
        logger.info(f"Parsed swap command: {swap_command}")
        
        # Build the swap transaction
        try:
            tx_data = await self.build_swap_transaction(
                swap_command=swap_command,
                wallet_address=wallet_address,
                chain_id=chain_id,
                skip_approval=skip_approval
            )
            
            # If successful, return the transaction data
            return tx_data
        except NoRouteFoundError as e:
            logger.error(f"No route found: {e}")
            raise  # Re-raise the same error
        except InsufficientLiquidityError as e:
            logger.error(f"Insufficient liquidity: {e}")
            raise  # Re-raise the same error
        except InvalidTokenError as e:
            logger.error(f"Invalid token: {e}")
            raise  # Re-raise the same error
        except TransferFromFailedError as e:
            logger.error(f"Transfer failed: {e}")
            raise  # Re-raise the same error
        except Exception as e:
            logger.exception(f"Error building swap transaction: {e}")
            raise ValueError(f"Failed to build swap transaction: {str(e)}")
    
    async def build_swap_transaction(
        self,
        swap_command: SwapCommand,
        wallet_address: str,
        chain_id: int,
        skip_approval: bool = False
    ) -> Dict[str, Any]:
        """
        Build a swap transaction based on the swap command.
        
        Args:
            swap_command: The parsed swap command
            wallet_address: Wallet address
            chain_id: Chain ID
            skip_approval: Whether to skip the approval check
            
        Returns:
            Transaction data
            
        Raises:
            NoRouteFoundError: If no route is found
            InsufficientLiquidityError: If there's insufficient liquidity
            InvalidTokenError: If a token is invalid
            ValueError: For other errors
        """
        logger.info(f"Building swap transaction for {swap_command.amount_in} {swap_command.token_in} to {swap_command.token_out} on chain {chain_id}")
        
        try:
            # Get token addresses
            from_token_info = await self.token_service.lookup_token(swap_command.token_in, chain_id)
            to_token_info = await self.token_service.lookup_token(swap_command.token_out, chain_id)
            
            from_token_address = from_token_info[0]
            to_token_address = to_token_info[0]
            
            if not from_token_address:
                logger.error(f"Could not find token: {swap_command.token_in} on chain {chain_id}")
                raise InvalidTokenError(f"Token {swap_command.token_in} not found on chain {chain_id}")
                
            if not to_token_address:
                logger.error(f"Could not find token: {swap_command.token_out} on chain {chain_id}")
                raise InvalidTokenError(f"Token {swap_command.token_out} not found on chain {chain_id}")
                
            logger.info(f"Resolved tokens: {swap_command.token_in} -> {from_token_address}, {swap_command.token_out} -> {to_token_address}")
            
            # Get token price to convert from human-readable amount to token units
            price_data, decimals = await self.get_token_price(swap_command.token_in, chain_id)
            if decimals is None:
                # If we can't get the price, use a default of 18 decimals
                decimals = 18
                logger.warning(f"Could not get decimals for {swap_command.token_in}, using default of 18")
            
            # Calculate the amount in token units
            amount_in_units = int(float(swap_command.amount_in) * (10 ** decimals))
            logger.info(f"Calculated amount in units: {swap_command.amount_in} {swap_command.token_in} = {amount_in_units} units (decimals: {decimals})")
            
            # Get the preferred aggregator from the command or use the default
            preferred_aggregator = "0x"  # Changed default from uniswap to 0x
            if hasattr(swap_command, "aggregator") and swap_command.aggregator:
                preferred_aggregator = swap_command.aggregator
            
            # Get the swap quote
            try:
                quote, aggregator = await self.get_quote(
                    token_in=from_token_address,
                    token_out=to_token_address,
                    amount=float(swap_command.amount_in),
                    chain_id=chain_id,
                    recipient=wallet_address,
                    slippage_percentage=swap_command.slippage if hasattr(swap_command, "slippage") and swap_command.slippage else 1.0,
                    preferred_aggregator=preferred_aggregator
                )
                
                logger.info(f"Got quote from {aggregator} aggregator")
                
            except NoRouteFoundError as e:
                logger.error(f"No route found: {e}")
                raise
            except InsufficientLiquidityError as e:
                logger.error(f"Insufficient liquidity: {e}")
                raise
            except Exception as e:
                logger.exception(f"Error getting swap quote: {e}")
                raise ValueError(f"Failed to get swap quote: {str(e)}")
            
            # Check if token needs approval
            needs_approval = False
            token_to_approve = None
            spender = None
            
            if not skip_approval and from_token_address.lower() != "0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee":
                # Only ERC20 tokens need approval (not native ETH)
                needs_approval = True
                token_to_approve = from_token_address
                spender = quote.router_address
                logger.info(f"Token {from_token_address} needs approval for spender {spender}")
            
            # Prepare transaction data for the frontend
            tx_data = {
                "to": quote.router_address,
                "data": quote.data,
                "value": quote.transaction_value if hasattr(quote, 'transaction_value') else "0",
                "chain_id": chain_id,
                "method": "swap",
                "gas_limit": str(quote.gas) if hasattr(quote, 'gas') and quote.gas else "350000",  # Default gas limit
                "needs_approval": needs_approval,
                "token_to_approve": token_to_approve,
                "spender": spender,
                "from_token_address": from_token_address,
                "to_token_address": to_token_address,
                "amount_in": swap_command.amount_in,
                "amount_in_units": str(amount_in_units),
                "token_in": swap_command.token_in,
                "token_out": swap_command.token_out,
                "pending_command": f"swap {swap_command.amount_in} {swap_command.token_in} for {swap_command.token_out}",
                "aggregator": aggregator,
                "metadata": {
                    "decimals": decimals,
                    "price": price_data
                }
            }
            
            logger.info(f"Built transaction: to={tx_data['to']}, value={tx_data['value']}, gas_limit={tx_data['gas_limit']}")
            return tx_data
                
        except NoRouteFoundError:
            raise  # Re-raise specific errors
        except InsufficientLiquidityError:
            raise
        except InvalidTokenError:
            raise
        except Exception as e:
            logger.exception(f"Error building swap transaction: {e}")
            raise ValueError(f"Failed to build swap transaction: {str(e)}")
    
    async def parse_swap_command(self, command: str, chain_id: Optional[int] = None) -> Optional[SwapCommand]:
        """
        Parse a swap command string into a SwapCommand object.
        
        Args:
            command: The swap command to parse
            chain_id: The chain ID for token lookups
            
        Returns:
            A SwapCommand object or None if parsing fails
        """
        try:
            # Use the swap agent to parse the command
            result = await self.swap_agent.process_swap(command, chain_id)
            
            if result.get("error"):
                logger.error(f"Error parsing swap command: {result['error']}")
                return None
            
            # Extract swap details from the metadata
            metadata = result.get("metadata", {})
            swap_details = metadata.get("swap_details", {})
            
            if not swap_details:
                logger.error("No swap details found in agent response")
                return None
            
            # Create a SwapCommand object
            return SwapCommand(
                action="swap",
                amount=swap_details.get("amount", 0),
                token_in=swap_details.get("token_in", ""),
                token_out=swap_details.get("token_out", ""),
                is_target_amount=swap_details.get("is_target_amount", False),
                amount_is_usd=swap_details.get("amount_is_usd", False),
                natural_command=swap_details.get("natural_command", command)
            )
            
        except Exception as e:
            logger.error(f"Failed to parse swap command: {e}")
            return None
    
    async def get_token_price(
        self, 
        token_symbol: str, 
        chain_id: int = 1
    ) -> Tuple[Optional[float], Optional[int]]:
        """
        Get the price of a token in USD.
        
        Args:
            token_symbol: The token symbol
            chain_id: The chain ID
            
        Returns:
            Tuple of (price_per_token, token_decimals) or (None, None) if not found
        """
        try:
            # For testing, return mock prices
            mock_prices = {
                "ETH": 3000.0,
                "WETH": 3000.0,
                "USDC": 1.0,
                "USDT": 1.0,
                "DAI": 1.0,
            }
            
            token_symbol_upper = token_symbol.upper()
            if token_symbol_upper in mock_prices:
                return mock_prices[token_symbol_upper], TOKEN_DECIMALS.get(token_symbol_upper, 18)
            
            # In a real implementation, you would call a price API here
            return None, None
            
        except Exception as e:
            logger.error(f"Error getting token price: {e}")
            return None, None
    
    async def execute_swap(
        self,
        swap_command: SwapCommand,
        wallet_address: str,
        chain_id: int,
        private_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute a swap transaction.
        
        Args:
            swap_command: The swap command
            wallet_address: The wallet address
            chain_id: The chain ID
            private_key: Optional private key for signing
            
        Returns:
            Dictionary with transaction result
        """
        try:
            # Build the swap transaction
            tx_data = await self.build_swap_transaction(
                swap_command=swap_command,
                wallet_address=wallet_address,
                chain_id=chain_id
            )
            
            # Check for errors
            if "error" in tx_data:
                return tx_data
            
            # Check if approval is needed
            if tx_data.get("method") == "approve":
                return {
                    **tx_data,
                    "message": "Token approval required before swap"
                }
            
            # Execute the transaction
            tx_hash = await transaction_executor.execute_transaction(
                wallet_address=wallet_address,
                tx_data=tx_data,
                chain_id=chain_id,
                private_key=private_key
            )
            
            return {
                "tx_hash": tx_hash,
                "success": True,
                "message": f"Swap transaction sent: {tx_hash}",
                "metadata": tx_data.get("metadata", {})
            }
            
        except Exception as e:
            logger.error(f"Error executing swap: {e}")
            return {
                "error": f"Failed to execute swap: {str(e)}",
                "success": False
            }
    
    async def get_0x_quote(
        self,
        token_in: str,
        token_out: str,
        amount: int,
        chain_id: int,
        wallet_address: str
    ) -> Dict[str, Any]:
        """
        Get a quote from the 0x API.
        
        Args:
            token_in: Input token address
            token_out: Output token address
            amount: Amount in smallest units
            chain_id: Chain ID
            wallet_address: Wallet address
            
        Returns:
            Quote data
            
        Raises:
            NoRouteFoundError: If no route is found
            InsufficientLiquidityError: If there's insufficient liquidity
            InvalidTokenError: If a token is invalid
            Exception: For other errors
        """
        logger.info(f"Getting 0x quote for {token_in} -> {token_out} on chain {chain_id}")
        
        # Map chain ID to 0x API chain name
        chain_mapping = {
            1: "ethereum",
            10: "optimism",
            56: "bsc",
            137: "polygon",
            42161: "arbitrum",
            8453: "base",
            534352: "scroll"
        }
        
        if chain_id not in chain_mapping:
            logger.error(f"Chain {chain_id} not supported by 0x API")
            raise NoRouteFoundError(f"Chain {chain_id} not supported by 0x API")
        
        chain_name = chain_mapping[chain_id]
        
        # Prepare API URL
        api_url = f"https://api.0x.org/swap/v1/quote"
        if chain_id != 1:
            api_url = f"https://api.0x.org/{chain_name}/swap/v1/quote"
        
        # Prepare query parameters
        params = {
            "sellToken": token_in,
            "buyToken": token_out,
            "sellAmount": str(amount),
            "takerAddress": wallet_address,
            "slippagePercentage": "0.01",  # 1% slippage
            "skipValidation": "true"
        }
        
        # Add API key if available
        api_key = os.environ.get("ZEROX_API_KEY")
        headers = {}
        if api_key:
            headers["0x-api-key"] = api_key
        else:
            logger.warning("No 0x API key found. Rate limits may apply.")
        
        logger.info(f"Requesting 0x quote from {api_url} with params: {params}")
        
        try:
            # Make API request
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(api_url, params=params, headers=headers)
                
                logger.info(f"0x API response status: {response.status_code}")
                
                if response.status_code != 200:
                    error_text = response.text
                    logger.error(f"0x API error: {error_text}")
                    
                    # Parse specific error types
                    if "insufficient_asset_liquidity" in error_text.lower():
                        raise InsufficientLiquidityError("Insufficient liquidity for this swap")
                    elif "no_routes_found" in error_text.lower():
                        raise NoRouteFoundError("No routes found for this swap")
                    elif "validation_failed" in error_text.lower() or "invalid_token" in error_text.lower():
                        raise InvalidTokenError(f"Invalid token(s) in the swap request")
                    else:
                        raise Exception(f"0x API error: {error_text}")
                
                # Parse response
                quote_data = response.json()
                
                # Extract relevant data
                to = quote_data.get("to")
                data = quote_data.get("data")
                value = quote_data.get("value", "0")
                
                # Validate required fields
                if not to or not data:
                    raise Exception("0x quote missing required fields (to, data)")
                
                # Convert value to hex if it's not already
                if not isinstance(value, str) or not value.startswith("0x"):
                    value = f"0x{int(value):x}"
                
                # Get gas estimate
                gas_estimate = quote_data.get("estimatedGas", 300000)
                gas_limit = int(gas_estimate * 1.5)  # Add 50% buffer
                
                # Return quote data
                return {
                    "to": to,
                    "data": data,
                    "value": value,
                    "gas_limit": str(gas_limit),
                    "source": "0x",
                    "buy_amount": quote_data.get("buyAmount"),
                    "sell_amount": quote_data.get("sellAmount"),
                    "price": quote_data.get("price"),
                    "estimated_gas": gas_estimate
                }
        except (NoRouteFoundError, InsufficientLiquidityError, InvalidTokenError) as e:
            # Re-raise specific exceptions
            logger.error(f"0x quote error: {str(e)}")
            raise
        except Exception as e:
            logger.exception(f"Error getting 0x quote: {e}")
            raise Exception(f"Failed to get quote from 0x API: {str(e)}")

    async def get_quote(
        self,
        token_in: str,
        token_out: str,
        amount: float,
        chain_id: int,
        recipient: str,
        slippage_percentage: float = 1.0,
        is_exact_output: bool = False,
        preferred_aggregator: str = "0x"  # Changed default to 0x
    ) -> Tuple[Union[KyberQuote, UniswapQuote], str]:
        """
        Get a swap quote from the preferred aggregator, with fallback to other aggregators.
        
        Args:
            token_in: Address of the token to sell
            token_out: Address of the token to buy
            amount: Amount of token_in to sell (or token_out to buy if is_exact_output=True)
            chain_id: Chain ID
            recipient: Address that will receive the bought tokens
            slippage_percentage: Maximum acceptable slippage in percentage
            is_exact_output: If True, amount is the amount of token_out to buy
            preferred_aggregator: Preferred aggregator to use ("0x", "uniswap", or "kyber")
        
        Returns:
            Tuple of (Quote object with transaction details, aggregator name)
        """
        errors = []
        
        # Convert amount to smallest units for 0x
        # Use token_service to get token info including symbol and decimals
        token_in_info = await self.token_service.lookup_token(token_in, chain_id)
        token_in_symbol = token_in_info[1].upper() if len(token_in_info) > 1 and token_in_info[1] else ""
        
        # Default to 18 decimals for most tokens, but use known decimals if available
        token_in_decimals = 18  # Default
        if token_in_symbol and token_in_symbol in TOKEN_DECIMALS:
            token_in_decimals = TOKEN_DECIMALS[token_in_symbol]
        
        amount_in_smallest_units = int(amount * (10 ** token_in_decimals))
        logger.info(f"Converting {amount} {token_in_symbol} to {amount_in_smallest_units} units (decimals: {token_in_decimals})")
        
        # Try the preferred aggregator first
        if preferred_aggregator.lower() == "0x":
            try:
                logger.info(f"Getting quote from 0x for {amount} {token_in_symbol} to {token_out}")
                quote = await self.get_0x_quote(
                    token_in=token_in,
                    token_out=token_out,
                    amount=amount_in_smallest_units,
                    chain_id=chain_id,
                    wallet_address=recipient
                )
                logger.info(f"Got quote from 0x: {quote}")
                
                # Create a structure similar to other quote returns
                structured_quote = {
                    "to": quote["to"],
                    "data": quote["data"],
                    "value": quote["value"],
                    "gas_limit": str(quote["gas_limit"]),
                    "source": "0x",
                    "buy_amount": quote["buy_amount"],
                    "sell_amount": quote["sell_amount"],
                    "price": quote["price"]
                }
                return structured_quote, "0x"
            except Exception as e:
                error_msg = str(e)
                logger.warning(f"Failed to get quote from 0x: {error_msg}")
                errors.append(f"0x error: {error_msg}")
                
                # Fall back to Uniswap
                try:
                    logger.info(f"Falling back to Uniswap for {amount} {token_in_symbol} to {token_out}")
                    quote = await get_uniswap_quote(
                        token_in=token_in,
                        token_out=token_out,
                        amount=amount,
                        chain_id=chain_id,
                        recipient=recipient,
                        slippage_percentage=slippage_percentage,
                        is_exact_output=is_exact_output
                    )
                    logger.info(f"Got quote from Uniswap: {quote}")
                    return quote, "uniswap"
                except Exception as uniswap_e:
                    error_msg = str(uniswap_e)
                    logger.warning(f"Failed to get quote from Uniswap: {error_msg}")
                    errors.append(f"Uniswap error: {error_msg}")
                    
                    # Finally try Kyber
                    try:
                        logger.info(f"Trying Kyber as last resort for {amount} {token_in_symbol} to {token_out}")
                        quote = await get_kyber_quote(
                            token_in=token_in,
                            token_out=token_out,
                            amount=amount_in_smallest_units,
                            chain_id=chain_id,
                            recipient=recipient
                        )
                        logger.info(f"Got quote from Kyber: {quote}")
                        return quote, "kyber"
                    except Exception as kyber_e:
                        error_msg = str(kyber_e)
                        logger.error(f"Failed to get quote from Kyber: {error_msg}")
                        errors.append(f"Kyber error: {error_msg}")
        elif preferred_aggregator.lower() == "uniswap":
            try:
                logger.info(f"Getting quote from Uniswap for {amount} {token_in_symbol} to {token_out}")
                quote = await get_uniswap_quote(
                    token_in=token_in,
                    token_out=token_out,
                    amount=amount,
                    chain_id=chain_id,
                    recipient=recipient,
                    slippage_percentage=slippage_percentage,
                    is_exact_output=is_exact_output
                )
                logger.info(f"Got quote from Uniswap: {quote}")
                return quote, "uniswap"
            except Exception as e:
                error_msg = str(e)
                logger.warning(f"Failed to get quote from Uniswap: {error_msg}")
                errors.append(f"Uniswap error: {error_msg}")
                
                # Try 0x as fallback
                try:
                    logger.info(f"Falling back to 0x for {amount} {token_in_symbol} to {token_out}")
                    quote = await self.get_0x_quote(
                        token_in=token_in,
                        token_out=token_out,
                        amount=amount_in_smallest_units,
                        chain_id=chain_id,
                        wallet_address=recipient
                    )
                    logger.info(f"Got quote from 0x: {quote}")
                    structured_quote = {
                        "to": quote["to"],
                        "data": quote["data"],
                        "value": quote["value"],
                        "gas_limit": str(quote["gas_limit"]),
                        "source": "0x",
                        "buy_amount": quote["buy_amount"],
                        "sell_amount": quote["sell_amount"],
                        "price": quote["price"]
                    }
                    return structured_quote, "0x"
                except Exception as zerox_e:
                    error_msg = str(zerox_e)
                    logger.warning(f"Failed to get quote from 0x: {error_msg}")
                    errors.append(f"0x error: {error_msg}")
                
                # Fall back to Kyber
                try:
                    logger.info(f"Falling back to Kyber for {amount} {token_in_symbol} to {token_out}")
                    quote = await get_kyber_quote(
                        token_in=token_in,
                        token_out=token_out,
                        amount=amount_in_smallest_units,
                        chain_id=chain_id,
                        recipient=recipient
                    )
                    logger.info(f"Got quote from Kyber: {quote}")
                    return quote, "kyber"
                except Exception as kyber_e:
                    error_msg = str(kyber_e)
                    logger.error(f"Failed to get quote from Kyber: {error_msg}")
                    errors.append(f"Kyber error: {error_msg}")
        else:
            # Try Kyber first
            try:
                logger.info(f"Getting quote from Kyber for {amount} {token_in_symbol} to {token_out}")
                quote = await get_kyber_quote(
                    token_in=token_in,
                    token_out=token_out,
                    amount=amount_in_smallest_units,
                    chain_id=chain_id,
                    recipient=recipient
                )
                logger.info(f"Got quote from Kyber: {quote}")
                return quote, "kyber"
            except Exception as e:
                error_msg = str(e)
                logger.warning(f"Failed to get quote from Kyber: {error_msg}")
                errors.append(f"Kyber error: {error_msg}")
                
                # Try 0x as fallback
                try:
                    logger.info(f"Falling back to 0x for {amount} {token_in_symbol} to {token_out}")
                    quote = await self.get_0x_quote(
                        token_in=token_in,
                        token_out=token_out,
                        amount=amount_in_smallest_units,
                        chain_id=chain_id,
                        wallet_address=recipient
                    )
                    logger.info(f"Got quote from 0x: {quote}")
                    structured_quote = {
                        "to": quote["to"],
                        "data": quote["data"],
                        "value": quote["value"],
                        "gas_limit": str(quote["gas_limit"]),
                        "source": "0x",
                        "buy_amount": quote["buy_amount"],
                        "sell_amount": quote["sell_amount"],
                        "price": quote["price"]
                    }
                    return structured_quote, "0x"
                except Exception as zerox_e:
                    error_msg = str(zerox_e)
                    logger.warning(f"Failed to get quote from 0x: {error_msg}")
                    errors.append(f"0x error: {error_msg}")
                
                # Fall back to Uniswap
                try:
                    logger.info(f"Falling back to Uniswap for {amount} {token_in_symbol} to {token_out}")
                    quote = await get_uniswap_quote(
                        token_in=token_in,
                        token_out=token_out,
                        amount=amount,
                        chain_id=chain_id,
                        recipient=recipient,
                        slippage_percentage=slippage_percentage,
                        is_exact_output=is_exact_output
                    )
                    logger.info(f"Got quote from Uniswap: {quote}")
                    return quote, "uniswap"
                except Exception as uniswap_e:
                    error_msg = str(uniswap_e)
                    logger.error(f"Failed to get quote from Uniswap: {error_msg}")
                    errors.append(f"Uniswap error: {error_msg}")
        
        # If we get here, all aggregators failed
        error_message = "\n".join(errors)
        logger.error(f"All aggregators failed to provide a quote: {error_message}")
        
        # Raise a specific error based on the error messages
        if any("liquidity" in err.lower() for err in errors):
            raise InsufficientLiquidityError("Insufficient liquidity for this swap on all aggregators")
        elif any("route" in err.lower() for err in errors):
            raise NoRouteFoundError("No valid route found for this swap on all aggregators")
        elif any("invalid token" in err.lower() for err in errors):
            raise InvalidTokenError("Invalid token for this swap on all aggregators")
        else:
            raise ValueError(f"Failed to get quote from all aggregators: {error_message}") 
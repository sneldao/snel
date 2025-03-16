"""
Service for handling all swap operations.
"""
import contextlib
from typing import Dict, Any, Optional, Tuple, List, Union
import logging
from app.agents.simple_swap_agent import SimpleSwapAgent
from app.services.token_service import TokenService
from app.models.commands import SwapCommand
from app.config.chains import is_native_token, get_native_token_address
from eth_utils import is_address
import os
import httpx
import json
from decimal import Decimal
from app.providers.openai import OpenAIProvider
# Import the consolidated price_service
from app.services.prices import price_service
import time
import asyncio
# Import the new token conversion utility
from app.utils.token_conversion import amount_to_smallest_units, smallest_units_to_amount, format_token_amount

# Import aggregator services
from app.services.aggregators import (
    get_zerox_quote,
    get_openocean_quote,
    get_kyber_quote,
    get_router_address
)

# Import the transaction executor
from app.services.transaction_executor import TransactionExecutor, transaction_executor

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

# Add missing constants
ETH_ADDRESS = "0x0000000000000000000000000000000000000000"
WETH_ADDRESS = {
    1: "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",  # Mainnet
    10: "0x4200000000000000000000000000000000000006",  # Optimism
    137: "0x7ceB23fD6bC0adD59E62ac25578270cFf1b9f619",  # Polygon
    42161: "0x82aF49447D8a07e3bd95BD0d56f35241523fBab1",  # Arbitrum
    8453: "0x4200000000000000000000000000000000000006",  # Base
    534352: "0x5300000000000000000000000000000000000004",  # Scroll
}

class TransferFromFailedError(Exception):
    """Raised when the token transfer fails, likely due to insufficient balance or allowance"""
    pass

class NoRouteFoundError(Exception):
    """Raised when no swap route is found across all aggregators"""
    pass

class InsufficientLiquidityError(Exception):
    """Raised when there's insufficient liquidity for the swap across all aggregators"""
    pass

class InvalidTokenError(Exception):
    """Raised when token is not supported or invalid across all aggregators"""
    pass

class SwapService:
    """Service for handling all swap operations."""
    
    def __init__(self, token_service: TokenService, swap_agent: SimpleSwapAgent):
        """
        Initialize the swap service.
        
        Args:
            token_service: Service for token lookups
            swap_agent: Agent for parsing swap commands
        """
        self.token_service = token_service
        self.swap_agent = swap_agent
        self.zerox_api_key = os.getenv("ZEROX_API_KEY")
        self.http_client = httpx.AsyncClient(verify=True, timeout=10.0)
        self.tx_executor = TransactionExecutor()
    
    async def process_swap_command(
        self,
        command: str,
        chain_id: int,
        wallet_address: str,
        skip_approval: bool = False,
        selected_aggregator: Optional[str] = None  # New parameter to select an aggregator
    ) -> Dict[str, Any]:
        """Process a swap command and build the transaction."""
        try:
            # Import Scroll-specific fixes if needed
            from app.services.scroll_handler import ScrollHandler
            
            # Parse the command
            swap_command = await self.parse_swap_command(command, chain_id, wallet_address)

            # If we received an error response, return it directly
            if not isinstance(swap_command, SwapCommand):
                return swap_command

            # Handle USD amount conversion
            if swap_command.amount_is_usd:
                logger.info(f"Converting USD amount ${swap_command.amount_in} to token amount")
                # Get token price
                token_price, _ = await self.get_token_price(
                    swap_command.token_in["symbol"], 
                    "usd", 
                    chain_id
                )

                if not token_price:
                    logger.error(f"Invalid price for {swap_command.token_in['symbol']}: {token_price}")
                    raise ValueError(f"Invalid price for {swap_command.token_in['symbol']}")

                # Special case handling for small USD amounts (e.g. $1)
                orig_amount = float(swap_command.amount_in)

                # DIRECT FIX: Handle small dollar amounts exactly
                if orig_amount <= 10 and swap_command.token_in["symbol"].upper() == "ETH":
                    # For small ETH amounts, use precise division and truncate to 6 decimals max
                    token_amount = orig_amount / token_price
                    token_amount = float(f"{token_amount:.6f}")
                    logger.info(f"SMALL AMOUNT FIX: Converted ${orig_amount} to {token_amount} ETH (price: ${token_price})")
                    swap_command.amount_in = str(token_amount)
                    # Make sure to update this flag
                    swap_command.amount_is_usd = False
                    # Continue with the rest of the function
                    logger.info(f"Updated swap amount to: {swap_command.amount_in} {swap_command.token_in['symbol']}")
                else:
                    # Calculate token amount from USD amount with proper decimal handling
                    token_amount = float(swap_command.amount_in) / token_price

                # Get token decimals
                decimals = await self.token_service.get_token_decimals(swap_command.token_in["address"], chain_id)
                logger.info(f"Token decimals: {decimals}")

                # Format with appropriate precision but avoid excessive rounding
                # For a $1 swap, we want to ensure precision is maintained
                if token_price > 1000:  # High-value tokens like BTC
                    token_amount = round(token_amount, 10)
                elif token_price > 100:  # Mid-value tokens like ETH
                    token_amount = round(token_amount, 8)
                else:  # Use more precision for low-value tokens
                    token_amount = round(token_amount, 6)

                logger.info(f"Converted ${swap_command.amount_in} to {token_amount} {swap_command.token_in['symbol']} (price: ${token_price})")
                swap_command.amount_in = str(token_amount)

            # Build the swap transaction
            logger.info(f"Building swap transaction for {swap_command.token_in['symbol']} to {swap_command.token_out['symbol']}")
            tx_data = await self.build_swap_transaction(
                swap_command=swap_command,
                chain_id=chain_id,
                wallet_address=wallet_address,
                skip_approval=skip_approval
            )

            # For Scroll chain, use only Brian API
            if chain_id == 534352:  # Scroll chain ID
                logger.info("Handling Scroll chain swap - using Brian API exclusively")
                
                if isinstance(swap_command, SwapCommand):
                    # Get transaction data from Brian API
                    brian_tx_data = await ScrollHandler.use_brian_api(
                        swap_command=swap_command,
                        wallet_address=wallet_address,
                        chain_id=chain_id
                    )
                    
                    if brian_tx_data:
                        logger.info("Successfully got transaction data from Brian API")
                        tx_data = brian_tx_data
                        # Set the selected aggregator to brian
                        selected_aggregator = "brian"
                    else:
                        # If Brian API fails, return an error message
                        logger.error("Brian API failed for Scroll swap and no fallback is configured")
                        return {
                            "error": "Swap on Scroll requires Brian API which is currently unavailable. Please ensure BRIAN_API_KEY is set in your environment variables.",
                            "method": "swap",
                            "metadata": {
                                "token_in_symbol": swap_command.token_in["symbol"] if isinstance(swap_command.token_in, dict) else swap_command.token_in,
                                "token_out_symbol": swap_command.token_out["symbol"] if isinstance(swap_command.token_out, dict) else swap_command.token_out,
                                "chain_id": chain_id
                            }
                        }
                else:
                    # If we don't have a SwapCommand, return an error
                    logger.error("Invalid swap command for Scroll")
                    return {
                        "error": "Invalid swap command for Scroll",
                        "method": "swap"
                    }

            # If the user has selected a specific aggregator, filter for that one
            if selected_aggregator and 'all_quotes' in tx_data:
                selected_quote = next(
                    (
                        quote
                        for quote in tx_data['all_quotes']
                        if quote.get('aggregator') == selected_aggregator
                    ),
                    None,
                )
                if selected_quote:
                    # Calculate minimum received amount with slippage
                    slippage = swap_command.slippage / 100.0  # Convert percentage to decimal
                    minimum_received = str(int(float(selected_quote["buy_amount"]) * (1 - slippage)))

                    # Return the selected quote data
                    return {
                        "to": selected_quote["to"],
                        "data": selected_quote["data"],
                        "value": selected_quote["value"],
                        "gas_limit": selected_quote.get("gas", "500000"),
                        "method": "swap",
                        "needs_approval": tx_data.get("needs_approval", False),
                        "token_to_approve": tx_data.get("token_to_approve"),
                        "spender": tx_data.get("spender"),
                        "pending_command": tx_data.get("pending_command", command),
                        "metadata": {
                            **tx_data.get("metadata", {}),
                            "buy_amount": selected_quote["buy_amount"],
                            "sell_amount": selected_quote["sell_amount"],
                            "price": selected_quote.get("price"),
                            "protocol": selected_quote.get("protocol", selected_aggregator),
                            "gas_usd": selected_quote.get("gas_usd", "0"),
                            "aggregator": selected_aggregator,
                            "minimum_received": minimum_received,
                            "estimated_gas_usd": selected_quote.get("gas_usd", "0"),
                        }
                    }
                else:
                    # If selected aggregator wasn't found, return all quotes
                    logger.warning(f"Selected aggregator {selected_aggregator} not found, returning all quotes")

            # Return all quotes for the frontend to display
            return {
                "method": "swap",
                "all_quotes": tx_data.get("all_quotes", []),
                "quotes_count": tx_data.get("quotes_count", 0),
                "needs_approval": tx_data.get("needs_approval", False),
                "token_to_approve": tx_data.get("token_to_approve"),
                "spender": tx_data.get("spender"),
                "pending_command": tx_data.get("pending_command", command),
                "metadata": tx_data.get("metadata", {}),
                "requires_selection": True  # Flag to indicate frontend should ask user to select
            }

        except Exception as e:
            logger.error(f"Error processing swap command: {str(e)}")
            raise
    
    async def build_swap_transaction(
        self,
        swap_command: SwapCommand,
        chain_id: int,
        wallet_address: str,
        skip_approval: bool = False
    ) -> Dict[str, Any]:
        """Build a swap transaction."""
        try:
            logger.info(f"Building swap transaction for command: {swap_command}")

            # Extract token addresses
            token_in_address = swap_command.token_in["address"] if isinstance(swap_command.token_in, dict) else swap_command.token_in
            token_out_address = swap_command.token_out["address"] if isinstance(swap_command.token_out, dict) else swap_command.token_out

            # Initialize approval variables
            needs_approval = False
            token_to_approve = None
            spender = None

            # Check if approval is needed
            if not skip_approval and not is_native_token(token_in_address):
                logger.info(f"Checking allowance for {token_in_address}")
                try:
                    allowance = await self.swap_agent.get_allowance(
                        token_in_address,  # Pass just the address
                        wallet_address,
                        token_out_address,
                        chain_id
                    )
                    if int(allowance) < int(swap_command.amount_in):
                        # Need approval
                        needs_approval = True
                        token_to_approve = token_in_address
                        # Get proper spender (router) address
                        spender = get_router_address(chain_id)
                        logger.info(f"Approval needed for {token_in_address}, spender: {spender}")
                except Exception as e:
                    logger.error(f"Error checking allowance: {str(e)}")
                    # Continue anyway, we'll handle approval later

            # Define order of aggregators to try
            aggregators = [
                ("0x", self.get_0x_quote),
                ("openocean", self.get_openocean_quote),
                ("kyber", self.get_kyber_quote)
            ]

            # Convert amount to smallest units
            amount_in = await self._convert_to_smallest_units(
                float(swap_command.amount_in),
                token_in_address,  # Pass just the address
                chain_id
            )

            # Import the aggregator fixes
            from app.services.aggregator_fixes import fix_quote_for_chain, should_include_quote
            
            # Get token out decimals for validation
            token_out_decimals = await self.token_service.get_token_decimals(token_out_address, chain_id)
            
            # Store all valid quotes
            all_quotes = []
            errors = []

            # Try each aggregator and collect quotes
            for name, get_quote_func in aggregators:
                try:
                    logger.info(f"Getting quote from {name}")

                    quote = await get_quote_func(
                        token_in_address, 
                        token_out_address,
                        amount_in,  # Already in smallest units
                        chain_id,
                        wallet_address,
                        swap_command.slippage
                    )
                    if quote:
                        # Add the aggregator name to the quote for frontend display
                        quote["aggregator"] = name
                        
                        # Apply chain-specific fixes to the quote
                        fixed_quote = fix_quote_for_chain(quote, chain_id, name, token_out_decimals)
                        
                        # Check if the quote should be included
                        if should_include_quote(fixed_quote, chain_id, name):
                            # Store the quote
                            all_quotes.append(fixed_quote)
                            logger.info(f"Got valid quote from {name}: {fixed_quote.get('buy_amount')} output tokens")
                        else:
                            logger.warning(f"Excluding invalid quote from {name}")
                            errors.append(f"{name}: Quote validation failed")
                except Exception as e:
                    logger.error(f"Error getting quote from {name}: {str(e)}")
                    errors.append(f"{name}: {str(e)}")

            # If we have no quotes, raise an exception
            if not all_quotes:
                error_msg = ", ".join(errors)
                logger.error(f"No quotes available: {error_msg}")
                if "No route found" in error_msg:
                    raise NoRouteFoundError("No route found for this swap")
                elif "liquidity" in error_msg.lower():
                    raise InsufficientLiquidityError("Insufficient liquidity for this swap")
                else:
                    raise ValueError(f"Failed to get quotes: {error_msg}")

            # Look up token information for metadata
            token_in_info = await self.token_service.lookup_token(token_in_address, chain_id)
            token_out_info = await self.token_service.lookup_token(token_out_address, chain_id)

            # Return all quotes and metadata 
            return {
                "all_quotes": all_quotes,
                "quotes_count": len(all_quotes),
                "needs_approval": needs_approval,
                "token_to_approve": token_to_approve,
                "spender": spender,
                "pending_command": swap_command.natural_command,
                "metadata": {
                    "token_in_address": token_in_address,
                    "token_in_symbol": token_in_info[1],
                    "token_in_name": token_in_info[2],
                    "token_in_verified": token_in_info[3].get("verified", False) if token_in_info[3] else False,
                    "token_in_source": token_in_info[3].get("source", "unknown") if token_in_info[3] else "unknown",
                    "token_out_address": token_out_address,
                    "token_out_symbol": token_out_info[1],
                    "token_out_name": token_out_info[2],
                    "token_out_verified": token_out_info[3].get("verified", False) if token_out_info[3] else False,
                    "token_out_source": token_out_info[3].get("source", "unknown") if token_out_info[3] else "unknown",
                }
            }
        except Exception as e:
            logger.error(f"Error building swap transaction: {str(e)}")
            raise

    async def get_0x_quote(
        self,
        token_in: Union[str, Dict],
        token_out: Union[str, Dict],
        amount: int,
        chain_id: int,
        wallet_address: str,
        slippage_percentage: float = 1.0
    ) -> Dict[str, Any]:
        """Get quote from 0x API using the modular service."""
        return await get_zerox_quote(
            self.http_client,
            token_in,
            token_out,
            amount,
            chain_id,
            wallet_address,
            slippage_percentage
        )

    async def get_openocean_quote(
        self,
        token_in: Union[str, Dict],
        token_out: Union[str, Dict],
        amount: float,
        chain_id: int,
        wallet_address: str,
        slippage_percentage: float = 1.0
    ) -> Optional[Dict[str, Any]]:
        """Get quote from OpenOcean API using the modular service."""
        return await get_openocean_quote(
            self.http_client,
            token_in,
            token_out,
            amount,
            chain_id,
            wallet_address,
            slippage_percentage,
            self._get_chain_name
        )

    async def get_kyber_quote(
        self,
        token_in: Union[str, Dict],
        token_out: Union[str, Dict],
        amount_in_smallest_units: int,
        chain_id: int,
        recipient: str,
        slippage_percentage: float = 1.0
    ) -> Optional[Dict[str, Any]]:
        """Get quote from Kyber API using the modular service."""
        return await get_kyber_quote(
            self.http_client,
            token_in,
            token_out,
            amount_in_smallest_units,
            chain_id,
            recipient,
            slippage_percentage
        )
    
    async def parse_swap_command(
        self,
        command: str,
        chain_id: int,
        wallet_address: str
    ) -> Union[SwapCommand, Dict[str, Any]]:
        """Parse a swap command."""
        try:
            logger.info(f"Parsing swap command: {command}")

            # Parse the command using the agent
            swap_agent = SimpleSwapAgent()
            response = await swap_agent.process_swap_command(command, chain_id)

            logger.info(f"Agent response: {response}")

            if response.get("error"):
                logger.error(f"Error from agent: {response.get('error')}")
                raise ValueError(f"Error parsing command: {response.get('error')}")

            content = response.get("content")
            if not content or content.get("type") != "swap_confirmation":
                logger.error(f"Invalid response from agent: {response}")

                # Check for missing information
                missing_info = self._detect_missing_information(command, response)
                if missing_info:
                    return missing_info
                
                raise ValueError(f"Invalid response from agent: {response}")
                
            # Extract content
            logger.info(f"Parsed swap: {content.get('amount')}  {content.get('token_in')} to {content.get('token_out')}")

            # Get necessary data from response
            token_in = content["token_in"]
            token_out = content["token_out"]
            amount = float(content["amount"])  # Ensure amount is float
            amount_is_usd = content.get("amount_is_usd", False)

            logger.info(f"Parsed swap: {amount} {'USD worth of' if amount_is_usd else ''} {token_in['symbol']} to {token_out['symbol']}")

            # Convert USD amount to token amount if needed
            if amount_is_usd:
                logger.info(f"Converting USD amount ${amount} to {token_in['symbol']} amount")

                # Get token price using the consolidated price_service
                price_data = await price_service.get_token_price(token_in["symbol"], "usd", chain_id)

                if not price_data or not isinstance(price_data, dict) or "price" not in price_data:
                    logger.error(f"Failed to get price for {token_in['symbol']}")
                    raise ValueError(f"Failed to get price for {token_in['symbol']}")

                token_price = float(price_data["price"])
                if token_price <= 0:
                    logger.error(f"Invalid price for {token_in['symbol']}: {token_price}")
                    raise ValueError(f"Invalid price for {token_in['symbol']}")

                # Special handling for small USD amounts (e.g. $1)
                orig_amount = amount

                # DIRECT FIX: Handle small dollar amounts exactly
                if orig_amount <= 10 and token_in["symbol"].upper() == "ETH":
                    # For small ETH amounts, use precise division with fixed precision
                    token_amount = orig_amount / token_price
                    token_amount = float(f"{token_amount:.6f}")
                    logger.info(f"SMALL AMOUNT FIX: Converted ${orig_amount} to {token_amount} ETH (price: ${token_price})")
                else:
                    # Calculate token amount from USD amount with proper decimal handling
                    token_amount = amount / token_price

                    # Get token decimals
                    decimals = await self.token_service.get_token_decimals(token_in["address"], chain_id)
                    logger.info(f"Token decimals: {decimals}")

                    # Format with appropriate precision but avoid excessive rounding
                    # For a $1 swap, we want to ensure precision is maintained
                    if token_price > 1000:  # High-value tokens like BTC
                        token_amount = round(token_amount, 10)
                    elif token_price > 100:  # Mid-value tokens like ETH
                        token_amount = round(token_amount, 8)
                    else:  # Low-value tokens
                        token_amount = round(token_amount, 6)

                    logger.info(f"Converted ${amount} to {token_amount} {token_in['symbol']} (price: ${token_price})")
                amount = token_amount
            # Create swap command with full token info
            swap_command = SwapCommand(
                action="swap",
                amount_in=str(amount),
                token_in=token_in,  # Pass the full token info dictionary
                token_out=token_out,  # Pass the full token info dictionary
                is_target_amount=content.get("is_target_amount", False),
                amount_is_usd=False,  # Set to False since we've already converted
                natural_command=command,
                slippage=0.5  # Default slippage
            )

            return swap_command

        except ValueError as e:
            logger.error(f"Value error: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error parsing swap command: {str(e)}")
            raise ValueError(f"Failed to parse swap command: {str(e)}")
    
    def _detect_missing_information(self, command: str, response: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Detect missing information in a swap command.
        
        Args:
            command: The original command
            response: The agent response
            
        Returns:
            Dict with missing information details or None if no missing information
        """
        missing_info = []
        clarification_prompt = None

        # Check if the command is too vague
        if "swap" in command.lower() and len(command.split()) < 3:
            missing_info.extend(("amount", "tokens"))
            clarification_prompt = "Please specify how much and which tokens you want to swap. For example: 'swap 0.1 ETH for USDC'"
            return {
                "missing_info": missing_info,
                "clarification_prompt": clarification_prompt
            }

        # Extract what we can from the response
        content = response.get("content", {})
        metadata = response.get("metadata", {})

        # Check for missing amount
        if not content.get("amount") and "amount" not in missing_info:
            missing_info.append("amount")

        # Check for missing tokens
        if not content.get("token_in") and "token_in" not in missing_info:
            missing_info.append("token_in")

        if not content.get("token_out") and "token_out" not in missing_info:
            missing_info.append("token_out")

        # If we have missing information, create a clarification prompt
        if missing_info:
            if "amount" in missing_info and "token_in" in missing_info and "token_out" in missing_info:
                clarification_prompt = "Please specify how much and which tokens you want to swap. For example: 'swap 0.1 ETH for USDC'"
            elif "amount" in missing_info:
                token_in = content.get("token_in", {}).get("symbol", "")
                token_out = content.get("token_out", {}).get("symbol", "")
                if token_in and token_out:
                    clarification_prompt = f"How much {token_in} would you like to swap for {token_out}?"
                else:
                    clarification_prompt = "Please specify how much you want to swap."
            elif "token_in" in missing_info:
                clarification_prompt = "Which token would you like to swap from?"
            elif "token_out" in missing_info:
                clarification_prompt = "Which token would you like to swap to?"

            return {
                "missing_info": missing_info,
                "clarification_prompt": clarification_prompt
            }

        return None
    
    async def get_token_price(
        self, 
        token_symbol: str,
        quote_currency: str = "usd",
        chain_id: int = 1
    ) -> Tuple[Optional[float], int]:
        """
        Get the price of a token in USD.
        
        Args:
            token_symbol: The token symbol
            quote_currency: The currency to get the price in (default: usd)
            chain_id: The chain ID
            
        Returns:
            Tuple of (price_per_token, token_decimals) or (None, default_decimals) if not found
        """
        try:
            # Use the consolidated price_service to get real-time prices
            return await price_service.get_token_price(token_symbol, quote_currency, chain_id)
            
        except Exception as e:
            logger.error(f"Error getting token price: {e}")
            return None, TOKEN_DECIMALS.get(token_symbol.upper(), 18)
    
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
            # Import the error handler
            from app.services.error_handler import handle_transaction_error
            
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
            # Use our new error handler
            return handle_transaction_error(e)

    async def _convert_to_smallest_units(self, amount: float, token_address: str, chain_id: int) -> int:
        """Convert a decimal amount to the smallest units based on token decimals."""
        try:
            # Get token decimals - this part still needs to be done in the service
            decimals = await self.token_service.get_token_decimals(token_address, chain_id)
            logger.info(f"Converting {amount} to smallest units using token_conversion util (decimals: {decimals})")
            
            # Use the new token conversion utility
            return amount_to_smallest_units(amount, decimals)
            
        except Exception as e:
            logger.error(f"Error converting amount to smallest units: {e}")
            raise

    def _get_chain_name(self, chain_id: int) -> str:
        """Get chain name for API endpoints"""
        chain_mapping = {
            1: "eth",  # OpenOcean uses "eth", Kyber uses "ethereum"
            10: "optimism",
            137: "polygon",
            42161: "arbitrum",
            8453: "base",
            534352: "scroll"
        }

        chain = chain_mapping.get(chain_id)
        if not chain:
            raise ValueError(f"Chain {chain_id} not supported")

        # Kyber uses "ethereum" instead of "eth"
        return "ethereum" if chain == "eth" else chain 

    async def get_swap_quotes(
        self,
        command: str,
        chain_id: int,
        wallet_address: str,
        slippage: float = 0.5
    ) -> Dict[str, Any]:
        """
        Get quotes for a swap command from multiple aggregators.
        Returns formatted quotes for the frontend.
        """
        try:
            # Parse the swap command
            swap_command = await self.parse_swap_command(command, chain_id, wallet_address)

            if not isinstance(swap_command, SwapCommand):
                raise ValueError(f"Failed to parse swap command: {command}")

            # Get token information
            logger.info(f"Parsed swap: {swap_command.amount_in}  {swap_command.token_in} to {swap_command.token_out}")

            token_in_info = await self.token_service.lookup_token(
                swap_command.token_in, chain_id
            )
            token_out_info = await self.token_service.lookup_token(
                swap_command.token_out, chain_id
            )

            # Extract token info (address, symbol, name, metadata)
            from_address, from_symbol, from_name, from_metadata = token_in_info
            to_address, to_symbol, to_name, to_metadata = token_out_info

            # Determine the amount to swap
            amount_in = float(swap_command.amount_in)

            # If amount is in USD, convert to token amount
            if swap_command.amount_is_usd:
                token_price, _ = await self.get_token_price(
                    from_symbol, "usd", chain_id
                )
                if not token_price:
                    raise ValueError(f"Could not get price for {from_symbol}")
                amount_in /= token_price

            # Convert to smallest units
            decimals = await self.token_service.get_token_decimals(from_address, chain_id)
            amount_in_smallest = amount_to_smallest_units(amount_in, decimals)

            # Get quotes from different aggregators
            quotes = []

            # Try 0x
            try:
                zero_x_quote = await self.get_0x_quote(
                    from_address,
                    to_address,
                    amount_in_smallest,
                    chain_id,
                    wallet_address,
                    slippage
                )
                if zero_x_quote:
                    quotes.append({
                        **zero_x_quote,
                        "aggregator": "0x",
                        "protocol": zero_x_quote.get("protocol", "0x")
                    })
            except Exception as e:
                logging.warning(f"Failed to get 0x quote: {e}")

            # Try OpenOcean
            try:
                openocean_quote = await self.get_openocean_quote(
                    from_address,
                    to_address,
                    amount_in,
                    chain_id,
                    wallet_address,
                    slippage
                )
                if openocean_quote:
                    quotes.append({
                        **openocean_quote,
                        "aggregator": "openocean",
                        "protocol": openocean_quote.get("protocol", "openocean")
                    })
            except Exception as e:
                logging.warning(f"Failed to get OpenOcean quote: {e}")

            # Try Kyber
            try:
                kyber_quote = await self.get_kyber_quote(
                    from_address,
                    to_address,
                    amount_in_smallest,
                    chain_id,
                    wallet_address,
                    slippage
                )
                if kyber_quote:
                    quotes.append({
                        **kyber_quote,
                        "aggregator": "kyber",
                        "protocol": kyber_quote.get("protocol", "kyber")
                    })
            except Exception as e:
                logging.warning(f"Failed to get Kyber quote: {e}")

            # Format quotes for frontend display
            formatted_quotes = []
            token_out_decimals = await self.token_service.get_token_decimals(
                to_address, chain_id
            )

            for quote in quotes:
                # Calculate minimum received with slippage
                buy_amount = quote.get("buy_amount", "0")
                slippage_factor = slippage / 100.0
                minimum_received = str(int(int(buy_amount) * (1 - slippage_factor)))

                # Format for AggregatorSelection component
                formatted_quotes.append({
                    "aggregator": quote.get("aggregator", "unknown"),
                    "protocol": quote.get("protocol", quote.get("aggregator", "unknown")),
                    "buy_amount": buy_amount,
                    "minimum_received": minimum_received,
                    "gas_usd": quote.get("gas_usd", "0"),
                    "gas": quote.get("gas", "500000"),
                    "to": quote.get("to", ""),
                    "data": quote.get("data", ""),
                    "value": quote.get("value", "0"),
                    "token_in_symbol": from_symbol,
                    "token_in_decimals": decimals,
                    "token_out_symbol": to_symbol,
                    "token_out_decimals": token_out_decimals
                })

            # Sort quotes by output amount (descending)
            formatted_quotes.sort(
                key=lambda q: int(q["buy_amount"]), 
                reverse=True
            )

            # For Scroll chain, use only Brian API
            if chain_id == 534352:  # Scroll chain ID
                from app.services.scroll_handler import ScrollHandler
                logger.info("Handling Scroll chain quotes - using Brian API exclusively")
                
                # Get transaction data from Brian API
                brian_tx_data = await ScrollHandler.use_brian_api(
                    swap_command=swap_command,
                    wallet_address=wallet_address,
                    chain_id=chain_id
                )
                
                if brian_tx_data and brian_tx_data.get("all_quotes"):
                    # Replace all quotes with Brian API quotes
                    formatted_quotes = []
                    
                    for quote in brian_tx_data["all_quotes"]:
                        if quote.get("is_approval", False):
                            continue
                            
                        formatted_quotes.append({
                            "aggregator": "brian",
                            "protocol": "Brian API",
                            "buy_amount": quote.get("buy_amount", "0"),
                            "minimum_received": quote.get("buy_amount", "0"),  # Will be adjusted with slippage later
                            "gas_usd": "0",
                            "gas": quote.get("gas", "500000"),
                            "to": quote.get("to", ""),
                            "data": quote.get("data", ""),
                            "value": quote.get("value", "0"),
                            "token_in_symbol": from_symbol,
                            "token_in_decimals": decimals,
                            "token_out_symbol": to_symbol,
                            "token_out_decimals": token_out_decimals
                        })
                    
                    # Add a note about Brian API
                    return {
                        "quotes": formatted_quotes,
                        "token_in": {
                            "address": from_address,
                            "symbol": from_symbol,
                            "name": from_name,
                            "metadata": from_metadata
                        },
                        "token_out": {
                            "address": to_address,
                            "symbol": to_symbol,
                            "name": to_name,
                            "metadata": to_metadata
                        },
                        "amount": amount_in,
                        "amount_is_usd": swap_command.amount_is_usd,
                        "scroll_note": "Using Brian API for Scroll swaps"
                    }
                else:
                    # If Brian API fails, return an error
                    raise ValueError("Brian API is required for Scroll swaps but is currently unavailable. Please ensure BRIAN_API_KEY is set in your environment variables.")

            return {
                "quotes": formatted_quotes,
                "token_in": {
                    "address": from_address,
                    "symbol": from_symbol,
                    "name": from_name,
                    "metadata": from_metadata
                },
                "token_out": {
                    "address": to_address,
                    "symbol": to_symbol,
                    "name": to_name,
                    "metadata": to_metadata
                },
                "amount": amount_in,
                "amount_is_usd": swap_command.amount_is_usd
            }
        except Exception as e:
            logging.exception(f"Error getting swap quotes: {e}")
            raise
            
    async def build_transaction_from_quote(
        self,
        wallet_address: str,
        chain_id: int,
        selected_quote: Dict[str, Any],
        pending_command: str
    ) -> Dict[str, Any]:
        """
        Build a transaction from a selected quote.
        """
        try:
            # Validate the quote
            required_fields = ["to", "data", "value"]
            for field in required_fields:
                if field not in selected_quote:
                    raise ValueError(f"Missing required field in quote: {field}")
            
            # Get gas parameters
            web3 = self.tx_executor.get_web3(chain_id)
            gas_params = await self.tx_executor.get_gas_parameters(web3, chain_id)
            
            # Estimate gas
            tx = {
                "from": wallet_address,
                "to": selected_quote["to"],
                "data": selected_quote["data"],
                "value": selected_quote["value"]
            }
            
            # Try to use gas from the quote if available
            gas_limit = selected_quote.get("gas")
            if not gas_limit:
                try:
                    gas_limit = await self.tx_executor.estimate_gas_with_buffer(
                        web3, tx, "swap"
                    )
                except Exception as e:
                    logging.warning(f"Failed to estimate gas: {e}")
                    gas_limit = 500000  # Fallback
            
            # Build transaction data
            tx_data = {
                "to": selected_quote["to"],
                "data": selected_quote["data"],
                "value": selected_quote["value"],
                "gas_limit": str(gas_limit),
                **gas_params,
                "method": "swap",
                "pending_command": pending_command,
                "metadata": {
                    "token_in_symbol": selected_quote.get("token_in_symbol"),
                    "token_out_symbol": selected_quote.get("token_out_symbol"),
                    "aggregator": selected_quote.get("aggregator"),
                    "buy_amount": selected_quote.get("buy_amount"),
                    "chain_id": chain_id
                }
            }
            
            # Apply Scroll-specific fixes if on Scroll chain
            if chain_id == 534352:  # Scroll chain ID
                from app.services.scroll_handler import ScrollHandler
                logger.info("Applying Scroll-specific fixes to transaction")
                tx_data = ScrollHandler.apply_scroll_fixes(tx_data, chain_id)
            
            return tx_data
        except Exception as e:
            logging.exception(f"Error building transaction from quote: {e}")
            raise

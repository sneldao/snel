from typing import Optional, Dict, Any
import logging
import json
from pydantic import Field
from emp_agents import OpenAIProvider
from app.agents.base import PointlessAgent
from app.services.token_service import TokenService
from app.services.prices import get_token_price
from eth_utils import is_address

logger = logging.getLogger(__name__)

# Special token addresses that we know about but might not be in the main config
SPECIAL_TOKEN_ADDRESSES = {
    534352: {  # Scroll
        "NURI": "0x0261c29c68a85c1d9f9d2dc0c02b1f9e8e0dC7cc",
    }
}

class SwapAgent(PointlessAgent):
    """Agent for handling token swaps."""
    token_service: TokenService = Field(default_factory=TokenService)
    
    model_config = {
        "arbitrary_types_allowed": True
    }
    
    def __init__(self, provider: OpenAIProvider):
        super().__init__(
            provider=provider,
            prompt="""
            You are a crypto assistant that understands natural language swap requests.
            Extract swap details from the message, being flexible in understanding various formats.
            
            The user might specify amounts in several ways:
            1. Direct amount: "swap 1 ETH for USDC"
            2. Target amount in token: "get me 100 USDC using ETH"
            3. Target amount in USD: "swap $50 worth of ETH to USDC"
            4. Natural language: "I want to trade my ETH for some USDC"
            5. Contract addresses: Handle Ethereum addresses (e.g. "0x1234...") exactly as provided
            
            Return a JSON object with:
            {
                "amount": number,  # The amount specified
                "token_in": string,  # Input token symbol or contract address exactly as provided
                "token_out": string,  # Output token symbol or contract address exactly as provided
                "is_target_amount": boolean,  # true if amount refers to output token or USD
                "amount_is_usd": boolean,  # true if amount is in USD
                "natural_command": string  # The command as understood in natural language
            }
            """
        )
    
    async def process_swap(self, input_text: str, chain_id: Optional[int] = None) -> Dict[str, Any]:
        """Process a swap request and return structured data."""
        try:
            # Get raw response from LLM
            response = await super().process(input_text)
            if response["error"]:
                return response
            
            # Parse the JSON response
            try:
                data = json.loads(response["content"])
                if "error" in data:
                    return {
                        "content": None,
                        "error": data["error"],
                        "metadata": {}
                    }
                
                # Look up tokens
                token_in = data["token_in"]
                token_out = data["token_out"]
                
                # Look up tokens
                token_in_address, token_in_symbol, token_in_name = await self.token_service.lookup_token(token_in, chain_id)
                if not token_in_symbol and not token_in_address:
                    error_msg = f"The token '{token_in}' is not recognized as a valid cryptocurrency or contract address."
                    return {
                        "content": None,
                        "error": error_msg,
                        "metadata": {}
                    }
                
                token_out_address, token_out_symbol, token_out_name = await self.token_service.lookup_token(token_out, chain_id)
                
                # Special case for NURI token on Scroll
                if (not token_out_symbol and not token_out_address) and token_out.upper() in ["NURI", "$NURI"] and chain_id == 534352:
                    token_out_address = "0x0261c29c68a85c1d9f9d2dc0c02b1f9e8e0dC7cc"
                    token_out_symbol = "NURI"
                    token_out_name = "NURI Token"
                    logger.info(f"Using hardcoded address for NURI token on Scroll: {token_out_address}")
                
                if not token_out_symbol and not token_out_address:
                    # For tokens with $ prefix, we'll allow them even without an address
                    if token_out.startswith('$'):
                        logger.warning(f"Token {token_out} not found, but allowing it as a special token")
                        token_out_symbol = token_out.lstrip('$')
                        
                        # Check if it's in our special token addresses
                        if token_out_symbol.upper() in SPECIAL_TOKEN_ADDRESSES.get(chain_id, {}):
                            token_out_address = SPECIAL_TOKEN_ADDRESSES[chain_id][token_out_symbol.upper()]
                            logger.info(f"Found special token address for {token_out_symbol}: {token_out_address}")
                            warning_msg = (
                                f"I found the contract address for {token_out}. "
                                "I'll use this address for the swap."
                            )
                        else:
                            warning_msg = (
                                f"⚠️ Warning: The token '{token_out}' could not be verified. "
                                "To proceed with the swap, please provide the contract address directly. "
                                "For example: 'swap ETH for 0x1234...abcd'. "
                                "You can find contract addresses on sites like Etherscan, CoinGecko, or the token's official website."
                            )
                    else:
                        error_msg = (
                            f"The token '{token_out}' is not recognized as a valid cryptocurrency or contract address. "
                            "Please provide the contract address directly. For example: 'swap ETH for 0x1234...abcd'. "
                            "You can find contract addresses on sites like Etherscan, CoinGecko, or the token's official website."
                        )
                        return {
                            "content": None,
                            "error": error_msg,
                            "metadata": {}
                        }
                
                # Use canonical symbols if found
                display_token_in = token_in_symbol if token_in_symbol else token_in
                display_token_out = token_out_symbol if token_out_symbol else token_out
                
                # For contract addresses, add the symbol in parentheses if available
                if is_address(token_in) and token_in_symbol:
                    display_token_in = f"{token_in_symbol} ({token_in[:6]}...{token_in[-4:]})"
                    if token_in_name:
                        display_token_in = f"{token_in_name} ({token_in_symbol}, {token_in[:6]}...{token_in[-4:]})"
                
                if is_address(token_out) and token_out_symbol:
                    display_token_out = f"{token_out_symbol} ({token_out[:6]}...{token_out[-4:]})"
                    if token_out_name:
                        display_token_out = f"{token_out_name} ({token_out_symbol}, {token_out[:6]}...{token_out[-4:]})"
                elif is_address(token_out) and not token_out_symbol:
                    # For unverified contract addresses, show a warning
                    display_token_out = f"{token_out[:6]}...{token_out[-4:]}"
                    warning_msg = (
                        f"⚠️ Warning: The token with address '{token_out}' could not be verified. "
                        "Please ensure you're swapping to the correct token before confirming."
                    )
                
                # Format response message
                if data.get("amount_is_usd", False):
                    # Calculate the input amount based on USD value
                    token_in_price, _ = await get_token_price(token_in_symbol or token_in)
                    eth_amount = data["amount"] / token_in_price
                    message = (
                        f"I'll help you swap approximately {eth_amount:.6f} {display_token_in} (~${data['amount']:.2f}) "
                        f"for {display_token_out}. The exact amount of tokens you'll receive will be determined at "
                        "the time of the swap based on current market rates."
                    )
                    command = f"swap {eth_amount:.6f} {token_in_symbol or token_in} for {token_out_symbol or token_out}"
                elif data.get("is_target_amount", False):
                    message = f"I'll help you swap {display_token_in} to get {data['amount']} {display_token_out}."
                    command = f"swap {token_in_symbol or token_in} for {data['amount']} {token_out_symbol or token_out}"
                else:
                    message = f"I'll help you swap {data['amount']} {display_token_in} for {display_token_out}."
                    command = f"swap {data['amount']} {token_in_symbol or token_in} for {token_out_symbol or token_out}"
                
                # Add warning if token couldn't be verified
                if 'warning_msg' in locals():
                    message = f"{message}\n\n{warning_msg}"
                
                message += " Does this look good? Reply with 'yes' to confirm or 'no' to cancel."
                
                # Store the actual addresses for the transaction
                actual_token_in = token_in_address if token_in_address else token_in
                actual_token_out = token_out_address if token_out_address else token_out
                
                return {
                    "content": message,
                    "error": None,
                    "metadata": {
                        "pending_command": command,
                        "swap_details": {
                            "amount": data["amount"],
                            "token_in": token_in_symbol or token_in,
                            "token_out": token_out_symbol or token_out,
                            "token_in_address": token_in_address,
                            "token_out_address": token_out_address,
                            "chain_id": chain_id,
                            "is_target_amount": data.get("is_target_amount", False),
                            "amount_is_usd": data.get("amount_is_usd", False),
                            "natural_command": data.get("natural_command", ""),
                            "token_in_name": token_in_name,
                            "token_out_name": token_out_name
                        }
                    }
                }
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse LLM response: {e}")
                return {
                    "content": None,
                    "error": "Could not parse swap command. Please try rephrasing your request.",
                    "metadata": {}
                }
                
        except Exception as e:
            logger.error(f"Error processing swap: {e}", exc_info=True)
            return {
                "content": None,
                "error": f"An error occurred while processing your request: {str(e)}",
                "metadata": {}
            } 
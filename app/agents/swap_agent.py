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
                # Add debug logging to see what's coming back from the LLM
                logger.info(f"Raw LLM response: {response['content']}")
                
                # Check if the response is empty or None
                if not response["content"]:
                    return {
                        "content": None,
                        "error": "Received empty response from language model",
                        "metadata": {}
                    }
                
                # Clean up the response if it's wrapped in markdown code blocks
                content = response["content"]
                if content.startswith("```") and "```" in content[3:]:
                    # Extract the content between the code blocks
                    content = content.split("```", 2)[1]
                    # Remove language identifier if present (e.g., "json")
                    if "\n" in content:
                        content = content.split("\n", 1)[1]
                    # Find the closing code block and remove everything after it
                    if "```" in content:
                        content = content.split("```")[0]
                    logger.info(f"Extracted JSON from markdown: {content}")
                
                # Try to parse as JSON
                try:
                    data = json.loads(content)
                except json.JSONDecodeError:
                    # Try one more time with the original content
                    logger.warning("Failed to parse extracted content, trying original response")
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
                
                # Look up tokens - handle the tuple unpacking correctly
                token_in_result = await self.token_service.lookup_token(token_in, chain_id)
                token_in_address = token_in_symbol = token_in_name = None
                token_in_metadata = {}
                
                # Safely unpack token_in_result
                if token_in_result:
                    if len(token_in_result) >= 1:
                        token_in_address = token_in_result[0]
                    if len(token_in_result) >= 2:
                        token_in_symbol = token_in_result[1]
                    if len(token_in_result) >= 3:
                        token_in_name = token_in_result[2]
                    if len(token_in_result) >= 4:
                        token_in_metadata = token_in_result[3] or {}
                
                if not token_in_symbol and not token_in_address:
                    error_msg = f"The token '{token_in}' is not recognized as a valid cryptocurrency or contract address."
                    return {
                        "content": None,
                        "error": error_msg,
                        "metadata": {}
                    }
                
                token_out_result = await self.token_service.lookup_token(token_out, chain_id)
                token_out_address = token_out_symbol = token_out_name = None
                token_out_metadata = {}
                
                # Safely unpack token_out_result
                if token_out_result:
                    if len(token_out_result) >= 1:
                        token_out_address = token_out_result[0]
                    if len(token_out_result) >= 2:
                        token_out_symbol = token_out_result[1]
                    if len(token_out_result) >= 3:
                        token_out_name = token_out_result[2]
                    if len(token_out_result) >= 4:
                        token_out_metadata = token_out_result[3] or {}
                
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
                    message = {
                        "type": "swap_confirmation",
                        "text": f"I'll help you swap approximately {eth_amount:.6f} {display_token_in} (~${data['amount']:.2f}) for {display_token_out}.",
                        "subtext": "The exact amount of tokens you'll receive will be determined at the time of the swap based on current market rates.",
                        "tokens": {
                            "in": {
                                "symbol": token_in_symbol,
                                "name": token_in_name,
                                "address": token_in_address,
                                "display": display_token_in,
                                "amount": eth_amount,
                                "usd_value": data['amount']
                            },
                            "out": {
                                "symbol": token_out_symbol,
                                "name": token_out_name,
                                "address": token_out_address,
                                "display": display_token_out
                            }
                        },
                        "verification_links": {
                            "in": self._get_verification_links(token_in_address or token_in_symbol, chain_id),
                            "out": self._get_verification_links(token_out_address or token_out_symbol, chain_id)
                        }
                    }
                    command = f"swap {eth_amount:.6f} {token_in_symbol or token_in} for {token_out_symbol or token_out}"
                elif data.get("is_target_amount", False):
                    message = {
                        "type": "swap_confirmation",
                        "text": f"I'll help you swap {display_token_in} to get {data['amount']} {display_token_out}.",
                        "tokens": {
                            "in": {
                                "symbol": token_in_symbol,
                                "name": token_in_name,
                                "address": token_in_address,
                                "display": display_token_in
                            },
                            "out": {
                                "symbol": token_out_symbol,
                                "name": token_out_name,
                                "address": token_out_address,
                                "display": display_token_out,
                                "amount": data['amount']
                            }
                        },
                        "verification_links": {
                            "in": self._get_verification_links(token_in_address or token_in_symbol, chain_id),
                            "out": self._get_verification_links(token_out_address or token_out_symbol, chain_id)
                        }
                    }
                    command = f"swap {token_in_symbol or token_in} for {data['amount']} {token_out_symbol or token_out}"
                else:
                    message = {
                        "type": "swap_confirmation",
                        "text": f"I'll help you swap {data['amount']} {display_token_in} for {display_token_out}.",
                        "tokens": {
                            "in": {
                                "symbol": token_in_symbol,
                                "name": token_in_name,
                                "address": token_in_address,
                                "display": display_token_in,
                                "amount": data['amount']
                            },
                            "out": {
                                "symbol": token_out_symbol,
                                "name": token_out_name,
                                "address": token_out_address,
                                "display": display_token_out
                            }
                        },
                        "verification_links": {
                            "in": self._get_verification_links(token_in_address or token_in_symbol, chain_id),
                            "out": self._get_verification_links(token_out_address or token_out_symbol, chain_id)
                        }
                    }
                    command = f"swap {data['amount']} {token_in_symbol or token_in} for {token_out_symbol or token_out}"
                
                # Add warning if token couldn't be verified
                if 'warning_msg' in locals():
                    message["warning"] = warning_msg
                
                message["confirmation_prompt"] = "Does this look good? Reply with 'yes' to confirm or 'no' to cancel in the chat."
                
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
                logger.error(f"Failed to parse LLM response as JSON: {e}")
                # Return a more helpful error message
                return {
                    "content": None,
                    "error": f"Failed to parse swap details. Please try again with a clearer request. Error: {str(e)}",
                    "metadata": {}
                }
            except KeyError as e:
                logger.error(f"Missing required field in LLM response: {e}")
                return {
                    "content": None,
                    "error": f"Missing required information in swap request: {str(e)}",
                    "metadata": {}
                }
            except Exception as e:
                logger.error(f"Error processing swap request: {e}")
                return {
                    "content": None,
                    "error": f"Error processing swap request: {str(e)}",
                    "metadata": {}
                }
            
        except Exception as e:
            logger.error(f"Error processing swap: {e}", exc_info=True)
            return {
                "content": None,
                "error": f"An error occurred while processing your request: {str(e)}",
                "metadata": {}
            }
            
    def _get_verification_links(self, token: str, chain_id: Optional[int] = None) -> Dict[str, str]:
        """Generate verification links for a token."""
        links = {}
        
        # Skip if token is None
        if not token:
            return links
            
        # Handle contract addresses
        if is_address(token):
            # Etherscan and similar
            if chain_id == 1:  # Ethereum Mainnet
                links["explorer"] = f"https://etherscan.io/token/{token}"
            elif chain_id == 137:  # Polygon
                links["explorer"] = f"https://polygonscan.com/token/{token}"
            elif chain_id == 10:  # Optimism
                links["explorer"] = f"https://optimistic.etherscan.io/token/{token}"
            elif chain_id == 42161:  # Arbitrum
                links["explorer"] = f"https://arbiscan.io/token/{token}"
            elif chain_id == 8453:  # Base
                links["explorer"] = f"https://basescan.org/token/{token}"
            elif chain_id == 534352:  # Scroll
                links["explorer"] = f"https://scrollscan.com/token/{token}"
            
            # Add CoinGecko if we have a contract address
            links["coingecko"] = f"https://www.coingecko.com/en/coins/{token}"
            
            # Add Dexscreener for price charts with the correct chain
            if chain_id == 1:  # Ethereum
                links["dexscreener"] = f"https://dexscreener.com/ethereum/{token}"
            elif chain_id == 137:  # Polygon
                links["dexscreener"] = f"https://dexscreener.com/polygon/{token}"
            elif chain_id == 42161:  # Arbitrum
                links["dexscreener"] = f"https://dexscreener.com/arbitrum/{token}"
            elif chain_id == 10:  # Optimism
                links["dexscreener"] = f"https://dexscreener.com/optimism/{token}"
            elif chain_id == 8453:  # Base
                links["dexscreener"] = f"https://dexscreener.com/base/{token}"
            elif chain_id == 534352:  # Scroll
                links["dexscreener"] = f"https://dexscreener.com/scroll/{token}"
            elif chain_id == 43114:  # Avalanche
                links["dexscreener"] = f"https://dexscreener.com/avalanche/{token}"
            else:
                # Default to search if chain not specifically handled
                links["dexscreener"] = f"https://dexscreener.com/search?q={token}"
            
        # Handle token symbols
        else:
            # Clean the token symbol (remove $ prefix if present)
            clean_token = token.lstrip('$')
            token_lower = clean_token.lower()
            
            # For well-known tokens, add CoinGecko
            if token_lower in ["eth", "weth", "usdc", "usdt", "dai"]:
                links["coingecko"] = f"https://www.coingecko.com/en/coins/{token_lower}"
                links["dexscreener"] = f"https://dexscreener.com/search?q={token_lower}"
            # For custom tokens, add search links
            else:
                # Add search links for any token, including custom tokens
                links["coingecko"] = f"https://www.coingecko.com/en/search?query={token_lower}"
                links["dexscreener"] = f"https://dexscreener.com/search?q={token_lower}"
                
                # If it's a token with $ prefix, add a link to search for it on DEX aggregators
                if token.startswith('$'):
                    links["explorer"] = f"https://etherscan.io/search?q={clean_token}"
        
        return links 
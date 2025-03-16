"""
Service for interacting with the Brian API for Web3 transactions.
"""
import logging
import os
import json
import httpx
from typing import Dict, Any, Optional, List, Union
from decimal import Decimal

from app.models.commands import SwapCommand
from app.utils.token_conversion import amount_to_smallest_units, smallest_units_to_amount

logger = logging.getLogger(__name__)

class BrianAPIService:
    """Service for interacting with the Brian API for Web3 transactions."""
    
    def __init__(self):
        """Initialize the Brian API service."""
        self.api_key = os.getenv("BRIAN_API_KEY")
        self.api_url = os.getenv("BRIAN_API_URL", "https://api.brianknows.org/api/v0")
        self.http_client = httpx.AsyncClient(verify=True, timeout=30.0)
        
        if not self.api_key:
            logger.warning("BRIAN_API_KEY environment variable not set. Brian API will not work.")
    
    async def get_swap_transaction(
        self,
        swap_command: SwapCommand,
        wallet_address: str,
        chain_id: int
    ) -> Dict[str, Any]:
        """
        Get a swap transaction from the Brian API.
        
        Args:
            swap_command: The swap command
            wallet_address: The wallet address
            chain_id: The chain ID
            
        Returns:
            Dictionary with transaction data
        """
        try:
            if not self.api_key:
                raise ValueError("BRIAN_API_KEY environment variable not set")
            
            # Extract token symbols
            token_in_symbol = swap_command.token_in["symbol"] if isinstance(swap_command.token_in, dict) else swap_command.token_in
            token_out_symbol = swap_command.token_out["symbol"] if isinstance(swap_command.token_out, dict) else swap_command.token_out
            
            # Construct the prompt for Brian API
            amount = swap_command.amount_in
            prompt = f"swap {amount} {token_in_symbol} for {token_out_symbol} on scroll"
            
            logger.info(f"Sending prompt to Brian API: {prompt}")
            
            # Call the Brian API
            response = await self.http_client.post(
                f"{self.api_url}/agent/transaction",
                headers={
                    "Content-Type": "application/json",
                    "x-brian-api-key": self.api_key
                },
                json={
                    "prompt": prompt,
                    "address": wallet_address,
                    "chainId": str(chain_id)
                }
            )
            
            # Check for errors
            try:
                response.raise_for_status()
                
                # Parse the response
                result = response.json()
            except httpx.HTTPStatusError as e:
                # Handle HTTP errors (4xx, 5xx)
                error_text = await e.response.text()
                logger.error(f"HTTP error from Brian API: {e.response.status_code} - {error_text}")
                raise ValueError(f"Error from Brian API: HTTP {e.response.status_code} - {error_text[:100]}")
            except json.JSONDecodeError as e:
                # Handle invalid JSON responses
                error_text = await response.text()
                logger.error(f"Invalid JSON response from Brian API: {error_text[:200]}")
                raise ValueError(f"Invalid JSON response from Brian API: {error_text[:100]}")
            logger.info(f"Brian API response: {json.dumps(result, indent=2)}")
            
            # Extract the transaction data
            if not result.get("result") or not isinstance(result["result"], list) or len(result["result"]) == 0:
                raise ValueError("No transaction data returned from Brian API")
            
            # Get the first transaction result
            tx_result = result["result"][0]
            
            # Extract the transaction steps
            steps = tx_result.get("data", {}).get("steps", [])
            if not steps:
                raise ValueError("No transaction steps returned from Brian API")
            
            # Format the transaction data for our system
            formatted_quotes = []
            
            # Process each step (there might be approval steps and swap steps)
            for step in steps:
                # Skip if missing required fields
                if not all(k in step for k in ["to", "data", "value"]):
                    continue
                
                # Determine if this is an approval or swap step
                is_approval = "approve" in step.get("data", "").lower()
                
                # Get metadata from the transaction result
                metadata = tx_result.get("data", {})
                
                # Create a quote object
                quote = {
                    "to": step["to"],
                    "data": step["data"],
                    "value": step["value"],
                    "gas": step.get("gasLimit", "500000"),
                    "aggregator": "brian",
                    "protocol": metadata.get("protocol", {}).get("name", "brian"),
                    "sell_amount": metadata.get("fromAmount", "0"),
                    "buy_amount": metadata.get("toAmount", "0"),
                    "price": metadata.get("toAmountUSD", "0"),
                    "gas_usd": "0",  # Brian API doesn't provide gas cost in USD
                    "is_approval": is_approval
                }
                
                formatted_quotes.append(quote)
            
            # Extract token information
            token_in_info = tx_result.get("data", {}).get("fromToken", {})
            token_out_info = tx_result.get("data", {}).get("toToken", {})
            
            # Return the formatted quotes and metadata
            return {
                "all_quotes": formatted_quotes,
                "quotes_count": len(formatted_quotes),
                "needs_approval": any(q.get("is_approval", False) for q in formatted_quotes),
                "token_to_approve": token_in_info.get("address") if any(q.get("is_approval", False) for q in formatted_quotes) else None,
                "spender": formatted_quotes[0].get("to") if any(q.get("is_approval", False) for q in formatted_quotes) else None,
                "pending_command": swap_command.natural_command,
                "metadata": {
                    "token_in_address": token_in_info.get("address"),
                    "token_in_symbol": token_in_info.get("symbol"),
                    "token_in_name": token_in_info.get("name"),
                    "token_in_verified": True,  # Assume verified since it's from Brian API
                    "token_in_source": "brian",
                    "token_out_address": token_out_info.get("address"),
                    "token_out_symbol": token_out_info.get("symbol"),
                    "token_out_name": token_out_info.get("name"),
                    "token_out_verified": True,  # Assume verified since it's from Brian API
                    "token_out_source": "brian",
                    "fromChainId": tx_result.get("data", {}).get("fromChainId"),
                    "toChainId": tx_result.get("data", {}).get("toChainId"),
                    "fromAmountUSD": tx_result.get("data", {}).get("fromAmountUSD"),
                    "toAmountUSD": tx_result.get("data", {}).get("toAmountUSD"),
                    "solver": tx_result.get("solver", "brian"),
                    "action": tx_result.get("action", "swap"),
                }
            }
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error from Brian API: {e.response.status_code} - {e.response.text}")
            raise ValueError(f"Error from Brian API: {e.response.text}")
        except Exception as e:
            logger.error(f"Error getting swap transaction from Brian API: {str(e)}")
            raise
    
    async def extract_parameters(self, prompt: str) -> Dict[str, Any]:
        """
        Extract parameters from a prompt using the Brian API.
        
        Args:
            prompt: The prompt to extract parameters from
            
        Returns:
            Dictionary with extracted parameters
        """
        try:
            if not self.api_key:
                raise ValueError("BRIAN_API_KEY environment variable not set")
            
            logger.info(f"Extracting parameters from prompt: {prompt}")
            
            # Call the Brian API
            response = await self.http_client.post(
                f"{self.api_url}/agent/parameters-extraction",
                headers={
                    "Content-Type": "application/json",
                    "x-brian-api-key": self.api_key
                },
                json={
                    "prompt": prompt
                }
            )
            
            # Check for errors
            try:
                response.raise_for_status()
                
                # Parse the response
                result = response.json()
                logger.info(f"Brian API parameter extraction response: {json.dumps(result, indent=2)}")
            except httpx.HTTPStatusError as e:
                # Handle HTTP errors (4xx, 5xx)
                error_text = await e.response.text()
                logger.error(f"HTTP error from Brian API: {e.response.status_code} - {error_text}")
                raise ValueError(f"Error from Brian API: HTTP {e.response.status_code} - {error_text[:100]}")
            except json.JSONDecodeError as e:
                # Handle invalid JSON responses
                error_text = await response.text()
                logger.error(f"Invalid JSON response from Brian API: {error_text[:200]}")
                raise ValueError(f"Invalid JSON response from Brian API: {error_text[:100]}")
            
            # Return the extracted parameters
            return result
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error from Brian API: {e.response.status_code} - {e.response.text}")
            raise ValueError(f"Error from Brian API: {e.response.text}")
        except Exception as e:
            logger.error(f"Error extracting parameters from Brian API: {str(e)}")
            raise
    
    async def get_token_info(self, token_symbol: str, chain_id: int) -> Dict[str, Any]:
        """
        Get token information from the Brian API.
        
        Args:
            token_symbol: The token symbol
            chain_id: The chain ID
            
        Returns:
            Dictionary with token information
        """
        try:
            if not self.api_key:
                raise ValueError("BRIAN_API_KEY environment variable not set")
            
            # Construct a prompt to get token information
            prompt = f"What is the address of {token_symbol} on chain {chain_id}?"
            
            logger.info(f"Getting token info from Brian API: {prompt}")
            
            # Call the Brian API
            response = await self.http_client.post(
                f"{self.api_url}/agent/knowledge",
                headers={
                    "Content-Type": "application/json",
                    "x-brian-api-key": self.api_key
                },
                json={
                    "prompt": prompt,
                    "kb": "public-knowledge-box"
                }
            )
            
            # Check for errors
            try:
                response.raise_for_status()
                
                # Parse the response
                result = response.json()
                logger.info(f"Brian API token info response: {json.dumps(result, indent=2)}")
            except httpx.HTTPStatusError as e:
                # Handle HTTP errors (4xx, 5xx)
                error_text = await e.response.text()
                logger.error(f"HTTP error from Brian API: {e.response.status_code} - {error_text}")
                raise ValueError(f"Error from Brian API: HTTP {e.response.status_code} - {error_text[:100]}")
            except json.JSONDecodeError as e:
                # Handle invalid JSON responses
                error_text = await response.text()
                logger.error(f"Invalid JSON response from Brian API: {error_text[:200]}")
                raise ValueError(f"Invalid JSON response from Brian API: {error_text[:100]}")
            
            # Extract token information from the response
            # This is a bit tricky as we need to parse the text response
            answer = result.get("answer", "")
            
            # Look for token address in the answer
            import re
            address_match = re.search(r'0x[a-fA-F0-9]{40}', answer)
            address = address_match.group(0) if address_match else None
            
            # Return the token information
            return {
                "address": address,
                "symbol": token_symbol,
                "name": token_symbol,  # We don't have the full name from this API call
                "chainId": chain_id
            }
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error from Brian API: {e.response.status_code} - {e.response.text}")
            raise ValueError(f"Error from Brian API: {e.response.text}")
        except Exception as e:
            logger.error(f"Error getting token info from Brian API: {str(e)}")
            raise

# Create a singleton instance
brian_service = BrianAPIService()

"""
Service for interacting with the Brian API for Web3 transactions.
"""
import logging
import os
import json
import httpx
from typing import Dict, Any, Optional, List, Union
from decimal import Decimal
from dotenv import load_dotenv

# Load environment variables from .env files
load_dotenv()
load_dotenv(".env.local", override=True)  # Override with .env.local if it exists

from app.models.commands import SwapCommand
from app.utils.token_conversion import amount_to_smallest_units, smallest_units_to_amount

logger = logging.getLogger(__name__)

class BrianAPIService:
    """Service for interacting with the Brian API for Web3 transactions."""
    
    def __init__(self):
        """Initialize the Brian API service."""
        self.api_key = os.getenv("BRIAN_API_KEY")
        self.api_url = os.getenv("BRIAN_API_URL", "https://api.brianknows.org/api/v0")
        
        # Check if SSL verification should be disabled for development
        self.verify_ssl = os.getenv("DISABLE_SSL_VERIFY", "").lower() not in ("true", "1", "yes")
        self.http_client = None  # Initialize as None, create when needed
        
        if not self.api_key:
            logger.warning("BRIAN_API_KEY environment variable not set. Brian API will not work.")
    
    async def _get_http_client(self) -> httpx.AsyncClient:
        """Get or create an HTTP client."""
        if self.http_client is None or self.http_client.is_closed:
            self.http_client = httpx.AsyncClient(
                verify=self.verify_ssl,
                timeout=30.0
            )
        return self.http_client
    
    async def _make_api_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make an API request to the Brian API."""
        try:
            url = f"{self.api_url}/{endpoint}"
            
            # Add API key to headers if available
            headers = kwargs.get("headers", {})
            if self.api_key:
                headers["x-brian-api-key"] = self.api_key
            kwargs["headers"] = headers
            
            # Set longer timeout for Brian API requests
            timeout = httpx.Timeout(60.0, connect=30.0)  # 60 seconds total, 30 seconds for connection
            
            async with httpx.AsyncClient(timeout=timeout, verify=self.verify_ssl) as client:
                try:
                    response = await client.request(method, url, **kwargs)
                    response.raise_for_status()
                    return response.json()
                except httpx.TimeoutException as e:
                    logger.error(f"Timeout connecting to Brian API: {str(e)}")
                    raise ValueError(f"Request to Brian API timed out. Please try again.")
                except httpx.HTTPStatusError as e:
                    error_text = e.response.text if hasattr(e.response, 'text') else str(e)
                    logger.error(f"HTTP error from Brian API: {error_text}")
                    raise ValueError(f"Error from Brian API: {error_text}")
                except httpx.RequestError as e:
                    logger.error(f"Network error connecting to Brian API: {str(e)}")
                    raise ValueError(f"Network error connecting to Brian API. Please check your connection.")
                
        except Exception as e:
            logger.error(f"Unexpected error in Brian API request: {str(e)}")
            if isinstance(e, ValueError):
                raise
            raise ValueError(f"Unexpected error in Brian API request: {str(e)}")
    
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
            response = await self._make_api_request(
                "POST",
                "agent/transaction",
                json={
                    "prompt": prompt,
                    "address": wallet_address,
                    "chainId": str(chain_id)
                }
            )

            logger.info(f"Brian API response: {json.dumps(response, indent=2)}")

            # Extract the transaction data
            if not response.get("result") or not isinstance(response["result"], list) or len(response["result"]) == 0:
                raise ValueError("No transaction data returned from Brian API")

            # Get the first transaction result
            tx_result = response["result"][0]

            # Extract the transaction steps
            steps = tx_result.get("data", {}).get("steps", [])
            if not steps:
                raise ValueError("No transaction steps returned from Brian API")

            # Format the transaction data for our system
            formatted_quotes = []

            # Process each step (there might be approval steps and swap steps)
            for step in steps:
                # Skip if missing required fields
                if any(k not in step for k in ["to", "data", "value"]):
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
            response = await self._make_api_request(
                "POST",
                "agent/parameters-extraction",
                json={
                    "prompt": prompt
                }
            )
            
            logger.info(f"Brian API parameter extraction response: {json.dumps(response, indent=2)}")
            
            # Return the extracted parameters
            return response
            
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
            response = await self._make_api_request(
                "POST",
                "agent/knowledge",
                json={
                    "prompt": prompt,
                    "kb": "public-knowledge-box"
                }
            )
            
            logger.info(f"Brian API token info response: {json.dumps(response, indent=2)}")
            
            # Extract token information from the response
            # This is a bit tricky as we need to parse the text response
            answer = response.get("answer", "")
            
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
            
        except Exception as e:
            logger.error(f"Error getting token info from Brian API: {str(e)}")
            raise
    
    async def get_transfer_transaction(
        self,
        token_symbol: str,
        amount: float,
        recipient_address: str,
        wallet_address: str,
        chain_id: int
    ) -> Dict[str, Any]:
        """
        Get a token transfer transaction from the Brian API.
        
        Args:
            token_symbol: The token symbol to transfer
            amount: The amount to transfer
            recipient_address: The recipient's wallet address
            wallet_address: The sender's wallet address
            chain_id: The chain ID
            
        Returns:
            Dictionary with transaction data
        """
        try:
            if not self.api_key:
                raise ValueError("BRIAN_API_KEY environment variable not set")
            
            # Construct the prompt for Brian API
            prompt = f"transfer {amount} {token_symbol} to {recipient_address}"
            
            logger.info(f"Sending transfer prompt to Brian API: {prompt}")
            
            # Call the Brian API
            response = await self._make_api_request(
                "POST",
                "agent/transaction",
                json={
                    "prompt": prompt,
                    "address": wallet_address,
                    "chainId": str(chain_id)
                }
            )
            
            logger.info(f"Brian API transfer response: {json.dumps(response, indent=2)}")
            
            # Extract the transaction data
            if not response.get("result") or not isinstance(response["result"], list) or len(response["result"]) == 0:
                raise ValueError("No transaction data returned from Brian API")
            
            # Get the first transaction result
            tx_result = response["result"][0]
            
            # Extract the transaction steps
            steps = tx_result.get("data", {}).get("steps", [])
            if not steps:
                raise ValueError("No transaction steps returned from Brian API")
            
            # Format the transaction data for our system
            formatted_tx = {
                "to": steps[0]["to"],
                "data": steps[0]["data"],
                "value": steps[0]["value"],
                "gas": steps[0].get("gasLimit", "500000"),
                "method": "transfer",
                "metadata": {
                    "token_symbol": token_symbol,
                    "amount": amount,
                    "recipient": recipient_address,
                    "chain_id": chain_id
                }
            }
            
            return formatted_tx
            
        except Exception as e:
            logger.error(f"Error getting transfer transaction from Brian API: {str(e)}")
            raise
    
    def _get_chain_name(self, chain_id: int) -> str:
        """Get the chain name for a given chain ID."""
        chain_names = {
            1: "ethereum",
            10: "optimism",
            56: "bsc",
            137: "polygon",
            42161: "arbitrum",
            8453: "base",
            534352: "scroll",
            43114: "avalanche"
        }
        return chain_names.get(chain_id, f"chain_{chain_id}")

    async def get_bridge_transaction(
        self,
        token_symbol: str,
        amount: float,
        from_chain_id: int,
        to_chain_id: int,
        wallet_address: str
    ) -> Dict[str, Any]:
        """
        Get a cross-chain bridge transaction from the Brian API.
        
        Args:
            token_symbol: The token symbol to bridge
            amount: The amount to bridge
            from_chain_id: The source chain ID
            to_chain_id: The destination chain ID
            wallet_address: The wallet address
            
        Returns:
            Dictionary with transaction data
        """
        try:
            if not self.api_key:
                raise ValueError("BRIAN_API_KEY environment variable not set")

            # Construct the prompt for Brian
            from_chain_name = self._get_chain_name(from_chain_id)
            to_chain_name = self._get_chain_name(to_chain_id)
            prompt = f"bridge {amount} {token_symbol} from {from_chain_name} to {to_chain_name}"
            
            logger.info(f"Sending bridge prompt to Brian API: {prompt}")
            
            # Make the API request
            response = await self._make_api_request(
                "POST",
                "agent/transaction",
                json={
                    "prompt": prompt,
                    "address": wallet_address,
                    "chainId": str(from_chain_id)
                }
            )
            
            logger.info(f"Brian API bridge response: {json.dumps(response, indent=2)}")
            
            # Extract the transaction data
            if not response.get("result") or not isinstance(response["result"], list) or len(response["result"]) == 0:
                raise ValueError("No transaction data returned from Brian API")
            
            # Get the first transaction result
            tx_result = response["result"][0]
            
            # Extract the transaction steps
            steps = tx_result.get("data", {}).get("steps", [])
            if not steps:
                raise ValueError("No transaction steps returned from Brian API")
            
            # Format the transaction data for our system
            formatted_quotes = []
            
            # Process each step
            for step in steps:
                # Skip if missing required fields
                if any(k not in step for k in ["to", "data", "value"]):
                    continue
                
                # Determine if this is an approval step
                is_approval = "approve" in step.get("data", "").lower()
                
                # Create a quote object
                quote = {
                    "to": step["to"],
                    "data": step["data"],
                    "value": step["value"],
                    "gas": step.get("gasLimit", "500000"),
                    "method": "bridge",
                    "protocol": tx_result.get("data", {}).get("protocol", {}).get("name", "brian"),
                    "is_approval": is_approval,
                    "from_chain": from_chain_name,
                    "to_chain": to_chain_name
                }
                
                formatted_quotes.append(quote)
            
            return {
                "all_quotes": formatted_quotes,
                "quotes_count": len(formatted_quotes),
                "needs_approval": any(q.get("is_approval", False) for q in formatted_quotes),
                "pending_command": prompt,
                "metadata": {
                    "token_symbol": token_symbol,
                    "amount": amount,
                    "from_chain_id": from_chain_id,
                    "to_chain_id": to_chain_id,
                    "from_chain_name": from_chain_name,
                    "to_chain_name": to_chain_name
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting bridge transaction from Brian API: {str(e)}")
            raise
    
    async def get_token_balances(
        self,
        wallet_address: str,
        chain_id: int,
        token_symbol: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get token balances from the Brian API.
        
        Args:
            wallet_address: The wallet address
            chain_id: The chain ID
            token_symbol: Optional specific token to check
            
        Returns:
            Dictionary with balance information
        """
        try:
            if not self.api_key:
                raise ValueError("BRIAN_API_KEY environment variable not set")

            # Construct the prompt for Brian API
            prompt = "check balance"
            if token_symbol:
                prompt += f" of {token_symbol}"

            # Get chain name for better prompts
            chain_names = {
                1: "ethereum",
                10: "optimism",
                56: "bsc",
                137: "polygon",
                42161: "arbitrum",
                8453: "base",
                534352: "scroll",
                43114: "avalanche"
            }

            chain_name = chain_names.get(chain_id, f"chain {chain_id}")
            prompt += f" on {chain_name}"

            logger.info(f"Sending balance prompt to Brian API: {prompt}")

            # Call the Brian API
            response = await self._make_api_request(
                "POST",
                "agent/knowledge",
                json={
                    "prompt": prompt,
                    "address": wallet_address,
                    "chainId": str(chain_id),
                    "kb": "public-knowledge-box"
                }
            )

            logger.info(f"Brian API balance response: {json.dumps(response, indent=2)}")

            # Extract the balance information
            answer = response.get("answer", "")

            # Return the balance information
            return {
                "answer": answer,
                "wallet_address": wallet_address,
                "chain_id": chain_id,
                "token_symbol": token_symbol,
                "chain_name": chain_name
            }

        except Exception as e:
            logger.error(f"Error getting token balances from Brian API: {str(e)}")
            raise
    
    async def cleanup(self):
        """Cleanup resources when service is no longer needed."""
        if self.http_client and not self.http_client.is_closed:
            await self.http_client.aclose()
            self.http_client = None

# Create a singleton instance
brian_service = BrianAPIService()

# Register cleanup on module unload
import atexit
import asyncio

def cleanup_brian_service():
    """Cleanup the Brian service when the module is unloaded."""
    if brian_service.http_client and not brian_service.http_client.is_closed:
        try:
            loop = asyncio.get_event_loop()
            if not loop.is_closed():
                loop.run_until_complete(brian_service.cleanup())
        except Exception as e:
            logger.error(f"Error cleaning up Brian service: {e}")

atexit.register(cleanup_brian_service)

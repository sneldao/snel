"""
Shared Brian API utilities for DRY principle.
Common patterns for Brian API calls and response handling.
"""
import json
import httpx
from typing import Dict, Any, Optional
from app.utils.chain_utils import ChainRegistry
import logging

logger = logging.getLogger(__name__)


class BrianAPIError(Exception):
    """Exception for Brian API errors."""
    pass


class BrianAPIUtils:
    """Shared utilities for Brian API interactions."""
    
    @staticmethod
    def validate_wallet_address(wallet_address: str) -> None:
        """Validate wallet address and raise error if invalid."""
        if not wallet_address or wallet_address.strip() == "":
            raise BrianAPIError("Wallet address is required. Please connect your wallet.")
    
    @staticmethod
    def format_request_payload(prompt: str, chain_id: int, wallet_address: str) -> Dict[str, Any]:
        """Format standard Brian API request payload."""
        BrianAPIUtils.validate_wallet_address(wallet_address)
        
        return {
            "prompt": prompt,
            "chainId": str(chain_id),  # Brian expects string
            "address": wallet_address
        }
    
    @staticmethod
    def log_request(operation: str, prompt: str, chain_id: int, wallet_address: str) -> None:
        """Log Brian API request details."""
        chain_name = ChainRegistry.get_chain_name(chain_id)
        logger.info(f"Calling Brian API for {operation} with: {prompt}")
        logger.info(f"Chain: {chain_id} ({chain_name}), Wallet: {wallet_address}")
    
    @staticmethod
    def handle_http_error(response: httpx.Response, operation: str) -> Dict[str, Any]:
        """Handle HTTP errors from Brian API with user-friendly messages."""
        status_code = response.status_code
        response_text = response.text
        
        logger.error(f"Brian API {status_code} error for {operation}: {response_text}")
        
        if status_code == 404:
            return {
                "error": "user_friendly",
                "message": f"This {operation} is not available at the moment. Please check your parameters and try again.",
                "technical_details": f"Brian API returned 404: {response_text}"
            }
        elif status_code == 400:
            return {
                "error": "user_friendly",
                "message": f"Invalid {operation} parameters. Please check your input and try again.",
                "technical_details": f"Brian API returned 400: {response_text}"
            }
        elif status_code == 429:
            return {
                "error": "user_friendly",
                "message": "Too many requests. Please wait a moment and try again.",
                "technical_details": f"Brian API returned 429: {response_text}"
            }
        elif status_code >= 500:
            return {
                "error": "user_friendly",
                "message": f"The {operation} service is temporarily unavailable. Please try again later.",
                "technical_details": f"Brian API returned {status_code}: {response_text}"
            }
        else:
            return {
                "error": "user_friendly",
                "message": f"Unable to process {operation}. Please try again.",
                "technical_details": f"Brian API returned {status_code}: {response_text}"
            }
    
    @staticmethod
    def handle_timeout_error(operation: str) -> Dict[str, Any]:
        """Handle timeout errors from Brian API."""
        logger.error(f"Brian API timeout for {operation}")
        return {
            "error": "user_friendly",
            "message": f"The {operation} service is taking too long to respond. Please try again.",
            "technical_details": "Brian API timeout"
        }
    
    @staticmethod
    def handle_connection_error(operation: str, error: Exception) -> Dict[str, Any]:
        """Handle connection errors from Brian API."""
        logger.error(f"Error calling Brian API for {operation}: {str(error)}")
        return {
            "error": "user_friendly",
            "message": f"Unable to connect to {operation} service. Please try again later.",
            "technical_details": str(error)
        }
    
    @staticmethod
    def validate_response_data(data: Dict[str, Any], operation: str) -> Dict[str, Any]:
        """Validate Brian API response data."""
        if not data.get("result") or len(data["result"]) == 0:
            logger.warning(f"Brian API returned no {operation} results")
            return {
                "error": "user_friendly",
                "message": f"Unable to create {operation} transaction. Please check your parameters.",
                "technical_details": "Brian API returned no results"
            }
        
        # Extract the relevant transaction data
        transaction = data["result"][0]
        transaction_data = transaction.get("data", {})
        
        steps = transaction_data.get("steps", [])
        if not steps:
            logger.warning(f"Brian API returned no {operation} steps")
            return {
                "error": "user_friendly",
                "message": f"No valid {operation} route found. Please check your parameters.",
                "technical_details": "Brian API returned no steps"
            }
        
        return {"success": True, "transaction": transaction, "transaction_data": transaction_data}
    
    @staticmethod
    def format_success_response(
        transaction: Dict[str, Any],
        transaction_data: Dict[str, Any],
        operation: str
    ) -> Dict[str, Any]:
        """Format successful Brian API response."""
        steps = transaction_data.get("steps", [])
        solver = transaction.get("solver", "")
        
        # Get protocol information
        protocol = {
            "name": solver or transaction_data.get("protocol", {}).get("name", "brian")
        }
        
        # Extract token information
        from_token = transaction_data.get("fromToken", {})
        to_token = transaction_data.get("toToken", {})
        
        return {
            "success": True,
            "steps": steps,
            "protocol": protocol,
            "solver": solver,
            "description": transaction.get("description", f"{operation.title()} transaction"),
            "gasCostUSD": transaction_data.get("gasCostUSD"),
            "fromToken": from_token.get("symbol", ""),
            "toToken": to_token.get("symbol", ""),
            "fromAmount": transaction_data.get("fromAmount", ""),
            "toAmount": transaction_data.get("toAmount", ""),
            "fromChainId": transaction_data.get("fromChainId"),
            "toChainId": transaction_data.get("toChainId"),
            "metadata": {
                "gas_cost_usd": transaction_data.get("gasCostUSD"),
                "from_amount_usd": transaction_data.get("fromAmountUSD"),
                "to_amount_usd": transaction_data.get("toAmountUSD"),
                "protocol": protocol,
                "description": transaction_data.get("description", ""),
                "full_response": transaction_data  # For debugging
            }
        }
    
    @staticmethod
    async def make_brian_api_call(
        base_url: str,
        headers: Dict[str, str],
        prompt: str,
        chain_id: int,
        wallet_address: str,
        operation: str,
        timeout: float = 30.0
    ) -> Dict[str, Any]:
        """
        Make a standardized Brian API call with error handling.
        
        Args:
            base_url: Brian API base URL
            headers: Request headers
            prompt: The prompt to send to Brian
            chain_id: Blockchain network ID
            wallet_address: User's wallet address
            operation: Operation type (for logging/errors)
            timeout: Request timeout in seconds
            
        Returns:
            Standardized response dictionary
        """
        try:
            # Log the request
            BrianAPIUtils.log_request(operation, prompt, chain_id, wallet_address)
            
            # Prepare request payload
            request_payload = BrianAPIUtils.format_request_payload(prompt, chain_id, wallet_address)
            logger.info(f"Request payload: {json.dumps(request_payload, indent=2)}")
            
            # Make the API call
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{base_url}/agent/transaction",
                    headers=headers,
                    json=request_payload,
                    timeout=timeout
                )
                
                # Handle HTTP errors
                if response.status_code != 200:
                    return BrianAPIUtils.handle_http_error(response, operation)
                
                # Parse response
                data = response.json()
                logger.info(f"Brian API {operation} response: {json.dumps(data, indent=2)}")
                
                # Validate response data
                validation_result = BrianAPIUtils.validate_response_data(data, operation)
                if "error" in validation_result:
                    return validation_result
                
                # Format success response
                return BrianAPIUtils.format_success_response(
                    validation_result["transaction"],
                    validation_result["transaction_data"],
                    operation
                )
                
        except httpx.TimeoutException:
            return BrianAPIUtils.handle_timeout_error(operation)
        except Exception as e:
            return BrianAPIUtils.handle_connection_error(operation, e)

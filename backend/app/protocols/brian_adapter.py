"""
Brian Protocol adapter implementation.
"""
import os
import httpx
import json
import logging
from decimal import Decimal
from typing import Dict, Any, List
from app.models.token import TokenInfo

logger = logging.getLogger(__name__)

class BrianAdapter:
    """Brian Protocol adapter."""

    # Chain name mapping
    CHAIN_NAMES = {
        1: "ethereum",
        10: "optimism",
        56: "bsc",
        137: "polygon",
        42161: "arbitrum",
        8453: "base",
        43114: "avalanche",
        59144: "linea",
        324: "zksync",
        534352: "scroll"
    }

    # Supported chains
    SUPPORTED_CHAINS = list(CHAIN_NAMES.keys())

    def __init__(self):
        """Initialize the Brian protocol adapter."""
        self.api_key = os.getenv("BRIAN_API_KEY")
        self.api_url = os.getenv("BRIAN_API_URL", "https://api.brianknows.org/api/v0")

        if not self.api_key:
            raise ValueError("BRIAN_API_KEY environment variable not set")

        self.http_client = None

    @property
    def protocol_id(self) -> str:
        return "brian"

    @property
    def name(self) -> str:
        return "Brian Protocol"

    @property
    def supported_chains(self) -> List[int]:
        """List of supported chain IDs."""
        return self.SUPPORTED_CHAINS

    def is_supported(self, chain_id: int) -> bool:
        """Check if this protocol supports the given chain."""
        return chain_id in self.supported_chains

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self.http_client is None or self.http_client.is_closed:
            self.http_client = httpx.AsyncClient(
                timeout=30.0,
                headers={
                    "x-brian-api-key": self.api_key,
                    "Content-Type": "application/json"
                }
            )
        return self.http_client

    async def close(self):
        """Close HTTP client."""
        if self.http_client and not self.http_client.is_closed:
            await self.http_client.aclose()

    def get_chain_name(self, chain_id: int) -> str:
        """Get human-readable chain name."""
        return self.CHAIN_NAMES.get(chain_id, f"chain{chain_id}")

    async def get_quote(
        self,
        from_token: TokenInfo,
        to_token: TokenInfo,
        amount: Decimal,
        chain_id: int,
        wallet_address: str,
        to_chain_id: int = None,
    ) -> Dict[str, Any]:
        """Get swap quote from Brian API."""
        if not self.is_supported(chain_id):
            raise ValueError(f"Chain {chain_id} not supported by Brian protocol")

        # Get token addresses for this chain
        from_address = from_token.get_address(chain_id)
        to_address = to_token.get_address(chain_id)

        if not from_address or not to_address:
            raise ValueError(f"One or both tokens not supported on chain {chain_id}")

        client = await self._get_client()
        chain_name = self.get_chain_name(chain_id)

        # Use proper token symbols in the prompt
        from_symbol = from_token.symbol
        to_symbol = to_token.symbol

        # Format the prompt using chain name
        prompt = f"swap {float(amount)} {from_symbol} for {to_symbol} on {chain_name}"

        logger.info(f"Calling Brian API with: {prompt}, chain_id: {chain_id}")

        try:
            response = await client.post(
                f"{self.api_url}/agent/transaction",
                json={
                    "prompt": prompt,
                    "chainId": str(chain_id),  # Brian expects string
                    "address": wallet_address
                }
            )

            # Handle common error cases
            if response.status_code == 404:
                logger.error(f"Brian API 404 error: {response.text}")
                raise ValueError("This swap pair is not available at the moment.")

            if response.status_code == 400:
                logger.error(f"Brian API 400 error: {response.text}")
                raise ValueError("Invalid swap parameters. Please check your token symbols.")

            if response.status_code != 200:
                logger.error(f"Brian API error {response.status_code}: {response.text}")
                raise ValueError("The swap service is temporarily unavailable.")

            data = response.json()
            logger.debug(f"Brian API response: {json.dumps(data, indent=2)}")

            # Check if we got a valid result
            if not data.get("result") or not data["result"]:
                logger.error("Brian API returned empty result")
                error_message = data.get("error", {}).get("message", "Unable to find a valid swap route.")
                if "not supported" in error_message.lower():
                    raise ValueError(f"This token pair is not supported on {self.get_chain_name(chain_id)}.")
                elif "insufficient liquidity" in error_message.lower():
                    raise ValueError(f"Insufficient liquidity for this swap on {self.get_chain_name(chain_id)}.")
                elif "slippage" in error_message.lower():
                    raise ValueError(f"Slippage too high for this swap. Try a smaller amount.")
                else:
                    raise ValueError(f"Unable to find a valid swap route: {error_message}")

            # Extract transaction data
            transaction = data["result"][0]
            transaction_data = transaction.get("data", {})
            steps = transaction_data.get("steps", [])

            if not steps:
                logger.error("Brian API returned no steps")
                raise ValueError("No valid swap route found.")

            # Get protocol information
            solver = transaction.get("solver", "")
            protocol_name = solver or transaction_data.get("protocol", {}).get("name", "brian")

            # Extract token information directly from Brian's response
            from_token_data = transaction_data.get("fromToken", {})
            to_token_data = transaction_data.get("toToken", {})

            # Use Brian's token information directly - no need for additional lookups
            from_address = from_token_data.get("address", "")
            to_address = to_token_data.get("address", "")

            # Brian provides complete token info, use it directly
            from_token_info = {
                "address": from_address,
                "symbol": from_token_data.get("symbol", from_token.symbol),
                "decimals": from_token_data.get("decimals", from_token.decimals),
                "name": from_token_data.get("name", from_token.name)
            }

            to_token_info = {
                "address": to_address,
                "symbol": to_token_data.get("symbol", to_token.symbol),
                "decimals": to_token_data.get("decimals", to_token.decimals),
                "name": to_token_data.get("name", to_token.name)
            }

            # Format response in standardized format
            # Check if this is a multi-step transaction
            is_multi_step = len(steps) > 1

            if is_multi_step:
                # Format steps for backend compatibility
                formatted_steps = []
                for step in steps:
                    formatted_steps.append({
                        "to": step.get("to", ""),
                        "data": step.get("data", ""),
                        "value": step.get("value", "0"),
                        "gasLimit": step.get("gasLimit", "500000"),
                        "chainId": chain_id
                    })

                # For multi-step transactions, return flow information
                return {
                    "success": True,
                    "protocol": "brian",
                    "requires_multi_step": True,
                    "total_steps": len(steps),
                    "current_step": 1,
                    "step_type": "approval" if len(steps) > 1 else "swap",
                    "steps": formatted_steps,  # Add formatted steps for backend
                    "transaction": {
                        "to": steps[0].get("to", ""),
                        "data": steps[0].get("data", ""),
                        "value": steps[0].get("value", "0"),
                        "chainId": chain_id,
                        "gasLimit": steps[0].get("gasLimit", "500000"),
                        "method": "approval" if len(steps) > 1 else "swap"
                    },
                    "flow_info": {
                        "current_step": 1,
                        "total_steps": len(steps),
                        "step_type": "approval" if len(steps) > 1 else "swap",
                        "operation_type": "swap"
                    },
                    "metadata": {
                        "gas_cost_usd": transaction_data.get("gasCostUSD"),
                        "from_amount_usd": transaction_data.get("fromAmountUSD"),
                        "to_amount_usd": transaction_data.get("toAmountUSD"),
                        "to_amount_min": transaction_data.get("toAmountMin"),
                        "source": protocol_name,
                        "description": transaction_data.get("description", ""),
                        "from_token": from_token_info,
                        "to_token": to_token_info,
                        "all_steps": steps,  # Include all steps in metadata
                        "brian_response": transaction_data  # Include full Brian response for debugging
                    }
                }
            else:
                # Single step transaction
                return {
                    "success": True,
                    "protocol": "brian",
                    "requires_multi_step": False,
                    "total_steps": 1,
                    "transaction": {
                        "to": steps[0].get("to", ""),
                        "data": steps[0].get("data", ""),
                        "value": steps[0].get("value", "0"),
                        "chainId": chain_id,
                        "gasLimit": steps[0].get("gasLimit", "500000"),
                        "method": "swap"
                    },
                    "metadata": {
                        "gas_cost_usd": transaction_data.get("gasCostUSD"),
                        "from_amount_usd": transaction_data.get("fromAmountUSD"),
                        "to_amount_usd": transaction_data.get("toAmountUSD"),
                        "to_amount_min": transaction_data.get("toAmountMin"),
                        "source": protocol_name,
                        "description": transaction_data.get("description", ""),
                        "from_token": from_token_info,
                        "to_token": to_token_info,
                        "brian_response": transaction_data  # Include full Brian response for debugging
                    }
                }

        except httpx.TimeoutException:
            logger.error("Brian API timeout")
            raise ValueError("The request took too long to process.")

        except httpx.RequestError as e:
            logger.error(f"Brian API request error: {str(e)}")
            raise ValueError("Unable to connect to the swap service.")

        except json.JSONDecodeError:
            logger.error("Brian API JSON decode error")
            raise ValueError("Received invalid response from the swap service.")

        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            raise ValueError(f"An unexpected error occurred: {str(e)}")

    async def build_transaction(
        self,
        quote: Dict[str, Any],
        chain_id: int,
    ) -> Dict[str, Any]:
        """Build transaction from quote."""
        # Brian quotes include transaction data either in 'transaction' field (single-step)
        # or in 'steps' array (multi-step)

        if "transaction" in quote:
            # Single-step transaction
            tx_data = quote["transaction"]
        elif "steps" in quote and quote["steps"]:
            # Multi-step transaction - use first step
            tx_data = quote["steps"][0]
        else:
            raise ValueError("Invalid quote format - missing transaction data")

        return {
            "to": tx_data.get("to", ""),
            "data": tx_data.get("data", ""),
            "value": tx_data.get("value", "0"),
            "gas_limit": tx_data.get("gasLimit", "500000"),
            "chainId": chain_id
        }
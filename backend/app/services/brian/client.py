"""
Brian API client implementation.
"""
from typing import Dict, Any, Optional
import httpx
from fastapi import HTTPException
import os
import json

class BrianClient:
    def __init__(self):
        self.api_key = os.getenv("BRIAN_API_KEY")
        if not self.api_key:
            raise ValueError("BRIAN_API_KEY environment variable is not set")

        self.base_url = "https://api.brianknows.org/api/v0"
        self.headers = {
            "x-brian-api-key": self.api_key,
            "Content-Type": "application/json"
        }

    async def get_bridge_transaction(self, token: str, amount: float, from_chain_id: int, to_chain_id: int, wallet_address: str) -> Dict[str, Any]:
        """Get a bridge transaction from Brian API."""
        try:
            # Map chain_ids to chain names
            from_chain_name = self._get_chain_name(from_chain_id)
            to_chain_name = self._get_chain_name(to_chain_id)

            # Format the prompt for bridging - match Brian API examples exactly
            # Example from docs: "I want to bridge 10 USDC from Ethereum to Arbitrum"
            prompt = f"I want to bridge {amount} {token} from {from_chain_name} to {to_chain_name}"

            # Validate wallet address
            if not wallet_address or wallet_address.strip() == "":
                print("ERROR: Wallet address is empty or None")
                return {
                    "error": "user_friendly",
                    "message": "Wallet address is required for bridging. Please connect your wallet.",
                    "technical_details": "Empty wallet address provided"
                }

            print(f"Calling Brian API for bridge with: {prompt}")
            print(f"From chain: {from_chain_id} ({from_chain_name}), To chain: {to_chain_id} ({to_chain_name})")
            print(f"Wallet address: {wallet_address}")

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/agent/transaction",
                    headers=self.headers,
                    json={
                        "prompt": prompt,
                        "chainId": str(from_chain_id),  # Brian expects string, use source chain
                        "address": wallet_address
                    },
                    timeout=30.0
                )

                if response.status_code == 404:
                    print(f"Brian API 404 error for bridge: {response.text}")
                    return {
                        "error": "user_friendly",
                        "message": "This bridge route is not available at the moment. Please try a different token or amount.",
                        "technical_details": f"Brian API returned 404: {response.text}"
                    }

                if response.status_code == 400:
                    print(f"Brian API 400 error for bridge: {response.text}")
                    return {
                        "error": "user_friendly",
                        "message": "Invalid bridge parameters. Please check your token and chain selection.",
                        "technical_details": f"Brian API returned 400: {response.text}"
                    }

                if response.status_code != 200:
                    print(f"Brian API error {response.status_code} for bridge: {response.text}")
                    return {
                        "error": "user_friendly",
                        "message": "The bridge service is temporarily unavailable. Please try again later.",
                        "technical_details": f"Brian API returned {response.status_code}: {response.text}"
                    }

                data = response.json()
                print(f"Brian API bridge response: {json.dumps(data, indent=2)}")

                if not data.get("result") or len(data["result"]) == 0:
                    print("Brian API returned no bridge results")
                    return {
                        "error": "user_friendly",
                        "message": "No bridge route found for this token pair. Please try a different amount or token.",
                        "technical_details": "Brian API returned no results"
                    }

                # Extract the relevant transaction data
                transaction = data["result"][0]
                transaction_data = transaction.get("data", {})

                steps = transaction_data.get("steps", [])

                if not steps:
                    print("Brian API returned no bridge steps")
                    return {
                        "error": "user_friendly",
                        "message": "No valid bridge route found. Please try a different amount or token.",
                        "technical_details": "Brian API returned no steps"
                    }

                # Get protocol information
                solver = transaction.get("solver", "")
                protocol = {
                    "name": solver or transaction_data.get("protocol", {}).get("name", "brian")
                }

                # Return the transaction data in the expected format
                return {
                    "steps": steps,
                    "protocol": protocol,
                    "solver": solver,
                    "description": transaction.get("description", f"Bridge {amount} {token}"),
                    "gasCostUSD": transaction_data.get("gasCostUSD"),
                    "fromToken": token,
                    "toToken": token,  # Same token on destination chain
                    "fromAmount": str(amount),
                    "fromChainId": from_chain_id,
                    "toChainId": to_chain_id
                }

        except httpx.TimeoutException:
            print("Brian API timeout for bridge")
            return {
                "error": "user_friendly",
                "message": "The bridge service is taking too long to respond. Please try again.",
                "technical_details": "Brian API timeout"
            }
        except Exception as e:
            print(f"Error calling Brian API for bridge: {str(e)}")
            return {
                "error": "user_friendly",
                "message": "Unable to connect to bridge service. Please try again later.",
                "technical_details": str(e)
            }

    async def get_swap_transaction(self, from_token: str, to_token: str, amount: float, chain_id: int, wallet_address: str) -> Dict[str, Any]:
        """Get a swap transaction from Brian API."""
        try:
            # Map chain_id to chain name
            chain_name = self._get_chain_name(chain_id)

            # Format the prompt according to Brian's examples
            prompt = f"swap {amount} {from_token} for {to_token} on {chain_name}"

            print(f"Calling Brian API with: {prompt}, chain_id: {chain_id}, address: {wallet_address}")
            print(f"Token addresses - from: {from_token}, to: {to_token}")

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/agent/transaction",
                    headers=self.headers,
                    json={
                        "prompt": prompt,
                        "chainId": str(chain_id),  # Brian expects string
                        "address": wallet_address
                    },
                    timeout=30.0  # Increased timeout for reliability
                )

                if response.status_code == 404:
                    print(f"Brian API 404 error: {response.text}")
                    return {
                        "error": "user_friendly",
                        "message": "This swap pair is not available at the moment. Please try a different pair or amount.",
                        "technical_details": f"Brian API returned 404: {response.text}"
                    }

                if response.status_code == 400:
                    print(f"Brian API 400 error: {response.text}")
                    return {
                        "error": "user_friendly",
                        "message": "Invalid swap parameters. Please check your token symbols and try again.",
                        "technical_details": f"Brian API returned 400: {response.text}"
                    }

                if response.status_code != 200:
                    print(f"Brian API error {response.status_code}: {response.text}")
                    return {
                        "error": "user_friendly",
                        "message": "The swap service is temporarily unavailable. Please try again later.",
                        "technical_details": f"Brian API returned {response.status_code}: {response.text}"
                    }

                data = response.json()
                print(f"Brian API response: {json.dumps(data, indent=2)}")

                # Check if we got a valid result
                if not data.get("result") or not data["result"]:
                    print("Brian API returned empty result")
                    return {
                        "error": "user_friendly",
                        "message": "Unable to find a valid swap route. Please try a different amount or token pair.",
                        "technical_details": "Brian API returned empty result"
                    }

                # Extract the relevant transaction data
                transaction = data["result"][0]
                transaction_data = transaction.get("data", {})

                steps = transaction_data.get("steps", [])

                if not steps:
                    print("Brian API returned no steps")
                    return {
                        "error": "user_friendly",
                        "message": "No valid swap route found. Please try a different amount or token pair.",
                        "technical_details": "Brian API returned no steps"
                    }

                # Get protocol information
                solver = transaction.get("solver", "")
                protocol = {
                    "name": solver or transaction_data.get("protocol", {}).get("name", "brian")
                }

                # Return formatted transaction data
                return {
                    "success": True,
                    "steps": steps,
                    "metadata": {
                        "gas_cost_usd": transaction_data.get("gasCostUSD"),
                        "from_amount_usd": transaction_data.get("fromAmountUSD"),
                        "to_amount_usd": transaction_data.get("toAmountUSD"),
                        "to_amount_min": transaction_data.get("toAmountMin"),
                        "protocol": protocol,
                        "description": transaction_data.get("description", "")
                    }
                }

        except httpx.TimeoutException:
            return {
                "error": "user_friendly",
                "message": "The request took too long to process. Please try again.",
                "technical_details": "Request timeout"
            }
        except httpx.RequestError as e:
            return {
                "error": "user_friendly",
                "message": "Unable to connect to the swap service. Please try again later.",
                "technical_details": f"Request error: {str(e)}"
            }
        except json.JSONDecodeError:
            return {
                "error": "user_friendly",
                "message": "Received invalid response from the swap service. Please try again.",
                "technical_details": "JSON decode error"
            }
        except Exception as e:
            return {
                "error": "user_friendly",
                "message": "An unexpected error occurred. Please try again later.",
                "technical_details": f"Unexpected error: {str(e)}"
            }

    def _get_chain_name(self, chain_id: int) -> str:
        """Map chain ID to a human-readable chain name."""
        chain_map = {
            1: "Ethereum",  # Capitalize to match Brian API examples
            10: "Optimism",
            56: "BSC",
            137: "Polygon",
            42161: "Arbitrum",  # Match Brian API examples exactly
            8453: "Base",
            43114: "Avalanche",
            59144: "Linea",
            324: "ZK Sync",
            534352: "Scroll"
        }
        return chain_map.get(chain_id, f"chain{chain_id}")

# Global instance
brian_client = BrianClient()
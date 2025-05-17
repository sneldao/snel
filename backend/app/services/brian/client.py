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
        return chain_map.get(chain_id, f"chain{chain_id}")

# Global instance
brian_client = BrianClient() 
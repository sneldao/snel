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
            # Format the prompt according to Brian's examples
            prompt = f"swap {amount} {from_token} for {to_token}"
            
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
                    return {
                        "error": "user_friendly",
                        "message": "This swap pair is not available at the moment. Please try a different pair or amount.",
                        "technical_details": f"Brian API returned 404: {response.text}"
                    }
                
                if response.status_code == 400:
                    return {
                        "error": "user_friendly",
                        "message": "Invalid swap parameters. Please check your token symbols and try again.",
                        "technical_details": f"Brian API returned 400: {response.text}"
                    }

                if response.status_code != 200:
                    return {
                        "error": "user_friendly",
                        "message": "The swap service is temporarily unavailable. Please try again later.",
                        "technical_details": f"Brian API returned {response.status_code}: {response.text}"
                    }

                data = response.json()
                
                # Check if we got a valid result
                if not data.get("result") or not data["result"]:
                    return {
                        "error": "user_friendly",
                        "message": "Unable to find a valid swap route. Please try a different amount or token pair.",
                        "technical_details": "Brian API returned empty result"
                    }

                # Extract the relevant transaction data
                transaction = data["result"][0]
                steps = transaction.get("data", {}).get("steps", [])
                
                if not steps:
                    return {
                        "error": "user_friendly",
                        "message": "No valid swap route found. Please try a different amount or token pair.",
                        "technical_details": "Brian API returned no steps"
                    }

                # Return formatted transaction data
                return {
                    "success": True,
                    "steps": steps,
                    "metadata": {
                        "gas_cost_usd": transaction["data"].get("gasCostUSD"),
                        "from_amount_usd": transaction["data"].get("fromAmountUSD"),
                        "to_amount_usd": transaction["data"].get("toAmountUSD"),
                        "to_amount_min": transaction["data"].get("toAmountMin"),
                        "protocol": transaction["data"].get("protocol", {}).get("name")
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

# Global instance
brian_client = BrianClient() 
"""
Brian API client implementation.
"""
from typing import Dict, Any, Optional
import httpx
from fastapi import HTTPException
import os
import json
from app.utils.chain_utils import ChainRegistry
from app.utils.brian_api_utils import BrianAPIUtils

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

            # Format the prompt for bridging - use exact format from Brian API docs
            # Documentation example: "I want to bridge 10 USDC from Ethereum to Arbitrum"

            # Try different prompt formats based on Brian API examples
            # First, let's try with more standard amounts and see if very small amounts are the issue
            if float(amount) < 0.001:
                # For very small amounts, suggest a larger amount
                return {
                    "error": "user_friendly",
                    "message": f"Amount {amount} {token.upper()} is too small for bridging. Please try an amount of at least 0.001 {token.upper()}.",
                    "technical_details": f"Amount {amount} below minimum bridge threshold"
                }

            # Use exact chain names that Brian expects
            # Based on documentation, try different chain name formats
            chain_name_mapping = {
                "Base": "Base",
                "Arbitrum": "Arbitrum",
                "Scroll": "Scroll",
                "Optimism": "Optimism",
                "Ethereum": "Ethereum",
                "Polygon": "Polygon"
            }

            # Try alternative names if the standard ones don't work
            from_chain_alt = chain_name_mapping.get(from_chain_name, from_chain_name)
            to_chain_alt = chain_name_mapping.get(to_chain_name, to_chain_name)

            # Try multiple prompt formats - Brian API can be sensitive to exact wording
            prompt_variations = [
                f"I want to bridge {amount} {token.upper()} from {from_chain_alt} to {to_chain_alt}",
                f"bridge {amount} {token.upper()} from {from_chain_alt} to {to_chain_alt}",
                f"Bridge {amount} {token} from {from_chain_alt} to {to_chain_alt}",
            ]

            # Start with the first prompt format (matches documentation)
            prompt = prompt_variations[0]

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

            # Prepare request payload
            request_payload = {
                "prompt": prompt,
                "chainId": str(from_chain_id),  # Brian expects string, use source chain
                "address": wallet_address
            }
            print(f"Request payload: {json.dumps(request_payload, indent=2)}")

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/agent/transaction",
                    headers=self.headers,
                    json=request_payload,
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

                if response.status_code == 500:
                    print(f"Brian API 500 error for bridge: {response.text}")
                    # Check if it's a token-specific issue
                    if token.upper() != "ETH":
                        return {
                            "error": "user_friendly",
                            "message": f"Bridge for {token.upper()} is not currently supported. We currently support ETH bridging. Please try bridging ETH instead.",
                            "technical_details": f"Brian API returned 500: {response.text}"
                        }
                    else:
                        return {
                            "error": "user_friendly",
                            "message": f"Bridge from {from_chain_name} to {to_chain_name} is not currently supported. Please try a different route.",
                            "technical_details": f"Brian API returned 500: {response.text}"
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

    async def get_transfer_transaction(self, token: str, amount: float, to_address: str, chain_id: int, wallet_address: str) -> Dict[str, Any]:
        """Get a transfer transaction from Brian API."""
        # Format the prompt according to Brian's examples
        chain_name = ChainRegistry.get_chain_name(chain_id)
        prompt = f"transfer {amount} {token} to {to_address} on {chain_name}"

        # Use shared Brian API utilities
        result = await BrianAPIUtils.make_brian_api_call(
            base_url=self.base_url,
            headers=self.headers,
            prompt=prompt,
            chain_id=chain_id,
            wallet_address=wallet_address,
            operation="transfer",
            timeout=30.0
        )

        # Add transfer-specific fields to successful responses
        if result.get("success"):
            result.update({
                "toAddress": to_address,
                "fromChainId": chain_id,
                "toChainId": chain_id,  # Same chain for transfers
            })

        return result

    async def get_balance(
        self,
        wallet_address: str,
        chain_id: int,
        token: str = None
    ) -> Dict[str, Any]:
        """
        Get wallet balance using Brian API

        Args:
            wallet_address: Wallet address to check balance for
            chain_id: Chain ID to check balance on
            token: Optional specific token to check (if None, checks all balances)

        Returns:
            Dictionary with balance information
        """
        try:
            # Get chain name for the prompt
            chain_name = self._get_chain_name(chain_id)

            # Format the prompt for balance checking
            if token:
                prompt = f"What is my {token.upper()} balance?"
            else:
                prompt = f"What is my balance?"

            # Validate wallet address
            if not wallet_address or not wallet_address.startswith('0x'):
                return {
                    "error": "user_friendly",
                    "message": "Invalid wallet address provided.",
                    "technical_details": f"Invalid wallet address: {wallet_address}"
                }

            print(f"Calling Brian API for balance check with: {prompt}")
            print(f"Chain: {chain_id} ({chain_name})")
            print(f"Wallet address: {wallet_address}")

            # Prepare request payload
            payload = {
                "prompt": prompt,
                "chainId": str(chain_id),
                "address": wallet_address
            }

            print(f"Request payload: {payload}")

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/agent/transaction",
                    headers=self.headers,
                    json=payload,
                    timeout=30.0
                )

                print(f"Brian API response status: {response.status_code}")
                print(f"Brian API response: {response.text}")

                if response.status_code == 200:
                    data = response.json()

                    # Check if Brian successfully processed the balance request
                    if "result" in data and data["result"]:
                        result = data["result"][0] if isinstance(data["result"], list) else data["result"]

                        # Extract balance information from the response
                        return {
                            "success": True,
                            "balance_data": result,
                            "chain": chain_name,
                            "address": wallet_address,
                            "token": token or "All tokens"
                        }
                    else:
                        # Brian API returned success but no balance data
                        return {
                            "error": "user_friendly",
                            "message": f"Unable to retrieve balance for {wallet_address} on {chain_name}.",
                            "technical_details": f"Brian API returned no balance data: {response.text}"
                        }

                elif response.status_code == 500:
                    response_text = response.text
                    print(f"Brian API 500 error for balance: {response_text}")

                    return {
                        "error": "user_friendly",
                        "message": f"Balance checking is temporarily unavailable for {chain_name}. Please try again later.",
                        "technical_details": f"Brian API returned 500: {response_text}"
                    }

                else:
                    return {
                        "error": "user_friendly",
                        "message": f"Unable to check balance on {chain_name}. Please try again.",
                        "technical_details": f"Brian API returned {response.status_code}: {response.text}"
                    }

        except Exception as e:
            print(f"Balance check error: {str(e)}")
            return {
                "error": "user_friendly",
                "message": "Balance checking service is currently unavailable. Please try again later.",
                "technical_details": f"Exception: {str(e)}"
            }

    def _get_chain_name(self, chain_id: int) -> str:
        """Map chain ID to a human-readable chain name."""
        return ChainRegistry.get_chain_name(chain_id)

# Global instance
brian_client = BrianClient()
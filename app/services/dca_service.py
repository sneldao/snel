from typing import Dict, Any, Optional, Tuple, List, Union
import logging
import os
import httpx
import json
from datetime import datetime, timedelta
from eth_account import Account
from eth_account.messages import encode_defunct
import secrets
import time
import re
from decimal import Decimal

from app.agents.dca_agent import DCAAgent
from app.services.token_service import TokenService
from app.utils.token_conversion import amount_to_smallest_units, smallest_units_to_amount, format_token_amount
from app.services.transaction_executor import TransactionExecutor
from app.services.base_service import BaseService
from app.models.token import Token
from app.config import (
    OPENOCEAN_DCA_CONTRACT,
    OPENOCEAN_DCA_API_URL,
    WETH_ADDRESS,
)

logger = logging.getLogger(__name__)

class DCAService(BaseService):
    """
    Service for Dollar Cost Averaging (DCA) operations using OpenOcean.
    """
    
    def __init__(self, token_service: TokenService, dca_agent: DCAAgent):
        super().__init__()
        self.token_service = token_service
        self.dca_agent = dca_agent
        self.http_client = httpx.AsyncClient(timeout=30.0)
        self.tx_executor = TransactionExecutor()
        self.base_url = "https://open-api.openocean.finance/v1"
        
        # Set this service in the DCA agent - safely handle the circular reference
        try:
            # Only set if the field exists
            if hasattr(self.dca_agent, 'dca_service'):
                self.dca_agent.dca_service = self
        except Exception as e:
            logger.warning(f"Could not set dca_service in DCAAgent: {e}")
    
    async def process_dca_command(
        self,
        command: str,
        chain_id: int,
        wallet_address: str
    ) -> Dict[str, Any]:
        """
        Process a DCA command and return appropriate response.
        """
        try:
            # Parse the command
            parsed = await self.dca_agent.parse_dca_command(command)
            if not parsed:
                return {
                    "type": "error",
                    "content": "Invalid DCA command format"
                }

            # Get token details
            token_in_result = await self.token_service.lookup_token(
                parsed["token_in"],
                chain_id
            )
            if not token_in_result:
                return {
                    "type": "error",
                    "content": f"Could not find token {parsed['token_in']}"
                }
            
            address_in, symbol_in, name_in, metadata_in = token_in_result
            # Get token decimals
            token_in_decimals = await self.token_service.get_token_decimals(address_in, chain_id)
            token_in = {
                "address": address_in,
                "symbol": symbol_in,
                "name": name_in,
                "metadata": metadata_in,
                "decimals": token_in_decimals,
                "verified": metadata_in.get("verified", True)  # Default to True for predefined tokens
            }

            token_out_result = await self.token_service.lookup_token(
                parsed["token_out"],
                chain_id
            )
            if not token_out_result:
                return {
                    "type": "error",
                    "content": f"Could not find token {parsed['token_out']}"
                }
            
            address_out, symbol_out, name_out, metadata_out = token_out_result
            # Get token decimals
            token_out_decimals = await self.token_service.get_token_decimals(address_out, chain_id)
            token_out = {
                "address": address_out,
                "symbol": symbol_out,
                "name": name_out,
                "metadata": metadata_out,
                "decimals": token_out_decimals,
                "verified": metadata_out.get("verified", True)  # Default to True for predefined tokens
            }

            # Convert ETH to WETH if needed
            if token_in["symbol"].upper() == "ETH":
                token_in["address"] = WETH_ADDRESS
            if token_out["symbol"].upper() == "ETH":
                token_out["address"] = WETH_ADDRESS

            # Calculate amounts in wei
            amount_in_wei = amount_to_smallest_units(
                parsed["amount"],
                token_in["decimals"]
            )

            # Calculate frequency in seconds
            frequency_seconds = self._calculate_frequency_seconds(
                parsed["frequency"]
            )

            # Calculate number of times based on duration
            times = parsed["duration"] * 86400 // frequency_seconds

            # Get approval data
            approval_data = await self._get_approval_data(
                wallet_address=wallet_address,
                chain_id=chain_id,
                token_address=token_in["address"],
                amount=amount_in_wei
            )

            if not approval_data.get("success"):
                return {
                    "content": {
                        "type": "error",
                        "message": approval_data.get("error", "Failed to get approval data")
                    },
                    "error": approval_data.get("error", "Failed to get approval data")
                }

            # Store next step data
            next_step = {
                "type": "dca_setup",
                "wallet_address": wallet_address,
                "chain_id": chain_id,
                "maker_amount": amount_in_wei,
                "taker_amount": "0",  # Will be calculated during setup
                "maker_asset": token_in["address"],
                "taker_asset": token_out["address"],
                "frequency_seconds": frequency_seconds,
                "times": times
            }

            # Format the response
            return {
                "content": {
                    "type": "dca_confirmation",
                    "amount": parsed["amount"],
                    "token_in": {
                        "address": token_in["address"],
                        "symbol": token_in["symbol"],
                        "name": token_in["name"],
                        "decimals": token_in["decimals"],
                        "metadata": token_in["metadata"],
                        "verified": token_in["verified"]
                    },
                    "token_out": {
                        "address": token_out["address"],
                        "symbol": token_out["symbol"],
                        "name": token_out["name"],
                        "decimals": token_out["decimals"],
                        "metadata": token_out["metadata"],
                        "verified": token_out["verified"]
                    },
                    "frequency": parsed["frequency"],
                    "duration": parsed["duration"],
                    "amount_is_usd": parsed.get("amount_is_usd", False)
                },
                "metadata": {
                    "command": command,
                    "chain_id": chain_id,
                    "wallet_address": wallet_address,
                    "parsed_command": parsed,
                    "next_step": next_step,
                    "token_in_address": token_in["address"],
                    "token_in_symbol": token_in["symbol"],
                    "token_in_name": token_in["name"],
                    "token_in_decimals": token_in["decimals"],
                    "token_in_verified": token_in["verified"],
                    "token_out_address": token_out["address"],
                    "token_out_symbol": token_out["symbol"],
                    "token_out_name": token_out["name"],
                    "token_out_decimals": token_out["decimals"],
                    "token_out_verified": token_out["verified"],
                    "maker_asset": token_in["address"],
                    "taker_asset": token_out["address"],
                    "maker_amount": amount_in_wei,
                    "taker_amount": "0",  # Will be calculated during setup
                    "frequency_seconds": frequency_seconds,
                    "times": times,
                    "transaction": {
                        "to": token_in["address"],
                        "data": approval_data["data"],
                        "value": "0",
                        "method": "approve"
                    }
                }
            }

        except Exception as e:
            logger.exception("Error in process_dca_command")
            return {
                "type": "error",
                "content": f"Failed to process DCA command: {str(e)}"
            }
    
    async def create_dca_order(
        self,
        wallet_address: str,
        chain_id: int,
        token_in: Dict[str, Any],
        token_out: Dict[str, Any],
        amount: float,
        frequency: str,
        duration: int
    ) -> Dict[str, Any]:
        """
        Create a DCA order with OpenOcean.
        
        Args:
            wallet_address: The user's wallet address
            chain_id: The blockchain chain ID
            token_in: The input token details
            token_out: The output token details
            amount: The amount to swap each time
            frequency: How often to swap (daily, weekly, monthly)
            duration: How many days to run the DCA for
            
        Returns:
            A dictionary with the DCA order details or error
        """
        try:
            # OpenOcean DCA is only available on Base chain
            if chain_id != 8453:
                return {
                    "success": False,
                    "error": "OpenOcean DCA is only available on Base chain."
                }
                
            # Convert chain ID to chain name for OpenOcean API
            chain_name = self._get_chain_name(chain_id)
            
            # Convert amount to smallest units
            token_in_decimals = await self.token_service.get_token_decimals(token_in["address"], chain_id)
            amount_in_smallest_units = amount_to_smallest_units(amount, token_in_decimals)
            
            # Calculate time parameters based on frequency
            frequency_seconds = self._frequency_to_seconds(frequency)
            times = duration * 86400 // frequency_seconds  # How many swaps will be made
            
            # Check if total value meets minimum requirements ($5 per swap)
            minimum_per_swap = 5  # $5 minimum per swap
            if token_in["symbol"] == "USDC" and amount < minimum_per_swap:
                return {
                    "success": False,
                    "error": f"OpenOcean DCA requires a minimum of ${minimum_per_swap} per swap. Please increase your amount."
                }
            
            # If output token is ETH, we need to use WETH instead
            if token_out["symbol"] == "ETH":
                # Get WETH address on this chain
                token_out = {
                    "address": WETH_ADDRESS,
                    "symbol": "WETH",
                    "name": "Wrapped Ether",
                    "source": "predefined",
                    "verified": True
                }
                
            # First, get a quote for the swap to determine exchange rate
            quote_url = f"{self.base_url}/{chain_name}/quote"
            
            quote_params = {
                "inTokenAddress": token_in["address"],
                "outTokenAddress": token_out["address"],
                "amount": str(amount_in_smallest_units),
                "slippage": "1",  # 1% slippage
                "gasPrice": "5",
                "disabledDexIds": "",
                "referrer": "0x0000000000000000000000000000000000000000"
            }
            
            logger.info(f"Getting quote for DCA initialization: {quote_params}")
            
            try:
                quote_response = await self.http_client.get(quote_url, params=quote_params)
                quote_response.raise_for_status()
                quote_data = quote_response.json()
                
                if quote_data.get("code") != 200:
                    raise Exception(f"Failed to get quote: {quote_data.get('message')}")
                
                quote_result = quote_data.get("data", {})
                taker_amount = quote_result.get("outAmount")
                
                if not taker_amount:
                    raise Exception("Failed to get output amount from quote")
                
                # Get approval for the DCA contract to spend the token
                approval_tx = await self.tx_executor.build_approval_transaction(
                    wallet_address=wallet_address,
                    token_address=token_in["address"],
                    spender=OPENOCEAN_DCA_CONTRACT,
                    amount=amount_in_smallest_units,
                    chain_id=chain_id
                )
                
                # Return the approval transaction first
                return {
                    "success": True,
                    "status": "needs_approval",
                    "transaction": approval_tx,
                    "next_step": {
                        "type": "dca_setup",
                        "maker_amount": str(amount_in_smallest_units),
                        "taker_amount": taker_amount,
                        "maker_asset": token_in["address"],
                        "taker_asset": token_out["address"],
                        "frequency_seconds": frequency_seconds,
                        "times": times,
                        "chain_id": chain_id,
                        "wallet_address": wallet_address,
                        "contract": OPENOCEAN_DCA_CONTRACT
                    }
                }
                
            except Exception as e:
                logger.error(f"Error getting quote or creating DCA order: {e}")
                return {
                    "success": False,
                    "error": f"Failed to initialize DCA: {str(e)}"
                }
            
        except Exception as e:
            logger.error(f"Error creating DCA order: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def cancel_dca_order(self, order_hash: str, chain_id: int) -> Dict[str, Any]:
        """
        Cancel a DCA order.
        
        Args:
            order_hash: The hash of the order to cancel
            chain_id: The blockchain chain ID
            
        Returns:
            A dictionary with the cancellation result
        """
        try:
            # Convert chain ID to chain name for OpenOcean API
            chain_name = self._get_chain_name(chain_id)
            
            cancel_url = f"{self.base_url}/{chain_name}/dca/cancel"
            cancel_data = {"hash": order_hash}
            
            try:
                response = await self.http_client.post(cancel_url, json=cancel_data)
                response.raise_for_status()
                data = response.json()
                
                if data.get("code") != 200:
                    logger.warning(f"DCA cancel API returned error: {data}")
                    return {
                        "success": False,
                        "error": f"API error: {data.get('message', 'Unknown error')}"
                    }
                
                return {
                    "success": True,
                    "order_hash": order_hash,
                    "status": "cancelled",
                    "details": data.get("data", {})
                }
                
            except Exception as e:
                logger.error(f"Error cancelling DCA order via API: {e}")
                
                # Fallback response
                return {
                    "success": True,
                    "order_hash": order_hash,
                    "status": "cancelled",
                    "error": f"API error: {str(e)}",
                    "is_fallback": True
                }
            
        except Exception as e:
            logger.error(f"Error cancelling DCA order: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_dca_orders(
        self,
        wallet_address: str,
        chain_id: int,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Get DCA orders for a wallet address.
        
        Args:
            wallet_address: The wallet address to get orders for
            chain_id: The blockchain chain ID
            limit: Maximum number of orders to return
            
        Returns:
            A dictionary with the orders or error
        """
        try:
            # Convert chain ID to chain name for OpenOcean API
            chain_name = self._get_chain_name(chain_id)
            
            orders_url = f"{self.base_url}/{chain_name}/dca/address/{wallet_address}"
            params = {
                "limit": limit,
                "statuses": [1, 3, 5]  # Active statuses
            }
            
            try:
                response = await self.http_client.get(orders_url, params=params)
                response.raise_for_status()
                data = response.json()
                
                if data.get("code") != 200:
                    logger.warning(f"DCA orders API returned error: {data}")
                    return {
                        "success": False,
                        "error": f"API error: {data.get('message', 'Unknown error')}"
                    }
                
                return {
                    "success": True,
                    "orders": data.get("data", []),
                    "count": len(data.get("data", []))
                }
                
            except Exception as e:
                logger.error(f"Error getting DCA orders via API: {e}")
                
                # Fallback response
                return {
                    "success": True,
                    "orders": [],
                    "count": 0,
                    "error": f"API error: {str(e)}",
                    "is_fallback": True
                }
            
        except Exception as e:
            logger.error(f"Error getting DCA orders: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _get_chain_name(self, chain_id: int) -> str:
        """
        Convert chain ID to chain name for OpenOcean API.
        
        Args:
            chain_id: The blockchain chain ID
            
        Returns:
            The chain name
        """
        chain_map = {
            1: "eth",
            10: "optimism",
            56: "bsc",
            137: "polygon",
            42161: "arbitrum",
            43114: "avax",
            8453: "base",
            534352: "scroll"
        }
        
        return chain_map.get(chain_id, "eth")
    
    def _frequency_to_seconds(self, frequency: str) -> int:
        """
        Convert frequency to seconds.
        
        Args:
            frequency: The frequency (daily, weekly, monthly)
            
        Returns:
            Frequency in seconds
        """
        frequency_map = {
            "daily": 86400,     # 24 hours
            "weekly": 604800,   # 7 days
            "monthly": 2592000  # 30 days
        }
        
        return frequency_map.get(frequency, 86400)
    
    async def setup_dca_order(
        self,
        wallet_address: str,
        chain_id: int,
        maker_amount: str,
        taker_amount: str,
        maker_asset: str,
        taker_asset: str,
        frequency_seconds: int,
        times: int
    ) -> Dict[str, Any]:
        """
        Set up a DCA order after approval is granted.
        """
        try:
            # Generate order hash
            order_hash = await self._generate_order_hash(
                wallet_address=wallet_address,
                maker_asset=maker_asset,
                taker_asset=taker_asset,
                maker_amount=maker_amount,
                taker_amount=taker_amount,
                frequency_seconds=frequency_seconds,
                times=times
            )

            # Get token details
            maker_token_info = await self.token_service.get_token_info(maker_asset, chain_id)
            taker_token_info = await self.token_service.get_token_info(taker_asset, chain_id)
            
            if not maker_token_info or not taker_token_info:
                return {
                    "success": False,
                    "error": "Failed to get token information"
                }
            
            maker_token_decimals = maker_token_info.get("decimals", 18)
            taker_token_decimals = taker_token_info.get("decimals", 18)

            # Calculate amount rate
            try:
                amount_rate = str(float(taker_amount) / float(maker_amount))
            except (ValueError, ZeroDivisionError):
                amount_rate = "1.0"  # Default if calculation fails

            # Build DCA request as per OpenOcean docs
            dca_request = {
                "makerAmount": maker_amount,
                "takerAmount": taker_amount,
                "signature": "",  # Should be signed by the user via frontend SDK
                "orderHash": order_hash,
                "orderMaker": wallet_address,
                "remainingMakerAmount": maker_amount,
                "data": {
                    "salt": order_hash[2:],  # Remove '0x' prefix
                    "makerAsset": maker_asset,
                    "takerAsset": taker_asset,
                    "maker": wallet_address,
                    "receiver": "0x0000000000000000000000000000000000000000",
                    "allowedSender": "0x0000000000000000000000000000000000000000",
                    "makingAmount": maker_amount,
                    "takingAmount": taker_amount,
                    "makerAssetData": "0x",
                    "takerAssetData": "0x",
                    "getMakerAmount": "0x",
                    "getTakerAmount": "0x",
                    "predicate": "0x",
                    "permit": "0x",
                    "interaction": "0x"
                },
                "isActive": True,
                "chainId": chain_id,
                "expireTime": frequency_seconds * times,
                "amountRate": amount_rate,
                "time": frequency_seconds,
                "times": times,
                "minPrice": "0.9",  # 10% price range
                "maxPrice": "1.1",
                "version": "v2"  # Use v2 for first-time integration
            }

            # Log the request for debugging
            logger.info(f"OpenOcean DCA request: {json.dumps(dca_request)}")

            # Call OpenOcean API to create DCA order
            chain_name = self._get_chain_name(chain_id)
            response = await self._call_openocean_api(
                "post",
                f"{self.base_url}/{chain_name}/dca/swap",
                json=dca_request
            )

            if not response.get("success"):
                # Log the error for debugging
                logger.error(f"OpenOcean API error: {response.get('error')}")
                
                # For now, return a clear error message
                return {
                    "success": False,
                    "error": f"Failed to create DCA order: {response.get('error')}"
                }

            # Return transaction data
            return {
                "success": True,
                "transaction": {
                    "to": OPENOCEAN_DCA_CONTRACT,
                    "data": response["data"].get("input", "0x"),
                    "value": "0",
                    "gas_limit": "300000",  # Default gas limit
                },
                "metadata": {
                    "order_hash": order_hash,
                    "maker_asset": maker_asset,
                    "taker_asset": taker_asset,
                    "maker_amount": maker_amount,
                    "taker_amount": taker_amount,
                    "frequency_seconds": frequency_seconds,
                    "times": times
                }
            }

        except Exception as e:
            logger.exception("Error in setup_dca_order")
            return {
                "success": False,
                "error": f"Failed to setup DCA order: {str(e)}"
            }
    
    async def _get_approval_data(
        self,
        wallet_address: str,
        chain_id: int,
        token_address: str,
        amount: str
    ) -> Dict[str, Any]:
        """
        Get approval transaction data for a token.
        """
        try:
            # For DCA v2, we need to get approval for the DCA contract
            # This is handled by the transaction executor
            approval_tx = await self.tx_executor.build_approval_transaction(
                token_address=token_address,
                spender_address=OPENOCEAN_DCA_CONTRACT,
                wallet_address=wallet_address,
                chain_id=chain_id,
                amount=amount
            )

            return {
                "success": True,
                "data": approval_tx.get("data")
            }

        except Exception as e:
            logger.exception(f"Error getting approval data: {e}")
            return {
                "success": False,
                "error": f"Failed to get approval data: {str(e)}"
            }

    async def _generate_order_hash(
        self,
        wallet_address: str,
        maker_asset: str,
        taker_asset: str,
        maker_amount: str,
        taker_amount: str,
        frequency_seconds: int,
        times: int
    ) -> str:
        """
        Generate a unique hash for the DCA order.
        """
        try:
            # For DCA v2, we need to generate a unique salt
            salt = secrets.token_hex(32)
            
            # Build the order data structure as per OpenOcean docs
            order_data = {
                "salt": salt,
                "makerAsset": maker_asset,
                "takerAsset": taker_asset,
                "maker": wallet_address,
                "receiver": "0x0000000000000000000000000000000000000000",
                "allowedSender": "0x0000000000000000000000000000000000000000",
                "makingAmount": maker_amount,
                "takingAmount": taker_amount,
                "makerAssetData": "0x",
                "takerAssetData": "0x",
                "getMakerAmount": "0x",
                "getTakerAmount": "0x",
                "predicate": "0x",
                "permit": "0x",
                "interaction": "0x"
            }

            # Return the salt as the order hash for now
            # In a real implementation, we would use the OpenOcean SDK to generate this
            return f"0x{salt}"

        except Exception as e:
            logger.exception("Error generating order hash")
            raise Exception(f"Failed to generate order hash: {str(e)}")

    def _calculate_frequency_seconds(self, frequency: str) -> int:
        """
        Calculate frequency in seconds based on the frequency string.
        """
        if frequency.lower() == "daily":
            return 86400  # 24 hours
        elif frequency.lower() == "weekly":
            return 604800  # 7 days
        elif frequency.lower() == "monthly":
            return 2592000  # 30 days
        else:
            raise ValueError(f"Invalid frequency: {frequency}")

    async def _call_openocean_api(
        self,
        method: str,
        url: str,
        json: dict = None,
        params: dict = None,
        headers: dict = None
    ) -> Dict[str, Any]:
        """
        Make a call to the OpenOcean API.
        """
        try:
            # Use default headers if none provided
            if headers is None:
                headers = {'Content-Type': 'application/json'}

            response = await self.http_client.request(
                method,
                url,
                json=json,
                params=params,
                headers=headers
            )
            response.raise_for_status()
            data = response.json()

            # Check OpenOcean API response code
            if data.get("code") != 200:
                return {
                    "success": False,
                    "error": data.get("message", "Unknown API error")
                }

            return {
                "success": True,
                "data": data.get("data", {})
            }

        except Exception as e:
            logger.error(f"Error calling OpenOcean API: {e}")
            return {
                "success": False,
                "error": f"Failed to call OpenOcean API: {str(e)}"
            } 
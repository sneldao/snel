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

from app.agents.dca_agent import DCAAgent
from app.services.token_service import TokenService
from app.utils.token_conversion import amount_to_smallest_units, smallest_units_to_amount
from app.services.transaction_executor import TransactionExecutor

logger = logging.getLogger(__name__)

class DCAService:
    """
    Service for Dollar Cost Averaging (DCA) operations using OpenOcean.
    """
    
    def __init__(self, token_service: TokenService, dca_agent: DCAAgent):
        self.token_service = token_service
        self.dca_agent = dca_agent
        self.http_client = httpx.AsyncClient(timeout=30.0)
        self.tx_executor = TransactionExecutor()
        self.base_url = "https://open-api.openocean.finance/v1"
        
        # Set this service in the DCA agent
        self.dca_agent.dca_service = self
    
    async def process_dca_command(
        self,
        command: str,
        chain_id: int,
        wallet_address: str
    ) -> Dict[str, Any]:
        """
        Process a DCA command.
        
        Args:
            command: The natural language DCA command
            chain_id: The blockchain chain ID
            wallet_address: The user's wallet address
            
        Returns:
            A dictionary with the DCA confirmation or error details
        """
        try:
            # Use the DCAAgent to parse the command
            try:
                result = await self.dca_agent.process_dca_command(command, chain_id, wallet_address)
                
                # Handle string error responses
                if isinstance(result, str):
                    logger.error(f"DCA agent returned string error: {result}")
                    return {
                        "type": "error",
                        "content": result,
                        "status": "error"
                    }
                
                # Handle dictionary errors
                if isinstance(result, dict) and "error" in result:
                    return result
                
                # Add wallet address to metadata
                if "metadata" in result:
                    result["metadata"]["wallet_address"] = wallet_address
                
                return result
            except Exception as e:
                logger.error(f"Error in DCA agent: {e}")
                return {
                    "type": "error",
                    "content": f"Failed to process DCA command: {str(e)}",
                    "status": "error"
                }
            
        except Exception as e:
            logger.error(f"Error processing DCA command: {e}")
            return {
                "type": "error",
                "content": f"Failed to process DCA command: {str(e)}",
                "status": "error"
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
            # For simplicity, we'll estimate based on USDC (assuming 1 USDC = $1)
            minimum_per_swap = 5  # $5 minimum per swap
            if token_in["symbol"] == "USDC" and amount < minimum_per_swap:
                return {
                    "success": False,
                    "error": f"OpenOcean DCA requires a minimum of ${minimum_per_swap} per swap. Please increase your amount."
                }
            
            # If output token is ETH, we need to use WETH instead
            if token_out["symbol"] == "ETH":
                # Get WETH address on this chain
                weth_address = "0x4200000000000000000000000000000000000006"  # WETH on Base
                token_out = {
                    "address": weth_address,
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
                
                # Extract necessary information from the quote
                if quote_data.get("code") != 200:
                    raise Exception(f"Failed to get quote: {quote_data.get('message')}")
                
                quote_result = quote_data.get("data", {})
                taker_amount = quote_result.get("outAmount")
                
                if not taker_amount:
                    raise Exception("Failed to get output amount from quote")
                
                # Default parameters for price range (10% up or down)
                min_price = "0.9"
                max_price = "1.1"
                
                # Generate order hash and signature
                salt = secrets.token_hex(32)
                timestamp = int(time.time())
                order_hash = f"0x{secrets.token_hex(32)}"
                
                # Create signature (in production, this would use the user's private key)
                # For now, we'll create a transaction that simulates approval for the DCA contract
                
                # Build the DCA request
                dca_request = {
                    "route": {
                        "makerAmount": str(amount_in_smallest_units),
                        "takerAmount": taker_amount,
                        "orderHash": order_hash,
                        "orderMaker": wallet_address,
                        "remainingMakerAmount": str(amount_in_smallest_units),
                        "data": {
                            "salt": salt,
                            "makerAsset": token_in["address"],
                            "takerAsset": token_out["address"],
                            "maker": wallet_address,
                            "receiver": "0x0000000000000000000000000000000000000000",
                            "allowedSender": "0x0000000000000000000000000000000000000000",
                            "makingAmount": str(amount_in_smallest_units),
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
                        "expireTime": frequency_seconds,
                        "amountRate": quote_result.get("instantRate", "1.0"),
                        "interaction": "0x",
                        "time": frequency_seconds,
                        "times": times,
                        "minPrice": min_price,
                        "maxPrice": max_price
                    }
                }
                
                # Get OpenOcean DCA contract address
                dca_contract = "0x6672f20e25d0C02f8555F36b4A3D079D2df47d9e"  # OpenOcean DCA contract on Base
                
                # We need to first get approval for the DCA contract to spend the token
                approval_tx = await self.tx_executor.build_approval_transaction(
                    wallet_address=wallet_address,
                    token_address=token_in["address"],
                    spender=dca_contract,
                    amount=amount_in_smallest_units,
                    chain_id=chain_id
                )
                
                # Log the request and transaction data
                logger.info(f"Created DCA request: {json.dumps(dca_request)}")
                logger.info(f"Created approval transaction: {json.dumps(approval_tx, default=str)}")
                
                # Return the transaction and DCA order details
                return {
                    "success": True,
                    "order_id": order_hash,
                    "details": {
                        "token_in": token_in,
                        "token_out": token_out,
                        "amount_per_period": amount,
                        "frequency": frequency,
                        "duration": duration,
                        "start_time": datetime.now().isoformat(),
                        "end_time": (datetime.now() + timedelta(days=duration)).isoformat(),
                        "status": "pending_approval",
                        "chain_id": chain_id,
                        "wallet_address": wallet_address,
                        "remaining_swaps": times,
                        "next_swap_time": (datetime.now() + timedelta(seconds=frequency_seconds)).isoformat()
                    },
                    "transaction": approval_tx,
                    "dca_order": dca_request
                }
                
            except Exception as e:
                logger.error(f"Error getting quote or creating DCA order: {e}")
                
                # Fallback to a basic approval transaction
                approval_tx = await self.tx_executor.build_approval_transaction(
                    wallet_address=wallet_address,
                    token_address=token_in["address"],
                    spender="0x6672f20e25d0C02f8555F36b4A3D079D2df47d9e",  # OpenOcean DCA contract on Base
                    amount=amount_in_smallest_units,
                    chain_id=chain_id
                )
                
                return {
                    "success": True,
                    "order_id": f"dca_{datetime.now().timestamp()}",
                    "details": {
                        "token_in": token_in,
                        "token_out": token_out,
                        "amount_per_period": amount,
                        "frequency": frequency,
                        "duration": duration,
                        "start_time": datetime.now().isoformat(),
                        "end_time": (datetime.now() + timedelta(days=duration)).isoformat(),
                        "status": "pending_approval",
                        "chain_id": chain_id,
                        "wallet_address": wallet_address,
                        "remaining_swaps": times,
                        "next_swap_time": (datetime.now() + timedelta(seconds=frequency_seconds)).isoformat()
                    },
                    "transaction": approval_tx
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
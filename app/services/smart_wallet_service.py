import os
import json
import logging
import asyncio
import secrets
import base64
from datetime import datetime
from typing import Dict, Optional, Tuple, List, Any, Union
from redis import asyncio as aioredis
from redis.exceptions import RedisError
from eth_account import Account

# Import Coinbase CDP SDK
from cdp import Cdp, SmartWallet, FunctionCall, EncodedCall

logger = logging.getLogger(__name__)

class SmartWalletService:
    """Service for managing ERC-4337 Smart Wallets through Coinbase CDP SDK."""
    
    def __init__(self, redis_url: Optional[str] = None):
        """Initialize the wallet service.
        
        Args:
            redis_url: Redis URL for storing wallet data (optional)
        """
        self.redis_url = redis_url
        self.redis_client = None
        self._initialize_coinbase_sdk()
    
    def _initialize_coinbase_sdk(self):
        """Initialize the Coinbase CDP SDK with API keys from environment."""
        try:
            # Get API keys from environment
            api_key_name = os.getenv("CDP_API_KEY_NAME")
            api_key_private_key = os.getenv("CDP_API_KEY_PRIVATE_KEY")
            
            if not api_key_name or not api_key_private_key:
                raise ValueError("Coinbase CDP API keys not found in environment variables")
            
            # Configure the CDP SDK
            Cdp.configure(api_key_name, api_key_private_key)
            logger.info("Coinbase CDP SDK initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Coinbase CDP SDK: {e}")
            raise
    
    async def connect_redis(self) -> bool:
        """Connect to Redis if URL is provided."""
        if not self.redis_url:
            logger.warning("No Redis URL provided. Wallet data will not be persisted.")
            return False
        
        try:
            self.redis_client = await aioredis.from_url(self.redis_url, decode_responses=True)
            await self.redis_client.ping()
            logger.info("Connected to Redis successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.redis_client = None
            return False
    
    async def create_smart_wallet(self, user_id: str, platform: str = "telegram") -> Dict[str, Any]:
        """Create a smart wallet for a user.
        
        Args:
            user_id: Unique identifier for the user
            platform: Platform identifier (e.g., "telegram")
            
        Returns:
            Dict containing wallet information
        """
        try:
            # Generate a unique wallet identifier
            unique_id = f"{platform}:{user_id}"
            logger.info(f"Creating smart wallet for user {unique_id}")
            
            # Check if we have a Redis client and if the wallet already exists
            if self.redis_client:
                existing_wallet = await self.get_smart_wallet(user_id, platform)
                if existing_wallet:
                    logger.info(f"Smart wallet already exists for user {unique_id}")
                    return existing_wallet
            
            # Create owner account (EOA) that will control the smart wallet
            private_key = Account.create().key
            owner = Account.from_key(private_key)
            
            # Create a new smart wallet using Coinbase CDP SDK
            smart_wallet = SmartWallet.create(account=owner)
            
            # Create wallet data structure
            wallet_data = {
                "user_id": user_id,
                "platform": platform,
                "address": smart_wallet.address,
                "owner_address": owner.address,
                "private_key": private_key.hex(),  # This should be encrypted in production!
                "network": "base-sepolia",
                "created_at": datetime.now().isoformat()
            }
            
            # Persist wallet data if Redis is available
            if self.redis_client:
                try:
                    # Store wallet data in two formats:
                    # 1. As smart_wallet:{platform}:{user_id} -> wallet data
                    wallet_key = f"smart_wallet:{platform}:{user_id}"
                    await self.redis_client.set(wallet_key, json.dumps(wallet_data))
                    
                    # 2. As address:{address} -> platform:user_id (for reverse lookup)
                    address_key = f"address:{smart_wallet.address}"
                    await self.redis_client.set(address_key, unique_id)
                    
                    logger.info(f"Smart wallet data stored in Redis for user {unique_id}")
                except RedisError as e:
                    logger.error(f"Failed to store smart wallet data in Redis: {e}")
            
            # Return wallet data without private key for security
            public_wallet_data = wallet_data.copy()
            public_wallet_data.pop("private_key", None)
            return public_wallet_data
            
        except Exception as e:
            logger.exception(f"Error creating smart wallet: {e}")
            return {"error": str(e)}
    
    async def get_smart_wallet(self, user_id: str, platform: str = "telegram") -> Optional[Dict[str, Any]]:
        """Get a user's smart wallet data.
        
        Args:
            user_id: Unique identifier for the user
            platform: Platform identifier (e.g., "telegram")
            
        Returns:
            Dict containing wallet information or None if not found
        """
        try:
            # Check if Redis is available
            if not self.redis_client:
                await self.connect_redis()
                if not self.redis_client:
                    logger.warning("Redis not available. Cannot retrieve wallet data.")
                    return None
            
            # Get wallet data from Redis
            wallet_key = f"smart_wallet:{platform}:{user_id}"
            wallet_data = await self.redis_client.get(wallet_key)
            
            if not wallet_data:
                logger.info(f"No smart wallet found for user {platform}:{user_id}")
                return None
            
            wallet_data = json.loads(wallet_data)
            
            # Return wallet data without private key for security
            public_wallet_data = wallet_data.copy()
            public_wallet_data.pop("private_key", None)
            return public_wallet_data
            
        except Exception as e:
            logger.exception(f"Error getting smart wallet: {e}")
            return None
    
    async def get_smart_wallet_with_private_key(self, user_id: str, platform: str = "telegram") -> Optional[Dict[str, Any]]:
        """Get a user's smart wallet data including private key (for internal use only).
        
        Args:
            user_id: Unique identifier for the user
            platform: Platform identifier (e.g., "telegram")
            
        Returns:
            Dict containing wallet information or None if not found
        """
        try:
            # Check if Redis is available
            if not self.redis_client:
                await self.connect_redis()
                if not self.redis_client:
                    logger.warning("Redis not available. Cannot retrieve wallet data.")
                    return None
            
            # Get wallet data from Redis
            wallet_key = f"smart_wallet:{platform}:{user_id}"
            wallet_data = await self.redis_client.get(wallet_key)
            
            if not wallet_data:
                logger.info(f"No smart wallet found for user {platform}:{user_id}")
                return None
            
            return json.loads(wallet_data)
            
        except Exception as e:
            logger.exception(f"Error getting smart wallet with private key: {e}")
            return None
    
    async def get_wallet_balance(self, user_id: str, platform: str = "telegram") -> Dict[str, Any]:
        """Get a user's smart wallet balance.
        
        Args:
            user_id: Unique identifier for the user
            platform: Platform identifier (e.g., "telegram")
            
        Returns:
            Dict containing balance information
        """
        try:
            # Get wallet data with private key
            wallet_data = await self.get_smart_wallet_with_private_key(user_id, platform)
            if not wallet_data:
                logger.info(f"No smart wallet found for user {platform}:{user_id}")
                return {"error": "No wallet found"}
            
            address = wallet_data.get("address")
            private_key = wallet_data.get("private_key")
            
            if not address or not private_key:
                logger.error(f"Wallet data for {platform}:{user_id} missing required fields")
                return {"error": "Invalid wallet data"}
            
            # Recreate the smart wallet object
            owner = Account.from_key(bytes.fromhex(private_key))
            
            # We need to instantiate the smart wallet with the stored address
            # This will be more efficient than creating a new one
            smart_wallet = SmartWallet.from_address(address, owner)
            
            # For now we'll just get ETH balance using Web3 providers
            # In a real application, you'd have more sophisticated balance checking
            balance_info = {
                "address": address,
                "balance": {
                    "eth": "0.0"  # Placeholder - implementing actual balance checking is complex
                }
            }
            
            return balance_info
            
        except Exception as e:
            logger.exception(f"Error getting wallet balance: {e}")
            return {"error": str(e)}
    
    async def send_transaction(self, user_id: str, platform: str, to_address: str, amount: float) -> Dict[str, Any]:
        """Send a transaction from a user's smart wallet.
        
        Args:
            user_id: Unique identifier for the user
            platform: Platform identifier (e.g., "telegram")
            to_address: Recipient address
            amount: Amount of ETH to send
            
        Returns:
            Dict containing transaction result
        """
        try:
            # Get wallet data with private key
            wallet_data = await self.get_smart_wallet_with_private_key(user_id, platform)
            if not wallet_data:
                logger.info(f"No smart wallet found for user {platform}:{user_id}")
                return {"success": False, "message": "No wallet found"}
            
            address = wallet_data.get("address")
            private_key = wallet_data.get("private_key")
            
            if not address or not private_key:
                logger.error(f"Wallet data for {platform}:{user_id} missing required fields")
                return {"success": False, "message": "Invalid wallet data"}
            
            # Recreate the smart wallet object
            owner = Account.from_key(bytes.fromhex(private_key))
            smart_wallet = SmartWallet.from_address(address, owner)
            
            # Convert amount to Wei
            import web3
            value = web3.Web3.to_wei(amount, "ether")
            
            # Prepare a transaction using user operation
            logger.info(f"Sending {amount} ETH from {address} to {to_address}")
            
            # Create a transaction with automatic gas sponsoring on Sepolia
            user_operation = smart_wallet.send_user_operation(
                calls=[
                    EncodedCall(to=to_address, data="0x", value=value)
                ],
                chain_id=84532,  # Base Sepolia chain ID
            )
            
            # Wait for the transaction to complete
            logger.info("Waiting for transaction to complete...")
            user_operation.wait(interval_seconds=0.5, timeout_seconds=30)
            
            # Check transaction status
            if user_operation.status == "SUCCESSFUL":
                tx_hash = user_operation.transaction_hash
                logger.info(f"Transaction successful: {tx_hash}")
                return {
                    "success": True,
                    "message": "Transaction sent successfully",
                    "tx_hash": tx_hash,
                    "from": address,
                    "to": to_address,
                    "amount": amount
                }
            else:
                logger.error(f"Transaction failed: {user_operation.error}")
                return {
                    "success": False,
                    "message": f"Transaction failed: {user_operation.error}",
                }
            
        except Exception as e:
            logger.exception(f"Error sending transaction: {e}")
            return {"success": False, "message": f"Error: {e}"}
    
    async def delete_wallet(self, user_id: str, platform: str = "telegram") -> Dict[str, Any]:
        """Delete a user's smart wallet data.
        
        Args:
            user_id: Unique identifier for the user
            platform: Platform identifier (e.g., "telegram")
            
        Returns:
            Dict containing result of operation
        """
        try:
            # Check if Redis is available
            if not self.redis_client:
                await self.connect_redis()
                if not self.redis_client:
                    logger.warning("Redis not available. Cannot delete wallet data.")
                    return {"success": False, "message": "Redis not available, wallet data could not be deleted"}
            
            # Get wallet data
            wallet_data = await self.get_smart_wallet_with_private_key(user_id, platform)
            if not wallet_data:
                logger.info(f"No smart wallet found for user {platform}:{user_id}")
                return {"success": False, "message": "No wallet found"}
            
            # Get wallet address
            address = wallet_data.get("address")
            
            # Delete wallet data from Redis in both storage formats
            try:
                # 1. Delete the smart_wallet:{platform}:{user_id} key
                wallet_key = f"smart_wallet:{platform}:{user_id}"
                await self.redis_client.delete(wallet_key)
                logger.info(f"Deleted smart wallet data for {wallet_key}")
                
                # 2. Delete the address:{address} reverse mapping if address exists
                if address:
                    address_key = f"address:{address}"
                    await self.redis_client.delete(address_key)
                    logger.info(f"Deleted address mapping for {address_key}")
                
                return {"success": True, "message": "Wallet deleted successfully"}
            except RedisError as e:
                logger.error(f"Failed to delete wallet data in Redis: {e}")
                return {"success": False, "message": f"Error deleting wallet data: {e}"}
                
        except Exception as e:
            logger.exception(f"Error deleting wallet: {e}")
            return {"success": False, "message": f"Error: {e}"}
    
    async def fund_wallet_from_faucet(self, user_id: str, platform: str = "telegram") -> Dict[str, Any]:
        """Fund a user's smart wallet using the Base Sepolia faucet.
        
        Args:
            user_id: Unique identifier for the user
            platform: Platform identifier (e.g., "telegram")
            
        Returns:
            Dict containing result of operation
        """
        try:
            # Get wallet data
            wallet_data = await self.get_smart_wallet(user_id, platform)
            if not wallet_data:
                logger.info(f"No smart wallet found for user {platform}:{user_id}")
                return {"success": False, "message": "No wallet found"}
            
            # Get wallet address
            address = wallet_data.get("address")
            
            if not address:
                logger.error(f"Wallet data for {platform}:{user_id} missing address")
                return {"success": False, "message": "Invalid wallet data"}
            
            # Currently there's no direct way to fund a smart wallet through the SDK
            # Typically you would direct users to a faucet website
            # For Base Sepolia, users can visit: https://faucet.base.org
            
            # For demonstration purposes, we'll just return instructions
            return {
                "success": True,
                "message": "To fund your wallet, visit the Base Sepolia faucet",
                "address": address,
                "faucet_url": "https://faucet.base.org",
                "instructions": "Visit the faucet and request testnet ETH for your wallet address"
            }
            
        except Exception as e:
            logger.exception(f"Error funding wallet: {e}")
            return {"success": False, "message": f"Error: {e}"}
    
    async def get_wallet_by_address(self, address: str) -> Optional[Dict[str, Any]]:
        """Look up a wallet by its address.
        
        Args:
            address: Wallet address to look up
            
        Returns:
            Dict containing user information or None if not found
        """
        try:
            # Check if Redis is available
            if not self.redis_client:
                await self.connect_redis()
                if not self.redis_client:
                    logger.warning("Redis not available. Cannot look up wallet by address.")
                    return None
            
            # Get the user ID from the address mapping
            address_key = f"address:{address}"
            user_id_key = await self.redis_client.get(address_key)
            
            if not user_id_key:
                logger.info(f"No wallet found for address {address}")
                return None
            
            # Parse the platform:user_id format
            platform, user_id = user_id_key.split(":", 1)
            
            # Get the wallet data
            return await self.get_smart_wallet(user_id, platform)
            
        except Exception as e:
            logger.exception(f"Error getting wallet by address: {e}")
            return None
    
    async def execute_contract_call(self, user_id: str, platform: str, contract_address: str, abi: List[Dict[str, Any]], function_name: str, args: List[Any]) -> Dict[str, Any]:
        """Execute a smart contract function call from a user's smart wallet.
        
        Args:
            user_id: Unique identifier for the user
            platform: Platform identifier (e.g., "telegram")
            contract_address: Address of the contract to call
            abi: Contract ABI for the function
            function_name: Name of the function to call
            args: Arguments to pass to the function
            
        Returns:
            Dict containing transaction result
        """
        try:
            # Get wallet data with private key
            wallet_data = await self.get_smart_wallet_with_private_key(user_id, platform)
            if not wallet_data:
                logger.info(f"No smart wallet found for user {platform}:{user_id}")
                return {"success": False, "message": "No wallet found"}
            
            address = wallet_data.get("address")
            private_key = wallet_data.get("private_key")
            
            if not address or not private_key:
                logger.error(f"Wallet data for {platform}:{user_id} missing required fields")
                return {"success": False, "message": "Invalid wallet data"}
            
            # Recreate the smart wallet object
            owner = Account.from_key(bytes.fromhex(private_key))
            smart_wallet = SmartWallet.from_address(address, owner)
            
            # Prepare a contract call
            logger.info(f"Calling {function_name} on contract {contract_address}")
            
            # Create a transaction with automatic gas sponsoring on Sepolia
            user_operation = smart_wallet.send_user_operation(
                calls=[
                    FunctionCall(
                        to=contract_address,
                        abi=abi,
                        function_name=function_name,
                        args=args
                    )
                ],
                chain_id=84532,  # Base Sepolia chain ID
            )
            
            # Wait for the transaction to complete
            logger.info("Waiting for transaction to complete...")
            user_operation.wait(interval_seconds=0.5, timeout_seconds=30)
            
            # Check transaction status
            if user_operation.status == "SUCCESSFUL":
                tx_hash = user_operation.transaction_hash
                logger.info(f"Contract call successful: {tx_hash}")
                return {
                    "success": True,
                    "message": "Contract call executed successfully",
                    "tx_hash": tx_hash,
                    "contract": contract_address,
                    "function": function_name
                }
            else:
                logger.error(f"Contract call failed: {user_operation.error}")
                return {
                    "success": False,
                    "message": f"Contract call failed: {user_operation.error}",
                }
            
        except Exception as e:
            logger.exception(f"Error executing contract call: {e}")
            return {"success": False, "message": f"Error: {e}"}
    
    async def batch_transactions(self, user_id: str, platform: str, transactions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Execute a batch of transactions from a user's smart wallet.
        
        Args:
            user_id: Unique identifier for the user
            platform: Platform identifier (e.g., "telegram")
            transactions: List of transaction objects to execute in a batch
            
        Returns:
            Dict containing transaction result
        """
        try:
            # Get wallet data with private key
            wallet_data = await self.get_smart_wallet_with_private_key(user_id, platform)
            if not wallet_data:
                logger.info(f"No smart wallet found for user {platform}:{user_id}")
                return {"success": False, "message": "No wallet found"}
            
            address = wallet_data.get("address")
            private_key = wallet_data.get("private_key")
            
            if not address or not private_key:
                logger.error(f"Wallet data for {platform}:{user_id} missing required fields")
                return {"success": False, "message": "Invalid wallet data"}
            
            # Recreate the smart wallet object
            owner = Account.from_key(bytes.fromhex(private_key))
            smart_wallet = SmartWallet.from_address(address, owner)
            
            # Prepare calls for batch transaction
            calls = []
            
            import web3
            
            for tx in transactions:
                tx_type = tx.get("type")
                
                if tx_type == "transfer":
                    # Simple ETH transfer
                    to_address = tx.get("to")
                    amount = tx.get("amount")
                    value = web3.Web3.to_wei(amount, "ether")
                    
                    calls.append(
                        EncodedCall(to=to_address, data="0x", value=value)
                    )
                    
                elif tx_type == "contract_call":
                    # Contract function call
                    contract_address = tx.get("contract_address")
                    abi = tx.get("abi")
                    function_name = tx.get("function_name")
                    args = tx.get("args", [])
                    value = web3.Web3.to_wei(tx.get("value", 0), "ether")
                    
                    calls.append(
                        FunctionCall(
                            to=contract_address,
                            abi=abi,
                            function_name=function_name,
                            args=args,
                            value=value
                        )
                    )
            
            if not calls:
                return {"success": False, "message": "No valid transactions in batch"}
            
            # Execute batch transaction
            logger.info(f"Executing batch of {len(calls)} transactions")
            
            # Create a transaction with automatic gas sponsoring on Sepolia
            user_operation = smart_wallet.send_user_operation(
                calls=calls,
                chain_id=84532,  # Base Sepolia chain ID
            )
            
            # Wait for the transaction to complete
            logger.info("Waiting for batch transaction to complete...")
            user_operation.wait(interval_seconds=0.5, timeout_seconds=60)
            
            # Check transaction status
            if user_operation.status == "SUCCESSFUL":
                tx_hash = user_operation.transaction_hash
                logger.info(f"Batch transaction successful: {tx_hash}")
                return {
                    "success": True,
                    "message": "Batch transaction executed successfully",
                    "tx_hash": tx_hash,
                    "transaction_count": len(calls)
                }
            else:
                logger.error(f"Batch transaction failed: {user_operation.error}")
                return {
                    "success": False,
                    "message": f"Batch transaction failed: {user_operation.error}",
                }
            
        except Exception as e:
            logger.exception(f"Error executing batch transactions: {e}")
            return {"success": False, "message": f"Error: {e}"} 
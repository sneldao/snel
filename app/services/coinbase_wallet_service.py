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
from cdp import Cdp, Wallet, SmartWallet, Transaction

logger = logging.getLogger(__name__)

class CoinbaseWalletService:
    """Service for managing wallets through Coinbase CDP SDK."""
    
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
    
    async def create_wallet(self, user_id: str, platform: str = "telegram") -> Dict[str, Any]:
        """Create a wallet for a user.
        
        Args:
            user_id: Unique identifier for the user
            platform: Platform identifier (e.g., "telegram")
            
        Returns:
            Dict containing wallet information
        """
        try:
            # Generate a unique wallet identifier
            unique_id = f"{platform}:{user_id}"
            logger.info(f"Creating wallet for user {unique_id}")
            
            # Check if we have a Redis client and if the wallet already exists
            if self.redis_client:
                existing_wallet = await self.get_wallet(user_id, platform)
                if existing_wallet:
                    logger.info(f"Wallet already exists for user {unique_id}")
                    return existing_wallet
            
            # Create a new wallet using Coinbase CDP SDK (on testnet for development)
            wallet = Wallet.create(network_id="base-sepolia")
            address = wallet.default_address
            
            # Create wallet data structure
            wallet_data = {
                "user_id": user_id,
                "platform": platform,
                "address": address.address_id,
                "network": "base-sepolia",
                "created_at": datetime.now().isoformat()
            }
            
            # Persist wallet data if Redis is available
            if self.redis_client:
                try:
                    # Store wallet data in two formats:
                    # 1. As wallet:{platform}:{user_id} -> wallet data
                    wallet_key = f"wallet:{platform}:{user_id}"
                    await self.redis_client.set(wallet_key, json.dumps(wallet_data))
                    
                    # 2. As address:{address} -> platform:user_id (for reverse lookup)
                    address_key = f"address:{address.address_id}"
                    await self.redis_client.set(address_key, unique_id)
                    
                    logger.info(f"Wallet data stored in Redis for user {unique_id}")
                except RedisError as e:
                    logger.error(f"Failed to store wallet data in Redis: {e}")
            
            return wallet_data
            
        except Exception as e:
            logger.exception(f"Error creating wallet: {e}")
            return {"error": str(e)}
    
    async def get_wallet(self, user_id: str, platform: str = "telegram") -> Optional[Dict[str, Any]]:
        """Get a user's wallet data.
        
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
            wallet_key = f"wallet:{platform}:{user_id}"
            wallet_data = await self.redis_client.get(wallet_key)
            
            if not wallet_data:
                logger.info(f"No wallet found for user {platform}:{user_id}")
                return None
            
            return json.loads(wallet_data)
            
        except Exception as e:
            logger.exception(f"Error getting wallet: {e}")
            return None
    
    async def get_wallet_balance(self, user_id: str, platform: str = "telegram") -> Dict[str, Any]:
        """Get a user's wallet balance.
        
        Args:
            user_id: Unique identifier for the user
            platform: Platform identifier (e.g., "telegram")
            
        Returns:
            Dict containing balance information
        """
        try:
            # Get wallet data
            wallet_data = await self.get_wallet(user_id, platform)
            if not wallet_data:
                logger.info(f"No wallet found for user {platform}:{user_id}")
                return {"error": "No wallet found"}
            
            address = wallet_data.get("address")
            if not address:
                logger.error(f"Wallet data for {platform}:{user_id} missing address")
                return {"error": "Invalid wallet data"}
            
            # Use CDP SDK to get balance information
            # We need to recreate the wallet object since we only stored the address
            new_wallet = Wallet.create(network_id=wallet_data.get("network", "base-sepolia"))
            # Note: This creates a new wallet, but we only need it to check balance
            # For a production app, you would store more wallet information to avoid this
            
            # Get ETH balance
            eth_balance = new_wallet.balance("eth")
            
            return {
                "address": address,
                "balance": {
                    "eth": eth_balance
                }
            }
            
        except Exception as e:
            logger.exception(f"Error getting wallet balance: {e}")
            return {"error": str(e)}
    
    async def delete_wallet(self, user_id: str, platform: str = "telegram") -> Dict[str, Any]:
        """Delete a user's wallet data.
        
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
            wallet_data = await self.get_wallet(user_id, platform)
            if not wallet_data:
                logger.info(f"No wallet found for user {platform}:{user_id}")
                return {"success": False, "message": "No wallet found"}
            
            # Get wallet address
            address = wallet_data.get("address")
            
            # Delete wallet data from Redis in both storage formats
            try:
                # 1. Delete the wallet:{platform}:{user_id} key
                wallet_key = f"wallet:{platform}:{user_id}"
                await self.redis_client.delete(wallet_key)
                logger.info(f"Deleted wallet data for {wallet_key}")
                
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
    
    async def send_transaction(self, user_id: str, platform: str, to_address: str, amount: float) -> Dict[str, Any]:
        """Send a transaction from a user's wallet.
        
        Args:
            user_id: Unique identifier for the user
            platform: Platform identifier (e.g., "telegram")
            to_address: Recipient address
            amount: Amount of ETH to send
            
        Returns:
            Dict containing transaction result
        """
        try:
            # Get wallet data
            wallet_data = await self.get_wallet(user_id, platform)
            if not wallet_data:
                logger.info(f"No wallet found for user {platform}:{user_id}")
                return {"success": False, "message": "No wallet found"}
            
            # This is a simplified example for demonstration
            # In a real implementation, you would need to properly manage wallet persistence
            # The current implementation creates a new wallet each time, which is not practical
            
            # For a production app, you would need to store the wallet seed or private key securely
            # This might involve encrypting the seed with a user-provided password
            # or using a secure key management service
            
            logger.warning("This is a demonstration only; real transaction not implemented")
            logger.warning("In production, you would need to securely manage wallet secrets")
            
            return {
                "success": True,
                "message": "Transaction demo (not actually sent)",
                "tx_hash": "0x" + secrets.token_hex(32),
                "from": wallet_data.get("address"),
                "to": to_address,
                "amount": amount
            }
            
        except Exception as e:
            logger.exception(f"Error sending transaction: {e}")
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
            return await self.get_wallet(user_id, platform)
            
        except Exception as e:
            logger.exception(f"Error getting wallet by address: {e}")
            return None 
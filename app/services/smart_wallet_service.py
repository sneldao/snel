import os
import json
import logging
import asyncio
import secrets
import base64
import ssl
import certifi
from datetime import datetime
from typing import Dict, Optional, Tuple, List, Any, Union
from redis import asyncio as aioredis
from redis.exceptions import RedisError
from eth_account import Account

# Import Coinbase CDP SDK
from cdp import Cdp, SmartWallet, FunctionCall, EncodedCall
from app.services.wallet_service import WalletService

logger = logging.getLogger(__name__)

class SmartWalletService(WalletService):
    """Service for managing ERC-4337 Smart Wallets through Coinbase CDP SDK."""
    
    def __init__(self, redis_url: Optional[str] = None):
        """Initialize the wallet service.
        
        Args:
            redis_url: Redis URL for storing wallet data (optional)
        """
        super().__init__(redis_url=redis_url)
        self._configure_ssl()
        self._initialize_coinbase_sdk()
    
    def _configure_ssl(self):
        """Configure SSL certificates to ensure secure connections."""
        try:
            # Set the SSL certificate path to the certifi bundle
            os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()
            os.environ['SSL_CERT_FILE'] = certifi.where()
            
            # Make sure the SSL context is using the proper certificates
            ssl_context = ssl.create_default_context(cafile=certifi.where())
            
            logger.info(f"SSL certificates properly configured using: {certifi.where()}")
        except Exception as e:
            logger.error(f"Failed to configure SSL certificates: {e}")
            raise
    
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
            
            # Check if we're using Coinbase-Managed (2-of-2) wallets for production
            use_managed_wallet = os.getenv("CDP_USE_MANAGED_WALLET", "").lower() in ("true", "1", "yes")
            if use_managed_wallet:
                # Enable Server-Signer for Coinbase-Managed (2-of-2) wallets
                Cdp.use_server_signer = True
                logger.info("Using Coinbase-Managed (2-of-2) wallets for production")
            else:
                logger.info("Using Developer-Managed (1-of-1) wallets for development")
                
        except Exception as e:
            logger.error(f"Failed to initialize Coinbase CDP SDK: {e}")
            raise
    
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
            logger.info(f"Initializing new SmartWallet for {platform}:{user_id}")
            smart_wallet = SmartWallet.create(account=owner)
            
            # Create wallet data structure
            wallet_data = {
                "user_id": user_id,
                "platform": platform,
                "address": smart_wallet.address,
                "owner_address": owner.address,
                "private_key": private_key.hex(),  # This should be encrypted in production!
                "network": "base-sepolia",
                "wallet_type": "coinbase_cdp",
                "created_at": datetime.now().isoformat()
            }
            
            # Persist wallet data if Redis is available
            if self.redis_client:
                try:
                    # Store wallet data
                    wallet_key = f"smart_wallet:{platform}:{user_id}"
                    await self.redis_client.set(
                        wallet_key,
                        json.dumps(wallet_data)
                    )
                    
                    # Also store in messaging format for compatibility
                    messaging_key = f"messaging:{platform}:user:{user_id}:wallet"
                    await self.redis_client.set(
                        messaging_key,
                        smart_wallet.address
                    )
                    
                    # Store reverse mapping
                    address_key = f"address:{smart_wallet.address}:user"
                    await self.redis_client.set(
                        address_key,
                        json.dumps({"user_id": user_id, "platform": platform})
                    )
                    
                    logger.info(f"Smart wallet data stored in Redis for user {unique_id}")
                except Exception as e:
                    logger.error(f"Failed to store smart wallet data in Redis: {e}")
                    # Continue even if Redis storage fails
            
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
                # Try to get the address from messaging format
                messaging_key = f"messaging:{platform}:user:{user_id}:wallet"
                address = await self.redis_client.get(messaging_key)
                
                if not address:
                    logger.info(f"No smart wallet found for user {platform}:{user_id}")
                    return None
                
                # If we just have the address but not the full wallet data, return minimal info
                if isinstance(address, bytes):
                    address = address.decode('utf-8')
                    
                return {
                    "address": address,
                    "user_id": user_id,
                    "platform": platform,
                    "wallet_type": "coinbase_cdp",
                    "network": "base-sepolia"
                }
            
            if isinstance(wallet_data, bytes):
                wallet_data = wallet_data.decode('utf-8')
                
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
            
            if isinstance(wallet_data, bytes):
                wallet_data = wallet_data.decode('utf-8')
                
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
            owner = Account.from_key(bytes.fromhex(private_key) if isinstance(private_key, str) else private_key)
            
            # Instantiate the smart wallet with the stored address
            # This is more efficient than creating a new one
            smart_wallet = SmartWallet.from_address(address, owner)
            
            # For now we'll just get ETH balance
            # In a real implementation, you can use smart_wallet to get balances for all assets
            return {
                "address": address,
                "balance": {
                    "eth": "0.1"  # Placeholder - actual balance checking to be implemented
                }
            }
            
        except Exception as e:
            logger.exception(f"Error getting wallet balance: {e}")
            return {"error": str(e)}
    
    async def send_transaction(self, user_id: str, platform: str, to_address: str, amount: float) -> Dict[str, Any]:
        """Send a transaction from a user's smart wallet.
        
        Args:
            user_id: Unique identifier for the user
            platform: Platform identifier (e.g., "telegram")
            to_address: Recipient address
            amount: Amount to send
            
        Returns:
            Dict containing transaction info
        """
        try:
            # Get wallet data with private key
            wallet_data = await self.get_smart_wallet_with_private_key(user_id, platform)
            if not wallet_data:
                return {"error": "No wallet found"}
            
            address = wallet_data.get("address")
            private_key = wallet_data.get("private_key")
            
            if not address or not private_key:
                return {"error": "Invalid wallet data"}
            
            # Recreate the smart wallet object
            owner = Account.from_key(bytes.fromhex(private_key) if isinstance(private_key, str) else private_key)
            smart_wallet = SmartWallet.from_address(address, owner)
            
            # Convert amount to wei (smallest ETH unit)
            from decimal import Decimal
            from web3 import Web3
            value = Web3.to_wei(Decimal(str(amount)), "ether")
            
            # Send user operation
            user_operation = smart_wallet.send_user_operation(
                calls=[
                    EncodedCall(to=to_address, data="0x", value=value)
                ],
                chain_id=84532  # Base Sepolia chain ID
                # Paymaster is automatically used on testnet
            )
            
            # Wait for the operation to complete
            user_operation.wait(interval_seconds=0.2, timeout_seconds=20)
            
            # Check the status and get transaction hash
            if user_operation.transaction_hash:
                return {
                    "success": True,
                    "transaction_hash": user_operation.transaction_hash,
                    "from_address": address,
                    "to_address": to_address,
                    "amount": amount
                }
            else:
                return {
                    "success": False,
                    "error": "Transaction failed"
                }
                
        except Exception as e:
            logger.exception(f"Error sending transaction: {e}")
            return {"error": str(e)}
    
    async def fund_wallet_from_faucet(self, user_id: str, platform: str) -> Dict[str, Any]:
        """Get testnet ETH from the faucet for a user's wallet.
        
        Args:
            user_id: Unique identifier for the user
            platform: Platform identifier (e.g., "telegram")
            
        Returns:
            Dict containing faucet info
        """
        try:
            # Get wallet data
            wallet_data = await self.get_smart_wallet(user_id, platform)
            if not wallet_data:
                return {"error": "No wallet found"}
            
            # Get private key for wallet operations
            private_key_data = await self.get_smart_wallet_with_private_key(user_id, platform)
            if not private_key_data or not private_key_data.get("private_key"):
                return {"error": "Could not retrieve wallet private key"}
                
            address = wallet_data.get("address")
            private_key = private_key_data.get("private_key")
            
            # Recreate the smart wallet object
            owner = Account.from_key(bytes.fromhex(private_key) if isinstance(private_key, str) else private_key)
            smart_wallet = SmartWallet.from_address(address, owner)
            
            try:
                # Request ETH from faucet
                faucet_transaction = smart_wallet.faucet()
                
                # Wait for the faucet transaction to complete
                faucet_transaction.wait()
                
                logger.info(f"Faucet transaction completed for {platform}:{user_id}")
                
                # Also try to get USDC from faucet
                try:
                    usdc_faucet = smart_wallet.faucet(asset_id="usdc")
                    usdc_faucet.wait()
                    logger.info(f"USDC faucet transaction completed for {platform}:{user_id}")
                except Exception as e:
                    logger.warning(f"USDC faucet request failed: {e}")
                
                return {
                    "success": True, 
                    "transaction_hash": faucet_transaction.transaction_hash,
                    "faucet_url": "https://faucet.base.org"
                }
            except Exception as e:
                logger.exception(f"Error requesting from faucet: {e}")
                return {
                    "success": False,
                    "error": str(e),
                    "faucet_url": "https://faucet.base.org"
                }
                
        except Exception as e:
            logger.exception(f"Error in fund_wallet_from_faucet: {e}")
            return {"error": str(e)}
    
    async def delete_wallet(self, user_id: str, platform: str) -> Dict[str, Any]:
        """Override from parent class to delete a smart wallet.
        
        Args:
            user_id: User ID
            platform: Platform identifier
            
        Returns:
            Dict with deletion status
        """
        try:
            # Get the wallet address first before we delete anything
            wallet_data = await self.get_smart_wallet(user_id, platform)
            if not wallet_data:
                return {
                    "success": True,
                    "message": "No wallet found to delete"
                }
                
            address = wallet_data.get("address")
            
            # Delete from smart wallet storage
            wallet_key = f"smart_wallet:{platform}:{user_id}"
            await self.redis_client.delete(wallet_key)
            
            # Delete from messaging storage
            messaging_key = f"messaging:{platform}:user:{user_id}:wallet"
            await self.redis_client.delete(messaging_key)
            
            # Delete address mapping
            if address:
                address_key = f"address:{address}:user"
                await self.redis_client.delete(address_key)
            
            logger.info(f"Deleted smart wallet for {platform}:{user_id}")
            
            return {
                "success": True,
                "message": "Smart wallet deleted successfully"
            }
                
        except Exception as e:
            logger.exception(f"Error deleting smart wallet: {e}")
            return {
                "success": False,
                "message": f"Error deleting wallet: {str(e)}"
            }
    
    async def connect_redis(self) -> bool:
        """Connect to Redis if URL is provided."""
        if not self.redis_url:
            logger.warning("No Redis URL provided. Wallet data will not be persisted.")
            return False
        
        try:
            self.redis_client = await aioredis.from_url(
                self.redis_url,
                decode_responses=True,
                ssl_cert_reqs=None if "upstash" in self.redis_url.lower() else True
            )
            await self.redis_client.ping()
            logger.info("Connected to Redis successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.redis_client = None
            return False 
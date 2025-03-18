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
        
        # Configure SSL first
        self._configure_ssl()
        
        # Initialize Coinbase CDP SDK - but don't validate here
        # This allows the class to be instantiated even if CDP is not properly configured yet
        try:
            # _initialize_coinbase_sdk returns True if successful, False otherwise
            self.cdp_initialized = self._initialize_coinbase_sdk()
            if self.cdp_initialized:
                logger.info("SmartWalletService initialized successfully with CDP SDK")
            else:
                logger.warning("SmartWalletService initialized but CDP SDK is not available")
        except Exception as e:
            logger.error(f"Failed to initialize Coinbase CDP SDK: {e}")
            self.cdp_initialized = False
            # Don't raise an exception, just mark as not initialized
    
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
                logger.error("CDP_API_KEY_NAME and CDP_API_KEY_PRIVATE_KEY must be set in environment variables")
                return False
            
            # Log the API key name (but not the private key) for debugging
            logger.info(f"Initializing Coinbase CDP SDK with API key name: {api_key_name}")
            
            # Configure the CDP SDK
            try:
                Cdp.configure(api_key_name, api_key_private_key)
                logger.info("Coinbase CDP SDK initialized successfully")
            except Exception as config_error:
                logger.error(f"Error configuring CDP SDK: {config_error}")
                return False
            
            # Check if we're using Coinbase-Managed (2-of-2) wallets for production
            use_managed_wallet = os.getenv("CDP_USE_MANAGED_WALLET", "").lower() in ("true", "1", "yes")
            if use_managed_wallet:
                # Enable Server-Signer for Coinbase-Managed (2-of-2) wallets
                try:
                    Cdp.use_server_signer = True
                    logger.info("Using Coinbase-Managed (2-of-2) wallets for production")
                except Exception as server_signer_error:
                    logger.error(f"Error enabling server signer: {server_signer_error}")
                    # Non-fatal, continue
            else:
                logger.info("Using Developer-Managed (1-of-1) wallets for development")
            
            return True
                
        except Exception as e:
            logger.error(f"Failed to initialize Coinbase CDP SDK: {e}")
            return False
    
    def _verify_cdp_configured(self) -> bool:
        """Verify that the CDP SDK is properly configured.
        
        Returns:
            Boolean indicating if the CDP SDK is properly configured
        """
        # Check that the API key is configured - this uses the public interface rather than internal attributes
        # This is a non-destructive check that doesn't make any network calls
        try:
            # Check if Cdp has been initialized by looking at its configuration state
            # Using a different approach that's independent of internal implementation details
            api_key_name = os.getenv("CDP_API_KEY_NAME")
            
            # We only have access to verify that we've attempted to configure the SDK
            # We can't verify if the key is valid without making a network call
            if not api_key_name:
                logger.error("CDP_API_KEY_NAME environment variable not set")
                return False
                
            return True
        except Exception as e:
            logger.error(f"Error verifying CDP configuration: {e}")
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
            # Check if CDP SDK is properly initialized
            if not hasattr(self, 'cdp_initialized') or not self.cdp_initialized:
                logger.error("Cannot create smart wallet: CDP SDK not properly initialized")
                return {
                    "success": False,
                    "error": "CDP SDK not properly initialized. Smart wallet creation is unavailable."
                }
                
            # Generate a unique wallet identifier
            unique_id = f"{platform}:{user_id}"
            logger.info(f"Creating smart wallet for user {unique_id}")
            
            # Check if wallet already exists in Redis
            wallet_key = f"wallet:{platform}:{user_id}"
            
            try:
                existing_wallet = await self.redis_client.get(wallet_key)
                
                if existing_wallet:
                    try:
                        wallet_data = json.loads(existing_wallet)
                        logger.info(f"Found existing wallet for {unique_id}: {wallet_data.get('address')}")
                        return {
                            "success": True,
                            "address": wallet_data.get("address"),
                            "chain": wallet_data.get("chain", "base_sepolia"),
                            "is_new": False
                        }
                    except json.JSONDecodeError:
                        logger.error(f"Invalid JSON in Redis for wallet {wallet_key}: {existing_wallet}")
                        # Continue to create a new wallet
            except Exception as redis_err:
                logger.error(f"Error checking for existing wallet in Redis: {redis_err}")
                # Continue to create a new wallet
                
            # Create a new wallet using CDP SDK
            try:
                # Import module here to get better error messages
                try:
                    from cdp import SmartWallet
                except ImportError as imp_err:
                    logger.error(f"Error importing SmartWallet: {imp_err}")
                    return {
                        "success": False,
                        "error": f"CDP SDK not properly installed: {str(imp_err)}"
                    }
                
                # Simplest possible call to SmartWallet.create
                # Avoid using optional parameters that might cause issues
                logger.info("Calling SmartWallet.create with minimal parameters")
                
                # Try with different parameters if the first attempt fails
                try:
                    wallet = SmartWallet.create()
                except Exception as simple_err:
                    logger.error(f"Simple SmartWallet.create failed: {simple_err}, trying with project_id")
                    try:
                        wallet = SmartWallet.create(project_id=unique_id)
                    except Exception as project_err:
                        logger.error(f"SmartWallet.create with project_id failed: {project_err}")
                        raise project_err  # Re-raise the error
                
                wallet_address = wallet.address
                logger.info(f"Created new wallet for {unique_id}: {wallet_address}")
                
                # Store wallet info in Redis
                wallet_data = {
                    "address": wallet_address,
                    "chain": "base_sepolia",  # Default to Base Sepolia testnet
                    "platform": platform,
                    "user_id": user_id,
                    "created_at": datetime.utcnow().isoformat()
                }
                
                # Save to Redis
                try:
                    await self.redis_client.set(wallet_key, json.dumps(wallet_data))
                    logger.info(f"Saved wallet data to Redis for {unique_id}")
                except Exception as redis_err:
                    logger.error(f"Failed to save wallet data to Redis: {redis_err}")
                    # Continue even if Redis fails - we still have the wallet address
                
                return {
                    "success": True,
                    "address": wallet_address,
                    "chain": "base_sepolia",
                    "is_new": True
                }
            except Exception as wallet_err:
                # Specific error handling for wallet creation
                logger.error(f"Failed to create wallet via CDP SDK: {wallet_err}")
                return {
                    "success": False,
                    "error": f"Failed to create wallet: {str(wallet_err)}"
                }
                
        except Exception as e:
            logger.exception(f"Unexpected error creating smart wallet: {e}")
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}"
            }
    
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
    
    async def get_cdp_sdk_diagnostics(self) -> Dict[str, Any]:
        """Get diagnostic information about the CDP SDK.
        
        Returns:
            Dict containing diagnostic information
        """
        try:
            # Check for environment variables
            api_key_name = os.getenv("CDP_API_KEY_NAME", "")
            api_key_private_key_exists = bool(os.getenv("CDP_API_KEY_PRIVATE_KEY", ""))
            use_cdp_sdk = os.getenv("USE_CDP_SDK", "false").lower() in ["true", "1", "yes"]
            use_managed_wallet = os.getenv("CDP_USE_MANAGED_WALLET", "false").lower() in ["true", "1", "yes"]
            
            # Check CDP module information
            cdp_module_info = {}
            try:
                import cdp
                cdp_module_info = {
                    "module_exists": True,
                    "version": getattr(cdp, "__version__", "unknown"),
                    "path": getattr(cdp, "__file__", "unknown"),
                }
            except ImportError:
                cdp_module_info = {
                    "module_exists": False,
                    "error": "CDP module not found or not importable"
                }
                
            # Check if the CDP is configured
            cdp_configured = hasattr(self, 'cdp_initialized') and self.cdp_initialized
            
            # Get SmartWallet class info
            smart_wallet_info = {}
            try:
                smart_wallet_info = {
                    "class_exists": hasattr(cdp, "SmartWallet"),
                    "create_method_exists": hasattr(cdp.SmartWallet, "create") if hasattr(cdp, "SmartWallet") else False,
                }
            except Exception as sw_err:
                smart_wallet_info = {
                    "error": f"Error checking SmartWallet class: {sw_err}"
                }
                
            # Return all diagnostic information
            return {
                "environment": {
                    "CDP_API_KEY_NAME": api_key_name[:10] + "..." if len(api_key_name) > 10 else api_key_name,
                    "CDP_API_KEY_PRIVATE_KEY": "exists" if api_key_private_key_exists else "missing",
                    "USE_CDP_SDK": use_cdp_sdk,
                    "CDP_USE_MANAGED_WALLET": use_managed_wallet,
                },
                "cdp_module": cdp_module_info,
                "cdp_configured": cdp_configured,
                "smart_wallet_info": smart_wallet_info,
                "redis_connected": self.redis_client is not None,
            }
        except Exception as e:
            logger.exception(f"Error getting CDP SDK diagnostics: {e}")
            return {
                "error": str(e)
            } 
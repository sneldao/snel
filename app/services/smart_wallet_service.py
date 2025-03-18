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
    
    async def _cleanup_invalid_wallet(self, platform: str, user_id: str) -> None:
        """Delete invalid wallet entries from Redis.
        
        Args:
            platform: Platform identifier (e.g., "telegram")
            user_id: User identifier
        """
        try:
            # Keys to delete
            keys_to_delete = [
                f"wallet:{platform}:{user_id}",
                f"messaging:{platform}:user:{user_id}:wallet",
                f"smart_wallet:{platform}:{user_id}"
            ]
            
            for key in keys_to_delete:
                try:
                    await self.redis_client.delete(key)
                    logger.info(f"Deleted invalid wallet entry: {key}")
                except Exception as e:
                    logger.error(f"Error deleting key {key}: {e}")
                    
        except Exception as e:
            logger.error(f"Error in _cleanup_invalid_wallet: {e}")
            
    async def create_smart_wallet(self, user_id: str, platform: str = "telegram", chain: str = "base_sepolia") -> Dict[str, Any]:
        """Create a new smart wallet for a user.
        
        Args:
            user_id: User ID (e.g., Telegram user ID)
            platform: Platform identifier (e.g., "telegram")
            chain: Chain to use (e.g., "base_sepolia")
            
        Returns:
            Dict with wallet info or error
        """
        logger.info(f"Creating smart wallet for {platform}:{user_id} on chain {chain}")
        
        # Check if CDP SDK is initialized
        if not self.cdp_initialized:
            error_msg = "Coinbase CDP SDK is not properly initialized. Check API keys."
            logger.error(error_msg)
            return {"error": error_msg}
            
        # Verify that the CDP SDK is available
        if not self._verify_cdp_configured():
            error_msg = "Coinbase CDP SDK is not properly configured"
            logger.error(error_msg)
            return {"error": error_msg}
            
        # Connect to Redis if not already connected
        if not self.redis_client:
            try:
                await self.connect_redis()
                if not self.redis_client:
                    error_msg = "Failed to connect to Redis"
                    logger.error(error_msg)
                    return {"error": error_msg}
            except Exception as e:
                error_msg = f"Redis connection error: {str(e)}"
                logger.exception(error_msg)
                return {"error": error_msg}
                
        # Determine wallet key
        wallet_key = f"wallet:{platform}:{user_id}"
            
        try:
            # First check if user already has a wallet
            existing_wallet = await self.get_smart_wallet(user_id, platform)
            
            # If wallet found, return it
            if existing_wallet and existing_wallet.get("address"):
                logger.info(f"Found existing wallet for {platform}:{user_id}: {existing_wallet.get('address')}")
                return {
                    "address": existing_wallet.get("address"),
                    "chain": existing_wallet.get("chain", chain),
                    "user_id": user_id,
                    "platform": platform
                }
        except Exception as e:
            logger.warning(f"Error checking for existing wallet for {platform}:{user_id}: {e}")
            # Continue to create a new wallet
                
        try:
            # Create a new owner account (EOA) that will control the smart wallet
            logger.info(f"Creating new owner account (EOA) for {platform}:{user_id}")
            owner = Account.create()
            owner_address = owner.address
            owner_key = owner.key.hex()
            logger.info(f"Created owner account with address {owner_address}")
            
            # Create a new smart wallet with this owner
            logger.info(f"Creating smart wallet with owner {owner_address}")
            try:
                smart_wallet = SmartWallet.create(account=owner)
                logger.info(f"Smart wallet created with address {smart_wallet.address}")
            except Exception as wallet_e:
                logger.exception(f"Error creating smart wallet with CDP SDK: {wallet_e}")
                return {"error": f"Failed to create smart wallet: {str(wallet_e)}"}
                
            # Store wallet data in Redis
            # WARNING: In production, you should encrypt the private key before storing it
            wallet_data = {
                "address": smart_wallet.address,
                "owner_address": owner_address,
                "private_key": owner_key,  # WARNING: Encrypt this in production!
                "user_id": user_id,
                "platform": platform,
                "chain": chain,
                "wallet_type": "coinbase_cdp",
                "created_at": datetime.now().isoformat()
            }
            
            try:
                # Store in Redis - save with the platform user ID as the key
                await self.redis_client.set(wallet_key, json.dumps(wallet_data))
                logger.info(f"Stored wallet data in Redis under key {wallet_key}")
                
                # Also store in messaging format for compatibility with messaging agent
                messaging_key = f"messaging:{platform}:user:{user_id}:wallet"
                await self.redis_client.set(messaging_key, smart_wallet.address)
                logger.info(f"Stored wallet address in Redis under key {messaging_key}")
                
                # Return wallet data without private key for security
                public_wallet_data = {k: v for k, v in wallet_data.items() if k != "private_key"}
                return public_wallet_data
            except Exception as redis_e:
                logger.exception(f"Error storing wallet data in Redis: {redis_e}")
                return {"error": f"Failed to store wallet data: {str(redis_e)}"}
                
        except Exception as e:
            logger.exception(f"Error creating smart wallet for {platform}:{user_id}: {e}")
            return {"error": str(e)}
    
    async def get_smart_wallet(self, user_id: str, platform: str) -> Optional[Dict[str, Any]]:
        """Get a user's smart wallet data.
        
        Args:
            user_id: User ID string
            platform: Platform identifier (telegram, discord, etc.)
            
        Returns:
            Dict containing wallet information or None if not found
        """
        try:
            # Log the request details
            logger.info(f"Retrieving smart wallet for user {platform}:{user_id}")
            
            if not self.redis_client:
                logger.error("Redis client not initialized in get_smart_wallet")
                return None
            
            # Define all possible key formats to check
            possible_keys = [
                f"wallet:{platform}:{user_id}",
                f"smart_wallet:{platform}:{user_id}",
                f"cdp_wallet:{platform}:{user_id}"
            ]
            
            wallet_data = None
            used_key = None
            
            # Try each key format
            for key in possible_keys:
                data = await self.redis_client.get(key)
                if data:
                    wallet_data = data
                    used_key = key
                    logger.info(f"Found wallet data using key format: {key}")
                    break
            
            if not wallet_data:
                # Try to get just the address from messaging format
                messaging_key = f"messaging:{platform}:user:{user_id}:wallet"
                address_data = await self.redis_client.get(messaging_key)
                
                if not address_data:
                    logger.info(f"No smart wallet found for {platform}:{user_id} under any key format")
                    return None
                
                # If we just have the address but not the full wallet data,
                # return minimal wallet info with the address
                address = address_data.decode('utf-8') if isinstance(address_data, bytes) else address_data
                logger.info(f"Found wallet address only for {platform}:{user_id}: {address}")
                
                return {
                    "address": address,
                    "user_id": user_id,
                    "platform": platform,
                    "wallet_type": "coinbase_cdp",
                    "chain": "base_sepolia"  # Default to base_sepolia
                }
            
            # Parse wallet data
            try:
                wallet_str = wallet_data.decode('utf-8') if isinstance(wallet_data, bytes) else wallet_data
                wallet_dict = json.loads(wallet_str)
                
                # Ensure required fields exist
                if not wallet_dict.get("address"):
                    logger.warning(f"Wallet data found but missing address for {platform}:{user_id}")
                    return None
                
                # Remove private key if present for security
                if "private_key" in wallet_dict:
                    wallet_dict = {k: v for k, v in wallet_dict.items() if k != "private_key"}
                
                logger.info(f"Successfully retrieved wallet data for {platform}:{user_id} - Address: {wallet_dict.get('address')}, Chain: {wallet_dict.get('chain', 'unknown')}")
                return wallet_dict
            except json.JSONDecodeError as e:
                logger.error(f"Error decoding wallet data for {platform}:{user_id} from key {used_key}: {e}")
                # Try to interpret as plain text address if JSON parsing fails
                try:
                    address = wallet_data.decode('utf-8') if isinstance(wallet_data, bytes) else wallet_data
                    if address and len(address) >= 40:  # Rough check for address-like string
                        return {
                            "address": address,
                            "user_id": user_id,
                            "platform": platform,
                            "wallet_type": "coinbase_cdp",
                            "chain": "base_sepolia"  # Default to base_sepolia
                        }
                except:
                    pass
                return None
        except Exception as e:
            logger.exception(f"Error retrieving smart wallet for {platform}:{user_id}: {e}")
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
    
    async def get_wallet_balance(self, user_id: str, platform: str, chain: str) -> Dict[str, Any]:
        """Get the balance of a user's smart wallet.
        
        Args:
            user_id: User ID
            platform: Platform identifier (e.g., "telegram")
            chain: Chain to use (e.g., "base_sepolia")
            
        Returns:
            Dict containing balance information
        """
        try:
            logger.info(f"Getting wallet balance for {platform}:{user_id} on chain {chain}")
            
            # Get wallet data
            wallet_data = await self.get_smart_wallet(user_id, platform)
            if not wallet_data or not wallet_data.get("address"):
                logger.warning(f"No wallet found for {platform}:{user_id}")
                return {
                    "success": False,
                    "error": "No wallet found",
                    "balance": "0",
                    "chain": chain
                }
                
            # Get wallet address
            wallet_address = wallet_data.get("address")
            wallet_chain = chain  # Use the provided chain parameter
            
            # Map chain to chain ID
            chain_id_map = {
                "base_sepolia": 84532,
                "base_mainnet": 8453,
                "ethereum_sepolia": 11155111,
                "ethereum_mainnet": 1
            }
            
            chain_id = chain_id_map.get(wallet_chain, 84532)  # Default to Base Sepolia
            
            # Create chain info for display
            chain_info = {
                "id": chain_id,
                "name": wallet_chain.replace("_", " ").title(),
                "is_testnet": "sepolia" in wallet_chain or "goerli" in wallet_chain
            }
            
            # Attempt to get balance using Web3
            try:
                from web3 import Web3
                
                # Choose provider based on chain
                if "base" in wallet_chain:
                    provider_url = "https://sepolia.base.org" if "sepolia" in wallet_chain else "https://mainnet.base.org"
                else:
                    provider_url = "https://rpc.ankr.com/eth_sepolia" if "sepolia" in wallet_chain else "https://rpc.ankr.com/eth"
                
                # Connect to Web3
                w3 = Web3(Web3.HTTPProvider(provider_url))
                
                # Check connection
                if not w3.is_connected():
                    logger.warning(f"Unable to connect to provider at {provider_url}")
                    return {
                        "success": False,
                        "error": f"Unable to connect to blockchain provider for {chain_info['name']}",
                        "address": wallet_address,
                        "chain": wallet_chain,
                        "chain_info": chain_info,
                        "balance": "0" 
                    }
                
                # Get ETH balance
                balance_wei = w3.eth.get_balance(wallet_address)
                balance_eth = w3.from_wei(balance_wei, 'ether')
                
                logger.info(f"Retrieved balance for {wallet_address} on {wallet_chain}: {balance_eth} ETH")
                
                return {
                    "success": True,
                    "address": wallet_address,
                    "chain": wallet_chain,
                    "chain_info": chain_info,
                    "balance": str(balance_eth),
                    "balance_wei": str(balance_wei)
                }
            except ImportError:
                logger.error("Web3 not available, cannot get accurate balance")
                return {
                    "success": False,
                    "error": "Web3 library not available",
                    "address": wallet_address,
                    "chain": wallet_chain,
                    "chain_info": chain_info,
                    "balance": "0"
                }
            except Exception as web3_error:
                logger.exception(f"Error getting balance with Web3: {web3_error}")
                return {
                    "success": False,
                    "error": f"Error retrieving balance: {str(web3_error)}",
                    "address": wallet_address,
                    "chain": wallet_chain,
                    "chain_info": chain_info,
                    "balance": "0"
                }
                
        except Exception as e:
            logger.exception(f"Error in get_wallet_balance: {e}")
            return {
                "success": False,
                "error": str(e),
                "chain": chain,
                "balance": "0"
            }
    
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
    
    async def switch_chain(self, user_id: str, platform: str, chain: str) -> Dict[str, Any]:
        """Switch the blockchain network for a user's wallet.
        
        Args:
            user_id: User ID
            platform: Platform identifier (e.g., "telegram")
            chain: New chain to use (e.g., "base_sepolia")
            
        Returns:
            Dict with success status and chain info
        """
        try:
            logger.info(f"Switching chain to {chain} for {platform}:{user_id}")
            
            # Get wallet data
            wallet_data = await self.get_smart_wallet(user_id, platform)
            if not wallet_data or not wallet_data.get("address"):
                logger.warning(f"No wallet found for {platform}:{user_id}")
                return {
                    "success": False,
                    "message": "No wallet found. Please create a wallet first using /connect"
                }
                
            # Get supported networks
            supported_chains = {
                "base_sepolia": {
                    "id": 84532,
                    "name": "Base Sepolia",
                    "is_testnet": True
                },
                "base_mainnet": {
                    "id": 8453,
                    "name": "Base Mainnet",
                    "is_testnet": False
                },
                "ethereum_sepolia": {
                    "id": 11155111,
                    "name": "Ethereum Sepolia",
                    "is_testnet": True
                },
                "ethereum_mainnet": {
                    "id": 1,
                    "name": "Ethereum Mainnet",
                    "is_testnet": False
                },
                "scroll_sepolia": {
                    "id": 534351,
                    "name": "Scroll Sepolia",
                    "is_testnet": True
                }
            }
            
            # Check if requested chain is supported
            if chain not in supported_chains:
                logger.warning(f"Unsupported chain requested: {chain}")
                return {
                    "success": False,
                    "message": f"Unsupported network: {chain}",
                    "supported_chains": list(supported_chains.keys())
                }
            
            # Get wallet address and retrieve full wallet data from Redis
            address = wallet_data.get("address")
            
            # Define all possible key formats to check
            possible_keys = [
                f"wallet:{platform}:{user_id}",
                f"smart_wallet:{platform}:{user_id}",
                f"cdp_wallet:{platform}:{user_id}"
            ]
            
            wallet_data_str = None
            used_key = None
            
            # Find the wallet data in Redis
            for key in possible_keys:
                data = await self.redis_client.get(key)
                if data:
                    wallet_data_str = data
                    used_key = key
                    logger.info(f"Found wallet data using key format: {key}")
                    break
            
            if not wallet_data_str or not used_key:
                logger.warning(f"Could not find wallet data in Redis for {platform}:{user_id}")
                return {
                    "success": False,
                    "message": "Could not find wallet data. Please reconnect your wallet using /connect"
                }
            
            # Parse wallet data and update chain
            try:
                wallet_dict = json.loads(wallet_data_str) if isinstance(wallet_data_str, bytes) else json.loads(wallet_data_str)
                
                # Update the chain
                wallet_dict["chain"] = chain
                
                # Save updated wallet data back to Redis
                await self.redis_client.set(used_key, json.dumps(wallet_dict))
                logger.info(f"Updated wallet chain to {chain} for {platform}:{user_id}")
                
                return {
                    "success": True,
                    "chain": chain,
                    "chain_info": supported_chains[chain],
                    "message": f"Successfully switched to {supported_chains[chain]['name']}"
                }
            except json.JSONDecodeError as e:
                logger.error(f"Error decoding wallet data: {e}")
                return {
                    "success": False,
                    "message": "Error processing wallet data"
                }
                
        except Exception as e:
            logger.exception(f"Error switching chain: {e}")
            return {
                "success": False,
                "message": f"Error switching network: {str(e)}"
            }
    
    async def get_supported_chains(self) -> List[Dict[str, Any]]:
        """Get a list of supported blockchain networks.
        
        Returns:
            List of supported chain information
        """
        # Return a list of supported chains
        return [
            {
                "id": "base_sepolia",
                "name": "Base Sepolia",
                "description": "Base L2 testnet",
                "chain_id": 84532,
                "is_testnet": True
            },
            {
                "id": "ethereum_sepolia",
                "name": "Ethereum Sepolia",
                "description": "Ethereum testnet",
                "chain_id": 11155111,
                "is_testnet": True
            },
            {
                "id": "scroll_sepolia",
                "name": "Scroll Sepolia",
                "description": "Scroll L2 testnet",
                "chain_id": 534351,
                "is_testnet": True
            }
        ] 
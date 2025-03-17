import os
import logging
import httpx
import json
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv
import redis.asyncio as redis
from app.core.config import settings

# Load environment variables
load_dotenv()
load_dotenv(".env.local", override=True)

logger = logging.getLogger(__name__)

# Particle Auth Configuration
PARTICLE_PROJECT_ID = os.getenv("PARTICLE_PROJECT_ID", "")
PARTICLE_CLIENT_KEY = os.getenv("PARTICLE_CLIENT_KEY", "")
PARTICLE_APP_ID = os.getenv("PARTICLE_APP_ID", "")

# Testnet Configuration
DEFAULT_CHAIN = "scroll_sepolia"
SUPPORTED_CHAINS = {
    "scroll_sepolia": {
        "name": "Scroll Sepolia",
        "chainId": 534351,
        "rpcUrl": "https://sepolia-rpc.scroll.io"
    },
    "base_sepolia": {
        "name": "Base Sepolia",
        "chainId": 84532,
        "rpcUrl": "https://sepolia.base.org"
    },
    "ethereum_sepolia": {
        "name": "Ethereum Sepolia",
        "chainId": 11155111,
        "rpcUrl": "https://ethereum-sepolia.publicnode.com"
    }
}

class WalletService:
    """
    Service for wallet operations, including creation, management,
    and network switching.
    """
    redis_client: Optional[redis.Redis] = None
    
    def __init__(self):
        """Initialize the wallet service."""
        # Initialize Redis connection if REDIS_URL is set
        if settings.REDIS_URL:
            try:
                self.redis_client = redis.from_url(settings.REDIS_URL)
                logger.info("Redis client initialized for WalletService")
            except Exception as e:
                logger.exception(f"Error initializing Redis client: {e}")
                self.redis_client = None
        else:
            logger.warning("REDIS_URL not set, wallet persistence disabled")
        
        self.http_client = httpx.AsyncClient(timeout=30.0)
        
        # Validate configuration
        if not all([PARTICLE_PROJECT_ID, PARTICLE_CLIENT_KEY, PARTICLE_APP_ID]):
            logger.warning("Particle Auth configuration incomplete. Smart wallet features will be limited.")
    
    async def get_supported_chains(self) -> List[Dict[str, Any]]:
        """
        Get list of supported blockchain networks.
        
        Returns:
            List of chain information dictionaries
        """
        # Return hardcoded list of supported chains
        return [
            {
                "id": "scroll_sepolia",
                "name": "Scroll Sepolia",
                "chainId": 534351,
                "rpc": "https://sepolia-rpc.scroll.io",
                "explorer": "https://sepolia.scrollscan.com",
                "description": "Scroll L2 testnet"
            },
            {
                "id": "base_sepolia",
                "name": "Base Sepolia",
                "chainId": 84532,
                "rpc": "https://sepolia.base.org",
                "explorer": "https://sepolia.basescan.org",
                "description": "Base L2 testnet"
            },
            {
                "id": "ethereum_sepolia",
                "name": "Ethereum Sepolia",
                "chainId": 11155111,
                "rpc": "https://ethereum-sepolia-rpc.publicnode.com",
                "explorer": "https://sepolia.etherscan.io",
                "description": "Ethereum testnet"
            }
        ]
    
    async def create_wallet(
        self,
        user_id: str,
        platform: str,
        wallet_address: str,
        chain: str = "scroll_sepolia"
    ) -> Dict[str, Any]:
        """
        Create a wallet for a user.
        
        Args:
            user_id: User ID
            platform: Platform identifier (e.g., "telegram", "web")
            wallet_address: Wallet address to associate with user
            chain: Chain ID to create the wallet on
            
        Returns:
            Dict with creation status
        """
        # Check if Redis is available
        if not self.redis_client:
            logger.warning("Redis not available, wallet creation not persisted")
            return {
                "success": True,
                "message": "Wallet created (not persisted)",
                "wallet_address": wallet_address,
                "chain": chain
            }
            
        try:
            # Create unique key for this user's wallet
            user_key = f"wallet:{platform}:{user_id}"
            
            # Get chain info
            chain_info = None
            chains = await self.get_supported_chains()
            for c in chains:
                if c["id"] == chain:
                    chain_info = c
                    break
                    
            if not chain_info:
                return {
                    "success": False,
                    "message": f"Unsupported chain: {chain}"
                }
                
            # Store wallet info in Redis
            wallet_info = {
                "user_id": user_id,
                "platform": platform,
                "wallet_address": wallet_address,
                "chain": chain,
                "chain_info": chain_info
            }
            
            await self.redis_client.set(
                user_key,
                json.dumps(wallet_info)
            )
            
            logger.info(f"Created wallet for {platform}:{user_id} on {chain}")
            
            return {
                "success": True,
                "message": "Wallet created successfully",
                "wallet_address": wallet_address,
                "chain": chain,
                "chain_info": chain_info
            }
            
        except Exception as e:
            logger.exception(f"Error creating wallet: {e}")
            return {
                "success": False,
                "message": f"Error creating wallet: {str(e)}"
            }
    
    async def get_wallet_info(self, user_id: str, platform: str) -> Optional[Dict[str, Any]]:
        """
        Get wallet information for a user.
        
        Args:
            user_id: User ID
            platform: Platform (telegram, whatsapp, etc.)
            
        Returns:
            Wallet information or None if not found
        """
        # Create the user key
        user_key = f"messaging:{platform}:user:{user_id}:wallet"
        
        try:
            # Get the wallet address
            wallet_data = await self.redis_client.get(user_key)
            
            if not wallet_data:
                logger.info(f"No wallet found for {platform}:{user_id}")
                return None
                
            # Parse the wallet data
            if wallet_data.startswith("{"):
                # Handle JSON wallet data
                try:
                    wallet_info = json.loads(wallet_data)
                    return wallet_info
                except json.JSONDecodeError:
                    # Fallback to treating it as a plain wallet address
                    wallet_address = wallet_data
            else:
                # Plain wallet address
                wallet_address = wallet_data
                
            # Get the current chain from wallet settings
            chain_key = f"messaging:{platform}:user:{user_id}:chain"
            chain = await self.redis_client.get(chain_key) or DEFAULT_CHAIN
            
            # Get chain info
            chain_info = self._get_chain_info(chain)
            
            # Return structured wallet info
            return {
                "wallet_address": wallet_address,
                "platform": platform,
                "user_id": user_id,
                "chain": chain,
                "chain_info": chain_info
            }
        except Exception as e:
            if "Event loop is closed" in str(e):
                # Handle event loop closed error in serverless environments
                logger.warning(f"Redis event loop closed, recreating client for {platform}:{user_id}")
                try:
                    # Recreate the Redis client
                    self.redis_client = self._create_redis_client()
                    # Try again with the new client
                    wallet_data = await self.redis_client.get(user_key)
                    if not wallet_data:
                        return None
                    
                    # Return a basic wallet info object
                    return {
                        "wallet_address": wallet_data,
                        "platform": platform,
                        "user_id": user_id,
                        "chain": DEFAULT_CHAIN,
                        "chain_info": self._get_chain_info(DEFAULT_CHAIN)
                    }
                except Exception as retry_error:
                    logger.error(f"Error retrying wallet info: {retry_error}")
                    return None
            else:
                logger.error(f"Error getting wallet info: {e}")
                return None

    def _create_redis_client(self):
        """Create a new Redis client instance."""
        import redis.asyncio as aioredis
        
        # Check if we're using Upstash
        if self.redis_url.startswith("rediss://"):
            # Upstash Redis with SSL
            from redis.asyncio.connection import Connection
            
            # Configure Redis for Upstash
            ssl_enabled = True
            logger.info("Using Upstash Redis client")
            return aioredis.from_url(self.redis_url, ssl=ssl_enabled, decode_responses=True)
        else:
            # Standard Redis
            logger.info("Using standard Redis client")
            return aioredis.from_url(self.redis_url, decode_responses=True)
    
    async def delete_wallet(self, user_id: str, platform: str) -> Dict[str, Any]:
        """
        Delete a wallet for a user.
        
        Args:
            user_id: User ID
            platform: Platform identifier
            
        Returns:
            Dict with deletion status
        """
        # Check if Redis is available
        if not self.redis_client:
            logger.warning("Redis not available, wallet deletion not persisted")
            return {
                "success": True,
                "message": "Wallet deleted (not persisted)"
            }
            
        try:
            # Delete wallet info from Redis
            user_key = f"wallet:{platform}:{user_id}"
            deleted = await self.redis_client.delete(user_key)
            
            if deleted:
                logger.info(f"Deleted wallet for {platform}:{user_id}")
                return {
                    "success": True,
                    "message": "Wallet deleted successfully"
                }
            else:
                logger.info(f"No wallet found to delete for {platform}:{user_id}")
                return {
                    "success": False,
                    "message": "No wallet found to delete"
                }
                
        except Exception as e:
            logger.exception(f"Error deleting wallet: {e}")
            return {
                "success": False,
                "message": f"Error deleting wallet: {str(e)}"
            }
    
    async def switch_chain(
        self,
        user_id: str,
        platform: str,
        chain: str
    ) -> Dict[str, Any]:
        """
        Switch the chain for a user's wallet.
        
        Args:
            user_id: User ID
            platform: Platform identifier
            chain: Chain ID to switch to
            
        Returns:
            Dict with switch status
        """
        # Check if Redis is available
        if not self.redis_client:
            logger.warning("Redis not available, chain switch not persisted")
            return {
                "success": False,
                "message": "Redis not available, chain switch not persisted"
            }
            
        try:
            # Get current wallet info
            wallet_info = await self.get_wallet_info(user_id, platform)
            if not wallet_info:
                return {
                    "success": False,
                    "message": "No wallet found for this user"
                }
                
            # Get chain info
            chain_info = None
            chains = await self.get_supported_chains()
            for c in chains:
                if c["id"] == chain:
                    chain_info = c
                    break
                    
            if not chain_info:
                return {
                    "success": False,
                    "message": f"Unsupported chain: {chain}"
                }
                
            # Update wallet info with new chain
            wallet_info["chain"] = chain
            wallet_info["chain_info"] = chain_info
            
            # Save updated wallet info
            user_key = f"wallet:{platform}:{user_id}"
            await self.redis_client.set(
                user_key,
                json.dumps(wallet_info)
            )
            
            logger.info(f"Switched chain for {platform}:{user_id} to {chain}")
            
            return {
                "success": True,
                "message": "Chain switched successfully",
                "chain": chain,
                "chain_info": chain_info
            }
            
        except Exception as e:
            logger.exception(f"Error switching chain: {e}")
            return {
                "success": False,
                "message": f"Error switching chain: {str(e)}"
            } 
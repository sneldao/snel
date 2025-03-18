import os
import logging
import httpx
import json
import time
import base64
import secrets
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
PARTICLE_API_BASE = "https://api.particle.network"

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
    redis_url: Optional[str] = None
    
    def __init__(self, redis_service=None, redis_url=None):
        """Initialize the wallet service."""
        if redis_service:
            self.redis_client = redis_service.client
        elif redis_url:
            self.redis_url = redis_url
            self._create_redis_client()
        else:
            self.redis_url = os.getenv("REDIS_URL", "")
            if self.redis_url:
                self._create_redis_client()
            
        # Check if Particle Auth is properly configured
        if not all([PARTICLE_PROJECT_ID, PARTICLE_CLIENT_KEY, PARTICLE_APP_ID]):
            logger.warning("Particle Auth configuration incomplete. Smart wallet features will be limited.")
    
    def _get_chain_info(self, chain_id: str) -> Dict[str, Any]:
        """Get chain information for the given chain ID."""
        chain_info = SUPPORTED_CHAINS.get(chain_id, SUPPORTED_CHAINS[DEFAULT_CHAIN])
        return {
            "id": chain_id,
            "name": chain_info["name"],
            "chainId": chain_info["chainId"],
            "rpcUrl": chain_info["rpcUrl"]
        }
    
    async def get_supported_chains(self) -> List[Dict[str, Any]]:
        """Get list of supported chains with their details."""
        chains = []
        for chain_id, chain_info in SUPPORTED_CHAINS.items():
            chains.append({
                "id": chain_id,
                "name": chain_info["name"],
                "chainId": chain_info["chainId"],
                "rpcUrl": chain_info["rpcUrl"]
            })
        return chains

    async def _create_particle_auth_token(self, user_id: str, platform: str) -> Optional[str]:
        """
        Create a Particle Auth token for a user.
        
        Args:
            user_id: User ID
            platform: Platform identifier
            
        Returns:
            Auth token or None if creation failed
        """
        if not all([PARTICLE_PROJECT_ID, PARTICLE_CLIENT_KEY, PARTICLE_APP_ID]):
            logger.warning("Particle Auth configuration incomplete. Unable to create auth token.")
            return None
            
        try:
            # Create a unique ID for this user based on platform and user_id
            unique_id = f"{platform}_{user_id}"
            
            # Generate a timestamp for the token
            timestamp = int(time.time())
            
            # Create payload for Particle Auth
            payload = {
                "projectUuid": PARTICLE_PROJECT_ID,
                "appUuid": PARTICLE_APP_ID,
                "userInfo": {
                    "uuid": unique_id
                },
                "timestamp": timestamp
            }
            
            # Make API request to Particle Auth to get token
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{PARTICLE_API_BASE}/server/auth-service/token",
                    json=payload,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": PARTICLE_CLIENT_KEY
                    }
                )
                
                if response.status_code != 200:
                    logger.error(f"Error creating Particle Auth token: {response.text}")
                    return None
                    
                result = response.json()
                return result.get("token")
                
        except Exception as e:
            logger.exception(f"Error creating Particle Auth token: {e}")
            return None

    async def _create_particle_wallet(self, user_id: str, platform: str, chain: str) -> Optional[Dict[str, Any]]:
        """
        Create a wallet using Particle Auth.
        
        Args:
            user_id: User ID
            platform: Platform identifier
            chain: Chain ID to create the wallet on
            
        Returns:
            Dict with wallet info or None if creation failed
        """
        try:
            # Get chain ID for the request
            chain_info = self._get_chain_info(chain)
            chain_id = chain_info["chainId"]
            
            # Generate a secure entropy for wallet creation
            entropy = base64.b64encode(secrets.token_bytes(32)).decode('utf-8')
            
            # Create a unique user ID - removing special characters for UUID format
            unique_id = f"{platform}_{user_id}"
            unique_id = unique_id.replace('-', '').replace('_', '')[:32]
            
            # Create payload for Particle wallet creation using server RPC API
            # Note: the projectId should NOT have hyphens in the RPC format
            clean_project_id = PARTICLE_PROJECT_ID.replace('-', '')
            
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "particle_aa_createWallet",
                "params": [
                    {
                        "projectId": clean_project_id,
                        "chainId": chain_id,
                        "userUuid": unique_id,
                        "entropy": entropy
                    }
                ]
            }
            
            logger.info(f"Creating wallet with payload: {json.dumps(payload)}")
            
            # Make API request to create wallet
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{PARTICLE_API_BASE}/server/rpc",
                    json=payload,
                    headers={
                        "Content-Type": "application/json",
                        "PN-Project-Id": PARTICLE_PROJECT_ID,
                        "PN-Secret": PARTICLE_CLIENT_KEY
                    }
                )
                
                if response.status_code != 200:
                    logger.error(f"Error creating Particle wallet: {response.text}")
                    return None
                
                result = response.json()
                
                # Check for error in the RPC response
                if "error" in result:
                    error_msg = result.get("error", {}).get("message", "Unknown error")
                    logger.error(f"RPC error creating wallet: {error_msg}")
                    return None
                
                # Extract address from result
                wallet_data = result.get("result", {})
                wallet_address = wallet_data.get("smartAccount")
                
                if not wallet_address:
                    logger.error("No wallet address returned from Particle API")
                    return None
                    
                return {
                    "wallet_address": wallet_address,
                    "master_key": wallet_data.get("masterKey", ""),
                    "user_uuid": unique_id
                }
                
        except Exception as e:
            logger.exception(f"Error creating Particle wallet: {e}")
            return None
            
    async def create_wallet(
        self,
        user_id: str,
        platform: str,
        wallet_address: Optional[str] = None,
        chain: str = DEFAULT_CHAIN
    ) -> Dict[str, Any]:
        """
        Create a wallet for a user.
        
        Args:
            user_id: User ID
            platform: Platform identifier (e.g., "telegram", "web")
            wallet_address: Optional wallet address to associate with user
                           (if not provided, a new wallet will be created)
            chain: Chain ID to create the wallet on
            
        Returns:
            Dict with creation status
        """
        # Check if Redis is available
        if not self.redis_client:
            logger.warning("Redis not available, attempting to reconnect")
            self._create_redis_client()
            
            if not self.redis_client:
                logger.warning("Redis reconnection failed, wallet creation not persisted")
                if wallet_address:
                    return {
                        "success": True,
                        "message": "Wallet created (not persisted)",
                        "wallet_address": wallet_address,
                        "chain": chain
                    }
                else:
                    return {
                        "success": False,
                        "message": "Redis not available and no wallet address provided"
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
            
            # If wallet address is provided, just use it (this is typically for migrating existing wallets)
            if wallet_address:
                wallet_info = {
                    "user_id": user_id,
                    "platform": platform,
                    "wallet_address": wallet_address,
                    "wallet_type": "imported",
                    "chain": chain,
                    "chain_info": chain_info
                }
                
                await self.redis_client.set(
                    user_key,
                    json.dumps(wallet_info)
                )
                
                # Store reverse mapping for lookups
                await self.redis_client.set(
                    f"address:{wallet_address}:user",
                    json.dumps({"user_id": user_id, "platform": platform})
                )
                
                # Store messaging format too (for compatibility)
                messaging_key = f"messaging:{platform}:user:{user_id}:wallet"
                await self.redis_client.set(
                    messaging_key,
                    wallet_address  # Just store address string for compatibility
                )
                
                logger.info(f"Imported wallet {wallet_address} for {platform}:{user_id} on {chain}")
                
                return {
                    "success": True,
                    "message": "Wallet imported successfully",
                    "wallet_address": wallet_address,
                    "wallet_type": "imported",
                    "chain": chain,
                    "chain_info": chain_info
                }
            
            # For new wallet creation, require Particle Auth
            if not all([PARTICLE_PROJECT_ID, PARTICLE_CLIENT_KEY, PARTICLE_APP_ID]):
                logger.error("Particle Auth not configured, cannot create new wallet")
                return {
                    "success": False,
                    "message": "Wallet creation requires Particle Auth, which is not properly configured."
                }
            
            # Create wallet with Particle Auth
            particle_result = await self._create_particle_wallet(user_id, platform, chain)
            if not particle_result:
                logger.error("Failed to create Particle wallet")
                return {
                    "success": False,
                    "message": "Failed to create wallet with Particle Auth."
                }
                
            wallet_address = particle_result["wallet_address"]
            logger.info(f"Created Particle wallet {wallet_address} for {platform}:{user_id}")
            
            # Store wallet info in Redis
            wallet_info = {
                "user_id": user_id,
                "platform": platform,
                "wallet_address": wallet_address,
                "wallet_type": "particle",
                "chain": chain,
                "chain_info": chain_info,
                "master_key": particle_result.get("master_key", "")
            }
            
            await self.redis_client.set(
                user_key,
                json.dumps(wallet_info)
            )
            
            # Store messaging format too (for compatibility)
            messaging_key = f"messaging:{platform}:user:{user_id}:wallet"
            await self.redis_client.set(
                messaging_key,
                wallet_address  # Just store address string for compatibility
            )
            
            # Store reverse mapping for lookups
            await self.redis_client.set(
                f"address:{wallet_address}:user",
                json.dumps({"user_id": user_id, "platform": platform})
            )
            
            logger.info(f"Created wallet for {platform}:{user_id} on {chain}")
            
            return {
                "success": True,
                "message": "Wallet created successfully",
                "wallet_address": wallet_address,
                "wallet_type": "particle",
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
        # Check if Redis client is available
        if not self.redis_client:
            logger.warning("Redis client not available, attempting reconnection")
            self._create_redis_client()
            if not self.redis_client:
                logger.warning("Redis reconnection failed, returning no wallet info")
                return None
        
        # Create the user key
        user_key = f"messaging:{platform}:user:{user_id}:wallet"
        
        try:
            # Get the wallet address
            wallet_data = await self.redis_client.get(user_key)
            
            if not wallet_data:
                logger.info(f"No wallet found for {platform}:{user_id}")
                return None
                
            # Convert bytes to string if needed
            if isinstance(wallet_data, bytes):
                wallet_data = wallet_data.decode('utf-8')
                
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
            
            # Convert bytes to string if needed
            if isinstance(chain, bytes):
                chain = chain.decode('utf-8')
            
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
                    self._create_redis_client()
                    # Try again with the new client
                    wallet_data = await self.redis_client.get(user_key)
                    if not wallet_data:
                        return None
                    
                    # Convert bytes to string if needed
                    if isinstance(wallet_data, bytes):
                        wallet_data = wallet_data.decode('utf-8')
                    
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
        """
        Create a Redis client for wallet storage.
        """
        try:
            if not self.redis_url:
                logger.warning("Redis URL not provided to WalletService")
                return None
                
            logger.info(f"Creating Redis client with URL: {self.redis_url[:15]}...")
            
            # Create Redis client with SSL disabled if needed (for development)
            if os.getenv("DISABLE_SSL_VERIFY", "").lower() in ("true", "1", "yes"):
                self.redis_client = redis.from_url(
                    self.redis_url,
                    ssl_cert_reqs=None
                )
            else:
                # For Upstash Redis, we need to explicitly set ssl_cert_reqs
                if "upstash" in self.redis_url.lower():
                    self.redis_client = redis.from_url(
                        self.redis_url,
                        ssl_cert_reqs=None
                    )
                else:
                    self.redis_client = redis.from_url(self.redis_url)
                
            logger.info("Redis client created successfully")
            return self.redis_client
            
        except Exception as e:
            logger.exception(f"Error creating Redis client: {e}")
            self.redis_client = None
            return None
    
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
            logger.warning("Redis not available, attempting reconnection")
            self._create_redis_client()
            if not self.redis_client:
                logger.warning("Redis reconnection failed, wallet deletion not persisted")
                return {
                    "success": True,
                    "message": "Wallet deletion request processed (not persisted)"
                }
            
        try:
            # We need to handle both storage formats:
            # 1. wallet:{platform}:{user_id} (main format)
            # 2. messaging:{platform}:user:{user_id}:wallet (messaging format)
            
            # First, get the wallet address to delete reverse mapping
            wallet_info = await self.get_wallet_info(user_id, platform)
            wallet_address = None
            if wallet_info and "wallet_address" in wallet_info:
                wallet_address = wallet_info["wallet_address"]
            
            # Delete main wallet format
            user_key = f"wallet:{platform}:{user_id}"
            try:
                await self.redis_client.delete(user_key)
                logger.info(f"Deleted main wallet key: {user_key}")
            except Exception as e:
                # Handle non-async Redis clients that return int instead of awaitable
                if isinstance(e, TypeError) and "await" in str(e):
                    try:
                        self.redis_client.delete(user_key)
                        logger.info(f"Deleted main wallet key with non-async call: {user_key}")
                    except Exception as e2:
                        logger.error(f"Failed to delete main wallet key: {e2}")
                else:
                    logger.error(f"Failed to delete main wallet key: {e}")
            
            # Delete messaging format
            messaging_key = f"messaging:{platform}:user:{user_id}:wallet"
            try:
                await self.redis_client.delete(messaging_key)
                logger.info(f"Deleted messaging wallet key: {messaging_key}")
            except Exception as e:
                # Handle non-async Redis clients
                if isinstance(e, TypeError) and "await" in str(e):
                    try:
                        self.redis_client.delete(messaging_key)
                        logger.info(f"Deleted messaging wallet key with non-async call: {messaging_key}")
                    except Exception as e2:
                        logger.error(f"Failed to delete messaging wallet key: {e2}")
                else:
                    logger.error(f"Failed to delete messaging wallet key: {e}")
            
            # Delete reverse mapping if we have a wallet address
            if wallet_address:
                try:
                    await self.redis_client.delete(f"address:{wallet_address}:user")
                    logger.info(f"Deleted reverse address mapping for {wallet_address}")
                except Exception as e:
                    # Handle non-async Redis clients
                    if isinstance(e, TypeError) and "await" in str(e):
                        try:
                            self.redis_client.delete(f"address:{wallet_address}:user")
                            logger.info(f"Deleted reverse mapping with non-async call: {wallet_address}")
                        except Exception as e2:
                            logger.error(f"Failed to delete reverse mapping: {e2}")
                    else:
                        logger.error(f"Failed to delete reverse mapping: {e}")
            
            logger.info(f"Deleted wallet for {platform}:{user_id}")
            return {
                "success": True,
                "message": "Wallet deleted successfully"
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
            logger.warning("Redis not available, attempting reconnection")
            self._create_redis_client()
            if not self.redis_client:
                logger.warning("Redis reconnection failed, chain switch not persisted")
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
            
            # Update chain key separately for messaging format
            chain_key = f"messaging:{platform}:user:{user_id}:chain"
            await self.redis_client.set(
                chain_key,
                chain
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
import os
import logging
import json
import time
import secrets
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv
import redis.asyncio as redis

# Load environment variables
load_dotenv()
load_dotenv(".env.local", override=True)

logger = logging.getLogger(__name__)

# Testnet Configuration
DEFAULT_CHAIN = "base_sepolia"
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
    Service for basic wallet operations and network switching.
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
        chains.extend(
            {
                "id": chain_id,
                "name": chain_info["name"],
                "chainId": chain_info["chainId"],
                "rpcUrl": chain_info["rpcUrl"],
            }
            for chain_id, chain_info in SUPPORTED_CHAINS.items()
        )
        return chains
            
    async def create_wallet(
        self,
        user_id: str,
        platform: str,
        wallet_address: Optional[str] = None,
        chain: str = DEFAULT_CHAIN
    ) -> Dict[str, Any]:
        """
        Create or import a wallet for a user.
        
        Args:
            user_id: User ID
            platform: Platform identifier (e.g., "telegram", "web")
            wallet_address: Optional wallet address to associate with user
            chain: Chain ID to create the wallet on
            
        Returns:
            Dict with creation status
        """
        try:
            # Check if Redis is available
            if not self.redis_client:
                logger.warning("Redis not available, attempting reconnection")
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

            # Create unique key for this user's wallet
            user_key = f"wallet:{platform}:{user_id}"

            chains = await self.get_supported_chains()
            chain_info = next((c for c in chains if c["id"] == chain), None)
            if not chain_info:
                return {
                    "success": False,
                    "message": f"Unsupported chain: {chain}"
                }

            # If wallet address is provided, just use it
            if wallet_address:
                wallet_info = {
                    "user_id": user_id,
                    "platform": platform,
                    "wallet_address": wallet_address,
                    "wallet_type": "imported",
                    "chain": chain,
                    "chain_info": chain_info
                }

                try:
                    # Store wallet info
                    await self.redis_client.set(
                        user_key,
                        json.dumps(wallet_info)
                    )

                    # Store reverse mapping
                    await self.redis_client.set(
                        f"address:{wallet_address}:user",
                        json.dumps({"user_id": user_id, "platform": platform})
                    )

                    # Store messaging format
                    messaging_key = f"messaging:{platform}:user:{user_id}:wallet"
                    await self.redis_client.set(
                        messaging_key,
                        wallet_address
                    )
                except Exception as e:
                    logger.error(f"Error storing wallet data: {e}")
                    return {
                        "success": False,
                        "message": f"Error storing wallet data: {str(e)}"
                    }

                logger.info(f"Imported wallet {wallet_address} for {platform}:{user_id} on {chain}")

                return {
                    "success": True,
                    "message": "Wallet imported successfully",
                    "wallet_address": wallet_address,
                    "wallet_type": "imported",
                    "chain": chain,
                    "chain_info": chain_info
                }

            return {
                "success": False,
                "message": "Wallet address is required"
            }

        except Exception as e:
            logger.exception(f"Error in create_wallet: {e}")
            return {
                "success": False,
                "message": f"Error creating wallet: {str(e)}"
            }

    async def get_wallet_info(self, user_id: str, platform: str) -> Optional[Dict[str, Any]]:
        """
        Get wallet information for a user.
        
        Args:
            user_id: User ID
            platform: Platform identifier
            
        Returns:
            Dict with wallet info or None if not found
        """
        try:
            if not self.redis_client:
                return None

            # Try to get wallet info from Redis
            user_key = f"wallet:{platform}:{user_id}"
            wallet_data = await self.redis_client.get(user_key)

            if not wallet_data:
                # Try messaging format
                messaging_key = f"messaging:{platform}:user:{user_id}:wallet"
                wallet_address = await self.redis_client.get(messaging_key)
                
                if wallet_address:
                    if isinstance(wallet_address, bytes):
                        wallet_address = wallet_address.decode('utf-8')
                    return {
                        "wallet_address": wallet_address,
                        "chain": DEFAULT_CHAIN
                    }
                return None

            try:
                if isinstance(wallet_data, bytes):
                    wallet_data = wallet_data.decode('utf-8')
                return json.loads(wallet_data)
            except json.JSONDecodeError:
                logger.error(f"Invalid wallet data for {platform}:{user_id}: {wallet_data}")
                return None

        except Exception as e:
            logger.exception(f"Error getting wallet info: {e}")
            return None

    def _create_redis_client(self):
        """Create Redis client connection."""
        try:
            if not self.redis_url:
                logger.warning("No Redis URL provided")
                return

            self.redis_client = redis.from_url(self.redis_url)
            logger.info("Redis client created successfully")
        except Exception as e:
            logger.error(f"Error creating Redis client: {e}")
            self.redis_client = None

    async def delete_wallet(self, user_id: str, platform: str) -> Dict[str, Any]:
        """
        Delete a user's wallet.
        
        Args:
            user_id: User ID
            platform: Platform identifier
            
        Returns:
            Dict with deletion status
        """
        try:
            if not self.redis_client:
                return {
                    "success": False,
                    "message": "Redis not available"
                }

            # Get wallet info first
            wallet_info = await self.get_wallet_info(user_id, platform)
            if not wallet_info:
                return {
                    "success": True,
                    "message": "No wallet found to delete"
                }

            # Delete all wallet-related keys
            keys_to_delete = [
                f"wallet:{platform}:{user_id}",
                f"messaging:{platform}:user:{user_id}:wallet"
            ]

            wallet_address = wallet_info.get("wallet_address")
            if wallet_address:
                keys_to_delete.append(f"address:{wallet_address}:user")

            # Delete all keys
            for key in keys_to_delete:
                await self.redis_client.delete(key)

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
            chain: Chain to switch to
            
        Returns:
            Dict with switch status
        """
        try:
            # Get current wallet info
            wallet_info = await self.get_wallet_info(user_id, platform)
            if not wallet_info:
                return {
                    "success": False,
                    "message": "No wallet found"
                }

            # Validate chain
            chain_info = self._get_chain_info(chain)
            if not chain_info:
                return {
                    "success": False,
                    "message": f"Unsupported chain: {chain}"
                }

            # Update wallet info with new chain
            wallet_info["chain"] = chain
            wallet_info["chain_info"] = chain_info

            # Save updated wallet info
            if self.redis_client:
                user_key = f"wallet:{platform}:{user_id}"
                await self.redis_client.set(
                    user_key,
                    json.dumps(wallet_info)
                )

            return {
                "success": True,
                "message": f"Switched to {chain_info['name']}",
                "chain": chain,
                "chain_info": chain_info
            }

        except Exception as e:
            logger.exception(f"Error switching chain: {e}")
            return {
                "success": False,
                "message": f"Error switching chain: {str(e)}"
            } 
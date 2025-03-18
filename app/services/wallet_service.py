import os
import logging
import json
import time
import secrets
import base64
import aiohttp
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv
import redis.asyncio as redis
from app.core.config import settings

# Load environment variables
load_dotenv()
load_dotenv(".env.local", override=True)

logger = logging.getLogger(__name__)

# Coinbase CDP Configuration
CDP_API_KEY_NAME = os.getenv("CDP_API_KEY_NAME", "")
CDP_API_KEY_PRIVATE_KEY = os.getenv("CDP_API_KEY_PRIVATE_KEY", "")
USE_CDP_SDK = os.getenv("USE_CDP_SDK", "").lower() in ("true", "1", "yes")
CDP_VERIFY_SSL = os.getenv("CDP_VERIFY_SSL", "true").lower() not in ("false", "0", "no")

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
            
        # Check if Coinbase CDP is properly configured
        if not all([CDP_API_KEY_NAME, CDP_API_KEY_PRIVATE_KEY]):
            logger.warning("Coinbase CDP configuration incomplete. Smart wallet features will be limited.")
    
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

    async def _create_simulated_wallet(self, user_id: str, platform: str, chain: str) -> Optional[Dict[str, Any]]:
        """
        Create a simulated wallet (fallback when CDP is not available).
        
        Args:
            user_id: User ID
            platform: Platform identifier
            chain: Chain ID to create the wallet on
            
        Returns:
            Dict with wallet info or None if creation failed
        """
        try:
            # Generate a random Ethereum address
            random_bytes = secrets.token_bytes(20)
            wallet_address = f"0x{random_bytes.hex()}"

            return {
                "wallet_address": wallet_address,
                "wallet_type": "simulated"
            }

        except Exception as e:
            logger.exception(f"Error creating simulated wallet: {e}")
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

            # For new wallet creation, use simulated wallet
            wallet_result = await self._create_simulated_wallet(user_id, platform, chain)
            if not wallet_result:
                logger.error("Failed to create simulated wallet")
                return {
                    "success": False,
                    "message": "Failed to create wallet."
                }

            wallet_address = wallet_result["wallet_address"]
            logger.info(f"Created simulated wallet {wallet_address} for {platform}:{user_id}")

            # Store wallet info in Redis
            wallet_info = {
                "user_id": user_id,
                "platform": platform,
                "wallet_address": wallet_address,
                "wallet_type": "simulated",
                "chain": chain,
                "chain_info": chain_info
            }

            try:
                # Store wallet info
                await self.redis_client.set(
                    user_key,
                    json.dumps(wallet_info)
                )

                # Store messaging format
                messaging_key = f"messaging:{platform}:user:{user_id}:wallet"
                await self.redis_client.set(
                    messaging_key,
                    wallet_address
                )

                # Store reverse mapping
                await self.redis_client.set(
                    f"address:{wallet_address}:user",
                    json.dumps({"user_id": user_id, "platform": platform})
                )
            except Exception as e:
                logger.error(f"Error storing wallet data: {e}")
                return {
                    "success": False,
                    "message": f"Error storing wallet data: {str(e)}"
                }

            logger.info(f"Created wallet for {platform}:{user_id} on {chain}")

            return {
                "success": True,
                "message": "Wallet created successfully",
                "wallet_address": wallet_address,
                "wallet_type": "simulated",
                "chain": chain,
                "chain_info": chain_info
            }

        except Exception as e:
            logger.exception(f"Error creating wallet: {e}")
            return {
                "success": False,
                "message": f"Error creating wallet: {str(e)}"
            }

    async def get_wallet(self, user_id: str, platform: str) -> Dict[str, Any]:
        """
        Get wallet information for a user.
        
        Args:
            user_id: User ID
            platform: Platform (telegram, whatsapp, etc.)
            
        Returns:
            Dict with wallet information
        """
        wallet_info = await self.get_wallet_info(user_id, platform)
        
        if not wallet_info:
            return {
                "success": False,
                "message": "No wallet found for this user"
            }
        
        # Get wallet address and chain
        wallet_address = wallet_info.get("wallet_address")
        chain = wallet_info.get("chain", DEFAULT_CHAIN)
        chain_info = wallet_info.get("chain_info", self._get_chain_info(chain))
        
        return {
            "success": True,
            "wallet_address": wallet_address,
            "chain": chain,
            "chain_info": chain_info
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
    
    async def get_wallet_balance(self, user_id: str, platform: str, chain: Optional[str] = None) -> Dict[str, Any]:
        """
        Get balance for a user's wallet.
        
        Args:
            user_id: User ID
            platform: Platform identifier
            chain: Optional chain ID to check balance on
            
        Returns:
            Dict with balance information
        """
        # First get the wallet info
        wallet_info = await self.get_wallet_info(user_id, platform)

        if not wallet_info:
            return {
                "success": False,
                "message": "No wallet found for this user"
            }

        wallet_address = wallet_info.get("wallet_address")

        # Use provided chain or fallback to the one in wallet info
        if not chain:
            chain = wallet_info.get("chain", DEFAULT_CHAIN)

        chains = await self.get_supported_chains()
        chain_info = next((c for c in chains if c["id"] == chain), None)
        if not chain_info:
            return {
                "success": False,
                "message": f"Unsupported chain: {chain}"
            }

        # For simulated wallets, return a default balance
        wallet_type = wallet_info.get("wallet_type", "standard")
        if wallet_type == "simulated":
            return {
                "success": True,
                "message": "Simulated wallet balance",
                "wallet_address": wallet_address,
                "chain": chain,
                "chain_info": chain_info,
                "balance": {
                    "eth": "0.1",
                    "tokens": [
                        {
                            "symbol": "USDC",
                            "balance": "10.0",
                            "address": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
                        }
                    ]
                }
            }

        # For real wallets, we would fetch the balance from a blockchain provider
        # In this example, we'll just return a simulated balance
        return {
            "success": True,
            "message": "Wallet balance",
            "wallet_address": wallet_address,
            "chain": chain,
            "chain_info": chain_info,
            "balance": {
                "eth": "0.05",
                "tokens": []
            }
        }

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
                    ssl_cert_reqs=None,
                    decode_responses=True
                )
            elif "upstash" in self.redis_url.lower():
                self.redis_client = redis.from_url(
                    self.redis_url,
                    ssl_cert_reqs=None,
                    decode_responses=True
                )
            else:
                self.redis_client = redis.from_url(
                    self.redis_url,
                    decode_responses=True
                )

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

            chains = await self.get_supported_chains()
            chain_info = next((c for c in chains if c["id"] == chain), None)
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
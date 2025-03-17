import os
import logging
import httpx
import json
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv

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
    Service for managing user wallets with Particle Auth.
    Ensures that users maintain full control of their keys at all times.
    """
    
    def __init__(self, redis_service=None):
        self.redis_service = redis_service
        self.http_client = httpx.AsyncClient(timeout=30.0)
        
        # Validate configuration
        if not all([PARTICLE_PROJECT_ID, PARTICLE_CLIENT_KEY, PARTICLE_APP_ID]):
            logger.warning("Particle Auth configuration incomplete. Smart wallet features will be limited.")
    
    async def create_wallet(self, user_id: str, platform: str, chain: str = DEFAULT_CHAIN) -> Dict[str, Any]:
        """
        Create a new wallet for a user on the specified chain.
        Uses Particle Auth to generate wallet where user maintains control of keys.
        
        Returns a dict with wallet info and connection details.
        """
        logger.info(f"Creating wallet for user {user_id} on {chain}")
        
        # Ensure chain is supported
        if chain not in SUPPORTED_CHAINS:
            chain = DEFAULT_CHAIN
            
        chain_info = SUPPORTED_CHAINS[chain]
        
        try:
            # Generate unique auth parameters for this user
            # These parameters are used for client-side wallet initialization
            # NO private keys are stored on our server
            auth_params = {
                "projectId": PARTICLE_PROJECT_ID,
                "clientKey": PARTICLE_CLIENT_KEY,
                "appId": PARTICLE_APP_ID,
                "userId": f"{platform}_{user_id}",
                "chainId": chain_info["chainId"],
                "authType": "telegram"
            }
            
            # For Telegram, we can't store the actual wallet directly
            # Instead, we store the parameters needed for the user to initialize their wallet
            # The private key material is never exposed to our server
            
            # Store auth parameters in Redis for future reference
            if self.redis_service:
                key = f"wallet:{platform}:user:{user_id}:auth_params"
                await self.redis_service.set(key, json.dumps(auth_params))
                
                # Also store the chosen chain
                chain_key = f"wallet:{platform}:user:{user_id}:chain"
                await self.redis_service.set(chain_key, chain)
            
            # Return auth parameters and connection info
            # The actual wallet address will be created on the client side
            return {
                "success": True,
                "message": "Wallet initialization parameters created successfully",
                "auth_params": auth_params,
                "chain": chain,
                "chain_info": chain_info
            }
            
        except Exception as e:
            logger.exception(f"Error creating wallet: {e}")
            return {
                "success": False,
                "message": f"Error creating wallet: {str(e)}"
            }
    
    async def get_wallet_info(self, user_id: str, platform: str) -> Dict[str, Any]:
        """
        Get wallet information for a user.
        """
        logger.info(f"Getting wallet info for user {user_id} on {platform}")
        
        try:
            # Retrieve auth parameters from Redis
            if not self.redis_service:
                return {"success": False, "message": "Redis service not available"}
                
            key = f"wallet:{platform}:user:{user_id}:auth_params"
            auth_params_json = await self.redis_service.get(key)
            
            if not auth_params_json:
                return {
                    "success": False,
                    "message": "No wallet found for this user",
                    "has_wallet": False
                }
            
            auth_params = json.loads(auth_params_json)
            
            # Get current chain
            chain_key = f"wallet:{platform}:user:{user_id}:chain"
            chain = await self.redis_service.get(chain_key) or DEFAULT_CHAIN
            
            # Return wallet info
            return {
                "success": True,
                "message": "Wallet info retrieved successfully",
                "has_wallet": True,
                "auth_params": auth_params,
                "chain": chain,
                "chain_info": SUPPORTED_CHAINS.get(chain, SUPPORTED_CHAINS[DEFAULT_CHAIN])
            }
            
        except Exception as e:
            logger.exception(f"Error getting wallet info: {e}")
            return {
                "success": False,
                "message": f"Error retrieving wallet info: {str(e)}"
            }
    
    async def switch_chain(self, user_id: str, platform: str, chain: str) -> Dict[str, Any]:
        """
        Switch the current chain for a user's wallet.
        """
        logger.info(f"Switching chain to {chain} for user {user_id} on {platform}")
        
        # Ensure chain is supported
        if chain not in SUPPORTED_CHAINS:
            return {
                "success": False,
                "message": f"Chain {chain} not supported. Supported chains: {', '.join(SUPPORTED_CHAINS.keys())}"
            }
        
        try:
            # Check if user has a wallet
            wallet_info = await self.get_wallet_info(user_id, platform)
            if not wallet_info.get("has_wallet", False):
                return {
                    "success": False,
                    "message": "No wallet found for this user. Please create a wallet first."
                }
            
            # Update the chain in Redis
            if self.redis_service:
                chain_key = f"wallet:{platform}:user:{user_id}:chain"
                await self.redis_service.set(chain_key, chain)
            
            # Return success
            return {
                "success": True,
                "message": f"Switched to {SUPPORTED_CHAINS[chain]['name']} successfully",
                "chain": chain,
                "chain_info": SUPPORTED_CHAINS[chain]
            }
            
        except Exception as e:
            logger.exception(f"Error switching chain: {e}")
            return {
                "success": False,
                "message": f"Error switching chain: {str(e)}"
            }
    
    async def get_supported_chains(self) -> List[Dict[str, Any]]:
        """
        Get a list of supported chains.
        """
        return [
            {
                "id": chain_id,
                "name": chain_info["name"],
                "chainId": chain_info["chainId"],
                "isDefault": chain_id == DEFAULT_CHAIN
            }
            for chain_id, chain_info in SUPPORTED_CHAINS.items()
        ] 
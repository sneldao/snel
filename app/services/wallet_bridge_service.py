import os
import json
import logging
import asyncio
import uuid
from typing import Dict, Optional, Any, List
from datetime import datetime, timedelta
from redis import asyncio as aioredis
from eth_account.messages import encode_defunct
from web3 import Web3

logger = logging.getLogger(__name__)

class WalletBridgeService:
    """Service for managing wallet connections via web3 bridge."""
    
    def __init__(self, redis_url: Optional[str] = None):
        """Initialize the wallet bridge service.
        
        Args:
            redis_url: Redis URL for storing pending transactions
        """
        self.redis_url = redis_url
        self.redis_client = None
        
        # Get environment variables for bridge URL and bot name
        self.bridge_url = os.getenv("WALLET_BRIDGE_URL", "http://localhost:8000/static/wallet-bridge.html")
        self.bot_name = os.getenv("BOT_USERNAME", "pointless_snel_bot")
        
        logger.info(f"WalletBridgeService initialized with bridge URL: {self.bridge_url}")
        logger.info(f"Bot username set to: {self.bot_name}")
        
    async def connect_redis(self) -> bool:
        """Connect to Redis if URL is provided."""
        if not self.redis_url:
            logger.warning("No Redis URL provided. Transaction data will not be persisted.")
            return False
        
        try:
            self.redis_client = await aioredis.from_url(
                self.redis_url,
                decode_responses=True
            )
            await self.redis_client.ping()
            logger.info("Connected to Redis successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.redis_client = None
            return False
            
    async def create_transaction_request(
        self,
        user_id: str,
        platform: str,
        transaction_data: Dict[str, Any],
        transaction_type: str = "transaction"
    ) -> Dict[str, Any]:
        """Create a new transaction request.
        
        Args:
            user_id: User ID (e.g., Telegram user ID)
            platform: Platform identifier (e.g., "telegram")
            transaction_data: Transaction data to be signed
            transaction_type: Type of request ("transaction" or "signature")
            
        Returns:
            Dict with transaction info and URL
        """
        try:
            if not self.redis_client:
                await self.connect_redis()
                
            # Generate a unique transaction ID
            tx_id = f"tx:{platform}:{user_id}:{datetime.now().timestamp()}"
            
            # Store transaction data in Redis with 1 hour expiry
            tx_data = {
                "id": tx_id,
                "user_id": user_id,
                "platform": platform,
                "type": transaction_type,
                "data": transaction_data,
                "status": "pending",
                "created_at": datetime.now().isoformat()
            }
            
            # Store in Redis with 1 hour expiry
            await self.redis_client.setex(
                tx_id,
                3600,  # 1 hour expiry
                json.dumps(tx_data)
            )
            
            # Generate bridge URL
            bridge_url = (
                f"{self.bridge_url}?"
                f"botName={self.bot_name}&"
                f"type={transaction_type}&"
                f"uid={user_id}&"
                f"source=/api/transaction/{tx_id}&"
                f"callback=/api/callback/{tx_id}"
            )
            
            return {
                "success": True,
                "transaction_id": tx_id,
                "bridge_url": bridge_url,
                "expires_in": 3600
            }
            
        except Exception as e:
            logger.exception(f"Error creating transaction request: {e}")
            return {
                "success": False,
                "error": str(e)
            }
            
    async def get_transaction_status(self, tx_id: str) -> Dict[str, Any]:
        """Get the status of a transaction request.
        
        Args:
            tx_id: Transaction ID
            
        Returns:
            Dict with transaction status
        """
        try:
            if not self.redis_client:
                await self.connect_redis()
                
            tx_data = await self.redis_client.get(tx_id)
            if not tx_data:
                return {
                    "success": False,
                    "error": "Transaction not found"
                }
                
            return {
                "success": True,
                "data": json.loads(tx_data)
            }
            
        except Exception as e:
            logger.exception(f"Error getting transaction status: {e}")
            return {
                "success": False,
                "error": str(e)
            }
            
    async def update_transaction_status(
        self,
        tx_id: str,
        status: str,
        result: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Update the status of a transaction request.
        
        Args:
            tx_id: Transaction ID
            status: New status
            result: Optional result data
            
        Returns:
            Dict with updated transaction info
        """
        try:
            if not self.redis_client:
                await self.connect_redis()
                
            tx_data = await self.redis_client.get(tx_id)
            if not tx_data:
                return {
                    "success": False,
                    "error": "Transaction not found"
                }
                
            tx_dict = json.loads(tx_data)
            tx_dict["status"] = status
            tx_dict["updated_at"] = datetime.now().isoformat()
            
            if result:
                tx_dict["result"] = result
                
            # Update in Redis, maintaining the original expiry
            await self.redis_client.setex(
                tx_id,
                3600,  # 1 hour expiry
                json.dumps(tx_dict)
            )
            
            return {
                "success": True,
                "data": tx_dict
            }
            
        except Exception as e:
            logger.exception(f"Error updating transaction status: {e}")
            return {
                "success": False,
                "error": str(e)
            }
            
    def format_transaction_message(self, tx_data: Dict[str, Any]) -> str:
        """Format transaction data into a human-readable message.
        
        Args:
            tx_data: Transaction data
            
        Returns:
            Formatted message string
        """
        try:
            if tx_data.get("type") == "transaction":
                # Format regular transaction
                to_address = tx_data.get("data", {}).get("to", "Unknown")
                value = Web3.from_wei(int(tx_data.get("data", {}).get("value", "0")), "ether")
                
                return (
                    f"🔄 Transaction Request\n\n"
                    f"To: `{to_address}`\n"
                    f"Amount: {value} ETH\n\n"
                    f"Click the link below to sign this transaction with your wallet:"
                )
            else:
                # Format signature request
                domain = tx_data.get("data", {}).get("domain", {})
                message = tx_data.get("data", {}).get("message", {})
                
                return (
                    f"✍️ Signature Request\n\n"
                    f"Domain: {domain.get('name')}\n"
                    f"Contract: `{domain.get('verifyingContract', 'Unknown')}`\n\n"
                    f"Click the link below to sign this message with your wallet:"
                )
                
        except Exception as e:
            logger.error(f"Error formatting transaction message: {e}")
            return "Error formatting transaction details. Please check the transaction data in your wallet."
    
    # -------------------------------------------------------------------------------
    # Compatibility methods for API consistency with previous wallet service
    # -------------------------------------------------------------------------------
    
    async def create_wallet(self, user_id: str, platform: str = "telegram", chain: str = "base_sepolia") -> Dict[str, Any]:
        """Create a new wallet record for a user (compatibility method).
        
        Note: With the bridge, we don't actually create a wallet, just store connection info.
        
        Args:
            user_id: User ID (e.g., Telegram user ID)
            platform: Platform identifier (e.g., "telegram")
            chain: Chain to use (e.g., "base_sepolia")
            
        Returns:
            Dict with connection success info
        """
        try:
            if not self.redis_client:
                await self.connect_redis()
                
            # See if user already has a record
            existing_wallet = await self.get_wallet_info(user_id, platform)
            if existing_wallet and existing_wallet.get("address"):
                return {
                    "success": True,
                    "address": existing_wallet.get("address"),
                    "chain": existing_wallet.get("chain", chain),
                    "message": "Wallet already connected"
                }
                
            # Generate a placeholder record - will be updated when user connects
            wallet_data = {
                "user_id": user_id,
                "platform": platform,
                "chain": chain,
                "status": "pending_connection",
                "created_at": datetime.now().isoformat()
            }
            
            # Store in Redis
            wallet_key = f"wallet:{platform}:{user_id}"
            await self.redis_client.set(wallet_key, json.dumps(wallet_data))
            
            return {
                "success": True,
                "chain": chain,
                "message": "Ready to connect external wallet"
            }
            
        except Exception as e:
            logger.exception(f"Error in create_wallet: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_wallet_info(self, user_id: str, platform: str = "telegram") -> Dict[str, Any]:
        """Get wallet information for a user.
        
        Args:
            user_id: User identifier (e.g. Telegram ID)
            platform: Platform identifier (telegram, web, etc.)
            
        Returns:
            Dict with wallet information or None if not found
        """
        logger.info(f"Getting wallet info for {platform}:{user_id}")
        
        # Connect to Redis if not already connected
        if not self.redis_client:
            try:
                success = await self.connect_redis()
                if not success:
                    return {"success": False, "error": "Failed to connect to Redis"}
            except Exception as e:
                logger.error(f"Redis connection error: {str(e)}")
                return {"success": False, "error": f"Redis connection error: {str(e)}"}
        
        try:
            # Get the wallet address mapping
            wallet_key = f"messaging:{platform}:user:{user_id}:wallet"
            wallet_address = await self.redis_client.get(wallet_key)
            
            if not wallet_address:
                logger.info(f"No wallet found for {platform}:{user_id}")
                return {"success": False, "error": "No wallet found for this user"}
                
            # Try to decode as string if it's bytes
            if isinstance(wallet_address, bytes):
                wallet_address = wallet_address.decode('utf-8')
            
            # Get chain information (default or from user preferences)
            chain_key = f"messaging:{platform}:user:{user_id}:chain"
            chain = await self.redis_client.get(chain_key)
            
            if chain and isinstance(chain, bytes):
                chain = chain.decode('utf-8')
            
            if not chain:
                chain = "base_sepolia"  # Default chain
            
            # Get chain info
            supported_chains = await self.get_supported_chains()
            chain_info = next((c for c in supported_chains if c["id"] == chain), None)
            
            # Return comprehensive wallet info
            return {
                "success": True,
                "wallet_address": wallet_address,
                "address": wallet_address,  # Keep for backward compatibility
                "user_id": user_id,
                "platform": platform,
                "chain": chain,
                "chain_info": chain_info or {
                    "id": chain,
                    "name": chain.replace("_", " ").title(),
                    "chain_id": 84532 if chain == "base_sepolia" else 0,
                    "is_testnet": "sepolia" in chain or "goerli" in chain
                }
            }
            
        except Exception as e:
            logger.exception(f"Error getting wallet info: {e}")
            return {"success": False, "error": f"Error getting wallet info: {str(e)}"}
            
    async def get_wallet_balance(self, user_id: str, platform: str = "telegram", chain: str = "base_sepolia") -> Dict[str, Any]:
        """Get wallet balance for a user.
        
        Args:
            user_id: User identifier (e.g. Telegram ID)
            platform: Platform identifier (telegram, web, etc.)
            chain: Chain to check balance on
            
        Returns:
            Dict with balance information
        """
        logger.info(f"Getting wallet balance for {platform}:{user_id} on chain {chain}")
        
        # Get wallet info first
        wallet_info = await self.get_wallet_info(user_id, platform)
        
        if not wallet_info or not wallet_info.get("success"):
            return {
                "success": False,
                "error": wallet_info.get("error", "No wallet found for this user")
            }
            
        wallet_address = wallet_info.get("wallet_address")
        if not wallet_address:
            return {
                "success": False,
                "error": "Invalid wallet info - missing address"
            }
        
        # Use the chain provided or the one from wallet info
        if not chain and wallet_info.get("chain"):
            chain = wallet_info.get("chain")
            
        # Get chain info
        supported_chains = await self.get_supported_chains()
        chain_info = next((c for c in supported_chains if c["id"] == chain), None)
        
        if not chain_info:
            chain_info = {
                "id": chain,
                "name": chain.replace("_", " ").title(),
                "chain_id": 84532 if chain == "base_sepolia" else 0,
                "is_testnet": "sepolia" in chain or "goerli" in chain,
                "explorer_url": (
                    f"https://sepolia.basescan.org/address/{wallet_address}" 
                    if chain == "base_sepolia" else f"https://etherscan.io/address/{wallet_address}"
                )
            }
        else:
            # Add explorer URL to chain info
            if "explorer_url" not in chain_info:
                if chain == "base_sepolia":
                    chain_info["explorer_url"] = f"https://sepolia.basescan.org/address/{wallet_address}"
                elif chain == "ethereum_sepolia":
                    chain_info["explorer_url"] = f"https://sepolia.etherscan.io/address/{wallet_address}"
                elif chain == "base_mainnet":
                    chain_info["explorer_url"] = f"https://basescan.org/address/{wallet_address}"
                elif chain == "ethereum_mainnet":
                    chain_info["explorer_url"] = f"https://etherscan.io/address/{wallet_address}"
                else:
                    chain_info["explorer_url"] = f"https://etherscan.io/address/{wallet_address}"
        
        # For now, return mock balance data with more comprehensive token info
        # In a real implementation, you would query a blockchain provider here
        
        # Generate some random test tokens based on the chain
        test_tokens = []
        if "sepolia" in chain:
            test_tokens = [
                {
                    "symbol": "USDC",
                    "name": "USD Coin",
                    "balance": "100.0",
                    "address": "0x07865c6e87b9f70255377e024ace6630c1eaa37f"
                },
                {
                    "symbol": "USDT",
                    "name": "Tether",
                    "balance": "200.0",
                    "address": "0x1c35ebe4f1b262f3f8b60a2bc1d86ade444f5929"
                }
            ]
        
        return {
            "success": True,
            "wallet_address": wallet_address,
            "chain": chain,
            "chain_info": chain_info,
            "balance": {
                "eth": "0.1",
                "tokens": test_tokens
            }
        }
    
    async def delete_wallet(self, user_id: str, platform: str) -> Dict[str, Any]:
        """Delete wallet connection info (compatibility method).
        
        Args:
            user_id: User ID
            platform: Platform identifier
            
        Returns:
            Dict with deletion status
        """
        try:
            if not self.redis_client:
                await self.connect_redis()
                
            # Delete wallet record
            wallet_key = f"wallet:{platform}:{user_id}"
            await self.redis_client.delete(wallet_key)
            
            return {
                "success": True,
                "message": "Wallet connection removed"
            }
            
        except Exception as e:
            logger.exception(f"Error in delete_wallet: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def switch_chain(self, user_id: str, platform: str, chain: str) -> Dict[str, Any]:
        """Switch chain for a user (compatibility method).
        
        Args:
            user_id: User ID
            platform: Platform identifier
            chain: New chain
            
        Returns:
            Dict with switch status
        """
        try:
            if not self.redis_client:
                await self.connect_redis()
                
            # Get wallet info
            wallet_info = await self.get_wallet_info(user_id, platform)
            
            if not wallet_info:
                return {
                    "success": False,
                    "message": "No wallet connected"
                }
                
            # Update chain
            wallet_info["chain"] = chain
            
            # Save updated info
            wallet_key = f"wallet:{platform}:{user_id}"
            await self.redis_client.set(wallet_key, json.dumps(wallet_info))
            
            return {
                "success": True,
                "chain": chain,
                "message": f"Chain switched to {chain}"
            }
            
        except Exception as e:
            logger.exception(f"Error in switch_chain: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_supported_chains(self) -> List[Dict[str, Any]]:
        """Get list of supported chains (compatibility method).
        
        Returns:
            List of chain info dicts
        """
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
                "id": "base_mainnet",
                "name": "Base Mainnet",
                "description": "Base L2 mainnet",
                "chain_id": 8453,
                "is_testnet": False
            },
            {
                "id": "ethereum_mainnet",
                "name": "Ethereum Mainnet",
                "description": "Ethereum mainnet",
                "chain_id": 1,
                "is_testnet": False
            }
        ]
    
    async def fund_wallet_from_faucet(self, user_id: str, platform: str) -> Dict[str, Any]:
        """Provide faucet info (compatibility method).
        
        Args:
            user_id: User ID
            platform: Platform identifier
            
        Returns:
            Dict with faucet info
        """
        wallet_info = await self.get_wallet_info(user_id, platform)
        
        if not wallet_info or not wallet_info.get("address"):
            return {
                "success": False,
                "error": "No wallet connected"
            }
            
        chain = wallet_info.get("chain", "base_sepolia")
        
        # Instead of funding, return faucet links based on chain
        faucet_urls = {
            "base_sepolia": "https://www.coinbase.com/faucets/base-sepolia-faucet",
            "ethereum_sepolia": "https://sepoliafaucet.com/",
            "scroll_sepolia": "https://scroll.io/blog/scalingCryptography"
        }
        
        return {
            "success": True,
            "message": "Use the faucet link to get testnet funds",
            "faucet_url": faucet_urls.get(chain, faucet_urls["base_sepolia"])
        }

    async def register_pending_connection(
        self,
        connection_id: str,
        user_id: str,
        platform: str = "telegram",
        expiration_seconds: int = 300
    ) -> Dict[str, Any]:
        """Register a pending wallet connection.
        
        Args:
            connection_id: Unique ID for this connection request
            user_id: User identifier (e.g. Telegram ID)
            platform: Platform identifier (telegram, web, etc.)
            expiration_seconds: How long the connection request is valid
            
        Returns:
            Dict with connection details
        """
        logger.info(f"Registering pending wallet connection for {platform}:{user_id} with ID {connection_id}")
        
        # Connect to Redis if not already connected
        if not self.redis_client:
            try:
                logger.info("No Redis client, attempting to connect")
                success = await self.connect_redis()
                if not success:
                    logger.error("Failed to connect to Redis")
                    return {"success": False, "error": "Failed to connect to Redis"}
            except Exception as e:
                logger.error(f"Redis connection error: {str(e)}")
                return {"success": False, "error": "Redis connection error"}
        
        # Create connection data
        connection_data = {
            "connection_id": connection_id,
            "user_id": str(user_id),
            "platform": platform,
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "expires_at": (datetime.now() + timedelta(seconds=expiration_seconds)).isoformat()
        }
        
        logger.info(f"Connection data created: {connection_data}")
        
        try:
            # Store in Redis with expiration
            # Use the wallet_bridge: prefix to match existing code
            connection_key = f"wallet_bridge:connection:{connection_id}"
            await self.redis_client.setex(
                connection_key,
                expiration_seconds,
                json.dumps(connection_data)
            )
            logger.info(f"Stored connection data in Redis with key: {connection_key}")
            
            # Also track this connection for the user
            user_connections_key = f"wallet_bridge:user:{platform}:{user_id}:connections"
            await self.redis_client.sadd(user_connections_key, connection_id)
            logger.info(f"Added connection ID to user's connections list: {user_connections_key}")
            
            # Hardcode the public URL directly instead of relying on environment variables
            public_bridge_url = "https://snel-pointless.vercel.app/static/wallet-bridge.html"
            logger.info(f"Using hardcoded public bridge URL: {public_bridge_url}")
            
            # Generate connection URL with params expected by the wallet-bridge.html
            connection_url = (
                f"{public_bridge_url}?"
                f"botName={self.bot_name}&"
                f"action=connect&"
                f"uid={connection_id}&"
                f"source=/api/wallet-bridge/status/{connection_id}&"
                f"callback=/api/wallet-bridge/connect"
            )
            logger.info(f"Generated connection URL: {connection_url}")
            
            return {
                "success": True,
                "connection_id": connection_id,
                "expires_in": expiration_seconds,
                "connection_url": connection_url
            }
            
        except Exception as e:
            logger.exception(f"Error registering pending connection: {e}")
            return {
                "success": False,
                "error": str(e)
            }
            
    async def complete_wallet_connection(
        self,
        connection_id: str,
        wallet_address: str
    ) -> Dict[str, Any]:
        """Complete a wallet connection by verifying and storing the connected address.
        
        Args:
            connection_id: Unique ID for this connection request
            wallet_address: The wallet address that was connected
            
        Returns:
            Dict with connection and user details
        """
        logger.info(f"Completing wallet connection {connection_id} for address {wallet_address}")
        
        # Connect to Redis if not already connected
        if not self.redis_client:
            try:
                success = await self.connect_redis()
                if not success:
                    return {"success": False, "error": "Failed to connect to Redis"}
            except Exception as e:
                logger.error(f"Redis connection error: {str(e)}")
                return {"success": False, "error": "Redis connection error"}
        
        try:
            # Get the connection details
            key = f"wallet_bridge:connection:{connection_id}"
            connection_data_str = await self.redis_client.get(key)
            
            if not connection_data_str:
                return {"success": False, "error": "Connection request not found or expired"}
            
            # Parse the connection data
            connection_data = json.loads(connection_data_str)
            user_id = connection_data.get("user_id")
            platform = connection_data.get("platform", "telegram")
            
            if not user_id:
                return {"success": False, "error": "Invalid connection data"}
            
            # Update the connection status
            connection_data["status"] = "completed"
            connection_data["wallet_address"] = wallet_address
            connection_data["completed_at"] = datetime.now().isoformat()
            
            # Save the updated connection data
            await self.redis_client.set(key, json.dumps(connection_data))
            
            # Store the wallet address mapping for the user
            await self.redis_client.set(f"messaging:{platform}:user:{user_id}:wallet", wallet_address)
            
            # Also store the reverse mapping
            await self.redis_client.set(f"wallet:{wallet_address}:{platform}:user", user_id)
            
            logger.info(f"Completed wallet connection for {platform}:{user_id} with address {wallet_address}")
            
            return {
                "success": True,
                "connection_id": connection_id,
                "user_id": user_id,
                "platform": platform,
                "wallet_address": wallet_address
            }
            
        except Exception as e:
            logger.exception(f"Error completing wallet connection: {e}")
            return {"success": False, "error": str(e)}
            
    async def get_connection_status(self, connection_id: str) -> Dict[str, Any]:
        """Get the status of a wallet connection.
        
        Args:
            connection_id: The connection ID to check
            
        Returns:
            Dict with connection status
        """
        logger.info(f"Getting status of wallet connection {connection_id}")
        
        # Connect to Redis if not already connected
        if not self.redis_client:
            try:
                success = await self.connect_redis()
                if not success:
                    return {"success": False, "error": "Failed to connect to Redis"}
            except Exception as e:
                logger.error(f"Redis connection error: {str(e)}")
                return {"success": False, "error": "Redis connection error"}
        
        try:
            # Check if connection exists
            connection_key = f"wallet_bridge:connection:{connection_id}"
            connection_data = await self.redis_client.get(connection_key)
            
            if not connection_data:
                return {
                    "success": False, 
                    "status": "not_found",
                    "message": "Connection not found or expired"
                }
                
            # Parse connection data
            connection = json.loads(connection_data)
            status = connection.get("status", "pending")
            wallet_address = connection.get("wallet_address")
            
            # Return formatted status
            return {
                "success": True,
                "status": status,
                "wallet_address": wallet_address,
                "connection_id": connection_id,
                "created_at": connection.get("created_at"),
                "expires_at": connection.get("expires_at"),
                "is_completed": status == "completed",
                "is_pending": status == "pending"
            }
            
        except Exception as e:
            logger.exception(f"Error getting connection status: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def generate_connect_url(self, connection_id: str) -> str:
        """Generate a URL for connecting a wallet.
        
        Args:
            connection_id: Unique ID for this connection attempt
            
        Returns:
            URL that user can visit to connect wallet
        """
        # Hardcode the public URL directly instead of relying on environment variables
        public_bridge_url = "https://snel-pointless.vercel.app/static/wallet-bridge.html"
        logger.info(f"Using hardcoded public bridge URL: {public_bridge_url}")
            
        # Construct the URL with connection ID and bot name parameters
        # Format the URL to match the expected format by the Telegram agent
        full_url = (
            f"{public_bridge_url}?"
            f"botName={self.bot_name}&"
            f"action=connect&"
            f"uid={connection_id}&"
            f"source=/api/wallet-bridge/status/{connection_id}&"
            f"callback=/api/wallet-bridge/connect"
        )
        logger.info(f"Generated wallet connect URL: {full_url}")
        return full_url

    async def verify_wallet_connection(
        self,
        connection_id: str,
        wallet_address: str,
        signature: str,
        message: str
    ) -> Dict[str, Any]:
        """Verify a wallet connection.
        
        Args:
            connection_id: The connection ID from the registration
            wallet_address: The wallet address being connected
            signature: The signature to verify
            message: The message that was signed
            
        Returns:
            Dict with verification status
        """
        logger.info(f"Verifying wallet connection for ID {connection_id}")
        
        # Connect to Redis if not already connected
        if not self.redis_client:
            try:
                logger.info("No Redis client, attempting to connect")
                success = await self.connect_redis()
                if not success:
                    logger.error("Failed to connect to Redis")
                    return {"success": False, "error": "Failed to connect to Redis"}
            except Exception as e:
                logger.error(f"Redis connection error: {str(e)}")
                return {"success": False, "error": "Redis connection error"}
        
        try:
            # Check if connection exists
            connection_key = f"wallet_bridge:connection:{connection_id}"
            connection_data = await self.redis_client.get(connection_key)
            
            if not connection_data:
                logger.warning(f"Connection ID {connection_id} not found")
                return {"success": False, "error": "Connection ID not found or expired"}
            
            connection = json.loads(connection_data)
            user_id = connection.get("user_id")
            platform = connection.get("platform", "telegram")
            
            if not user_id:
                logger.warning(f"Connection has no user_id: {connection}")
                return {"success": False, "error": "Invalid connection data"}
            
            # Verify signature
            try:
                # We'll implement basic signature verification
                # For a production service, you'd want more robust verification
                
                # For now, assume signature is valid if it's not empty
                # Replace with proper signature verification in production
                if not signature or len(signature) < 20:
                    logger.warning(f"Invalid signature: {signature}")
                    return {"success": False, "error": "Invalid signature"}
                
                # Store wallet address in Redis using the right key format
                user_wallet_key = f"messaging:{platform}:user:{user_id}:wallet"
                await self.redis_client.set(user_wallet_key, wallet_address)
                logger.info(f"Stored wallet address {wallet_address} for user {platform}:{user_id} with key {user_wallet_key}")
                
                # Set default chain
                user_chain_key = f"messaging:{platform}:user:{user_id}:chain"
                await self.redis_client.set(user_chain_key, "base_sepolia")
                logger.info(f"Set default chain for user {platform}:{user_id} to base_sepolia")
                
                # Update connection status to completed
                connection["status"] = "completed"
                connection["wallet_address"] = wallet_address
                connection["completed_at"] = datetime.now().isoformat()
                await self.redis_client.set(connection_key, json.dumps(connection))
                logger.info(f"Updated connection status to completed for {connection_id}")
                
                logger.info(f"Wallet connection verified for {platform}:{user_id} with address {wallet_address}")
                
                return {
                    "success": True,
                    "user_id": user_id,
                    "platform": platform,
                    "wallet_address": wallet_address
                }
            except Exception as e:
                logger.exception(f"Error verifying signature: {e}")
                return {"success": False, "error": f"Signature verification error: {str(e)}"}
            
        except Exception as e:
            logger.exception(f"Error in verify_wallet_connection: {e}")
            return {"success": False, "error": str(e)} 
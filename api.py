import configure_logging  # This must be the first import

import os
from pathlib import Path
from dotenv import load_dotenv
import datetime
import sys
import json
from typing import Dict, Optional
import redis.asyncio as redis
import asyncio

# Load environment variables from .env file BEFORE importing dowse
env_path = Path(__file__).parent / '.env'
load_dotenv(env_path)

# Ensure OpenAI key is set before importing dowse
if not os.environ.get("OPENAI_API_KEY"):
    openai_key = os.environ.get("OPENAI_API_KEY_LOCAL")  # Try local key
    if openai_key:
        os.environ["OPENAI_API_KEY"] = openai_key

# Now we can safely import dowse
from dowse import Pipeline

import logging
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.models.commands import (
    CommandRequest, CommandResponse, TransactionRequest, TransactionResponse,
    UserMessage, BotMessage, SwapCommand
)
from app.config.chains import ChainConfig, TOKEN_ADDRESSES, NATIVE_TOKENS
from app.services.pipeline import init_pipeline
from app.services.prices import get_token_price

# Initialize logger
logger = logging.getLogger(__name__)

class RedisPendingCommandStore:
    """Redis-backed store for pending commands."""
    KEY_PREFIX = "pending_cmd"  # Namespace for all command keys
    MAX_RETRIES = 3  # Maximum number of retries for operations
    RETRY_DELAY = 0.1  # Delay between retries in seconds
    
    def __init__(self):
        self._logger = logging.getLogger(__name__)
        self._redis = None
        self._redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379")
        
    async def _ensure_connection(self):
        """Ensure Redis connection is active, reconnect if needed."""
        try:
            if not self._redis:
                self._redis = redis.from_url(
                    self._redis_url,
                    encoding="utf-8",
                    decode_responses=True,
                    retry_on_timeout=True,
                    health_check_interval=30,
                    socket_keepalive=True,  # Keep connection alive
                    socket_timeout=5,  # 5 second timeout
                    retry_on_error=[redis.ConnectionError, redis.TimeoutError]  # Auto-retry on these errors
                )
            await self._redis.ping()
        except (redis.ConnectionError, redis.TimeoutError) as e:
            self._logger.warning(f"Redis connection lost, attempting to reconnect: {e}")
            try:
                # Close existing connection if any
                if self._redis:
                    await self._redis.close()
                # Create new connection
                self._redis = redis.from_url(
                    self._redis_url,
                    encoding="utf-8",
                    decode_responses=True,
                    retry_on_timeout=True,
                    health_check_interval=30,
                    socket_keepalive=True,
                    socket_timeout=5,
                    retry_on_error=[redis.ConnectionError, redis.TimeoutError]
                )
                await self._redis.ping()
                self._logger.info("Successfully reconnected to Redis")
            except Exception as e:
                self._logger.error(f"Failed to reconnect to Redis: {e}")
                raise RuntimeError("Redis connection failed")

    async def _retry_operation(self, operation):
        """Retry an operation with exponential backoff."""
        last_error = None
        for attempt in range(self.MAX_RETRIES):
            try:
                await self._ensure_connection()
                return await operation()
            except (redis.ConnectionError, redis.TimeoutError) as e:
                last_error = e
                if attempt < self.MAX_RETRIES - 1:
                    delay = self.RETRY_DELAY * (2 ** attempt)  # Exponential backoff
                    self._logger.warning(f"Operation failed, retrying in {delay}s: {e}")
                    await asyncio.sleep(delay)
                continue
            except Exception as e:
                self._logger.error(f"Unexpected error during operation: {e}")
                raise
        raise RuntimeError(f"Operation failed after {self.MAX_RETRIES} attempts: {last_error}")

    def _make_key(self, address: str) -> str:
        """Create a Redis key for a wallet address."""
        from eth_utils import to_checksum_address
        try:
            # Convert to checksum address if it's a valid Ethereum address
            if address.startswith("0x"):
                checksummed = to_checksum_address(address)
                return f"{self.KEY_PREFIX}:{checksummed}"
        except ValueError:
            pass
        # For non-ETH addresses (e.g. test accounts), just lowercase
        return f"{self.KEY_PREFIX}:{address.lower()}"

    async def initialize(self):
        """Initialize the Redis connection."""
        await self._ensure_connection()
        self._logger.info("Successfully connected to Redis")
    
    async def store_command(self, user_id: str, command: str, chain_id: Optional[int] = None) -> None:
        """Store a pending command for a user."""
        data = {
            "command": command,
            "chain_id": chain_id,
            "timestamp": datetime.datetime.now().isoformat()
        }
        
        key = self._make_key(user_id)
        
        async def _store():
            # Store with 30 minute TTL
            await self._redis.setex(key, 1800, json.dumps(data))
            
            # Verify storage
            stored_data = await self._redis.get(key)
            if not stored_data:
                raise RuntimeError("Command was not stored successfully")
            
            ttl = await self._redis.ttl(key)
            self._logger.info(f"Stored command for key {key}: {command} (chain: {chain_id})")
            self._logger.info(f"Command TTL for key {key}: {ttl} seconds")
            
        await self._retry_operation(_store)
    
    async def get_command(self, user_id: str) -> Optional[Dict]:
        """Get a pending command for a user."""
        key = self._make_key(user_id)
        self._logger.info(f"Attempting to get command for key {key}")
        
        async def _get():
            # Get data and TTL
            data = await self._redis.get(key)
            ttl = await self._redis.ttl(key)
            
            self._logger.info(f"Command TTL for key {key}: {ttl} seconds")
            self._logger.info(f"Raw Redis data for key {key}: {data}")
            
            if not data:
                self._logger.info(f"No command found for key {key}")
                return None
                
            command_data = json.loads(data)
            self._logger.info(f"Found command for key {key}: {command_data['command']}")
            return command_data
            
        return await self._retry_operation(_get)
    
    async def clear_command(self, user_id: str) -> None:
        """Clear a pending command for a user."""
        key = self._make_key(user_id)
        
        async def _clear():
            exists = await self._redis.exists(key)
            if exists:
                await self._redis.delete(key)
                self._logger.info(f"Cleared command for key {key}")
            else:
                self._logger.warning(f"No command found to clear for key {key}")
                
        await self._retry_operation(_clear)

    async def list_all_commands(self) -> list[str]:
        """List all pending command keys (useful for debugging)."""
        async def _list():
            return await self._redis.keys(f"{self.KEY_PREFIX}:*")
            
        return await self._retry_operation(_list)

# Global command store
command_store = RedisPendingCommandStore()

try:
    from eth_rpc import set_alchemy_key
    from kyber import (
        get_quote as kyber_quote,
        KyberSwapError,
        NoRouteFoundError,
        InsufficientLiquidityError,
        InvalidTokenError,
        BuildTransactionError,
        get_chain_from_chain_id,
        TransferFromFailedError,
    )
except ImportError as e:
    logger.error(f"Failed to import required packages: {e}")
    raise

# Set up rate limiter
limiter = Limiter(key_func=get_remote_address)
app = FastAPI()
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Add CORS middleware with more restrictive settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Local development
        "http://127.0.0.1:3000",  # Alternative local URL
        "https://snel-pointless.vercel.app",  # Production domain
        "https://snel-pointless-git-main-papas-projects-5b188431.vercel.app",  # Add preview domains
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize required services
def init_services():
    # Get environment variables (these should be set in Vercel)
    alchemy_key = os.environ.get("ALCHEMY_KEY")
    coingecko_key = os.environ.get("COINGECKO_API_KEY")

    if not all([alchemy_key, coingecko_key]):
        logger.error("Missing required environment variables")
        raise ValueError("Missing required environment variables")

    # Set Alchemy key
    set_alchemy_key(alchemy_key)

# OpenAI API key header
openai_key_header = APIKeyHeader(name="X-OpenAI-Key", auto_error=False)

def get_openai_key(api_key: str = Depends(openai_key_header)) -> str:
    # First try to get from header (production)
    if api_key:
        return api_key

    # Then try environment variable (development)
    env_key = os.environ.get("OPENAI_API_KEY")
    if env_key:
        return env_key

    raise HTTPException(
        status_code=401,
        detail="OpenAI API Key is required (either in header or environment)"
    )

# Global pipeline instance
pipeline = None

def get_pipeline(openai_key: str) -> Pipeline:
    """Get or create the pipeline instance."""
    global pipeline
    if pipeline is None:
        # Set OpenAI key in environment
        os.environ["OPENAI_API_KEY"] = openai_key
        # Initialize pipeline
        pipeline = init_pipeline(openai_key)
    return pipeline

@app.on_event("startup")
async def startup_event():
    """Initialize services."""
    init_services()
    
    # Initialize Redis connection
    try:
        await command_store.initialize()
        
        # Test Redis operations
        test_user_id = "test_user"
        test_command = "test_command"
        
        # Store test command
        await command_store.store_command(test_user_id, test_command)
        logger.info("Test command stored successfully")
        
        # Retrieve test command
        stored_command = await command_store.get_command(test_user_id)
        if stored_command and stored_command["command"] == test_command:
            logger.info("Test command retrieved successfully")
        else:
            logger.error("Test command retrieval failed")
            
        # Clear test command
        await command_store.clear_command(test_user_id)
        logger.info("Test command cleared successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize Redis: {e}")
        raise

@app.post("/api/process-command")
@limiter.limit("20/minute")
async def process_command(
    request: Request,
    command_request: CommandRequest,
    openai_key: str = Depends(get_openai_key)
) -> CommandResponse:
    try:
        # Get pipeline instance
        pipeline = get_pipeline(openai_key)
        
        # Always convert user ID to checksum address if it's an ETH address
        from eth_utils import to_checksum_address
        try:
            if command_request.creator_id.startswith("0x"):
                user_id = to_checksum_address(command_request.creator_id)
            else:
                user_id = command_request.creator_id.lower()
        except ValueError:
            user_id = command_request.creator_id.lower()
            
        command_request.creator_id = user_id
        
        logger.info(f"Processing command: {command_request.content} on chain {command_request.chain_id}")
        logger.info(f"User ID (normalized): {user_id}, Name: {command_request.creator_name}")
        
        # Handle confirmations
        content = command_request.content.lower().strip()
        if content in ["yes", "y", "confirm"]:
            # List all commands for debugging
            all_keys = await command_store.list_all_commands()
            logger.info(f"All pending command keys: {all_keys}")
            
            # Get pending command
            try:
                # Double-check the key format
                key = command_store._make_key(user_id)
                logger.info(f"Looking up command with key: {key}")
                
                # Get raw data first
                raw_data = await command_store._redis.get(key)
                logger.info(f"Raw Redis data: {raw_data}")
                
                pending_data = await command_store.get_command(user_id)
                logger.info(f"Parsed pending data: {pending_data}")
                
                if not pending_data:
                    logger.error(f"No pending command found for user {user_id}")
                    return CommandResponse(
                        content="No pending command found. Please try your swap command again.",
                        error_message="No pending command found"
                    )
                
                # Execute the pending command
                pending_command = pending_data["command"]
                chain_id = pending_data.get("chain_id") or command_request.chain_id  # Fallback to current chain_id
                logger.info(f"Found pending command for user {user_id}: {pending_command} on chain {chain_id}")
                
                try:
                    # Parse the command to get swap details
                    parts = pending_command.split()
                    if len(parts) == 5 and parts[0].lower() == "swap" and parts[3].lower() == "for":
                        amount = float(parts[1])
                        token_in = parts[2].upper()
                        token_out = parts[4].upper()
                        
                        logger.info(f"Creating transaction request for {amount} {token_in} -> {token_out} on chain {chain_id}")
                        
                        # Create a transaction request
                        tx_request = TransactionRequest(
                            command=pending_command,
                            chain_id=chain_id,
                            wallet_address=user_id
                        )
                        
                        # Clear the command only after successful creation of tx request
                        await command_store.clear_command(user_id)
                        
                        # Return success response
                        return CommandResponse(
                            content=f"Preparing to swap {amount} {token_in} for {token_out}...",
                            pending_command=None,
                            metadata={"transaction_request": tx_request.model_dump()}
                        )
                    else:
                        raise ValueError("Invalid command format")
                        
                except Exception as e:
                    logger.error(f"Error executing command: {e}")
                    return CommandResponse(
                        content="Sorry, something went wrong executing your command.",
                        error_message=str(e)
                    )
                
            except Exception as e:
                logger.error(f"Error retrieving pending command: {e}", exc_info=True)
                return CommandResponse(
                    content="Sorry, something went wrong retrieving your pending command.",
                    error_message=str(e)
                )
            
        # Convert request to Tweet
        tweet = command_request.to_tweet()
        
        # Process through pipeline
        result = await pipeline.process(tweet)
        logger.info(f"Pipeline result: {result}")
        
        # Handle pipeline errors
        if result.error_message:
            return CommandResponse(
                content=f"Sorry, I couldn't process your command: {result.error_message}",
                error_message=result.error_message
            )
        
        # Convert result to BotMessage
        bot_message = BotMessage.from_agent_message(result)
        
        # Store pending command if one was generated
        if bot_message.metadata and "pending_command" in bot_message.metadata:
            logger.info(f"Storing pending command for user {user_id}: {bot_message.metadata['pending_command']}")
            await command_store.store_command(
                user_id,
                bot_message.metadata["pending_command"],
                command_request.chain_id
            )
            
            # Verify storage immediately
            stored = await command_store.get_command(user_id)
            if not stored:
                logger.error(f"Failed to verify command storage for user {user_id}")
                raise RuntimeError("Failed to store command")
        
        # Convert BotMessage to API response
        response = CommandResponse.from_bot_message(bot_message)
        
        # Add pending command to response if it exists
        if bot_message.metadata and "pending_command" in bot_message.metadata:
            response.pending_command = bot_message.metadata["pending_command"]
            
        return response
            
    except Exception as e:
        logger.error(f"Unexpected error in command processing: {e}", exc_info=True)
        return CommandResponse(
            content="Sorry, something went wrong. Please try again!",
            error_message=str(e)
        )

async def parse_swap_command(command: str, chain_id: Optional[int] = None) -> SwapCommand:
    """Parse a swap command string into a SwapCommand object."""
    try:
        # Remove 'approved:' prefix if present
        if command.startswith("approved:"):
            command = command[9:]  # Remove 'approved:' prefix
            
        parts = command.split()  # Don't convert to lower case here
        if len(parts) == 5 and parts[0].lower() == "swap" and (parts[3].lower() == "for" or parts[3].lower() == "to"):
            # Get tokens preserving case
            token_in = parts[2]
            token_out = parts[4]
            
            # Only convert to upper case if they're not contract addresses
            from app.services.prices import _is_valid_contract_address
            if not _is_valid_contract_address(token_in):
                token_in = token_in.upper()
            if not _is_valid_contract_address(token_out):
                token_out = token_out.upper()
            
            # Handle token aliases
            if token_in in ["ETH", "WETH"]:
                token_in = "ETH"
            if token_out in ["ETH", "WETH"]:
                token_out = "ETH"
            if token_in in ["USD", "USDC"]:
                token_in = "USDC"
            if token_out in ["USD", "USDC"]:
                token_out = "USDC"
                
            try:
                # Try to parse amount as float
                amount = float(parts[1])
                
                # If amount is very small (like 0.000373) and token is ETH, this is likely a calculated amount
                # from a target amount swap, so we should use it directly
                if token_in == "ETH" and amount < 0.01:
                    logger.info(f"Using pre-calculated ETH amount: {amount}")
                    return SwapCommand(
                        action="swap",
                        amount=amount,
                        token_in=token_in,
                        token_out=token_out,  # Preserve case for contract address
                        is_target_amount=False  # We're using the calculated amount directly
                    )
                    
                return SwapCommand(
                    action="swap",
                    amount=amount,
                    token_in=token_in,
                    token_out=token_out,  # Preserve case for contract address
                    is_target_amount=False
                )
            except ValueError:
                logger.error(f"Failed to parse amount: {parts[1]}")
                return None
                
        return None
    except (ValueError, IndexError) as e:
        logger.error(f"Failed to parse swap command: {e}")
        return None

@app.post("/api/execute-transaction")
@limiter.limit("10/minute")
async def execute_transaction(
    request: Request,
    tx_request: TransactionRequest,
    openai_key: str = Depends(get_openai_key)
) -> TransactionResponse:
    try:
        os.environ["OPENAI_API_KEY"] = openai_key
        
        logger.info(f"Executing transaction for command: {tx_request.command} on chain {tx_request.chain_id}")
        
        # Track if this is a post-approval attempt
        is_post_approval = tx_request.command.startswith("approved:")
        
        # Validate chain support
        if not ChainConfig.is_supported(tx_request.chain_id):
            raise ValueError(
                f"Chain {tx_request.chain_id} is not supported. Supported chains: "
                f"{', '.join(f'{name} ({id})' for id, name in ChainConfig.SUPPORTED_CHAINS.items())}"
            )

        # Parse the swap command
        swap_command = await parse_swap_command(tx_request.command, tx_request.chain_id)
        if not swap_command:
            logger.error(f"Failed to parse swap command: {tx_request.command}")
            raise ValueError(f"Invalid swap command format. Expected format: 'swap 1 usdc for eth', got: {tx_request.command}")

        # Get token addresses
        token_addresses = TOKEN_ADDRESSES.get(tx_request.chain_id, {})
        if not token_addresses:
            raise ValueError(f"No token addresses configured for chain {tx_request.chain_id}")
        
        try:
            # Get decimals for input token
            _, token_in_decimals = await get_token_price(
                swap_command.token_in,
                token_addresses.get(swap_command.token_in),
                tx_request.chain_id
            )
            
            # Calculate amount_in based on decimals
            if swap_command.token_in == "ETH":
                # For ETH, we need to be extra careful with the decimal conversion
                # Convert the float amount to wei directly
                from web3 import Web3
                amount_in = int(Web3.to_wei(swap_command.amount, 'ether'))
                logger.info(f"Converting {swap_command.amount} ETH to {amount_in} wei")
            else:
                amount_in = int(swap_command.amount * (10 ** token_in_decimals))
            
            logger.info(f"Calculated amount_in: {amount_in} ({swap_command.amount} * 10^{token_in_decimals})")
            
            # Handle native ETH vs WETH
            token_in = token_addresses[swap_command.token_in] if swap_command.token_in in token_addresses else swap_command.token_in
            token_out = token_addresses[swap_command.token_out] if swap_command.token_out in token_addresses else swap_command.token_out
            
            # If swapping from ETH, use native ETH address
            if swap_command.token_in == "ETH":
                token_in = "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE"
            
            # If swapping to ETH, use WETH address for routing
            if swap_command.token_out == "ETH":
                token_out = token_addresses["ETH"]  # Use WETH address
            
            logger.info(f"Preparing Kyber quote with token_in: {token_in}, token_out: {token_out}")
            
            try:
                # Preserve case for contract addresses in Kyber API call
                quote = await kyber_quote(
                    token_in=token_in,
                    token_out=token_out,  # Use original case
                    amount=amount_in,
                    chain_id=tx_request.chain_id,
                    recipient=tx_request.wallet_address
                )
                
                # Return swap transaction
                return TransactionResponse(
                    to=quote.router_address,
                    data=quote.data,
                    value=hex(amount_in) if swap_command.token_in == "ETH" else "0x0",
                    chain_id=tx_request.chain_id,
                    method="swap",
                    gas_limit=hex(int(float(quote.gas) * 1.1)),  # Add 10% buffer for gas
                    needs_approval=False
                )

            except TransferFromFailedError as e:
                error_str = str(e).lower()
                if "insufficient funds" in error_str:
                    raise ValueError("Insufficient funds for transaction. Please try a smaller amount.")
                    
                # Only handle approval if input token is not ETH and we haven't just approved
                if swap_command.token_in != "ETH" and not is_post_approval:
                    logger.info(f"Token approval needed for {swap_command.token_in}")
                    return TransactionResponse(
                        to=token_addresses[swap_command.token_in],
                        data="0x095ea7b3" +  # approve(address,uint256)
                             "000000000000000000000000" +  # Pad router address
                             "6131B5fae19EA4f9D964eAc0408E4408b66337b5" +  # Kyber router address
                             "f" * 64,  # Max uint256 for unlimited approval
                        value="0x0",
                        chain_id=tx_request.chain_id,
                        method="approve",
                        gas_limit="0x186a0",  # 100,000 gas
                        needs_approval=True,
                        token_to_approve=token_addresses[swap_command.token_in],
                        spender="0x6131B5fae19EA4f9D964eAc0408E4408b66337b5",  # Kyber router
                        pending_command=f"approved:{tx_request.command}"  # Mark as approved for next attempt
                    )
                elif swap_command.token_in == "ETH":
                    raise ValueError("Insufficient ETH balance for the transaction")
                else:
                    # If we've just approved and still getting transfer failed, there might be another issue
                    raise ValueError("Token transfer failed even after approval. Please check your balance and try again.")
                    
            except (NoRouteFoundError, InsufficientLiquidityError, InvalidTokenError, BuildTransactionError) as e:
                logger.error(f"Kyber error: {e}")
                raise HTTPException(status_code=400, detail=str(e))

        except ValueError as ve:
            logger.error(f"Value error in swap preparation: {ve}")
            raise HTTPException(status_code=400, detail=str(ve))
            
    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        logger.error(f"Error preparing swap: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while preparing the swap: {str(e)}"
        )

@app.get("/api/test-kyber")
async def test_kyber():
    """Test endpoint to verify Kyber integration."""
    try:
        # Test with USDC -> ETH on Base
        test_quote = await kyber_quote(
            token_in="0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",  # USDC on Base
            token_out="0x4200000000000000000000000000000000000006",  # WETH on Base
            amount=1000000,  # 1 USDC (6 decimals)
            chain_id=8453,  # Base
            recipient="0x0000000000000000000000000000000000000000"  # Zero address for testing
        )
        return {
            "status": "success",
            "message": "Kyber integration working",
            "quote": {
                "router": test_quote.router_address,
                "gas": test_quote.gas
            }
        }
    except Exception as e:
        logger.error(f"Kyber test failed: {e}")
        return {
            "status": "error",
            "message": str(e)
        }

@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    try:
        # Check if required environment variables are set
        env_vars = {
            "ALCHEMY_KEY": bool(os.environ.get("ALCHEMY_KEY")),
            "COINGECKO_API_KEY": bool(os.environ.get("COINGECKO_API_KEY")),
        }
        
        return {
            "status": "healthy",
            "timestamp": datetime.datetime.now().isoformat(),
            "environment": {
                "python_version": sys.version,
                "environment_variables": env_vars
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }

# This is required for Vercel
app = app 
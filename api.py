import configure_logging  # This must be the first import

import os
from pathlib import Path
from dotenv import load_dotenv
import datetime
import sys
import json
from typing import Dict, Optional, List, Any, Tuple, Union
from urllib.parse import urlparse
from upstash_redis import Redis
import asyncio
import aiohttp

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

def parse_redis_url(url):
    """Parse Redis URL to get Upstash REST URL and token."""
    if not url or not isinstance(url, str):
        raise ValueError(f"Invalid Redis URL: {url}. Expected a string URL, got {type(url)}")
        
    parsed = urlparse(url)
    hostname = parsed.hostname
    
    if not hostname:
        raise ValueError(f"Invalid Redis URL: {url}. Could not parse hostname.")
    
    # Handle both URL formats (redis:// and https://)
    if url.startswith('redis://') or url.startswith('rediss://'):
        rest_url = f"https://{hostname}"
        token = parsed.password
        if not token:
            raise ValueError(f"Invalid Redis URL: {url}. No password/token found.")
    else:
        rest_url = url
        token = os.environ.get("UPSTASH_REDIS_TOKEN") or parsed.password
        if not token:
            raise ValueError(f"Invalid Redis URL: {url}. No UPSTASH_REDIS_TOKEN environment variable or password in URL.")
    
    logger.info(f"Parsed Redis URL: {rest_url} (hostname: {hostname})")
    return rest_url, token

class RedisPendingCommandStore:
    """Store pending commands in Redis."""
    def __init__(self):
        # Check for either Redis URL format
        redis_url = os.getenv("REDIS_URL")
        upstash_url = os.getenv("UPSTASH_REDIS_REST_URL")
        upstash_token = os.getenv("UPSTASH_REDIS_REST_TOKEN")
        
        # Validate that we have valid connection parameters
        if not ((redis_url and isinstance(redis_url, str)) or 
                (upstash_url and upstash_token and isinstance(upstash_url, str) and isinstance(upstash_token, str))):
            raise ValueError("Either REDIS_URL (as string) or both UPSTASH_REDIS_REST_URL and UPSTASH_REDIS_REST_TOKEN (as strings) are required")

        # Initialize Redis client
        if upstash_url and upstash_token and isinstance(upstash_url, str) and isinstance(upstash_token, str):
            self._redis = Redis(
                url=upstash_url,
                token=upstash_token
            )
        elif redis_url and isinstance(redis_url, str):
            # Parse Redis URL for Upstash REST format
            from urllib.parse import urlparse
            parsed = urlparse(redis_url)
            rest_url = f"https://{parsed.hostname}"
            token = parsed.password
            self._redis = Redis(url=rest_url, token=token)
        else:
            # This should never happen due to the validation above
            raise ValueError("No valid Redis connection parameters found")

        self._ttl = 1800  # 30 minutes

    def _make_key(self, user_id: str) -> str:
        """Create a Redis key for a user's pending command."""
        # Ensure consistent formatting of user_id
        if user_id.startswith("0x"):
            # For Ethereum addresses, always use lowercase to ensure consistency
            normalized_id = user_id.lower()
        else:
            # For other IDs, also use lowercase for consistency
            normalized_id = user_id.lower()
            
        logger.info(f"Normalized user ID from {user_id} to {normalized_id}")
        return f"pending_command:{normalized_id}"

    def store_command(self, user_id: str, command: str, chain_id: int) -> None:
        """Store a pending command for a user."""
        key = self._make_key(user_id)
        logger.info(f"Storing command with key: {key}, command: {command}, chain_id: {chain_id}")
        
        # Log all existing keys for debugging
        try:
            all_keys = self._redis.keys("pending_command:*")
            logger.info(f"All existing keys before storing: {all_keys}")
        except Exception as e:
            logger.error(f"Error listing keys: {e}")
        
        try:
            self._redis.set(
                key,
                json.dumps({
                    "command": command,
                    "chain_id": chain_id,
                    "timestamp": datetime.datetime.now().isoformat()
                }),
                ex=self._ttl
            )
            logger.info(f"Command stored successfully for key: {key}")
            
            # Verify storage immediately
            value = self._redis.get(key)
            if value:
                logger.info(f"Verified command storage: {value}")
            else:
                logger.error(f"Failed to verify command storage for key: {key}")
        except Exception as e:
            logger.error(f"Error storing command: {e}")

    def get_command(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get a pending command for a user."""
        key = self._make_key(user_id)
        logger.info(f"Getting command with key: {key}")
        
        # Log all existing keys for debugging
        try:
            all_keys = self._redis.keys("pending_command:*")
            logger.info(f"All existing keys when retrieving: {all_keys}")
        except Exception as e:
            logger.error(f"Error listing keys: {e}")
        
        try:
            value = self._redis.get(key)
            if value:
                logger.info(f"Found command for key {key}: {value}")
                return json.loads(value)
            else:
                logger.info(f"No command found for key: {key}")
                return None
        except Exception as e:
            logger.error(f"Error getting command: {e}")
            return None

    def clear_command(self, user_id: str) -> None:
        """Clear a pending command for a user."""
        key = self._make_key(user_id)
        self._redis.delete(key)

    def list_all_commands(self) -> List[Dict[str, Any]]:
        """List all pending commands."""
        keys = self._redis.keys("pending_command:*")
        if not keys:
            return []
        
        values = self._redis.mget(*keys)
        commands = []
        for key, value in zip(keys, values):
            if value:
                command_data = json.loads(value)
                command_data["user_id"] = key.split(":", 1)[1]
                commands.append(command_data)
        return commands

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
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://snel-pointless.vercel.app",
        "https://snel-pointless-git-main-papas-projects-5b188431.vercel.app"
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
    moralis_key = os.environ.get("MORALIS_API_KEY")

    if not all([alchemy_key, coingecko_key]):
        logger.error("Missing required environment variables")
        raise ValueError("Missing required environment variables")

    # Set Alchemy key
    set_alchemy_key(alchemy_key)

# OpenAI API key header
openai_key_header = APIKeyHeader(name="X-OpenAI-Key", auto_error=False)

def get_openai_key(api_key: str = Depends(openai_key_header)) -> str:
    # Check if we're in development mode
    is_development = os.environ.get("ENVIRONMENT") == "development"
    
    # First try to get from header (user-provided key)
    if api_key:
        return api_key

    # Then try environment variable (only in development)
    env_key = os.environ.get("OPENAI_API_KEY")
    if env_key and is_development:
        logger.info("Using development OpenAI API key from environment")
        return env_key
    
    # In production, require user-provided key
    if not is_development:
        raise HTTPException(
            status_code=401,
            detail="OpenAI API Key is required in the X-OpenAI-Key header for production use"
        )
    
    # If we're in development but no key is available
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
    # Log environment
    environment = os.environ.get("ENVIRONMENT", "production")
    logger.info(f"Starting API in {environment} environment")
    
    init_services()
    
    # Test Redis connection
    try:
        # Test Redis operations
        test_user_id = "test_user"
        test_command = "test_command"
        
        # Store test command
        command_store.store_command(test_user_id, test_command, chain_id=1)  # Use chain_id=1 for testing
        logger.info("Test command stored successfully")
        
        # Retrieve test command
        stored_command = command_store.get_command(test_user_id)
        if stored_command and stored_command["command"] == test_command:
            logger.info("Test command retrieved successfully")
        else:
            logger.error("Test command retrieval failed")
            
        # Clear test command
        command_store.clear_command(test_user_id)
        logger.info("Test command cleared successfully")
        
    except Exception as e:
        logger.error(f"Failed to test Redis connection: {e}")
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
                # Store the original ID for logging
                original_id = command_request.creator_id
                
                # For Redis operations, we'll use lowercase for consistency
                user_id = command_request.creator_id.lower()
                
                # For display and other operations, we can use checksum
                checksum_id = to_checksum_address(command_request.creator_id)
                
                logger.info(f"User ID normalization: Original: {original_id}, Lowercase: {user_id}, Checksum: {checksum_id}")
            else:
                user_id = command_request.creator_id.lower()
                logger.info(f"User ID normalized to lowercase: {user_id}")
        except ValueError:
            user_id = command_request.creator_id.lower()
            logger.info(f"User ID normalized to lowercase (after ValueError): {user_id}")
            
        # Update the request with normalized ID
        command_request.creator_id = user_id
        
        logger.info(f"Processing command: {command_request.content} on chain {command_request.chain_id}")
        logger.info(f"User ID (normalized): {user_id}, Name: {command_request.creator_name}")
        
        # Handle confirmations
        content = command_request.content.lower().strip()
        if content in ["yes", "y", "confirm"]:
            logger.info(f"Confirmation received from user {user_id}")
            
            # List all commands for debugging
            all_keys = command_store.list_all_commands()
            logger.info(f"All pending command keys: {all_keys}")
            
            # Get pending command
            try:
                # Double-check the key format
                key = command_store._make_key(user_id)
                logger.info(f"Looking up command with key: {key}")
                
                # Get raw data first
                raw_data = command_store._redis.get(key)
                logger.info(f"Raw Redis data for key {key}: {raw_data}")
                
                # Try direct Redis get with different key formats for debugging
                try:
                    # Try with lowercase user ID
                    lowercase_key = f"pending_command:{user_id.lower()}"
                    if lowercase_key != key:
                        lowercase_data = command_store._redis.get(lowercase_key)
                        logger.info(f"Raw Redis data for lowercase key {lowercase_key}: {lowercase_data}")
                    
                    # Try with non-checksum address
                    if user_id.startswith("0x"):
                        non_checksum_key = f"pending_command:{user_id.lower()}"
                        if non_checksum_key != key and non_checksum_key != lowercase_key:
                            non_checksum_data = command_store._redis.get(non_checksum_key)
                            logger.info(f"Raw Redis data for non-checksum key {non_checksum_key}: {non_checksum_data}")
                except Exception as e:
                    logger.error(f"Error checking alternative keys: {e}")
                
                pending_data = command_store.get_command(user_id)
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
                        command_store.clear_command(user_id)
                        
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
            command_store.store_command(
                user_id,
                bot_message.metadata["pending_command"],
                command_request.chain_id
            )
            
            # Verify storage immediately
            stored = command_store.get_command(user_id)
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
            
        # Check for dollar amount format
        is_dollar_amount = False
        
        # First, try to parse as a regular swap command
        parts = command.split()
        if len(parts) >= 5:
            # Check for dollar amount format: "swap eth for usdc, $1 worth"
            # or "swap $1 worth of eth for usdc"
            dollar_indicators = ["$", "dollar", "dollars", "usd", "worth"]
            
            command_str = command.lower()
            if any(indicator in command_str for indicator in dollar_indicators):
                is_dollar_amount = True
                logger.info(f"Detected dollar amount format in command: {command}")
                
                # Try to extract the dollar amount
                dollar_amount = None
                
                # Pattern: "swap eth for usdc, $1 worth"
                if "," in command_str and "$" in command_str:
                    # Extract the part after the comma
                    after_comma = command_str.split(",", 1)[1].strip()
                    # Extract the number after the $ sign
                    if "$" in after_comma:
                        try:
                            dollar_amount = float(after_comma.split("$")[1].split()[0])
                            logger.info(f"Extracted dollar amount: ${dollar_amount}")
                        except (ValueError, IndexError):
                            logger.error("Failed to extract dollar amount after comma")
                
                # Pattern: "swap $1 worth of eth for usdc"
                elif "$" in command_str and "worth" in command_str and "of" in command_str:
                    try:
                        # Extract the part between $ and "worth"
                        dollar_part = command_str.split("$")[1].split("worth")[0].strip()
                        dollar_amount = float(dollar_part)
                        logger.info(f"Extracted dollar amount from 'worth of' pattern: ${dollar_amount}")
                    except (ValueError, IndexError):
                        logger.error("Failed to extract dollar amount from 'worth of' pattern")
                
                # If we found a dollar amount, we need to determine the tokens
                if dollar_amount is not None:
                    # Extract token_in and token_out
                    token_in = None
                    token_out = None
                    
                    # Pattern: "swap eth for usdc, $1 worth"
                    if "for" in command_str:
                        parts = command_str.split("for")
                        if len(parts) >= 2:
                            # Extract token_in from the part before "for"
                            before_for = parts[0].strip()
                            if "swap" in before_for:
                                token_in_part = before_for.split("swap")[1].strip()
                                if "worth of" in token_in_part:
                                    token_in = token_in_part.split("worth of")[1].strip()
                                else:
                                    token_in = token_in_part
                            
                            # Extract token_out from the part after "for"
                            after_for = parts[1].strip()
                            if "," in after_for:
                                token_out = after_for.split(",")[0].strip()
                            else:
                                token_out = after_for.split()[0].strip()
                    
                    if token_in and token_out:
                        logger.info(f"Extracted tokens from dollar amount command: {token_in} -> {token_out}")
                        
                        # Look up tokens
                        token_in_address, token_in_symbol = await lookup_token(token_in, chain_id)
                        token_out_address, token_out_symbol = await lookup_token(token_out, chain_id)
                        
                        # Use the canonical symbols if found
                        if token_in_symbol:
                            token_in = token_in_symbol
                        if token_out_symbol:
                            token_out = token_out_symbol
                        
                        # For dollar amount swaps, we need to calculate the token amount
                        # This will be handled by the pipeline, so we just set is_target_amount=False
                        # and amount_is_usd=True
                        return SwapCommand(
                            action="swap",
                            amount=dollar_amount,
                            token_in=token_in.upper(),
                            token_out=token_out.upper(),
                            is_target_amount=False,
                            amount_is_usd=True
                        )
        
        # If not a dollar amount format, proceed with regular parsing
        if len(parts) == 5 and parts[0].lower() == "swap" and (parts[3].lower() == "for" or parts[3].lower() == "to"):
            # Get tokens
            token_in = parts[2]
            token_out = parts[4]
            
            # Look up tokens
            token_in_address, token_in_symbol = await lookup_token(token_in, chain_id)
            token_out_address, token_out_symbol = await lookup_token(token_out, chain_id)
            
            # Use the canonical symbols if found
            if token_in_symbol:
                token_in = token_in_symbol
            if token_out_symbol:
                token_out = token_out_symbol
            
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
                        token_out=token_out,
                        is_target_amount=False
                    )
                    
                return SwapCommand(
                    action="swap",
                    amount=amount,
                    token_in=token_in,
                    token_out=token_out,
                    is_target_amount=False
                )
            except ValueError:
                logger.error(f"Failed to parse amount: {parts[1]}")
                return None
                
        return None
    except (ValueError, IndexError) as e:
        logger.error(f"Failed to parse swap command: {e}")
        return None

# Token decimals mapping
TOKEN_DECIMALS = {
    "ETH": 18,
    "WETH": 18,
    "USDC": 6,
    "USDT": 6,
    "DAI": 18,
}

# Add token aliases mapping
TOKEN_ALIASES = {
    # Common aliases
    "ETH": ["WETH", "ETHEREUM"],
    "USDC": ["USD", "USDC.E"],
    "USDT": ["TETHER"],
    "BTC": ["WBTC", "BITCOIN"],
    
    # Chain-specific tokens
    "SCR": ["$SCR", "SCROLL"],  # Scroll token
    "OP": ["$OP", "OPTIMISM"],  # Optimism token
    "ARB": ["$ARB", "ARBITRUM"],  # Arbitrum token
    "BASE": ["$BASE"],  # Base token
    "MATIC": ["$MATIC", "POLYGON"],  # Polygon token
}

# Reverse lookup for aliases
REVERSE_ALIASES = {}
for main_token, aliases in TOKEN_ALIASES.items():
    for alias in aliases:
        REVERSE_ALIASES[alias] = main_token

async def lookup_token(token_symbol: str, chain_id: int) -> Tuple[Optional[str], Optional[str]]:
    """
    Look up a token by symbol or alias and return its address and canonical symbol.
    
    Args:
        token_symbol: The token symbol or alias to look up
        chain_id: The chain ID to look up the token on
        
    Returns:
        Tuple of (token_address, canonical_symbol) or (None, None) if not found
    """
    # Clean up the token symbol
    clean_symbol = token_symbol.upper().strip()
    if clean_symbol.startswith("$"):
        clean_symbol = clean_symbol[1:]  # Remove $ prefix
    
    logger.info(f"Looking up token: {clean_symbol} on chain {chain_id}")
    
    # Check if it's a known alias
    if clean_symbol in REVERSE_ALIASES:
        canonical_symbol = REVERSE_ALIASES[clean_symbol]
        logger.info(f"Found alias {clean_symbol} -> {canonical_symbol}")
        clean_symbol = canonical_symbol
    
    # Check if it's in our predefined token addresses
    chain_tokens = TOKEN_ADDRESSES.get(chain_id, {})
    if clean_symbol in chain_tokens:
        logger.info(f"Found token {clean_symbol} in predefined addresses")
        return chain_tokens[clean_symbol], clean_symbol
    
    # Try to look up using Moralis API
    moralis_api_key = os.environ.get("MORALIS_API_KEY")
    if not moralis_api_key:
        logger.warning("Moralis API key not found, skipping token lookup")
        return None, None
    
    try:
        # Map chain ID to Moralis chain name
        chain_mapping = {
            1: "eth",
            10: "optimism",
            56: "bsc",
            137: "polygon",
            42161: "arbitrum",
            8453: "base",
            534352: "scroll"
        }
        
        moralis_chain = chain_mapping.get(chain_id)
        if not moralis_chain:
            logger.warning(f"Chain {chain_id} not supported by Moralis")
            return None, None
        
        # Query Moralis API
        async with aiohttp.ClientSession() as session:
            url = f"https://deep-index.moralis.io/api/v2/erc20/metadata/symbols"
            params = {
                "chain": moralis_chain,
                "symbols": clean_symbol
            }
            headers = {
                "accept": "application/json",
                "X-API-Key": moralis_api_key
            }
            
            async with session.get(url, params=params, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    if data and len(data) > 0:
                        # Return the first match
                        token_data = data[0]
                        logger.info(f"Found token via Moralis: {token_data}")
                        return token_data.get("address"), token_data.get("symbol")
                else:
                    logger.warning(f"Moralis API returned status {response.status}")
    
    except Exception as e:
        logger.error(f"Error looking up token with Moralis: {e}")
    
    # If all else fails, try CoinGecko as a last resort
    try:
        coingecko_api_key = os.environ.get("COINGECKO_API_KEY")
        if not coingecko_api_key:
            return None, None
            
        async with aiohttp.ClientSession() as session:
            url = "https://pro-api.coingecko.com/api/v3/search"
            params = {
                "query": clean_symbol,
                "x_cg_pro_api_key": coingecko_api_key
            }
            
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if data and "coins" in data and len(data["coins"]) > 0:
                        # Get the first match
                        coin = data["coins"][0]
                        logger.info(f"Found token via CoinGecko: {coin}")
                        # CoinGecko doesn't provide addresses directly, but we can return the symbol
                        return None, coin.get("symbol").upper()
    
    except Exception as e:
        logger.error(f"Error looking up token with CoinGecko: {e}")
    
    return None, None

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
            # Handle dollar amount swaps
            if swap_command.amount_is_usd:
                logger.info(f"Processing dollar amount swap: ${swap_command.amount} worth of {swap_command.token_in} for {swap_command.token_out}")
                
                # Get token price to convert USD to token amount
                from app.services.prices import get_token_price
                price_per_token, token_in_decimals = await get_token_price(
                    swap_command.token_in,
                    token_addresses.get(swap_command.token_in),
                    tx_request.chain_id
                )
                
                if not price_per_token:
                    raise ValueError(f"Could not get price for {swap_command.token_in}")
                
                # Calculate token amount from USD amount
                token_amount = swap_command.amount / price_per_token
                logger.info(f"Converted ${swap_command.amount} to {token_amount} {swap_command.token_in} at price ${price_per_token}")
                
                # Update the swap command with the calculated token amount
                swap_command.amount = token_amount
            else:
                # Get token decimals - first try hardcoded values, then fallback to price API
                token_in_upper = swap_command.token_in.upper()
                if token_in_upper in TOKEN_DECIMALS:
                    token_in_decimals = TOKEN_DECIMALS[token_in_upper]
                    logger.info(f"Using hardcoded decimals for {token_in_upper}: {token_in_decimals}")
                else:
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
                # For other tokens, use their specific decimals
                amount_in = int(swap_command.amount * (10 ** token_in_decimals))
                logger.info(f"Converting {swap_command.amount} {swap_command.token_in} to {amount_in} (using {token_in_decimals} decimals)")
            
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
        # Check Redis connection
        redis_status = "unknown"
        redis_error = None
        try:
            # Test basic Redis operations
            test_key = "health_check_test"
            # Check if Redis is properly initialized
            if hasattr(command_store, '_redis') and command_store._redis is not None:
                command_store._redis.set(test_key, "test")
                command_store._redis.delete(test_key)
                redis_status = "connected"
            else:
                redis_status = "error"
                redis_error = "Redis client not properly initialized"
        except Exception as e:
            redis_status = "error"
            redis_error = str(e)
            logger.error(f"Redis health check failed: {e}")

        # Check if required environment variables are set
        env_vars = {
            "REDIS_URL": os.environ.get("REDIS_URL") and isinstance(os.environ.get("REDIS_URL"), str),
            "UPSTASH_REDIS_REST_URL": os.environ.get("UPSTASH_REDIS_REST_URL") and isinstance(os.environ.get("UPSTASH_REDIS_REST_URL"), str),
            "UPSTASH_REDIS_REST_TOKEN": os.environ.get("UPSTASH_REDIS_REST_TOKEN") and isinstance(os.environ.get("UPSTASH_REDIS_REST_TOKEN"), str),
            "MORALIS_API_KEY": bool(os.environ.get("MORALIS_API_KEY")),
            "ALCHEMY_KEY": bool(os.environ.get("ALCHEMY_KEY")),
            "COINGECKO_API_KEY": bool(os.environ.get("COINGECKO_API_KEY")),
        }
        
        return {
            "status": "healthy" if redis_status == "connected" else "unhealthy",
            "timestamp": datetime.datetime.now().isoformat(),
            "services": {
                "redis": {
                    "status": redis_status,
                    "error": redis_error
                }
            },
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
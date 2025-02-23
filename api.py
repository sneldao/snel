import configure_logging  # This must be the first import

import os
import asyncio
import logging
from typing import Optional
from enum import StrEnum
from fastapi import FastAPI, HTTPException, Header, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
from eth_typing import HexAddress
import httpx
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import datetime
import sys

# Initialize logger using the configured logger
logger = logging.getLogger(__name__)

try:
    from eth_rpc import set_alchemy_key
    from dowse import Pipeline
    from dowse.impls.basic.llms import BasicTweetClassifier, BasicTwitterCommands, BasicTwitterQuestion
    from dowse.impls.basic.effects import Printer
    from dowse.impls.basic.source import TwitterMock
    from dowse.models import Tweet
    from kyber import (
        get_quote as kyber_quote,
        KyberSwapError,
        NoRouteFoundError,
        InsufficientLiquidityError,
        InvalidTokenError,
        BuildTransactionError,
        get_chain_from_chain_id,
    )
except ImportError as e:
    logger.error(f"Failed to import required packages: {e}")
    raise

class Classifications(StrEnum):
    """A class that defines the different classifications that can be made by the pipeline."""
    COMMANDS = "commands"
    QUESTION = "question"

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
        "https://snel-pointless.vercel.app",  # Production domain
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

init_services()

# OpenAI API key header
openai_key_header = APIKeyHeader(name="X-OpenAI-Key", auto_error=False)

class CommandRequest(BaseModel):
    content: str
    creator_name: str = "@user"
    creator_id: int = 1
    chain_id: Optional[int] = None  # Add chain_id field

class CommandResponse(BaseModel):
    content: Optional[str] = None
    error_message: Optional[str] = None
    pending_command: Optional[str] = None

class TransactionRequest(BaseModel):
    command: str
    wallet_address: HexAddress
    chain_id: int  # Add chain_id to the request

class TransactionResponse(BaseModel):
    to: HexAddress
    data: str
    value: str  # hex string of the value in wei
    chain_id: int
    method: str  # e.g., "swap", "transfer"
    gas_limit: str  # hex string
    gas_price: Optional[str] = None  # hex string, optional for EIP-1559
    max_fee_per_gas: Optional[str] = None  # hex string, for EIP-1559
    max_priority_fee_per_gas: Optional[str] = None  # hex string, for EIP-1559
    needs_approval: bool = False
    token_to_approve: Optional[HexAddress] = None
    spender: Optional[HexAddress] = None

class SwapCommand(BaseModel):
    token_in: str
    token_out: str
    amount_in: float

class ChainConfig:
    """Configuration for supported chains."""
    SUPPORTED_CHAINS = {
        1: "Ethereum",
        8453: "Base",
        42161: "Arbitrum",
        10: "Optimism",
        137: "Polygon",
        43114: "Avalanche"
    }

    @staticmethod
    def is_supported(chain_id: int) -> bool:
        return chain_id in ChainConfig.SUPPORTED_CHAINS

    @staticmethod
    def get_chain_name(chain_id: int) -> str:
        return ChainConfig.SUPPORTED_CHAINS.get(chain_id, "Unknown")

async def get_token_addresses(chain_id: int) -> dict[str, HexAddress]:
    """Get token addresses for the specified chain."""
    # Common token addresses across different chains
    addresses = {
        1: {  # Ethereum
            "ETH": HexAddress("0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE"),
            "USDC": HexAddress("0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"),
            "UNI": HexAddress("0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984"),
        },
        8453: {  # Base
            "ETH": HexAddress("0x4200000000000000000000000000000000000006"),
            "USDC": HexAddress("0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"),
            "UNI": HexAddress("0x0000000000000000000000000000000000000000"),  # Example
        },
        10: {  # Optimism
            "ETH": HexAddress("0x4200000000000000000000000000000000000006"),
            "USDC": HexAddress("0x7F5c764cBc14f9669B88837ca1490cCa17c31607"),  # Updated USDC on Optimism
            "UNI": HexAddress("0x6fd9d7AD17242c41f7131d257212c54A0e816691"),
        },
        42161: {  # Arbitrum
            "ETH": HexAddress("0x82aF49447D8a07e3bd95BD0d56f35241523fBab1"),
            "USDC": HexAddress("0xaf88d065e77c8cC2239327C5EDb3A432268e5831"),
            "UNI": HexAddress("0xFa7F8980b0f1E64A2062791cc3b0871572f1F7f0"),
        },
        137: {  # Polygon
            "ETH": HexAddress("0x7ceB23fD6bC0adD59E62ac25578270cFf1b9f619"),
            "USDC": HexAddress("0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"),
            "UNI": HexAddress("0xb33EaAd8d922B1083446DC23f610c2567fB5180f"),
        },
        43114: {  # Avalanche
            "ETH": HexAddress("0x49D5c2BdFfac6CE2BFdB6640F4F80f226bc10bAB"),
            "USDC": HexAddress("0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E"),
            "UNI": HexAddress("0x8eBAf22B6F053dFFeaf46f4Dd9eFA95D89ba8580"),
        },
        534352: {  # Scroll
            "ETH": HexAddress("0x5300000000000000000000000000000000000004"),
            "USDC": HexAddress("0x06eFdBFf2a14a7c8E15944D1F4A48F9F95F663A4"),
            "UNI": HexAddress("0x0000000000000000000000000000000000000000"),  # Placeholder
        }
    }
    
    if chain_id not in addresses:
        chain_name = ChainConfig.get_chain_name(chain_id)
        raise ValueError(f"Token addresses not configured for {chain_name} (chain ID: {chain_id})")
    
    return addresses[chain_id]

async def get_token_price(token_id: str) -> float:
    """Get token price from CoinGecko."""
    token_mapping = {
        "ETH": "ethereum",
        "UNI": "uniswap",
        # Add more tokens as needed
    }
    
    if token_id not in token_mapping:
        raise ValueError(f"Unsupported token: {token_id}")
        
    coin_id = token_mapping[token_id]
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd"
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers={
                    "x-cg-demo-api-key": os.environ["COINGECKO_API_KEY"]
                }
            )
            if response.status_code == 429:  # Rate limit exceeded
                logger.warning("CoinGecko rate limit exceeded")
                raise HTTPException(
                    status_code=429,
                    detail="Rate limit exceeded. Please try again later."
                )
            data = response.json()
            return data[coin_id]["usd"]
    except httpx.HTTPError as e:
        logger.error(f"HTTP error fetching price from CoinGecko: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch price data. Please try again later."
        )
    except Exception as e:
        logger.error(f"Error fetching price from CoinGecko: {e}")
        raise

async def handle_price_query(query: str) -> str:
    """Handle price-related queries."""
    try:
        # Extract token symbol from query
        token = query.lower()
        if "$eth" in token or "eth" in token:
            price = await get_token_price("ETH")
            return f"The current price of ETH is ${price:,.2f}"
        elif "$uni" in token or "uni" in token:
            price = await get_token_price("UNI")
            return f"The current price of UNI is ${price:,.2f}"
        # Add more tokens as needed
        else:
            return "I can check prices for ETH and UNI. Please specify which token you'd like to know about."
    except Exception as e:
        logger.error(f"Error getting price: {e}")
        return "Sorry, I couldn't fetch the price at the moment. Please try again later."

async def parse_swap_command(content: str, chain_id: int) -> Optional[SwapCommand]:
    """Parse a swap command to extract token and amount information."""
    content = content.lower()
    try:
        # Basic pattern matching for swap commands
        if "swap" not in content:
            return None
            
        # Extract amount and tokens
        words = content.split()
        amount = None
        token_in = None
        token_out = None
        
        for i, word in enumerate(words):
            if word.replace(".", "").isdigit():
                amount = float(word)
                if i + 1 < len(words):
                    token_in = words[i + 1].strip("$")
            elif word == "for" and i + 1 < len(words):
                token_out = words[i + 1].strip("$")
                
        if amount and token_in and token_out:
            # Validate chain support
            if not ChainConfig.is_supported(chain_id):
                raise ValueError(
                    f"Chain {chain_id} is not supported. Supported chains: "
                    f"{', '.join(f'{name} ({id})' for id, name in ChainConfig.SUPPORTED_CHAINS.items())}"
                )

            # Get token addresses for the chain
            token_addresses = await get_token_addresses(chain_id)
            
            # Validate tokens are supported on this chain
            token_in_upper = token_in.upper()
            token_out_upper = token_out.upper()
            
            if token_in_upper not in token_addresses:
                raise ValueError(f"{token_in_upper} is not supported on {ChainConfig.get_chain_name(chain_id)}")
            if token_out_upper not in token_addresses:
                raise ValueError(f"{token_out_upper} is not supported on {ChainConfig.get_chain_name(chain_id)}")

            return SwapCommand(
                token_in=token_in_upper,
                token_out=token_out_upper,
                amount_in=amount
            )
        return None
    except Exception as e:
        logger.error(f"Error parsing swap command: {e}")
        raise

async def get_openai_key(
    openai_key: str = Depends(openai_key_header),
) -> str:
    """Validate and return OpenAI API key."""
    if not openai_key:
        raise HTTPException(
            status_code=401,
            detail="OpenAI API key is required. Please provide it in the X-OpenAI-Key header."
        )
    return openai_key

async def get_api_keys(request: Request) -> dict[str, str]:
    """Get OpenAI API key from request headers."""
    openai_key = request.headers.get("X-OpenAI-Key")
    if not openai_key:
        raise HTTPException(
            status_code=401,
            detail="OpenAI API key is required. Please provide it in the X-OpenAI-Key header."
        )
    return {"OPENAI_API_KEY": openai_key}

@app.post("/api/process-command")
@limiter.limit("20/minute")
async def process_command(
    request: Request,
    command_request: CommandRequest,
    openai_key: str = Depends(get_openai_key)
) -> CommandResponse:
    try:
        # Set OpenAI API key for this request
        os.environ["OPENAI_API_KEY"] = openai_key
        
        logger.info(f"Processing command: {command_request.content} on chain {command_request.chain_id}")
        
        # Check if it's a price query
        if "price" in command_request.content.lower():
            response = await handle_price_query(command_request.content)
            return CommandResponse(content=response)

        # Check if it's a swap command
        content = command_request.content.lower()
        if "swap" in content:
            try:
                logger.info("Processing swap command...")
                # Use the provided chain ID or default to Base
                chain_id = command_request.chain_id if command_request.chain_id else 8453
                logger.info(f"Using chain ID: {chain_id}")
                
                swap_command = await parse_swap_command(content, chain_id=chain_id)
                logger.info(f"Parsed swap command: {swap_command}")
                
                if swap_command:
                    # Store the normalized command format for later execution
                    normalized_command = f"swap {swap_command.amount_in} {swap_command.token_in} for {swap_command.token_out}"
                    logger.info(f"Normalized command: {normalized_command}")
                    
                    # Get chain name for the message
                    chain_name = ChainConfig.get_chain_name(chain_id)
                    logger.info(f"Chain name: {chain_name}")
                    
                    # For now, return a preview of what will be swapped
                    preview = (
                        f"I'll help you swap {swap_command.amount_in} {swap_command.token_in} "
                        f"for {swap_command.token_out}.\n\n"
                        f"The swap will be executed on the {chain_name} chain.\n\n"
                        f"Does this look good? Reply with 'yes' to confirm or 'no' to cancel."
                    )
                    return CommandResponse(
                        content=preview,
                        error_message=None,
                        pending_command=normalized_command
                    )
                else:
                    logger.warning("Failed to parse swap command")
                    return CommandResponse(
                        content="I couldn't understand your swap command. Please use the format: 'swap 1 usdc for eth'"
                    )
            except ValueError as ve:
                logger.error(f"ValueError in swap command: {ve}")
                return CommandResponse(content=str(ve))
            except Exception as e:
                logger.error(f"Error processing swap command: {e}", exc_info=True)
                # Check if this is a transaction rejection
                if "User rejected the request" in str(e):
                    return CommandResponse(
                        content="Transaction cancelled by user.",
                        error_message=None
                    )
                return CommandResponse(
                    content="Sorry, I couldn't process your swap command. Please try again with the format: 'swap 1 usdc for eth'"
                )

        # If we get here, it's not a swap or price command, so use the pipeline
        try:
            result = await pipeline.process(
                Tweet(
                    id=1,
                    content=command_request.content,
                    creator_id=command_request.creator_id,
                    creator_name=command_request.creator_name,
                )
            )
            
            if not result or not result.content:
                return CommandResponse(
                    content="I'm not sure how to help with that. Try asking about prices or making a swap!"
                )

            # Clean up the response format
            content = result.content
            if isinstance(content, str):
                if content.startswith('response="') and content.endswith('"'):
                    content = content[10:-1]

            return CommandResponse(content=content)
            
        except Exception as e:
            logger.error(f"Pipeline processing error: {e}")
            return CommandResponse(
                content="I'm having trouble understanding that command. Try asking about prices or making a swap!"
            )

    except Exception as e:
        logger.error(f"Unexpected error in command processing: {e}", exc_info=True)
        # Check if this is a transaction rejection
        if "User rejected the request" in str(e):
            return CommandResponse(
                content="Transaction cancelled by user.",
                error_message=None
            )
        return CommandResponse(
            content="Sorry, something went wrong. Please try again!"
        )

async def execute_swap(
    token_in: HexAddress,
    token_out: HexAddress,
    amount: int,
    chain_id: int,
    recipient: HexAddress,
) -> TransactionResponse:
    """Execute swap using Kyber's API."""
    try:
        logger.info(f"Executing swap with Kyber: token_in={token_in}, token_out={token_out}, amount={amount}, recipient={recipient}")
        
        # Get quote and build transaction from Kyber
        quote = await kyber_quote(
            token_in=token_in,
            token_out=token_out,
            amount=amount,
            chain_id=chain_id,
            recipient=recipient
        )
        
        logger.info(f"Got quote from Kyber: {quote}")

        # If token_in is not ETH/WETH, we need to check if approval is needed
        if token_in not in [
            "0x4200000000000000000000000000000000000006",  # WETH on OP/Base
            "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE",  # ETH
        ]:
            # Return both approval and swap transactions
            return TransactionResponse(
                to=quote.router_address,
                data=quote.data,
                value="0x0",
                chain_id=chain_id,
                method="swap",
                gas_limit=hex(int(float(quote.gas) * 1.1)),
                needs_approval=True,
                token_to_approve=token_in,
                spender=quote.router_address
            )
        
        # Convert the response to our transaction format
        return TransactionResponse(
            to=quote.router_address,
            data=quote.data,
            value="0x0",
            chain_id=chain_id,
            method="swap",
            gas_limit=hex(int(float(quote.gas) * 1.1)),
            needs_approval=False
        )
            
    except NoRouteFoundError as e:
        logger.error(f"No route found error: {e}")
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except InsufficientLiquidityError as e:
        logger.error(f"Insufficient liquidity error: {e}")
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except InvalidTokenError as e:
        logger.error(f"Invalid token error: {e}")
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except BuildTransactionError as e:
        logger.error(f"Build transaction error: {e}")
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except KyberSwapError as e:
        logger.error(f"KyberSwap error: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Swap failed: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error in execute_swap: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while processing the swap. Please try again."
        )

@app.post("/api/execute-transaction")
@limiter.limit("10/minute")
async def execute_transaction(
    request: Request,
    tx_request: TransactionRequest,
    openai_key: str = Depends(get_openai_key)
) -> TransactionResponse:
    try:
        # Set OpenAI API key for this request
        os.environ["OPENAI_API_KEY"] = openai_key
        
        logger.info(f"Executing transaction for command: {tx_request.command} on chain {tx_request.chain_id}")
        
        # Validate chain support
        if not ChainConfig.is_supported(tx_request.chain_id):
            raise ValueError(
                f"Chain {tx_request.chain_id} is not supported. Supported chains: "
                f"{', '.join(f'{name} ({id})' for id, name in ChainConfig.SUPPORTED_CHAINS.items())}"
            )

        # Parse the swap command with the actual chain ID
        swap_command = await parse_swap_command(tx_request.command, tx_request.chain_id)
        if not swap_command:
            logger.error(f"Failed to parse swap command: {tx_request.command}")
            raise ValueError(f"Invalid swap command format. Expected format: 'swap 1 usdc for eth', got: {tx_request.command}")

        # Get token addresses for the chain
        token_addresses = await get_token_addresses(tx_request.chain_id)
        
        try:
            # Handle decimals correctly for different tokens
            decimals = 18  # Default for most tokens
            if swap_command.token_in == "USDC":
                decimals = 6  # USDC uses 6 decimals
            
            amount_in = int(swap_command.amount_in * (10 ** decimals))
            
            # Execute the swap
            try:
                return await execute_swap(
                    token_in=token_addresses[swap_command.token_in],
                    token_out=token_addresses[swap_command.token_out],
                    amount=amount_in,
                    chain_id=tx_request.chain_id,
                    recipient=tx_request.wallet_address,
                )
            except Exception as swap_error:
                logger.error(f"Error executing swap: {swap_error}")
                if "User rejected the request" in str(swap_error):
                    raise HTTPException(
                        status_code=400,
                        detail="Transaction cancelled by user"
                    )
                elif "No route found" in str(swap_error):
                    raise HTTPException(
                        status_code=400,
                        detail="No valid swap route found. Try a different amount or token pair."
                    )
                elif "insufficient liquidity" in str(swap_error).lower():
                    raise HTTPException(
                        status_code=400,
                        detail="Not enough liquidity for this swap. Try a smaller amount."
                    )
                else:
                    raise HTTPException(
                        status_code=500,
                        detail=f"Failed to execute swap: {str(swap_error)}"
                    )

        except ValueError as ve:
            logger.error(f"Value error in swap preparation: {ve}")
            raise HTTPException(
                status_code=400,
                detail=str(ve)
            )
        except Exception as e:
            logger.error(f"Error preparing swap: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"An error occurred while preparing the swap: {str(e)}"
            )

    except HTTPException:
        raise
    except ValueError as ve:
        logger.error(f"ValueError in transaction preparation: {ve}")
        raise HTTPException(
            status_code=400,
            detail=str(ve)
        )
    except Exception as e:
        logger.error(f"Unexpected error in transaction preparation: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred. Please try again."
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
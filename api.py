import os
import asyncio
import logging
from typing import Optional
from pathlib import Path
from enum import StrEnum
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from eth_typing import HexAddress
import httpx

from eth_rpc import set_alchemy_key
from dowse import Pipeline
from dowse.impls.basic.llms import BasicTweetClassifier, BasicTwitterCommands, BasicTwitterQuestion
from dowse.impls.basic.effects import Printer
from dowse.impls.basic.source import TwitterMock
from dowse.models import Tweet
from dowse.tools.best_route.quicknode import swap as quicknode_swap
from dowse.tools.best_route.kyber import (
    get_quote as kyber_quote,
    KyberSwapError,
    NoRouteFoundError,
    InsufficientLiquidityError,
    InvalidTokenError,
    BuildTransactionError,
)
from dowse.tools.best_route.kyber import get_chain_from_chain_id

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Classifications(StrEnum):
    """A class that defines the different classifications that can be made by the pipeline."""
    COMMANDS = "commands"
    QUESTION = "question"

# Load environment variables
env_path = Path('.env').absolute()
if not env_path.exists():
    raise FileNotFoundError(f"Could not find .env file at {env_path}")
load_dotenv(dotenv_path=env_path, override=True)

# Ensure all required environment variables are in os.environ
required_vars = {
    "ALCHEMY_KEY": os.getenv("ALCHEMY_KEY"),
    "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
    "QUICKNODE_ENDPOINT": os.getenv("QUICKNODE_ENDPOINT"),
    "COINGECKO_API_KEY": os.getenv("COINGECKO_API_KEY")
}

for var_name, value in required_vars.items():
    if not value:
        raise ValueError(f"{var_name} environment variable is required")
    os.environ[var_name] = value

# Set Alchemy key
set_alchemy_key(required_vars["ALCHEMY_KEY"])

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class CommandRequest(BaseModel):
    content: str
    creator_name: str = "@user"
    creator_id: int = 1

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
        # Add more chains as needed
    }
    
    if chain_id not in addresses:
        raise ValueError(f"Token addresses not configured for chain {chain_id}")
    
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
                    "x-cg-demo-api-key": required_vars["COINGECKO_API_KEY"]
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

@app.post("/api/process-command")
async def process_command(request: CommandRequest) -> CommandResponse:
    try:
        logger.info(f"Processing command: {request.content}")
        
        # Check if it's a price query
        if "price" in request.content.lower():
            response = await handle_price_query(request.content)
            return CommandResponse(content=response)

        # Check if it's a swap command
        content = request.content.lower()
        if "swap" in content:
            try:
                # Default to Base chain for initial preview
                swap_command = await parse_swap_command(content, chain_id=8453)
                if swap_command:
                    # Store the normalized command format for later execution
                    normalized_command = f"swap {swap_command.amount_in} {swap_command.token_in} for {swap_command.token_out}"
                    # For now, return a preview of what will be swapped
                    preview = (
                        f"I'll help you swap {swap_command.amount_in} {swap_command.token_in} "
                        f"for {swap_command.token_out}.\n\n"
                        "The swap will be executed on the Base chain.\n\n"
                        f"Does this look good? Reply with 'yes' to confirm or 'no' to cancel."
                    )
                    return CommandResponse(
                        content=preview,
                        error_message=None,
                        pending_command=normalized_command  # Add this field to store the normalized command
                    )
                else:
                    return CommandResponse(
                        content="I couldn't understand your swap command. Please use the format: 'swap 1 usdc for eth'"
                    )
            except ValueError as ve:
                return CommandResponse(content=str(ve))
            except Exception as e:
                logger.error(f"Error processing swap command: {e}")
                return CommandResponse(
                    content="Sorry, I couldn't process your swap command. Please try again with the format: 'swap 1 usdc for eth'"
                )

        # If we get here, it's not a swap or price command, so use the pipeline
        try:
            result = await pipeline.process(
                Tweet(
                    id=1,
                    content=request.content,
                    creator_id=request.creator_id,
                    creator_name=request.creator_name,
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
        return CommandResponse(
            content="Sorry, something went wrong. Please try again!"
        )

async def get_quicknode_endpoint() -> str:
    """Get and validate QuickNode endpoint."""
    endpoint = os.environ.get("QUICKNODE_ENDPOINT")
    if not endpoint:
        raise ValueError("QUICKNODE_ENDPOINT environment variable is required")
    
    # Remove trailing slash if present
    endpoint = endpoint.rstrip('/')
    
    # Validate the endpoint format
    if not endpoint.startswith(('https://', 'http://')):
        raise ValueError("QUICKNODE_ENDPOINT must start with https:// or http://")
    
    return endpoint

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
            recipient=recipient  # Pass the recipient address
        )
        
        logger.info(f"Got quote from Kyber: {quote}")
        
        # Convert the response to our transaction format
        return TransactionResponse(
            to=quote.router_address,  # The Kyber router contract
            data=quote.data,  # The encoded swap data
            value="0x0",  # No ETH value being sent
            chain_id=chain_id,
            method="swap",
            gas_limit=hex(int(float(quote.gas) * 1.1)),  # Use quote's gas estimate with 10% buffer
            max_fee_per_gas=None,  # Will be calculated by the wallet
            max_priority_fee_per_gas=None  # Will be calculated by the wallet
        )
            
    except NoRouteFoundError:
        raise HTTPException(
            status_code=400,
            detail="No route found for this swap. Try a different amount or token pair."
        )
    except InsufficientLiquidityError:
        raise HTTPException(
            status_code=400,
            detail="Not enough liquidity for this swap. Try a smaller amount."
        )
    except InvalidTokenError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Token not supported on this chain: {str(e)}"
        )
    except BuildTransactionError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to build swap: {str(e)}"
        )
    except KyberSwapError as e:
        logger.error(f"KyberSwap error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Swap service temporarily unavailable. Please try again."
        )
    except Exception as e:
        logger.error(f"Unexpected error during swap execution: {e}")
        raise HTTPException(
            status_code=500,
            detail="Something went wrong. Please try again."
        )

@app.post("/api/execute-transaction")
async def execute_transaction(request: TransactionRequest) -> TransactionResponse:
    try:
        logger.info(f"Executing transaction for command: {request.command} on chain {request.chain_id}")
        
        # Validate chain support
        if not ChainConfig.is_supported(request.chain_id):
            raise ValueError(
                f"Chain {request.chain_id} is not supported. Supported chains: "
                f"{', '.join(f'{name} ({id})' for id, name in ChainConfig.SUPPORTED_CHAINS.items())}"
            )

        # Parse the swap command with the actual chain ID
        swap_command = await parse_swap_command(request.command, request.chain_id)
        if not swap_command:
            logger.error(f"Failed to parse swap command: {request.command}")
            raise ValueError(f"Invalid swap command format. Expected format: 'swap 1 usdc for eth', got: {request.command}")

        # Get token addresses for the chain
        token_addresses = await get_token_addresses(request.chain_id)
        
        try:
            # Handle decimals correctly for different tokens
            decimals = 18  # Default for most tokens
            if swap_command.token_in == "USDC":
                decimals = 6  # USDC uses 6 decimals
            
            amount_in = int(swap_command.amount_in * (10 ** decimals))
            
            # Execute the swap
            return await execute_swap(
                token_in=token_addresses[swap_command.token_in],
                token_out=token_addresses[swap_command.token_out],
                amount=amount_in,
                chain_id=request.chain_id,
                recipient=request.wallet_address,
            )

        except Exception as e:
            logger.error(f"Error preparing swap data: {e}")
            if "400 Bad Request" in str(e):
                raise HTTPException(
                    status_code=400,
                    detail="Invalid swap parameters. Please check token addresses and amounts."
                )
            raise HTTPException(
                status_code=500,
                detail=f"Failed to prepare swap: {str(e)}"
            )

    except ValueError as ve:
        logger.error(f"ValueError in transaction preparation: {str(ve)}")
        raise HTTPException(
            status_code=400,
            detail=f"Invalid transaction parameters: {str(ve)}"
        )
    
    except Exception as e:
        logger.error(f"Unexpected error in transaction preparation: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while preparing the transaction: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 
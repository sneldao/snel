from enum import StrEnum
from typing import Optional, Dict, Any, Literal, Type
import logging
from pydantic import BaseModel, Field
from dowse import Pipeline
from dowse.models import Tweet, AgentMessage
from dowse.interfaces import Classifier, Executor, Processor
from dowse.impls.basic.effects import Printer
from emp_agents.providers import OpenAIProvider, OpenAIModelType
from app.models.commands import SwapCommand, BotMessage
from emp_agents import AgentBase
from emp_agents.models import Message, SystemMessage
import json
from upstash_redis.errors import UpstashError

logger = logging.getLogger(__name__)

# Define classification types
class SwapTweet(Tweet):
    """Tweet classified as a swap command."""
    pass

class PriceTweet(Tweet):
    """Tweet classified as a price query."""
    pass

class UnknownTweet(Tweet):
    """Tweet classified as unknown."""
    pass

class TweetWithChain(Tweet):
    """Tweet with chain information."""
    chain_id: Optional[int] = None
    creator_id: str = "anonymous"  # Changed from int to str to support wallet addresses

class ProcessedSwapCommand(BaseModel):
    """Processed swap command with extracted details."""
    amount: float
    token_in: str
    token_out: str
    chain_id: Optional[int] = None
    is_target_amount: bool = False  # True if amount refers to token_out
    amount_is_usd: bool = False  # True if amount is in USD
    natural_command: str = ""  # The command as understood in natural language

class LoadChainData(Processor[Tweet, TweetWithChain]):
    """Processor to add chain information to tweets."""
    async def process(self, tweet: Tweet) -> AgentMessage[TweetWithChain]:
        data = tweet.model_dump()
        if not data.get('chain_id'):
            data['chain_id'] = getattr(tweet, 'chain_id', None)
        return AgentMessage(
            content=TweetWithChain(**data),
            error_message=None
        )

class SwapCommandExtractor(Processor[TweetWithChain, ProcessedSwapCommand]):
    """Extract swap command details from a tweet."""
    provider: OpenAIProvider = Field(description="OpenAI provider for LLM completion")
    prompt: str = Field(default="""
    You are a crypto assistant that understands natural language swap requests.
    Extract swap details from the message, being flexible in understanding various formats.
    
    The user might specify amounts in several ways:
    1. Direct amount: "swap 1 ETH for USDC"
    2. Target amount in token: "get me 100 USDC using ETH"
    3. Target amount in USD: "swap $50 worth of ETH to USDC"
    4. Natural language: "I want to trade my ETH for some USDC"
    5. Contract addresses: Handle Ethereum addresses (e.g. "0x1234...") exactly as provided
    6. Custom tokens: Handle custom tokens with $ prefix (e.g. "$PEPE", "$DICKBUTT") exactly as provided
    
    Return a JSON object with:
    {
        "amount": number,  # The amount specified
        "token_in": string,  # Input token symbol or contract address exactly as provided
        "token_out": string,  # Output token symbol or contract address exactly as provided
        "is_target_amount": boolean,  # true if amount refers to output token or USD
        "amount_is_usd": boolean,  # true if amount is in USD
        "natural_command": string  # The command as understood in natural language
    }
    
    Examples:
    "swap eth to usdc, $1 worth" ->
    {
        "amount": 1.0,
        "token_in": "ETH",
        "token_out": "USDC",
        "is_target_amount": true,
        "amount_is_usd": true,
        "natural_command": "swap ETH worth $1 to get USDC"
    }
    
    "please swap $5 of eth into 0xaF13924f23Be104b96c6aC424925357463b0d105" ->
    {
        "amount": 5.0,
        "token_in": "ETH",
        "token_out": "0xaF13924f23Be104b96c6aC424925357463b0d105",
        "is_target_amount": true,
        "amount_is_usd": true,
        "natural_command": "swap $5 worth of ETH into token at 0xaF13924f23Be104b96c6aC424925357463b0d105"
    }
    
    "swap $1 of eth for $dickbutt" ->
    {
        "amount": 1.0,
        "token_in": "ETH",
        "token_out": "$dickbutt",
        "is_target_amount": true,
        "amount_is_usd": true,
        "natural_command": "swap $1 worth of ETH for $dickbutt token"
    }
    
    If you can't understand the swap request, return:
    {
        "error": "Specific error message explaining what's wrong"
    }
    
    IMPORTANT: 
    1. When a contract address is provided, use it EXACTLY as given, preserving case.
    2. When a custom token with $ prefix is provided, use it EXACTLY as given, preserving case.
    3. DO NOT reject custom tokens with $ prefix - pass them through exactly as provided.
    """)

    async def process(self, tweet: TweetWithChain) -> AgentMessage[ProcessedSwapCommand]:
        try:
            # Create an agent with our prompt
            agent = AgentBase(
                prompt=self.prompt,
                provider=self.provider
            )
            
            # Get the response
            response = await agent.answer(tweet.content)
            logger.info(f"Raw LLM response for swap command: {response}")
            
            # Parse the JSON response
            try:
                data = json.loads(response)
                if "error" in data:
                    return AgentMessage(
                        content=None,
                        error_message=data["error"]
                    )
                
                # Validate tokens using Moralis/CoinGecko
                from app.services.prices import validate_token, _is_valid_contract_address
                
                # Special handling for contract addresses
                token_in = data["token_in"]
                token_out = data["token_out"]
                
                # Special handling for custom tokens with $ prefix
                is_custom_token_in = token_in.startswith('$')
                is_custom_token_out = token_out.startswith('$')
            
                
                # Check if tokens are known special tokens
                if is_custom_token_in and token_in.lower() in known_special_tokens:
                    logger.info(f"Recognized special token {token_in}")
                    token_in_valid = True
                else:
                    # Validate input token (skip validation for custom tokens with $ prefix)
                    token_in_valid = is_custom_token_in or _is_valid_contract_address(token_in) or await validate_token(token_in, tweet.chain_id)
                
                if not token_in_valid:
                    error_msg = (
                        f"The token '{token_in}' is not recognized as a valid cryptocurrency or contract address. "
                        "Please verify the token symbol or provide a valid contract address."
                    )
                    logger.warning(f"Token validation failed: {error_msg}")
                    return AgentMessage(
                        content=None,
                        error_message=error_msg
                    )
                
                # Check if tokens are known special tokens
                if is_custom_token_out and token_out.lower() in known_special_tokens:
                    logger.info(f"Recognized special token {token_out}")
                    token_out_valid = True
                else:
                    # Validate output token (skip validation for custom tokens with $ prefix)
                    token_out_valid = is_custom_token_out or _is_valid_contract_address(token_out) or await validate_token(token_out, tweet.chain_id)
                
                if not token_out_valid:
                    error_msg = (
                        f"The token '{token_out}' is not recognized as a valid cryptocurrency or contract address. "
                        "Please verify the token symbol or provide a valid contract address."
                    )
                    logger.warning(f"Token validation failed: {error_msg}")
                    return AgentMessage(
                        content=None,
                        error_message=error_msg
                    )
                
                # For special tokens, replace with known contract address if needed
                if is_custom_token_in and token_in.lower() in known_special_tokens:
                    logger.info(f"Replacing {token_in} with contract address {known_special_tokens[token_in.lower()]}")
                    token_in = known_special_tokens[token_in.lower()]
                
                if is_custom_token_out and token_out.lower() in known_special_tokens:
                    logger.info(f"Replacing {token_out} with contract address {known_special_tokens[token_out.lower()]}")
                    token_out = known_special_tokens[token_out.lower()]
                
                # Create the command object
                command_obj = ProcessedSwapCommand(
                    amount=data["amount"],
                    token_in=token_in if is_custom_token_in or _is_valid_contract_address(token_in) else token_in.upper(),
                    token_out=token_out if is_custom_token_out or _is_valid_contract_address(token_out) else token_out.upper(),
                    chain_id=tweet.chain_id,
                    is_target_amount=data["is_target_amount"],
                    amount_is_usd=data.get("amount_is_usd", False),
                    natural_command=data.get("natural_command", "")
                )
                
                # Return success with metadata
                return AgentMessage(
                    content=command_obj,
                    error_message=None,
                    metadata={
                        "natural_command": data.get("natural_command", ""),
                        "is_target_amount": command_obj.is_target_amount,
                        "amount_is_usd": command_obj.amount_is_usd,
                        "command_details": command_obj.model_dump()
                    }
                )
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse LLM response: {e}")
                return AgentMessage(
                    content=None,
                    error_message="Could not parse swap command. Please try rephrasing your request."
                )
                
        except Exception as e:
            logger.error(f"Error extracting swap command: {e}", exc_info=True)
            return AgentMessage(
                content=None,
                error_message=f"An error occurred while processing your request: {str(e)}"
            )

class PriceExtractor(Processor[TweetWithChain, str]):
    """Extract token symbol from a price query."""
    provider: OpenAIProvider = Field(description="OpenAI provider for LLM completion")
    prompt: str = Field(default="""
    Extract the token symbol from the price query.
    Supported tokens: ETH, USDC, UNI
    
    Return just the token symbol or null if not found.
    """)

    async def process(self, tweet: TweetWithChain) -> AgentMessage[str]:
        try:
            # Create an agent with our prompt
            agent = AgentBase(
                prompt=self.prompt,
                provider=self.provider
            )
            
            # Get the response
            response = await agent.answer(tweet.content)
            
            token = response.strip().upper()
            if token in ["ETH", "USDC", "UNI"]:
                return AgentMessage(
                    content=token,
                    error_message=None
                )
            else:
                return AgentMessage(
                    content=None,
                    error_message=f"Unsupported token: {token}"
                )
                
        except Exception as e:
            logger.error(f"Error extracting token symbol: {e}")
            return AgentMessage(
                content=None,
                error_message=str(e)
            )

class SwapExecutor(Executor[TweetWithChain, ProcessedSwapCommand]):
    """Executor for swap commands."""
    provider: OpenAIProvider = Field(description="OpenAI provider for LLM completion")
    prompt: str = Field(default="""
    Format a user-friendly swap confirmation message based on the command details:
    
    For USD amounts:
    "I'll help you swap approximately [calculated_amount] [token_in] (~$[usd_amount]) for [token_out]. The exact amount of [token_out] will be determined at the time of the swap."
    
    For target token amounts:
    "I'll help you swap [token_in] to get [target_amount] [token_out]."
    
    For direct amounts:
    "I'll help you swap [amount] [token_in] for [token_out]."
    
    If token_in or token_out is a contract address, try to include its name/symbol if available.
    
    For custom tokens with $ prefix (like $PEPE or $DICKBUTT), add this warning:
    "Note: [token] appears to be a custom token. Please verify the contract address before proceeding with the swap."
    
    Add: "Does this look good? Reply with 'yes' to confirm or 'no' to cancel."
    """)
    processors: list[type[Processor]] = [SwapCommandExtractor]

    async def get_token_info(self, token: str, chain_id: Optional[int] = None) -> tuple[str, Optional[str], bool]:
        """Get token display info (address/symbol, name if available, and whether it's verified)."""
        from app.services.prices import _is_valid_contract_address, get_token_metadata
        
        # Check if this is a custom token with $ prefix
        if token.startswith('$'):
            return token, None, False  # Not verified
            
        if not _is_valid_contract_address(token):
            return token.upper(), None, True  # Standard tokens are verified
            
        try:
            if chain_id:
                logger.info(f"Fetching metadata for token {token} on chain {chain_id}")
                # Try to get metadata from Moralis
                metadata = await get_token_metadata(token, chain_id)
                
                if metadata:
                    symbol = metadata.get("symbol", "").upper()
                    name = metadata.get("name")
                    return symbol, name, True  # Tokens with metadata are verified
                    
        except Exception as e:
            logger.warning(f"Failed to get token metadata: {e}")
            
        # If we get here, we couldn't get metadata
        return token, None, False  # Not verified

    async def execute(self, input_: TweetWithChain) -> AgentMessage[ProcessedSwapCommand]:
        try:
            # First run the processors
            result = None
            for processor_cls in self.processors:
                processor = processor_cls(provider=self.provider)
                result = await processor.process(input_)
                if result.error_message:
                    return result
                input_ = result.content
                
            if not result or result.error_message:
                return AgentMessage(
                    content=None,
                    error_message=result.error_message if result else "Failed to process command"
                )
                
            command = result.content
            
            # Get token info for display
            token_in_info, token_in_name, token_in_verified = await self.get_token_info(command.token_in, command.chain_id)
            token_out_info, token_out_name, token_out_verified = await self.get_token_info(command.token_out, command.chain_id)
            
            # Add warnings for unverified tokens
            warnings = []
            if not token_in_verified:
                warnings.append(f"⚠️ {token_in_info} appears to be a custom or unverified token. Please verify before proceeding.")
            if not token_out_verified:
                warnings.append(f"⚠️ {token_out_info} appears to be a custom or unverified token. Please verify before proceeding.")
            
            # Format the response using the prompt
            if isinstance(input_, ProcessedSwapCommand):
                try:
                    # Get token prices if needed
                    from app.services.prices import get_token_price, _is_valid_contract_address
                    
                    # Get token display info - preserve original addresses for the command
                    token_in_original = input_.token_in
                    token_out_original = input_.token_out
                    
                    logger.info(f"Getting token info for input token: {token_in_original}")
                    token_in_symbol, token_in_name, token_in_verified = await self.get_token_info(input_.token_in, input_.chain_id)
                    logger.info(f"Getting token info for output token: {token_out_original}")
                    token_out_symbol, token_out_name, token_out_verified = await self.get_token_info(input_.token_out, input_.chain_id)
                    
                    logger.info(f"Token info - Input: {token_in_name or token_in_symbol}, Output: {token_out_name or token_out_symbol}")
                    
                    # Format display names - use name if available, otherwise use address
                    token_in_display = token_in_name or token_in_symbol
                    token_out_display = token_out_name or token_out_symbol
                    
                    if input_.amount_is_usd:
                        # Calculate the input amount based on USD value
                        token_in_price, _ = await get_token_price(input_.token_in)
                        eth_amount = input_.amount / token_in_price
                        message = (
                            f"I'll help you swap approximately {eth_amount:.6f} {token_in_display} (~${input_.amount:.2f}) "
                            f"for {token_out_display}. The exact amount of tokens you'll receive will be determined at "
                            "the time of the swap based on current market rates."
                        )
                        # IMPORTANT: Use original addresses in the command
                        command = f"swap {eth_amount:.6f} {token_in_original} for {token_out_original}"
                        
                        # Update the input object with the calculated amount
                        input_.amount = eth_amount
                        input_.is_target_amount = False
                        input_.amount_is_usd = False
                    elif input_.is_target_amount:
                        message = f"I'll help you swap {token_in_display} to get {input_.amount} {token_out_display}."
                        command = f"swap {token_in_original} for {input_.amount} {token_out_original}"
                    else:
                        message = f"I'll help you swap {input_.amount} {token_in_display} for {token_out_display}."
                        command = f"swap {input_.amount} {token_in_original} for {token_out_original}"
                    
                    message += " Does this look good? Reply with 'yes' to confirm or 'no' to cancel."
                    
                    # Create a Tweet with the response
                    tweet = BotMessage(
                        id=0,  # Bot messages use ID 0
                        content=message,
                        creator_name="@bot",
                        creator_id="bot",
                        metadata={
                            "pending_command": command,
                            "swap_details": {
                                **input_.model_dump(),
                                "natural_command": input_.natural_command,
                                "is_target_amount": input_.is_target_amount,
                                "amount_is_usd": input_.amount_is_usd,
                                "token_in_name": token_in_name,
                                "token_out_name": token_out_name
                            }
                        }
                    )
                    
                    return AgentMessage(
                        content=tweet,
                        error_message=None,
                        metadata=tweet.metadata
                    )
                except UpstashError as e:
                    logger.error(f"Redis error while processing swap: {e}")
                    return AgentMessage(
                        content=None,
                        error_message="Unable to process your swap request at the moment. Please try again."
                    )
                except Exception as e:
                    logger.error(f"Error formatting swap message: {e}", exc_info=True)
                    return AgentMessage(
                        content=None,
                        error_message=f"Failed to prepare swap message: {str(e)}"
                    )
        except Exception as e:
            logger.error(f"Error in swap execution: {e}", exc_info=True)
            return AgentMessage(
                content=None,
                error_message=f"Failed to process swap command: {str(e)}"
            )
        return AgentMessage(
            content=None,
            error_message="Failed to process swap command"
        )

class PriceExecutor(Executor[TweetWithChain, str]):
    """Executor for price queries."""
    provider: OpenAIProvider = Field(description="OpenAI provider for LLM completion")
    prompt: str = Field(default="""
    Format the price response:
    "The current price of [token] is $[price]"
    """)
    processors: list[type[Processor]] = [PriceExtractor]

    async def execute(self, input_: TweetWithChain) -> AgentMessage[str]:
        # First run the processors
        for processor_cls in self.processors:
            processor = processor_cls(provider=self.provider)
            result = await processor.process(input_)
            if result.error_message:
                return result
            input_ = result.content

        # Format the response using the prompt
        if isinstance(input_, str):
            # Create an agent with our prompt
            agent = AgentBase(
                prompt=self.prompt,
                provider=self.provider
            )
            
            # Get the response
            response = await agent.answer(f"Token: {input_}")
            
            # Create a Tweet with the response
            tweet = BotMessage(
                id=0,  # Bot messages use ID 0
                content=response,
                creator_name="@bot",
                creator_id="bot",
                metadata={
                    "token": input_
                }
            )
            
            return AgentMessage(
                content=tweet,
                error_message=None
            )
        return AgentMessage(
            content=None,
            error_message="Failed to process price query"
        )

class UnknownExecutor(Executor[TweetWithChain, TweetWithChain]):
    """Executor for unknown commands."""
    provider: OpenAIProvider = Field(description="OpenAI provider for LLM completion")
    prompt: str = Field(default="I don't understand that request. I can help you with token swaps (e.g. 'swap 1 ETH for USDC') or price queries (e.g. 'what's the price of ETH?').")
    processors: list[type[Processor]] = []

    async def execute(self, input_: TweetWithChain) -> AgentMessage[TweetWithChain]:
        # Create an agent with our prompt
        agent = AgentBase(
            prompt=self.prompt,
            provider=self.provider
        )
        
        # Get the response
        response = await agent.answer(input_.content)
        
        # Create a Tweet with the response
        tweet = BotMessage(
            id=0,  # Bot messages use ID 0
            content=response,
            creator_name="@bot",
            creator_id="bot"
        )
        
        return AgentMessage(
            content=tweet,
            error_message=None
        )

# Global pipeline instance
pipeline = None

def init_pipeline(openai_key: str) -> Pipeline[Tweet, TweetWithChain, Literal["swap", "price", "unknown"]]:
    """Initialize the Dowse pipeline with specialized agents."""
    global pipeline
    if pipeline is None:
        # Create OpenAI provider with specific model
        provider = OpenAIProvider(
            api_key=openai_key,
            default_model=OpenAIModelType.gpt4o
        )
        
        # Create pipeline with routing and effects
        pipeline = Pipeline[Tweet, TweetWithChain, Literal["swap", "price", "unknown"]](
            processors=[LoadChainData()],
            classifier=Classifier[TweetWithChain, Literal["swap", "price", "unknown"]](
                prompt="""
                You are a crypto assistant that helps users with token swaps and price queries.
                Classify the input message into one of these categories:
                - swap: Any message about swapping, exchanging, or buying tokens
                - price: Any message asking about token prices or values
                - unknown: Any other message
                
                Respond with just the classification.
                """,
                provider=provider,
                mapping={
                    "swap": "swap",
                    "price": "price",
                    "unknown": "unknown"
                }
            ),
            handlers={
                "swap": SwapExecutor(provider=provider),
                "price": PriceExecutor(provider=provider),
                "unknown": UnknownExecutor(provider=provider)
            }
        )
    
    return pipeline

def get_pipeline(openai_key: str) -> Pipeline[Tweet, TweetWithChain, Literal["swap", "price", "unknown"]]:
    """Get the Dowse pipeline instance, initializing it if necessary."""
    global pipeline
    if pipeline is None:
        return init_pipeline(openai_key)
    return pipeline 
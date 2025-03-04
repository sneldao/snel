from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, validator
from .base import PointlessAgent, AgentMessage
from app.services.token_service import TokenService
from app.services.prices import get_token_price
import logging
import json

logger = logging.getLogger(__name__)

class PriceResponse(BaseModel):
    """Response model for price queries."""
    tokens: List[str]
    vs_currency: str = "USD"
    natural_command: Optional[str] = None
    is_contract_address: bool = False

    @validator("tokens", each_item=True)
    def validate_token(cls, v):
        if not v:
            raise ValueError("Token cannot be empty")
        # Allow contract addresses to pass through without modification
        return v if v.startswith("0x") else v.strip().upper()

    @validator("vs_currency")
    def validate_vs_currency(cls, v):
        if not v:
            raise ValueError("vs_currency cannot be empty")
        return v.strip().upper()

class PriceAgent(PointlessAgent):
    """Agent for processing price queries."""
    token_service: TokenService = Field(default_factory=TokenService)
    
    def __init__(self, prompt: str = "", provider = None):
        if not prompt:
            prompt = "You are a helpful assistant that processes price queries for cryptocurrencies. You extract token names from natural language questions about prices."
        super().__init__(
            prompt=prompt,
            model="gpt-4-turbo-preview",
            temperature=0.7,
            provider=provider
        )

    async def process_price(self, query: str) -> Dict[str, Any]:
        """Process a price query and return structured response."""
        try:
            response = await self.process(query, response_format=PriceResponse)
            
            if response.get("error"):
                return AgentMessage(
                    error=response["error"],
                    metadata={"query": query}
                ).model_dump()

            return AgentMessage(
                content=response["content"],
                metadata={"query": query}
            ).model_dump()

        except Exception as e:
            return AgentMessage(
                error=f"Failed to process price query: {str(e)}",
                metadata={"query": query}
            ).model_dump()

    async def process_price_query(self, input_text: str, chain_id: Optional[int] = None) -> Dict[str, Any]:
        """Process a price query and return structured data."""
        try:
            # Get raw response from LLM
            response = await self.process(input_text, response_format=PriceResponse)
            if response.get("error"):
                return response
            
            # Extract the response content
            data = response.get("content", {})
            if not data.get("tokens"):
                return AgentMessage(
                    error="No tokens found in query",
                    metadata={"query": input_text}
                ).model_dump()
            
            # Extract token (preserve original case and $ prefix)
            original_token = data["tokens"][0]
            
            # Check if it's a contract address
            if original_token.startswith("0x"):
                logger.info(f"Processing contract address: {original_token}")
                token_info = await self.token_service.lookup_token(original_token, chain_id or 1)
                address, symbol, name, metadata = token_info
                
                if not symbol:
                    return AgentMessage(
                        error=f"Could not find token information for contract address {original_token}",
                        metadata={"query": input_text}
                    ).model_dump()
                
                # Try to get the price using the contract address
                try:
                    price, _ = await get_token_price(symbol, address, chain_id)
                    if price is not None:
                        message = f"The current price of {symbol} ({name}) is ${price:.6f}"
                        return AgentMessage(
                            content=message,
                            metadata={
                                "token": symbol,
                                "price": price,
                                "token_info": metadata
                            }
                        ).model_dump()
                    else:
                        chain_name = self._get_chain_name(chain_id or 1)
                        message = (
                            f"Found token {symbol} ({name}) at {address} but couldn't get its current price on {chain_name}. "
                            f"This could be because:\n"
                            f"1. The token has low or no liquidity in DEX pools\n"
                            f"2. The token is not yet listed on major exchanges\n"
                            f"3. The token is too new or not actively traded"
                        )
                        return AgentMessage(
                            content=message,
                            metadata={
                                "token": symbol,
                                "address": address,
                                "chain_id": chain_id,
                                "error": "no_liquidity"
                            }
                        ).model_dump()
                except Exception as e:
                    logger.error(f"Error getting price for contract {address}: {e}")
                    return AgentMessage(
                        error=f"Failed to get price for token at {address}",
                        metadata={"query": input_text}
                    ).model_dump()
            
            token = original_token.upper()
            
            # Special handling for major cryptocurrencies that might not be on the current chain
            major_cryptos = {
                "BTC": "bitcoin", 
                "BITCOIN": "bitcoin",
                "ETH": "ethereum", 
                "ETHEREUM": "ethereum",
                "SOL": "solana",
                "SOLANA": "solana",
                "DOGE": "dogecoin",
                "DOGECOIN": "dogecoin",
                "XRP": "ripple",
                "RIPPLE": "ripple",
                "ADA": "cardano",
                "CARDANO": "cardano"
            }
            
            if token in major_cryptos:
                try:
                    # Use a direct price lookup for major cryptocurrencies
                    logger.info(f"Using direct price lookup for major cryptocurrency: {token}")
                    
                    # Import the price service
                    from app.services.prices import price_service
                    
                    # Get the price directly from CoinGecko
                    price_data = await price_service._get_price_from_coingecko(token, "usd")
                    if price_data and "price" in price_data:
                        price = price_data["price"]
                        
                        message = f"The current price of {token} is ${price:.6f}"
                        
                        return AgentMessage(
                            content=message,
                            metadata={
                                "token": token,
                                "price": price,
                                "source": "coingecko"
                            }
                        ).model_dump()
                except Exception as e:
                    logger.error(f"Failed to get price for major crypto {token}: {e}")
            
            # Regular token lookup for chain-specific tokens
            logger.info(f"Looking up token {original_token} on chain {chain_id or 1}")
            token_info = await self.token_service.lookup_token(original_token, chain_id or 1)
            address, symbol, name, metadata = token_info
            
            if not address and original_token.startswith('$'):
                # Try OpenOcean lookup for custom tokens
                logger.info(f"Trying OpenOcean lookup for custom token: {original_token}")
                from app.services.prices import price_service
                
                # First try to get the token info from OpenOcean
                clean_symbol = original_token.lstrip('$').upper()
                openocean_result = await self.token_service._lookup_token_by_symbol_openocean(clean_symbol, chain_id or 1)
                if openocean_result[0]:  # If we found the token
                    address = openocean_result[0]
                    symbol = original_token  # Keep the original symbol with $
                    name = openocean_result[2]
                    metadata = {
                        "verified": True,
                        "source": "openocean",
                        "links": self.token_service._get_verification_links(address, chain_id or 1)
                    }
                    
                    # Try to get the price from OpenOcean
                    price_data = await price_service._get_price_from_openocean(symbol, address, chain_id or 1)
                    if price_data and "price" in price_data:
                        message = f"The current price of {symbol} is ${price_data['price']:.6f}"
                        return AgentMessage(
                            content=message,
                            metadata={
                                "token": symbol,
                                "price": price_data["price"],
                                "token_info": metadata
                            }
                        ).model_dump()
            
            if not address:
                # If token not found, provide a helpful message
                chain_name = self._get_chain_name(chain_id or 1)
                message = (
                    f"I couldn't find the token '{original_token}' on the {chain_name} chain. "
                    f"You can:\n"
                    f"1. Try a different token symbol\n"
                    f"2. Specify a different chain\n"
                    f"3. Provide the contract address using: price [contract_address] on {chain_id or 1}"
                )
                
                # Suggest some popular tokens on the current chain
                popular_tokens = self._get_popular_tokens_for_chain(chain_id or 1)
                if popular_tokens:
                    tokens_str = ", ".join([f"${t}" for t in popular_tokens])
                    message += f"\n\nPopular tokens on {chain_name} include: {tokens_str}."
                
                return AgentMessage(
                    content=message,
                    metadata={
                        "query": input_text,
                        "requires_contract": True,
                        "chain_id": chain_id or 1,
                        "chain_name": chain_name,
                        "token_symbol": original_token
                    }
                ).model_dump()
            
            # Use canonical symbol if found
            display_symbol = symbol or token
            
            # Get token price
            try:
                # Try OpenOcean first for custom tokens
                if original_token.startswith('$'):
                    from app.services.prices import price_service
                    price_data = await price_service._get_price_from_openocean(display_symbol, address, chain_id or 1)
                    if price_data and "price" in price_data:
                        price = price_data["price"]
                    else:
                        price, _ = await get_token_price(display_symbol, address, chain_id)
                else:
                    price, _ = await get_token_price(display_symbol, address, chain_id)
                
                if price is None:
                    # If price not found, provide a helpful message
                    chain_name = self._get_chain_name(chain_id or 1)
                    message = (
                        f"I found the token {display_symbol} but couldn't get its current price on the {chain_name} chain. "
                        f"This could be because:\n"
                        f"1. The token has low or no liquidity in DEX pools\n"
                        f"2. The token is not yet listed on major exchanges\n"
                        f"3. The token is too new or not actively traded\n\n"
                        f"You can try checking DEX interfaces like Uniswap or Base Swap directly to see if there are any active trading pairs."
                    )
                    
                    return AgentMessage(
                        content=message,
                        metadata={
                            "query": input_text,
                            "token": display_symbol,
                            "address": address,
                            "chain_id": chain_id,
                            "error": "no_liquidity"
                        }
                    ).model_dump()
                
                # Format response message
                message = f"The current price of {display_symbol} is ${price:.6f}"
                
                return AgentMessage(
                    content=message,
                    metadata={
                        "token": display_symbol,
                        "price": price,
                        "token_info": metadata
                    }
                ).model_dump()
                
            except Exception as e:
                logger.error(f"Failed to get price for {display_symbol}: {e}")
                chain_name = self._get_chain_name(chain_id or 1)
                message = f"I couldn't find the current price for {display_symbol} on the {chain_name} chain. Please try again later or try a different token."
                
                return AgentMessage(
                    content=message,
                    metadata={"query": input_text}
                ).model_dump()
                
        except Exception as e:
            logger.error(f"Error processing price query: {e}", exc_info=True)
            return AgentMessage(
                content="I'm having trouble processing your price query. Please try again with a different token or specify the chain explicitly.",
                metadata={"query": input_text}
            ).model_dump()
    
    def _get_chain_name(self, chain_id: int) -> str:
        """Get a human-readable chain name from a chain ID."""
        chain_names = {
            1: "Ethereum",
            10: "Optimism",
            56: "BNB Chain",
            137: "Polygon",
            42161: "Arbitrum",
            8453: "Base",
            534352: "Scroll"
        }
        return chain_names.get(chain_id, f"chain {chain_id}")
    
    def _get_popular_tokens_for_chain(self, chain_id: int) -> List[str]:
        """Get a list of popular tokens for a specific chain."""
        popular_tokens = {
            1: ["ETH", "USDC", "USDT", "DAI", "WBTC"],
            10: ["OP", "ETH", "USDC", "USDT", "DAI"],
            56: ["BNB", "BUSD", "CAKE", "USDT", "USDC"],
            137: ["MATIC", "USDC", "USDT", "DAI", "WETH"],
            42161: ["ARB", "ETH", "USDC", "USDT", "DAI"],
            8453: ["ETH", "USDC", "DAI", "WETH", "CBETH"],
            534352: ["ETH", "USDC", "USDT", "DAI", "SCR"]
        }
        return popular_tokens.get(chain_id, []) 
from typing import Optional, Dict, Any
import logging
import json
from pydantic import Field
from emp_agents.providers import OpenAIProvider
from app.agents.base import PointlessAgent
from app.services.token_service import TokenService
from app.services.prices import get_token_price

logger = logging.getLogger(__name__)

class PriceAgent(PointlessAgent):
    """Agent for handling token price queries."""
    token_service: TokenService = Field(default_factory=TokenService)
    
    model_config = {
        "arbitrary_types_allowed": True
    }
    
    def __init__(self, provider: OpenAIProvider):
        super().__init__(
            provider=provider,
            prompt="""
            You are a crypto assistant that helps users check token prices.
            Extract the token symbol from the price query.
            
            Return a JSON object with:
            {
                "token": string  # The token symbol the user is asking about
            }
            
            If you can't understand the query, return:
            {
                "error": "Specific error message explaining what's wrong"
            }
            """
        )
    
    async def process_price_query(self, input_text: str, chain_id: Optional[int] = None) -> Dict[str, Any]:
        """Process a price query and return structured data."""
        try:
            # Get raw response from LLM
            response = await super().process(input_text)
            if response["error"]:
                return response
            
            # Parse the JSON response
            try:
                data = json.loads(response["content"])
                if "error" in data:
                    return {
                        "content": None,
                        "error": data["error"],
                        "metadata": {}
                    }
                
                # Extract token
                token = data["token"].upper()
                
                # Look up token address
                token_address, token_symbol, token_name = await self.token_service.lookup_token(token, chain_id)
                if not token_symbol and not token_address:
                    error_msg = f"The token '{token}' is not recognized as a valid cryptocurrency."
                    return {
                        "content": None,
                        "error": error_msg,
                        "metadata": {}
                    }
                
                # Use canonical symbol if found
                if token_symbol:
                    token = token_symbol
                
                # Get token price
                try:
                    price, _ = await get_token_price(token, token_address, chain_id)
                    
                    # Format response message
                    message = f"The current price of {token} is ${price:.6f}"
                    
                    return {
                        "content": message,
                        "error": None,
                        "metadata": {
                            "token": token,
                            "price": price
                        }
                    }
                except Exception as e:
                    logger.error(f"Failed to get price for {token}: {e}")
                    return {
                        "content": None,
                        "error": f"Could not get the current price for {token}. Please try again later.",
                        "metadata": {}
                    }
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse LLM response: {e}")
                return {
                    "content": None,
                    "error": "Could not understand your price query. Please try rephrasing your request.",
                    "metadata": {}
                }
                
        except Exception as e:
            logger.error(f"Error processing price query: {e}", exc_info=True)
            return {
                "content": None,
                "error": f"An error occurred while processing your request: {str(e)}",
                "metadata": {}
            } 
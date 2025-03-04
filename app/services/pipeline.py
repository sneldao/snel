from typing import Optional, Dict, Any
import logging
from pydantic import BaseModel, Field
from app.services.token_service import TokenService
from app.agents.simple_swap_agent import SimpleSwapAgent
from app.agents.price_agent import PriceAgent

logger = logging.getLogger(__name__)

class Pipeline(BaseModel):
    """Pipeline for processing commands and queries."""
    token_service: TokenService
    swap_agent: SimpleSwapAgent
    price_agent: PriceAgent
    
    model_config = {
        "arbitrary_types_allowed": True
    }

    async def process(self, input_text: str, chain_id: Optional[int] = None) -> Dict[str, Any]:
        """Process input text and return appropriate response."""
        logger.info(f"Processing input: {input_text}")
        
        # Normalize input text
        normalized_text = input_text.lower().strip()
        
        # Check if this is a swap command
        is_swap_command = (
            normalized_text.startswith("swap") or
            ("swap" in normalized_text and any(token in normalized_text for token in ["eth", "usdc", "dai", "usdt", "$"])) or
            ("convert" in normalized_text and any(token in normalized_text for token in ["eth", "usdc", "dai", "usdt", "$"]))
        )
        
        # Check if this is a price query
        is_price_query = (
            "price" in normalized_text or 
            "how much" in normalized_text or
            "what is" in normalized_text and any(token in normalized_text for token in ["eth", "btc", "usdc", "dai", "usdt"])
        )
        
        # Try to process as a swap command first
        if is_swap_command:
            try:
                logger.info("Processing as swap command")
                result = await self.swap_agent.process_swap(input_text, chain_id)
                if not result.get("error"):
                    # Successfully processed as swap
                    return result
                else:
                    logger.warning(f"Swap processing failed: {result.get('error')}")
                    # Fall through to price query
            except Exception as e:
                logger.error(f"Error processing swap command: {e}")
                # Fall through to price query
        
        # Try to process as a price query
        if is_price_query:
            try:
                logger.info("Processing as price query")
                result = await self.price_agent.process_price_query(input_text, chain_id)
                if not result.get("error"):
                    # Successfully processed as price query
                    return result
                else:
                    logger.warning(f"Price query processing failed: {result.get('error')}")
                    # Fall through to general query
            except Exception as e:
                logger.error(f"Error processing price query: {e}")
                # Fall through to general query
        
        # If we get here, process as a general query
        logger.info("Processing as general query")
        try:
            from app.agents.base import AgentMessage
            result = await self.swap_agent.process(input_text)
            return result
        except Exception as e:
            logger.error(f"Error processing general query: {e}")
            return {
                "error": f"Failed to process input: {str(e)}",
                "metadata": {
                    "input": input_text,
                    "swap_error": is_swap_command,
                    "price_error": is_price_query
                }
            } 
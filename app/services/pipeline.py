from typing import Optional, Dict, Any
import logging
from pydantic import BaseModel, Field
from app.services.token_service import TokenService
from app.agents.simple_swap_agent import SimpleSwapAgent
from app.agents.price_agent import PriceAgent
from app.agents.dca_agent import DCAAgent
import re

logger = logging.getLogger(__name__)

class Pipeline(BaseModel):
    """Pipeline for processing commands and queries."""
    token_service: TokenService
    swap_agent: SimpleSwapAgent
    price_agent: PriceAgent
    dca_agent: Optional[DCAAgent] = None
    
    model_config = {
        "arbitrary_types_allowed": True
    }
    
    def __init__(self, **data):
        super().__init__(**data)
        # Initialize DCA agent if not provided
        if self.dca_agent is None:
            self.dca_agent = DCAAgent(token_service=self.token_service)

    async def process(self, input_text: str, chain_id: Optional[int] = None) -> Dict[str, Any]:
        """Process input text and return appropriate response."""
        logger.info(f"Processing input: {input_text}")
        
        # Normalize input text
        normalized_text = input_text.lower().strip()
        
        # Check if this is a DCA command
        is_dca_command = (
            normalized_text.startswith("dca ") or
            normalized_text.startswith("dollar cost average ") or
            # Add more variations
            re.search(r"\b(please|can you|can we|can i|could you|i want to|setup|set up)\s+dca\b", normalized_text) is not None or
            # Existing pattern
            ("dca" in normalized_text and any(token in normalized_text for token in ["eth", "usdc", "dai", "usdt", "$"])) or
            ("dollar cost average" in normalized_text)
        )
        
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
        
        # Try to process as a DCA command first
        if is_dca_command:
            try:
                logger.info("Processing as DCA command")
                result = await self.dca_agent.process_dca_command(input_text, chain_id)
                if not result.get("error"):
                    # Successfully processed as DCA
                    return {**result, "agent_type": "dca"}
                else:
                    logger.warning(f"DCA processing failed: {result.get('error')}")
                    # Fall through to other processing
            except Exception as e:
                logger.error(f"Error processing DCA command: {e}")
                # Fall through to other processing
        
        # Try to process as a swap command
        if is_swap_command:
            try:
                logger.info("Processing as swap command")
                result = await self.swap_agent.process_swap_command(input_text, chain_id)
                if not result.get("error"):
                    # Successfully processed as swap
                    return {**result, "agent_type": "swap"}
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
                    return {**result, "agent_type": "price"}
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
            return {**result, "agent_type": "default"}
        except Exception as e:
            logger.error(f"Error processing general query: {e}")
            return {
                "error": f"Failed to process input: {str(e)}",
                "metadata": {
                    "input": input_text,
                    "dca_error": is_dca_command,
                    "swap_error": is_swap_command,
                    "price_error": is_price_query
                },
                "agent_type": "default"
            } 
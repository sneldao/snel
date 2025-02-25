from typing import Optional, Dict, Any
import logging
from pydantic import BaseModel
from emp_agents import AgentBase
from emp_agents.providers import OpenAIProvider

logger = logging.getLogger(__name__)

class PointlessAgent(BaseModel):
    """Base class for Pointless agents."""
    provider: OpenAIProvider
    prompt: str
    
    async def process(self, input_text: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Process input text and return a response."""
        try:
            agent = AgentBase(
                prompt=self.prompt,
                provider=self.provider
            )
            
            response = await agent.answer(input_text)
            return {
                "content": response,
                "error": None,
                "metadata": metadata or {}
            }
        except Exception as e:
            logger.error(f"Error in agent processing: {e}", exc_info=True)
            return {
                "content": None,
                "error": str(e),
                "metadata": metadata or {}
            } 
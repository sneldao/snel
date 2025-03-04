from fastapi import Depends
from typing import Dict, Any, Optional, Type
import logging
import os

from app.agents.base import PointlessAgent
from app.agents.simple_swap_agent import SimpleSwapAgent
from app.agents.price_agent import PriceAgent
from app.services.token_service import TokenService
from app.services.redis_service import RedisService
from app.api.dependencies import get_redis_service
from app.prompts import SWAP_PROMPT, PRICE_PROMPT
from emp_agents.providers import OpenAIProvider

logger = logging.getLogger(__name__)

# Base prompt for general queries
BASE_PROMPT = """You are Snel, a friendly and helpful AI assistant focused on crypto and DeFi.
Your responses must be extremely concise and to the point - never more than 1-2 short sentences.
Avoid lengthy explanations or step-by-step instructions unless explicitly asked.
For complex topics, give the most important information first in a single sentence.
Never use markdown formatting unless specifically requested."""

class AgentFactory:
    """Factory for creating agent instances."""
    
    def __init__(self, token_service: TokenService, redis_service: RedisService):
        self.token_service = token_service
        self.redis_service = redis_service
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
    
    def create_agent(self, agent_type: str) -> PointlessAgent:
        """Create an agent of the specified type."""
        logger.info(f"Creating {agent_type} agent with openai provider")
        
        if agent_type == "swap":
            return SimpleSwapAgent()
        elif agent_type == "price":
            return PriceAgent(provider="openai")
        else:
            # Default agent
            return PointlessAgent(prompt="", model="gpt-4-turbo-preview")

    @staticmethod
    async def process_command(
        command: str,
        wallet_address: Optional[str] = None,
        chain_id: Optional[int] = None,
        creator_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        agent_type: str = "default",
        provider: str = "openai",
        api_key: Optional[str] = None,
        redis_service: Optional[RedisService] = None,
        token_service: Optional[TokenService] = None,
    ) -> Dict[str, Any]:
        """
        Process a command using the specified agent type.
        
        Args:
            command: Command to process
            wallet_address: Wallet address of the user
            chain_id: Chain ID to use for the agent
            creator_id: Creator ID of the user
            metadata: Additional metadata for the command
            agent_type: Type of agent to use
            provider: Provider to use
            api_key: API key for the provider
            redis_service: Redis service instance
            token_service: Token service instance
            
        Returns:
            Result of processing the command
        """
        # Create agent factory
        if not token_service:
            token_service = TokenService()
            
        # Create agent based on type
        agent = AgentFactory(token_service=token_service, redis_service=redis_service).create_agent(agent_type)
        
        # Process command based on agent type
        if agent_type == "swap":
            return await agent.process_swap_command(command, chain_id)
        elif agent_type == "price":
            return await agent.process_price_query(command, chain_id)
        else:
            return await agent.process(command, metadata)

def get_agent_factory(
    redis_service: RedisService = Depends(get_redis_service)
) -> AgentFactory:
    """Get an instance of AgentFactory."""
    token_service = TokenService()
    return AgentFactory(token_service=token_service, redis_service=redis_service) 
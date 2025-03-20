from typing import Optional, Dict, Any
import logging
from app.services.token_service import TokenService
from app.services.redis_service import RedisService
from app.agents.base import PointlessAgent
from app.agents.simple_swap_agent import SimpleSwapAgent
from app.agents.price_agent import PriceAgent
from app.agents.dca_agent import DCAAgent
from app.agents.brian_agent import BrianAgent
from app.services.swap_service import SwapService
from app.agents.messaging_agent import MessagingAgent

logger = logging.getLogger(__name__)

# Base prompt for general queries
BASE_PROMPT = """You are Snel, a friendly and helpful AI assistant focused on crypto and DeFi.
Your responses must be extremely concise and to the point - never more than 1-2 short sentences.
Avoid lengthy explanations or step-by-step instructions unless explicitly asked.
For complex topics, give the most important information first in a single sentence.
You're not pessimistic, just comically slow and relaxed about everything.
Occasionally make jokes about your slow pace as a snail, and how pointless it all is.
Never use markdown formatting unless specifically requested."""

# Price agent prompt
PRICE_AGENT_PROMPT = """You are a price checking assistant. Your responses should be concise and focused on price information.
When asked about prices, respond with the current price in a clear, simple format.
If you don't have price information, suggest checking a specific token or ask for clarification."""

class AgentFactory:
    """Factory for creating agent instances."""
    
    def __init__(self, token_service: TokenService, redis_service: RedisService):
        self.token_service = token_service
        self.redis_service = redis_service
        logger.info("AgentFactory initialized")
    
    def create_agent(self, agent_type: str, api_key: Optional[str] = None) -> PointlessAgent:
        """Create an agent of the specified type."""
        logger.info(f"Creating {agent_type} agent with API key: {'provided' if api_key else 'not provided'}")

        if agent_type == "brian":
            # Create a Brian agent for token transfers, bridging, and balance checking
            return BrianAgent(
                token_service=self.token_service,
                api_key=api_key
            )
        elif agent_type == "dca":
            return DCAAgent(
                token_service=self.token_service,
                redis_service=self.redis_service,
                api_key=api_key
            )
        elif agent_type == "messaging":
            # For messaging agent, we need to create a swap service
            swap_agent = SimpleSwapAgent(api_key=api_key)
            swap_service = SwapService(token_service=self.token_service, swap_agent=swap_agent)

            return MessagingAgent(
                token_service=self.token_service,
                swap_service=swap_service,
                api_key=api_key
            )
        elif agent_type == "price":
            # Create price agent with API key
            return PriceAgent(api_key=api_key)
        elif agent_type == "swap":
            return SimpleSwapAgent(api_key=api_key)
        else:
            # Default agent
            return PointlessAgent(prompt=BASE_PROMPT, model="gpt-4-turbo-preview", api_key=api_key)

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
        """Process a command using the specified agent type."""
        # Create token service if not provided
        if not token_service:
            token_service = TokenService()

        # Create agent factory
        factory = AgentFactory(token_service=token_service, redis_service=redis_service)

        # Create agent based on type
        agent = factory.create_agent(agent_type, api_key)

        # Process command based on agent type
        if agent_type == "dca":
            return await agent.process_dca_command(
                command, 
                chain_id=chain_id,
                wallet_address=wallet_address
            )
        elif agent_type == "price":
            return await agent.process_price_query(command, chain_id)
        elif agent_type == "swap":
            return await agent.process_swap_command(command, chain_id)
        else:
            return await agent.process(command, metadata)

def get_agent_factory():
    """Dependency injection for AgentFactory."""
    return AgentFactory(token_service=None, redis_service=None)

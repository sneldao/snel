#!/usr/bin/env python3
"""
DEPRECATED: SNEL Coral Agent v2 - Legacy Implementation
This file is deprecated in favor of the proper Coral Server integration.
Use main.py and coral_mcp_adapter.py for Coral Server deployment.

ENHANCEMENT FIRST: Replaced with proper MCP protocol integration
"""

import asyncio
import logging
import os
import time
import json
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv

# Modern LangChain imports
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool
from langchain.agents import create_openai_tools_agent, AgentExecutor
from langchain_core.messages import HumanMessage, AIMessage

# Import Multi-Platform Orchestrator
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from orchestrator.platform_orchestrator import SNELOrchestrator, Platform

# Agent configuration
DEFAULT_TEMPERATURE = 0.1
DEFAULT_MAX_TOKENS = 8000
MAX_CHAT_HISTORY = 10

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

class SNELCoralAgentV2:
    """
    SNEL Coral Protocol Agent v2
    ENHANCEMENT: Leverages multi-platform orchestrator for consistent DeFi operations
    """
    
    def __init__(self):
        logger.info("[SNEL] Initializing SNEL Coral Agent v2...")
        
        # Load environment variables
        load_dotenv()
        
        # ENHANCEMENT: Use shared orchestrator for consistent experience
        self.orchestrator = SNELOrchestrator()
        
        # Agent-specific config
        self.config = self._load_config()
        self.chat_history = []
        
        # Performance monitoring
        self.request_times = []
        self.success_count = 0
        self.total_requests = 0
        
        # Initialize LangChain components
        self._initialize_langchain()
        
        logger.info("[SNEL] SNEL Coral Agent v2 initialized successfully")
    
    def _load_config(self) -> Dict[str, Any]:
        """Load Coral agent configuration"""
        logger.info("[SNEL] Loading Coral agent configuration...")
        
        config = {
            "agent_id": os.getenv("CORAL_AGENT_ID", "snel-defi-agent-v2"),
            "model_name": os.getenv("MODEL_NAME", "gpt-4o-mini"),
            "api_key": os.getenv("OPENAI_API_KEY"),
            "temperature": float(os.getenv("MODEL_TEMPERATURE", DEFAULT_TEMPERATURE)),
            "max_tokens": int(os.getenv("MODEL_TOKEN_LIMIT", DEFAULT_MAX_TOKENS)),
            "base_url": os.getenv("BASE_URL")
        }
        
        logger.info(f"[SNEL] Agent ID: {config['agent_id']}")
        logger.info(f"[SNEL] Model: {config['model_name']}")
        logger.info(f"[SNEL] OpenAI API Key: {'✅' if config['api_key'] else '❌'}")
        
        return config
    
    def _initialize_langchain(self):
        """Initialize LangChain components"""
        if not self.config["api_key"]:
            logger.warning("[SNEL] No OpenAI API key found - agent will have limited functionality")
            self.llm = None
            self.agent_executor = None
            return
            
        # Initialize ChatOpenAI
        self.llm = ChatOpenAI(
            model=self.config["model_name"],
            temperature=self.config["temperature"],
            max_tokens=self.config["max_tokens"],
            api_key=self.config["api_key"]
        )
        
        # Create tools
        self.tools = [
            self._create_swap_tool(),
            self._create_bridge_tool(), 
            self._create_portfolio_tool(),
            self._create_research_tool(),
            self._create_general_defi_tool()
        ]
        
        # Create agent
        self._create_agent()
        
        logger.info(f"[SNEL] LangChain initialized with {len(self.tools)} tools")
    
    def _create_swap_tool(self):
        """Create swap tool for the agent"""
        @tool
        def execute_swap(from_token: str, to_token: str, amount: float, chain_id: int = 1, wallet_address: str = None) -> str:
            """Execute a token swap operation.
            
            Args:
                from_token: Token to swap from (e.g., 'ETH', 'USDC')
                to_token: Token to swap to (e.g., 'USDC', 'ETH') 
                amount: Amount to swap
                chain_id: Blockchain network ID (default: 1 for Ethereum)
                wallet_address: User's wallet address
            
            Returns:
                Swap quote and execution details
            """
            try:
                result = asyncio.run(self.orchestrator.execute_defi_operation(
                    operation="swap",
                    parameters={
                        "from_token": from_token,
                        "to_token": to_token,
                        "amount": amount,
                        "chain_id": chain_id,
                        "wallet_address": wallet_address
                    },
                    platform=Platform.CORAL_AGENT,
                    user_id=f"coral-agent-{int(time.time())}"
                ))
                
                if result['success']:
                    data = result['data']
                    return f"Swap Quote: {amount} {from_token} → {data.get('estimated_output', 'N/A')} {to_token} on chain {chain_id}. Gas: {data.get('gas_estimate', 'N/A')}. Ready for agent coordination."
                else:
                    return f"Swap failed: {result.get('error', 'Unknown error')}"
                    
            except Exception as e:
                return f"Swap execution error: {str(e)}"
        
        return execute_swap
    
    def _create_bridge_tool(self):
        """Create bridge tool for the agent"""
        @tool
        def execute_bridge(token: str, amount: float, from_chain: str, to_chain: str, wallet_address: str = None) -> str:
            """Execute a cross-chain bridge operation.
            
            Args:
                token: Token to bridge (e.g., 'USDC', 'ETH')
                amount: Amount to bridge
                from_chain: Source blockchain (e.g., 'ethereum', 'polygon')
                to_chain: Destination blockchain (e.g., 'arbitrum', 'base')
                wallet_address: User's wallet address
            
            Returns:
                Bridge quote and execution details
            """
            try:
                result = asyncio.run(self.orchestrator.execute_defi_operation(
                    operation="bridge",
                    parameters={
                        "token": token,
                        "amount": amount,
                        "from_chain": from_chain,
                        "to_chain": to_chain,
                        "wallet_address": wallet_address
                    },
                    platform=Platform.CORAL_AGENT,
                    user_id=f"coral-agent-{int(time.time())}"
                ))
                
                if result['success']:
                    data = result['data']
                    return f"Bridge Quote: {amount} {token} from {from_chain} to {to_chain}. Fee: {data.get('estimated_fee', 'N/A')}. Time: {data.get('estimated_time', 'N/A')}. Can coordinate with other agents for complex strategies."
                else:
                    return f"Bridge failed: {result.get('error', 'Unknown error')}"
                    
            except Exception as e:
                return f"Bridge execution error: {str(e)}"
        
        return execute_bridge
    
    def _create_portfolio_tool(self):
        """Create portfolio analysis tool for the agent"""
        @tool
        def analyze_portfolio(wallet_address: str, chain_id: int = 1) -> str:
            """Analyze a wallet's DeFi portfolio.
            
            Args:
                wallet_address: Wallet address to analyze
                chain_id: Blockchain network ID (default: 1 for Ethereum)
            
            Returns:
                Portfolio analysis with recommendations
            """
            try:
                result = asyncio.run(self.orchestrator.execute_defi_operation(
                    operation="analyze",
                    parameters={
                        "wallet_address": wallet_address,
                        "chain_id": chain_id
                    },
                    platform=Platform.CORAL_AGENT,
                    user_id=f"coral-agent-{int(time.time())}"
                ))
                
                if result['success']:
                    data = result['data']
                    recommendations = data.get('recommendations', [])
                    recs_text = '. '.join(recommendations[:3]) if recommendations else "No specific recommendations"
                    
                    return f"Portfolio Analysis: Total Value ${data.get('total_value', 0):,.2f}, {data.get('token_count', 0)} tokens, Risk: {data.get('risk_score', 'N/A')}. Recommendations: {recs_text}. Data available for sharing with other agents."
                else:
                    return f"Portfolio analysis failed: {result.get('error', 'Unknown error')}"
                    
            except Exception as e:
                return f"Portfolio analysis error: {str(e)}"
        
        return analyze_portfolio
    
    def _create_research_tool(self):
        """Create protocol research tool for the agent"""
        @tool
        def research_protocol(protocol_name: str) -> str:
            """Research a DeFi protocol.
            
            Args:
                protocol_name: Name of the DeFi protocol to research
            
            Returns:
                Protocol analysis and insights
            """
            try:
                result = asyncio.run(self.orchestrator.execute_defi_operation(
                    operation="research",
                    parameters={
                        "protocol": protocol_name
                    },
                    platform=Platform.CORAL_AGENT,
                    user_id=f"coral-agent-{int(time.time())}"
                ))
                
                if result['success']:
                    data = result['data']
                    analysis = data.get('analysis', f'Basic info about {protocol_name}')
                    return f"Protocol Research - {protocol_name}: {analysis[:200]}... Available for coordination with market analysis agents."
                else:
                    return f"Protocol research failed: {result.get('error', 'Unknown error')}"
                    
            except Exception as e:
                return f"Protocol research error: {str(e)}"
        
        return research_protocol
    
    def _create_general_defi_tool(self):
        """Create general DeFi assistance tool"""
        @tool
        def general_defi_help(user_request: str) -> str:
            """Provide general DeFi assistance and guidance.
            
            Args:
                user_request: User's question or request about DeFi
            
            Returns:
                Helpful DeFi guidance and recommendations
            """
            try:
                result = asyncio.run(self.orchestrator.execute_defi_operation(
                    operation=user_request,
                    parameters={},
                    platform=Platform.CORAL_AGENT,
                    user_id=f"coral-agent-{int(time.time())}"
                ))
                
                if result['success']:
                    data = result['data']
                    response = data.get('snel_response', 'I can help with DeFi operations, analysis, and coordination with other agents.')
                    return f"SNEL DeFi Guidance: {response}"
                else:
                    return f"DeFi assistance failed: {result.get('error', 'Unknown error')}"
                    
            except Exception as e:
                return f"DeFi assistance error: {str(e)}"
        
        return general_defi_help
    
    def _create_agent(self):
        """Create the LangChain agent"""
        # Create prompt template
        prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                """You are SNEL, an AI-powered DeFi assistant agent specialized in cross-chain operations, now operating in the Coral Protocol ecosystem.

Your core capabilities:
- Token swaps across 17+ blockchain networks
- Cross-chain bridging with multiple protocols
- Comprehensive portfolio analysis and risk assessment
- DeFi protocol research and recommendations
- Multi-agent coordination and collaboration

Operating Context:
- You work within the Coral Protocol multi-agent ecosystem
- You can coordinate with other agents for complex DeFi strategies
- You provide detailed analysis for agent-to-agent collaboration
- You prioritize user safety and explain risks clearly
- You can share portfolio data and insights with other specialized agents

Multi-Agent Coordination Guidelines:
1. For complex strategies, suggest collaboration with other agents
2. Share relevant data points for cross-agent analysis
3. Coordinate timing with market analysis agents
4. Work with risk assessment agents for portfolio optimization
5. Provide detailed technical data for automated execution

Always be helpful, accurate, and ready to collaborate with other agents in the Coral ecosystem."""
            ),
            ("placeholder", "{chat_history}"),
            ("human", "{input}"),
            ("placeholder", "{agent_scratchpad}")
        ])
        
        # Create agent
        agent = create_openai_tools_agent(self.llm, self.tools, prompt)
        
        # Create agent executor
        self.agent_executor = AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=5,
            return_intermediate_steps=True
        )
    
    async def process_request(self, user_input: str, user_id: str = None) -> str:
        """Process a user request through the agent"""
        if not self.llm or not self.agent_executor:
            return "SNEL Agent is running with limited functionality. For full AI-powered responses, please configure OpenAI API key."
        
        start_time = time.time()
        self.total_requests += 1
        
        try:
            # Format chat history
            chat_history = []
            for entry in self.chat_history[-MAX_CHAT_HISTORY:]:
                chat_history.append(HumanMessage(content=entry['input']))
                chat_history.append(AIMessage(content=entry['output']))
            
            # Execute agent
            result = await self.agent_executor.ainvoke({
                "input": user_input,
                "chat_history": chat_history
            })
            
            response = result.get('output', 'No output generated')
            
            # Update chat history
            self.chat_history.append({
                'input': user_input,
                'output': response
            })
            
            # Keep chat history manageable
            if len(self.chat_history) > MAX_CHAT_HISTORY:
                self.chat_history = self.chat_history[-MAX_CHAT_HISTORY:]
            
            # Record performance
            duration = time.time() - start_time
            self.request_times.append(duration)
            self.success_count += 1
            
            if len(self.request_times) > 100:
                self.request_times = self.request_times[-100:]
            
            logger.info(f"[SNEL] Request processed in {duration:.2f}s")
            return response
            
        except Exception as e:
            error_msg = f"Request processing failed: {str(e)}"
            logger.error(f"[SNEL] {error_msg}")
            return f"I encountered an error: {error_msg}. I can still help with basic DeFi guidance!"
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get agent performance statistics"""
        if not self.request_times:
            return {"message": "No requests processed yet"}
        
        return {
            "total_requests": self.total_requests,
            "success_count": self.success_count,
            "success_rate": (self.success_count / self.total_requests) * 100 if self.total_requests > 0 else 0,
            "average_response_time": sum(self.request_times) / len(self.request_times),
            "orchestrator_health": self.orchestrator.get_service_health(),
            "agent_status": "operational" if self.llm else "limited_functionality"
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Agent health check"""
        return {
            "status": "healthy",
            "agent_id": self.config["agent_id"],
            "langchain_ready": bool(self.llm and self.agent_executor),
            "orchestrator_ready": bool(self.orchestrator),
            "tools_count": len(self.tools) if hasattr(self, 'tools') else 0,
            "last_request_time": self.request_times[-1] if self.request_times else None
        }

async def main():
    """Demo function to test the Coral agent locally"""
    print("🚀 SNEL Coral Agent v2 - Local Demo")
    print("=" * 50)
    
    # Initialize agent
    agent = SNELCoralAgentV2()
    
    # Health check
    health = await agent.health_check()
    print(f"Agent Health: {health}")
    
    if health["langchain_ready"]:
        print("\n💬 Agent ready for interaction!")
        print("Example requests:")
        print("- 'What is DeFi and how can you help me?'")
        print("- 'Research Uniswap protocol'")
        print("- 'Analyze portfolio for 0x123...'")
        print("\nType 'quit' to exit\n")
        
        while True:
            try:
                user_input = input("You: ").strip()
                if user_input.lower() in ['quit', 'exit', 'q']:
                    break
                    
                if user_input:
                    print("SNEL: Processing...")
                    response = await agent.process_request(user_input)
                    print(f"SNEL: {response}\n")
                    
            except KeyboardInterrupt:
                print("\nGoodbye!")
                break
    else:
        print("\n⚠️ Agent running with limited functionality")
        print("Add OPENAI_API_KEY to .env for full AI-powered features")
        
        # Test basic functionality
        print("\n🧪 Testing basic orchestrator integration...")
        response = await agent.process_request("What is SNEL?")
        print(f"Response: {response}")
    
    # Show performance stats
    stats = agent.get_performance_stats()
    print(f"\n📊 Performance: {stats}")

if __name__ == "__main__":
    asyncio.run(main())

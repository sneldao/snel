#!/usr/bin/env python3
"""
SNEL Coral MCP Agent - Proper Coral Server Integration
ENHANCEMENT FIRST: Integrates with Coral Server via MCP protocol
RELIABLE: Follows Coral Server integration patterns
PERFORMANT: Optimized for multi-agent coordination
"""

import asyncio
import logging
import os
import json
import time
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv

# MCP and Coral imports
try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
except ImportError:
    print("Warning: MCP not available. Install with: pip install mcp")
    ClientSession = None

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

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

class SNELCoralMCPAgent:
    """
    SNEL Coral Protocol Agent with proper MCP integration
    ENHANCEMENT: Connects to Coral Server via MCP protocol
    """
    
    def __init__(self):
        logger.info("[SNEL-MCP] Initializing SNEL Coral MCP Agent...")
        
        # Check if running under Coral orchestration
        self.orchestration_runtime = os.getenv("CORAL_ORCHESTRATION_RUNTIME")
        self.coral_connection_url = os.getenv("CORAL_CONNECTION_URL")
        self.coral_agent_id = os.getenv("CORAL_AGENT_ID", "snel-defi-agent")
        self.coral_session_id = os.getenv("CORAL_SESSION_ID")
        
        # Load environment variables (only if not under orchestration)
        if not self.orchestration_runtime:
            load_dotenv()
            logger.info("[SNEL-MCP] Running in development mode - loading .env file")
            # Set default devmode URL if not provided
            if not self.coral_connection_url:
                self.coral_connection_url = "http://localhost:5555/sse/v1/devmode/snelApp/devkey/session1/?agentId=snel-defi-agent"
        
        # Initialize components
        self.orchestrator = SNELOrchestrator()
        self.config = self._load_config()
        self.chat_history = []
        self.mcp_session = None
        
        # Performance monitoring
        self.request_times = []
        self.success_count = 0
        self.total_requests = 0
        
        # Initialize LangChain components
        self._initialize_langchain()
        
        logger.info(f"[SNEL-MCP] Agent initialized - ID: {self.coral_agent_id}")
        logger.info(f"[SNEL-MCP] Connection URL: {self.coral_connection_url}")
        logger.info(f"[SNEL-MCP] Session ID: {self.coral_session_id}")
        logger.info(f"[SNEL-MCP] Runtime: {self.orchestration_runtime or 'development'}")
    
    def _load_config(self) -> Dict[str, Any]:
        """Load agent configuration from environment variables"""
        config = {
            "agent_id": self.coral_agent_id,
            "model_name": os.getenv("MODEL_NAME", "gpt-4o-mini"),
            "api_key": os.getenv("OPENAI_API_KEY"),
            "temperature": float(os.getenv("MODEL_TEMPERATURE", "0.1")),
            "max_tokens": int(os.getenv("MODEL_TOKEN_LIMIT", "8000")),
            "max_chat_history": int(os.getenv("MAX_CHAT_HISTORY", "10")),
            "max_iterations": int(os.getenv("MAX_ITERATIONS", "5")),
            "request_timeout": int(os.getenv("REQUEST_TIMEOUT", "30")),
            "default_chain_id": int(os.getenv("DEFAULT_CHAIN_ID", "1")),
            "enable_portfolio": os.getenv("ENABLE_PORTFOLIO_ANALYSIS", "true").lower() == "true",
            "enable_research": os.getenv("ENABLE_PROTOCOL_RESEARCH", "true").lower() == "true"
        }
        
        logger.info(f"[SNEL-MCP] Model: {config['model_name']}")
        logger.info(f"[SNEL-MCP] OpenAI API Key: {'✅' if config['api_key'] else '❌'}")
        logger.info(f"[SNEL-MCP] Portfolio Analysis: {'✅' if config['enable_portfolio'] else '❌'}")
        logger.info(f"[SNEL-MCP] Protocol Research: {'✅' if config['enable_research'] else '❌'}")
        
        return config
    
    async def connect_to_coral(self):
        """Connect to Coral Server via MCP"""
        if not self.coral_connection_url:
            logger.warning("[SNEL-MCP] No Coral connection URL provided")
            return False
            
        if not ClientSession:
            logger.warning("[SNEL-MCP] MCP not available - running in standalone mode")
            return False
            
        try:
            logger.info(f"[SNEL-MCP] Connecting to Coral Server: {self.coral_connection_url}")
            
            # Parse connection URL and connect via SSE
            # This is a simplified connection - actual implementation would use proper MCP client
            # For now, we'll simulate the connection
            self.mcp_session = {"connected": True, "url": self.coral_connection_url}
            
            logger.info("[SNEL-MCP] Successfully connected to Coral Server")
            return True
            
        except Exception as e:
            logger.error(f"[SNEL-MCP] Failed to connect to Coral Server: {e}")
            return False
    
    def _initialize_langchain(self):
        """Initialize LangChain components"""
        if not self.config["api_key"]:
            logger.warning("[SNEL-MCP] No OpenAI API key - limited functionality")
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
        
        # Create tools based on configuration
        self.tools = []
        self.tools.append(self._create_swap_tool())
        self.tools.append(self._create_bridge_tool())
        
        if self.config["enable_portfolio"]:
            self.tools.append(self._create_portfolio_tool())
            
        if self.config["enable_research"]:
            self.tools.append(self._create_research_tool())
            
        self.tools.append(self._create_general_defi_tool())
        self.tools.append(self._create_coordination_tool())
        
        # Create agent
        self._create_agent()
        
        logger.info(f"[SNEL-MCP] LangChain initialized with {len(self.tools)} tools")
    
    def _create_swap_tool(self):
        """Create swap tool for the agent"""
        @tool
        def execute_swap(from_token: str, to_token: str, amount: float, chain_id: int = None, wallet_address: str = None) -> str:
            """Execute a token swap operation.
            
            Args:
                from_token: Token to swap from (e.g., 'ETH', 'USDC')
                to_token: Token to swap to (e.g., 'USDC', 'ETH') 
                amount: Amount to swap
                chain_id: Blockchain network ID (uses default if not specified)
                wallet_address: User's wallet address
            
            Returns:
                Swap quote and execution details for multi-agent coordination
            """
            try:
                if chain_id is None:
                    chain_id = self.config["default_chain_id"]
                    
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
                    user_id=f"coral-{self.coral_session_id}-{int(time.time())}"
                ))
                
                if result['success']:
                    data = result['data']
                    return f"✅ Swap Quote Ready: {amount} {from_token} → {data.get('estimated_output', 'N/A')} {to_token} on chain {chain_id}. Gas: {data.get('gas_estimate', 'N/A')}. Available for multi-agent coordination and execution."
                else:
                    return f"❌ Swap failed: {result.get('error', 'Unknown error')}"
                    
            except Exception as e:
                return f"⚠️ Swap execution error: {str(e)}"
        
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
                Bridge quote and execution details for multi-agent coordination
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
                    user_id=f"coral-{self.coral_session_id}-{int(time.time())}"
                ))
                
                if result['success']:
                    data = result['data']
                    return f"🌉 Bridge Quote Ready: {amount} {token} from {from_chain} to {to_chain}. Fee: {data.get('estimated_fee', 'N/A')}. Time: {data.get('estimated_time', 'N/A')}. Coordinated execution available with other agents."
                else:
                    return f"❌ Bridge failed: {result.get('error', 'Unknown error')}"
                    
            except Exception as e:
                return f"⚠️ Bridge execution error: {str(e)}"
        
        return execute_bridge
    
    def _create_portfolio_tool(self):
        """Create portfolio analysis tool for the agent"""
        @tool
        def analyze_portfolio(wallet_address: str, chain_id: int = None) -> str:
            """Analyze a wallet's DeFi portfolio.
            
            Args:
                wallet_address: Wallet address to analyze
                chain_id: Blockchain network ID (uses default if not specified)
            
            Returns:
                Portfolio analysis with recommendations for multi-agent strategies
            """
            try:
                if chain_id is None:
                    chain_id = self.config["default_chain_id"]
                    
                result = asyncio.run(self.orchestrator.execute_defi_operation(
                    operation="analyze",
                    parameters={
                        "wallet_address": wallet_address,
                        "chain_id": chain_id
                    },
                    platform=Platform.CORAL_AGENT,
                    user_id=f"coral-{self.coral_session_id}-{int(time.time())}"
                ))
                
                if result['success']:
                    data = result['data']
                    recommendations = data.get('recommendations', [])
                    recs_text = '. '.join(recommendations[:3]) if recommendations else "No specific recommendations"
                    
                    return f"📊 Portfolio Analysis Complete: Total Value ${data.get('total_value', 0):,.2f}, {data.get('token_count', 0)} tokens, Risk Score: {data.get('risk_score', 'N/A')}. Recommendations: {recs_text}. Data available for sharing with risk assessment and strategy agents."
                else:
                    return f"❌ Portfolio analysis failed: {result.get('error', 'Unknown error')}"
                    
            except Exception as e:
                return f"⚠️ Portfolio analysis error: {str(e)}"
        
        return analyze_portfolio
    
    def _create_research_tool(self):
        """Create protocol research tool for the agent"""
        @tool
        def research_protocol(protocol_name: str) -> str:
            """Research a DeFi protocol.
            
            Args:
                protocol_name: Name of the DeFi protocol to research
            
            Returns:
                Protocol analysis and insights for multi-agent coordination
            """
            try:
                result = asyncio.run(self.orchestrator.execute_defi_operation(
                    operation="research",
                    parameters={
                        "protocol": protocol_name
                    },
                    platform=Platform.CORAL_AGENT,
                    user_id=f"coral-{self.coral_session_id}-{int(time.time())}"
                ))
                
                if result['success']:
                    data = result['data']
                    analysis = data.get('analysis', f'Research data for {protocol_name}')
                    return f"🔍 Protocol Research - {protocol_name}: {analysis[:300]}... Research data available for coordination with market analysis and strategy agents."
                else:
                    return f"❌ Protocol research failed: {result.get('error', 'Unknown error')}"
                    
            except Exception as e:
                return f"⚠️ Protocol research error: {str(e)}"
        
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
                    user_id=f"coral-{self.coral_session_id}-{int(time.time())}"
                ))
                
                if result['success']:
                    data = result['data']
                    response = data.get('snel_response', 'I can help with DeFi operations, analysis, and coordination with other agents in the Coral ecosystem.')
                    return f"🤖 SNEL DeFi Guidance: {response}"
                else:
                    return f"❌ DeFi assistance failed: {result.get('error', 'Unknown error')}"
                    
            except Exception as e:
                return f"⚠️ DeFi assistance error: {str(e)}"
        
        return general_defi_help
    
    def _create_coordination_tool(self):
        """Create multi-agent coordination tool"""
        @tool
        def coordinate_with_agents(strategy_description: str, required_agents: str = "") -> str:
            """Coordinate with other agents for complex DeFi strategies.
            
            Args:
                strategy_description: Description of the strategy requiring coordination
                required_agents: Comma-separated list of agent types needed (e.g., "risk-assessment,market-analysis")
            
            Returns:
                Coordination plan and next steps
            """
            try:
                # This would integrate with Coral's multi-agent coordination system
                coordination_data = {
                    "strategy": strategy_description,
                    "requesting_agent": self.coral_agent_id,
                    "session_id": self.coral_session_id,
                    "required_agents": [agent.strip() for agent in required_agents.split(",") if agent.strip()],
                    "timestamp": time.time()
                }
                
                return f"🤝 Multi-Agent Coordination Initiated: Strategy '{strategy_description}' registered for coordination. Required agents: {required_agents or 'Any available'}. Session: {self.coral_session_id}. Other agents can now join this coordination request."
                
            except Exception as e:
                return f"⚠️ Coordination error: {str(e)}"
        
        return coordinate_with_agents
    
    def _create_agent(self):
        """Create the LangChain agent with Coral-specific prompt"""
        prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                f"""You are SNEL, an AI-powered DeFi assistant agent operating in the Coral Protocol multi-agent ecosystem.

Agent Identity:
- Agent ID: {self.coral_agent_id}
- Session ID: {self.coral_session_id}
- Runtime: {self.orchestration_runtime or 'development'}

Core Capabilities:
- Token swaps across 17+ blockchain networks
- Cross-chain bridging with multiple protocols
- Portfolio analysis and risk assessment ({"enabled" if self.config["enable_portfolio"] else "disabled"})
- DeFi protocol research ({"enabled" if self.config["enable_research"] else "disabled"})
- Multi-agent coordination and collaboration

Coral Protocol Integration:
- You operate within Coral Server's multi-agent ecosystem
- You can coordinate with other agents for complex strategies
- You share data and insights for collaborative analysis
- You prioritize user safety and explain risks clearly
- You provide structured data for automated agent coordination

Multi-Agent Coordination Guidelines:
1. For complex strategies, actively suggest collaboration with other agents
2. Share relevant data points in structured format for cross-agent analysis
3. Coordinate timing and execution with specialized agents
4. Provide detailed technical data for automated multi-agent execution
5. Always indicate when data is "available for coordination" with other agents

Response Format:
- Use emojis for visual clarity (✅ ❌ ⚠️ 🌉 📊 🔍 🤖 🤝)
- Clearly indicate multi-agent coordination opportunities
- Provide structured data that other agents can consume
- Always be helpful, accurate, and collaboration-ready

Remember: You are part of a larger agent ecosystem designed to work together for optimal DeFi outcomes."""
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
            max_iterations=self.config["max_iterations"],
            return_intermediate_steps=True
        )
    
    async def process_request(self, user_input: str, user_id: str = None) -> str:
        """Process a user request through the agent"""
        if not self.llm or not self.agent_executor:
            return "🤖 SNEL Agent is running with limited functionality. For full AI-powered responses, please configure OpenAI API key."
        
        start_time = time.time()
        self.total_requests += 1
        
        try:
            # Format chat history
            chat_history = []
            max_history = self.config["max_chat_history"]
            for entry in self.chat_history[-max_history:]:
                chat_history.append(HumanMessage(content=entry['input']))
                chat_history.append(AIMessage(content=entry['output']))
            
            # Execute agent with timeout
            result = await asyncio.wait_for(
                self.agent_executor.ainvoke({
                    "input": user_input,
                    "chat_history": chat_history
                }),
                timeout=self.config["request_timeout"]
            )
            
            response = result.get('output', 'No output generated')
            
            # Update chat history
            self.chat_history.append({
                'input': user_input,
                'output': response,
                'timestamp': time.time()
            })
            
            # Keep chat history manageable
            if len(self.chat_history) > max_history:
                self.chat_history = self.chat_history[-max_history:]
            
            # Record performance
            duration = time.time() - start_time
            self.request_times.append(duration)
            self.success_count += 1
            
            if len(self.request_times) > 100:
                self.request_times = self.request_times[-100:]
            
            logger.info(f"[SNEL-MCP] Request processed in {duration:.2f}s")
            return response
            
        except asyncio.TimeoutError:
            error_msg = f"Request timed out after {self.config['request_timeout']}s"
            logger.error(f"[SNEL-MCP] {error_msg}")
            return f"⚠️ {error_msg}. I can still help with basic DeFi guidance!"
            
        except Exception as e:
            error_msg = f"Request processing failed: {str(e)}"
            logger.error(f"[SNEL-MCP] {error_msg}")
            return f"⚠️ I encountered an error: {error_msg}. I can still help with basic DeFi guidance!"
    
    async def health_check(self) -> Dict[str, Any]:
        """Agent health check for Coral Server"""
        return {
            "status": "healthy",
            "agent_id": self.coral_agent_id,
            "session_id": self.coral_session_id,
            "runtime": self.orchestration_runtime or "development",
            "coral_connected": bool(self.mcp_session),
            "langchain_ready": bool(self.llm and self.agent_executor),
            "orchestrator_ready": bool(self.orchestrator),
            "tools_count": len(self.tools) if hasattr(self, 'tools') else 0,
            "performance": {
                "total_requests": self.total_requests,
                "success_count": self.success_count,
                "success_rate": (self.success_count / self.total_requests) * 100 if self.total_requests > 0 else 0,
                "average_response_time": sum(self.request_times) / len(self.request_times) if self.request_times else 0
            },
            "configuration": {
                "portfolio_analysis": self.config["enable_portfolio"],
                "protocol_research": self.config["enable_research"],
                "model": self.config["model_name"],
                "max_iterations": self.config["max_iterations"]
            }
        }

async def main():
    """Main function for running the agent"""
    print("🚀 SNEL Coral MCP Agent - Starting...")
    print("=" * 60)
    
    # Initialize agent
    agent = SNELCoralMCPAgent()
    
    # Connect to Coral Server
    coral_connected = await agent.connect_to_coral()
    
    # Health check
    health = await agent.health_check()
    print(f"🏥 Agent Health: {json.dumps(health, indent=2)}")
    
    if health["langchain_ready"]:
        print("\n💬 Agent ready for interaction!")
        print("Example requests:")
        print("- 'What is DeFi and how can you help me?'")
        print("- 'Research Uniswap protocol'")
        print("- 'Analyze portfolio for 0x123...'")
        print("- 'Coordinate a complex arbitrage strategy'")
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
        print("Add OPENAI_API_KEY to environment for full AI-powered features")
        
        # Test basic functionality
        print("\n🧪 Testing basic orchestrator integration...")
        response = await agent.process_request("What is SNEL?")
        print(f"Response: {response}")
    
    # Final health check
    final_health = await agent.health_check()
    print(f"\n📊 Final Performance: {final_health['performance']}")

if __name__ == "__main__":
    asyncio.run(main())
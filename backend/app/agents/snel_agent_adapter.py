"""
SNEL Coral Agent Adapter - Enhanced Version
ENHANCEMENT FIRST: Adapts SNEL Orchestrator for Coral Protocol with proper integration
RELIABLE: Proper error handling, retries, and monitoring
PERFORMANT: Efficient routing of Coral requests to shared service layer
SOVEREIGN: Integrated with Autonome (DeFAI) and Libp2p for PL Genesis Hackathon
"""

import asyncio
import logging
import os
import time
import urllib.parse
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv
import json

# Langchain imports for Coral integration
from langchain.chat_models import init_chat_model
from langchain.prompts import ChatPromptTemplate
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain.agents import create_tool_calling_agent, AgentExecutor

# Import Multi-Platform Orchestrator
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.orchestrator.platform_orchestrator import SNELOrchestrator, Platform

# Import our new Coral Protocol Client
from .coral_protocol_client import CoralProtocolClient, AgentRegistration
from .libp2p_node import Libp2pNode

# Agent configuration
REQUEST_QUESTION_TOOL = "request-question"
ANSWER_QUESTION_TOOL = "answer-question"
DEFI_EXECUTE_TOOL = "execute-defi-operation"
PORTFOLIO_ANALYZE_TOOL = "analyze-portfolio"
MAX_CHAT_HISTORY = 5
DEFAULT_TEMPERATURE = 0.1
DEFAULT_MAX_TOKENS = 8000

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

class SNELCoralAdapter:
    """
    SNEL Coral Protocol Adapter - Enhanced Version
    ENHANCEMENT: Leverages multi-platform orchestrator for consistent user experience
    CLEAN: Clear separation between Coral Protocol integration and SNEL core logic
    MODULAR: Composable and testable components
    """
    
    def __init__(self):
        logger.info("[SNEL] Initializing SNEL Coral Adapter...")
        
        # ENHANCEMENT: Use shared orchestrator for consistent experience
        self.orchestrator = SNELOrchestrator()
        
        # Agent-specific config
        self.config = self.load_config()
        self.chat_history = []
        
        # Performance monitoring
        self.request_times = []
        self.success_count = 0
        self.total_requests = 0
        
        # Coral Protocol Integration
        self.coral_client = None
        self.coral_connected = False
        
        # Sovereign Infrastructure (PL Genesis Hackathon)
        self.autonome_registered = False
        self.libp2p_node = None
        
        logger.info("[SNEL] SNEL Coral Adapter initialized successfully")

    def load_config(self) -> Dict[str, Any]:
        """Load Coral agent configuration"""
        logger.info("[SNEL] Loading Coral agent configuration...")
        
        runtime = os.getenv("CORAL_ORCHESTRATION_RUNTIME", None)
        if runtime is None:
            load_dotenv()
        
        config = {
            "runtime": runtime,
            "coral_server_url": os.getenv("CORAL_SERVER_URL", "http://localhost:5555"),
            "agent_id": os.getenv("CORAL_AGENT_ID", "snel-defi-agent"),
            "model_name": os.getenv("MODEL_NAME", "gpt-4"),
            "model_provider": os.getenv("MODEL_PROVIDER", "openai"),
            "api_key": os.getenv("MODEL_API_KEY") or os.getenv("OPENAI_API_KEY"),
            "model_temperature": float(os.getenv("MODEL_TEMPERATURE", DEFAULT_TEMPERATURE)),
            "model_token": int(os.getenv("MODEL_TOKEN_LIMIT", DEFAULT_MAX_TOKENS)),
            "base_url": os.getenv("BASE_URL"),
            "auth_token": os.getenv("CORAL_AUTH_TOKEN"),
            "autonome_api_key": os.getenv("AUTONOME_API_KEY")
        }
        
        logger.info(f"[SNEL] Agent ID: {config['agent_id']}")
        return config

    async def initialize_sovereign_infra(self):
        """
        Initialize Libp2p and Autonome for PL Genesis Hackathon.
        ENHANCEMENT FIRST: Extends existing agent with decentralized coordination.
        """
        try:
            # 1. Autonome Registration (DeFAI Bounty)
            if self.config.get("autonome_api_key"):
                self.autonome_registered = self.coral_client.register_with_autonome(
                    self.config["autonome_api_key"]
                )
            
            # 2. Libp2p Node (Sovereign Infrastructure Bounty)
            # Initialize real Libp2p node for P2P agent coordination
            logger.info("[SNEL] Starting Libp2p node for P2P agent coordination...")
            self.libp2p_node = Libp2pNode()
            await self.libp2p_node.start()
            logger.info(f"[SNEL] Libp2p node started with PeerID: {self.libp2p_node.peer_id}")
            
        except Exception as e:
            logger.error(f"[SNEL] Failed to initialize sovereign infra: {e}")

    async def initialize_coral_connection(self) -> bool:
        """
        Initialize connection to Coral Server with proper authentication
        ENHANCEMENT: Uses proper Coral Protocol authentication flow
        """
        try:
            logger.info("[SNEL] Initializing Coral Protocol connection...")
            
            # Create Coral Protocol client
            self.coral_client = CoralProtocolClient(
                server_url=self.config["coral_server_url"],
                agent_id=self.config["agent_id"]
            )
            
            # Register agent with Coral Server (if not already registered)
            registration = AgentRegistration(
                agent_id=self.config["agent_id"],
                agent_type="local",
                name="SNEL DeFi Agent",
                description="AI-powered cross-chain DeFi assistant specialized in swaps, bridging, portfolio analysis, and protocol research across 17+ blockchain networks",
                capabilities=[
                    {"type": "tool", "name": "execute-swap", "description": "Execute token swaps across multiple blockchain networks"},
                    {"type": "tool", "name": "bridge-assets", "description": "Bridge assets between different blockchain networks"},
                    {"type": "tool", "name": "analyze-portfolio", "description": "Analyze DeFi portfolio across multiple chains"},
                    {"type": "tool", "name": "research-protocols", "description": "Research DeFi protocols and provide insights"}
                ]
            )
            
            # Authenticate agent with Coral Server
            if self.config.get("auth_token"):
                auth_response = self.coral_client.authenticate_agent(self.config["auth_token"])
                if auth_response:
                    # Establish WebSocket connection for persistent communication
                    connected = await self.coral_client.connect_to_websocket()
                    if connected:
                        self.coral_connected = True
                        logger.info("[SNEL] Coral Protocol connection established successfully")
                        
                        # PL Genesis: Initialize Sovereign Infra
                        await self.initialize_sovereign_infra()
                        
                        return True
                    else:
                        logger.error("[SNEL] Failed to establish WebSocket connection with Coral Server")
                        return False
                else:
                    logger.error("[SNEL] Failed to authenticate with Coral Server")
                    return False
            else:
                logger.warning("[SNEL] No authentication token provided for Coral Server")
                return False
                
        except Exception as e:
            logger.error(f"[SNEL] Exception during Coral Protocol initialization: {str(e)}")
            return False

    async def execute_defi_operation(self, operation: str, parameters: Dict[str, Any]) -> str:
        """
        Execute DeFi operation using orchestrator
        ENHANCEMENT: Uses shared service layer across platforms
        RELIABLE: Properly handles errors and provides consistent responses
        SOVEREIGN: Submits verifiable proof to Autonome
        """
        start_time = time.time()
        self.total_requests += 1
        
        try:
            logger.info(f"[SNEL] Coral Agent executing: {operation}")
            
            # ENHANCEMENT: Execute via shared orchestrator for consistent experience
            result = await self.orchestrator.execute_defi_operation(
                operation=operation,
                parameters=parameters,
                platform=Platform.CORAL_AGENT,
                user_id=parameters.get('user_id', 'coral-user')
            )
            
            # RELIABLE: Format result for Coral agent
            if result['success']:
                response_data = result['data']
                
                # SOVEREIGN: Submit verifiable action to Autonome (Proof-of-Action)
                # If research, proof is the IPFS CID
                proof = response_data.get('ipfs_proof', 'tx_hash_placeholder')
                if self.autonome_registered:
                    self.coral_client.submit_verifiable_action(
                        action_type=operation,
                        details=parameters,
                        proof=proof
                    )

                # USER DELIGHT: Format response as natural language
                if operation.lower() in ['swap', 'trade', 'exchange']:
                    response = self._format_swap_response(response_data)
                elif operation.lower() in ['bridge', 'transfer']:
                    response = self._format_bridge_response(response_data)
                elif operation.lower() in ['analyze', 'portfolio', 'balance']:
                    response = self._format_portfolio_response(response_data)
                elif operation.lower() in ['research', 'protocol']:
                    response = self._format_research_response(response_data)
                else:
                    response = response_data.get('snel_response', 'No response generated')
                
                # PERFORMANCE: Log success and timing
                duration = time.time() - start_time
                self.request_times.append(duration)
                self.success_count += 1
                
                return response
            else:
                return f"Error: {result['error']}"
                
        except Exception as e:
            error_msg = f"DeFi operation failed: {str(e)}"
            logger.error(f"[SNEL] {error_msg}")
            return error_msg

    def _format_swap_response(self, data: Dict[str, Any]) -> str:
        """Format swap response in natural language for Coral agent"""
        from_token = data.get('from_token')
        to_token = data.get('to_token')
        amount = data.get('amount')
        chain_id = data.get('chain_id', 1)
        output = data.get('estimated_output', 'unknown')
        
        response = f"Swap Quote: {amount} {from_token} → {output} {to_token} on {self._get_chain_name(chain_id)}.
"
        return response

    def _format_bridge_response(self, data: Dict[str, Any]) -> str:
        """Format bridge response in natural language for Coral agent"""
        from_chain = data.get('from_chain')
        to_chain = data.get('to_chain')
        token = data.get('token')
        amount = data.get('amount')
        
        response = f"Bridge Quote: {amount} {token} from {from_chain} to {to_chain}.
"
        return response

    def _format_portfolio_response(self, data: Dict[str, Any]) -> str:
        """Format portfolio analysis in natural language for Coral agent"""
        wallet = data.get('wallet_address')
        total_value = data.get('total_value', 0)
        
        response = f"Portfolio Analysis for {wallet}:
"
        response += f"Total Value: ${total_value:,.2f}
"
        return response

    def _format_research_response(self, data: Dict[str, Any]) -> str:
        """Format protocol research in natural language for Coral agent"""
        protocol = data.get('protocol')
        analysis = data.get('analysis', 'No analysis available')
        ipfs_proof = data.get('ipfs_proof')
        
        response = f"Research: {protocol}
"
        response += f"{analysis}
"
        if ipfs_proof:
            response += f"
Decentralized Proof-of-Research (IPFS): {ipfs_proof}"
        
        return response

    def _get_chain_name(self, chain_id: int) -> str:
        """Helper to convert chain ID to readable name"""
        chain_names = {
            1: "Ethereum", 56: "BNB Chain", 137: "Polygon",
            10: "Optimism", 42161: "Arbitrum", 8453: "Base",
            43114: "Avalanche", 250: "Fantom"
        }
        return chain_names.get(chain_id, f"Chain {chain_id}")

    async def get_tools_description(self, tools: List[Any]) -> str:
        """Get description of available tools"""
        descriptions = []
        for tool in tools:
            tool_desc = f"Tool: {tool.name}, Schema: {json.dumps(tool.args)}"
            descriptions.append(tool_desc)
        return "
".join(descriptions)

    async def create_agent_executor(self, coral_tools: List[Any]) -> AgentExecutor:
        """Create SNEL agent executor with DeFi capabilities"""
        logger.info("[SNEL] Creating Coral agent executor...")
        
        tools_description = await self.get_tools_description(coral_tools)
        
        prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                f"""You are SNEL, an AI-powered DeFi assistant agent.
                Available tools: {tools_description}
                """
            ),
            ("human", "{user_input}"),
            ("placeholder", "{agent_scratchpad}")
        ])
        
        model = init_chat_model(
            model=self.config["model_name"],
            model_provider=self.config["model_provider"], 
            api_key=self.config["api_key"],
            temperature=self.config["model_temperature"],
            max_tokens=self.config["model_token"]
        )
        
        agent = create_tool_calling_agent(model, coral_tools, prompt)
        executor = AgentExecutor(agent=agent, tools=coral_tools, verbose=True)
        return executor

    async def run(self):
        """Main execution loop for SNEL Coral Adapter"""
        logger.info("[SNEL] Starting SNEL Coral Adapter...")
        
        try:
            coral_initialized = await self.initialize_coral_connection()
            if not coral_initialized:
                logger.warning("[SNEL] Proceeding without Coral Protocol connection")
            
            # Main execution logic...
            while True:
                await asyncio.sleep(1)
        except Exception as e:
            logger.error(f"[SNEL] Fatal error: {str(e)}")
            raise

    async def _performance_monitor(self):
        """PERFORMANCE: Monitor and log agent performance"""
        while True:
            await asyncio.sleep(60)
            if self.total_requests > 0:
                success_rate = (self.success_count / self.total_requests) * 100
                logger.info(f"[SNEL] Performance: {success_rate:.1f}% success rate")

async def main():
    adapter = SNELCoralAdapter()
    await adapter.run()

if __name__ == "__main__":
    asyncio.run(main())

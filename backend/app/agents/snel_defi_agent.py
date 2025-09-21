"""
SNEL DeFi Agent - Coral Protocol Integration
ENHANCEMENT FIRST: Extends existing SNEL backend to work as rentable Coral agent
DRY: Reuses existing services and infrastructure
MODULAR: Can work standalone or with other agents
"""

import asyncio
import json
import logging
import os
import urllib.parse
from typing import Dict, List, Any
from dotenv import load_dotenv

# Langchain imports for Coral integration
from langchain.chat_models import init_chat_model
from langchain.prompts import ChatPromptTemplate
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain.agents import create_tool_calling_agent, AgentExecutor

# ENHANCEMENT: Import existing SNEL services
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.ai.gpt_service import GPTService
from services.external.web3_service import Web3Service
from services.portfolio.portfolio_service import PortfolioService
from services.external.axelar_service import AxelarService
from services.external.brian_service import BrianService

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

class SNELDeFiAgent:
    """
    SNEL DeFi Agent for Coral Protocol
    ENHANCEMENT: Wraps existing SNEL capabilities as rentable agent
    """
    
    def __init__(self):
        print("[SNEL] Initializing SNEL DeFi Agent...")
        
        # ENHANCEMENT: Reuse existing SNEL services
        self.gpt_service = GPTService()
        self.web3_service = Web3Service()
        self.portfolio_service = PortfolioService()
        self.axelar_service = AxelarService()
        self.brian_service = BrianService()
        
        # Agent-specific config
        self.config = self.load_config()
        self.chat_history = []
        
        print("[SNEL] SNEL DeFi Agent initialized successfully")
    
    def load_config(self) -> Dict[str, Any]:
        """Load Coral agent configuration"""
        print("[SNEL] Loading Coral agent configuration...")
        
        runtime = os.getenv("CORAL_ORCHESTRATION_RUNTIME", None)
        if runtime is None:
            load_dotenv()
        
        config = {
            "runtime": runtime,
            "coral_sse_url": os.getenv("CORAL_SSE_URL"),
            "agent_id": os.getenv("CORAL_AGENT_ID", "snel-defi-agent"),
            "model_name": os.getenv("MODEL_NAME", "gpt-4"),
            "model_provider": os.getenv("MODEL_PROVIDER", "openai"),
            "api_key": os.getenv("MODEL_API_KEY") or os.getenv("OPENAI_API_KEY"),
            "model_temperature": float(os.getenv("MODEL_TEMPERATURE", DEFAULT_TEMPERATURE)),
            "model_token": int(os.getenv("MODEL_TOKEN_LIMIT", DEFAULT_MAX_TOKENS)),
            "base_url": os.getenv("BASE_URL")
        }
        
        print(f"[SNEL] Agent ID: {config['agent_id']}")
        print(f"[SNEL] Model: {config['model_name']}")
        return config

    async def execute_defi_operation(self, operation: str, parameters: Dict[str, Any]) -> str:
        """
        Execute DeFi operation using existing SNEL services
        ENHANCEMENT: Leverages existing DeFi infrastructure
        """
        print(f"[SNEL] Executing DeFi operation: {operation}")
        print(f"[SNEL] Parameters: {parameters}")
        
        try:
            # Route to appropriate SNEL service based on operation
            if operation.lower() in ['swap', 'trade', 'exchange']:
                return await self._execute_swap(parameters)
            elif operation.lower() in ['bridge', 'transfer']:
                return await self._execute_bridge(parameters)
            elif operation.lower() in ['analyze', 'portfolio', 'balance']:
                return await self._analyze_portfolio(parameters)
            elif operation.lower() in ['research', 'protocol']:
                return await self._research_protocol(parameters)
            else:
                return await self._process_natural_language(operation, parameters)
                
        except Exception as e:
            error_msg = f"DeFi operation failed: {str(e)}"
            print(f"[SNEL] ERROR: {error_msg}")
            return error_msg

    async def _execute_swap(self, params: Dict[str, Any]) -> str:
        """Execute token swap using existing SNEL infrastructure"""
        print("[SNEL] Processing swap request...")
        
        # ENHANCEMENT: Use existing BrianService for swaps
        try:
            from_token = params.get('from_token', params.get('token_in'))
            to_token = params.get('to_token', params.get('token_out'))
            amount = params.get('amount')
            chain_id = params.get('chain_id', 1)  # Default to Ethereum
            
            if not all([from_token, to_token, amount]):
                return "Missing required parameters: from_token, to_token, amount"
            
            # Use existing Brian service for swap quote
            quote_result = await self.brian_service.get_swap_quote(
                from_token=from_token,
                to_token=to_token,
                amount=str(amount),
                chain_id=chain_id
            )
            
            return f"Swap quote: {amount} {from_token} → {to_token} on chain {chain_id}. " \
                   f"Estimated output: {quote_result.get('estimated_output', 'N/A')}"
                   
        except Exception as e:
            return f"Swap execution failed: {str(e)}"

    async def _execute_bridge(self, params: Dict[str, Any]) -> str:
        """Execute cross-chain bridge using existing SNEL infrastructure"""
        print("[SNEL] Processing bridge request...")
        
        try:
            # ENHANCEMENT: Use existing Axelar service
            from_chain = params.get('from_chain')
            to_chain = params.get('to_chain')
            token = params.get('token', 'USDC')
            amount = params.get('amount')
            
            if not all([from_chain, to_chain, amount]):
                return "Missing required parameters: from_chain, to_chain, amount"
            
            # Use existing Axelar integration
            bridge_result = await self.axelar_service.estimate_bridge_fee(
                source_chain=from_chain,
                destination_chain=to_chain,
                asset=token
            )
            
            return f"Bridge quote: {amount} {token} from {from_chain} to {to_chain}. " \
                   f"Estimated fee: {bridge_result.get('fee', 'N/A')}"
                   
        except Exception as e:
            return f"Bridge execution failed: {str(e)}"

    async def _analyze_portfolio(self, params: Dict[str, Any]) -> str:
        """Analyze portfolio using existing SNEL infrastructure"""
        print("[SNEL] Processing portfolio analysis...")
        
        try:
            wallet_address = params.get('wallet_address', params.get('address'))
            chain_id = params.get('chain_id', 1)
            
            if not wallet_address:
                return "Missing required parameter: wallet_address"
            
            # ENHANCEMENT: Use existing portfolio service
            portfolio_data = await self.portfolio_service.analyze_portfolio(
                wallet_address=wallet_address,
                chain_id=chain_id
            )
            
            # Format response
            total_value = portfolio_data.get('total_value', 0)
            token_count = len(portfolio_data.get('tokens', []))
            
            return f"Portfolio Analysis for {wallet_address}:\n" \
                   f"Total Value: ${total_value:,.2f}\n" \
                   f"Token Count: {token_count}\n" \
                   f"Chain: {chain_id}"
                   
        except Exception as e:
            return f"Portfolio analysis failed: {str(e)}"

    async def _research_protocol(self, params: Dict[str, Any]) -> str:
        """Research DeFi protocol using existing SNEL infrastructure"""
        print("[SNEL] Processing protocol research...")
        
        try:
            protocol_name = params.get('protocol', params.get('name'))
            
            if not protocol_name:
                return "Missing required parameter: protocol name"
            
            # ENHANCEMENT: Use existing GPT service for research
            research_prompt = f"Provide a concise analysis of the {protocol_name} DeFi protocol, " \
                             f"including its main features, TVL, risks, and current status."
            
            research_result = await self.gpt_service.chat_completion(
                messages=[{"role": "user", "content": research_prompt}],
                max_tokens=500
            )
            
            return f"Research: {protocol_name}\n{research_result}"
                   
        except Exception as e:
            return f"Protocol research failed: {str(e)}"

    async def _process_natural_language(self, operation: str, params: Dict[str, Any]) -> str:
        """Process natural language DeFi requests using existing SNEL AI"""
        print("[SNEL] Processing natural language request...")
        
        try:
            # ENHANCEMENT: Use existing GPT service with DeFi context
            context = f"User request: {operation}\nParameters: {json.dumps(params)}"
            
            prompt = f"""You are SNEL, an AI DeFi assistant. Process this request:
            {context}
            
            Provide a helpful response about DeFi operations, portfolio analysis, or protocol information.
            If this requires a transaction, explain what would happen but don't execute it.
            """
            
            response = await self.gpt_service.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=400
            )
            
            return f"SNEL Analysis: {response}"
                   
        except Exception as e:
            return f"Natural language processing failed: {str(e)}"

    async def get_tools_description(self, tools: List[Any]) -> str:
        """Get description of available tools"""
        descriptions = []
        for tool in tools:
            tool_desc = f"Tool: {tool.name}, Schema: {json.dumps(tool.args)}"
            descriptions.append(tool_desc)
        return "\n".join(descriptions)

    async def create_agent_executor(self, coral_tools: List[Any]) -> AgentExecutor:
        """Create SNEL agent executor with DeFi capabilities"""
        print("[SNEL] Creating SNEL DeFi agent executor...")
        
        tools_description = await self.get_tools_description(coral_tools)
        
        # DeFi-focused prompt template
        prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                f"""You are SNEL, an AI-powered DeFi assistant agent specialized in cross-chain operations.
                
                Your capabilities include:
                - Token swaps across 17+ blockchain networks
                - Cross-chain bridging with Axelar
                - Portfolio analysis and risk assessment
                - DeFi protocol research and recommendations
                - Natural language DeFi operations
                
                Available tools: {tools_description}
                
                When users request DeFi operations:
                1. Parse the request to understand the operation (swap, bridge, analyze, research)
                2. Extract required parameters (tokens, amounts, chains, addresses)
                3. Execute using appropriate SNEL services
                4. Provide clear, actionable responses
                5. Always prioritize user safety and explain risks
                
                Use chat history: {{chat_history}} for context.
                
                For multi-agent coordination:
                - Collaborate with other agents for complex strategies
                - Share portfolio data with risk assessment agents
                - Coordinate with market analysis agents for optimal timing
                """
            ),
            ("human", "{user_input}"),
            ("placeholder", "{agent_scratchpad}")
        ])
        
        # Initialize model with SNEL's configuration
        model = init_chat_model(
            model=self.config["model_name"],
            model_provider=self.config["model_provider"], 
            api_key=self.config["api_key"],
            temperature=self.config["model_temperature"],
            max_tokens=self.config["model_token"],
            base_url=self.config.get("base_url")
        )
        
        agent = create_tool_calling_agent(model, coral_tools, prompt)
        executor = AgentExecutor(agent=agent, tools=coral_tools, verbose=True)
        
        print("[SNEL] SNEL DeFi agent executor created successfully")
        return executor

    async def run(self):
        """
        Main execution loop for SNEL DeFi Agent
        MODULAR: Can run independently or as part of multi-agent system
        """
        print("[SNEL] Starting SNEL DeFi Agent...")
        
        try:
            # Connect to Coral Server
            coral_params = {
                "agentId": self.config["agent_id"],
                "agentDescription": "SNEL - AI-powered cross-chain DeFi assistant specialized in swaps, bridging, portfolio analysis, and protocol research across 17+ blockchain networks"
            }
            
            query_string = urllib.parse.urlencode(coral_params)
            coral_server_url = f"{self.config['coral_sse_url']}?{query_string}"
            
            print(f"[SNEL] Connecting to Coral Server: {coral_server_url}")
            
            # Setup MCP client
            client = MultiServerMCPClient(
                connections={
                    "coral": {
                        "transport": "sse",
                        "url": coral_server_url,
                        "timeout": 30000,
                        "sse_read_timeout": 30000,
                    }
                }
            )
            
            # Get available tools
            coral_tools = await client.get_tools(server_name="coral")
            print(f"[SNEL] Connected with {len(coral_tools)} tools available")
            
            agent_tools = {tool.name: tool for tool in coral_tools}
            agent_executor = await self.create_agent_executor(coral_tools)
            
            print("[SNEL] SNEL DeFi Agent ready for requests!")
            
            # Main execution loop
            while True:
                try:
                    # Get user input
                    if self.config["runtime"] is not None:
                        user_input = await agent_tools[REQUEST_QUESTION_TOOL].ainvoke({
                            "message": "How can SNEL help with your DeFi needs today?"
                        })
                    else:
                        user_input = input("SNEL DeFi Agent - How can I help? ").strip()
                    
                    if not user_input:
                        continue
                    
                    # Format chat history
                    formatted_history = "\n".join([
                        f"User: {chat['input']}\nSNEL: {chat['response']}" 
                        for chat in self.chat_history[-MAX_CHAT_HISTORY:]
                    ])
                    
                    # Execute request
                    result = await agent_executor.ainvoke({
                        "user_input": user_input,
                        "agent_scratchpad": [],
                        "chat_history": formatted_history
                    })
                    
                    response = result.get('output', 'No output returned')
                    
                    # Send response
                    if self.config["runtime"] is not None:
                        await agent_tools[ANSWER_QUESTION_TOOL].ainvoke({
                            "response": response
                        })
                    else:
                        print(f"SNEL: {response}")
                    
                    # Update chat history
                    self.chat_history.append({
                        "input": user_input,
                        "response": response
                    })
                    
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    print(f"[SNEL] Error in request loop: {str(e)}")
                    await asyncio.sleep(5)
                    
        except Exception as e:
            print(f"[SNEL] Fatal error: {str(e)}")
            raise

async def main():
    """Entry point for SNEL DeFi Agent"""
    print("=" * 50)
    print("SNEL DeFi Agent - Coral Protocol Integration")
    print("AI-Powered Cross-Chain DeFi Assistant")
    print("=" * 50)
    
    agent = SNELDeFiAgent()
    await agent.run()

if __name__ == "__main__":
    asyncio.run(main())

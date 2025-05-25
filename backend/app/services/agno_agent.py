from agno.agent import Agent
from agno.models.anthropic import Claude
from agno.tools.reasoning import ReasoningTools
from web3 import Web3
from typing import Optional, Dict
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Web3Helper:
    def __init__(self, supported_chains: Dict[int, str]):
        self.supported_chains = supported_chains
        self.web3_instances = {}

        # Initialize Web3 instances for each chain
        for chain_id, chain_name in supported_chains.items():
            rpc_url = os.getenv(f"{chain_name.upper()}_RPC_URL")
            if rpc_url:
                self.web3_instances[chain_id] = Web3(Web3.HTTPProvider(rpc_url))

    def get_balance(self, address: str, chain_id: Optional[int] = None) -> Optional[float]:
        """Get the native token balance for an address on a specific chain."""
        if chain_id and chain_id in self.web3_instances:
            w3 = self.web3_instances[chain_id]
            try:
                balance = w3.eth.get_balance(address)
                return float(w3.from_wei(balance, 'ether'))
            except Exception as e:
                print(f"Error getting balance for {address} on chain {chain_id}: {str(e)}")
                return None
        return None

    def get_token_balance(self, token_address: str, wallet_address: str, chain_id: int) -> Optional[float]:
        """Get the balance of a specific token for a wallet on a chain."""
        if chain_id not in self.web3_instances:
            return None

        w3 = self.web3_instances[chain_id]
        try:
            # ERC20 ABI for balanceOf
            abi = [{"constant":True,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"type":"function"}]
            contract = w3.eth.contract(address=token_address, abi=abi)
            balance = contract.functions.balanceOf(wallet_address).call()
            decimals = contract.functions.decimals().call()
            return float(balance) / (10 ** decimals)
        except Exception as e:
            print(f"Error getting token balance for {token_address} on chain {chain_id}: {str(e)}")
            return None

class PortfolioManagementAgent:
    # Define supported chains and their IDs
    SUPPORTED_CHAINS = {
        1: "Ethereum",
        8453: "Base",
        42161: "Arbitrum",
        10: "Optimism",
        137: "Polygon",
        43114: "Avalanche",
        534352: "Scroll",
        56: "BSC",
        59144: "Linea",
        5000: "Mantle",
        81457: "Blast",
        324: "zkSync Era",
    }

    def __init__(self):
        # Get API keys from environment
        anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
        if not anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in environment variables")

        # Initialize Web3 helper
        self.web3_helper = Web3Helper(self.SUPPORTED_CHAINS)

        # Initialize Agno agent for analysis
        self.agent = Agent(
            model=Claude(
                id="claude-3-sonnet-20240229",
                api_key=anthropic_api_key
            ),
            tools=[
                ReasoningTools(add_instructions=True),
            ],
            description="Portfolio Management Agent for DeFi cross-chain analysis.",
            instructions=[
                "Analyze user's DeFi portfolio across multiple chains.",
                "Provide intelligent rebalancing and risk assessment suggestions.",
                "Output clear, actionable recommendations.",
                "Use on-chain data to provide accurate portfolio insights.",
                "Consider market conditions and trends in analysis.",
                "Format responses in markdown for better readability.",
                f"Supported chains: {', '.join(self.SUPPORTED_CHAINS.values())}",
            ],
            markdown=True
        )

    def analyze_portfolio(self, user_prompt: str, wallet_address: str, chain_id: Optional[int] = None) -> str:
        """
        Analyze a user's portfolio using their wallet address.

        Args:
            user_prompt: The user's analysis request
            wallet_address: The user's wallet address to analyze
            chain_id: Optional current chain ID to focus analysis

        Returns:
            str: Analysis results and recommendations
        """
        try:
            # Build chain context
            chain_context = ""
            balances = {}

            # If chain_id is provided, only check that chain
            chains_to_check = [chain_id] if chain_id else self.SUPPORTED_CHAINS.keys()

            # Get balances for all chains or specific chain
            for cid in chains_to_check:
                if cid in self.SUPPORTED_CHAINS:
                    balance = self.web3_helper.get_balance(wallet_address, cid)
                    if balance:
                        balances[self.SUPPORTED_CHAINS[cid]] = balance
                        chain_context += f"\n{self.SUPPORTED_CHAINS[cid]} balance: {balance} {self.SUPPORTED_CHAINS[cid]}"

            # Enhance the prompt with the wallet address and chain context
            enhanced_prompt = f"""
            Analyze the portfolio for wallet address: {wallet_address}
            {chain_context}
            User request: {user_prompt}

            Please provide:
            1. Current portfolio composition across supported chains
            2. Asset allocation and distribution
            3. Risk assessment and exposure analysis
            4. Chain-specific insights and opportunities
            5. Actionable recommendations for portfolio optimization

            Focus on providing accurate on-chain data and clear, actionable insights.
            If certain chains are not accessible, note that in the analysis.
            """

            # Get the agent's response using the run method with timeout handling
            import concurrent.futures

            def run_agent():
                return self.agent.run(enhanced_prompt)

            # Use ThreadPoolExecutor with timeout
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(run_agent)
                try:
                    response = future.result(timeout=120)  # 2-minute timeout
                except concurrent.futures.TimeoutError:
                    return "Portfolio analysis is taking longer than expected. This might be due to complex on-chain positions or network delays. Please try again in a moment."
                except Exception as e:
                    print(f"Agent execution failed: {str(e)}")
                    return f"Error during portfolio analysis: {str(e)}"

            if response:
                if hasattr(response, 'content'):
                    if response.content:
                        # Clean up the content and return it
                        full_content = response.content.strip()
                        # Remove the <r> tags if present
                        if full_content.startswith('<r>') and full_content.endswith('</r>'):
                            full_content = full_content[3:-4].strip()

                        return full_content
                    else:
                        return "Error: Portfolio analysis generated empty content. Please try again."
                else:
                    if isinstance(response, str):
                        return response.strip()
                    else:
                        return "Error: Portfolio analysis returned unexpected response format. Please try again."
            else:
                return "Error: Portfolio analysis agent failed to generate response. Please try again."

        except Exception as e:
            print(f"Exception in analyze_portfolio: {str(e)}")
            import traceback
            traceback.print_exc()
            return f"Error analyzing portfolio: {str(e)}"

    def create_summary(self, full_analysis: str) -> str:
        """Create a concise summary of the portfolio analysis for better UX."""
        try:
            # Extract key points using simple text processing
            lines = full_analysis.split('\n')
            summary_points = []

            # Look for key sections and extract main points
            current_section = ""
            for line in lines:
                line = line.strip()
                if not line:
                    continue

                # Identify section headers
                if line.startswith('##') or line.startswith('###'):
                    current_section = line.replace('#', '').strip()
                    continue

                # Extract bullet points and key insights
                if line.startswith('-') and len(line) > 20:
                    # Clean up bullet point
                    point = line[1:].strip()
                    if len(point) < 100:  # Keep only concise points
                        summary_points.append(f"• {point}")
                elif line.startswith('**') and line.endswith('**'):
                    # Extract bold headers
                    header = line.replace('*', '').strip()
                    if len(header) < 50:
                        summary_points.append(f"**{header}**")

            # If we have points, create a summary
            if summary_points:
                # Take the first 5-6 most important points
                key_points = summary_points[:6]
                summary = "**Portfolio Analysis Summary:**\n\n" + "\n".join(key_points)

                # Add a note about the full analysis
                summary += "\n\n*Click 'View Full Analysis' for detailed recommendations and insights.*"
                return summary
            else:
                # Fallback: create a simple summary from the first few sentences
                sentences = full_analysis.replace('\n', ' ').split('.')
                first_sentences = [s.strip() for s in sentences[:3] if len(s.strip()) > 20]
                if first_sentences:
                    return "**Portfolio Analysis Summary:**\n\n" + ". ".join(first_sentences) + ".\n\n*Click 'View Full Analysis' for complete details.*"
                else:
                    return "Portfolio analysis completed. Click 'View Full Analysis' for detailed insights and recommendations."

        except Exception as e:
            print(f"Error creating summary: {str(e)}")
            return "Portfolio analysis completed. Click 'View Full Analysis' for detailed insights and recommendations."
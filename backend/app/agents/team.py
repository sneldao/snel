from textwrap import dedent
import logging
from typing import Dict, Any, List
from tenacity import retry, stop_after_attempt, wait_exponential

from agno.agent import Agent
from agno.models.anthropic import Claude
from agno.models.openai import OpenAIChat
from agno.team.team import Team
from agno.tools.reasoning import ReasoningTools
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.tools.yfinance import YFinanceTools

logger = logging.getLogger(__name__)

# Portfolio Management Agent - Handles portfolio analysis and rebalancing
portfolio_agent = Agent(
    name="Portfolio Manager",
    role="Analyze and optimize DeFi portfolios across chains",
    model=OpenAIChat(id="gpt-4o-mini"),
    tools=[
        YFinanceTools(stock_price=True, analyst_recommendations=True),
        ReasoningTools(add_instructions=True),
    ],
    instructions=dedent("""\
        1. Portfolio Analysis 📊
           - Track holdings across 16+ chains
           - Calculate risk metrics and exposure
           - Monitor stablecoin allocations
           - Evaluate gas costs and efficiency
        2. Optimization Strategy 📈
           - Suggest rebalancing opportunities
           - Identify yield farming potential
           - Calculate impermanent loss risk
           - Optimize for user risk tolerance
        3. Performance Tracking 📉
           - Monitor portfolio performance
           - Track historical returns
           - Compare against benchmarks
           - Generate performance reports
    """),
    add_datetime_to_instructions=True,
)

# Risk Assessment Agent - Evaluates protocol and market risks
risk_agent = Agent(
    name="Risk Assessor",
    role="Evaluate DeFi protocol and market risks",
    model=OpenAIChat(id="gpt-4o-mini"),
    tools=[
        DuckDuckGoTools(),  # For researching protocol risks
        ReasoningTools(add_instructions=True),
    ],
    instructions=dedent("""\
        1. Protocol Analysis 🔍
           - Audit smart contract risks
           - Monitor TVL and activity
           - Track historical incidents
           - Assess protocol maturity
        2. Market Risk 📊
           - Monitor market conditions
           - Track correlation metrics
           - Analyze volatility patterns
           - Evaluate liquidity depth
        3. Regulatory Assessment 📋
           - Monitor compliance status
           - Track regulatory changes
           - Assess jurisdictional risks
           - Flag potential issues
    """),
    add_datetime_to_instructions=True,
)

# Yield Optimization Agent - Discovers and analyzes yield opportunities
yield_agent = Agent(
    name="Yield Hunter",
    role="Discover and analyze yield opportunities",
    model=OpenAIChat(id="gpt-4o-mini"),
    tools=[
        DuckDuckGoTools(),  # For researching yield opportunities
        ReasoningTools(add_instructions=True),
    ],
    instructions=dedent("""\
        1. Yield Discovery 🔍
           - Scout new opportunities
           - Calculate real yields
           - Compare risk-adjusted returns
           - Track historical stability
        2. Strategy Analysis 📈
           - Evaluate farming strategies
           - Calculate compound effects
           - Assess pool dynamics
           - Monitor reward tokens
        3. Implementation Planning 📋
           - Plan entry/exit timing
           - Calculate gas costs
           - Optimize transaction path
           - Monitor success metrics
    """),
    add_datetime_to_instructions=True,
)

# MEV Protection Agent - Protects transactions from MEV attacks
mev_agent = Agent(
    name="MEV Guardian",
    role="Protect transactions from MEV attacks",
    model=OpenAIChat(id="gpt-4o-mini"),
    tools=[
        ReasoningTools(add_instructions=True),
    ],
    instructions=dedent("""\
        1. Transaction Analysis 🔍
           - Monitor pending txns
           - Detect sandwich risks
           - Identify frontrun threats
           - Calculate MEV exposure
        2. Protection Strategy 🛡️
           - Route via private pools
           - Time block submissions
           - Use protective measures
           - Monitor success rate
        3. Performance Tracking 📊
           - Calculate value saved
           - Monitor protection rate
           - Track gas overhead
           - Report effectiveness
    """),
    add_datetime_to_instructions=True,
)

# Team Leader - Coordinates all agents and makes final decisions
team_leader = Team(
    name="DeFi Strategy Team",
    mode="coordinate",  # Using coordinate mode for complex decision making
    model=Claude(id="claude-3-7-sonnet-latest"),
    members=[portfolio_agent, risk_agent, yield_agent, mev_agent],
    tools=[ReasoningTools(add_instructions=True)],
    instructions=[
        "Coordinate agents to optimize DeFi portfolios",
        "Prioritize risk-adjusted returns",
        "Consider gas costs and MEV protection",
        "Generate clear, actionable recommendations",
        "Ensure all recommendations include risk disclaimers",
        "Format responses in markdown with clear sections",
        "Include confidence scores for recommendations",
    ],
    markdown=True,
    show_members_responses=True,
    enable_agentic_context=True,
    add_datetime_to_instructions=True,
    success_criteria="The team has successfully analyzed and optimized the portfolio while managing risks.",
)

class AgentError(Exception):
    """Base exception for agent-related errors"""
    pass

class AgentTimeoutError(AgentError):
    """Raised when an agent operation times out"""
    pass

class AgentResponseError(AgentError):
    """Raised when an agent provides an invalid response"""
    pass

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry_error_callback=lambda _: {"error": "All retries failed"}
)
def process_portfolio_command(command: str) -> Dict[str, Any]:
    """
    Process a natural language portfolio command through the agent team.
    
    Args:
        command: Natural language command from user
        
    Returns:
        Dict containing:
        - success: bool indicating if command was processed successfully
        - response: formatted response with recommendations
        - confidence: float indicating confidence in recommendations
        - risks: list of identified risks
        - next_steps: list of suggested next steps
    """
    try:
        # Process command through team leader
        response = team_leader.get_response(
            command,
            stream=True,
            stream_intermediate_steps=True,
            show_full_reasoning=True,
        )
        
        # Parse and validate response
        if not response or not isinstance(response, str):
            raise AgentResponseError("Invalid response from agent team")
            
        # Extract structured information
        result = {
            "success": True,
            "response": response,
            "confidence": _extract_confidence(response),
            "risks": _extract_risks(response),
            "next_steps": _extract_next_steps(response)
        }
        
        return result
        
    except Exception as e:
        logger.error(f"Error processing command '{command}': {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "response": "An error occurred while processing your request. Please try again."
        }

def _extract_confidence(response: str) -> float:
    """Extract confidence score from response"""
    try:
        # Look for confidence indicators in the response
        if "High confidence" in response:
            return 0.9
        elif "Medium confidence" in response:
            return 0.7
        elif "Low confidence" in response:
            return 0.5
        return 0.6  # Default moderate confidence
    except Exception:
        return 0.5

def _extract_risks(response: str) -> List[str]:
    """Extract risk factors from response"""
    try:
        risks = []
        # Look for risk section in markdown
        if "## Risks" in response:
            risk_section = response.split("## Risks")[1].split("##")[0]
            # Extract bullet points
            risks = [r.strip("- ").strip() for r in risk_section.split("\n") if r.strip().startswith("-")]
        return risks
    except Exception:
        return ["Unable to extract risk factors"]

def _extract_next_steps(response: str) -> List[str]:
    """Extract next steps from response"""
    try:
        steps = []
        # Look for next steps section in markdown
        if "## Next Steps" in response:
            steps_section = response.split("## Next Steps")[1].split("##")[0]
            # Extract bullet points
            steps = [s.strip("- ").strip() for s in steps_section.split("\n") if s.strip().startswith("-")]
        return steps
    except Exception:
        return ["Unable to extract next steps"] 
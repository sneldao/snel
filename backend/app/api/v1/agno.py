from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from app.services.agno_agent import PortfolioManagementAgent
from typing import Optional
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

class PortfolioAnalysisRequest(BaseModel):
    prompt: str = Field(description="Prompt for portfolio analysis")
    wallet_address: Optional[str] = Field(default=None, description="User's wallet address")
    chain_id: Optional[int] = Field(default=None, description="Current chain ID")

class PortfolioAnalysisResponse(BaseModel):
    result: str = Field(description="Agent result")
    summary: str = Field(description="Concise summary for better UX")
    full_analysis: str = Field(description="Complete detailed analysis")

try:
    # Instantiate the agent once (will validate environment variables)
    portfolio_agent = PortfolioManagementAgent()
except ValueError as e:
    logger.error(f"Failed to initialize Agno agent: {str(e)}")
    portfolio_agent = None

@router.post("/portfolio-analysis", response_model=PortfolioAnalysisResponse)
def analyze_portfolio(request: PortfolioAnalysisRequest):
    try:
        # Check if agent was properly initialized
        if portfolio_agent is None:
            raise HTTPException(
                status_code=500,
                detail="Agno agent not properly configured. Please check ANTHROPIC_API_KEY in environment variables."
            )

        if not request.wallet_address:
            raise HTTPException(
                status_code=400,
                detail="Wallet address is required for portfolio analysis"
            )

        # Validate chain ID if provided
        if request.chain_id and request.chain_id not in portfolio_agent.SUPPORTED_CHAINS:
            supported_chains = ", ".join(f"{name} ({id})" for id, name in portfolio_agent.SUPPORTED_CHAINS.items())
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported chain ID. Supported chains are: {supported_chains}"
            )

        # Pass prompt, wallet address, and chain ID to the agent
        logger.info(f"Analyzing portfolio for wallet: {request.wallet_address}, chain: {request.chain_id}")
        full_analysis = portfolio_agent.analyze_portfolio(
            request.prompt,
            request.wallet_address,
            request.chain_id
        )

        if not full_analysis:
            logger.error("Portfolio analysis returned empty result")
            raise HTTPException(
                status_code=500,
                detail="Portfolio analysis failed to generate results. Please try again."
            )

        # Generate a concise summary for better UX
        summary = portfolio_agent.create_summary(full_analysis)

        # Debug logging
        logger.info(f"Portfolio analysis response - Summary length: {len(summary)}, Full analysis length: {len(full_analysis)}")

        response = PortfolioAnalysisResponse(
            result=summary,  # Return summary as the main result for backward compatibility
            summary=summary,
            full_analysis=full_analysis
        )

        # Log the response structure for debugging
        logger.info(f"Response structure: result={len(response.result)}, summary={len(response.summary)}, full_analysis={len(response.full_analysis)}")

        return response
    except HTTPException:
        raise
    except ValueError as e:
        # Handle configuration errors
        raise HTTPException(
            status_code=500,
            detail=f"Configuration error: {str(e)}"
        )
    except Exception as e:
        logger.exception("Error in portfolio analysis")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to analyze portfolio: {str(e)}"
        )
"""
Portfolio command processor.
Handles portfolio analysis and management operations.
"""
import logging

from app.models.unified_models import (
    UnifiedCommand, UnifiedResponse, AgentType
)
from app.services.portfolio.portfolio_service import get_portfolio_summary
from .base_processor import BaseProcessor

logger = logging.getLogger(__name__)


class PortfolioProcessor(BaseProcessor):
    """Processes portfolio commands."""
    
    async def process(self, unified_command: UnifiedCommand) -> UnifiedResponse:
        """
        Process portfolio analysis command.
        
        Handles:
        - Portfolio value summary
        - Asset allocation
        - Diversification analysis
        - Risk assessment
        """
        try:
            logger.info(f"Processing portfolio command: {unified_command.command}")
            
            # Validate wallet connection
            if not unified_command.wallet_address:
                return self._create_error_response(
                    "Wallet address required for portfolio analysis",
                    AgentType.PORTFOLIO
                )
            
            # Get chain name for display
            chain_name = self.settings.chains.supported_chains.get(
                unified_command.chain_id,
                f"Chain {unified_command.chain_id}"
            )
            
            logger.info(f"Analyzing portfolio for {unified_command.wallet_address} on {chain_name}")
            
            # Get portfolio summary using consolidated service
            # This now uses the shared TokenQueryService for Web3 connections
            portfolio_data = await get_portfolio_summary(
                wallet_address=unified_command.wallet_address,
                chain_id=unified_command.chain_id
            )
            
            if "error" in portfolio_data:
                raise Exception(portfolio_data["error"])
            
            # Format successful portfolio response
            content = {
                "message": f"Portfolio analysis complete for {chain_name}",
                "type": "portfolio_analysis",
                "wallet_address": unified_command.wallet_address,
                "total_value_usd": portfolio_data.get("total_portfolio_value_usd", 0),
                "native_value_usd": portfolio_data.get("native_value_usd", 0),
                "token_value_usd": portfolio_data.get("token_value_usd", 0),
                "risk_score": portfolio_data.get("risk_score", "N/A"),
                "diversification_score": portfolio_data.get("diversification_score", "N/A"),
                "chain_distribution": portfolio_data.get("chain_distribution", {}),
                "requires_transaction": False
            }
            
            return self._create_success_response(
                content=content,
                agent_type=AgentType.PORTFOLIO,
                metadata={
                    "parsed_command": {
                        "chain": chain_name,
                        "command_type": "portfolio"
                    },
                    "portfolio_details": portfolio_data
                }
            )
            
        except Exception as e:
            logger.exception("Error processing portfolio command")
            return self._create_error_response(
                f"Portfolio analysis failed: {str(e)}",
                AgentType.PORTFOLIO,
                str(e)
            )

"""
Protocol research command processor.
Handles protocol research and analysis operations.
"""
import logging
import re
import os
from openai import AsyncOpenAI

from app.models.unified_models import (
    UnifiedCommand, UnifiedResponse, AgentType
)
from app.services.external.firecrawl_service import get_protocol_details, analyze_protocol_with_ai
from .base_processor import BaseProcessor

logger = logging.getLogger(__name__)


class ProtocolProcessor(BaseProcessor):
    """Processes protocol research commands."""
    
    async def process(self, unified_command: UnifiedCommand) -> UnifiedResponse:
        """
        Process protocol research command.
        
        Handles:
        - Protocol information gathering
        - Firecrawl web scraping
        - AI-powered protocol analysis
        """
        try:
            logger.info(f"Processing protocol research: {unified_command.command}")
            
            # Extract protocol name from command
            protocol_name = self._extract_protocol_name(unified_command)
            
            if not protocol_name:
                return self._create_error_response(
                    "Please specify a protocol to research. E.g., 'research Uniswap'",
                    AgentType.PROTOCOL_RESEARCH,
                    "No protocol specified"
                )
            
            logger.info(f"Researching protocol: {protocol_name}")
            
            # Scrape protocol content
            scrape_result = await get_protocol_details(
                protocol_name=protocol_name,
                max_content_length=2000,
                timeout=15,
                debug=True
            )
            
            if not scrape_result.get("scraping_success", False):
                return self._create_error_response(
                    f"Unable to find information about {protocol_name}. Check the protocol name and try again.",
                    AgentType.PROTOCOL_RESEARCH,
                    scrape_result.get("error", "Research failed")
                )
            
            # Analyze scraped content with AI
            openai_key = unified_command.openai_api_key or os.getenv("OPENAI_API_KEY")
            logger.info(f"Starting AI analysis for {protocol_name}")
            
            ai_result = await analyze_protocol_with_ai(
                protocol_name=protocol_name,
                raw_content=scrape_result.get("raw_content", ""),
                source_url=scrape_result.get("source_url", ""),
                openai_api_key=openai_key
            )
            
            # Combine results
            result = {
                **scrape_result,
                **ai_result,
                "type": "protocol_research_result"
            }
            
            content = {
                "message": f"Research complete for {protocol_name}",
                "type": "protocol_research_result",
                "protocol_name": protocol_name,
                "ai_summary": result.get("ai_summary", ""),
                "protocol_type": result.get("protocol_type", "DeFi Protocol"),
                "key_features": result.get("key_features", []),
                "security_info": result.get("security_info", ""),
                "financial_metrics": result.get("financial_metrics", ""),
                "analysis_quality": result.get("analysis_quality", "medium"),
                "source_url": result.get("source_url", ""),
                "raw_content": result.get("raw_content", ""),
                "analysis_success": result.get("analysis_success", False),
                "content_length": result.get("content_length", 0),
                "requires_transaction": False
            }
            
            return self._create_success_response(
                content=content,
                agent_type=AgentType.PROTOCOL_RESEARCH,
                metadata={
                    "parsed_command": {
                        "protocol": protocol_name,
                        "command_type": "protocol_research"
                    },
                    "research_details": {
                        "protocols_scraped": result.get("protocols_scraped", 1),
                        "scraping_success": result.get("scraping_success", False),
                        "source": result.get("source", "firecrawl")
                    }
                }
            )
            
        except Exception as e:
            logger.exception("Error processing protocol research")
            return self._create_error_response(
                "Protocol research service is temporarily unavailable",
                AgentType.PROTOCOL_RESEARCH,
                str(e)
            )
    
    def _extract_protocol_name(self, unified_command: UnifiedCommand) -> str:
        """Extract protocol name from command."""
        details = unified_command.details
        
        # Try to extract from details first
        if details and details.token_in and details.token_in.symbol:
            return details.token_in.symbol
        
        if details and hasattr(details, 'protocol_name'):
            return details.protocol_name
        
        # Extract from command text using regex
        command_lower = unified_command.command.lower()
        patterns = [
            r'research\s+(\w+)',
            r'tell me about\s+(\w+)',
            r'what is\s+(\w+)',
            r'about\s+(\w+)',
            r'info on\s+(\w+)',
            r'explain\s+(\w+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, command_lower)
            if match:
                return match.group(1)
        
        return None

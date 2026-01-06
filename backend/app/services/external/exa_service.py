"""
Exa discovery service - high-level interface for protocol discovery.
Uses ExaClient for actual API calls and data extraction.
"""
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


async def discover_defi_protocols(
    query: str,
    max_results: int = 5,
    timeout: int = 15,
) -> Dict[str, Any]:
    """
    Discover DeFi protocols and opportunities using Exa semantic search.
    
    High-level convenience function that creates a client and performs search.
    
    Args:
        query: Search query for DeFi opportunities
        max_results: Maximum number of results to return
        timeout: Request timeout in seconds
        
    Returns:
        Dictionary with search results and extracted opportunities
    """
    try:
        import os
        from app.services.external.exa_client import ExaClient, ExaError
        
        api_key = os.getenv("EXA_API_KEY", "")
        
        if not api_key:
            logger.error("Exa API key not configured")
            return {
                "error": "Exa API key not configured",
                "protocols_found": 0,
                "yield_opportunities": 0,
                "best_apy_found": "Unknown",
                "search_success": False,
                "protocols": []
            }
        
        # Create client (cache_client will be None unless injected)
        client = ExaClient(
            api_key=api_key,
            timeout=timeout,
            cache_client=None,  # Could be injected via DI
        )
        
        # Perform search
        result = await client.search_opportunities(
            query=query,
            category="yield",
            max_results=max_results,
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Exa discovery error: {e}")
        return {
            "error": str(e),
            "protocols_found": 0,
            "yield_opportunities": 0,
            "best_apy_found": "Unknown",
            "search_success": False,
            "protocols": []
        }

"""Build unified protocol research responses from different sources."""
from typing import Dict, Any, Optional, List, TYPE_CHECKING

if TYPE_CHECKING:
    from app.services.knowledge_base import ProtocolMetrics


class ProtocolResponseBuilder:
    """Single source of truth for protocol research response formatting."""
    
    @staticmethod
    def from_knowledge_base(
        protocol_name: str,
        entry: Any,  # ProtocolEntry
        metrics: Optional[Any] = None,  # Optional[ProtocolMetrics]
    ) -> Dict[str, Any]:
        """
        Build response from built-in knowledge base entry.
        
        Args:
            protocol_name: Name of the protocol
            entry: ProtocolEntry from knowledge base
            metrics: Optional dynamic metrics
            
        Returns:
            Formatted response content dict
        """
        content = {
            "message": f"Here's what I know about {entry.official_name}:",
            "type": "protocol_research_result",
            "protocol_name": protocol_name,
            "official_name": entry.official_name,
            "ai_summary": entry.summary,
            "protocol_type": entry.type,
            "key_features": entry.key_features,
            "analysis_quality": "high",
            "source_url": entry.source_url or "",
            "raw_content": "",
            "analysis_success": True,
            "content_length": 0,
            "requires_transaction": False,
            # Structured fields
            "privacy_explanation": entry.privacy_explanation or "",
            "technical_explanation": entry.technical_explanation or "",
            "how_it_works": entry.how_it_works or "",
            "recommended_wallets": entry.recommended_wallets,
            "use_cases": entry.use_cases,
            "from_knowledge_base": True,
            # Relationships
            "integrations_with": entry.integrations_with,
            "bridges_to": entry.bridges_to,
            "competes_with": entry.competes_with,
        }
        
        # Add dynamic metrics if available
        if metrics:
            content["metrics"] = {
                "tvl": metrics.tvl,
                "volume_24h": metrics.volume_24h,
                "market_cap": metrics.market_cap,
                "apy_yield": metrics.apy_yield,
                "fees": metrics.fees,
                "last_updated": metrics.last_updated.isoformat() if metrics.last_updated else None,
            }
        
        return content
    
    @staticmethod
    def from_firecrawl(
        protocol_name: str,
        scrape_result: Dict[str, Any],
        analysis_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Build response from Firecrawl scrape + AI analysis.
        
        Args:
            protocol_name: Name of the protocol
            scrape_result: Result from get_protocol_details()
            analysis_result: Result from ProtocolAnalyzer.analyze_scraped_content()
            
        Returns:
            Formatted response content dict
        """
        merged = {**scrape_result, **analysis_result}
        
        content = {
            "message": f"Research complete for {protocol_name}",
            "type": "protocol_research_result",
            "protocol_name": protocol_name,
            "ai_summary": merged.get("ai_summary", ""),
            "source_url": merged.get("source_url", ""),
            "raw_content": merged.get("raw_content", ""),
            "analysis_success": merged.get("analysis_success", False),
            "requires_transaction": False,
        }
        
        return content
    
    @staticmethod
    def from_ai_fallback(
        protocol_name: str,
        analysis_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Build response from AI general knowledge (no KB, no Firecrawl).
        
        Args:
            protocol_name: Name of the protocol
            analysis_result: Result from ProtocolAnalyzer.generate_fallback_summary()
            
        Returns:
            Formatted response content dict
        """
        content = {
            "message": analysis_result.get("ai_summary", ""),
            "type": "protocol_research_result",
            "protocol_name": protocol_name,
            "ai_summary": analysis_result.get("ai_summary", ""),
            "analysis_quality": "medium",
            "analysis_success": True,
            "from_ai_fallback": True,
            "requires_transaction": False,
        }
        
        return content
    
    @staticmethod
    def error_response(
        protocol_name: str,
        error_message: str,
    ) -> Dict[str, Any]:
        """
        Build error response.
        
        Args:
            protocol_name: Name of the protocol
            error_message: Error description
            
        Returns:
            Formatted error response dict
        """
        return {
            "message": error_message,
            "type": "protocol_research_result",
            "protocol_name": protocol_name,
            "analysis_success": False,
            "requires_transaction": False,
            "error": error_message,
        }

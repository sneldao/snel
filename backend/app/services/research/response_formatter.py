"""
Response formatting per intent type.
Structures responses to match user mental models for different query types.
"""
from typing import Dict, Any, List
from app.services.research.router import Intent


class ResponseFormatter:
    """Format research responses based on intent type."""
    
    @staticmethod
    def format_concept_response(
        concept_name: str,
        kb_data: Dict[str, Any],
        ai_explanation: str = None,
    ) -> Dict[str, Any]:
        """
        Format concept/educational response.
        
        Returns: {
            explanation, examples, related_concepts, 
            use_cases, recommended_resources
        }
        """
        return {
            "type": "concept",
            "concept": concept_name,
            "official_name": kb_data.get("official_name", concept_name),
            "explanation": kb_data.get("summary") or ai_explanation,
            "technical_explanation": kb_data.get("technical_explanation", ""),
            "how_it_works": kb_data.get("how_it_works", ""),
            "privacy_explanation": kb_data.get("privacy_explanation", ""),
            "key_features": kb_data.get("key_features", []),
            "use_cases": kb_data.get("use_cases", []),
            "recommended_wallets": kb_data.get("recommended_wallets", []),
            "related_concepts": [],  # Could be populated from KB
            "sources": {
                "source_type": "knowledge_base",
                "cached": True,
            },
        }
    
    @staticmethod
    def format_depth_response(
        protocol_name: str,
        firecrawl_data: Dict[str, Any],
        ai_analysis: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Format deep protocol research response.
        
        Returns: {
            protocol, type, summary, features, metrics,
            security, governance, source_url, analysis
        }
        """
        return {
            "type": "protocol_research",
            "protocol": {
                "name": protocol_name,
                "official_name": ai_analysis.get("official_name", protocol_name),
                "type": ai_analysis.get("protocol_type", "DeFi Protocol"),
                "summary": ai_analysis.get("ai_summary", ""),
            },
            "features": {
                "key_features": ai_analysis.get("key_features", []),
                "technical_details": firecrawl_data.get("extracted_data", {}),
            },
            "metrics": {
                "tvl": ai_analysis.get("tvl_analyzed", "N/A"),
                "financial_metrics": ai_analysis.get("financial_metrics", ""),
            },
            "security": {
                "audit_status": ai_analysis.get("security_audits", "Unknown"),
                "security_info": ai_analysis.get("security_info", ""),
            },
            "governance": {
                "token": ai_analysis.get("governance_token", "Unknown"),
                "voting": ai_analysis.get("governance_mechanism", ""),
            },
            "source": {
                "url": firecrawl_data.get("source_url", ""),
                "extracted_at": firecrawl_data.get("extracted_at", ""),
                "tool": "firecrawl",
            },
            "analysis": {
                "quality": ai_analysis.get("analysis_quality", "medium"),
                "success": ai_analysis.get("analysis_success", False),
            },
            "raw_content": firecrawl_data.get("raw_content", ""),
        }
    
    @staticmethod
    def format_discovery_response(
        query: str,
        exa_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Format discovery/opportunity response.
        
        Returns: {
            query, opportunities[], summary, sorted_by,
            best_opportunity, risk_assessment
        }
        """
        opportunities = exa_data.get("protocols", [])
        
        # Sort by APY descending
        sorted_opportunities = sorted(
            opportunities,
            key=lambda x: float(x.get("apy", "0").replace("%", "")) or 0,
            reverse=True
        )
        
        # Assess risk levels (simplistic)
        for opp in sorted_opportunities:
            opp["risk_level"] = ResponseFormatter._assess_risk(opp)
        
        return {
            "type": "discovery",
            "query": query,
            "summary": {
                "total_found": exa_data.get("protocols_found", 0),
                "yield_opportunities": exa_data.get("yield_opportunities", 0),
                "best_apy": exa_data.get("best_apy_found", "Unknown"),
            },
            "opportunities": sorted_opportunities,
            "ranking": {
                "sorted_by": "apy_descending",
                "total": len(sorted_opportunities),
            },
            "filters_available": [
                "apy", "tvl", "protocol_type", "risk_level"
            ],
            "source": {
                "tool": "exa",
                "search_type": "semantic",
            },
        }
    
    @staticmethod
    def _assess_risk(opportunity: Dict[str, Any]) -> str:
        """
        Simple risk assessment based on TVL and APY.
        
        Low: High TVL ($1B+), lower APY (<20%)
        Medium: Medium TVL, medium APY
        High: Low TVL or very high APY (>50%)
        """
        tvl = opportunity.get("tvl", "Unknown")
        apy = opportunity.get("apy", "Unknown")
        
        # If we can't extract metrics, assume medium
        if tvl == "Unknown" or apy == "Unknown":
            return "medium"
        
        try:
            # Extract numeric values
            tvl_value = float(''.join(c for c in tvl if c.isdigit() or c == '.'))
            apy_value = float(apy.replace("%", ""))
            
            # Risk calculation
            if "B" in tvl and apy_value < 20:
                return "low"
            elif "M" in tvl and apy_value > 50:
                return "high"
            elif apy_value > 50:
                return "high"
            else:
                return "medium"
        except (ValueError, IndexError):
            return "medium"
    
    @staticmethod
    def get_routing_context(intent: Intent) -> Dict[str, Any]:
        """
        Get context for displaying routing decision to user.
        Helpful for transparency and debugging.
        """
        contexts = {
            "concept": {
                "label": "General Knowledge",
                "emoji": "📚",
                "description": "Educational explanation",
                "cache_duration": "24 hours",
            },
            "depth": {
                "label": "Deep Research",
                "emoji": "🔍",
                "description": "Comprehensive protocol analysis",
                "cache_duration": "6 hours",
            },
            "discovery": {
                "label": "Opportunity Search",
                "emoji": "💰",
                "description": "Finding yield and opportunities",
                "cache_duration": "1 hour",
            },
        }
        return contexts.get(intent, {})

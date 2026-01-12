"""
Intent-driven research routing system.
Routes queries to the appropriate research tool (KB, Firecrawl, Exa) based on intent.
"""
import logging
import re
from typing import Literal, Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Intent types
Intent = Literal["concept", "depth", "discovery"]


@dataclass
class RoutingDecision:
    """Result of intent classification and routing decision."""
    intent: Intent
    confidence: float  # 0.0-1.0
    query: str
    original_query: str
    explanation: str
    extracted_entity: Optional[str] = None  # Protocol/concept name extracted from query


class ResearchRouter:
    """
    Single source of truth for routing research queries to the right tool.
    
    Intent types:
    - concept: General knowledge/education (KB → Exa if needed)
    - depth: Specific protocol research (Firecrawl → AI analysis)
    - discovery: Opportunity finding (Exa → ranked list)
    """

    # Pattern matching for each intent type
    CONCEPT_PATTERNS = [
        r"(?:explain|what is|how does|describe)\s+(privacy|shielding|bridging|governance|defi|yield farming|dex|lending|staking)",
        r"what (?:is|are)\s+(privacy|defi|crypto|blockchain|protocol)",
        r"explain\s+([\w\s]+)(?:feature|mechanism|technology)",
        r"how (?!does \w+ work\b)(does|do|can|would)\s+",  # Avoid "how does protocol work" -> depth
    ]

    DEPTH_PATTERNS = [
        r"research\s+(\w+)",
        r"tell me about\s+(\w+)",
        r"(?:what|who|where|when|how) (?:is|are|was|were)\s+(\w+)(?:\s+protocol)?",
        r"information (?:about|on)\s+(\w+)",
        r"details (?:about|on|for)\s+(\w+)",
        r"explain\s+(\w+)\s+(?:protocol|blockchain|token)",
        r"(?:how|why) does (\w+)\s+work",
    ]

    DISCOVERY_PATTERNS = [
        r"find\s+.*(?:yield|opportunities|rates|apr|apy|protocols|farming)",
        r"(?:best|highest|top)\s+.*(?:yield|apy|apr|opportunities|protocols)",
        r"(?:opportunities|protocols)\s+(?:on|in|for)\s+(\w+)",
        r"(?:compare|list)\s+.*(?:yields|protocols|opportunities)",
        r"(?:show|find)\s+(?:yield|opportunities|protocols|apy|apr)\s+",
        r"what.*(?:yield|apy|apr|opportunities).*(?:on|in|for)\s+(\w+)",
        r"(?:yield|farming|staking)\s+opportunities",
        r"defi\s+(?:opportunities|protocols)\s+(?:on|in|for)\s+(\w+)",
        r"(?:high|highest|top)\s+(?:apy|apr)\s+",
    ]

    # Protocols/tokens that should always trigger depth search
    SPECIFIC_ENTITIES = {
        "uniswap", "aave", "compound", "curve", "balancer", "makerdao", "lido", "yearn",
        "convex", "sushiswap", "zcash", "ethereum", "bitcoin", "polygon", "arbitrum",
        "optimism", "base", "linea", "scroll", "blast", "mantle", "mode", "zksync",
        "aura", "pendle", "frax", "lybra", "morpho", "dyad", "ether.fi", "renzo",
        "mnee",  # MNEE stablecoin
    }

    # Keywords that boost discovery intent
    DISCOVERY_KEYWORDS = {
        "yield", "apy", "apr", "farming", "opportunities", "rates", "best",
        "highest", "compare", "list", "find", "show", "opportunities",
    }

    def classify_intent(self, query: str) -> RoutingDecision:
        """
        Classify query into intent type.
        
        Args:
            query: User's query string
            
        Returns:
            RoutingDecision with intent, confidence, and routing details
        """
        query_lower = query.lower().strip()
        original_query = query

        # Check discovery patterns FIRST (highest priority)
        for pattern in self.DISCOVERY_PATTERNS:
            match = re.search(pattern, query_lower, re.IGNORECASE)
            if match:
                return RoutingDecision(
                    intent="discovery",
                    confidence=0.90,
                    query=query_lower,
                    original_query=original_query,
                    explanation=f"Matches discovery pattern",
                )

        # Check concept patterns SECOND
        for pattern in self.CONCEPT_PATTERNS:
            match = re.search(pattern, query_lower, re.IGNORECASE)
            if match:
                return RoutingDecision(
                    intent="concept",
                    confidence=0.85,
                    query=query_lower,
                    original_query=original_query,
                    explanation=f"Matches concept pattern",
                )

        # Check for specific entities THIRD (high confidence depth)
        for entity in self.SPECIFIC_ENTITIES:
            if re.search(rf"\b{entity}\b", query_lower):
                return RoutingDecision(
                    intent="depth",
                    confidence=0.95,
                    query=query_lower,
                    original_query=original_query,
                    explanation=f"Specific protocol/entity '{entity}' mentioned",
                    extracted_entity=entity,
                )

        # Check depth patterns (lowest priority)
        for pattern in self.DEPTH_PATTERNS:
            match = re.search(pattern, query_lower, re.IGNORECASE)
            if match:
                entity = match.group(1) if match.lastindex else "unknown"
                return RoutingDecision(
                    intent="depth",
                    confidence=0.80,
                    query=query_lower,
                    original_query=original_query,
                    explanation=f"Matches depth pattern for '{entity}'",
                    extracted_entity=entity,
                )

        # Default: concept if it looks like a question, discovery if it's a command
        if any(q in query_lower for q in ["?", "what", "how", "why", "explain", "describe"]):
            return RoutingDecision(
                intent="concept",
                confidence=0.50,
                query=query_lower,
                original_query=original_query,
                explanation="Detected as question (fallback)",
            )

        if any(cmd in query_lower for cmd in ["find", "show", "list", "compare", "search"]):
            return RoutingDecision(
                intent="discovery",
                confidence=0.60,
                query=query_lower,
                original_query=original_query,
                explanation="Detected as command (fallback)",
            )

        # Default to depth if all else fails
        return RoutingDecision(
            intent="depth",
            confidence=0.40,
            query=query_lower,
            original_query=original_query,
            explanation="No pattern matched (default to depth)",
        )

    def _has_discovery_keywords(self, query: str) -> bool:
        """Check if query contains discovery-related keywords."""
        return any(keyword in query.lower() for keyword in self.DISCOVERY_KEYWORDS)

    def transform_query_for_tool(self, decision: RoutingDecision) -> str:
        """
        Transform the original query for the specific tool.
        
        Examples:
        - depth: "research aave" → "aave defi protocol documentation"
        - discovery: "find yield on base" → "highest apy staking farming yield base"
        - concept: "explain privacy" → "privacy" (unchanged)
        """
        intent = decision.intent
        query = decision.original_query.lower()

        if intent == "concept":
            # For concepts, extract the concept term
            for pattern in self.CONCEPT_PATTERNS:
                match = re.search(pattern, query, re.IGNORECASE)
                if match and match.lastindex:
                    concept = match.group(1)
                    return concept
            return query

        elif intent == "depth":
            # Extract protocol name and enhance for better results
            for pattern in self.DEPTH_PATTERNS:
                match = re.search(pattern, query, re.IGNORECASE)
                if match and match.lastindex:
                    protocol = match.group(1)
                    return f"{protocol} defi protocol documentation features security"
            return query

        elif intent == "discovery":
            # Transform discovery query to optimize for semantic search
            # Remove words like "find", "show" and enhance with yield keywords
            transformed = re.sub(r"^(?:find|show|list|search)\s+", "", query, flags=re.IGNORECASE)
            transformed = re.sub(r"^(?:best|top|highest)\s+", "", transformed, flags=re.IGNORECASE)
            
            # Ensure yield-related terms are present
            if not any(kw in transformed.lower() for kw in ["yield", "apy", "apr", "farming", "staking"]):
                transformed = f"{transformed} yield opportunities"
            
            # Enhance with common search terms
            if not any(chain in transformed.lower() for chain in ["base", "ethereum", "arbitrum", "optimism", "polygon"]):
                pass  # Don't add chain if not specified
            
            return transformed

        return query

    async def get_cache_ttl(self, decision: RoutingDecision) -> int:
        """Get cache TTL (in seconds) based on intent type."""
        cache_policy = {
            "concept": 24 * 3600,      # 24 hours - static knowledge
            "depth": 6 * 3600,         # 6 hours - protocol data changes slowly
            "discovery": 3600,         # 1 hour - yields change hourly
        }
        return cache_policy.get(decision.intent, 3600)

    def log_routing_decision(self, decision: RoutingDecision) -> None:
        """Log routing decision for debugging and analytics."""
        logger.info(
            f"Routing decision: intent={decision.intent} "
            f"confidence={decision.confidence:.2f} "
            f"explanation={decision.explanation} "
            f"original='{decision.original_query}' "
            f"transformed='{decision.query}'"
        )

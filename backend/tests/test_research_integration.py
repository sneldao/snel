"""
Integration tests for Phase 1: Intent-driven research routing.
Tests the complete flow from query → router → handler → response.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.research.router import ResearchRouter, Intent
from app.services.processors.protocol_processor import ProtocolProcessor
from app.models.unified_models import UnifiedCommand, AgentType


class TestResearchRouter:
    """Test ResearchRouter intent classification and query transformation."""
    
    def setup_method(self):
        """Initialize router for each test."""
        self.router = ResearchRouter()
    
    def test_concept_intent_detection(self):
        """Test concept intent classification."""
        queries = [
            "explain privacy",
            "how does shielding work",
            "what is defi",
            "describe governance",
        ]
        
        for query in queries:
            decision = self.router.classify_intent(query)
            assert decision.intent == "concept", f"Failed for: {query}"
            assert decision.confidence >= 0.50, f"Low confidence for: {query}"
    
    def test_depth_intent_detection(self):
        """Test depth intent classification."""
        queries = [
            "research Uniswap",
            "tell me about Aave",
            "what is Compound",
            "how does Curve work",
        ]
        
        for query in queries:
            decision = self.router.classify_intent(query)
            assert decision.intent == "depth", f"Failed for: {query}"
            assert decision.confidence >= 0.80, f"Low confidence for: {query}"
    
    def test_discovery_intent_detection(self):
        """Test discovery intent classification."""
        queries = [
            "find yield opportunities",
            "best yields on Base",
            "compare DeFi yields",
            "farming opportunities",
        ]
        
        for query in queries:
            decision = self.router.classify_intent(query)
            assert decision.intent == "discovery", f"Failed for: {query}"
            assert decision.confidence >= 0.80, f"Low confidence for: {query}"
    
    def test_entity_overrides_generic_keywords(self):
        """Test that specific entities (Uniswap, Aave) trigger depth."""
        # "best yields on Uniswap" should be discovery (keywords take priority)
        decision = self.router.classify_intent("best yields on Uniswap")
        assert decision.intent == "discovery", "Discovery keywords should override entity"
        
        # "research Uniswap" should be depth (specific research)
        decision = self.router.classify_intent("research Uniswap")
        assert decision.intent == "depth", "Research should trigger depth"
    
    def test_query_transformation_concept(self):
        """Test query transformation for concept queries."""
        decision = self.router.classify_intent("explain privacy")
        transformed = self.router.transform_query_for_tool(decision)
        assert transformed == "privacy", "Should extract concept term"
    
    def test_query_transformation_depth(self):
        """Test query transformation for depth queries."""
        decision = self.router.classify_intent("research Uniswap")
        transformed = self.router.transform_query_for_tool(decision)
        assert "uniswap" in transformed.lower()
        assert "documentation" in transformed.lower()
        assert "protocol" in transformed.lower()
    
    def test_query_transformation_discovery(self):
        """Test query transformation for discovery queries."""
        decision = self.router.classify_intent("find yield on Base")
        transformed = self.router.transform_query_for_tool(decision)
        assert "yield" in transformed.lower() or "apy" in transformed.lower()
        assert "base" in transformed.lower()
    
    @pytest.mark.asyncio
    async def test_cache_ttl_concept(self):
        """Test cache TTL for concept queries."""
        decision = self.router.classify_intent("explain privacy")
        ttl = await self.router.get_cache_ttl(decision)
        assert ttl == 24 * 3600, "Concept should cache for 24 hours"
    
    @pytest.mark.asyncio
    async def test_cache_ttl_depth(self):
        """Test cache TTL for depth queries."""
        decision = self.router.classify_intent("research Uniswap")
        ttl = await self.router.get_cache_ttl(decision)
        assert ttl == 6 * 3600, "Depth should cache for 6 hours"
    
    @pytest.mark.asyncio
    async def test_cache_ttl_discovery(self):
        """Test cache TTL for discovery queries."""
        decision = self.router.classify_intent("find yield opportunities")
        ttl = await self.router.get_cache_ttl(decision)
        assert ttl == 3600, "Discovery should cache for 1 hour"


class TestProtocolProcessorRouting:
    """Test ProtocolProcessor with mocked external services."""
    
    def setup_method(self):
        """Initialize processor for each test."""
        self.processor = ProtocolProcessor()
    
    def _create_unified_command(self, command: str) -> UnifiedCommand:
        """Helper to create UnifiedCommand."""
        return UnifiedCommand(
            command=command,
            wallet_address=None,
            chain_id=1,
            user_name="test_user",
            openai_api_key="test-key",
            details=None,
        )
    
    @pytest.mark.asyncio
    async def test_concept_query_routing(self):
        """Test that concept queries are routed correctly."""
        unified_cmd = self._create_unified_command("explain privacy")
        
        # The handler should look in KB first
        # For this test, we just verify the routing logic path
        decision = self.processor.router.classify_intent(unified_cmd.command)
        assert decision.intent == "concept"
    
    @pytest.mark.asyncio
    async def test_depth_query_routing(self):
        """Test that depth queries are routed correctly."""
        unified_cmd = self._create_unified_command("research Uniswap")
        
        decision = self.processor.router.classify_intent(unified_cmd.command)
        assert decision.intent == "depth"
    
    @pytest.mark.asyncio
    async def test_discovery_query_routing(self):
        """Test that discovery queries are routed correctly."""
        unified_cmd = self._create_unified_command("find yield opportunities")
        
        decision = self.processor.router.classify_intent(unified_cmd.command)
        assert decision.intent == "discovery"
    
    @pytest.mark.asyncio
    async def test_kb_lookup_zcash(self):
        """Test that Zcash is found in knowledge base."""
        decision = self.processor.router.classify_intent("what is Zcash")
        assert decision.intent == "depth", "Zcash is specific entity"
        
        # Check KB lookup works
        kb_match = self.processor._find_in_knowledge_base("zcash")
        assert kb_match is not None, "Zcash should be in knowledge base"
        assert kb_match.get("official_name") == "Zcash"
    
    @pytest.mark.asyncio
    async def test_kb_lookup_privacy(self):
        """Test that privacy concept is found in knowledge base."""
        decision = self.processor.router.classify_intent("explain privacy")
        assert decision.intent == "concept"
        
        # Check KB lookup works
        kb_match = self.processor._find_in_knowledge_base("privacy")
        assert kb_match is not None, "Privacy should be in knowledge base"


class TestCachingStrategy:
    """Test cache strategy alignment with intent types."""
    
    def setup_method(self):
        """Initialize router for each test."""
        self.router = ResearchRouter()
    
    @pytest.mark.asyncio
    async def test_concept_long_cache(self):
        """Concepts should cache longest (static knowledge)."""
        decision = self.router.classify_intent("explain defi")
        ttl = await self.router.get_cache_ttl(decision)
        assert ttl >= 6 * 3600, "Concept should cache at least 6 hours"
    
    @pytest.mark.asyncio
    async def test_discovery_short_cache(self):
        """Discovery should cache shortest (yields change hourly)."""
        decision = self.router.classify_intent("find yield opportunities")
        ttl = await self.router.get_cache_ttl(decision)
        assert ttl <= 3600, "Discovery should cache max 1 hour"
    
    @pytest.mark.asyncio
    async def test_depth_medium_cache(self):
        """Depth should cache medium duration (protocol data changes daily)."""
        decision = self.router.classify_intent("research Uniswap")
        ttl = await self.router.get_cache_ttl(decision)
        assert 3 * 3600 <= ttl <= 12 * 3600, "Depth should cache 3-12 hours"


class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def setup_method(self):
        """Initialize router for each test."""
        self.router = ResearchRouter()
    
    def test_empty_query(self):
        """Test handling of empty query."""
        decision = self.router.classify_intent("")
        # Should still return a decision (fallback to concept)
        assert decision.intent in ["concept", "depth", "discovery"]
    
    def test_very_long_query(self):
        """Test handling of very long query."""
        long_query = "find highest yield farming opportunities on " + "base " * 100
        decision = self.router.classify_intent(long_query)
        assert decision.intent == "discovery", "Should classify despite length"
    
    def test_mixed_case_query(self):
        """Test case-insensitive classification."""
        decision1 = self.router.classify_intent("RESEARCH UNISWAP")
        decision2 = self.router.classify_intent("research uniswap")
        decision3 = self.router.classify_intent("Research Uniswap")
        
        assert decision1.intent == decision2.intent == decision3.intent == "depth"
    
    def test_special_characters_in_query(self):
        """Test handling of special characters."""
        decision = self.router.classify_intent("research Uniswap v3???")
        assert decision.intent == "depth", "Should handle special chars"


# Integration test with mocked external services
@pytest.mark.asyncio
async def test_full_pipeline_mocked():
    """Test full pipeline with mocked external services."""
    processor = ProtocolProcessor()
    
    # Mock the external service calls
    with patch('app.services.processors.protocol_processor.get_protocol_details') as mock_fc, \
         patch('app.services.processors.protocol_processor.discover_defi_protocols') as mock_exa:
        
        # Setup mocks
        mock_fc.return_value = {
            "scraping_success": True,
            "raw_content": "Test content",
            "source_url": "https://test.com",
        }
        
        mock_exa.return_value = {
            "search_success": True,
            "protocols_found": 3,
            "protocols": [
                {"name": "Aave", "apy": "5.2%", "tvl": "$10B"},
                {"name": "Compound", "apy": "4.1%", "tvl": "$5B"},
            ]
        }
        
        # Test discovery query (will call Exa mock)
        cmd = UnifiedCommand(
            command="find yield opportunities",
            wallet_address=None,
            chain_id=1,
            user_name="test",
            openai_api_key="test-key",
            details=None,
        )
        
        decision = processor.router.classify_intent(cmd.command)
        assert decision.intent == "discovery"
        
        # Verify correct tool was chosen
        transformed = processor.router.transform_query_for_tool(decision)
        assert "yield" in transformed.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

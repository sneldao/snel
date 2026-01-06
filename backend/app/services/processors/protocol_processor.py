"""
Protocol research command processor.
Handles protocol research and analysis operations with built-in knowledge base.
Follows ENHANCEMENT FIRST principle: uses existing contextual processor knowledge as fallback.
"""
import logging
import re
import os
from typing import Optional, Tuple, Any

from app.models.unified_models import (
    UnifiedCommand, UnifiedResponse, AgentType, CommandType
)
from app.services.error_guidance_service import ErrorContext
from app.services.external.firecrawl_service import (
    get_protocol_details,
)
from app.services.external.firecrawl_client import FirecrawlClient, FirecrawlError
from app.services.research.router import ResearchRouter, Intent
from app.services.research.research_logger import research_logger
from app.services.knowledge_base import get_protocol_kb, ProtocolMetrics
from app.services.analysis import ProtocolAnalyzer
from app.services.protocol import ProtocolResponseBuilder
from .base_processor import BaseProcessor

logger = logging.getLogger(__name__)

# Knowledge base is now managed by the ProtocolKnowledgeBase service
# This provides: static entries, dynamic metrics, analytics, and structured schema


class ProtocolProcessor(BaseProcessor):
    """Processes protocol research commands with intelligent routing."""
    
    def __init__(self, **kwargs):
        """Initialize protocol processor with router."""
        super().__init__(**kwargs)
        self.router = ResearchRouter()
    
    async def process(self, unified_command: UnifiedCommand) -> UnifiedResponse:
        """
        Process protocol research command with intelligent routing.
        
        Routes to appropriate tool based on intent:
        - concept: Built-in knowledge base
        - depth: Firecrawl deep research
        - discovery: Exa opportunity finding
        
        ENHANCEMENT FIRST: Uses built-in knowledge base when available
        """
        try:
            logger.info(f"Processing protocol research: {unified_command.command}")
            
            # Classify intent and get routing decision
            routing_decision = self.router.classify_intent(unified_command.command)
            self.router.log_routing_decision(routing_decision)
            
            # Route based on intent
            if routing_decision.intent == "concept":
                return await self._handle_concept_query(routing_decision, unified_command)
            elif routing_decision.intent == "depth":
                return await self._handle_depth_query(routing_decision, unified_command)
            elif routing_decision.intent == "discovery":
                return await self._handle_discovery_query(routing_decision, unified_command)
            else:
                # Fallback
                return self._create_error_response(
                    "Unable to understand your research request",
                    AgentType.PROTOCOL_RESEARCH,
                    f"Unexpected intent: {routing_decision.intent}"
                )
            
        except Exception as e:
            logger.exception("Error processing protocol research")
            return self._create_error_response(
                "Protocol research service is temporarily unavailable",
                AgentType.PROTOCOL_RESEARCH,
                str(e)
            )
    
    async def _handle_concept_query(
        self,
        routing_decision,
        unified_command: UnifiedCommand
    ) -> UnifiedResponse:
        """Handle concept/educational queries (knowledge base first)."""
        try:
            concept_name = self.router.transform_query_for_tool(routing_decision)
            logger.info(f"Handling concept query: {concept_name}")
            
            # Check knowledge base
            kb_result = await self._lookup_kb(concept_name)
            if kb_result:
                matched_key, entry = kb_result
                logger.info(f"Found '{concept_name}' in knowledge base as '{matched_key}'")
                content = ProtocolResponseBuilder.from_knowledge_base(matched_key, entry)
                return self._create_success_response(
                    content=content,
                    agent_type=AgentType.PROTOCOL_RESEARCH,
                    metadata={
                        "source": "knowledge_base",
                        "protocol": matched_key,
                        "knowledge_base_match": True,
                        "research_details": {
                            "source": "snel_built_in_knowledge_base",
                            "guaranteed_accuracy": True,
                        }
                    }
                )
            
            # Fallback to AI for unknown concepts
            logger.info(f"Concept '{concept_name}' not in KB, using AI fallback")
            return await self._handle_research_error(
                concept_name,
                unified_command.openai_api_key,
                "concept"
            )
            
        except Exception as e:
            logger.error(f"Error handling concept query: {e}")
            return await self._handle_research_error(
                routing_decision.original_query,
                unified_command.openai_api_key,
                "concept",
                error=e
            )
    
    async def _handle_depth_query(
        self,
        routing_decision,
        unified_command: UnifiedCommand
    ) -> UnifiedResponse:
        """Handle depth queries (specific protocol research)."""
        # Determine research mode: quick (KB + AI) or deep (KB + Firecrawl + AI)
        research_mode = unified_command.research_mode or "quick"
        logger.info(f"Protocol research mode: {research_mode}")
        
        # Start timer for duration tracking
        start_time = research_logger.start_timer()
        
        try:
            # Use extracted entity name for KB lookup, not transformed query
            protocol_name = routing_decision.extracted_entity or self.router.transform_query_for_tool(routing_decision)
            logger.info(f"Handling depth query: {protocol_name} (mode: {research_mode}, extracted: {routing_decision.extracted_entity})")
            
            # Try knowledge base first with the extracted entity name (both modes)
            kb_result = await self._lookup_kb(protocol_name)
            if kb_result:
                matched_key, entry = kb_result
                logger.info(f"Found '{protocol_name}' in knowledge base as '{matched_key}'")
                metrics = self._get_protocol_metrics(matched_key)
                content = ProtocolResponseBuilder.from_knowledge_base(matched_key, entry, metrics)
                
                # Log successful KB lookup
                duration_ms = research_logger.calculate_duration_ms(start_time)
                research_logger.log_research(
                    protocol_name=matched_key,
                    research_mode=research_mode,
                    source="knowledge_base",
                    duration_ms=duration_ms,
                    user_id=unified_command.user_name,
                    success=True,
                )
                
                return self._create_success_response(
                    content=content,
                    agent_type=AgentType.PROTOCOL_RESEARCH,
                    metadata={
                        "source": "knowledge_base",
                        "protocol": matched_key,
                        "research_mode": research_mode,
                        "knowledge_base_match": True,
                        "research_details": {
                            "source": "snel_built_in_knowledge_base",
                            "guaranteed_accuracy": True,
                            "duration_ms": duration_ms,
                        }
                    }
                )
            
            # Route based on research mode
            if research_mode == "quick":
                # Quick mode: KB failed, fall back to AI general knowledge
                logger.info(f"Quick research: KB not found, using AI fallback for {protocol_name}")
                return await self._handle_research_error(
                    protocol_name,
                    unified_command.openai_api_key,
                    "quick",
                    user_id=unified_command.user_name,
                    start_time=start_time
                )
            else:
                # Deep mode: Use Firecrawl for detailed research
                return await self._handle_deep_research(
                    protocol_name,
                    unified_command.openai_api_key,
                    user_id=unified_command.user_name,
                    start_time=start_time
                )
                
        except Exception as e:
            logger.warning(f"Research query failed: {e}")
            protocol_name = routing_decision.original_query
            return await self._handle_research_error(
                protocol_name,
                unified_command.openai_api_key,
                research_mode,
                user_id=unified_command.user_name,
                start_time=start_time,
                error=e
            )
    
    async def _handle_deep_research(
        self,
        protocol_name: str,
        openai_key: Optional[str],
        user_id: Optional[str] = None,
        start_time: Optional[float] = None,
    ) -> UnifiedResponse:
        """
        Perform deep research using Firecrawl Search+Scrape + AI analysis.
        Only called when quick research (KB + AI) is insufficient.
        """
        try:
            logger.info(f"Starting deep research for {protocol_name} via Firecrawl")
            from app.core.dependencies import get_service_container
            from app.config.settings import get_settings
            
            container = get_service_container(get_settings())
            firecrawl_client = container.get_firecrawl_client()
            
            scrape_result = await get_protocol_details(
                firecrawl_client,
                protocol_name,
                use_llm_extraction=True,
            )
            
            if scrape_result.get("scraping_success", False):
                # Analyze scraped content with AI
                openai_key = openai_key or os.getenv("OPENAI_API_KEY")
                logger.info(f"Starting AI analysis for {protocol_name}")
                
                analyzer = ProtocolAnalyzer(openai_key)
                ai_result = await analyzer.analyze_scraped_content(
                    protocol_name=protocol_name,
                    raw_content=scrape_result.get("raw_content", ""),
                    source_url=scrape_result.get("source_url", ""),
                )
                
                content = ProtocolResponseBuilder.from_firecrawl(protocol_name, scrape_result, ai_result)
                
                # Calculate duration and cost
                duration_ms = research_logger.calculate_duration_ms(start_time) if start_time else 0
                source_urls = scrape_result.get("full_response", {}).get("urls", [])
                firecrawl_cost = research_logger.calculate_firecrawl_cost(len(source_urls))
                
                # Log successful deep research
                research_logger.log_research(
                    protocol_name=protocol_name,
                    research_mode="deep",
                    source="firecrawl",
                    duration_ms=duration_ms,
                    user_id=user_id,
                    firecrawl_cost=firecrawl_cost,
                    source_urls=source_urls,
                    success=True,
                )
                
                return self._create_success_response(
                    content=content,
                    agent_type=AgentType.PROTOCOL_RESEARCH,
                    metadata={
                        "parsed_command": {
                            "protocol": protocol_name,
                            "command_type": "protocol_research"
                        },
                        "research_details": {
                            "scraping_success": True,
                            "source": "firecrawl",
                            "research_mode": "deep",
                            "duration_ms": duration_ms,
                            "firecrawl_cost": firecrawl_cost,
                        }
                    }
                )
            else:
                error_msg = scrape_result.get("error", "Firecrawl scraping failed")
                logger.warning(f"Deep research failed for {protocol_name}: {error_msg}")
                raise FirecrawlError(error_msg)
                
        except FirecrawlError as e:
            logger.warning(f"Deep research (Firecrawl) failed: {e}, falling back to AI")
            return await self._handle_research_error(
                protocol_name,
                openai_key,
                "deep",
                error=e
            )
    
    async def _handle_discovery_query(
        self,
        routing_decision,
        unified_command: UnifiedCommand
    ) -> UnifiedResponse:
        """Handle discovery queries (opportunity finding with Exa)."""
        try:
            query = self.router.transform_query_for_tool(routing_decision)
            logger.info(f"Handling discovery query: {query}")
            
            # Get Exa client with optional caching
            from app.core.dependencies import get_service_container
            from app.config.settings import get_settings
            
            container = get_service_container(get_settings())
            exa_client = container.get_exa_client()
            
            # Use Exa for opportunity discovery
            exa_result = await exa_client.search_opportunities(
                query=query,
                max_results=5,
                cache=True,
            )
            
            if exa_result.get("search_success", False) and exa_result.get("protocols"):
                protocols = exa_result.get("protocols", [])
                
                content = {
                    "message": f"Found {len(protocols)} DeFi opportunity/opportunities",
                    "type": "discovery_result",
                    "opportunities": protocols,
                    "summary": {
                        "count": exa_result.get("protocols_found", 0),
                        "yield_opportunities": exa_result.get("yield_opportunities", 0),
                        "best_apy": exa_result.get("best_apy_found", "Unknown"),
                    },
                    "requires_transaction": False,
                }
                
                return self._create_success_response(
                    content=content,
                    agent_type=AgentType.PROTOCOL_RESEARCH,
                    metadata={
                        "parsed_command": {
                            "query": routing_decision.original_query,
                            "command_type": "opportunity_discovery"
                        },
                        "research_details": {
                            "tool": "exa",
                            "protocols_found": exa_result.get("protocols_found", 0),
                            "yield_opportunities": exa_result.get("yield_opportunities", 0),
                        }
                    }
                )
            else:
                error_msg = exa_result.get("error", "No protocols found")
                logger.warning(f"Exa discovery failed: {error_msg}")
                return self._create_error_response(
                    f"Unable to find opportunities: {error_msg}",
                    AgentType.PROTOCOL_RESEARCH,
                    error_msg
                )
            
        except Exception as e:
            logger.error(f"Error handling discovery query: {e}")
            return self._create_error_response(
                "Unable to search for opportunities",
                AgentType.PROTOCOL_RESEARCH,
                str(e)
            )
    
    async def _lookup_kb(self, protocol_name: str) -> Optional[Tuple[str, Any]]:
        """
        Look up protocol in knowledge base.
        Single source of truth for KB queries.
        
        Args:
            protocol_name: Name of the protocol to look up
            
        Returns:
            Tuple of (matched_key, ProtocolEntry) or None if not found
        """
        kb = get_protocol_kb()
        return kb.get(protocol_name)
    
    def _get_protocol_metrics(self, protocol_name: str) -> Optional[ProtocolMetrics]:
        """
        Get dynamic metrics for a protocol from KB.
        
        Args:
            protocol_name: Name of the protocol
            
        Returns:
            ProtocolMetrics or None if not available
        """
        kb = get_protocol_kb()
        return kb.get_metrics(protocol_name)
    
    async def _handle_research_error(
        self,
        protocol_name: str,
        openai_key: Optional[str],
        query_type: str,
        user_id: Optional[str] = None,
        start_time: Optional[float] = None,
        error: Optional[Exception] = None,
    ) -> UnifiedResponse:
        """
        Centralized error handling for research queries.
        Falls back to AI general knowledge when primary research fails.
        
        Args:
            protocol_name: Name of the protocol
            openai_key: Optional OpenAI API key
            query_type: Type of query ('quick', 'deep', 'concept')
            user_id: Optional user ID for logging
            start_time: Optional start time for duration calculation
            error: Optional exception that triggered the fallback
            
        Returns:
            UnifiedResponse with AI fallback or error message
        """
        try:
            openai_key = openai_key or os.getenv("OPENAI_API_KEY")
            if not openai_key:
                # Log failed research
                duration_ms = research_logger.calculate_duration_ms(start_time) if start_time else 0
                research_logger.log_research(
                    protocol_name=protocol_name,
                    research_mode=query_type,
                    source="ai_general",
                    duration_ms=duration_ms,
                    user_id=user_id,
                    success=False,
                    error_message="OpenAI API key not available",
                )
                
                return self._create_error_response(
                    f"I couldn't find information about {protocol_name} and the research service is unavailable. Please try a different protocol or check the spelling.",
                    AgentType.PROTOCOL_RESEARCH,
                    "No OpenAI key available"
                )
            
            logger.info(f"Using AI fallback for {protocol_name} ({query_type} query)")
            analyzer = ProtocolAnalyzer(openai_key)
            ai_result = await analyzer.generate_fallback_summary(protocol_name)
            
            if ai_result.get("analysis_success"):
                content = ProtocolResponseBuilder.from_ai_fallback(protocol_name, ai_result)
                
                # Log successful AI fallback
                duration_ms = research_logger.calculate_duration_ms(start_time) if start_time else 0
                research_logger.log_research(
                    protocol_name=protocol_name,
                    research_mode=query_type,
                    source="ai_general",
                    duration_ms=duration_ms,
                    user_id=user_id,
                    success=True,
                )
                
                return self._create_success_response(
                    content=content,
                    agent_type=AgentType.PROTOCOL_RESEARCH,
                    metadata={
                        "source": "ai_fallback",
                        "protocol": protocol_name,
                        "query_type": query_type,
                        "duration_ms": duration_ms,
                        "note": "Using AI general knowledge (KB and web research unavailable)"
                    }
                )
            else:
                error_msg = ai_result.get("error", "Unable to generate response")
                logger.error(f"AI fallback failed for {protocol_name}: {error_msg}")
                
                # Log failed AI fallback
                duration_ms = research_logger.calculate_duration_ms(start_time) if start_time else 0
                research_logger.log_research(
                    protocol_name=protocol_name,
                    research_mode=query_type,
                    source="ai_general",
                    duration_ms=duration_ms,
                    user_id=user_id,
                    success=False,
                    error_message=error_msg,
                )
                
                return self._create_error_response(
                    f"Unable to find information about {protocol_name}",
                    AgentType.PROTOCOL_RESEARCH,
                    error_msg
                )
            
        except Exception as e:
            logger.exception(f"Error handling research fallback for {protocol_name}")
            
            # Log exception
            duration_ms = research_logger.calculate_duration_ms(start_time) if start_time else 0
            research_logger.log_research(
                protocol_name=protocol_name,
                research_mode=query_type,
                source="ai_general",
                duration_ms=duration_ms,
                user_id=user_id,
                success=False,
                error_message=str(e),
            )
            
            return self._create_error_response(
                f"Unable to answer questions about {protocol_name} at this time",
                AgentType.PROTOCOL_RESEARCH,
                str(e)
            )
"""
Protocol research command processor.
Handles protocol research and analysis operations with built-in knowledge base.
Follows ENHANCEMENT FIRST principle: uses existing contextual processor knowledge as fallback.
"""
import logging
import re
import os
from typing import Union
from openai import AsyncOpenAI

from app.models.unified_models import (
    UnifiedCommand, UnifiedResponse, AgentType, CommandType
)
from app.services.error_guidance_service import ErrorContext
from app.services.external.firecrawl_service import (
    get_protocol_details,
    analyze_protocol_with_ai,
    answer_protocol_question,
)
from app.services.external.firecrawl_client import FirecrawlClient, FirecrawlError
from app.services.research.router import ResearchRouter, Intent
from app.services.knowledge_base import get_protocol_kb, ProtocolMetrics
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
            kb = get_protocol_kb()
            kb_result = kb.get(concept_name)
            if kb_result:
                matched_key, entry = kb_result
                logger.info(f"Found '{concept_name}' in knowledge base as '{matched_key}'")
                return self._create_response_from_knowledge(matched_key, entry)
            
            # Fallback to AI for unknown concepts
            logger.info(f"Concept '{concept_name}' not in KB, using AI fallback")
            return await self._create_ai_fallback_response(
                concept_name,
                unified_command.openai_api_key
            )
            
        except Exception as e:
            logger.error(f"Error handling concept query: {e}")
            return self._create_error_response(
                "Unable to answer that question",
                AgentType.PROTOCOL_RESEARCH,
                str(e)
            )
    
    async def _handle_depth_query(
        self,
        routing_decision,
        unified_command: UnifiedCommand
    ) -> UnifiedResponse:
        """Handle depth queries (specific protocol research)."""
        try:
            # Use extracted entity name for KB lookup, not transformed query
            protocol_name = routing_decision.extracted_entity or self.router.transform_query_for_tool(routing_decision)
            logger.info(f"Handling depth query: {protocol_name} (extracted: {routing_decision.extracted_entity})")
            
            # Try knowledge base first with the extracted entity name
            kb = get_protocol_kb()
            kb_result = kb.get(protocol_name)
            if kb_result:
                matched_key, entry = kb_result
                logger.info(f"Found '{protocol_name}' in knowledge base as '{matched_key}'")
                return self._create_response_from_knowledge(matched_key, entry)
            
            # Use Firecrawl for detailed research
            logger.info(f"Attempting Firecrawl for {protocol_name}")
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
                # Analyze with AI
                openai_key = unified_command.openai_api_key or os.getenv("OPENAI_API_KEY")
                logger.info(f"Starting AI analysis for {protocol_name}")
                
                ai_result = await analyze_protocol_with_ai(
                    protocol_name=protocol_name,
                    raw_content=scrape_result.get("raw_content", ""),
                    source_url=scrape_result.get("source_url", ""),
                    openai_api_key=openai_key,
                )
                
                result = {**scrape_result, **ai_result}
                
                content = {
                    "message": f"Research complete for {protocol_name}",
                    "type": "protocol_research_result",
                    "protocol_name": protocol_name,
                    "ai_summary": result.get("ai_summary", ""),
                    "source_url": result.get("source_url", ""),
                    "raw_content": result.get("raw_content", ""),
                    "analysis_success": result.get("analysis_success", False),
                    "requires_transaction": False,
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
                            "scraping_success": True,
                            "source": "firecrawl",
                        }
                    }
                )
            else:
                logger.warning(f"Firecrawl scraping failed for {protocol_name}")
                raise FirecrawlError(scrape_result.get("error", "Unknown error"))
                
        except (FirecrawlError, Exception) as e:
            logger.warning(f"Depth research failed: {e}, falling back to AI")
            protocol_name = routing_decision.original_query
            return await self._create_ai_fallback_response(
                protocol_name,
                unified_command.openai_api_key
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
    
    def _create_response_from_knowledge(self, protocol_name: str, entry) -> UnifiedResponse:
        """Create response from built-in knowledge base using ProtocolEntry."""
        kb = get_protocol_kb()
        
        # Get metrics if available (dynamic data from Firecrawl cache)
        metrics = kb.get_metrics(protocol_name)
        
        # Convert ProtocolEntry to response dict
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
        
        return self._create_success_response(
            content=content,
            agent_type=AgentType.PROTOCOL_RESEARCH,
            metadata={
                "source": "knowledge_base",
                "protocol": protocol_name,
                "knowledge_base_match": True,
                "research_details": {
                    "source": "snel_built_in_knowledge_base",
                    "guaranteed_accuracy": True,
                    "last_verified": entry.last_verified.isoformat() if entry.last_verified else None,
                    "aliases": entry.aliases,
                }
            }
        )
    
    async def _create_ai_fallback_response(self, protocol_name: str, openai_key: Union[str, None]) -> UnifiedResponse:
        """Create response using AI when Firecrawl fails and knowledge base is empty."""
        try:
            openai_key = openai_key or os.getenv("OPENAI_API_KEY")
            if not openai_key:
                return self._create_error_response(
                    f"I couldn't find information about {protocol_name} and the research service is unavailable. Please try a different protocol or check the spelling.",
                    AgentType.PROTOCOL_RESEARCH,
                    "No OpenAI key available"
                )
            
            client = AsyncOpenAI(api_key=openai_key)
            
            # Use AI to provide general knowledge about the protocol
            prompt = f"""
You are SNEL, a DeFi expert. The user asked about {protocol_name}.
Your web research failed, but you can still provide useful general knowledge about this protocol if you know about it.

Provide a helpful response about {protocol_name} in this format:
- Brief explanation (1-2 sentences)
- Key features (as a list)
- Type of protocol
- How it relates to DeFi or privacy if applicable

Keep it concise and accurate. If you don't have reliable information, say so clearly.
"""
            
            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "You are SNEL, a knowledgeable DeFi assistant. Provide accurate information about blockchain protocols."
                    },
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.3  # Lower temperature for factual accuracy
            )
            
            ai_response = response.choices[0].message.content
            
            content = {
                "message": ai_response,
                "type": "protocol_research_result",
                "protocol_name": protocol_name,
                "ai_summary": ai_response,
                "analysis_quality": "medium",
                "analysis_success": True,
                "from_ai_fallback": True
            }
            
            return self._create_success_response(
                content=content,
                agent_type=AgentType.PROTOCOL_RESEARCH,
                metadata={
                    "source": "ai_fallback",
                    "protocol": protocol_name,
                    "note": "Web research unavailable, using AI general knowledge"
                }
            )
            
        except Exception as e:
            logger.exception(f"AI fallback failed for {protocol_name}")
            return self._create_error_response(
                f"AI fallback failed: {str(e)}",
                AgentType.PROTOCOL_RESEARCH,
                str(e)
            )
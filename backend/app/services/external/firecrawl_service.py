"""
Protocol research service using Firecrawl API.
Handles scraping, searching, and AI analysis of DeFi protocols.
Note: AI analysis moved to app.services.analysis.ProtocolAnalyzer
"""
import logging
import os
from typing import Dict, Any, Optional, List
from openai import AsyncOpenAI

from app.services.external.firecrawl_client import FirecrawlClient, FirecrawlError

logger = logging.getLogger(__name__)


# LLM extraction schema for protocol information
PROTOCOL_EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "protocol_name": {
            "type": "string",
            "description": "Official name of the protocol"
        },
        "protocol_type": {
            "type": "string",
            "description": "Type of protocol (DEX, Lending, Staking, etc.)",
        },
        "description": {
            "type": "string",
            "description": "Brief description of what the protocol does"
        },
        "key_features": {
            "type": "array",
            "items": {"type": "string"},
            "description": "List of key features"
        },
        "tvl": {
            "type": "string",
            "description": "Total Value Locked if available"
        },
        "security_audits": {
            "type": "string",
            "description": "Security audit information"
        },
    },
    "required": ["protocol_name", "protocol_type", "description"]
}


async def get_protocol_details(
    client: FirecrawlClient,
    protocol_name: str,
    use_llm_extraction: bool = True,
) -> Dict[str, Any]:
    """
    Get detailed information about a DeFi protocol.
    
    Args:
        client: FirecrawlClient instance
        protocol_name: Name of the protocol to research
        use_llm_extraction: Whether to use LLM for structured extraction
        
    Returns:
        Dictionary with protocol details
    """
    try:
        query = f"{protocol_name} defi protocol documentation features"
        
        results = await client.search_and_scrape(
            query,
            max_urls=3,
            use_llm_extraction=use_llm_extraction,
            extraction_schema=PROTOCOL_EXTRACTION_SCHEMA if use_llm_extraction else None,
        )
        
        if not results:
            return {
                "error": f"No information found for {protocol_name}",
                "scraping_success": False,
                "protocol_name": protocol_name,
            }
        
        # Use first result (best prioritized URL)
        best_result = results[0]
        
        return {
            "protocol_name": protocol_name,
            "scraping_success": True,
            "source_url": best_result.get("url", ""),
            "raw_content": best_result.get("markdown", ""),
            "extracted_data": best_result.get("llm_extraction_output", {}),
            "full_response": best_result,
        }
        
    except FirecrawlError as e:
        logger.error(f"Firecrawl error researching {protocol_name}: {e}")
        return {
            "error": str(e),
            "scraping_success": False,
            "protocol_name": protocol_name,
        }
    except Exception as e:
        logger.error(f"Unexpected error researching {protocol_name}: {e}")
        return {
            "error": f"Unexpected error: {str(e)}",
            "scraping_success": False,
            "protocol_name": protocol_name,
        }


# NOTE: analyze_protocol_with_ai() has been consolidated into ProtocolAnalyzer service
# See: app/services/analysis/protocol_analyzer.py
# This function is deprecated but kept for backward compatibility if needed elsewhere


async def answer_protocol_question_with_client(
    client: FirecrawlClient,
    protocol_name: str,
    question: str,
    openai_api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Answer follow-up questions about a protocol using general knowledge.
    Falls back to OpenAI without scraped content when insufficient context.
    
    Args:
        client: FirecrawlClient instance (not used, kept for compatibility)
        protocol_name: Name of the protocol
        question: User's question
        openai_api_key: OpenAI API key
        
    Returns:
        Dictionary with answer
    """
    if not openai_api_key:
        openai_api_key = os.getenv("OPENAI_API_KEY")
    
    if not openai_api_key:
        return {
            "error": "OpenAI API key not configured",
            "answer": "Unable to answer questions without OpenAI configuration.",
            "success": False,
        }
    
    try:
        client_openai = AsyncOpenAI(api_key=openai_api_key)
        
        prompt = f"""You are a DeFi expert. Answer this question about {protocol_name}:

QUESTION: {question}

Provide a clear, accurate answer (2-4 sentences) based on your knowledge of DeFi and {protocol_name}.
"""
        
        response = await client_openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": f"You are a DeFi expert providing helpful information about {protocol_name}.",
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=300,
            temperature=0.3,
        )
        
        answer = response.choices[0].message.content
        
        return {
            "protocol_name": protocol_name,
            "question": question,
            "answer": answer,
            "success": True,
        }
        
    except Exception as e:
        logger.error(f"Error answering question about {protocol_name}: {e}")
        return {
            "error": str(e),
            "answer": "I encountered an error processing your question. Please try again.",
            "success": False,
        }


async def get_multi_protocol_details(
    client: FirecrawlClient,
    protocol_names: List[str],
    use_llm_extraction: bool = True,
) -> Dict[str, Any]:
    """
    Get details for multiple protocols efficiently using batch processing.
    
    Args:
        client: FirecrawlClient instance
        protocol_names: List of protocol names
        use_llm_extraction: Whether to use LLM extraction
        
    Returns:
        Dictionary with aggregated results
    """
    if not protocol_names:
        return {
            "error": "No protocols specified",
            "scraping_success": False,
            "protocols_scraped": 0,
            "protocols": [],
        }
    
    protocols = []
    successful_scrapes = 0
    
    for name in protocol_names:
        try:
            result = await get_protocol_details(
                client,
                name,
                use_llm_extraction=use_llm_extraction,
            )
            
            protocols.append(result)
            
            if result.get("scraping_success"):
                successful_scrapes += 1
                
        except Exception as e:
            logger.error(f"Error researching {name}: {e}")
            protocols.append({
                "protocol_name": name,
                "error": str(e),
                "scraping_success": False,
            })
    
    return {
        "scraping_success": successful_scrapes > 0,
        "protocols_scraped": successful_scrapes,
        "protocols": protocols,
    }


# Backward compatibility wrapper for existing API endpoints
async def answer_protocol_question(
    protocol_name: str,
    question: str,
    raw_content: str,
    openai_api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Backward-compatible wrapper for existing API endpoints.
    Uses provided raw_content instead of fetching from Firecrawl.
    """
    if not openai_api_key:
        openai_api_key = os.getenv("OPENAI_API_KEY")
    
    if not openai_api_key:
        return {
            "error": "OpenAI API key not configured",
            "answer": "Unable to answer questions without OpenAI configuration.",
            "success": False,
        }
    
    if not raw_content or len(raw_content.strip()) < 50:
        return {
            "error": "Insufficient content",
            "answer": "I don't have enough information to answer that question.",
            "success": False,
        }
    
    try:
        client_openai = AsyncOpenAI(api_key=openai_api_key)
        
        prompt = f"""
You are a DeFi expert. Answer this question about {protocol_name} based ONLY on the provided content.

CONTENT:
{raw_content[:3000]}

QUESTION: {question}

Provide a clear, accurate answer (2-4 sentences). If the information isn't in the content, say so clearly.
"""
        
        response = await client_openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": f"You are a DeFi expert answering questions about {protocol_name}. Use only the provided content.",
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=300,
            temperature=0.3,
        )
        
        answer = response.choices[0].message.content
        
        return {
            "protocol_name": protocol_name,
            "question": question,
            "answer": answer,
            "success": True,
        }
        
    except Exception as e:
        logger.error(f"Error answering question about {protocol_name}: {e}")
        return {
            "error": str(e),
            "answer": "I encountered an error processing your question. Please try again.",
            "success": False,
        }

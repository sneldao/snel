"""Protocol analysis using OpenAI."""
import logging
import os
from typing import Dict, Any, Optional
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


class ProtocolAnalyzer:
    """Single source of truth for all protocol AI analysis."""
    
    def __init__(self, openai_api_key: Optional[str] = None):
        """Initialize with OpenAI API key."""
        self.openai_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        if not self.openai_key:
            raise ValueError("OpenAI API key not configured")
    
    async def analyze_scraped_content(
        self,
        protocol_name: str,
        raw_content: str,
        source_url: str = "",
    ) -> Dict[str, Any]:
        """
        Analyze protocol content scraped from web.
        Used when Firecrawl returns raw content that needs AI synthesis.
        
        Args:
            protocol_name: Name of the protocol
            raw_content: Raw scraped content (markdown)
            source_url: URL where content was scraped
            
        Returns:
            Dictionary with ai_summary and analysis metadata
        """
        if not raw_content or len(raw_content.strip()) < 100:
            return {
                "error": "Insufficient content for analysis",
                "analysis_success": False,
                "protocol_name": protocol_name,
            }
        
        try:
            client = AsyncOpenAI(api_key=self.openai_key)
            
            prompt = f"""
You are a DeFi expert analyzing protocol documentation. Extract and summarize the following information about {protocol_name}:

CONTENT:
{raw_content[:3000]}

Provide a structured analysis with:
1. Protocol Type (DEX, Lending, Staking, etc.)
2. Key Features (as a list)
3. Security Status (Audited/Not Audited/Unknown)
4. Financial Metrics (TVL, APY, etc. if available)
5. Brief Summary (2-3 sentences)

Keep the response concise and factual.
"""
            
            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a DeFi expert. Provide accurate, structured analysis of blockchain protocols.",
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=500,
                temperature=0.3,  # Low temperature for factual accuracy
            )
            
            ai_summary = response.choices[0].message.content
            
            return {
                "protocol_name": protocol_name,
                "ai_summary": ai_summary,
                "source_url": source_url,
                "analysis_success": True,
            }
            
        except Exception as e:
            logger.error(f"AI analysis error for {protocol_name}: {e}")
            return {
                "error": f"Analysis failed: {str(e)}",
                "analysis_success": False,
                "protocol_name": protocol_name,
            }
    
    async def generate_fallback_summary(
        self,
        protocol_name: str,
    ) -> Dict[str, Any]:
        """
        Generate protocol summary using only AI general knowledge.
        Used when KB lookup fails and no scraped content available.
        
        Args:
            protocol_name: Name of the protocol
            
        Returns:
            Dictionary with ai_summary from general knowledge
        """
        try:
            client = AsyncOpenAI(api_key=self.openai_key)
            
            prompt = f"""
You are SNEL, a DeFi expert. The user asked about {protocol_name}.

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
            
            return {
                "protocol_name": protocol_name,
                "ai_summary": ai_response,
                "analysis_success": True,
                "from_general_knowledge": True,
            }
            
        except Exception as e:
            logger.exception(f"AI fallback failed for {protocol_name}")
            return {
                "error": str(e),
                "analysis_success": False,
                "protocol_name": protocol_name,
            }
    
    async def answer_question(
        self,
        protocol_name: str,
        question: str,
        raw_content: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Answer follow-up questions about a protocol.
        Can use scraped content if available, falls back to general knowledge.
        
        Args:
            protocol_name: Name of the protocol
            question: User's question
            raw_content: Optional scraped content to base answer on
            
        Returns:
            Dictionary with answer
        """
        try:
            client = AsyncOpenAI(api_key=self.openai_key)
            
            if raw_content and len(raw_content.strip()) >= 50:
                # Use content-based answer
                prompt = f"""
You are a DeFi expert. Answer this question about {protocol_name} based ONLY on the provided content.

CONTENT:
{raw_content[:3000]}

QUESTION: {question}

Provide a clear, accurate answer (2-4 sentences). If the information isn't in the content, say so clearly.
"""
            else:
                # Use general knowledge
                prompt = f"""You are a DeFi expert. Answer this question about {protocol_name}:

QUESTION: {question}

Provide a clear, accurate answer (2-4 sentences) based on your knowledge of DeFi and {protocol_name}.
"""
            
            response = await client.chat.completions.create(
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

import os
import logging
import httpx
import asyncio
from typing import List, Dict, Any, Optional

# Set up logging
logger = logging.getLogger(__name__)

# Get API key from environment
EXA_API_KEY = os.getenv("EXA_API_KEY", "")

class ExaAPIError(Exception):
    """Exception raised for Exa API errors"""
    pass

def _extract_key_summary(text: str, title: str) -> str:
    """Extract key information from text to create a concise summary."""
    if not text:
        return "No description available"

    # Split into sentences
    sentences = text.replace('\n', ' ').split('. ')

    # Key terms that indicate important information
    key_terms = [
        'protocol', 'defi', 'yield', 'apy', 'apr', 'tvl', 'lending', 'borrowing',
        'staking', 'liquidity', 'pool', 'vault', 'farm', 'earn', 'interest',
        'collateral', 'deposit', 'withdraw', 'rewards', 'governance'
    ]

    # Find sentences with key terms
    relevant_sentences = []
    for sentence in sentences[:10]:  # Only check first 10 sentences
        sentence = sentence.strip()
        if len(sentence) > 20 and len(sentence) < 200:  # Reasonable length
            if any(term in sentence.lower() for term in key_terms):
                relevant_sentences.append(sentence)

    # If we found relevant sentences, use them
    if relevant_sentences:
        summary = '. '.join(relevant_sentences[:2])  # Max 2 sentences
        return summary[:200] + "..." if len(summary) > 200 else summary

    # Fallback to first meaningful sentence
    for sentence in sentences[:5]:
        sentence = sentence.strip()
        if len(sentence) > 30 and len(sentence) < 150:
            return sentence

    # Last resort - truncate original text
    return text[:100] + "..." if len(text) > 100 else text

async def discover_defi_protocols(
    query: str,
    max_results: int = 3,  # Reduced from 5 to 3
    timeout: int = 8  # Reduced from 15 to 8 seconds
) -> Dict[str, Any]:
    """
    Discover DeFi protocols using Exa search API
    
    Args:
        query: Search query for DeFi protocols
        max_results: Maximum number of results to return
        timeout: Request timeout in seconds
        
    Returns:
        Dictionary with protocol data and search results
    """
    if not EXA_API_KEY:
        logger.error("Exa API key not found in environment variables")
        return {
            "error": "Exa API key not configured",
            "protocols_found": 0,
            "yield_opportunities": 0,
            "best_apy_found": "0.0%",
            "search_success": False,
            "protocols": []
        }
    
    # Enhance query with DeFi focus
    enhanced_query = f"{query} defi protocol yield apy tvl"
    
    # Exa API endpoint
    url = "https://api.exa.ai/search"
    
    headers = {
        "Authorization": f"Bearer {EXA_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Simplified payload to match working curl format
    payload = {
        "query": enhanced_query,
        "num_results": max_results
    }
    
    try:
        # Configure timeout properly for httpx
        timeout_config = httpx.Timeout(timeout=timeout, connect=10.0, read=timeout, write=10.0)
        async with httpx.AsyncClient(timeout=timeout_config) as client:
            response = await client.post(url, json=payload, headers=headers)
            
            if response.status_code != 200:
                logger.error(f"Exa API error: {response.status_code} - {response.text}")
                return {
                    "error": f"Exa API error: {response.status_code}",
                    "protocols_found": 0,
                    "yield_opportunities": 0,
                    "best_apy_found": "0.0%", 
                    "search_success": False,
                    "protocols": []
                }
            
            data = response.json()
            results = data.get("results", [])
            
            # Process results to extract protocol information with better filtering
            protocols = []
            apy_values = []

            for result in results:
                title = result.get("title", "")
                url = result.get("url", "")
                text = result.get("text", "")

                # Better filtering for DeFi protocols
                defi_keywords = ["protocol", "defi", "yield", "apy", "staking", "lending", "liquidity", "tvl"]
                if not any(keyword in title.lower() or keyword in text.lower() for keyword in defi_keywords):
                    continue

                # Skip if it's clearly not a protocol (news, blogs, etc.)
                skip_keywords = ["news", "article", "blog", "guide", "tutorial", "how to"]
                if any(keyword in title.lower() for keyword in skip_keywords):
                    continue
                
                # Extract APY if present
                apy = "Unknown"
                apy_value = 0.0
                
                apy_matches = [
                    # Match patterns like "10.5% APY" or "APY: 10.5%"
                    s for s in text.split() if "%" in s and any(c.isdigit() for c in s)
                ]
                
                if apy_matches:
                    for match in apy_matches:
                        # Clean up the match and extract numeric value
                        numeric_part = ''.join(c for c in match if c.isdigit() or c == '.')
                        try:
                            value = float(numeric_part)
                            if 0 <= value <= 1000:  # Reasonable APY range
                                apy = f"{value}%"
                                apy_value = value
                                apy_values.append(value)
                                break
                        except ValueError:
                            pass
                
                # Extract TVL if present
                tvl = "Unknown"
                tvl_matches = [
                    s for s in text.split() if "$" in s and "million" in text.lower() or "billion" in text.lower()
                ]
                
                if tvl_matches:
                    tvl = tvl_matches[0]
                
                # Create a better summary by extracting key sentences
                summary = _extract_key_summary(text, title)

                protocol = {
                    "name": title,
                    "url": url,
                    "apy": apy,
                    "tvl": tvl,
                    "summary": summary
                }
                
                protocols.append(protocol)
            
            # Calculate yield opportunities (protocols with APY)
            yield_opportunities = sum(1 for p in protocols if p["apy"] != "Unknown")
            
            # Get best APY
            best_apy = max(apy_values) if apy_values else 0.0
            best_apy_str = f"{best_apy}%" if best_apy > 0 else "0.0%"
            
            return {
                "protocols_found": len(protocols),
                "yield_opportunities": yield_opportunities,
                "best_apy_found": best_apy_str,
                "search_success": True,
                "protocols": protocols
            }
    
    except asyncio.TimeoutError:
        logger.error(f"Exa API timeout after {timeout} seconds")
        return {
            "error": f"Exa API timeout after {timeout} seconds",
            "protocols_found": 0,
            "yield_opportunities": 0,
            "best_apy_found": "0.0%",
            "search_success": False,
            "protocols": []
        }
    
    except Exception as e:
        logger.exception(f"Exa API error: {str(e)}")
        return {
            "error": f"Exa API error: {str(e)}",
            "protocols_found": 0,
            "yield_opportunities": 0,
            "best_apy_found": "0.0%",
            "search_success": False,
            "protocols": []
        }
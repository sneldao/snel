import os
import logging
import httpx
import asyncio
import re
import json
from typing import Dict, Any, Optional, List
from urllib.parse import quote_plus

# Set up logging
logger = logging.getLogger(__name__)

# Set to True to enable detailed debug output
DEBUG_MODE = True

# Get API key from environment
FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY", "")

class FirecrawlAPIError(Exception):
    """Exception raised for Firecrawl API errors"""
    pass

def _filter_verbose_content(content: str) -> str:
    """Filter out verbose/irrelevant content from scraped data."""
    if not content:
        return ""

    # Split into lines for processing
    lines = content.split('\n')
    filtered_lines = []

    # Patterns to skip (common verbose sections)
    skip_patterns = [
        'cookie', 'privacy', 'terms', 'subscribe', 'newsletter',
        'advertisement', 'ads', 'tracking', 'analytics', 'widget',
        'footer', 'header', 'navigation', 'menu', 'sidebar',
        'social media', 'follow us', 'share', 'like', 'tweet',
        'javascript', 'css', 'html', 'script', 'style',
        'loading', 'please wait', 'error', '404', '500',
        'topper/widget', 'session', 'storage', 'pending'
    ]

    # Keep patterns (relevant content)
    keep_patterns = [
        'apy', 'apr', 'yield', 'tvl', 'total value locked',
        'protocol', 'defi', 'lending', 'borrowing', 'staking',
        'liquidity', 'pool', 'farm', 'vault', 'strategy',
        'audit', 'security', 'risk', 'collateral', 'interest'
    ]

    for line in lines:
        line_lower = line.lower().strip()

        # Skip empty lines or very short lines
        if len(line_lower) < 10:
            continue

        # Skip lines with verbose patterns
        if any(pattern in line_lower for pattern in skip_patterns):
            continue

        # Prioritize lines with relevant DeFi content
        if any(pattern in line_lower for pattern in keep_patterns):
            filtered_lines.append(line.strip())
        # Also keep lines that look like descriptions (reasonable length)
        elif 20 <= len(line.strip()) <= 200 and not line.strip().startswith('#'):
            filtered_lines.append(line.strip())

    # Join and limit total length
    result = '\n'.join(filtered_lines[:10])  # Max 10 relevant lines
    return result[:800] + "..." if len(result) > 800 else result

async def get_protocol_details(
    protocol_name: str,
    max_content_length: int = 500,  # Reduced from 800 to 500
    timeout: int = 8,  # Reduced from 15 to 8 seconds
    debug: bool = DEBUG_MODE
) -> Dict[str, Any]:
    """
    Get detailed information about a DeFi protocol using Firecrawl
    
    Args:
        protocol_name: Name of the protocol to research
        max_content_length: Maximum content length to return
        timeout: Request timeout in seconds
        
    Returns:
        Dictionary with protocol details
    """
    if not FIRECRAWL_API_KEY:
        logger.error("Firecrawl API key not found in environment variables")
        return {
            "error": "Firecrawl API key not configured",
            "tvl_analyzed": "N/A",
            "security_audits": "Unknown",
            "live_rates": "Not available",
            "scraping_success": False,
            "protocols_scraped": 0
        }
    
    # Prepare URL-safe protocol name
    safe_name = quote_plus(protocol_name)
    
    # Firecrawl API endpoint - use v1 search endpoint for better results
    url = f"https://api.firecrawl.dev/v1/search"
    
    if debug:
        logger.info(f"[FIRECRAWL DEBUG] Searching for protocol: {protocol_name}")
        logger.info(f"[FIRECRAWL DEBUG] Search URL: {url}")
        logger.info("[FIRECRAWL DEBUG] Using v1 API search endpoint")
    
    headers = {
        "Authorization": f"Bearer {FIRECRAWL_API_KEY}",
        "Content-Type": "application/json"
    }
    
    try:
        # Simplified payload to match working curl format
        payload = {
            "query": f"{safe_name} defi protocol",
            "limit": 2
        }
            
        # Configure timeout properly for httpx
        timeout_config = httpx.Timeout(timeout=timeout, connect=10.0, read=timeout, write=10.0)
        async with httpx.AsyncClient(timeout=timeout_config) as client:
            if debug:
                logger.info(f"[FIRECRAWL DEBUG] Making POST request with payload: {payload}")
            response = await client.post(url, headers=headers, json=payload)
            
            if response.status_code != 200:
                logger.error(f"Firecrawl API error: {response.status_code} - {response.text}")
                return {
                    "error": f"Firecrawl API error: {response.status_code}",
                    "tvl_analyzed": "N/A",
                    "security_audits": "Unknown",
                    "live_rates": "Not available",
                    "scraping_success": False,
                    "protocols_scraped": 0
                }
            
            data = response.json()
            
            if debug:
                logger.info("[FIRECRAWL DEBUG] Raw API Response:")
                logger.info(json.dumps(data, indent=2))
            
            # Extract key information from the search results with better filtering
            content = ""
            result_url = ""

            # Handle v1 API response format
            if "data" in data and "results" in data["data"] and len(data["data"]["results"]) > 0:
                # Process search results from v1 API
                results = data["data"]["results"]
                for result in results[:2]:  # Use only top 2 results for accuracy
                    # Check if the result has markdown content (from scraping)
                    if "markdown" in result:
                        # Filter out verbose markdown content
                        markdown_content = result["markdown"]
                        # Remove common verbose sections
                        filtered_content = _filter_verbose_content(markdown_content)
                        content += filtered_content + "\n\n"
                    elif "description" in result:
                        # Use title and description if no markdown
                        title = result.get("title", "")
                        description = result.get("description", "")
                        # Only add if description is meaningful and not too long
                        if description and len(description) > 20 and len(description) < 500:
                            content += f"{title}\n{description}\n\n"

                    # Save the URL of the first result
                    if not result_url and "url" in result:
                        result_url = result["url"]

                # Remove trailing newlines
                content = content.strip()
            elif "results" in data and len(data["results"]) > 0:
                # Legacy response format (v0 API)
                first_result = data["results"][0]
                content = first_result.get("snippet", "")
                result_url = first_result.get("url", "")
                
                # If there's a title, add it to the content for more context
                if "title" in first_result:
                    content = f"{first_result['title']}\n\n{content}"
                
                # Combine snippets from top 3 results for more comprehensive info
                if len(data["results"]) > 1:
                    for result in data["results"][1:3]:  # Get 2nd and 3rd results
                        if "snippet" in result and result["snippet"]:
                            content += f"\n\n{result['snippet']}"
            elif "content" in data:
                # Direct content response (for backward compatibility)
                content = data.get("content", "")
                result_url = data.get("url", "")
            
            # Truncate content if needed
            content = content[:max_content_length] + "..." if len(content) > max_content_length else content
            
            # Extract TVL information
            tvl = "N/A"
            tvl_patterns = ["tvl", "total value locked", "aum", "assets under management"]
            for pattern in tvl_patterns:
                if pattern in content.lower():
                    # Find the sentence containing TVL
                    sentences = content.split('. ')
                    for sentence in sentences:
                        if pattern in sentence.lower() and ('$' in sentence or 'million' in sentence.lower() or 'billion' in sentence.lower()):
                            tvl = sentence.strip()
                            break
                    if tvl != "N/A":
                        break
            
            # Try to extract numeric TVL if possible
            if tvl != "N/A":
                import re
                # Look for dollar amounts
                dollar_matches = re.findall(r'\$\s*(\d+(?:\.\d+)?)\s*(million|billion|m|b|M|B)?', tvl)
                if dollar_matches:
                    amount, unit = dollar_matches[0] if len(dollar_matches[0]) > 1 else (dollar_matches[0][0], "")
                    amount = float(amount)
                    if unit.lower() in ['million', 'm']:
                        amount *= 1000000
                    elif unit.lower() in ['billion', 'b']:
                        amount *= 1000000000
                    tvl = f"${amount:,.0f}"
            
            # Extract security audit information
            security_audits = "Unknown"
            if "audit" in content.lower():
                if "not audited" in content.lower() or "no audit" in content.lower():
                    security_audits = "Not Audited"
                else:
                    auditors = []
                    known_auditors = ["certik", "chainsecurity", "consensys", "hacken", "quantstamp", "trail of bits", "openzeppelin", "peckshield", "omniscia", "zokyo", "certora", "sigma prime"]
                    for auditor in known_auditors:
                        if auditor in content.lower():
                            auditors.append(auditor.title())
                    
                    if auditors:
                        security_audits = f"Audited by {', '.join(auditors)}"
                    else:
                        security_audits = "Audited"
            
            # Check for additional security indicators
            security_indicators = []
            if "insurance" in content.lower() or "insured" in content.lower():
                security_indicators.append("Insurance Available")
            if "bug bounty" in content.lower():
                security_indicators.append("Bug Bounty Program")
            
            if security_indicators and security_audits != "Unknown":
                security_audits += f" • {' • '.join(security_indicators)}"
            elif security_indicators:
                security_audits = ' • '.join(security_indicators)
            
            # Extract live rates
            live_rates = []
            rate_patterns = ["apy", "apr", "yield", "interest", "rewards", "staking", "earning"]
            for pattern in rate_patterns:
                if pattern in content.lower():
                    # Find percentages near the pattern
                    segments = content.lower().split(pattern)
                    for i, segment in enumerate(segments[:-1]):  # Skip last segment which has no pattern after it
                        context = segment[-30:] + pattern + segments[i+1][:30]
                        percentage_indices = [j for j, char in enumerate(context) if char == '%']
                        for idx in percentage_indices:
                            # Look for numbers before the % sign
                            j = idx - 1
                            while j >= 0 and (context[j].isdigit() or context[j] == '.' or context[j].isspace()):
                                j -= 1
                            if j < idx - 1:  # We found at least one digit
                                rate = context[j+1:idx+1].strip()
                                if rate and rate not in live_rates:
                                    try:
                                        # Try to convert to a number to validate it's a real rate
                                        rate_value = float(rate.replace('%', '').strip())
                                        if 0 <= rate_value <= 1000:  # Reasonable range check
                                            live_rates.append(f"{rate_value:.2f}%")
                                    except ValueError:
                                        # If not a valid number, add it as is
                                        if rate not in live_rates:
                                            live_rates.append(rate)
            
            # Format rates nicely
            live_rates = sorted(live_rates, key=lambda x: float(x.replace('%', '')) if x.replace('%', '').replace('.', '').isdigit() else 0, reverse=True)
            if live_rates:
                best_rate = live_rates[0] if live_rates else "N/A"
                live_rates_str = f"{len(live_rates)} rates found (Best: {best_rate})"
            else:
                live_rates_str = "No rates found"
            
            # Extract key features or highlights
            features = []
            feature_indicators = ["feature", "benefit", "provides", "offers", "allows", "enables"]
            for indicator in feature_indicators:
                if indicator in content.lower():
                    sentences = content.split('. ')
                    for sentence in sentences:
                        if indicator in sentence.lower() and len(sentence) > 20 and len(sentence) < 150:
                            features.append(sentence.strip())
                            if len(features) >= 3:  # Limit to 3 features
                                break
                    if features:
                        break
                        
            result = {
                "protocol_name": protocol_name,
                "url": result_url,
                "tvl_analyzed": tvl,
                "security_audits": security_audits,
                "live_rates": live_rates_str,
                "rates": live_rates[:5],  # Include top 5 rates
                "content_preview": content[:200] + "..." if len(content) > 200 else content,
                "full_content": content,
                "scraping_success": True,
                "protocols_scraped": 1,
                "features": features,
                "source": "search" if "results" in data else "direct"
            }
            
            if debug:
                logger.info(f"[FIRECRAWL DEBUG] Processed Result:")
                logger.info(json.dumps(result, indent=2, default=str))
                
            return result
    
    except asyncio.TimeoutError:
        logger.error(f"Firecrawl API timeout after {timeout} seconds")
        return {
            "error": f"Firecrawl API timeout after {timeout} seconds",
            "tvl_analyzed": "N/A",
            "security_audits": "Unknown",
            "live_rates": "Not available",
            "scraping_success": False,
            "protocols_scraped": 0,
            "protocol_name": protocol_name,
            "rates": [],
            "features": [],
            "content_preview": f"Unable to retrieve data for {protocol_name} due to timeout."
        }
    
    except Exception as e:
        logger.exception(f"Firecrawl API error: {str(e)}")
        return {
            "error": f"Firecrawl API error: {str(e)}",
            "tvl_analyzed": "N/A",
            "security_audits": "Unknown",
            "live_rates": "Not available",
            "scraping_success": False,
            "protocols_scraped": 0,
            "protocol_name": protocol_name,
            "rates": [],
            "features": [],
            "content_preview": f"Unable to retrieve data for {protocol_name}."
        }

async def get_protocol_list() -> List[Dict[str, Any]]:
    """Get a list of popular DeFi protocols"""
    try:
        # Try to get a dynamic list from searching "top defi protocols"
        search_result = await get_protocol_details("top defi protocols by TVL")
        
        if search_result.get("scraping_success", False) and search_result.get("full_content"):
            content = search_result.get("full_content", "")
            
            # Extract protocol names using common patterns
            protocols = []
            lines = content.split('\n')
            
            for line in lines:
                # Look for numbered lists, bullet points, or protocol names followed by descriptions
                if (re.match(r'^\d+\.', line) or line.strip().startswith('•') or line.strip().startswith('-')) and len(line) < 100:
                    # Clean up the line
                    clean_line = line.strip().lstrip('•').lstrip('-').lstrip('1234567890.').strip()
                    
                    # Extract the first word or phrase that might be a protocol name
                    protocol_match = re.match(r'^([A-Za-z0-9]+(?:\s[A-Za-z0-9]+)?)', clean_line)
                    if protocol_match:
                        protocol_name = protocol_match.group(1)
                        if len(protocol_name) > 2 and protocol_name.lower() not in ["the", "and", "top", "best"]:
                            category = "Unknown"
                            if "dex" in line.lower() or "exchange" in line.lower():
                                category = "DEX"
                            elif "lend" in line.lower() or "borrow" in line.lower():
                                category = "Lending"
                            elif "staking" in line.lower() or "stake" in line.lower():
                                category = "Staking"
                            elif "yield" in line.lower():
                                category = "Yield"
                                
                            protocols.append({"name": protocol_name, "category": category})
            
            # If we found at least 3 protocols, use them
            if len(protocols) >= 3:
                # Add a few known ones at the end in case the extraction missed some
                known_protocols = [
                    {"name": "Uniswap", "category": "DEX"},
                    {"name": "Aave", "category": "Lending"},
                    {"name": "Compound", "category": "Lending"}
                ]
                
                # Add known protocols that aren't already in the list
                for known in known_protocols:
                    if not any(p["name"].lower() == known["name"].lower() for p in protocols):
                        protocols.append(known)
                        
                return protocols[:15]  # Return up to 15 protocols
    except Exception as e:
        logger.error(f"Error getting dynamic protocol list: {str(e)}")
    
    # Fallback to static list if dynamic approach fails
    return [
        {"name": "Uniswap", "category": "DEX"},
        {"name": "Aave", "category": "Lending"},
        {"name": "Compound", "category": "Lending"},
        {"name": "Curve", "category": "DEX"},
        {"name": "MakerDAO", "category": "CDP"},
        {"name": "Lido", "category": "Staking"},
        {"name": "Balancer", "category": "DEX"},
        {"name": "SushiSwap", "category": "DEX"},
        {"name": "Yearn Finance", "category": "Yield Aggregator"},
        {"name": "Convex Finance", "category": "Yield Optimizer"},
        {"name": "DeFi Protocol", "category": "General"},  # Fallback generic protocol
        {"name": "Crypto", "category": "General"},         # Another fallback
        {"name": "Blockchain", "category": "General"}      # Another fallback
    ]

async def get_multi_protocol_details(
    protocol_names: List[str],
    max_content_length: int = 2000,
    timeout: int = 30,
    debug: bool = DEBUG_MODE
) -> Dict[str, Any]:
    """
    Get details for multiple protocols
    
    Args:
        protocol_names: List of protocol names to research
        max_content_length: Maximum content length per protocol
        timeout: Request timeout in seconds
        
    Returns:
        Dictionary with aggregated protocol details
    """
    if not protocol_names:
        return {
            "error": "No protocol names provided",
            "tvl_analyzed": "N/A",
            "security_audits": "Unknown",
            "live_rates": "Not available",
            "scraping_success": False,
            "protocols_scraped": 0,
            "protocols": []
        }
    
    if debug:
        logger.info(f"[FIRECRAWL DEBUG] Multi-protocol search for: {protocol_names}")
        
    results = []
    successful_scrapes = 0
    all_rates = []
    
    for name in protocol_names:
        try:
            protocol_data = await get_protocol_details(name, max_content_length, timeout, debug)
            results.append(protocol_data)
            
            if protocol_data.get("scraping_success", False):
                successful_scrapes += 1
                all_rates.extend(protocol_data.get("rates", []))
        except Exception as e:
            logger.error(f"Error getting details for {name}: {str(e)}")
            results.append({
                "protocol_name": name,
                "error": str(e),
                "scraping_success": False
            })
    
    # Get highest TVL found
    tvl_analyzed = "N/A"
    for result in results:
        if result.get("tvl_analyzed", "N/A") != "N/A":
            tvl_analyzed = result.get("tvl_analyzed")
            break
    
    # Determine aggregate security status
    if all(r.get("security_audits", "Unknown") == "Unknown" for r in results):
        security_audits = "Unknown"
    elif any("Not Audited" == r.get("security_audits") for r in results):
        security_audits = "Some protocols not audited"
    elif any("Audited" in r.get("security_audits", "") for r in results):
        security_audits = "Audited protocols found"
    else:
        security_audits = "Varied security status"
    
    # Summary of live rates
    live_rates = f"{len(all_rates)} rates across {successful_scrapes} protocols"
    
    return {
        "tvl_analyzed": tvl_analyzed,
        "security_audits": security_audits,
        "live_rates": live_rates,
        "scraping_success": successful_scrapes > 0,
        "protocols_scraped": successful_scrapes,
        "protocols": results
    }
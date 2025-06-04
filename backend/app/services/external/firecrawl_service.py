import os
import logging
import httpx
import asyncio
import re
import json
from typing import Dict, Any, Optional, List
from urllib.parse import quote_plus
from openai import AsyncOpenAI

def strip_code_block(text: str) -> str:
    """
    Remove triple backtick code blocks (with or without 'json') from a string.
    """
    if not text:
        return ""
    # Remove ```json ... ``` or ``` ... ```
    return re.sub(r"```(?:json)?\s*([\s\S]*?)\s*```", r"\1", text, flags=re.IGNORECASE).strip()

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
    """Filter out verbose/irrelevant content from scraped data while preserving useful information."""
    if not content:
        return ""

    # For protocol research, we want to be less aggressive with filtering
    # Just remove obvious noise but keep most content for AI analysis

    # Split into lines for processing
    lines = content.split('\n')
    filtered_lines = []

    # Only skip truly irrelevant patterns
    skip_patterns = [
        'cookie policy', 'privacy policy', 'terms of service',
        'javascript', 'css', 'html', 'script', 'style',
        'loading...', 'please wait', 'error 404', 'error 500',
        'advertisement', 'ads by', 'sponsored'
    ]

    for line in lines:
        line_stripped = line.strip()
        line_lower = line_stripped.lower()

        # Skip empty lines
        if len(line_stripped) < 3:
            continue

        # Skip lines with noise patterns
        if any(pattern in line_lower for pattern in skip_patterns):
            continue

        # Keep most content - be much less aggressive
        if len(line_stripped) >= 3:
            filtered_lines.append(line_stripped)

    # Join and allow much more content for AI analysis
    result = '\n'.join(filtered_lines[:50])  # Increased from 10 to 50 lines
    return result[:3000] + "..." if len(result) > 3000 else result  # Increased from 800 to 3000 chars

async def get_protocol_details(
    protocol_name: str,
    max_content_length: int = 2000,  # Increased for better AI analysis
    timeout: int = 15,  # Increased for better scraping
    debug: bool = DEBUG_MODE
) -> Dict[str, Any]:
    """
    Get detailed information about a DeFi protocol using Firecrawl
    Returns raw scraped content for AI analysis instead of parsed fields

    Args:
        protocol_name: Name of the protocol to research
        max_content_length: Maximum content length to return
        timeout: Request timeout in seconds

    Returns:
        Dictionary with protocol details and raw content for AI analysis
    """
    if not FIRECRAWL_API_KEY:
        logger.error("Firecrawl API key not found in environment variables")
        return {
            "error": "Firecrawl API key not configured",
            "scraping_success": False,
            "protocol_name": protocol_name,
            "raw_content": "",
            "source_url": ""
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
        # Enhanced payload to get more comprehensive results
        payload = {
            "query": f"{safe_name} defi protocol documentation features",
            "limit": 5  # Get more URLs to try
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
            if "data" in data and len(data["data"]) > 0:
                # Process search results from v1 API
                results = data["data"]

                # Prioritize URLs for better content
                def prioritize_url(result):
                    url = result.get("url", "").lower()
                    # Prefer documentation and about pages for better content
                    if "docs." in url or "/docs" in url or "/documentation" in url:
                        return 0  # Highest priority for docs
                    elif "about" in url or "/about" in url:
                        return 1  # High priority for about pages
                    elif url.startswith(f"https://{protocol_name}.org") or url.startswith(f"https://{protocol_name}.com"):
                        return 2  # Medium priority for main domain
                    elif "app." in url or "/app" in url:
                        return 4  # Lower priority for app pages
                    else:
                        return 3  # Medium priority for other pages

                # Sort results to get the best URLs first
                sorted_results = sorted(results, key=prioritize_url)

                # Try multiple URLs to get better content
                content = ""
                result_url = ""
                for i, result in enumerate(sorted_results[:3]):  # Try up to 3 URLs
                    current_url = result.get("url", "")
                    if not current_url:
                        continue

                    if debug:
                        logger.info(f"[FIRECRAWL DEBUG] Trying URL {i+1}/3: {current_url}")

                    try:
                        # Use Firecrawl scrape endpoint to get full content
                        scrape_url = f"https://api.firecrawl.dev/v1/scrape"
                        scrape_payload = {
                            "url": current_url,
                            "formats": ["markdown", "html"],
                            "onlyMainContent": False,  # Get more content
                            "includeTags": ["p", "h1", "h2", "h3", "h4", "h5", "h6", "div", "section", "article"],
                            "excludeTags": ["nav", "footer", "header", "aside", "script", "style"],
                            "waitFor": 2000  # Wait for dynamic content to load
                        }

                        async with httpx.AsyncClient(timeout=timeout_config) as scrape_client:
                            scrape_response = await scrape_client.post(scrape_url, headers=headers, json=scrape_payload)

                            if scrape_response.status_code == 200:
                                scrape_data = scrape_response.json()
                                if debug:
                                    logger.info(f"[FIRECRAWL DEBUG] Scrape response status: {scrape_response.status_code}")

                                if "data" in scrape_data and "markdown" in scrape_data["data"]:
                                    markdown_content = scrape_data["data"]["markdown"]
                                    # Filter out verbose markdown content
                                    filtered_content = _filter_verbose_content(markdown_content)

                                    if debug:
                                        logger.info(f"[FIRECRAWL DEBUG] Scraped {len(filtered_content)} characters from {current_url}")

                                    # If we got good content (more than 500 chars), use it
                                    if len(filtered_content) > 500:
                                        content = filtered_content
                                        result_url = current_url
                                        break
                                    # Otherwise, keep the best content so far
                                    elif len(filtered_content) > len(content):
                                        content = filtered_content
                                        result_url = current_url
                                else:
                                    if debug:
                                        logger.info(f"[FIRECRAWL DEBUG] No markdown content in scrape response for {current_url}")
                            else:
                                if debug:
                                    logger.info(f"[FIRECRAWL DEBUG] Scrape failed with status: {scrape_response.status_code} for {current_url}")
                    except Exception as scrape_error:
                        if debug:
                            logger.info(f"[FIRECRAWL DEBUG] Scraping failed for {current_url}: {str(scrape_error)}")
                        continue

                # Fallback to search results if scraping failed
                if not content:
                    # Use the sorted results for better content
                    for result in sorted_results[:3]:  # Use top 3 sorted results for accuracy
                        # Use title and description from search results
                        title = result.get("title", "")
                        description = result.get("description", "")
                        # Only add if description is meaningful and not too long
                        if description and len(description) > 20 and len(description) < 500:
                            content += f"{title}\n{description}\n\n"

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
            
            # Extract and clean key features from links and content
            features = []
            key_services = []

            # Extract services from markdown links
            import re
            link_pattern = r'\[([^\]]+)\]\(([^)]+)\)'
            links = re.findall(link_pattern, content)

            seen_services = set()  # Track unique services
            for link_text, link_url in links:
                # Clean up the link text
                clean_text = link_text.replace('\\\\', '').replace('\\n', ' ').strip()
                if len(clean_text) > 2 and len(clean_text) < 100:
                    # Create a more descriptive service name by analyzing the URL too
                    service_name = clean_text

                    # Enhance service name based on URL context
                    if 'app.' in link_url or '/app' in link_url:
                        service_name = f"{clean_text} (Trading App)"
                    elif 'market' in link_url and 'market' not in clean_text.lower():
                        service_name = f"{clean_text} Markets"
                    elif 'governance' in link_url:
                        service_name = f"{clean_text} (Governance)"
                    elif 'docs' in link_url or 'developer' in link_url:
                        service_name = f"{clean_text} (Documentation)"
                    elif 'security' in link_url:
                        service_name = f"{clean_text} (Security)"
                    elif 'gho' in link_url.lower():
                        service_name = f"{clean_text} (Stablecoin)"

                    # Skip duplicates
                    service_key = service_name.lower().replace(' ', '')
                    if service_key in seen_services:
                        continue
                    seen_services.add(service_key)

                    # Categorize the service
                    if any(word in service_name.lower() for word in ['app', 'trading', 'platform']):
                        key_services.append(f"🔗 {service_name}")
                    elif any(word in service_name.lower() for word in ['stablecoin', 'token', 'coin', 'gho']):
                        key_services.append(f"💰 {service_name}")
                    elif any(word in service_name.lower() for word in ['governance', 'dao', 'vote']):
                        key_services.append(f"🏛️ {service_name}")
                    elif any(word in service_name.lower() for word in ['docs', 'developer', 'technical', 'documentation']):
                        key_services.append(f"📚 {service_name}")
                    elif any(word in service_name.lower() for word in ['security', 'audit', 'bug bounty']):
                        key_services.append(f"🛡️ {service_name}")
                    elif any(word in service_name.lower() for word in ['market', 'markets']):
                        key_services.append(f"📊 {service_name}")
                    else:
                        key_services.append(f"ℹ️ {service_name}")

            # Limit to most important services
            features = key_services[:6]

            # Create a clean, user-friendly summary
            protocol_type = "DeFi Protocol"
            content_lower = content.lower()

            # Check protocol name for known types
            if protocol_name.lower() in ["uniswap", "sushiswap", "curve", "balancer", "1inch"]:
                protocol_type = "Decentralized Exchange"
            elif protocol_name.lower() in ["aave", "compound", "maker", "makerdao"]:
                protocol_type = "Lending Protocol"
            elif protocol_name.lower() in ["lido", "rocket pool", "stakewise"]:
                protocol_type = "Staking Protocol"
            # Then check content
            elif "lending" in content_lower or "borrow" in content_lower:
                protocol_type = "Lending Protocol"
            elif any(word in content_lower for word in ["dex", "exchange", "swap", "trade", "trading", "marketplace"]):
                protocol_type = "Decentralized Exchange"
            elif "staking" in content_lower:
                protocol_type = "Staking Protocol"
            elif "yield" in content_lower:
                protocol_type = "Yield Protocol"

            # Create a clean summary without markdown
            clean_summary = f"{protocol_name.title()} is a {protocol_type.lower()}"

            # If we have features, add them to summary
            if features:
                # Get the first service name without emoji
                first_service = features[0].split(' ', 1)[1] if ' ' in features[0] else features[0]
                # Remove parenthetical info for cleaner summary
                first_service = first_service.split(' (')[0] if ' (' in first_service else first_service
                clean_summary += f" providing {len(features)} services including {first_service}"
            # If no features but we have content, extract key info
            elif content and len(content) > 50:
                # Extract the most informative sentence from content
                sentences = content.split('. ')
                best_sentence = ""
                for sentence in sentences:
                    if len(sentence) > 30 and len(sentence) < 150 and any(word in sentence.lower() for word in ['protocol', 'platform', 'exchange', 'defi', 'crypto', 'blockchain']):
                        best_sentence = sentence.strip()
                        break
                if best_sentence:
                    clean_summary += f". {best_sentence}"

            if security_audits != "Unknown":
                clean_summary += f". {security_audits}"

            # Return simplified result for AI analysis
            result = {
                "protocol_name": protocol_name,
                "source_url": result_url,
                "raw_content": content,
                "scraping_success": True,
                "content_length": len(content)
            }

            if debug:
                logger.info(f"[FIRECRAWL DEBUG] Simplified Result for AI Analysis:")
                logger.info(json.dumps(result, indent=2, default=str))

            return result
    
    except asyncio.TimeoutError:
        logger.error(f"Firecrawl API timeout after {timeout} seconds")
        return {
            "error": f"Firecrawl API timeout after {timeout} seconds",
            "scraping_success": False,
            "protocol_name": protocol_name,
            "raw_content": "",
            "source_url": ""
        }

    except Exception as e:
        logger.exception(f"Firecrawl API error: {str(e)}")
        return {
            "error": f"Firecrawl API error: {str(e)}",
            "scraping_success": False,
            "protocol_name": protocol_name,
            "raw_content": "",
            "source_url": ""
        }

async def analyze_protocol_with_ai(
    protocol_name: str,
    raw_content: str,
    source_url: str,
    openai_api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Analyze scraped protocol content using OpenAI for intelligent summarization

    Args:
        protocol_name: Name of the protocol
        raw_content: Raw scraped content from Firecrawl
        source_url: Source URL of the content
        openai_api_key: OpenAI API key for analysis

    Returns:
        Dictionary with AI-generated analysis and summary
    """
    if not openai_api_key:
        logger.warning(f"No OpenAI API key provided for {protocol_name} analysis")
        return {
            "error": "OpenAI API key required for protocol analysis",
            "protocol_name": protocol_name,
            "ai_summary": "",
            "key_features": [],
            "analysis_success": False
        }

    if not raw_content or len(raw_content.strip()) < 50:
        return {
            "error": "Insufficient content for analysis",
            "protocol_name": protocol_name,
            "ai_summary": f"Limited information available about {protocol_name}. Please try a different search or check the protocol name.",
            "key_features": [],
            "analysis_success": False
        }

    try:
        logger.info(f"Starting AI analysis for {protocol_name} with {len(raw_content)} characters of content")
        client = AsyncOpenAI(api_key=openai_api_key)

        # Create a comprehensive prompt for protocol analysis
        prompt = f"""
You are a DeFi protocol research expert. Analyze the following information about {protocol_name} and provide a comprehensive summary.

SCRAPED CONTENT:
{raw_content[:3000]}  # Limit content to avoid token limits

SOURCE: {source_url}

Please provide:
1. A clear, concise summary (2-3 sentences) explaining what {protocol_name} is and what it does
2. Key features and capabilities (list 3-5 main features)
3. Protocol type (e.g., DEX, Lending, Staking, etc.)
4. Any notable security information, audits, or risks mentioned
5. TVL, rates, or other financial metrics if available

Format your response as JSON with these fields:
- "summary": string (2-3 sentences)
- "protocol_type": string
- "key_features": array of strings
- "security_info": string
- "financial_metrics": string
- "analysis_quality": "high" | "medium" | "low" (based on content quality)

Be factual and only include information that's clearly stated in the content. If information is unclear or missing, indicate that.
"""

        response = await client.chat.completions.create(
            model="gpt-4o-mini",  # Use cost-effective model for analysis
            messages=[
                {"role": "system", "content": "You are a DeFi protocol research expert. Provide accurate, factual analysis based only on the provided content."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=800,
            temperature=0.3  # Lower temperature for more factual responses
        )

        # Parse the AI response
        ai_content = response.choices[0].message.content
        logger.info(f"OpenAI analysis completed for {protocol_name}. Response length: {len(ai_content) if ai_content else 0}")

        # Strip code block formatting before parsing
        ai_content_clean = strip_code_block(ai_content)
        # Try to parse as JSON, fallback to text if needed
        try:
            ai_analysis = json.loads(ai_content_clean)

            return {
                "protocol_name": protocol_name,
                "source_url": source_url,
                "ai_summary": ai_analysis.get("summary", ""),
                "protocol_type": ai_analysis.get("protocol_type", "DeFi Protocol"),
                "key_features": ai_analysis.get("key_features", []),
                "security_info": ai_analysis.get("security_info", ""),
                "financial_metrics": ai_analysis.get("financial_metrics", ""),
                "analysis_quality": ai_analysis.get("analysis_quality", "medium"),
                "raw_content": raw_content,
                "analysis_success": True
            }

        except json.JSONDecodeError:
            # Fallback to text-based response
            return {
                "protocol_name": protocol_name,
                "source_url": source_url,
                "ai_summary": ai_content,
                "protocol_type": "DeFi Protocol",
                "key_features": [],
                "security_info": "",
                "financial_metrics": "",
                "analysis_quality": "medium",
                "raw_content": raw_content,
                "analysis_success": True
            }

    except Exception as e:
        logger.error(f"OpenAI analysis error for {protocol_name}: {str(e)}")
        return {
            "error": f"AI analysis failed: {str(e)}",
            "protocol_name": protocol_name,
            "ai_summary": f"Unable to analyze {protocol_name} at this time. Raw content is available for manual review.",
            "key_features": [],
            "analysis_success": False,
            "raw_content": raw_content
        }

async def answer_protocol_question(
    protocol_name: str,
    question: str,
    raw_content: str,
    openai_api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Answer follow-up questions about a protocol using the previously scraped content

    Args:
        protocol_name: Name of the protocol
        question: User's follow-up question
        raw_content: Previously scraped content
        openai_api_key: OpenAI API key

    Returns:
        Dictionary with the answer
    """
    if not openai_api_key:
        return {
            "error": "OpenAI API key required for answering questions",
            "answer": "I need an OpenAI API key to answer questions about protocols.",
            "success": False
        }

    if not raw_content or len(raw_content.strip()) < 50:
        return {
            "error": "No protocol content available",
            "answer": f"I don't have enough information about {protocol_name} to answer that question. Please research the protocol first.",
            "success": False
        }

    try:
        client = AsyncOpenAI(api_key=openai_api_key)

        prompt = f"""
You are a DeFi protocol expert. Answer the user's question about {protocol_name} based ONLY on the provided content.

PROTOCOL CONTENT:
{raw_content[:4000]}

USER QUESTION: {question}

Please provide a clear, accurate answer based only on the information in the content above. If the information needed to answer the question is not in the content, say so clearly.

Keep your answer concise but informative (2-4 sentences).
"""

        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": f"You are a helpful assistant answering questions about {protocol_name}. Only use the provided content to answer questions."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=300,
            temperature=0.3
        )

        answer = response.choices[0].message.content

        return {
            "protocol_name": protocol_name,
            "question": question,
            "answer": answer,
            "success": True
        }

    except Exception as e:
        logger.error(f"Error answering question about {protocol_name}: {str(e)}")
        return {
            "error": f"Failed to answer question: {str(e)}",
            "answer": f"I encountered an error while trying to answer your question about {protocol_name}. Please try again.",
            "success": False
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
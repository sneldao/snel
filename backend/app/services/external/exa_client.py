"""
Unified Exa API client for DeFi protocol discovery.
Mirrors FirecrawlClient structure with neural search optimization.
"""
import logging
import json
import re
from typing import Optional, List, Dict, Any
import httpx

logger = logging.getLogger(__name__)


class ExaError(Exception):
    """Base exception for Exa API errors."""
    pass


class ExaClient:
    """
    High-level Exa API client optimized for DeFi discovery.
    Uses semantic/neural search for opportunity finding.
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.exa.ai",
        timeout: int = 15,
        cache_client: Optional[Any] = None,
    ):
        """
        Initialize Exa client.
        
        Args:
            api_key: Exa API key
            base_url: API base URL
            timeout: Request timeout in seconds
            cache_client: Optional Redis/cache client for caching results
        """
        if not api_key:
            raise ExaError("Exa API key is required")
        
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.cache_client = cache_client
        self.cache_ttl = 3600  # 1 hour for discovery results
        
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    async def search_opportunities(
        self,
        query: str,
        category: str = "yield",
        max_results: int = 5,
        cache: bool = True,
    ) -> Dict[str, Any]:
        """
        Search for DeFi opportunities using semantic search.
        
        Args:
            query: Search query (e.g., "highest yield farming on base")
            category: Opportunity type (yield, new, security_audits, governance)
            max_results: Number of results to return
            cache: Whether to cache results
            
        Returns:
            Dict with search results and extracted opportunities
        """
        cache_key = f"exa:search:{query}:{category}" if cache else None
        
        if cache_key and self.cache_client:
            cached = self._get_cache(cache_key)
            if cached:
                logger.info(f"Cache hit for Exa search: {query}")
                return cached
        
        try:
            # Query enhancement for better semantic matching
            enhanced_query = self._enhance_query(query, category)
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                payload = {
                    "query": enhanced_query,
                    "num_results": max_results,
                }
                
                response = await client.post(
                    f"{self.base_url}/search",
                    headers=self.headers,
                    json=payload,
                )
                
                if response.status_code != 200:
                    raise ExaError(
                        f"Search failed: {response.status_code} - {response.text}"
                    )
                
                data = response.json()
                results = self._parse_and_extract(data.get("results", []))
                
                response_data = {
                    "search_success": True,
                    "protocols_found": len(results),
                    "yield_opportunities": sum(1 for r in results if r.get("apy") != "Unknown"),
                    "best_apy_found": self._get_best_apy(results),
                    "protocols": results,
                }
                
                if cache_key and self.cache_client:
                    self._set_cache(cache_key, response_data)
                
                return response_data
                
        except httpx.TimeoutException:
            raise ExaError(f"Exa search timeout for query: {query}")
        except Exception as e:
            logger.error(f"Exa search error: {e}")
            raise ExaError(f"Search failed: {str(e)}")

    def _enhance_query(self, query: str, category: str) -> str:
        """
        Enhance query for better semantic matching.
        
        Args:
            query: Original user query
            category: Opportunity type
            
        Returns:
            Enhanced query string
        """
        # Add category-specific keywords
        enhancements = {
            "yield": "defi protocol yield apy farming",
            "new": "newly launched defi protocol 2024",
            "security_audits": "audited security protocol blockchain",
            "governance": "governance token voting rewards",
        }
        
        enhancement = enhancements.get(category, "defi protocol")
        
        # Only add if not already in query
        if enhancement.split()[0] not in query.lower():
            return f"{query} {enhancement}"
        
        return query

    def _parse_and_extract(self, results: List[Dict]) -> List[Dict]:
        """
        Parse Exa search results and extract structured opportunity data.
        
        Args:
            results: Raw Exa search results
            
        Returns:
            List of structured opportunity objects
        """
        opportunities = []
        
        for result in results:
            title = result.get("title", "")
            text = result.get("text", "")
            url = result.get("url", "")
            
            # Filter for DeFi protocols
            defi_keywords = ["protocol", "defi", "yield", "apy", "staking", "lending", "tvl"]
            if not any(keyword in title.lower() or keyword in text.lower() for keyword in defi_keywords):
                continue
            
            # Skip news/articles/blogs
            skip_keywords = ["news", "article", "blog", "guide", "tutorial", "how to"]
            if any(keyword in title.lower() for keyword in skip_keywords):
                continue
            
            # Extract APY
            apy = self._extract_apy(text)
            
            # Extract TVL
            tvl = self._extract_tvl(text)
            
            # Create summary
            summary = self._extract_summary(text, title)
            
            opportunity = {
                "name": title,
                "url": url,
                "apy": apy,
                "tvl": tvl,
                "summary": summary,
                "type": self._detect_protocol_type(title, text),
            }
            
            opportunities.append(opportunity)
        
        return opportunities

    def _extract_apy(self, text: str) -> str:
        """Extract APY from text."""
        apy_matches = [s for s in text.split() if "%" in s and any(c.isdigit() for c in s)]
        
        if apy_matches:
            for match in apy_matches:
                numeric_part = ''.join(c for c in match if c.isdigit() or c == '.')
                try:
                    value = float(numeric_part)
                    if 0 <= value <= 1000:  # Reasonable range
                        return f"{value}%"
                except ValueError:
                    pass
        
        return "Unknown"

    def _extract_tvl(self, text: str) -> str:
        """Extract TVL from text."""
        # Look for patterns like "$10B", "$5.2M", etc.
        tvl_pattern = r'\$[\d.]+\s*[BMK](?:illion)?'
        match = re.search(tvl_pattern, text, re.IGNORECASE)
        
        if match:
            return match.group(0)
        
        return "Unknown"

    def _extract_summary(self, text: str, title: str) -> str:
        """Extract concise summary from text."""
        if not text:
            return "No description available"
        
        # Split into sentences
        sentences = text.replace('\n', ' ').split('. ')
        
        # Key terms for DeFi
        key_terms = [
            'protocol', 'defi', 'yield', 'apy', 'apr', 'tvl', 'lending', 'borrowing',
            'staking', 'liquidity', 'pool', 'vault', 'farm', 'earn', 'interest',
            'collateral', 'deposit', 'withdraw', 'rewards', 'governance'
        ]
        
        # Find sentences with key terms
        relevant_sentences = []
        for sentence in sentences[:10]:
            sentence = sentence.strip()
            if 20 < len(sentence) < 200 and any(term in sentence.lower() for term in key_terms):
                relevant_sentences.append(sentence)
        
        if relevant_sentences:
            summary = '. '.join(relevant_sentences[:2])
            return summary[:200] + "..." if len(summary) > 200 else summary
        
        # Fallback to first meaningful sentence
        for sentence in sentences[:5]:
            sentence = sentence.strip()
            if 30 < len(sentence) < 150:
                return sentence
        
        return text[:100] + "..." if len(text) > 100 else text

    def _detect_protocol_type(self, title: str, text: str) -> str:
        """Detect protocol type from title and text."""
        combined = (title + " " + text).lower()
        
        type_patterns = {
            "DEX": ["dex", "exchange", "swap", "trading"],
            "Lending": ["lending", "lend", "borrow", "loan"],
            "Staking": ["staking", "stake", "validator"],
            "Yield": ["yield", "farm", "farming"],
            "Bridge": ["bridge", "cross-chain"],
            "Governance": ["governance", "dao", "vote"],
        }
        
        for ptype, keywords in type_patterns.items():
            if any(kw in combined for kw in keywords):
                return ptype
        
        return "Protocol"

    def _get_best_apy(self, results: List[Dict]) -> str:
        """Get highest APY from results."""
        apy_values = []
        
        for result in results:
            apy_str = result.get("apy", "Unknown")
            if apy_str != "Unknown":
                try:
                    value = float(apy_str.replace("%", ""))
                    apy_values.append(value)
                except ValueError:
                    pass
        
        if apy_values:
            return f"{max(apy_values)}%"
        
        return "Unknown"

    def _get_cache(self, key: str) -> Optional[Dict[str, Any]]:
        """Get value from cache."""
        if not self.cache_client:
            return None
        
        try:
            cached = self.cache_client.get(key)
            if cached:
                return json.loads(cached)
        except Exception as e:
            logger.warning(f"Cache get error: {e}")
        
        return None

    def _set_cache(self, key: str, value: Dict[str, Any]) -> None:
        """Set value in cache."""
        if not self.cache_client:
            return
        
        try:
            self.cache_client.setex(
                key,
                self.cache_ttl,
                json.dumps(value),
            )
        except Exception as e:
            logger.warning(f"Cache set error: {e}")

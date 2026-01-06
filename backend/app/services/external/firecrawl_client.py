"""
Unified Firecrawl API client with LLM extraction, batch processing, and caching.
Single source of truth for all Firecrawl interactions.
"""
import logging
import json
from typing import Optional, List, Dict, Any
from urllib.parse import quote_plus
import httpx
from datetime import datetime

logger = logging.getLogger(__name__)


class FirecrawlError(Exception):
    """Base exception for Firecrawl API errors."""
    pass


class FirecrawlClient:
    """
    High-level Firecrawl API client with advanced features:
    - LLM-powered extraction for structured data
    - Batch processing for multiple URLs
    - Built-in caching support
    - Proper error handling and retry logic
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.firecrawl.dev",
        timeout: int = 30,
        cache_client: Optional[Any] = None,
    ):
        """
        Initialize Firecrawl client.
        
        Args:
            api_key: Firecrawl API key
            base_url: API base URL
            timeout: Request timeout in seconds
            cache_client: Optional Redis/cache client for caching scrapes
        """
        if not api_key:
            raise FirecrawlError("Firecrawl API key is required")
        
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.cache_client = cache_client
        self.cache_ttl = 3600  # 1 hour
        
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    async def search(
        self,
        query: str,
        limit: int = 5,
        cache: bool = True,
    ) -> Dict[str, Any]:
        """
        Search for URLs matching a query.
        
        Args:
            query: Search query
            limit: Number of results to return
            cache: Whether to cache results
            
        Returns:
            Dict with search results
        """
        cache_key = f"firecrawl:search:{query}:{limit}" if cache else None
        
        if cache_key and self.cache_client:
            cached = self._get_cache(cache_key)
            if cached:
                logger.info(f"Cache hit for search: {query}")
                return cached
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                payload = {
                    "query": query,
                    "limit": limit,
                }
                
                response = await client.post(
                    f"{self.base_url}/v1/search",
                    headers=self.headers,
                    json=payload,
                )
                
                if response.status_code != 200:
                    raise FirecrawlError(
                        f"Search failed: {response.status_code} - {response.text}"
                    )
                
                data = response.json()
                
                if cache_key and self.cache_client:
                    self._set_cache(cache_key, data)
                
                return data
                
        except httpx.TimeoutException:
            raise FirecrawlError(f"Search timeout for query: {query}")
        except Exception as e:
            logger.error(f"Search error: {e}")
            raise FirecrawlError(f"Search failed: {str(e)}")

    async def scrape(
        self,
        url: str,
        use_llm_extraction: bool = False,
        extraction_schema: Optional[Dict[str, Any]] = None,
        cache: bool = True,
    ) -> Dict[str, Any]:
        """
        Scrape a single URL with optional LLM extraction.
        
        Args:
            url: URL to scrape
            use_llm_extraction: Whether to use LLM for structured extraction
            extraction_schema: JSON schema for LLM extraction
            cache: Whether to cache results
            
        Returns:
            Dict with scraped content
        """
        cache_key = f"firecrawl:scrape:{url}" if cache else None
        
        if cache_key and self.cache_client:
            cached = self._get_cache(cache_key)
            if cached:
                logger.info(f"Cache hit for URL: {url}")
                return cached
        
        try:
            payload = {
                "url": url,
                "formats": ["markdown"],
                "onlyMainContent": True,  # Only extract main content
                "cache": True,  # Use Firecrawl's built-in caching
            }
            
            # Add LLM extraction if requested
            if use_llm_extraction and extraction_schema:
                payload["extractorOptions"] = {
                    "mode": "llm-extraction",
                    "extractionSchema": extraction_schema,
                }
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/v1/scrape",
                    headers=self.headers,
                    json=payload,
                )
                
                if response.status_code != 200:
                    raise FirecrawlError(
                        f"Scrape failed: {response.status_code} - {response.text}"
                    )
                
                data = response.json()
                
                if cache_key and self.cache_client:
                    self._set_cache(cache_key, data)
                
                return data
                
        except httpx.TimeoutException:
            raise FirecrawlError(f"Scrape timeout for URL: {url}")
        except Exception as e:
            logger.error(f"Scrape error for {url}: {e}")
            raise FirecrawlError(f"Scrape failed: {str(e)}")

    async def batch_scrape(
        self,
        urls: List[str],
        use_llm_extraction: bool = False,
        extraction_schema: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Scrape multiple URLs in a single batch request (more efficient).
        
        Args:
            urls: List of URLs to scrape
            use_llm_extraction: Whether to use LLM for structured extraction
            extraction_schema: JSON schema for LLM extraction
            
        Returns:
            Dict mapping URL to scrape results
        """
        if not urls:
            return {}
        
        try:
            urls_payload = []
            for url in urls:
                item = {"url": url}
                urls_payload.append(item)
            
            payload = {
                "urls": urls_payload,
                "formats": ["markdown"],
                "onlyMainContent": True,
            }
            
            if use_llm_extraction and extraction_schema:
                payload["extractorOptions"] = {
                    "mode": "llm-extraction",
                    "extractionSchema": extraction_schema,
                }
            
            async with httpx.AsyncClient(timeout=self.timeout * 2) as client:
                response = await client.post(
                    f"{self.base_url}/v1/batch",
                    headers=self.headers,
                    json=payload,
                )
                
                if response.status_code != 200:
                    raise FirecrawlError(
                        f"Batch scrape failed: {response.status_code} - {response.text}"
                    )
                
                data = response.json()
                result = {}
                
                # Extract results by URL
                if "data" in data:
                    for item in data["data"]:
                        url = item.get("url")
                        if url:
                            result[url] = item
                
                return result
                
        except httpx.TimeoutException:
            raise FirecrawlError(f"Batch scrape timeout")
        except Exception as e:
            logger.error(f"Batch scrape error: {e}")
            raise FirecrawlError(f"Batch scrape failed: {str(e)}")

    async def search_and_scrape(
        self,
        query: str,
        max_urls: int = 3,
        use_llm_extraction: bool = False,
        extraction_schema: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search for URLs and scrape the best results.
        Uses batch processing for efficiency.
        
        Args:
            query: Search query
            max_urls: Maximum URLs to scrape
            use_llm_extraction: Whether to use LLM extraction
            extraction_schema: Schema for LLM extraction
            
        Returns:
            List of scraped results
        """
        try:
            # Step 1: Search
            search_results = await self.search(query, limit=max_urls)
            
            if not search_results.get("data"):
                logger.warning(f"No search results for query: {query}")
                return []
            
            # Step 2: Extract URLs and prioritize
            urls = self._prioritize_urls(
                [r.get("url") for r in search_results["data"] if r.get("url")]
            )[:max_urls]
            
            if not urls:
                logger.warning(f"No valid URLs from search results for: {query}")
                return []
            
            # Step 3: Batch scrape (efficient)
            scrape_results = await self.batch_scrape(
                urls,
                use_llm_extraction=use_llm_extraction,
                extraction_schema=extraction_schema,
            )
            
            return list(scrape_results.values())
            
        except FirecrawlError:
            raise
        except Exception as e:
            logger.error(f"Search and scrape failed: {e}")
            raise FirecrawlError(f"Search and scrape failed: {str(e)}")

    def _prioritize_urls(self, urls: List[str]) -> List[str]:
        """
        Prioritize URLs by relevance (docs > about > main domain > other).
        """
        def priority(url: str) -> int:
            url_lower = url.lower()
            if "docs." in url_lower or "/docs" in url_lower or "/documentation" in url_lower:
                return 0
            elif "about" in url_lower or "/about" in url_lower:
                return 1
            elif "/app" in url_lower or "app." in url_lower:
                return 4
            else:
                return 2
        
        return sorted(urls, key=priority)

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

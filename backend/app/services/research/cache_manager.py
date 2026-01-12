"""
Cache management for research operations.
Handles caching strategy across all three intent types.
"""
import json
import logging
from typing import Optional, Dict, Any
from app.services.research.router import Intent

logger = logging.getLogger(__name__)


class ResearchCacheManager:
    """
    Centralized cache management for research operations.
    Automatically determines cache TTL based on intent type.
    """
    
    # Cache TTL by intent type (in seconds)
    CACHE_TTL = {
        "concept": 24 * 3600,      # 24 hours - static knowledge
        "depth": 6 * 3600,         # 6 hours - protocol data
        "discovery": 3600,         # 1 hour - yields change hourly
    }
    
    def __init__(self, redis_client: Optional[Any] = None):
        """
        Initialize cache manager.
        
        Args:
            redis_client: Optional Redis client. If None, caching is disabled.
        """
        self.redis_client = redis_client
        self.enabled = redis_client is not None
    
    def get_cache_key(self, intent: Intent, query: str, tool: str = None) -> str:
        """
        Generate cache key for a query.
        
        Format: research:{intent}:{tool}:{query_hash}
        """
        import hashlib
        query_hash = hashlib.md5(query.lower().encode()).hexdigest()[:8]
        tool_part = f":{tool}" if tool else ""
        return f"research:{intent}{tool_part}:{query_hash}"
    
    async def get(
        self,
        intent: Intent,
        query: str,
        tool: str = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Get cached research result.
        
        Args:
            intent: Research intent type
            query: Original query string
            tool: Optional tool name (firecrawl, exa, kb)
            
        Returns:
            Cached result or None if not found
        """
        if not self.enabled:
            return None
        
        try:
            cache_key = self.get_cache_key(intent, query, tool)
            cached = self.redis_client.get(cache_key)
            
            if cached:
                logger.info(f"Cache hit: {cache_key}")
                return json.loads(cached)
            
            logger.debug(f"Cache miss: {cache_key}")
            return None
            
        except Exception as e:
            logger.warning(f"Cache get error: {e}")
            return None
    
    async def set(
        self,
        intent: Intent,
        query: str,
        result: Dict[str, Any],
        tool: str = None,
    ) -> bool:
        """
        Cache a research result.
        
        Args:
            intent: Research intent type
            query: Original query string
            result: Result to cache
            tool: Optional tool name (firecrawl, exa, kb)
            
        Returns:
            True if caching succeeded, False otherwise
        """
        if not self.enabled:
            return False
        
        try:
            cache_key = self.get_cache_key(intent, query, tool)
            ttl = self.CACHE_TTL.get(intent, 3600)
            
            self.redis_client.setex(
                cache_key,
                ttl,
                json.dumps(result),
            )
            
            logger.info(f"Cached result: {cache_key} (TTL: {ttl}s)")
            return True
            
        except Exception as e:
            logger.warning(f"Cache set error: {e}")
            return False
    
    async def invalidate(
        self,
        intent: Intent = None,
        query: str = None,
        tool: str = None,
    ) -> int:
        """
        Invalidate cache entries.
        
        Args:
            intent: Optional intent type to filter
            query: Optional query to filter
            tool: Optional tool to filter
            
        Returns:
            Number of keys deleted
        """
        if not self.enabled:
            return 0
        
        try:
            # Build pattern
            parts = ["research"]
            if intent:
                parts.append(intent)
            if tool:
                parts.append(tool)
            
            pattern = ":".join(parts) + ":*"
            
            # Find and delete matching keys
            keys = self.redis_client.keys(pattern)
            if keys:
                deleted = self.redis_client.delete(*keys)
                logger.info(f"Invalidated {deleted} cache entries matching {pattern}")
                return deleted
            
            return 0
            
        except Exception as e:
            logger.warning(f"Cache invalidation error: {e}")
            return 0
    
    async def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Cache stats including total entries, size, hit rate
        """
        if not self.enabled:
            return {"enabled": False}
        
        try:
            info = self.redis_client.info("memory")
            
            return {
                "enabled": True,
                "memory_used": info.get("used_memory_human", "N/A"),
                "total_memory": info.get("maxmemory_human", "N/A"),
                "memory_usage_percent": self._calculate_memory_usage(info),
            }
        except Exception as e:
            logger.warning(f"Cache stats error: {e}")
            return {"enabled": True, "error": str(e)}
    
    def _calculate_memory_usage(self, info: Dict) -> float:
        """Calculate memory usage percentage."""
        try:
            used = info.get("used_memory", 0)
            maxmem = info.get("maxmemory", 0)
            if maxmem > 0:
                return (used / maxmem) * 100
        except Exception:
            pass
        return 0.0
    
    def get_ttl_for_intent(self, intent: Intent) -> int:
        """Get cache TTL for a specific intent type."""
        return self.CACHE_TTL.get(intent, 3600)

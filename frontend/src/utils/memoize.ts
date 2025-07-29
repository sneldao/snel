/**
 * Advanced memoization utility with TTL, LRU, and performance tracking
 * 
 * Features:
 * - TTL (time-to-live) based cache expiration
 * - LRU (Least Recently Used) eviction policy
 * - Smart cache key generation from function arguments
 * - Support for async functions
 * - Cache size limits
 * - Cache invalidation methods
 * - Performance metrics
 */

// ======== Type Definitions ========

/**
 * Options for configuring the memoization behavior
 */
export interface MemoizeOptions {
  /** Time-to-live in milliseconds (0 = no expiration) */
  ttl?: number;
  /** Maximum number of items to store in cache (0 = unlimited) */
  maxSize?: number;
  /** Custom key generation function */
  keyGenerator?: (args: any[]) => string;
  /** Track performance metrics */
  trackPerformance?: boolean;
  /** Cache name for debugging */
  name?: string;
}

/**
 * Structure for items stored in the cache
 */
interface CacheItem<T> {
  /** The cached value */
  value: T;
  /** When this item was created */
  created: number;
  /** When this item expires (0 = never) */
  expires: number;
  /** When this item was last accessed */
  lastAccessed: number;
  /** Number of cache hits for this item */
  hits: number;
  /** Execution time of the original function (ms) */
  executionTime?: number;
}

/**
 * Cache performance metrics
 */
export interface CacheMetrics {
  /** Total number of function calls */
  calls: number;
  /** Number of cache hits */
  hits: number;
  /** Number of cache misses */
  misses: number;
  /** Hit rate (hits / calls) */
  hitRate: number;
  /** Average execution time of the original function (ms) */
  avgExecutionTime: number;
  /** Average time saved by using the cache (ms) */
  avgTimeSaved: number;
  /** Total time saved by using the cache (ms) */
  totalTimeSaved: number;
  /** Number of items evicted due to TTL expiration */
  expiredEvictions: number;
  /** Number of items evicted due to LRU policy */
  lruEvictions: number;
  /** Number of items evicted due to size limits */
  sizeEvictions: number;
  /** Current cache size */
  size: number;
  /** Maximum cache size reached */
  maxSizeReached: number;
  /** Cache name */
  name: string;
}

/**
 * Cache control interface returned by memoize
 */
export interface CacheControl<T extends Function> {
  /** The memoized function */
  fn: T;
  /** Clear the entire cache */
  clear: () => void;
  /** Clear a specific cache entry */
  clearKey: (key: string) => void;
  /** Get cache metrics */
  getMetrics: () => CacheMetrics;
  /** Get all cache keys */
  getKeys: () => string[];
  /** Check if a key exists in the cache */
  has: (key: string) => boolean;
  /** Get the size of the cache */
  size: () => number;
  /** Set a new TTL for the cache (ms) */
  setTTL: (ttl: number) => void;
  /** Set a new max size for the cache */
  setMaxSize: (size: number) => void;
}

// ======== Global Registry ========

/**
 * Global registry of all memoized caches for monitoring
 */
const cacheRegistry: Map<string, {
  cache: Map<string, any>,
  metrics: CacheMetrics,
  options: MemoizeOptions
}> = new Map();

// ======== Helper Functions ========

/**
 * Generate a cache key from function arguments
 */
function generateKey(args: any[]): string {
  try {
    // Handle special cases like undefined, functions, circular references
    return JSON.stringify(args, (_, value) => {
      // Handle special types
      if (typeof value === 'function') {
        return `[Function: ${value.name || 'anonymous'}]`;
      }
      if (value instanceof Date) {
        return `[Date: ${value.toISOString()}]`;
      }
      if (value instanceof RegExp) {
        return `[RegExp: ${value.toString()}]`;
      }
      if (value === undefined) {
        return '[undefined]';
      }
      if (value === Infinity) {
        return '[Infinity]';
      }
      if (Number.isNaN(value)) {
        return '[NaN]';
      }
      // Handle DOM nodes and other non-serializable objects
      if (value !== null && typeof value === 'object' && !Array.isArray(value)) {
        if (value.toString && value.toString !== Object.prototype.toString) {
          return `[Object: ${value.toString()}]`;
        }
        // For normal objects, we'll let JSON.stringify handle it
      }
      return value;
    });
  } catch (error) {
    // Fallback for circular structures or other JSON.stringify errors
    return args.map(arg => {
      try {
        if (typeof arg === 'object' && arg !== null) {
          return `obj:${Object.keys(arg).join(',')}`;
        }
        return String(arg);
      } catch (e) {
        return 'unstringifiable';
      }
    }).join('|');
  }
}

/**
 * Check if a cache item has expired
 */
function isExpired<T>(item: CacheItem<T>): boolean {
  return item.expires !== 0 && Date.now() > item.expires;
}

/**
 * Update LRU information for a cache item
 */
function updateLRU<T>(item: CacheItem<T>): void {
  item.lastAccessed = Date.now();
  item.hits++;
}

/**
 * Find the least recently used item in the cache
 */
function findLRUItem<T>(cache: Map<string, CacheItem<T>>): string | null {
  let lruKey: string | null = null;
  let oldest = Infinity;

  for (const [key, item] of cache.entries()) {
    if (item.lastAccessed < oldest) {
      oldest = item.lastAccessed;
      lruKey = key;
    }
  }

  return lruKey;
}

/**
 * Evict items from the cache based on size limits
 */
function evictItems<T>(
  cache: Map<string, CacheItem<T>>,
  maxSize: number,
  metrics: CacheMetrics
): void {
  if (maxSize <= 0 || cache.size <= maxSize) return;

  // Number of items to evict
  const toEvict = cache.size - maxSize;
  
  // Find the least recently used items
  const items = Array.from(cache.entries())
    .sort((a, b) => a[1].lastAccessed - b[1].lastAccessed)
    .slice(0, toEvict);

  // Evict items
  for (const [key] of items) {
    cache.delete(key);
    metrics.lruEvictions++;
  }
}

/**
 * Clean expired items from the cache
 */
function cleanExpired<T>(
  cache: Map<string, CacheItem<T>>,
  metrics: CacheMetrics
): void {
  for (const [key, item] of cache.entries()) {
    if (isExpired(item)) {
      cache.delete(key);
      metrics.expiredEvictions++;
    }
  }
}

// ======== Core Memoization Function ========

/**
 * Create a memoized version of a function with advanced caching features
 * 
 * @param fn The function to memoize
 * @param options Memoization options
 * @returns A memoized function with cache control methods
 */
export function memoize<T extends Function>(
  fn: T,
  options: MemoizeOptions = {}
): CacheControl<T> {
  // Default options
  const {
    ttl = 0, // No expiration by default
    maxSize = 0, // No limit by default
    keyGenerator = generateKey,
    trackPerformance = true,
    name = `cache-${Math.random().toString(36).substring(2, 9)}`
  } = options;

  // Initialize cache and metrics
  const cache = new Map<string, CacheItem<any>>();
  const metrics: CacheMetrics = {
    calls: 0,
    hits: 0,
    misses: 0,
    hitRate: 0,
    avgExecutionTime: 0,
    avgTimeSaved: 0,
    totalTimeSaved: 0,
    expiredEvictions: 0,
    lruEvictions: 0,
    sizeEvictions: 0,
    size: 0,
    maxSizeReached: 0,
    name
  };

  // Register this cache
  cacheRegistry.set(name, { cache, metrics, options });

  // Create the memoized function
  const memoized = function (this: any, ...args: any[]) {
    metrics.calls++;
    metrics.size = cache.size;
    metrics.maxSizeReached = Math.max(metrics.maxSizeReached, cache.size);

    // Generate cache key
    const key = keyGenerator(args);

    // Clean expired items periodically (every 10 calls)
    if (metrics.calls % 10 === 0) {
      cleanExpired(cache, metrics);
    }

    // Check if we have a cached value
    if (cache.has(key)) {
      const item = cache.get(key)!;

      // Check if the item has expired
      if (isExpired(item)) {
        cache.delete(key);
        metrics.expiredEvictions++;
      } else {
        // Cache hit
        updateLRU(item);
        metrics.hits++;
        metrics.hitRate = metrics.hits / metrics.calls;

        // Calculate time saved
        if (trackPerformance && item.executionTime !== undefined) {
          metrics.totalTimeSaved += item.executionTime;
          metrics.avgTimeSaved = metrics.totalTimeSaved / metrics.hits;
        }

        return item.value;
      }
    }

    // Cache miss
    metrics.misses++;
    metrics.hitRate = metrics.hits / metrics.calls;

    // Execute the original function and measure time
    const startTime = trackPerformance ? performance.now() : 0;
    let result;

    try {
      // Execute the original function
      result = fn.apply(this, args);

      // Handle promises
      if (result instanceof Promise) {
        return result.then((value) => {
          const endTime = trackPerformance ? performance.now() : 0;
          const executionTime = trackPerformance ? endTime - startTime : undefined;

          // Store the result in cache
          cache.set(key, {
            value,
            created: Date.now(),
            expires: ttl > 0 ? Date.now() + ttl : 0,
            lastAccessed: Date.now(),
            hits: 1,
            executionTime
          });

          // Update metrics
          if (trackPerformance && executionTime !== undefined) {
            metrics.avgExecutionTime = ((metrics.avgExecutionTime * (metrics.misses - 1)) + executionTime) / metrics.misses;
          }

          // Check if we need to evict items
          if (maxSize > 0 && cache.size > maxSize) {
            evictItems(cache, maxSize, metrics);
          }

          return value;
        });
      }

      // For synchronous functions
      const endTime = trackPerformance ? performance.now() : 0;
      const executionTime = trackPerformance ? endTime - startTime : undefined;

      // Store the result in cache
      cache.set(key, {
        value: result,
        created: Date.now(),
        expires: ttl > 0 ? Date.now() + ttl : 0,
        lastAccessed: Date.now(),
        hits: 1,
        executionTime
      });

      // Update metrics
      if (trackPerformance && executionTime !== undefined) {
        metrics.avgExecutionTime = ((metrics.avgExecutionTime * (metrics.misses - 1)) + executionTime) / metrics.misses;
      }

      // Check if we need to evict items
      if (maxSize > 0 && cache.size > maxSize) {
        evictItems(cache, maxSize, metrics);
      }

      return result;
    } catch (error) {
      // Don't cache errors
      throw error;
    }
  } as unknown as T;

  // Cache control methods
  const cacheControl: CacheControl<T> = {
    fn: memoized,
    clear: () => {
      cache.clear();
      // Reset metrics partially
      metrics.size = 0;
    },
    clearKey: (key: string) => {
      cache.delete(key);
      metrics.size = cache.size;
    },
    getMetrics: () => ({ ...metrics }), // Return a copy
    getKeys: () => Array.from(cache.keys()),
    has: (key: string) => cache.has(key),
    size: () => cache.size,
    setTTL: (newTTL: number) => {
      options.ttl = newTTL;
      // Update registry
      const registryEntry = cacheRegistry.get(name);
      if (registryEntry) {
        registryEntry.options.ttl = newTTL;
      }
    },
    setMaxSize: (newSize: number) => {
      options.maxSize = newSize;
      // Update registry
      const registryEntry = cacheRegistry.get(name);
      if (registryEntry) {
        registryEntry.options.maxSize = newSize;
      }
      // Evict items if needed
      if (newSize > 0 && cache.size > newSize) {
        evictItems(cache, newSize, metrics);
      }
    }
  };

  return cacheControl;
}

// ======== Utility Functions ========

/**
 * Get all registered caches
 */
export function getAllCaches(): { name: string; metrics: CacheMetrics }[] {
  return Array.from(cacheRegistry.entries()).map(([name, { metrics }]) => ({
    name,
    metrics: { ...metrics }
  }));
}

/**
 * Clear all registered caches
 */
export function clearAllCaches(): void {
  for (const [, { cache }] of cacheRegistry.entries()) {
    cache.clear();
  }
}

/**
 * Get metrics for a specific cache
 */
export function getCacheMetrics(name: string): CacheMetrics | undefined {
  const cache = cacheRegistry.get(name);
  return cache ? { ...cache.metrics } : undefined;
}

/**
 * Create a memoized function with a specific TTL
 */
export function memoizeWithTTL<T extends Function>(fn: T, ttl: number): CacheControl<T> {
  return memoize(fn, { ttl });
}

/**
 * Create a size-limited memoized function
 */
export function memoizeWithLimit<T extends Function>(fn: T, maxSize: number): CacheControl<T> {
  return memoize(fn, { maxSize });
}

/**
 * Create a memoized function with both TTL and size limits
 */
export function memoizeLimited<T extends Function>(
  fn: T,
  ttl: number,
  maxSize: number
): CacheControl<T> {
  return memoize(fn, { ttl, maxSize });
}

// Default export
export default memoize;

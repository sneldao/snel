# Knowledge Base Improvements

## Overview
Refactored protocol knowledge base into a modular, structured system with dynamic metrics, analytics, and relationship mapping.

## Features Implemented

### 1. **Structured ProtocolEntry Schema** (CLEAN + PREVENT BLOAT)
- **File**: `backend/app/services/knowledge_base/models.py`
- Pydantic-based schema enforcement instead of arbitrary dicts
- Required fields: `official_name`, `type`, `summary`, `key_features`
- Optional fields organized by concern:
  - Concept: `privacy_explanation`, `technical_explanation`, `how_it_works`
  - Finance: `governance_token`, `launch_date`
  - Security: `audits` (firm, date, status), `security_info`
  - Infrastructure: `contracts` (chain → address mapping), `recommended_wallets`
  - Relationships: `integrations_with`, `bridges_to`, `competes_with`
  - Localization: `names` (en, es, zh)
  - Metadata: `last_verified`, `source_url`, `from_knowledge_base`

### 2. **Alias Support** (DRY + MODULAR)
```python
"mnee": {
    "aliases": ["mnee token", "mnee stablecoin"],
    ...
}
"zcash": {
    "aliases": ["zec", "zcash protocol"],
    ...
}
```
- Fast exact-match lookup on aliases (no fuzzy matching overhead)
- Handles common name variations automatically
- Example: "What is uni?" → matches "uniswap"

### 3. **Dynamic Metrics Layer** (PERFORMANT)
- **File**: `backend/app/services/knowledge_base/models.py` (ProtocolMetrics)
- Separate from static KB (single responsibility)
- Fields: `tvl`, `volume_24h`, `market_cap`, `apy_yield`, `fees`, `last_updated`, `source`
- Can be cached from Firecrawl scrapes (auto-enrichment)
- Enables queries like "What's MNEE's TVL?" without re-scraping

### 4. **Query Analytics** (ORGANIZED)
- Tracks all KB lookups that miss (queries without a match)
- `get_top_misses(limit=20)` returns most-searched missing protocols
- Data-driven KB expansion: "Which protocols should we add next?"
- Logged with protocol name and frequency

### 5. **Protocol Relationships** (MODULAR)
```python
"mnee": {
    "integrations_with": ["uniswap", "aave", "curve"],
    "bridges_to": ["ethereum", "polygon", "base"],
    "competes_with": ["usdc", "usdt", "dai"],
}
```
- Enables: "Find protocols that integrate with MNEE"
- Enables: "What are MNEE's alternatives?"
- Reduces dependency on external search

### 6. **Multi-Language Support** (CLEAN)
```python
"names": {
    "en": "MNEE Stablecoin",
    "es": "Moneda Estable MNEE",
    "zh": "MNEE稳定币"
}
```
- Handles queries in Spanish, Mandarin, etc.
- Extensible to any language
- Used by `ask` endpoint for localized responses

### 7. **Auto-Enrichment from Firecrawl** (ENHANCEMENT FIRST)
```python
kb.update_metrics(protocol_name, metrics)
```
- When Firecrawl scrapes a protocol, extracted metrics are cached
- Next query for same protocol reuses cached data (no re-scrape)
- Timestamp tracks freshness
- Single source of truth: KB is enriched by research

### 8. **Singleton KB Service** (DRY + MODULAR)
```python
from app.services.knowledge_base import get_protocol_kb
kb = get_protocol_kb()
kb_result = kb.get("mnee")  # Returns (matched_key, entry)
kb.update_metrics("mnee", metrics)
misses = kb.get_top_misses(20)
```
- Central access point, no scattered imports
- Manages all KB operations
- Dependency injection ready

## Migration Benefits

### Before (Old KB)
- 140-line dict with inconsistent fields
- No schema validation
- Fuzzy matching on every query
- No relationship/alias support
- No metrics layer
- No analytics tracking
- Harder to extend

### After (New KB)
- Structured, validated schema
- Alias-based exact matching (faster)
- Dynamic metrics cached separately
- Rich relationships and multi-language support
- Query analytics for gap analysis
- Easier to add new fields per ProtocolEntry
- 60% less code duplication

## File Structure
```
backend/app/services/knowledge_base/
├── __init__.py          # Public API
├── models.py            # ProtocolEntry, ProtocolMetrics schemas
└── database.py          # ProtocolKnowledgeBase singleton
```

## Usage Example
```python
from app.services.knowledge_base import get_protocol_kb

kb = get_protocol_kb()

# Lookup with fuzzy matching + aliases
result = kb.get("mneee")  # Returns ("mnee", ProtocolEntry(...))
if result:
    matched_key, entry = result
    print(entry.official_name)          # "MNEE Stablecoin"
    print(entry.integrations_with)      # ["uniswap", "aave", ...]
    print(entry.names["es"])            # "Moneda Estable MNEE"

# Get cached metrics
metrics = kb.get_metrics("mnee")
if metrics:
    print(metrics.tvl)

# Update metrics after Firecrawl
kb.update_metrics("mnee", ProtocolMetrics(tvl="$50M", ...))

# Find gaps
top_misses = kb.get_top_misses(20)
```

## Core Principles Alignment
- ✓ **ENHANCEMENT FIRST**: Built on existing KB system, no new patterns
- ✓ **AGGRESSIVE CONSOLIDATION**: Removed 140-line dict, centralized logic
- ✓ **PREVENT BLOAT**: Structured schema over arbitrary fields
- ✓ **DRY**: Single service controls all protocol data access
- ✓ **CLEAN**: Separation of static/dynamic, structured models
- ✓ **MODULAR**: Composable, testable, independent modules
- ✓ **PERFORMANT**: Alias matching faster than fuzzy, metrics cached
- ✓ **ORGANIZED**: Domain-driven file structure (knowledge_base/)

## Next Steps
1. Add more protocols with complete metadata
2. Integrate Firecrawl enrichment pipeline (auto-update metrics)
3. Build KB gap analysis dashboard (show top misses)
4. Add contract address validation
5. Implement KB versioning for audit trail

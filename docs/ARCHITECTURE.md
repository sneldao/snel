# Architecture & Deployment

## Core Architecture

SNEL is a multi-platform DeFi orchestrator built with **ENHANCEMENT FIRST** principles, providing unified DeFi operations across web, mobile, and agent ecosystems.

### Platform Support
- **Web Application**: https://stable-snel.netlify.app/
- **LINE Mini-dApp**: Mobile-optimized DeFi interface
- **Coral Protocol Agent**: Multi-agent DeFi coordination
- **REST API**: Direct integration capabilities

### Core Components

#### Multi-Platform Orchestrator
```
SNELOrchestrator
├── Platform Detection (WEB_APP, CORAL_AGENT, LINE_MINI_DAPP, API)
├── Service Pool (Brian, OpenAI, Web3Helper, Axelar)
├── Request Deduplication & Caching
└── Platform-Specific Response Formatting
```

#### DeFi Operations
- **Token Swaps**: Multi-chain via Brian API + 0x Protocol
- **Cross-Chain Bridging**: Axelar GMP + LayerZero integration
- **Privacy Bridging**: Zcash integration for private transactions
- **X402 Agentic Payments**: AI-triggered payments on Cronos EVM
- **Portfolio Analysis**: Web3 balance aggregation + AI insights
- **Protocol Research**: AI-powered DeFi protocol analysis
- **Natural Language Processing**: OpenAI-powered command interpretation

#### Supported Networks (19+)
- **Layer 1**: Ethereum, Avalanche, BSC
- **Layer 2**: Base, Arbitrum, Optimism, Polygon
- **Cronos EVM**: Cronos Mainnet, Cronos Testnet (x402 support)
- **Privacy**: Zcash
- **Emerging**: zkSync, Scroll, Linea, Mantle, Blast, Mode, Taiko

### Coral Protocol Integration

#### MCP Adapter Architecture
```
CoralEnvironment → SNELCoralMCPAdapter → SNELOrchestrator
├── SSE/Stdio Protocol Handling
├── Tool Call Mapping (5 DeFi operations)
├── Payment Integration (Crossmint)
└── Health Monitoring & SLA
```

#### Agent Capabilities
1. **execute_swap** - Multi-chain token swaps ($0.10-$0.20)
2. **execute_bridge** - Cross-chain operations ($0.15-$0.30)
3. **execute_x402_payment** - AI-triggered payments on Cronos ($0.05-$0.15)
4. **analyze_portfolio** - Portfolio analysis ($0.05)
5. **research_protocol** - DeFi protocol research ($0.05)
6. **interpret_command** - Natural language processing ($0.01)

## Deployment Guide

### Quick Start

#### Web Application (Live)
- **URL**: https://stable-snel.netlify.app/
- **Status**: Production with real users
- **Features**: Full DeFi operations, portfolio analysis, multi-chain support

#### Local Development
```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

### Platform Deployments

#### 1. Web Application

##### Frontend (Netlify)
```bash
# Build and deploy
npm run build
netlify deploy --prod --dir=.next
```

##### Backend (Cloud)
```bash
# Docker deployment
docker build -t snel-backend .
docker run -p 8000:8000 snel-backend
```

##### Environment Variables
```env
OPENAI_API_KEY=your_openai_key
BRIAN_API_KEY=your_brian_key
REDIS_URL=redis://localhost:6379
```

#### 2. Coral Protocol Agent

##### Registration Process
1. **Email Registration**: hello@coralprotocol.org
2. **Required Files**:
   - coral-agent.toml
   - export_settings.json
   - Dockerfile.coral
   - wallet.toml (Crossmint config)

## Infrastructure Requirements

### Minimum Requirements
- **CPU**: 2 cores
- **RAM**: 4GB
- **Storage**: 20GB SSD
- **Network**: 100Mbps

### Recommended (Production)
- **CPU**: 4 cores
- **RAM**: 8GB
- **Storage**: 50GB SSD
- **Network**: 1Gbps
- **Load Balancer**: Multi-instance

### External Dependencies
- **Redis**: Caching and session storage
- **PostgreSQL**: User data and analytics (optional)
- **CDN**: Static asset delivery
- **Monitoring**: Health checks and alerts

## Monitoring & Observability

### Health Checks
```python
# Application health
GET /health
{
  "status": "healthy",
  "services": {
    "brian": "healthy",
    "openai": "healthy",
    "redis": "healthy"
  }
}
```

### Metrics Collection
- **Request Rate**: Requests per minute/hour
- **Response Time**: Average and P95 latency
- **Error Rate**: Failed requests percentage
- **Service Health**: External API availability

## Security Considerations

### API Security
- **Rate Limiting**: Per-user and global limits
- **CORS**: Restricted origins in production
- **HTTPS**: TLS 1.3 encryption
- **API Keys**: Secure storage and rotation

### Data Protection
- **No PII Storage**: Wallet addresses only
- **Encryption**: At rest and in transit
- **Audit Logs**: All operations logged
- **Access Control**: Role-based permissions

## Scaling Strategy

### Horizontal Scaling
```yaml
# Kubernetes deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: snel-backend
spec:
  replicas: 3
  selector:
    matchLabels:
      app: snel-backend
```

## Backup & Recovery

### Data Backup
- **Database**: Daily automated backups
- **Configuration**: Version-controlled configs
- **Logs**: Centralized log aggregation
- **Secrets**: Secure key backup

### Disaster Recovery
- **RTO**: 4 hours (Recovery Time Objective)
- **RPO**: 1 hour (Recovery Point Objective)
- **Failover**: Automated to backup region
- **Testing**: Monthly DR drills

## Performance Optimization

### Caching Strategy
- **Application Cache**: Redis for API responses
- **CDN Cache**: Static assets and API responses
- **Browser Cache**: Client-side caching headers
- **Database Cache**: Query result caching

### Database Optimization
- **Indexing**: Optimized query performance
- **Connection Pooling**: Efficient resource usage
- **Query Optimization**: Analyzed and tuned queries
- **Partitioning**: Large table optimization

### API Optimization
- **Response Compression**: Gzip compression
- **Pagination**: Large dataset handling
- **Field Selection**: Minimal response payloads
- **Async Processing**: Non-blocking operations

## Implementation Status & Changelog

### Latest: Bot Query Routing & Natural Language Support (Jan 7, 2026)

#### Issues Addressed

**1. Natural Language Queries Returning Generic Errors**
- **Problem**: User query "talk me through using mnee please" → Generic error "I'm not exactly sure how to handle that request"
- **Root Cause**: Regex parser only matched specific keywords ("what is", "tell me about", "research", "explain"), missing common variations
- **Impact**: Users couldn't ask about features in natural language; degraded UX for discovery
- **Status**: ✅ FIXED

**2. AI Classifier Fallback Missing**
- **Problem**: When regex parser fails and AI classifier unavailable (no API key), system returned error instead of graceful fallback
- **Root Cause**: No intermediate fallback between failed AI classification and error guidance
- **Impact**: System less resilient when API keys unavailable or API rate-limited
- **Status**: ✅ FIXED

**3. MNEE Knowledge Not Integrated into Query Handling**
- **Problem**: MNEE in knowledge base but not recognized by contextual processor patterns
- **Root Cause**: ContextualProcessor only had generic patterns, not token-specific ones
- **Impact**: MNEE queries didn't leverage built-in knowledge
- **Status**: ✅ FIXED

### Files Modified
- `backend/app/core/parser/unified_parser.py` (added CONTEXTUAL_QUESTION patterns with early priority)
- `backend/app/services/command_processor.py` (added fallback to CONTEXTUAL_QUESTION when AI fails)
- `backend/app/services/processors/contextual_processor.py` (enhanced patterns + added MNEE facts)

### Natural Language Pattern Additions

Added flexible patterns to catch variations:
```python
CommandType.CONTEXTUAL_QUESTION: [
    # Catches: talk, tell, teach, explain, help, guide, how, show, walk, describe
    # With optional "me", "through", "about"
    {
        "pattern": r"(?:talk|tell|teach|explain|help|guide|how|show|walk|describe)\s+(?:me\s+)?(?:through|about)?",
        "priority": 1
    },
    # Catches: can you help, could you help, how do i, show me, teach me
    {
        "pattern": r"(?:can you help|could you help|how do i|how can i|show me|teach me)\s+",
        "priority": 2
    }
]
```

**Now Successfully Handles:**
- "talk me through using mnee"
- "how do i use mnee"
- "can you help me with mnee"
- "show me how mnee works"
- "teach me about mnee"
- "explain mnee to me"

### MNEE Knowledge Enhancement

Enhanced ContextualProcessor to recognize and respond to MNEE queries:

**Pattern Recognition:**
```python
about_assistant_patterns = [
    # ... existing patterns ...
    "mnee", "stablecoin", "commerce payment", "programmatic money"
]
```

**Knowledge Facts:**
```
MNEE STABLECOIN FEATURES YOU SUPPORT:
- What is MNEE: A programmable USD-backed stablecoin for AI agents, commerce, and automated finance
- Core Capabilities: AI Agent Payments, Commerce Payments, DeFi Integration
- Use Cases: Invoice-referenced payments, autonomous settlement, programmatic transactions
```

### Environment Verification

✅ Production server (`snel-bot`) confirmed with all required API keys:
- OPENAI_API_KEY (set - enables AI classification fallback)
- BRIAN_API_KEY (set)
- FIRECRAWL_API_KEY (set)
- EXA_API_KEY (set)
- ZEROX_API_KEY (set)

### Backward Compatibility

✅ All changes are non-breaking:
- New patterns added early but don't interfere with existing command detection
- Regex parser priority unchanged (specific commands still matched first)
- Existing processors continue to function identically
- Fallback path only activates for previously-erroring queries
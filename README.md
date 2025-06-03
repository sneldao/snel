# SNEL - AI-Powered Cross-Chain DeFi Assistant

> **Smart, Natural, Efficient, Limitless** - Your AI companion for seamless DeFi operations across 16+ blockchain networks.

SNEL transforms complex DeFi operations into simple natural language commands. Execute swaps, bridge assets, and manage your portfolio across multiple blockchains with the power of AI - no more complex interfaces or manual protocol navigation.

## ✨ Key Features

### 🤖 **AI-Powered Interface**

- **Natural language commands**: `"swap 1 ETH for USDC"` or `"bridge $100 to Base"`
- **Context-aware responses** with step-by-step guidance
- **Smart protocol selection** for optimal pricing and gas efficiency

### 🌐 **Multi-Chain Support (16+ Networks)**

- **Layer 1**: Ethereum, Polygon, Avalanche, BNB Chain, Gnosis
- **Layer 2**: Base, Arbitrum, Optimism, Scroll, zkSync Era, Linea, Mantle, Blast, Mode, Taiko
- **Seamless cross-chain operations** with automatic network detection

### 🔄 **Advanced Transaction Handling**

- **Multi-step transaction flows** with clear progress indication
- **Approval + Swap sequences** handled automatically
- **Real-time status updates** with block explorer links
- **Intelligent error handling** with actionable suggestions

### 💱 **DEX Aggregation**

- **0x Protocol** integration for professional-grade liquidity
- **Brian API** for AI-powered DeFi operations
- **Automatic protocol selection** based on chain and trade size
- **Real-time quotes** with gas estimation

### 🔐 **Secure & User-Friendly**

- **ConnectKit/Wagmi** integration with 50+ wallet support
- **Non-custodial** - your keys, your crypto
- **Transaction simulation** before execution
- **Comprehensive error handling** for failed transactions

## 🏗️ Architecture

### Frontend (Next.js 14 + TypeScript)

```
├── 🎨 Chakra UI - Modern, accessible components
├── 🔗 Wagmi + ConnectKit - Web3 wallet integration
├── 🔄 React Query - Efficient data fetching
├── 📱 Responsive design - Mobile-first approach
└── 🎯 TypeScript - Type-safe development
```

### Backend (FastAPI + Python)

```
├── 🚀 FastAPI - High-performance async API
├── 🧠 OpenAI GPT - Natural language processing
├── 🔄 Redis - Session & cache management
├── 🌐 Multi-protocol integration (0x, Brian)
└── 📊 Comprehensive logging & monitoring
```

### Project Structure

```
snel/
├── frontend/          # Next.js application
│   ├── src/
│   │   ├── components/    # React components
│   │   ├── services/      # API & transaction services
│   │   ├── hooks/         # Custom React hooks
│   │   └── types/         # TypeScript definitions
├── backend/           # FastAPI application
│   ├── app/
│   │   ├── api/          # API endpoints
│   │   ├── services/     # Business logic
│   │   ├── protocols/    # DEX integrations
│   │   └── config/       # Configuration
└── docs/             # Documentation
```

## 💬 Usage Examples

### Basic Swaps

```
"swap 1 ETH for USDC"
"swap $100 worth of USDC for WBTC"
"exchange 0.5 BNB for CAKE on BSC"
```

### Cross-Chain Operations

```
"bridge 0.1 ETH from Ethereum to Base"
"move 100 USDC from Polygon to Arbitrum"
```

## 🚀 Quick Start

### Prerequisites

- **Node.js** 18+ and **npm**
- **Python** 3.9+ and **pip**
- **Redis** server
- **API Keys**: OpenAI, 0x Protocol, Brian API, WalletConnect

### 1. Clone & Setup

```bash
git clone <repository-url>
cd snel

# Backend setup
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Frontend setup
cd ../frontend
npm install
```

### 2. Environment Configuration

**Backend `.env`:**

```env
OPENAI_API_KEY=sk-...
ZEROX_API_KEY=your_0x_key
BRIAN_API_KEY=your_brian_key
REDIS_URL=redis://localhost:6379
ENVIRONMENT=development
```

**Frontend `.env.local`:**

```env
NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID=your_project_id
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 3. Launch Application

```bash
# Terminal 1: Start Redis
redis-server

# Terminal 2: Start Backend
cd backend && ./start.sh

# Terminal 3: Start Frontend
cd frontend && npm run dev
```

**🎉 Access at:** http://localhost:3000

## 🔧 Development

### Key Components

**Multi-Step Transaction System:**

- `TransactionFlowService` - Manages complex transaction sequences
- `TransactionProgress` - Visual progress indicator
- `MultiStepTransactionService` - Frontend transaction orchestration

**AI Agent System:**

- Enhanced system prompts with capability awareness
- Context-aware responses based on user's current network
- Intelligent protocol selection and error handling

### API Documentation

**Interactive API docs:** http://localhost:8000/docs

**Key Endpoints:**

- `POST /api/v1/swap/process-command` - Execute swap commands
- `POST /api/v1/chat/process-command` - AI chat interface
- `POST /api/v1/swap/complete-step` - Multi-step transaction handling
- `GET /api/v1/swap/flow-status/{address}` - Transaction flow status

## 🌐 Deployment

**Production URLs:**

- **Frontend**: [https://stable-snel.netlify.app](https://stable-snel.netlify.app)
- **Backend**: Hosted on Northflank with auto-scaling

**Deployment Stack:**

- **Frontend**: Netlify with automatic builds
- **Backend**: Northflank containerized deployment
- **Database**: Redis for session management
- **Monitoring**: Built-in logging and error tracking

## 🏆 Global Agent Hackathon 2025 - Progress Report

### 🎯 **Phase 1: Multi-Agent DeFi Orchestrator - IN PROGRESS**

_Target: Best Use of Agno ($5,000 Grand Prize)_

**Current Status:**
✅ Successfully integrated Agno framework
✅ Created initial Portfolio Management Agent service
✅ Added FastAPI endpoint for Agno integration
✅ Resolved Python environment setup (3.12 + PyYAML 6.0.2)

**Next Steps:**

- [ ] Complete Risk Assessment Agent implementation
- [ ] Integrate Yield Optimization Agent
- [ ] Add MEV Protection Agent
- [ ] Implement cross-agent communication protocols

### 🎯 **Phase 2: Automated Protocol Discovery**

_Target: Best Use of Browser Use ($2,500 Grand Prize) + Groq Integration ($300 Credits)_

**Current Status:**
🔄 Planning Phase

- Identified key integration points for Browser Use
- Mapped Groq API integration for enhanced performance

**Next Steps:**

- [ ] Implement Browser Use for protocol discovery
- [ ] Add Groq-powered market analysis
- [ ] Create automated protocol interaction system
- [ ] Build yield monitoring dashboard

### 📊 **Implementation Timeline (Updated):**

#### **Week 1 (Completed):**

✅ Environment setup and dependency resolution
✅ Agno framework integration
✅ Initial Portfolio Management Agent implementation

#### **Week 2 (Current):**

- [ ] Complete Portfolio Management Agent features
- [ ] Implement Risk Assessment Agent
- [ ] Add Groq API integration for analysis
- [ ] Begin Browser Use integration

#### **Week 3:**

- [ ] Implement protocol discovery automation
- [ ] Build yield optimization system
- [ ] Create automated interaction workflows
- [ ] Add cross-chain portfolio analysis

#### **Week 4:**

- [ ] System integration and testing
- [ ] Performance optimization
- [ ] Security audits
- [ ] Documentation and demo preparation

### 🎥 **Demo Preparation:**

Working on a comprehensive demo video showcasing:

1. Multi-agent portfolio optimization
2. Automated protocol discovery
3. Cross-chain yield optimization
4. Real-time risk assessment

### 🛠️ **Tech Stack Optimization:**

- **Primary Framework:** Agno for multi-agent orchestration
- **Discovery Engine:** Browser Use for protocol automation
- **Performance:** Groq API for enhanced analysis
- **Additional Tools:**
  - MCP.Run for development workflow (using AGNOHACK2025 promo)
  - Exa API integration (using EXA50API credits)
  - Firecrawl for data gathering (using hackathon5k promo)

### 📈 **Success Metrics (Current):**

- **Integration Progress:** 25% complete
- **Performance Benchmarks:** Initial testing phase
- **Risk Assessment:** Framework established
- **User Experience:** Basic flows implemented

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md).

1. **Fork** the repository
2. **Create** a feature branch: `git checkout -b feature/amazing-feature`
3. **Commit** changes: `git commit -m 'Add amazing feature'`
4. **Push** to branch: `git push origin feature/amazing-feature`
5. **Open** a Pull Request

## 📄 License

This project is licensed under the **MIT License** - see [LICENSE](LICENSE) for details.

---

**Built with ❤️ by papa**

# 🏗️ Architecture Improvement Plan

## 📊 Current Code Organization Assessment

**Overall Rating: 7.5/10** - Solid foundation with strategic improvement opportunities

### ✅ Strengths

- Clear domain separation (api/services/models/config)
- Unified command processing architecture
- Good type safety with Pydantic/TypeScript
- Consistent response formats

### 🚨 Critical Issues to Address

- Import chaos & potential circular dependencies
- Configuration scattered across files
- Inconsistent error handling patterns
- Mixed responsibilities in main.py

## 🎯 Improvement Roadmap

### Phase 1: Foundation (Week 1-2)

#### 1.1 Configuration Management

```python
# Create centralized configuration system
backend/app/
├── config/
│   ├── __init__.py
│   ├── settings.py          # Main settings class
│   ├── environments/        # Environment-specific configs
│   │   ├── development.py
│   │   ├── production.py
│   │   └── testing.py
│   └── validation.py        # Config validation
```

#### 1.2 Error Handling Standardization

```python
# Unified error handling system
backend/app/
├── core/
│   ├── exceptions.py        # Custom exception classes
│   ├── error_handlers.py    # Global error handlers
│   └── responses.py         # Standardized response formats
```

#### 1.3 Import Structure Cleanup

```python
# Clean import dependencies
- Remove local imports from methods
- Establish clear dependency injection
- Create proper service layer abstractions
- Fix circular dependency risks
```

### Phase 2: Architecture Enhancement (Week 2-3)

#### 2.1 Service Layer Restructuring

```python
backend/app/
├── services/
│   ├── core/               # Core business services
│   │   ├── command_processor.py
│   │   ├── transaction_manager.py
│   │   └── validation_service.py
│   ├── external/           # External API integrations
│   │   ├── brian/
│   │   ├── exa/
│   │   └── firecrawl/
│   └── domain/             # Domain-specific services
│       ├── portfolio/
│       ├── trading/
│       └── analytics/
```

#### 2.2 Database & Caching Layer

```python
# Add proper data persistence
backend/app/
├── database/
│   ├── models/             # SQLAlchemy models
│   ├── repositories/       # Data access layer
│   ├── migrations/         # Database migrations
│   └── cache/              # Redis caching layer
```

#### 2.3 Monitoring & Observability

```python
# Add comprehensive monitoring
backend/app/
├── monitoring/
│   ├── metrics.py          # Prometheus metrics
│   ├── logging.py          # Structured logging
│   ├── tracing.py          # Request tracing
│   └── health_checks.py    # Service health monitoring
```

### Phase 3: Advanced Features (Week 3-4)

#### 3.1 Event-Driven Architecture

```python
# Add event system for decoupling
backend/app/
├── events/
│   ├── bus.py              # Event bus implementation
│   ├── handlers/           # Event handlers
│   └── publishers/         # Event publishers
```

#### 3.2 Background Processing

```python
# Add job queue system
backend/app/
├── jobs/
│   ├── queue.py            # Job queue (Celery/RQ)
│   ├── tasks/              # Background tasks
│   └── schedulers/         # Scheduled jobs
```

#### 3.3 API Versioning & Documentation

```python
# Proper API versioning
backend/app/api/
├── v1/                     # Current API version
├── v2/                     # Future API version
└── common/                 # Shared API components
```

### Phase 4: Production Readiness (Week 4+)

#### 4.1 Security Enhancements

- Rate limiting per user/IP
- Input sanitization & validation
- API key management
- Request/response encryption

#### 4.2 Performance Optimization

- Database query optimization
- Response caching strategies
- Connection pooling
- Async processing optimization

#### 4.3 Deployment & DevOps

- Docker containerization
- CI/CD pipeline setup
- Environment management
- Monitoring & alerting

## 🚀 Quick Wins (Immediate Impact)

### 1. Configuration Centralization

```python
# Single source of truth for all settings
@dataclass
class Settings:
    # API Configuration
    api_timeout: int = 30
    max_retries: int = 3

    # External Services
    brian_api_url: str = "https://api.brian.ai"
    exa_api_key: str = field(default_factory=lambda: os.getenv("EXA_API_KEY"))

    # Database
    redis_url: str = "redis://localhost:6379"

    # Validation
    def __post_init__(self):
        if not self.exa_api_key:
            raise ValueError("EXA_API_KEY is required")
```

### 2. Standardized Error Responses

```python
# Consistent error format across all endpoints
class APIError(Exception):
    def __init__(self, message: str, code: str, status_code: int = 400):
        self.message = message
        self.code = code
        self.status_code = status_code

@app.exception_handler(APIError)
async def api_error_handler(request: Request, exc: APIError):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "message": exc.message,
                "code": exc.code,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
    )
```

### 3. Dependency Injection

```python
# Clean service dependencies
class ServiceContainer:
    def __init__(self):
        self.settings = Settings()
        self.brian_client = BrianClient(self.settings)
        self.command_processor = CommandProcessor(self.brian_client)

# Use in endpoints
@app.post("/chat/process-command")
async def process_command(
    command: ChatCommand,
    services: ServiceContainer = Depends(get_services)
):
    return await services.command_processor.process(command)
```

## 📈 Expected Outcomes

### Short-term (1-2 weeks)

- ✅ Cleaner, more maintainable code
- ✅ Faster development velocity
- ✅ Reduced bugs from configuration issues
- ✅ Better error debugging

### Medium-term (1 month)

- 🚀 Improved performance with caching
- 🚀 Better monitoring and observability
- 🚀 Easier testing and deployment
- 🚀 More reliable error handling

### Long-term (2-3 months)

- 🎯 Production-ready scalability
- 🎯 Advanced features (real-time updates, analytics)
- 🎯 Multi-environment deployment
- 🎯 Comprehensive monitoring & alerting

## 🎯 Priority Order

1. **🔥 Critical (Do First)**

   - Configuration management
   - Error handling standardization
   - Import structure cleanup

2. **⚡ High Impact**

   - Service layer restructuring
   - Database & caching layer
   - Monitoring setup

3. **📈 Enhancement**

   - Event-driven architecture
   - Background processing
   - Advanced features

4. **🚀 Production**
   - Security hardening
   - Performance optimization
   - DevOps & deployment

- Move long-running analyses to background jobs
- Implement job status tracking
- Handle job retries and failures
- Store progress updates

### 2. WebSocket Migration

Replace current SSE implementation with WebSocket for:

- Bi-directional communication
- Better connection management
- Improved error handling
- Real-time updates with guaranteed delivery

### 3. State Management Enhancement

Implement Redux with persistence:

```typescript
// Core state structure
{
  analyses: {
    active: Map<string, AnalysisProgress>,
    completed: Map<string, AnalysisResponse>,
    cached: Map<string, CachedAnalysis>
  },
  settings: {
    refreshInterval: number,
    cacheTimeout: number
  }
}
```

### 4. High Availability Setup

```yaml
# Basic deployment structure
services:
  api:
    replicas: 3
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]

  redis:
    replicas: 2
    persistence: true

  websocket:
    replicas: 2
```

## Implementation Phases

### Phase 1: Redis Integration

- [x] Redis server setup (COMPLETED)
- [ ] Implement caching for analysis results
- [ ] Add message queue for long-running tasks
- [ ] Add job status tracking

### Phase 2: WebSocket Migration

- [ ] Set up WebSocket server
- [ ] Implement client-side WebSocket handling
- [ ] Migrate existing SSE functionality
- [ ] Add reconnection logic

### Phase 3: State Management

- [ ] Implement Redux store
- [ ] Add persistence layer
- [ ] Migrate existing state
- [ ] Add offline support

### Phase 4: Scaling

- [ ] Configure load balancing
- [ ] Set up monitoring
- [ ] Implement logging
- [ ] Add health checks

## Technical Requirements

### Backend

- Python 3.8+
- FastAPI
- Redis 8.0+
- WebSocket support
- Background task processing

### Frontend

- React 18+
- Redux Toolkit
- TypeScript
- WebSocket client

### Infrastructure

- Docker
- Redis cluster
- Load balancer
- Monitoring tools

## Getting Started

1. Ensure Redis is running:

```bash
redis-server
```

2. Install dependencies:

```bash
pip install -r requirements.txt
npm install
```

3. Run development servers:

```bash
# Backend
uvicorn app.main:app --reload

# Frontend
npm run dev
```

## Monitoring and Maintenance

We'll implement:

- Prometheus metrics
- Grafana dashboards
- Error tracking
- Performance monitoring
- Automated backups

## Security Considerations

- Implement rate limiting
- Add request validation
- Set up proper authentication
- Configure CORS properly
- Secure WebSocket connections
- Encrypt sensitive data

## Contributing

1. Create a feature branch
2. Implement changes
3. Add tests
4. Submit PR
5. Code review
6. Merge after approval

## Next Steps

1. Begin with Redis integration for caching
2. Set up background job processing
3. Implement WebSocket server
4. Add state management
5. Configure monitoring
6. Deploy improvements incrementally

## Notes

- Keep existing functionality working during migration
- Implement changes incrementally
- Add tests for new features
- Document all changes
- Monitor performance impacts

# 🏗️ SNEL Architecture Overview

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
- **Portfolio Analysis**: Web3 balance aggregation + AI insights
- **Protocol Research**: AI-powered DeFi protocol analysis
- **Natural Language Processing**: OpenAI-powered command interpretation

#### Supported Networks (17+)
- **Layer 1**: Ethereum, Avalanche, BSC
- **Layer 2**: Base, Arbitrum, Optimism, Polygon
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
3. **analyze_portfolio** - Portfolio analysis ($0.05)
4. **research_protocol** - Protocol research ($0.08)
5. **general_defi_help** - Natural language assistance ($0.03)

### Performance Optimizations

#### Caching Strategy
- **Request Deduplication**: Prevent duplicate API calls
- **Platform-Specific Caching**: Web (portfolio), Coral (analysis), LINE (quotes)
- **Service Health Monitoring**: Circuit breakers for external APIs
- **Connection Pooling**: Reused HTTP connections

#### Error Handling
- **Graceful Degradation**: Fallback to basic functionality
- **Circuit Breakers**: Automatic service isolation
- **Retry Logic**: Exponential backoff for transient failures
- **Health Checks**: Continuous service monitoring

### Security Model

#### API Key Management
- **Environment Variables**: No hardcoded credentials
- **Service Isolation**: Separate API keys per service
- **Rate Limiting**: Per-service request limits
- **Audit Logging**: All operations logged

#### Transaction Safety
- **Read-Only Operations**: No direct wallet access
- **Quote Generation**: Simulation before execution
- **User Confirmation**: Required for all transactions
- **Gas Estimation**: Accurate cost prediction

### Deployment Architecture

#### Web Application
- **Frontend**: Next.js on Netlify
- **Backend**: FastAPI on cloud infrastructure
- **Database**: Redis for caching
- **CDN**: Global content delivery

#### Coral Agent
- **Container**: Docker with health checks
- **Registry**: Coral Protocol marketplace
- **Billing**: Crossmint payment integration
- **Monitoring**: Comprehensive metrics

#### LINE Mini-dApp
- **LIFF Integration**: LINE Front-end Framework
- **Mobile Optimization**: Touch-friendly interface
- **Push Notifications**: Transaction updates
- **Wallet Integration**: LINE Pay compatibility

### Data Flow

#### Request Processing
```
User Input → Platform Detection → Operation Mapping → Service Execution → Response Formatting
```

#### Multi-Agent Coordination (Coral)
```
Agent A (SNEL) → Tool Call → Orchestrator → Result → Agent B (Market Analysis)
```

#### Cross-Chain Operations
```
Source Chain → Bridge Protocol → Destination Chain → Confirmation → User Notification
```

### Scalability Design

#### Horizontal Scaling
- **Stateless Services**: No server-side sessions
- **Load Balancing**: Multiple orchestrator instances
- **Database Sharding**: Chain-specific data partitioning
- **CDN Distribution**: Global content delivery

#### Performance Metrics
- **Response Time**: <2s for quotes, <5s for analysis
- **Throughput**: 1000+ requests/minute
- **Uptime**: 99.5% SLA guarantee
- **Error Rate**: <1% for core operations

### Integration Points

#### External Services
- **Brian API**: DeFi operation execution
- **OpenAI**: Natural language processing
- **Axelar**: Cross-chain messaging
- **Alchemy/Infura**: Blockchain RPC
- **CoinGecko**: Price data

#### Partner Protocols
- **Uniswap**: DEX aggregation
- **Aave**: Lending protocols
- **Compound**: Yield farming
- **Curve**: Stablecoin swaps
- **1inch**: DEX optimization

This architecture enables SNEL to provide consistent, high-performance DeFi operations across all platforms while maintaining security, scalability, and user experience excellence.
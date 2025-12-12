# 🏗️ SNEL Architecture & Deployment Overview

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
4. **research_protocol** - DeFi protocol research ($0.05)
5. **interpret_command** - Natural language processing ($0.01)

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

##### Docker Build
```bash
cd backend/app/agents
docker build -f Dockerfile.coral -t snel-coral-agent .
```

##### Agent Configuration
```toml
[agent]
name = "snel-defi-agent"
version = "1.0.0"

[agent.runtime]
type = "docker"
dockerfile = "Dockerfile.coral"

[agent.options]
openai_api_key = { type = "string", required = true }
brian_api_key = { type = "string", required = true }
```

##### Deployment Commands
```bash
# Local testing (devmode)
./start_devmode.sh

# Production deployment
# (Handled by Coral Server orchestration)
```

#### 3. LINE Mini-dApp

##### LIFF Configuration
```javascript
// LINE Front-end Framework setup
liff.init({ liffId: 'your-liff-id' })
  .then(() => {
    // Initialize SNEL mini-dApp
  })
```

##### Mobile Optimization
- Touch-friendly interface
- Reduced feature set for mobile
- LINE Pay integration
- Push notifications

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

## Configuration Management

### Environment-Specific Configs

#### Development
```env
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=DEBUG
REDIS_URL=redis://localhost:6379
```

#### Staging
```env
ENVIRONMENT=staging
DEBUG=false
LOG_LEVEL=INFO
REDIS_URL=redis://staging-redis:6379
```

#### Production
```env
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=WARNING
REDIS_URL=redis://prod-redis:6379
ALLOWED_ORIGINS=https://stable-snel.netlify.app
```

### API Key Management
- **Development**: Local .env files
- **Staging/Production**: Environment variables
- **Coral Agent**: Coral orchestration provides keys
- **Security**: Never commit keys to repository

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

### Logging Strategy
```python
# Structured logging
logger.info("DeFi operation", extra={
    "operation": "swap",
    "chain_id": 1,
    "user_id": "user123",
    "duration": 1.5
})
```

### Alerting Rules
- **High Error Rate**: >5% errors in 5 minutes
- **Slow Response**: >5s average response time
- **Service Down**: Health check failures
- **High Load**: >80% CPU/memory usage

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

### Network Security
- **Firewall**: Restricted port access
- **VPN**: Secure admin access
- **DDoS Protection**: CDN-based mitigation
- **Intrusion Detection**: Automated monitoring

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

### Database Scaling
- **Read Replicas**: Multiple read instances
- **Sharding**: Chain-specific data partitioning
- **Caching**: Redis for frequent queries
- **Connection Pooling**: Efficient DB connections

### CDN Configuration
- **Static Assets**: Images, CSS, JS files
- **API Responses**: Cacheable endpoints
- **Geographic Distribution**: Global edge locations
- **Cache Invalidation**: Automated on deployments

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

### Rollback Strategy
```bash
# Quick rollback for deployments
git revert <commit-hash>
docker build -t snel-backend:rollback .
kubectl set image deployment/snel-backend app=snel-backend:rollback
```

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

This deployment guide ensures SNEL can be reliably deployed across all platforms while maintaining security, performance, and scalability requirements.
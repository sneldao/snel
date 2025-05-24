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

## 🏆 Global Agent Hackathon 2025 - Roadmap

SNEL is participating in the Global Agent Hackathon with ambitious enhancements to transform our platform into the ultimate AI-powered DeFi operating system.

### 🎯 **Phase 1: Multi-Agent DeFi Orchestrator**

_Target: Best Use of Agno ($5,000 Grand Prize)_

**"SNEL Multi-Agent DeFi Orchestrator"** - Transform SNEL into a sophisticated multi-agent system using Agno:

#### 🤖 **Core Agent Enhancement:**

**Portfolio Management Agent:**

- Analyzes user's holdings across all 16+ supported chains
- Provides intelligent rebalancing suggestions based on risk tolerance
- **Stablecoin Risk Assessment**: Specialized focus on stablecoin portfolio vs other assets
- Helps users clearly assess their level of risk exposure
- Optimizes portfolio allocation according to user preferences (conservative, moderate, aggressive)
- Cross-chain portfolio optimization for gas efficiency

**Risk Assessment Agent:**

- Real-time evaluation of smart contract risks and protocol security
- Market volatility analysis and correlation assessment
- Impermanent loss calculations for LP positions
- Stablecoin depeg risk monitoring (USDC, USDT, DAI, etc.)
- Regulatory risk assessment across different jurisdictions

**Yield Optimization Agent:**

- Discovers optimal yield farming opportunities across protocols
- Compares APY vs risk ratios for informed decision making
- Automated yield strategy execution with user approval
- Stablecoin-specific yield opportunities (Aave, Compound, Curve)

**MEV Protection Agent:**

- Detects and prevents MEV attacks during transactions
- Optimal transaction timing and routing
- Private mempool integration for sensitive transactions

#### 💬 **Enhanced User Experience:**

```
User: "Optimize my portfolio - I have 60% stablecoins but want more yield"
→ Portfolio Agent: Analyzes current allocation across chains
→ Risk Agent: Assesses market conditions and user risk tolerance
→ Yield Agent: Finds optimal stablecoin yield strategies
→ Result: "Move 20% USDC to Aave on Polygon (8.5% APY), keep 40% stable for safety"
```

### 🎯 **Phase 2: Automated Protocol Discovery**

_Target: Best Use of Browser Use ($2,500 Grand Prize)_

**"SNEL Stable Scout"** - Add automated protocol discovery and interaction using Browser Use:

#### 🔍 **Protocol Discovery Engine:**

**Stablecoin-Focused Discovery:**

- Automatically scout new DeFi protocols with stablecoin opportunities
- Monitor DeFiLlama, CoinGecko, and protocol announcements
- Track new stablecoin yield farming pools and strategies
- Identify emerging stablecoin protocols and their risk profiles

**Yield Opportunity Monitoring:**

- Real-time tracking of APY changes across protocols
- Alert system for new high-yield stablecoin opportunities
- Automated risk assessment of new protocols
- Historical yield performance analysis

**Market Intelligence:**

- Monitor crypto Twitter, Discord, and forums for alpha
- Track whale movements and large stablecoin transfers
- Sentiment analysis for market timing
- Early detection of protocol issues or exploits

#### 🤖 **Automated Interactions:**

- **Governance Participation**: Auto-vote on DAO proposals based on user preferences
- **Airdrop Optimization**: Strategic protocol interactions for potential airdrops
- **Portfolio Rebalancing**: Automated execution of agent recommendations
- **Yield Harvesting**: Automatic compound and reinvestment strategies

### 🚀 **Implementation Timeline:**

#### **Week 1-2: Multi-Agent Foundation**

- [ ] Integrate Agno framework
- [ ] Implement Portfolio Management Agent
- [ ] Build Risk Assessment Agent core logic
- [ ] Create agent communication protocols

#### **Week 3: Stablecoin Specialization**

- [ ] Develop stablecoin risk assessment algorithms
- [ ] Implement cross-chain portfolio analysis
- [ ] Build yield optimization for stablecoin strategies
- [ ] Create user preference learning system

#### **Week 4: Browser Automation**

- [ ] Integrate Browser Use framework
- [ ] Implement protocol discovery automation
- [ ] Build yield monitoring system
- [ ] Create automated interaction workflows

#### **Week 5: Integration & Testing**

- [ ] Connect multi-agent system with browser automation
- [ ] Comprehensive testing across all supported chains
- [ ] User interface enhancements for new features
- [ ] Performance optimization and security audits

### 📊 **Success Metrics:**

- **Portfolio Optimization**: 15%+ improvement in risk-adjusted returns
- **Discovery Efficiency**: 50+ new protocols discovered and assessed weekly
- **User Engagement**: 3x increase in transaction volume through intelligent recommendations
- **Risk Reduction**: 25% reduction in user exposure to high-risk protocols

### 🎬 **Demo Scenarios:**

1. **"I want to optimize my $50k stablecoin portfolio for maximum yield with medium risk"**
2. **"Find me the best new stablecoin farming opportunities this week"**
3. **"Rebalance my portfolio to reduce risk while maintaining 8%+ APY"**
4. **"Monitor the market and alert me of any stablecoin depeg risks"**

---

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

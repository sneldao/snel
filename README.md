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

### Portfolio Management

```
"show my ETH balance"
"check my portfolio on Base"
"what's my USDC balance across all chains"
```

### Market Information

```
"what's the price of ETH?"
"show me USDC/ETH rate"
"get current gas prices on Ethereum"
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

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md).

1. **Fork** the repository
2. **Create** a feature branch: `git checkout -b feature/amazing-feature`
3. **Commit** changes: `git commit -m 'Add amazing feature'`
4. **Push** to branch: `git push origin feature/amazing-feature`
5. **Open** a Pull Request

## 📄 License

This project is licensed under the **MIT License** - see [LICENSE](LICENSE) for details.

## 🆘 Support

- **Issues**: [GitHub Issues](https://github.com/your-repo/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-repo/discussions)
- **Documentation**: [Wiki](https://github.com/your-repo/wiki)

---

**Built with ❤️ for the DeFi community**

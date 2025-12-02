# SNEL - AI-Powered Cross-Chain DeFi Assistant

> **Smart, Natural, Efficient, Limitless** - Your AI companion for seamless DeFi operations across 16+ blockchain networks.

SNEL transforms complex DeFi operations into simple natural language commands. Execute swaps, bridge assets, and manage your portfolio across multiple blockchains with the power of AI - no more complex interfaces or manual protocol navigation.

## ✨ Key Features

- **🤖 AI-Powered Interface**: Use natural language commands like `"swap 1 ETH for USDC on Base"` or `"swap $100 of USDC for ETH"`.
- **🌐 Multi-Chain Support**: Operates on 16+ networks including Ethereum, Polygon, Base, and Arbitrum.
- **🔄 Advanced Transaction Handling**: Automatically handles multi-step processes like approvals and swaps with real-time status updates.
- **💱 Cross-Chain Protocol Integration**: Integrates with Axelar, 0x, and more for secure and efficient cross-chain operations.
- **🛡️ Privacy Bridging**: Bridge assets to privacy-preserving chains like Zcash using Axelar GMP.
- **💰 Smart Amount Conversion**: Automatically converts USD amounts to token amounts using real-time price data from CoinGecko.
- **🔐 Secure & User-Friendly**: Non-custodial, supports 50+ wallets, and provides transaction simulation.

## 🏗️ Architecture

- **Frontend**: Next.js 14, TypeScript, Chakra UI, Wagmi/ConnectKit.
- **Backend**: FastAPI (Python), OpenAI GPT, Redis.

### Project Structure

```
snel/
├── frontend/          # Next.js application
├── backend/           # FastAPI application
├── docs/              # Documentation
│   ├── ARCHITECTURE_FOUNDATION.md    # Core architecture & foundation
│   ├── GMP_INTEGRATION.md            # GMP integration guide
│   └── CHAIN_INTEGRATIONS_DEPLOYMENT.md  # Chain integrations & deployment
└── public/           # Static assets
```

### 📚 Documentation

- **[Architecture & Foundation](docs/ARCHITECTURE_FOUNDATION.md)** - Core architecture, foundation upgrades, and current status
- **[GMP Integration](docs/GMP_INTEGRATION.md)** - General Message Passing integration guide and implementation
- **[Chain Integrations & Deployment](docs/CHAIN_INTEGRATIONS_DEPLOYMENT.md)** - Blockchain integrations and deployment guides
- **[Privacy Education Implementation](PRIVACY_EDUCATION_IMPLEMENTATION.md)** - Zcash privacy bridging, user education, and real-time status tracking

### Supported Swap Commands

- `swap 1 ETH for USDC` - Standard token amount swap
- `swap $100 of USDC for ETH` - USD amount converted to token amount
- `swap $50 worth of ETH for USDC` - USD amount converted to token amount
- `swap 100 USDC to DAI on Polygon` - Cross-chain swap
- `bridge 1 ETH to Zcash` - Privacy bridge via Axelar
- `make my 100 USDC private` - Privacy-preserving cross-chain transfer

## 🚀 Quick Start

### Prerequisites

- **Node.js** 18+ and **npm**
- **Python** 3.9+ and **pip**
- **Redis** server
- **API Keys**: OpenAI, 0x Protocol etc.

### 1. Clone & Setup

```bash
git clone https://github.com/your-repo/snel.git
cd snel

# Backend setup
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Frontend setup
cd ../frontend
npm install
```

### 2. Environment Configuration

Configure your `.env` files in both `backend` and `frontend` directories using the `.env.example` files as a template.

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

## 🛣️ Roadmap

Our goal is to continuously improve SNEL. Here are some of our future plans:

### Phase 1: Foundation Refinement

- Centralized configuration management.
- Standardized error handling.
- Import structure cleanup.

### Phase 2: Architecture Enhancement

- Service layer restructuring.
- Add database & caching layer.
- Enhanced monitoring & observability.

### Phase 3: Advanced Features

- Event-driven architecture.
- Background processing for long-running tasks.
- API versioning.

### Phase 4: Production Readiness

- Security enhancements.
- Performance optimization.
- CI/CD pipeline improvements.

## 🤝 Contributing

We welcome contributions!

1. **Fork** the repository
2. **Create** a feature branch: `git checkout -b feature/amazing-feature`
3. **Commit** changes: `git commit -m 'Add amazing feature'`
4. **Push** to branch: `git push origin feature/amazing-feature`
5. **Open** a Pull Request

## 📄 License

This project is licensed under the **MIT License**.

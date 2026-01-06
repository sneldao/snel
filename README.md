# SNEL - AI-Powered Cross-Chain DeFi Assistant

> **Smart, Natural, Efficient, Limitless** - Your AI companion for seamless DeFi operations across 16+ blockchain networks.

SNEL transforms complex DeFi operations into simple natural language commands. Execute swaps, bridge assets, and manage your portfolio across multiple blockchains with the power of AI - no more complex interfaces or manual protocol navigation.

**Hackathon Track**: Payments Track - MNEE Stablecoin Integration

**MNEE Integration**: SNEL supports MNEE (ERC-20 Programmable Stablecoin) for commerce payments with invoice references on Ethereum mainnet. Contract: `0x8ccedbAe4916b79da7F3F612EfB2EB93A2bFD6cF`

## ✨ Key Features

- **🤖 AI-Powered Interface**: Use natural language commands like `"swap 1 ETH for USDC on Base"`, `"pay $100 MNEE to merchant for order #1234"`, or `"swap $100 of USDC for ETH"`.
- **🌐 Multi-Chain Support**: Operates on 16+ networks including Ethereum, Polygon, Base, and Arbitrum.
- **💳 MNEE Commerce Payments**: Native support for MNEE stablecoin with invoice references for business-to-business transactions.
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
│   ├── MAIN.md                 # Core architecture & deployment
│   ├── PRIVACY.md              # Privacy features & Zcash integration
│   ├── INTEGRATIONS.md         # LINE & WalletConnect integration
│   └── ROADMAP.md              # Hackathon roadmap & implementation
└── public/           # Static assets
```

### 📚 Documentation

All project documentation has been consolidated into four main files in the [docs/](docs/) directory:

- **[MAIN.md](docs/MAIN.md)** - Core architecture and deployment information
- **[PRIVACY.md](docs/PRIVACY.md)** - Privacy features and Zcash integration
- **[INTEGRATIONS.md](docs/INTEGRATIONS.md)** - LINE Mini-dApp and WalletConnect integration
- **[ROADMAP.md](docs/ROADMAP.md)** - Hackathon roadmap and implementation plan

See the [docs/README.md](docs/README.md) for a complete overview of the documentation structure.

### Supported Commands

**Token Swaps & Transfers**:
- `swap 1 ETH for USDC` - Standard token amount swap
- `swap $100 of USDC for ETH` - USD amount converted to token amount
- `swap $50 worth of ETH for USDC` - USD amount converted to token amount
- `swap 100 USDC to DAI on Polygon` - Cross-chain swap

**MNEE Commerce Payments**:
- `pay $100 MNEE to merchant for order #1234` - MNEE payment with invoice reference
- `send 50 MNEE to 0x... for invoice INV-001` - Direct MNEE transfer with memo

**Privacy & Bridging**:
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

## 🏆 Hackathon Submission

**Track**: Payments Track  
**Focus**: MNEE Stablecoin Integration for Programmable Commerce  
**Contract**: `0x8ccedbAe4916b79da7F3F612EfB2EB93A2bFD6cF` (Ethereum Mainnet)

SNEL integrates MNEE stablecoin as a native payment option, enabling:
- Natural language MNEE payment commands
- Invoice reference support for business transactions
- Seamless USD to MNEE conversion
- AI-powered commerce transaction routing

See our detailed [ROADMAP.md](docs/ROADMAP.md) for our hackathon plans and future development.

## 🤝 Contributing

We welcome contributions!

1. **Fork** the repository
2. **Create** a feature branch: `git checkout -b feature/amazing-feature`
3. **Commit** changes: `git commit -m 'Add amazing feature'`
4. **Push** to branch: `git push origin feature/amazing-feature`
5. **Open** a Pull Request

## 📄 License

This project is licensed under the **MIT License**. See the [LICENSE](LICENSE) file for full details.

All third-party dependencies are licensed under permissive open-source licenses (MIT, Apache 2.0, ISC). See [package.json](package.json), [frontend/package.json](frontend/package.json) for dependency details.
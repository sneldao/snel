# SNEL - AI-Powered Cross-Chain DeFi Assistant

> **Smart, Natural, Efficient, Limitless** - Your AI companion for seamless DeFi operations across 16+ blockchain networks.

SNEL transforms complex DeFi operations into simple natural language commands. Execute swaps, bridge assets, and manage your portfolio across multiple blockchains with the power of AI - no more complex interfaces or manual protocol navigation.

**Active Hackathon**: Cronos x402 Paytech Hackathon ([DoraHacks](https://dorahacks.io/hackathon/cronos-x402/detail))  
**Deadline**: January 23, 2026  
**Previous Track**: MNEE Programmable Stablecoin ([Devpost](https://mnee-eth.devpost.com/))

**MNEE Integration**: SNEL supports MNEE (ERC-20 Programmable Stablecoin) as a native currency for AI-driven payments and commerce.
- **Contract**: `0x8ccedbAe4916b79da7F3F612EfB2EB93A2bFD6cF` (Ethereum Mainnet)
- **Use Case**: Programmable B2B payments, automated invoicing, and agent-to-agent settlement using natural language.

## ✨ Key Features

- **🤖 AI-Powered Interface**: Use natural language commands like `"swap 1 ETH for USDC on Base"`, `"pay 1 USDC to recipient on cronos"`, or `"swap $100 of USDC for ETH"`.
- **🌐 Multi-Chain Support**: Operates on 19+ networks including Ethereum, Polygon, Base, Arbitrum, and Cronos EVM.
- **💳 X402 Agentic Payments**: AI-triggered payments with EIP-712 signing on Cronos testnet/mainnet and Ethereum. Supports USDC (Cronos) and MNEE (Ethereum).
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

**X402 Agentic Payments**:
- `pay agent 10 USDC for API calls` - AI-triggered payment on Cronos
- `setup weekly payment of 100 USDC to supplier.eth` - Recurring automated payment
- `process batch settlement for contractors` - Multi-recipient batch payment

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
git clone https://github.com/sneldao/snel.git
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

### 4. Test X402 Payment (Cronos Testnet)

1. Connect wallet to Cronos Testnet (Chain ID: 338)
2. Get testnet tokens:
   - TCRO: https://cronos.org/faucet
   - devUSDC.e: https://faucet.cronos.org
3. Type command: `pay 1 USDC to 0x1234567890123456789012345678901234567890 on cronos`
4. Sign transaction in wallet
5. See success message with tx hash

## 🏆 Cronos x402 Hackathon Submission

**Hackathon**: [Cronos x402 Paytech Hackathon](https://dorahacks.io/hackathon/cronos-x402/detail)  
**Track**: Main Track (x402 Applications) + Best x402 AI Agentic Finance Solution  
**Prize Pool**: $42,000  
**Deadline**: January 23, 2026

### Implementation Status

- ✅ **Phase 1**: Backend x402 integration validated (facilitator tests: 15/15 passing)
- ✅ **Phase 2**: Frontend payment flow complete (chat → confirmation → signing → settlement)
- ⏳ **Phase 3**: End-to-end testing on Cronos Testnet
- 📋 **Phase 4**: Demo video + DoraHacks submission

### How X402 Payments Work in SNEL

```
User Command: "pay 1 USDC to recipient on cronos"
    ↓
Natural language parsing (backend)
    ↓
Detect X402_PAYMENT command type
    ↓
Frontend shows payment confirmation
    ↓
User signs with EIP-712 (Wagmi)
    ↓
Backend submits to x402 facilitator
    ↓
On-chain settlement on Cronos EVM
    ↓
Success confirmation with tx hash
```

### Key Features Implemented

- **EIP-712 Signing**: Secure, user-controlled signatures with full message transparency
- **Multi-Network**: Cronos testnet/mainnet (USDC) and Ethereum (MNEE)
- **Natural Language**: Commands like `"pay 1 USDC to 0x... on cronos"`
- **Non-Custodial**: User signs directly, backend never holds private keys
- **Error Handling**: Clear feedback for all failure cases
- **Type Safety**: 100% TypeScript implementation

### Technical Stack

**Backend**: FastAPI (Python) + x402 Adapter + EIP-712 signing  
**Frontend**: Next.js + React + Wagmi + Chakra UI  
**Blockchain**: Cronos EVM + x402 Facilitator API  
**Wallet**: Wagmi (MetaMask, WalletConnect support)  

See [docs/PAYMENTS.md](docs/PAYMENTS.md) for detailed payment architecture and API specs.

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
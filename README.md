# SNEL - Cross-Chain Crypto Assistant

SNEL is a modern DeFi platform with a Next.js frontend and FastAPI backend that helps users swap tokens, bridge assets across chains, and manage their crypto portfolio through natural language interactions.

## 🌟 Key Features

- **Multi-Chain Support**: Ethereum, Base, Arbitrum, Optimism, Polygon, Avalanche, Scroll, BSC, Linea, Mantle, Blast, Mode, Gnosis, zkSync Era, Taiko, and Starknet
- **Protocol Integration**: 0x API and Brian API with automatic protocol selection
- **Natural Language Interface**: Chat-like interaction for all operations
- **Cross-Chain Operations**: Seamless token swaps and bridging across chains
- **Portfolio Management**: Balance checking and transaction monitoring
- **Modern UI**: Responsive Next.js frontend with real-time updates and wallet integration

## 🏗️ Architecture

```
snel/
├── backend/           # FastAPI backend service
│   └── app/
│       ├── api/      # API endpoints
│       ├── protocols/ # Protocol implementations
│       ├── services/ # Business logic
│       └── config/   # Configuration
├── frontend/         # Next.js web application
    ├── components/   # React components
    ├── pages/       # Next.js pages
    └── hooks/       # Custom React hooks
```

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- Redis (optional)

### Setup

1. Clone and install dependencies:

```bash
git clone https://github.com/sneldao/snel.git
cd snel

# Backend
pip install -r requirements.txt

# Frontend
cd frontend && npm install
```

2. Configure environment:

```bash
# Create .env file with:
NEXT_PUBLIC_API_URL=http://localhost:8000
ZEROX_API_KEY=your_0x_api_key
BRIAN_API_KEY=your_brian_api_key
REDIS_URL=redis://localhost:6379/0  # Optional
```

3. Run development servers:

```bash
make dev  # Starts both backend and frontend
```

## 🌐 Deployment

The application is deployed across multiple platforms for optimal performance:

- **Frontend**: Deployed on Netlify with automatic builds from the main branch

  - Production: [https://stable-snel.netlify.app](https://stable-snel.netlify.app)
  - Preview deployments for pull requests

- **Backend**: Hosted on Northflank for scalability
  - Containerized deployment with automatic scaling
  - Built-in monitoring and logging
  - Redis integration for state management

## 🗺️ Roadmap

1. **Bot Mode Implementation**

   - Fast, stateless API endpoints
   - Direct protocol integrations
   - Optimized for UI elements and power users

2. **Protocol Expansion**

   - Additional DEX aggregators
   - More chain-specific protocols
   - Cross-chain messaging protocols

3. **Advanced Features**

   - Portfolio analytics
   - DeFi strategy recommendations
   - Gas optimization across chains

4. **Platform Integration**
   - Mobile app development
   - Browser extension
   - Additional messaging platforms

## 📄 License

[MIT License](LICENSE)

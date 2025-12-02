# SNEL - AI-Powered Cross-Chain DeFi Assistant

## Project Overview

SNEL (Smart, Natural, Efficient, Limitless) is an AI-powered cross-chain DeFi assistant that transforms complex DeFi operations into simple natural language commands. The project enables users to execute swaps, bridge assets, and manage portfolios across 16+ blockchain networks using AI.

## Architecture

- **Frontend**: Next.js 14, TypeScript, Chakra UI, Wagmi/ConnectKit
- **Backend**: FastAPI (Python), OpenAI GPT, Redis
- **Multi-Chain Support**: 16+ networks including Ethereum, Polygon, Base, and Arbitrum
- **Protocol Integration**: Axelar, 0x, and other cross-chain protocols

## Key Features

- AI-powered natural language interface
- Multi-chain DeFi operations
- Advanced transaction handling with real-time status updates
- Cross-chain protocol integration
- Smart amount conversion using real-time price data
- Secure, non-custodial operations with 50+ wallet support
- **Privacy Bridging**: Bridge assets to Zcash for enhanced transaction privacy

## Project Structure

```
snel/
├── frontend/          # Next.js application
├── backend/           # FastAPI application
├── docs/              # Documentation
├── scripts/           # Utility scripts
└── public/            # Static assets
```

## Development Workflow

1. **Setup**: Clone repository and install dependencies
2. **Configuration**: Set up environment variables for both frontend and backend
3. **Development**: Run Redis, backend (FastAPI), and frontend (Next.js) concurrently
4. **Testing**: Test DeFi operations across different blockchain networks

## Supported Operations

- Token swaps with natural language commands
- Cross-chain asset bridging
- Portfolio management and analysis
- Real-time transaction monitoring
- USD amount to token conversion

## Technology Stack

### Frontend
- Next.js 14 with TypeScript
- Chakra UI for component library
- Wagmi/ConnectKit for wallet integration
- Web3 libraries for blockchain interaction

### Backend
- FastAPI for API development
- OpenAI GPT for natural language processing
- Redis for caching and session management
- Python libraries for blockchain integration

## Core Principles

- **ENHANCEMENT FIRST**: Always prioritize enhancing existing components over creating new ones
- **AGGRESSIVE CONSOLIDATION**: Delete unnecessary code rather than deprecating
- **PREVENT BLOAT**: Systematically audit and consolidate before adding new features
- **DRY**: Single source of truth for all shared logic
- **CLEAN**: Clear separation of concerns with explicit dependencies
- **MODULAR**: Composable, testable, independent modules
- **PERFORMANT**: Adaptive loading, caching, and resource optimization
- **ORGANIZED**: Predictable file structure with domain-driven design

## Getting Started

1. Clone the repository
2. Set up backend environment with Python 3.9+
3. Set up frontend environment with Node.js 18+
4. Configure environment variables
5. Start Redis server
6. Launch backend and frontend services
7. Access the application at http://localhost:3000

## Privacy Implementation Status

### Completed (Tier 1 - Essential)
- ✅ Parser recognizes privacy queries naturally ("make my X private", "you can do stuff in private?")
- ✅ AI classifier understands privacy features and provides guidance
- ✅ System knowledge base includes Zcash integration details
- ✅ Landing page highlights privacy features with shield icon
- ✅ Help modal includes Privacy Guide tab with wallet recommendations
- ✅ Backend response includes post-bridge guidance with wallet options
- ✅ Frontend displays comprehensive privacy bridge guidance component
- ✅ Single source of truth for privacy constants (wallets, FAQ, guidance)

### In Progress (Tier 2 - Polish)
- Contextual help popovers for privacy concepts
- Wallet integration / iframe embedding
- Step-by-step walkthrough modal

### Planned (Tier 3 - Nice to Have)
- Bridge status tracking with real-time updates
- Post-bridge UX with next steps
- Merchant directory integration

See [PRIVACY_EDUCATION_IMPLEMENTATION.md](PRIVACY_EDUCATION_IMPLEMENTATION.md) for details.
# Integrations & Privacy

## Unified Payment System

SNEL provides a unified payment architecture that seamlessly handles payments across multiple networks:

- **Cronos (USDC)**: Uses X402 protocol for automated conditional payments with EIP-712 signing
- **Ethereum (MNEE)**: Uses Relayer pattern for gasless payments with ERC-20 approvals
- **Security**: Client-side signing only, no private keys transmitted to backend
- **User Experience**: Single API abstracts protocol complexity, users don't need to know which protocol is used

See [PAYMENTS.md](./PAYMENTS.md) for detailed configuration and usage.

## Cronos x402 Integrations
**Official Tooling Utilized:**

### 1. X402 Facilitator SDK
SNEL leverages the official `@crypto.com/facilitator-client` in the frontend to ensure robust EIP-712 security.
- **Purpose**: Validates payment headers and ensures protocol compliance before signing.
- **Location**: `frontend/src/lib/x402-sdk.ts`

### 2. Crypto.com AI Agent SDK
The backend is architected to support the `cryptocom-agent-client` for advanced natural language interactions.
- **Purpose**: Enables the AI agent to query chain data and execute complex intents using Crypto.com's official LLM tooling.
- **Location**: `backend/app/integrations/cdc_agent.py`

### 3. Cronos DEX Integration
SNEL provides intelligent DEX routing on Cronos with specialized protocol adapters:

#### MM Finance Integration
- **Specialization**: USDC pairs with 60% WCRO/USDC trading volume
- **Router**: `0x145677FC4d9b8F19B5D56d1820c48e0443049a30` (MeerkatRouter)
- **Factory**: `0xd590cC180601AEcD6eeADD9B7f2B7611519544f4`
- **Token Support**: Official Cronos USDC (`0xc21223249CA28397B4B6541dfFaEcC539BfF0c59`) and WCRO (`0x5C7F8A570d578ED84E63fdFA7b1eE72dEae1AE23`)
- **Location**: `backend/app/protocols/mm_adapter.py`

#### VVS Finance Integration
- **Specialization**: General trading pairs with 64.6% overall volume share
- **Router**: `0x145863Eb42Cf62847A6Ca784e6416C1682b1b2Ae`
- **Factory**: `0x3B44B2a187a7b3824131F8db5a74194D0a42Fc15`
- **Location**: `backend/app/protocols/vvs_adapter.py`

#### Smart Routing Logic
SNEL automatically selects the optimal DEX based on token pairs:
- **USDC Pairs** (CRO ↔ USDC): Routes to **MM Finance** for best liquidity
- **Other Pairs** (CRO ↔ USDT, etc.): Routes to **VVS Finance** for best rates
- **Fallback**: Automatic fallback between protocols if one fails

### 4. Unified Agentic Workflow
SNEL acts as a unified "Agentic Layer" that intelligently routes user intent to the correct official SDK:
- "Pay 50 USDC on Cronos" -> **X402 SDK** (Cronos)
- "Swap 10 CRO to USDC" -> **MM Finance** (Cronos USDC specialist)
- "Swap 10 CRO to USDT" -> **VVS Finance** (Cronos general DEX)
- "Send 100 MNEE on Ethereum" -> **MNEE Relayer** (Ethereum)
- "What is the price of CRO?" -> **CDC Agent SDK** (Data)

## Privacy Features

### Privacy Bridging
- **Cross-Chain Bridging**: Axelar GMP + LayerZero integration
- **Privacy Bridging**: Zcash integration for private transactions
- **Supported Networks**: Multiple layer 1 and layer 2 networks with privacy features

### Zcash Integration
- **ZEC Support**: Native Zcash integration for private transactions
- **Bridge Capabilities**: Bridge assets to privacy-preserving chains like Zcash using Axelar GMP
- **Privacy Features**: Make transactions private through privacy-preserving cross-chain transfers

### Security Considerations
- **No PII Storage**: Wallet addresses only
- **Encryption**: At rest and in transit
- **Audit Logs**: All operations logged
- **Access Control**: Role-based permissions

## Hackathon Enhancement Plan

For the Scroll-based hackathon, we will enhance our integrations with:

### LINE Mini-dApp Enhancements
1. **Scroll-Specific Optimizations**
   - Gas-efficient transaction batching
   - Native Scroll contract interactions
   - Optimized signing workflows

2. **Advanced Payment Features**
   - Multi-recipient payment splitting
   - Scheduled payment functionality
   - Conditional payment triggers

3. **Enhanced User Experience**
   - Streamlined payment approval flows
   - Real-time transaction status updates
   - Improved error handling and recovery

### WalletConnect Enhancements
1. **Scroll Payment Optimization**
   - Optimize existing payment flows for Scroll
   - Implement gas-efficient transaction batching
   - Enhance transaction status tracking

2. **Enhanced Payment UX**
   - Create intuitive payment interface
   - Implement payment history and analytics
   - Add recipient management features

3. **Advanced Payment Features**
   - Add scheduled and conditional payments
   - Implement payment requests
   - Enhance security features

### Next Steps
1. Test the complete wallet integration flow
2. Verify transaction execution works correctly
3. Test on actual LINE Mini Dapp environment
4. Prepare demo for submission to LINE team
5. Implement hackathon-specific enhancements

## MNEE Stablecoin Integration

### Implementation Status
✅ **FULLY INTEGRATED AND TESTED** - Production Ready

### Overview
MNEE is a USD-backed programmable stablecoin with native support on 1Sat Ordinals and multi-chain Ethereum support. The backend MNEE Protocol Adapter provides complete integration with the MNEE API.

### Token Specification
- **Name**: MNEE Stablecoin
- **Symbol**: MNEE
- **Decimals**: 5 (1 MNEE = 100,000 atomic units = 10^5)
- **Primary Network**: 1Sat Ordinals (Chain ID: 236)
- **Multi-chain**: Ethereum (Chain ID: 1)
- **Ethereum Address**: `0x8ccedbAe4916b79da7F3F612EfB2EB93A2bFD6cF`
- **Features**: Instant transactions, gasless UX, near-zero fees
- **Collateral**: 1:1 USD backed by U.S. Treasury bills
- **Regulation**: Regulated in Antigua with AML/KYC compliance

### Implementation Details
- **Protocol Adapter**: `backend/app/protocols/mnee_adapter.py`
- **Token Configuration**: `backend/app/config/tokens.py`
- **Protocol Configuration**: `backend/app/config/protocols.py` (Registry)
- **Frontend Constants**: `frontend/src/constants/tokens.ts`

### API Integration
All 5 core MNEE API endpoints are fully integrated:

```
GET /v1/config              → get_config()
POST /v2/balance            → get_balance(addresses)
POST /v2/utxos              → get_utxos(addresses, page, size)
POST /v2/transfer           → transfer(rawtx) - returns ticket ID
GET /v2/ticket              → get_ticket(ticket_id)
```

### Backend Configuration

#### Environment Variables
Set in `.env` (or Hetzner server environment):
```env
# Sandbox API Key (for development/testing)
MNEE_API_KEY=a5ef6fcc02f4af14f2cf93a372f4ef86
MNEE_ENVIRONMENT=sandbox

# Production API Key (for live transactions on Hetzner)
MNEE_API_KEY=b628ee310f05d38504325f597b66c514
MNEE_ENVIRONMENT=production
```

#### Hetzner Server Deployment
To deploy on Hetzner with production API key:
```bash
# SSH into Hetzner server
ssh root@your-hetzner-ip

# Set environment variables
export MNEE_API_KEY=b628ee310f05d38504325f597b66c514
export MNEE_ENVIRONMENT=production

# Or update .env in the application directory
echo "MNEE_API_KEY=b628ee310f05d38504325f597b66c514" >> /path/to/app/.env
echo "MNEE_ENVIRONMENT=production" >> /path/to/app/.env

# Restart application
systemctl restart snel-backend
```

### Features
- ✅ Protocol Adapter with async API support
- ✅ Quote generation with real-time fees
- ✅ Transaction building for wallet signing
- ✅ Atomic unit conversions (5 decimals)
- ✅ Environment support (sandbox/production)
- ✅ ProtocolRegistry integration
- ✅ TokenQueryService integration
- ✅ Error handling & logging

### Payment Workflow
1. User requests MNEE payment
2. TokenQueryService locates MNEE token
3. ProtocolRegistry provides MNEEAdapter
4. get_quote() generates real quote with fees
5. build_transaction() creates API-ready transaction
6. Frontend displays quote with features/collateral
7. User signs via WalletConnect/wallet-bridge
8. Signed tx submitted to `/v2/transfer` API
9. Ticket ID returned for tracking
10. System monitors `/v2/ticket` for status
11. User notified on completion

### Testing
All tests available in `backend/`:

```bash
# Token configuration + service integration (4/4 tests)
python test_mnee_integration.py

# Complete flow integration (7/7 tests)
python test_mnee_integration_flow.py

# Complete workflow demonstration
python test_mnee_complete_demo.py

# Live API endpoint testing (requires API key)
python test_mnee_api_live.py
```

All tests pass and verify proper integration into application workflow.

## Current Capabilities
- Multi-chain support across 16+ networks (Ethereum, Arbitrum, Polygon, Base, Optimism, zkSync, Scroll, Linea, Mantle, Blast, Mode, Gnosis, Taiko, Avalanche, BSC)
- **Cronos DEX Integration** with smart routing (MM Finance for USDC pairs, VVS Finance for general trading)
- **MNEE stablecoin** with full protocol adapter and API integration
- **X402 Agentic Payments** with USDC swap support on Cronos
- Natural language processing for DeFi operations and payments
- Wallet connection and transaction management (50+ wallet support)
- LINE Mini-Dapp integration (mobile-first)
- Privacy features with Zcash integration
- Cross-chain bridging capabilities
- Invoice reference support for business payments
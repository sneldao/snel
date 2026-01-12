# Payments & Transactions

## Unified Payment Architecture

SNEL provides a unified payment system that works seamlessly across multiple networks and protocols while maintaining user control of funds.

### Supported Networks & Protocols

| Network | Chain ID | Token | Protocol | Features |
|---------|----------|-------|----------|----------|
| Cronos Mainnet | 25 | USDC | X402 | Automation, Conditional, Scheduled |
| Cronos Testnet | 338 | USDC | X402 | Automation, Conditional, Scheduled |
| Ethereum Mainnet | 1 | MNEE | X402 / Relayer | Automation, Recurring, Agentic |

### Security Model
- **Client-Side Signing**: All signatures generated in user's wallet
- **No Private Keys**: Backend never receives or stores private keys
- **The "Agentic" Standard**: X402 is used as the unified logic layer for all automations
- **Permission-Based**: Users grant specific permissions (EIP-712 signatures or ERC-20 approvals)

## X402 Agentic Payment Integration

### Core Features
- **Unified Automation**: Single interface for both Cronos and Ethereum automations
- **AI-Triggered Payments**: Autonomous payments executed by AI agents based on conditions
- **EIP-712 Authorization**: Secure cryptographic signatures for payment delegation  
- **Automated Settlement**: Recurring and scheduled payment workflows

### Natural Language Commands

```bash
# AI Agent Payments
"pay agent 10 USDC for API calls"
"setup recurring monthly payment of 1 mnee to globalnative.eth"

# Recurring Payments
"setup weekly payment of 100 USDC to supplier.eth"
"create monthly payment of 50 MNEE to contractor.eth"

# Batch Settlements
"process batch settlement for suppliers"
"execute batch payment to contractors"
```

### Flow Architecture

The X402 Processor creates a unified "Agentic Automation" experience across chains.

#### Cronos (Native X402)
1. **Preparation**: Backend generates EIP-712 typed data
2. **User Action**: User signs typed data in wallet
3. **Execution**: Facilitator executes via X402 protocol

#### Ethereum (MNEE Agentic)
1. **Preparation**: Backend prepares agentic flow details
2. **User Action**: User signs EIP-712 typed data (for agent authorization)
3. **Execution**: Backend executes via Relayer/Guardian system based on signed intent

## MNEE Stablecoin Integration

### Overview
MNEE is a programmable stablecoin designed for B2B payments and AI-driven commerce.

### Key Features
- **Instant Transactions**: Near-zero latency settlement
- **Gasless UX**: Users don't need ETH for gas fees
- **Programmable**: Smart contract automation capabilities
- **1:1 USD Backing**: Collateralized by U.S. Treasury bills

### Technical Details
- **Multi-chain Support**: Ethereum (Chain ID: 1)
- **Decimals**: 5 (1 MNEE = 100,000 atomic units = 10^5)
- **Ethereum Address**: `0x8ccedbAe4916b79da7F3F612EfB2EB93A2bFD6cF`

### Natural Language Commands

```bash
# Direct Payments
"send 100 MNEE to supplier.eth"
"pay 50 MNEE for services"

# Recurring Payments
"setup monthly payment of 1000 MNEE to contractor.eth"
"create weekly payment of 250 MNEE to vendor.eth"

# Conditional Payments
"pay 500 MNEE when milestone completed"
"release 1000 MNEE when invoice approved"
```

## Payment Actions System

### Overview
Payment Actions provide persistent, user-controlled automation for recurring and conditional payments.

### Core Features
- **Persistent Storage**: Actions survive server restarts
- **User Control**: Full CRUD operations via natural language
- **Flexible Scheduling**: One-time, recurring, or conditional execution
- **Multi-Backend Support**: Memory, Redis, or PostgreSQL storage

### Action Types

#### Recurring Payments
```bash
"create weekly payment of 100 USDC to supplier.eth"
"setup monthly salary payment of 5000 MNEE to employee.eth"
```

#### Conditional Payments
```bash
"pay 1000 MNEE when ETH price drops below $3000"
"release 500 USDC when milestone completed"
```

#### One-time Scheduled
```bash
"pay 2000 MNEE on December 31st"
"send 100 USDC tomorrow at 9 AM"
```

### Management Commands

```bash
# List actions
"show my payment actions"
"list all scheduled payments"

# Modify actions
"pause payment to supplier.eth"
"update contractor payment to 150 USDC"
"delete recurring payment to vendor.eth"

# Execute actions
"execute payment to supplier.eth now"
"trigger all pending payments"
```

## Configuration

Environment variables control the unified payment system:

```env
# Required: X402 Configuration (Cronos)
CRONOS_MAINNET_RPC_URL=https://evm.cronos.org
CRONOS_TESTNET_RPC_URL=https://evm-t3.cronos.org
X402_FACILITATOR_URL=https://facilitator.cronoslabs.org/v2/x402

# Required: MNEE Relayer Configuration (Ethereum)
ETH_RPC_URL=https://eth-mainnet.g.alchemy.com/v2/YOUR_ALCHEMY_KEY
MNEE_RELAYER_ADDRESS=0x[your_relayer_public_address]
MNEE_RELAYER_PRIVATE_KEY=0x[corresponding_private_key]

# Backend storage selection
PAYMENT_ACTIONS_BACKEND=redis    # "memory" | "redis" | "postgresql"
REDIS_URL=redis://localhost:6379

# Optional: MNEE API configuration
MNEE_API_KEY=your_mnee_api_key_here
MNEE_ENVIRONMENT=production      # "production" | "sandbox"
```

**Important**: 
- All RPC URLs and private keys must be in the **backend** environment
- Frontend only needs `NEXT_PUBLIC_API_URL` to communicate with backend
- Never put private keys or RPC URLs in frontend for security

## Technical Implementation

### Wallet Integration
- **Framework**: Wagmi v2 with Viem
- **Connectors**: WalletConnect, MetaMask, Injected wallets
- **Transaction Handling**: Automatic receipt waiting and confirmation
- **Error Recovery**: Comprehensive error handling with user feedback

### Transaction Flow
```typescript
// Example: MNEE approval with receipt waiting
const hash = await walletClient.writeContract({
    address: tokenAddress,
    abi: parseAbi(['function approve(address spender, uint256 amount) returns (bool)']),
    functionName: 'approve',
    args: [relayerAddress, amount]
});

// Automatic receipt waiting
await publicClient.waitForTransactionReceipt({ hash });
```

## API Endpoints

### Unified Payment API
- `POST /api/v1/payment/execute/prepare` - Prepare payment for signing
- `POST /api/v1/payment/execute/submit` - Submit signed payment

### Protocol-Specific APIs
- `POST /api/v1/x402/prepare-payment` - X402 preparation
- `POST /api/v1/x402/submit-payment` - X402 submission
- `GET /api/v1/mnee/relayer-address` - Get MNEE relayer address
- `GET /api/v1/mnee/allowance/{address}` - Check MNEE allowance
- `POST /api/v1/mnee/execute-relayed-payment` - Execute MNEE payment

### Payment Actions API
- `POST /api/v1/payment-actions` - Create payment action
- `GET /api/v1/payment-actions` - List user's actions
- `PUT /api/v1/payment-actions/{id}` - Update action
- `DELETE /api/v1/payment-actions/{id}` - Delete action
- `POST /api/v1/payment-actions/{id}/execute` - Execute action

## Usage Examples

### Cronos USDC Payment (X402)
```bash
# User command
"pay agent 50 USDC on cronos"

# Flow
1. Backend detects: cronos-testnet + USDC → X402
2. Generates EIP-712 typed data
3. User signs in wallet
4. Backend submits to X402 facilitator
5. On-chain settlement
```

### Ethereum MNEE Payment (Relayer)
```bash
# User command  
"setup recurring 100 MNEE payments"

# Flow
1. Backend detects: ethereum-mainnet + MNEE → Relayer
2. Checks user's MNEE allowance for relayer
3. User approves relayer (if needed)
4. Backend executes transferFrom when conditions met
5. On-chain settlement (backend pays gas)
```

## Testing

### Running Tests
```bash
cd backend
python -m pytest tests/test_payment_router.py -v
```

### Test Coverage
- Protocol routing logic (11 tests)
- Payment preparation and submission
- Error handling and validation
- Network/token validation

## Troubleshooting

### Common Issues

#### "MNEE Relayer not configured"
- Ensure `MNEE_RELAYER_ADDRESS` and `MNEE_RELAYER_PRIVATE_KEY` are set
- Verify relayer has sufficient ETH for gas

#### "Insufficient allowance"
- User needs to approve relayer address
- Check allowance with `/api/v1/mnee/allowance/{address}`

#### "X402 facilitator unreachable"
- Verify `X402_FACILITATOR_URL` is correct
- Check network connectivity

### Debug Mode
Set `LOG_LEVEL=DEBUG` to enable detailed logging of payment flows.

## Security Considerations

### Production Checklist
- [x] Remove private key parameters from API requests
- [x] Remove placeholder addresses and use proper resolution
- [x] Add proper environment variable validation
- [x] Implement proper wallet integration (Wagmi + WalletConnect)
- [x] Add transaction receipt waiting and confirmation
- [x] Comprehensive error handling and retry logic
- [ ] Add rate limiting and abuse prevention
- [ ] Secure relayer private key storage (AWS KMS, HashiCorp Vault)

### Implemented Security Features
1. **Wallet Integration**: Full Wagmi integration with WalletConnect support
2. **Transaction Receipts**: Automatic receipt waiting via `publicClient.waitForTransactionReceipt()`
3. **No Private Key Transmission**: Private keys never leave user's wallet
4. **Explicit Permissions**: Users see exactly what they're authorizing
5. **Limited Scope**: Signatures/approvals are for specific amounts and recipients
6. **Time Bounds**: X402 signatures have expiration times
7. **Revocable**: Users can revoke approvals at any time

### Wallet Support
- **MetaMask**: Native support via Wagmi
- **WalletConnect**: Full integration for mobile wallets
- **Injected Wallets**: Support for browser extension wallets
- **LINE Integration**: Bitget Wallet integration for LINE Mini-dApp
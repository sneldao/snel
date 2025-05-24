# SNEL Frontend

Modern Next.js 14 frontend for the SNEL cross-chain DeFi assistant with TypeScript, Chakra UI, and Web3 integration.

## 🏗️ Tech Stack

- **Framework**: Next.js 14 with App Router
- **Language**: TypeScript for type safety
- **UI Library**: Chakra UI for modern, accessible components
- **Web3**: Wagmi + ConnectKit for wallet integration
- **State Management**: React Query for server state
- **Styling**: Chakra UI theme system
- **Build Tool**: Next.js built-in bundler

## 📁 Project Structure

```
src/
├── components/           # React components
│   ├── CommandInput.tsx     # Main chat input
│   ├── CommandResponse.tsx  # Message display
│   ├── TransactionProgress.tsx # Multi-step progress
│   ├── SwapConfirmation.tsx # Swap confirmations
│   └── AgentCapabilities.tsx # Agent info display
├── services/            # API and business logic
│   ├── apiService.ts        # Backend API client
│   ├── transactionService.ts # Web3 transactions
│   └── multiStepTransactionService.ts # Multi-step handling
├── hooks/               # Custom React hooks
│   ├── useUserProfile.ts    # User profile management
│   └── useWallet.ts         # Wallet state
├── types/               # TypeScript definitions
│   └── responses.ts         # API response types
├── constants/           # App constants
│   └── chains.ts           # Blockchain configurations
└── lib/                # Utilities
    └── api.ts              # API helpers
```

## 🚀 Getting Started

### Prerequisites
- Node.js 18+
- npm or yarn

### Installation
```bash
npm install
```

### Environment Setup
Create `.env.local`:
```env
NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID=your_project_id
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Development
```bash
npm run dev          # Start development server
npm run build        # Build for production
npm run start        # Start production server
npm run lint         # Run ESLint
```

## 🔧 Key Features

### Multi-Step Transaction Handling
- **TransactionProgress**: Visual progress indicator for complex transactions
- **MultiStepTransactionService**: Orchestrates approval → swap sequences
- **Real-time updates**: Live status with block explorer links

### AI Chat Interface
- **CommandInput**: Natural language input with network detection
- **CommandResponse**: Context-aware response rendering
- **Agent switching**: Different agents for different operations

### Web3 Integration
- **50+ wallet support** via ConnectKit
- **Multi-chain detection** with automatic network switching
- **Transaction simulation** before execution
- **Comprehensive error handling** with user-friendly messages

### Responsive Design
- **Mobile-first** approach
- **Dark/light mode** support
- **Accessible** components following WCAG guidelines
- **Progressive enhancement** for better performance

## 🔌 API Integration

### Backend Communication
```typescript
// API service for backend communication
const apiService = new ApiService();

// Execute swap command
const response = await apiService.processSwapCommand({
  command: "swap 1 ETH for USDC",
  wallet_address: address,
  chain_id: chainId
});

// Handle multi-step transactions
const nextStep = await apiService.completeTransactionStep(
  address, chainId, txHash, true
);
```

### Transaction Execution
```typescript
// Transaction service for Web3 operations
const txService = new TransactionService(walletClient, publicClient, chainId);

// Execute transaction with proper error handling
const result = await txService.executeTransaction(transactionData);
```

## 🎨 UI Components

### Core Components
- **CommandInput**: Main chat interface with auto-complete
- **CommandResponse**: Renders different response types (text, transactions, confirmations)
- **TransactionProgress**: Multi-step transaction visualization
- **SwapConfirmation**: Interactive swap confirmation dialogs

### Utility Components
- **AgentCapabilities**: Displays current agent capabilities
- **NetworkBadge**: Shows current network status
- **TokenInfo**: Token information display with verification status

## 🔍 Development Guidelines

### Code Style
- Use TypeScript for all new code
- Follow React best practices (hooks, functional components)
- Implement proper error boundaries
- Use Chakra UI components consistently

### State Management
- Use React Query for server state
- Local state with useState/useReducer
- Context for global UI state (theme, modals)

### Performance
- Implement proper memoization with useMemo/useCallback
- Lazy load heavy components
- Optimize bundle size with dynamic imports

## 🧪 Testing

```bash
npm run test         # Run unit tests
npm run test:watch   # Watch mode
npm run test:coverage # Coverage report
```

## 📦 Build & Deployment

### Production Build
```bash
npm run build
npm run start
```

### Environment Variables
- `NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID`: WalletConnect project ID
- `NEXT_PUBLIC_API_URL`: Backend API URL
- `NEXT_PUBLIC_ENVIRONMENT`: Environment (development/production)

### Deployment
The frontend is automatically deployed to Netlify on push to main branch.

## 🤝 Contributing

1. Follow the existing code style
2. Add TypeScript types for new features
3. Test components thoroughly
4. Update documentation for new features
5. Ensure accessibility compliance

## 📚 Resources

- [Next.js Documentation](https://nextjs.org/docs)
- [Chakra UI Documentation](https://chakra-ui.com/docs)
- [Wagmi Documentation](https://wagmi.sh)
- [ConnectKit Documentation](https://docs.family.co/connectkit)

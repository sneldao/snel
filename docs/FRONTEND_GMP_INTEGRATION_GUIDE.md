# Frontend GMP Integration Guide

## 🎯 Overview

This guide shows how to integrate the new GMP (General Message Passing) system into your existing SNEL frontend while maintaining clean, performant, and modular code.

## 📁 New Components Structure

```
src/
├── contexts/
│   └── GMPContext.tsx              # Centralized GMP state management
├── components/
│   ├── GMP/
│   │   ├── GMPTransactionCard.tsx  # Beautiful transaction display
│   │   ├── GMPCommandHandler.tsx   # Smart command handler
│   │   └── GMPTransactionFlow.tsx  # Existing flow component
│   └── EnhancedCommandResponse.tsx # Enhanced response with GMP
├── hooks/
│   └── useGMPIntegration.ts        # Seamless API integration
└── services/
    └── axelarGMPService.ts         # Existing GMP service
```

## 🔧 Integration Steps

### Step 1: Add GMP Provider to Your App

Update your main app component (likely `src/app/layout.tsx` or similar):

```tsx
import { GMPProvider } from '../contexts/GMPContext';

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <ChakraProvider theme={theme}>
          <WagmiConfig config={wagmiConfig}>
            <ConnectKitProvider>
              <GMPProvider>  {/* Add this wrapper */}
                {children}
              </GMPProvider>
            </ConnectKitProvider>
          </WagmiConfig>
        </ChakraProvider>
      </body>
    </html>
  );
}
```

### Step 2: Replace CommandResponse with EnhancedCommandResponse

In your chat interface component:

```tsx
// Before
import { CommandResponse } from './CommandResponse';

// After
import { EnhancedCommandResponse } from './EnhancedCommandResponse';

// In your render method:
<EnhancedCommandResponse
  response={response}
  onExecuteTransaction={handleExecuteTransaction}
  isExecuting={isExecuting}
/>
```

### Step 3: Use the GMP Integration Hook

In your main chat component:

```tsx
import { useGMPIntegration } from '../hooks/useGMPIntegration';

export const ChatInterface = () => {
  const {
    executeCommand,
    activeTransactions,
    stats,
    isLikelyGMPCommand
  } = useGMPIntegration({
    onTransactionComplete: (id, result) => {
      console.log('GMP transaction completed:', id, result);
    },
    onTransactionError: (id, error) => {
      console.error('GMP transaction failed:', id, error);
    }
  });

  const handleSendMessage = async (message: string) => {
    try {
      // This now automatically handles GMP operations
      const response = await executeCommand(message, walletClient, chainId);
      
      // Response includes isGMPOperation flag and transactionId if applicable
      if (response.isGMPOperation) {
        console.log('GMP operation created:', response.transactionId);
      }
      
      // Add to chat history as usual
      addMessage(response);
    } catch (error) {
      console.error('Command failed:', error);
    }
  };

  return (
    <VStack spacing={4}>
      {/* Show GMP stats if there are active transactions */}
      {activeTransactions.length > 0 && (
        <Alert status="info">
          <AlertIcon />
          {activeTransactions.length} cross-chain transaction(s) in progress
        </Alert>
      )}
      
      {/* Your existing chat interface */}
      <ChatMessages messages={messages} />
      <ChatInput onSend={handleSendMessage} />
    </VStack>
  );
};
```

### Step 4: Add GMP Transaction Dashboard (Optional)

Create a dashboard to show active GMP transactions:

```tsx
import { useGMP } from '../contexts/GMPContext';
import { GMPTransactionCard } from '../components/GMP/GMPTransactionCard';

export const GMPDashboard = () => {
  const { state, executeTransaction } = useGMP();
  const { walletClient } = useWallet();

  return (
    <VStack spacing={4}>
      <Text fontSize="lg" fontWeight="semibold">
        Cross-Chain Transactions
      </Text>
      
      {Object.values(state.transactions).map(transaction => (
        <GMPTransactionCard
          key={transaction.id}
          transaction={transaction}
          onExecute={() => executeTransaction(transaction.id, walletClient)}
          compact={false}
        />
      ))}
    </VStack>
  );
};
```

## 🎨 Styling Integration

The new components use your existing Chakra UI theme and follow these principles:

### Color Scheme
- **Primary**: Blue (matches Axelar branding)
- **Success**: Green (completed transactions)
- **Warning**: Orange (pending operations)
- **Error**: Red (failed transactions)

### Animation
- **Framer Motion**: Smooth transitions and micro-interactions
- **Performance**: Optimized with `memo` and `useMemo`
- **Accessibility**: Respects `prefers-reduced-motion`

### Responsive Design
- **Mobile-first**: Works on all screen sizes
- **Touch-friendly**: Large tap targets
- **Readable**: Appropriate font sizes and contrast

## 🔄 Backward Compatibility

The integration maintains 100% backward compatibility:

- ✅ Existing commands work exactly as before
- ✅ Non-GMP operations use existing flow
- ✅ UI remains consistent for regular operations
- ✅ No breaking changes to existing APIs

## 🚀 Performance Optimizations

### State Management
- **Context optimization**: Prevents unnecessary re-renders
- **Memoization**: Heavy computations cached
- **Selective updates**: Only affected components re-render

### Network Efficiency
- **Request batching**: Multiple operations combined
- **Caching**: API responses cached appropriately
- **Polling optimization**: Smart intervals for transaction tracking

### Bundle Size
- **Tree shaking**: Only used components included
- **Code splitting**: GMP components loaded on demand
- **Lazy loading**: Heavy components loaded when needed

## 🧪 Testing Integration

### Unit Tests
```tsx
import { render, screen } from '@testing-library/react';
import { GMPProvider } from '../contexts/GMPContext';
import { EnhancedCommandResponse } from '../components/EnhancedCommandResponse';

test('renders GMP operation correctly', () => {
  const mockResponse = {
    content: {
      metadata: { uses_gmp: true },
      transaction_data: { type: 'cross_chain_swap' }
    }
  };

  render(
    <GMPProvider>
      <EnhancedCommandResponse response={mockResponse} />
    </GMPProvider>
  );

  expect(screen.getByText(/cross-chain/i)).toBeInTheDocument();
});
```

### Integration Tests
```tsx
import { useGMPIntegration } from '../hooks/useGMPIntegration';

test('executes GMP command correctly', async () => {
  const { executeCommand } = useGMPIntegration();
  
  const response = await executeCommand(
    'swap 100 USDC from Ethereum to MATIC on Polygon'
  );
  
  expect(response.isGMPOperation).toBe(true);
  expect(response.transactionId).toBeDefined();
});
```

## 📊 Monitoring & Analytics

### User Experience Metrics
- **Command recognition accuracy**: Track GMP vs regular commands
- **Transaction success rate**: Monitor cross-chain completion rates
- **User engagement**: Time spent on GMP features

### Performance Metrics
- **Response times**: API call latencies
- **Render performance**: Component render times
- **Memory usage**: Context state size

### Error Tracking
- **Failed transactions**: Categorize failure reasons
- **API errors**: Track service availability
- **User errors**: Common mistake patterns

## 🔧 Configuration

### Environment Variables
```env
# Add to your .env.local
NEXT_PUBLIC_AXELAR_ENVIRONMENT=mainnet
NEXT_PUBLIC_GMP_POLLING_INTERVAL=10000
NEXT_PUBLIC_GMP_MAX_RETRIES=3
```

### Feature Flags
```tsx
// Add to your config
export const features = {
  gmpEnabled: process.env.NODE_ENV === 'production',
  gmpAutoTracking: true,
  gmpNotifications: true
};
```

## 🎯 Next Steps

1. **Implement Step 1-3** above in your main app
2. **Test with sample GMP commands**
3. **Add GMP dashboard** for better UX
4. **Configure monitoring** for production
5. **Gather user feedback** and iterate

## 🆘 Troubleshooting

### Common Issues

**GMP Context not found**
```tsx
// Ensure GMPProvider wraps your app
<GMPProvider>
  <YourApp />
</GMPProvider>
```

**Transactions not tracking**
```tsx
// Check autoTrack is enabled
const { executeCommand } = useGMPIntegration({ autoTrack: true });
```

**Styling conflicts**
```tsx
// Use Chakra's theme tokens
const cardBg = useColorModeValue('white', 'gray.800');
```

---

This integration maintains your high standards for clean, performant, and delightful code while adding powerful cross-chain capabilities! 🚀

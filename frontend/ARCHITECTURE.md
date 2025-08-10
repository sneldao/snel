# SNEL Frontend Architecture

## Overview
Clean, modular architecture following DRY, CLEAN, ORGANISED, MODULAR, PERFORMANT principles.

## Core Components

### 🏗️ **Main Application Flow**
```
MainApp.tsx (Entry Point)
├── CommandInput (User Input)
├── GMPCompatibleCommandResponse (Smart Routing)
    ├── CommandResponse (Regular Operations)
    └── GMPCommandHandler (Cross-chain Operations - Lazy Loaded)
```

### ⚡ **GMP Integration Architecture**
```
GMP Integration Layer
├── GMPContext (State Management)
├── useGMPIntegration (Business Logic)
├── axelarGMPService (Blockchain Interface)
├── walletAdapters (Wallet Abstraction)
└── chainMappings (Centralized Constants)
```

### 🔗 **Service Layer**
- **apiService.ts** - Backend communication
- **axelarService.ts** - Asset transfers via Axelar SDK  
- **axelarGMPService.ts** - Advanced cross-chain operations
- **transactionService.ts** - Transaction management

### 🛠️ **Utility Layer**
- **chainMappings.ts** - Single source of truth for chain data
- **walletAdapters.ts** - Wallet client standardization
- **logger.ts** - Production-safe logging
- **formatters.ts** - Data formatting utilities

## Key Architectural Decisions

### ✅ **DRY (Don't Repeat Yourself)**
- Centralized chain mappings in `chainMappings.ts`
- Removed duplicate MainApp components
- Unified wallet interface via adapters

### ✅ **CLEAN**
- Clear separation of concerns
- Single responsibility principle
- Dependency injection patterns

### ✅ **ORGANISED**  
- Logical folder structure
- Consistent naming conventions
- Clear import/export patterns

### ✅ **MODULAR**
- Context-based state management
- Composable hook architecture
- Lazy-loaded components for performance

### ✅ **PERFORMANT**
- Code splitting with lazy loading
- Centralized constants to reduce duplication
- Efficient state updates
- Bundle size optimization

## GMP Integration Points

1. **Command Detection** - Backend returns `uses_gmp: true`
2. **UI Routing** - `GMPCompatibleCommandResponse` intelligently routes
3. **Transaction Creation** - `GMPContext` manages transaction lifecycle
4. **Wallet Integration** - Standardized via `walletAdapters` 
5. **Blockchain Execution** - Direct Axelar Gateway calls
6. **Status Tracking** - Real-time polling via AxelarGMPRecoveryAPI

## Performance Optimizations

- **Lazy Loading**: GMP components loaded on-demand
- **Centralized Mappings**: Reduced code duplication
- **Memoization**: Expensive computations cached
- **Bundle Analysis**: 1.34MB for GMP test page (acceptable for feature richness)

## Security Considerations

- Wallet client abstraction prevents direct private key access
- Transaction validation before execution  
- Error boundaries for graceful failure handling
- Production-safe logging (no sensitive data)

## Future Scalability

The architecture supports:
- Additional blockchain integrations
- New cross-chain protocols  
- Enhanced transaction types
- Advanced DeFi operations

Built for maintainability and extensibility while keeping performance optimal.
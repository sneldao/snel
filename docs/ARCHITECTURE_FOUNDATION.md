# SNEL Architecture & Foundation

## Overview

SNEL is an AI-powered cross-chain DeFi assistant with clean, modular architecture following DRY, CLEAN, ORGANISED, MODULAR, PERFORMANT principles.

## Core Architecture

### Main Application Flow

```
MainApp.tsx (Entry Point)
├── CommandInput (User Input)
├── GMPCompatibleCommandResponse (Smart Routing)
    ├── CommandResponse (Regular Operations)
    └── GMPCommandHandler (Cross-chain Operations - Lazy Loaded)
```

### GMP Integration Architecture

```
GMP Integration Layer
├── GMPContext (State Management)
├── useGMPIntegration (Business Logic)
├── axelarGMPService (Blockchain Interface)
├── walletAdapters (Wallet Abstraction)
└── chainMappings (Centralized Constants)
```

### Service Layer

- **apiService.ts** - Backend communication
- **axelarService.ts** - Asset transfers via Axelar SDK
- **axelarGMPService.ts** - Advanced cross-chain operations
- **transactionService.ts** - Transaction management

## Key Architectural Decisions

### DRY (Don't Repeat Yourself)

- Centralized chain mappings in `chainMappings.ts`
- Unified wallet interface via adapters
- Single source of truth for configurations

### CLEAN

- Clear separation of concerns
- Single responsibility principle
- Dependency injection patterns

### MODULAR

- Context-based state management
- Composable hook architecture
- Lazy-loaded components for performance

### PERFORMANT

- Code splitting with lazy loading
- Centralized constants to reduce duplication
- Efficient state updates

## GMP Integration Points

1. **Command Detection** - Backend returns `uses_gmp: true`
2. **UI Routing** - `GMPCompatibleCommandResponse` intelligently routes
3. **Transaction Creation** - `GMPContext` manages transaction lifecycle
4. **Wallet Integration** - Standardized via `walletAdapters`
5. **Blockchain Execution** - Direct Axelar Gateway calls
6. **Status Tracking** - Real-time polling via AxelarGMPRecoveryAPI

## Foundation Upgrade Summary

### Completed Upgrades

- **Next.js**: 14.1.0 → 15.5.2 (Latest stable)
- **React**: 18.2.0 → 18.3.1 (Stable, avoiding React 19 breaking changes)
- **TypeScript**: 5.8.3 → 5.9.2 (Latest stable)
- **Wagmi**: 2.8.8 → 2.16.9 (Latest with improved chain support)
- **Viem**: 2.24.0 → 2.37.3 (Latest with better RPC handling)

### Key Improvements

- **Performance Gains**: Improved compilation speed, better caching, faster builds
- **Developer Experience**: Better monorepo development, type safety, build reliability
- **Security & Stability**: Latest security patches, stable versions, clean architecture

### Removed Dependencies (Prevent Bloat)

- @axelar-network/axelar-gmp-sdk-solidity
- @heroicons/react
- @loadable/component
- @tanstack/react-query-devtools
- prismjs, react-syntax-highlighter, react-window

## Current Foundation Status

**Foundation Strength**: 100% Complete ✅
**Current Phase**: Circle Integration & Production Ready
**Major Milestone**: Circle CCTP V2 Integration ✅ COMPLETED

### Protocol Status Assessment

#### 0x Protocol ✅ PRODUCTION READY

- Real API v2 integration with permit2 support
- EIP-712 signature handling
- Transaction simulation and validation
- Circuit breakers and rate limiting
- **27/27 validation tests passing**
- **26,000+ req/sec peak performance**

#### Uniswap Protocol ✅ PRODUCTION READY

- Real API integration with ConfigurationManager
- V3 Concentrated Liquidity Optimization
- Permit2 Integration with EIP-712 signatures
- Parallel Quote Processing
- **7/7 validation tests passing**

#### Axelar Service ✅ PRODUCTION READY

- Real Axelar Integration with intelligent fallbacks
- Rate Limiting & Circuit Breakers (5 req/sec)
- Intelligent Fee Estimation with smart caching
- Cross-Chain Transaction Building
- **7/7 validation tests passing**

#### Circle CCTP V2 ✅ PRODUCTION READY

- Real Circle API Integration with authentication
- 9 supported chains (ETH, ARB, BASE, POLYGON, AVAX, LINEA, etc.)
- Fast Transfer Capabilities (1-5 minute settlements)
- Multi-step Transaction Building (approve + burn)
- **7/7 validation tests passing**

### Success Metrics

- **Foundation Completion**: 48/48 tests total (100% success rate)
- **Performance**: Sub-millisecond cache operations, 26K+ req/sec capability
- **Reliability**: Multi-RPC failover, circuit breakers implemented
- **Error Handling**: Zero mock returns, structured ProtocolError handling

## Roadmap: Architectural Improvements

### Phase 1: Foundation (Q4 2024 - Q1 2025)

- Domain-Driven Folder Restructuring
- Aggressive Component Consolidation
- Centralized Type Definitions

### Phase 2: Optimization (Q1 2025 - Q2 2025)

- Shared Utility Modules
- Dependency Injection Pattern
- Feature-Based Module Boundaries

### Phase 3: Backend Consolidation (Q2 2025 - Q3 2025)

- Backend Domain Organization
- Service consolidation and cleanup

### Phase 4: Performance & Standards (Q3 2025 - Q4 2025)

- Performance Optimizations
- Coding Standards & Conventions

## Core Principles Enforcement

### ENHANCEMENT FIRST

- Enhanced existing implementations instead of rewriting
- Leveraged existing infrastructure for new features

### AGGRESSIVE CONSOLIDATION

- Consolidated redundant code and configurations
- Single source of truth for all settings

### PREVENT BLOAT

- Systematic dependency audits
- Clear success criteria for each enhancement

### DRY (Don't Repeat Yourself)

- Centralized configurations and utilities
- Shared error handling patterns

### CLEAN

- Clear separation of concerns
- Structured error types with context

### MODULAR

- Independent protocol adapters
- Composable components and services

### PERFORMANT

- Connection pooling and caching
- Rate limiting and circuit breakers

### ORGANIZED

- Domain-driven file structure
- Predictable patterns across codebase

## Migration Strategy

### Week 1-2: Foundation

- Create new domain structure
- Set up centralized types and utilities
- Establish coding standards

### Week 3-4: Consolidation

- Migrate and merge duplicate components
- Implement dependency injection
- Consolidate services

### Week 5-6: Optimization

- Performance optimizations
- Code splitting implementation
- Comprehensive testing

### Ongoing: Maintenance

- Regular code audits
- Dependency updates
- Performance monitoring

## Success Metrics

- **Code Reduction**: 30-40% reduction in duplicate code
- **Bundle Size**: Maintain or improve current bundle sizes
- **Build Time**: Stable or improved build times
- **Test Coverage**: 80%+ coverage across all domains
- **Developer Velocity**: Improved development speed and reduced bugs

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

---

# 🚀 **ROADMAP: Architectural Consolidation & Improvements**

## **Phase 1: Foundation (Q4 2024 - Q1 2025)**

### **1.1 Domain-Driven Folder Restructuring** ⭐ **HIGH PRIORITY**

**Current Issues:**

- Components scattered across `/components`, `/components/Chat/`, `/components/GMP/`
- Services mixed between `/services` and `/services/enhanced/`
- No clear domain boundaries

**Target Structure:**

```
frontend/src/
├── domains/                    # Domain-driven organization
│   ├── auth/                  # Authentication & user management
│   ├── transactions/          # All transaction-related logic
│   │   ├── components/        # Transaction UI components
│   │   ├── services/          # Transaction business logic
│   │   ├── types/            # Transaction-specific types
│   │   └── hooks/            # Transaction hooks
│   ├── portfolio/             # Portfolio analysis & management
│   ├── chat/                  # Chat interface & messaging
│   ├── wallet/                # Wallet connection & management
│   └── shared/                # Cross-domain shared components
├── core/                      # Application core
│   ├── api/                   # API client & configuration
│   ├── config/                # App configuration
│   ├── utils/                 # Shared utilities
│   └── types/                 # Global type definitions
├── infrastructure/            # External integrations
│   ├── providers/             # React providers
│   ├── services/              # External service integrations
│   └── storage/               # Local storage & caching
```

### **1.2 Aggressive Component Consolidation** ⭐ **HIGH PRIORITY**

**Immediate Actions:**

- **Merge Duplicate Components:**

  - `CommandResponse.tsx` + `GMPCompatibleCommandResponse.tsx` → `CommandResponse.tsx`
  - `PortfolioSummary.tsx` + `EnhancedPortfolioSummary.tsx` → `PortfolioSummary.tsx`
  - Consolidate all transaction components under `/domains/transactions/components/`

- **Eliminate Redundancy:**
  - Remove `/components/Chat/` and `/components/GMP/` subdirectories
  - Consolidate similar UI components (buttons, modals, cards)
  - Merge overlapping service files

### **1.3 Centralized Type Definitions** ⭐ **MEDIUM PRIORITY**

**Current Issues:**

- Types scattered across multiple files
- Inconsistent type naming conventions
- Missing domain-specific type organization

**Implementation:**

```typescript
// frontend/src/core/types/index.ts
export * from "./api";
export * from "./domain-specific-types";

// frontend/src/core/types/api.ts
export interface ApiResponse<T> {
  /* centralized response type */
}
export interface ApiError {
  /* centralized error type */
}

// Domain-specific types
export * from "../../domains/transactions/types";
export * from "../../domains/portfolio/types";
```

## **Phase 2: Optimization (Q1 2025 - Q2 2025)**

### **2.1 Shared Utility Modules** ⭐ **MEDIUM PRIORITY**

**Consolidate Utilities:**

```typescript
// frontend/src/core/utils/index.ts
export * from "./formatting";
export * from "./validation";
export * from "./constants";

// Single source of truth for all formatting
export const formatCurrency = (value: number) => {
  /* implementation */
};
export const formatAddress = (address: string) => {
  /* implementation */
};
```

### **2.2 Dependency Injection Pattern** ⭐ **MEDIUM PRIORITY**

**Current Issues:**

- Services instantiated directly in components
- Tight coupling between components and services
- Difficult to test and mock

**Implementation:**

```typescript
// frontend/src/core/di/container.ts
class ServiceContainer {
  private services = new Map();

  register<T>(key: string, factory: () => T) {
    this.services.set(key, factory);
  }

  resolve<T>(key: string): T {
    const factory = this.services.get(key);
    return factory ? factory() : null;
  }
}

// Usage in components
const transactionService = useService("transactionService");
```

### **2.3 Feature-Based Module Boundaries** ⭐ **MEDIUM PRIORITY**

**Implementation:**

```typescript
// Each domain is a self-contained module
frontend/src/domains/transactions/
├── index.ts              # Public API exports
├── components/           # UI components
├── services/             # Business logic
├── hooks/                # Custom hooks
├── types/                # Type definitions
├── utils/                # Domain utilities
└── constants/            # Domain constants
```

## **Phase 3: Backend Consolidation (Q2 2025 - Q3 2025)**

### **3.1 Backend Domain Organization** ⭐ **HIGH PRIORITY**

**Current Issues:**

- Multiple standalone test files in root
- Service proliferation with overlapping responsibilities
- Inconsistent error handling patterns

**Target Structure:**

```
backend/app/
├── domains/              # Domain organization
│   ├── transactions/     # Transaction domain
│   ├── portfolio/        # Portfolio analysis
│   └── chat/            # Chat processing
├── core/                # Shared infrastructure
│   ├── services/        # Core services
│   ├── utils/           # Shared utilities
│   └── middleware/      # Custom middleware
├── infrastructure/      # External integrations
└── tests/               # Consolidated test structure
    ├── unit/
    ├── integration/
    └── e2e/
```

## **Phase 4: Performance & Standards (Q3 2025 - Q4 2025)**

### **4.1 Performance Optimizations** ⭐ **INTEGRATED**

**Immediate Improvements:**

- **Code Splitting:** Domain-based lazy loading
- **Caching Strategy:** Centralized cache management
- **Bundle Optimization:** Tree shaking and dead code elimination
- **Image Optimization:** WebP conversion and lazy loading

### **4.2 Coding Standards & Conventions** ⭐ **ONGOING**

**Establish Standards:**

- **File Naming:** `kebab-case` for files, `PascalCase` for components
- **Import Order:** External → Internal → Relative → Types
- **Error Handling:** Centralized error boundary components
- **Testing:** 80%+ coverage requirement with domain-specific test utilities

## **Key Benefits of This Roadmap**

### **🚀 Enhanced Developer Experience:**

- Clear domain boundaries and predictable file locations
- Single source of truth for shared logic
- Improved code discoverability and maintainability

### **⚡ Better Performance:**

- Lazy loading and optimized bundling
- Reduced code duplication
- Efficient state management

### **🧪 Enhanced Testability:**

- Modular structure enables better unit testing
- Dependency injection for easier mocking
- Domain-specific test utilities

### **📈 Scalability:**

- Domain-driven design supports team growth
- Feature-based modules enable independent development
- Clear architectural boundaries

### **🔒 Type Safety:**

- Centralized types prevent inconsistencies
- Domain-specific type definitions
- Better IDE support and error catching

## **Migration Strategy**

### **Week 1-2: Foundation**

- Create new domain structure
- Set up centralized types and utilities
- Establish coding standards

### **Week 3-4: Consolidation**

- Migrate and merge duplicate components
- Implement dependency injection
- Consolidate services

### **Week 5-6: Optimization**

- Performance optimizations
- Code splitting implementation
- Comprehensive testing

### **Ongoing: Maintenance**

- Regular code audits
- Dependency updates
- Performance monitoring

## **Success Metrics**

- **Code Reduction:** 30-40% reduction in duplicate code
- **Bundle Size:** Maintain or improve current bundle sizes
- **Build Time:** Stable or improved build times
- **Test Coverage:** 80%+ coverage across all domains
- **Developer Velocity:** Improved development speed and reduced bugs

---

_This roadmap represents a comprehensive architectural evolution that will significantly improve code quality, maintainability, and scalability while preserving current functionality and performance._

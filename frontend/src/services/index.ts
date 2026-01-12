// Main service exports
export { ApiService } from './apiService';
export { axelarService } from './axelarService';
// Removed: intentRouter - using unified backend parsing

// Transaction services - CONSOLIDATED
// NEW: TransactionFlowService consolidates transactionService + multiStepTransactionService
export { TransactionFlowService } from './transactionFlowService';
// export { TransactionBatchingService } from './transactionBatchingService'; // Service not implemented yet
export type { TransactionStep, MultiStepTransactionResult } from './transactionFlowService';

// Deprecated - use TransactionFlowService instead
export { TransactionService } from './transactionService';
export { PortfolioService } from './portfolioService';
export { websocketService } from './websocketService';

// X402 Agentic Payment Service
export { x402Service } from './x402Service';
export type { X402PaymentRequest, X402PaymentResult, X402HealthStatus } from './x402Service';

// Unified Payment Service (Protocol Router)
export { unifiedPaymentService } from './unifiedPaymentService';
export type {
    UnifiedPaymentRequest,
    UnifiedPaymentResult,
    PaymentProtocol,
    PaymentPreparationResult,
    NetworkInfo,
    ProtocolInfo
} from './unifiedPaymentService';

// MNEE Service
export { mneeService } from './mneeService';
export type { RelayedPaymentResponse, AllowanceResponse } from './mneeService';

// Types
// Removed: intentRouter types - using unified backend parsing
export type { TransferQuote, AxelarConfig } from './axelarService';
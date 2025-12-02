// Main service exports
export { ApiService } from './apiService';
export { axelarService } from './axelarService';
// Removed: intentRouter - using unified backend parsing

// Transaction services - CONSOLIDATED
// NEW: TransactionFlowService consolidates transactionService + multiStepTransactionService
export { TransactionFlowService } from './transactionFlowService';
export type { TransactionStep, MultiStepTransactionResult } from './transactionFlowService';

// Deprecated - use TransactionFlowService instead
export { TransactionService } from './transactionService';
export { PortfolioService } from './portfolioService';
export { websocketService } from './websocketService';

// Types
// Removed: intentRouter types - using unified backend parsing
export type { TransferQuote, AxelarConfig } from './axelarService';
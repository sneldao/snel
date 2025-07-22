/**
 * Wallet Error Handler
 * Handles wallet provider errors and prevents infinite recursion
 */

import { recursionGuard } from './recursionGuard';
import { logger } from './logger';

interface WalletError extends Error {
  code?: number;
  data?: any;
}

class WalletErrorHandler {
  private errorCounts = new Map<string, number>();
  private readonly MAX_ERRORS = 3;
  private readonly ERROR_RESET_TIME = 5000; // 5 seconds

  /**
   * Handle wallet provider errors with recursion prevention
   */
  handleWalletError(error: WalletError, context: string): Error {
    const errorKey = `${context}_${error.code || error.message}`;
    
    // Track error frequency
    const currentCount = this.errorCounts.get(errorKey) || 0;
    this.errorCounts.set(errorKey, currentCount + 1);
    
    // Reset error count after timeout
    setTimeout(() => {
      this.errorCounts.delete(errorKey);
    }, this.ERROR_RESET_TIME);
    
    // If too many similar errors, reset recursion guard
    if (currentCount >= this.MAX_ERRORS) {
      logger.warn(`[WalletErrorHandler] Too many similar errors in ${context}, resetting guards`);
      recursionGuard.resetAll();
    }
    
    // Log the error
    logger.error(`[WalletErrorHandler] ${context}:`, error);
    
    return this.formatWalletError(error);
  }

  /**
   * Format wallet errors for user display
   */
  private formatWalletError(error: WalletError): Error {
    // User rejection errors
    if (this.isUserRejection(error)) {
      return new Error('Transaction cancelled by user');
    }
    
    // Network errors
    if (this.isNetworkError(error)) {
      return new Error('Network connection error. Please check your internet connection.');
    }
    
    // Wallet connection errors
    if (this.isConnectionError(error)) {
      return new Error('Wallet connection lost. Please reconnect your wallet.');
    }
    
    // Provider errors
    if (this.isProviderError(error)) {
      return new Error('Wallet provider error. Please refresh the page and try again.');
    }
    
    // Generic error
    return new Error(error.message || 'An unexpected wallet error occurred');
  }

  private isUserRejection(error: WalletError): boolean {
    const message = error.message?.toLowerCase() || '';
    const code = error.code;
    
    return (
      code === 4001 || // User rejected request
      message.includes('user rejected') ||
      message.includes('user denied') ||
      message.includes('cancelled') ||
      message.includes('rejected')
    );
  }

  private isNetworkError(error: WalletError): boolean {
    const message = error.message?.toLowerCase() || '';
    const code = error.code;
    
    return (
      code === -32603 || // Internal error (often network)
      message.includes('network') ||
      message.includes('connection') ||
      message.includes('timeout') ||
      message.includes('fetch')
    );
  }

  private isConnectionError(error: WalletError): boolean {
    const message = error.message?.toLowerCase() || '';
    
    return (
      message.includes('not connected') ||
      message.includes('no provider') ||
      message.includes('wallet not found') ||
      message.includes('provider not found')
    );
  }

  private isProviderError(error: WalletError): boolean {
    const message = error.message?.toLowerCase() || '';
    const code = error.code;
    
    return (
      code === -32002 || // Resource unavailable
      code === -32005 || // Limit exceeded
      message.includes('provider') ||
      message.includes('internal error') ||
      message.includes('method not found')
    );
  }

  /**
   * Reset all error tracking
   */
  reset(): void {
    this.errorCounts.clear();
  }

  /**
   * Get current error statistics
   */
  getErrorStats(): Record<string, number> {
    return Object.fromEntries(this.errorCounts);
  }
}

// Create singleton instance
export const walletErrorHandler = new WalletErrorHandler();

/**
 * Global error handler for unhandled wallet provider errors
 */
export function setupGlobalWalletErrorHandler(): void {
  // Handle unhandled promise rejections
  window.addEventListener('unhandledrejection', (event) => {
    const error = event.reason;
    
    // Check if it's a wallet-related error
    if (isWalletRelatedError(error)) {
      logger.warn('[GlobalWalletErrorHandler] Caught unhandled wallet error:', error);
      
      // Prevent the error from causing a stack overflow
      event.preventDefault();
      
      // Reset recursion guards to prevent infinite loops
      recursionGuard.resetAll();
      
      // Handle the error
      walletErrorHandler.handleWalletError(error, 'unhandled_rejection');
    }
  });

  // Handle general errors
  window.addEventListener('error', (event) => {
    const error = event.error;
    
    if (isWalletRelatedError(error)) {
      logger.warn('[GlobalWalletErrorHandler] Caught wallet error:', error);
      
      // Reset recursion guards
      recursionGuard.resetAll();
      
      // Handle the error
      walletErrorHandler.handleWalletError(error, 'global_error');
    }
  });
}

/**
 * Check if an error is wallet-related
 */
function isWalletRelatedError(error: any): boolean {
  if (!error) return false;
  
  const message = (error.message || '').toLowerCase();
  const stack = (error.stack || '').toLowerCase();
  
  const walletKeywords = [
    'wallet',
    'provider',
    'metamask',
    'coinbase',
    'walletconnect',
    'web3',
    'ethereum',
    'transaction',
    'signer',
    'rpc',
    'jsonrpc'
  ];
  
  return walletKeywords.some(keyword => 
    message.includes(keyword) || stack.includes(keyword)
  );
}

/**
 * Wrapper for wallet operations with error handling
 */
export async function safeWalletOperation<T>(
  operation: () => Promise<T>,
  context: string
): Promise<T> {
  try {
    return await operation();
  } catch (error) {
    throw walletErrorHandler.handleWalletError(error as WalletError, context);
  }
}
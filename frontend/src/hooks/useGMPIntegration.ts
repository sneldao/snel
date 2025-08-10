/**
 * GMP Integration Hook
 * Seamless integration between existing API service and GMP functionality
 * Optimized for performance, error handling, and user experience
 */

import { useCallback, useMemo } from 'react';
import { useToast } from '@chakra-ui/react';
import { useGMP } from '../contexts/GMPContext';
import { ApiService } from '../services/apiService';
import { logger } from '../utils/logger';

interface GMPIntegrationOptions {
  onTransactionStart?: (transactionId: string) => void;
  onTransactionComplete?: (transactionId: string, result: any) => void;
  onTransactionError?: (transactionId: string, error: string) => void;
  autoTrack?: boolean;
}

export const useGMPIntegration = (options: GMPIntegrationOptions = {}) => {
  const {
    createTransaction,
    executeTransaction,
    trackTransaction,
    getTransaction,
    state
  } = useGMP();
  const toast = useToast();

  // Create apiService instance
  const apiService = useMemo(() => new ApiService(), []);

  const {
    onTransactionStart,
    onTransactionComplete,
    onTransactionError,
    autoTrack = true
  } = options;

  // Enhanced API service call with GMP detection
  const executeCommand = useCallback(async (
    command: string,
    walletClient?: any,
    chainId?: number
  ) => {
    try {
      logger.info('Executing command with GMP integration:', command);

      // Call the existing API service
      const response = await apiService.processCommand(
        command,
        walletClient?.account?.address,
        chainId,
        undefined, // userName
        undefined, // onProgress
        walletClient // signer
      );

      // Check if this is a GMP operation
      const isGMPOperation = response.content?.metadata?.uses_gmp || 
                            response.content?.metadata?.axelar_powered ||
                            response.content?.transaction_data?.protocol === 'axelar_gmp';

      if (isGMPOperation && response.content?.transaction_data) {
        logger.info('GMP operation detected, creating transaction');
        
        // Create GMP transaction
        const transactionId = await createTransaction({
          type: response.content.transaction_data.type,
          source_chain: response.content.transaction_data.source_chain || 
                       response.content.metadata?.source_chain,
          dest_chain: response.content.transaction_data.dest_chain || 
                     response.content.metadata?.dest_chain,
          steps: response.content.transaction_data.steps || [],
          metadata: {
            ...response.content.metadata,
            command,
            estimated_gas_fee: response.content.transaction_data.estimated_gas_fee,
            estimated_cost_usd: response.content.transaction_data.estimated_cost_usd
          }
        });

        // Notify transaction start
        onTransactionStart?.(transactionId);

        // Return enhanced response with transaction ID
        return {
          ...response,
          transactionId,
          isGMPOperation: true
        };
      }

      return {
        ...response,
        isGMPOperation: false
      };

    } catch (error) {
      logger.error('Command execution failed:', error);
      
      toast({
        title: 'Command Failed',
        description: error instanceof Error ? error.message : 'Unknown error occurred',
        status: 'error',
        duration: 5000,
        isClosable: true
      });

      throw error;
    }
  }, [apiService, createTransaction, onTransactionStart, toast]);

  // Execute GMP transaction with enhanced error handling
  const executeGMPTransaction = useCallback(async (
    transactionId: string,
    walletClient: any
  ) => {
    try {
      const transaction = getTransaction(transactionId);
      if (!transaction) {
        throw new Error('Transaction not found');
      }

      logger.info('Executing GMP transaction:', transactionId);

      // Execute the transaction
      await executeTransaction(transactionId, walletClient);

      // Start auto-tracking if enabled
      if (autoTrack) {
        const trackingInterval = setInterval(async () => {
          try {
            await trackTransaction(transactionId);
            const updatedTransaction = getTransaction(transactionId);
            
            if (updatedTransaction?.status === 'completed') {
              clearInterval(trackingInterval);
              onTransactionComplete?.(transactionId, updatedTransaction);
              
              toast({
                title: 'Transaction Completed',
                description: 'Your cross-chain transaction has been completed successfully',
                status: 'success',
                duration: 5000,
                isClosable: true
              });
            } else if (updatedTransaction?.status === 'error') {
              clearInterval(trackingInterval);
              onTransactionError?.(transactionId, 'Transaction failed');
            }
          } catch (trackingError) {
            logger.error('Transaction tracking error:', trackingError);
          }
        }, 10000); // Check every 10 seconds

        // Clear interval after 30 minutes (max reasonable time for cross-chain)
        setTimeout(() => clearInterval(trackingInterval), 30 * 60 * 1000);
      }

      return transaction;

    } catch (error) {
      logger.error('GMP transaction execution failed:', error);
      onTransactionError?.(transactionId, error instanceof Error ? error.message : 'Unknown error');
      throw error;
    }
  }, [
    executeTransaction,
    trackTransaction,
    getTransaction,
    autoTrack,
    onTransactionComplete,
    onTransactionError,
    toast
  ]);

  // Get transaction status with caching
  const getTransactionStatus = useCallback((transactionId: string) => {
    return getTransaction(transactionId);
  }, [getTransaction]);

  // Check if command might be GMP operation (for UI hints)
  const isLikelyGMPCommand = useCallback((command: string) => {
    const gmpKeywords = [
      'cross-chain',
      'from ethereum to',
      'from polygon to',
      'from arbitrum to',
      'on polygon',
      'on arbitrum',
      'on base',
      'call function',
      'execute on',
      'add liquidity.*using.*from',
      'stake.*using.*from'
    ];

    const commandLower = command.toLowerCase();
    return gmpKeywords.some(keyword => 
      new RegExp(keyword).test(commandLower)
    );
  }, []);

  // Get active transactions
  const activeTransactions = useMemo(() => {
    return Object.values(state.transactions).filter(
      tx => tx.status === 'pending' || tx.status === 'processing'
    );
  }, [state.transactions]);

  // Get completed transactions
  const completedTransactions = useMemo(() => {
    return Object.values(state.transactions).filter(
      tx => tx.status === 'completed'
    );
  }, [state.transactions]);

  // Get failed transactions
  const failedTransactions = useMemo(() => {
    return Object.values(state.transactions).filter(
      tx => tx.status === 'error'
    );
  }, [state.transactions]);

  // Statistics
  const stats = useMemo(() => ({
    total: Object.keys(state.transactions).length,
    active: activeTransactions.length,
    completed: completedTransactions.length,
    failed: failedTransactions.length,
    successRate: Object.keys(state.transactions).length > 0 
      ? (completedTransactions.length / Object.keys(state.transactions).length) * 100 
      : 0
  }), [state.transactions, activeTransactions, completedTransactions, failedTransactions]);

  return {
    // Core functions
    executeCommand,
    executeGMPTransaction,
    getTransactionStatus,
    
    // Utilities
    isLikelyGMPCommand,
    
    // Data
    activeTransactions,
    completedTransactions,
    failedTransactions,
    stats,
    
    // State
    isLoading: state.isLoading,
    error: state.error,
    supportedChains: state.supportedChains,
    supportedOperations: state.supportedOperations
  };
};

export default useGMPIntegration;

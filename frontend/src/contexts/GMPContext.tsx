/**
 * GMP Context Provider
 * Centralized state management for General Message Passing operations
 * Optimized for performance, maintainability, and user experience
 */

import React, { createContext, useContext, useReducer, useCallback, useEffect } from 'react'; // Dummy change
import { useToast } from '@chakra-ui/react';
import { axelarGMPService, GMPTransactionStatus } from '../services/axelarGMPService';
import { logger } from '../utils/logger';

// Types for clean type safety
export interface GMPTransaction {
  id: string;
  type: 'cross_chain_swap' | 'gmp_operation';
  status: 'pending' | 'processing' | 'completed' | 'error';
  sourceChain: string;
  destChain: string;
  sourceTxHash?: string;
  destTxHash?: string;
  steps: GMPTransactionStep[];
  metadata: Record<string, any>;
  createdAt: Date;
  updatedAt: Date;
  
  // Transaction details
  recipient: string;
  sourceToken?: string;
  destToken?: string;
  amount?: string;
  calldata?: string;
}

export interface GMPTransactionStep {
  id: string;
  title: string;
  description: string;
  status: 'pending' | 'processing' | 'completed' | 'error';
  txHash?: string;
  estimatedTime?: string;
  error?: string;
}

interface GMPState {
  transactions: Record<string, GMPTransaction>;
  activeTransaction: string | null;
  isLoading: boolean;
  error: string | null;
  supportedChains: string[];
  supportedOperations: string[];
}

// Action types for reducer
type GMPAction =
  | { type: 'SET_LOADING'; payload: boolean }
  | { type: 'SET_ERROR'; payload: string | null }
  | { type: 'ADD_TRANSACTION'; payload: GMPTransaction }
  | { type: 'UPDATE_TRANSACTION'; payload: { id: string; updates: Partial<GMPTransaction> } }
  | { type: 'SET_ACTIVE_TRANSACTION'; payload: string | null }
  | { type: 'UPDATE_TRANSACTION_STEP'; payload: { transactionId: string; stepId: string; updates: Partial<GMPTransactionStep> } }
  | { type: 'SET_SUPPORTED_CHAINS'; payload: string[] }
  | { type: 'SET_SUPPORTED_OPERATIONS'; payload: string[] };

// Initial state
const initialState: GMPState = {
  transactions: {},
  activeTransaction: null,
  isLoading: false,
  error: null,
  supportedChains: [],
  supportedOperations: []
};

// Reducer for state management
const gmpReducer = (state: GMPState, action: GMPAction): GMPState => {
  switch (action.type) {
    case 'SET_LOADING':
      return { ...state, isLoading: action.payload };
    
    case 'SET_ERROR':
      return { ...state, error: action.payload, isLoading: false };
    
    case 'ADD_TRANSACTION':
      return {
        ...state,
        transactions: {
          ...state.transactions,
          [action.payload.id]: action.payload
        },
        activeTransaction: action.payload.id
      };
    
    case 'UPDATE_TRANSACTION':
      const { id, updates } = action.payload;
      return {
        ...state,
        transactions: {
          ...state.transactions,
          [id]: {
            ...state.transactions[id],
            ...updates,
            updatedAt: new Date()
          }
        }
      };
    
    case 'SET_ACTIVE_TRANSACTION':
      return { ...state, activeTransaction: action.payload };
    
    case 'UPDATE_TRANSACTION_STEP':
      const { transactionId, stepId, updates: stepUpdates } = action.payload;
      const transaction = state.transactions[transactionId];
      if (!transaction) return state;
      
      return {
        ...state,
        transactions: {
          ...state.transactions,
          [transactionId]: {
            ...transaction,
            steps: transaction.steps.map(step =>
              step.id === stepId ? { ...step, ...stepUpdates } : step
            ),
            updatedAt: new Date()
          }
        }
      };
    
    case 'SET_SUPPORTED_CHAINS':
      return { ...state, supportedChains: action.payload };
    
    case 'SET_SUPPORTED_OPERATIONS':
      return { ...state, supportedOperations: action.payload };
    
    default:
      return state;
  }
};

// Context interface
interface GMPContextValue {
  state: GMPState;
  
  // Transaction management
  createTransaction: (transactionData: any) => Promise<string>;
  updateTransactionStatus: (id: string, status: GMPTransactionStatus) => void;
  trackTransaction: (id: string) => Promise<void>;
  
  // Execution
  executeTransaction: (id: string, signer: any) => Promise<void>;
  
  // Utilities
  getTransaction: (id: string) => GMPTransaction | undefined;
  getActiveTransaction: () => GMPTransaction | undefined;
  getSupportedChains: () => string[];
  getSupportedOperations: () => string[];
  
  // UI helpers
  setError: (error: string | null) => void;
  clearError: () => void;
}

// Create context
const GMPContext = createContext<GMPContextValue | undefined>(undefined);

// Provider component
export const GMPProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [state, dispatch] = useReducer(gmpReducer, initialState);
  const toast = useToast();

  // Initialize supported chains and operations
  useEffect(() => {
    const initializeGMP = async () => {
      try {
        const chains = axelarGMPService.getSupportedChains();
        dispatch({ type: 'SET_SUPPORTED_CHAINS', payload: chains.map(String) });
        
        // Mock supported operations - in real app, this would come from API
        const operations = [
          'cross_chain_swap',
          'cross_chain_transfer', 
          'general_message_passing',
          'cross_chain_contract_call',
          'cross_chain_liquidity_provision'
        ];
        dispatch({ type: 'SET_SUPPORTED_OPERATIONS', payload: operations });
      } catch (error) {
        logger.error('Failed to initialize GMP context:', error);
        dispatch({ type: 'SET_ERROR', payload: 'Failed to initialize GMP services' });
      }
    };

    initializeGMP();
  }, []);

  // Create transaction
  const createTransaction = useCallback(async (transactionData: any): Promise<string> => {
    const transactionId = `gmp_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    
    const transaction: GMPTransaction = {
      id: transactionId,
      type: transactionData.type || 'cross_chain_swap',
      status: 'pending',
      sourceChain: transactionData.source_chain || 'Ethereum',
      destChain: transactionData.dest_chain || 'Polygon',
      recipient: transactionData.recipient || transactionData.to || '',
      sourceToken: transactionData.source_token,
      destToken: transactionData.dest_token,
      amount: transactionData.amount,
      calldata: transactionData.calldata || transactionData.data,
      steps: transactionData.steps?.map((step: any, index: number) => ({
        id: `step_${index}`,
        title: step.description || `Step ${index + 1}`,
        description: step.description || '',
        status: 'pending' as const,
        estimatedTime: step.estimatedTime
      })) || [],
      metadata: transactionData.metadata || {},
      createdAt: new Date(),
      updatedAt: new Date()
    };

    dispatch({ type: 'ADD_TRANSACTION', payload: transaction });
    
    logger.info('Created GMP transaction:', transactionId);
    return transactionId;
  }, []);

  // Update transaction status
  const updateTransactionStatus = useCallback((id: string, status: GMPTransactionStatus) => {
    dispatch({
      type: 'UPDATE_TRANSACTION',
      payload: {
        id,
        updates: {
          status: status.status as any,
          sourceTxHash: status.sourceTxHash,
          destTxHash: status.destTxHash
        }
      }
    });

    // Update steps based on status
    if (status.gasPaid) {
      dispatch({
        type: 'UPDATE_TRANSACTION_STEP',
        payload: {
          transactionId: id,
          stepId: 'step_0',
          updates: { status: 'completed', txHash: status.sourceTxHash }
        }
      });
    }

    if (status.approved) {
      dispatch({
        type: 'UPDATE_TRANSACTION_STEP',
        payload: {
          transactionId: id,
          stepId: 'step_1',
          updates: { status: 'completed' }
        }
      });
    }

    if (status.executed) {
      dispatch({
        type: 'UPDATE_TRANSACTION_STEP',
        payload: {
          transactionId: id,
          stepId: 'step_2',
          updates: { status: 'completed', txHash: status.destTxHash }
        }
      });
    }
  }, []);

  // Track transaction
  const trackTransaction = useCallback(async (id: string) => {
    const transaction = state.transactions[id];
    if (!transaction || !transaction.sourceTxHash) return;

    try {
      const status = await axelarGMPService.trackTransaction(
        transaction.sourceTxHash,
        transaction.sourceChain,
        transaction.destChain
      );

      if (status) {
        updateTransactionStatus(id, status);
      }
    } catch (error) {
      logger.error('Failed to track transaction:', error);
      dispatch({
        type: 'UPDATE_TRANSACTION',
        payload: {
          id,
          updates: { status: 'error' }
        }
      });
    }
  }, [state.transactions, updateTransactionStatus]);

  // Execute transaction
  const executeTransaction = useCallback(async (id: string, walletClient: any) => {
    const transaction = state.transactions[id];
    if (!transaction) {
      throw new Error('Transaction not found');
    }

    dispatch({ type: 'SET_LOADING', payload: true });

    try {
      // Import wallet adapter
      const { createEthersSigner, getAxelarChainName } = await import('../utils/walletAdapters');
      
      // Convert wallet client to ethers signer
      const signer = createEthersSigner(walletClient);
      if (!signer) {
        throw new Error('Failed to create ethers signer from wallet client');
      }

      const chainId = walletClient.chainId || walletClient.chain?.id;
      if (!chainId) {
        throw new Error('Chain ID not available from wallet client');
      }

      // Update first step to processing
      dispatch({
        type: 'UPDATE_TRANSACTION_STEP',
        payload: {
          transactionId: id,
          stepId: 'step_0',
          updates: { status: 'processing' }
        }
      });

      // Prepare GMP parameters based on transaction type
      let result;
      if (transaction.type === 'cross_chain_swap') {
        // Execute cross-chain swap via Axelar GMP
        const swapParams = {
          destinationChain: typeof transaction.destChain === 'number' 
            ? getAxelarChainName(transaction.destChain)
            : transaction.destChain,
          destinationAddress: transaction.recipient,
          payload: transaction.calldata || '0x', // Should come from backend
          tokenSymbol: transaction.sourceToken || 'USDC',
          amount: transaction.amount || '0',
          gasLimit: 500000,
          refundAddress: await signer.getAddress()
        };

        result = await axelarGMPService.executeContractCallWithToken(
          chainId,
          swapParams,
          signer
        );
      } else {
        // Execute regular contract call
        const callParams = {
          destinationChain: typeof transaction.destChain === 'number' 
            ? getAxelarChainName(transaction.destChain)
            : transaction.destChain,
          destinationAddress: transaction.recipient,
          payload: transaction.calldata || '0x',
          gasLimit: 500000,
          refundAddress: await signer.getAddress()
        };

        result = await axelarGMPService.executeContractCall(
          chainId,
          callParams,
          signer
        );
      }

      if (!result.success) {
        throw new Error(result.error || 'Transaction execution failed');
      }

      // Update transaction with real tx hash
      dispatch({
        type: 'UPDATE_TRANSACTION',
        payload: {
          id,
          updates: {
            status: 'processing',
            sourceTxHash: result.txHash
          }
        }
      });

      // Complete first step
      dispatch({
        type: 'UPDATE_TRANSACTION_STEP',
        payload: {
          transactionId: id,
          stepId: 'step_0',
          updates: { status: 'completed', txHash: result.txHash }
        }
      });

      // Start tracking
      setTimeout(() => trackTransaction(id), 5000);

      toast({
        title: 'Transaction Submitted',
        description: `Cross-chain transaction submitted: ${result.txHash}`,
        status: 'success',
        duration: 5000,
        isClosable: true
      });

    } catch (error) {
      logger.error('Transaction execution failed:', error);
      dispatch({
        type: 'UPDATE_TRANSACTION',
        payload: {
          id,
          updates: { status: 'error' }
        }
      });

      toast({
        title: 'Transaction Failed',
        description: error instanceof Error ? error.message : 'Unknown error occurred',
        status: 'error',
        duration: 5000,
        isClosable: true
      });
    } finally {
      dispatch({ type: 'SET_LOADING', payload: false });
    }
  }, [state.transactions, trackTransaction, toast]);

  // Utility functions
  const getTransaction = useCallback((id: string) => state.transactions[id], [state.transactions]);
  const getActiveTransaction = useCallback(() => 
    state.activeTransaction ? state.transactions[state.activeTransaction] : undefined,
    [state.activeTransaction, state.transactions]
  );
  const getSupportedChains = useCallback(() => state.supportedChains, [state.supportedChains]);
  const getSupportedOperations = useCallback(() => state.supportedOperations, [state.supportedOperations]);

  // Error management
  const setError = useCallback((error: string | null) => {
    dispatch({ type: 'SET_ERROR', payload: error });
  }, []);

  const clearError = useCallback(() => {
    dispatch({ type: 'SET_ERROR', payload: null });
  }, []);

  // Active transaction tracking with polling
  useEffect(() => {
    const activeTransactions = Object.values(state.transactions).filter(
      tx => tx.status === 'processing' && tx.sourceTxHash
    );

    if (activeTransactions.length === 0) return;

    const trackingInterval = setInterval(async () => {
      for (const tx of activeTransactions) {
        try {
          await trackTransaction(tx.id);
        } catch (error) {
          logger.error(`Failed to track transaction ${tx.id}:`, error);
        }
      }
    }, 15000); // Track every 15 seconds

    // Cleanup after 45 minutes (reasonable max time for cross-chain)
    const cleanupTimeout = setTimeout(() => {
      clearInterval(trackingInterval);
    }, 45 * 60 * 1000);

    return () => {
      clearInterval(trackingInterval);
      clearTimeout(cleanupTimeout);
    };
  }, [state.transactions, trackTransaction]);

  const contextValue: GMPContextValue = {
    state,
    createTransaction,
    updateTransactionStatus,
    trackTransaction,
    executeTransaction,
    getTransaction,
    getActiveTransaction,
    getSupportedChains,
    getSupportedOperations,
    setError,
    clearError
  };

  return (
    <GMPContext.Provider value={contextValue}>
      {children}
    </GMPContext.Provider>
  );
};

// Custom hook for using GMP context
export const useGMP = (): GMPContextValue => {
  const context = useContext(GMPContext);
  if (!context) {
    throw new Error('useGMP must be used within a GMPProvider');
  }
  return context;
};

export default GMPContext;

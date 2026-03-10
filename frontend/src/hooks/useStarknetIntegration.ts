/**
 * Starknet Integration Hook
 * Handles Starknet-specific transactions and interaction with Starknet contracts.
 */

import { useCallback } from 'react';
import { useToast } from '@chakra-ui/react';
import { useAccount } from '@starknet-react/core';
import { logger } from '../utils/logger';

interface StarknetIntegrationOptions {
  onTransactionStart?: (txHash: string) => void;
  onTransactionComplete?: (txHash: string, result: Record<string, any>) => void;
  onTransactionError?: (error: string) => void;
}

export const useStarknetIntegration = (options: StarknetIntegrationOptions = {}) => {
  const { address, isConnected } = useAccount();
  const toast = useToast();

  const {
    onTransactionStart,
    onTransactionComplete,
    onTransactionError
  } = options;

  const executeStarknetCall = useCallback<(
    contractAddress: string,
    entrypoint: string,
    calldata: string[]
  ) => Promise<Record<string, any> | undefined>>(async (
    contractAddress: string,
    entrypoint: string,
    calldata: string[]
  ) => {
    if (!isConnected || !address) {
      const error = 'Starknet wallet not connected';
      onTransactionError?.(error);
      toast({
        title: 'Error',
        description: error,
        status: 'error',
        duration: 5000,
        isClosable: true
      });
      return;
    }

    try {
      logger.info('Executing Starknet call:', { contractAddress, entrypoint, calldata });

      // Mock transaction result for demonstration
      const result = {
        transaction_hash: `0x${Math.random().toString(16).slice(2).padStart(64, '0')}`
      };

      if (result?.transaction_hash) {
        onTransactionStart?.(result.transaction_hash);

        toast({
          title: 'Starknet Transaction Sent',
          description: `Hash: ${result.transaction_hash.slice(0, 10)}...`,
          status: 'info',
          duration: 5000,
          isClosable: true
        });

        // In a real app, we'd wait for receipt
        onTransactionComplete?.(result.transaction_hash, result);
        return result;
      }
    } catch (error) {
      logger.error('Starknet execution failed:', error);
      const errorMsg = error instanceof Error ? error.message : 'Unknown Starknet error';
      onTransactionError?.(errorMsg);

      toast({
        title: 'Starknet Error',
        description: errorMsg,
        status: 'error',
        duration: 5000,
        isClosable: true
      });
      throw error;
    }
  }, [address, isConnected, onTransactionStart, onTransactionComplete, onTransactionError, toast]);

  return {
    executeStarknetCall,
    isConnected,
    address
  } as const;
};

export default useStarknetIntegration;

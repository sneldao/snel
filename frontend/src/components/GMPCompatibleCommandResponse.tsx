/**
 * GMP Compatible Command Response
 * Backward-compatible wrapper that adds GMP capabilities to your existing CommandResponse
 * Maintains all existing functionality while adding cross-chain features
 */

import React, { memo, useMemo, lazy, Suspense } from 'react';
import { CommandResponse } from './CommandResponse';
import { useGMPIntegration } from '../hooks/useGMPIntegration';
import { VStack, Alert, AlertIcon, Text, useColorModeValue, Spinner, Box } from '@chakra-ui/react';

// Lazy load GMP components to reduce initial bundle size
const GMPCommandHandler = lazy(() => import('./GMP/GMPCommandHandler').then(m => ({ default: m.GMPCommandHandler })));
import { AgentType } from '../utils/agentInfo'; // Correct import for AgentType

import { ResponseContent, ResponseMetadata, TransactionData } from '../types/responses';

interface GMPCompatibleCommandResponseProps {
  content: ResponseContent;
  timestamp: string;
  isCommand: boolean;
  agentType?: AgentType;
  status?: "pending" | "processing" | "success" | "error";
  awaitingConfirmation?: boolean;
  transaction?: TransactionData;
  metadata?: ResponseMetadata;
  onExecuteTransaction?: (transactionData: TransactionData) => Promise<void>;
  isExecuting?: boolean;
  // Additional props for compatibility
  requires_selection?: boolean;
  all_quotes?: any[];
  onQuoteSelect?: (response: any, quote: any) => void;
  onActionClick?: (action: Record<string, unknown>) => void;
  className?: string;
}

export const GMPCompatibleCommandResponse: React.FC<GMPCompatibleCommandResponseProps> = memo((props) => {
  const { isLikelyGMPCommand } = useGMPIntegration();
  
  // Check if this is a GMP operation
  const isGMPOperation = useMemo(() => {
    // Simple type checks without type predicates
    const hasMetadata = (content: ResponseContent): boolean => {
      return typeof content === 'object' && content !== null && 'metadata' in content;
    };
    
    const hasTransactionData = (content: ResponseContent): boolean => {
      return typeof content === 'object' && content !== null && 'transaction_data' in content;
    };
    
    const hasOriginalCommand = (content: ResponseContent): boolean => {
      return typeof content === 'object' && content !== null && 'original_command' in (content as any);
    };
    
    return (hasMetadata(props.content) && (props.content as any).metadata?.uses_gmp) ||
           (hasMetadata(props.content) && (props.content as any).metadata?.axelar_powered) ||
           (hasTransactionData(props.content) && (props.content as any).transaction_data?.protocol === 'axelar_gmp') ||
           (hasOriginalCommand(props.content) && isLikelyGMPCommand(((props.content as any).original_command) || ''));
  }, [props.content, isLikelyGMPCommand]);

  // Check if command suggests GMP (for hints)
  const showGMPHint = useMemo(() => {
    if (isGMPOperation) return false; // Don't show hint if already GMP
    
    const command = (props.metadata?.parsed_command as any)?.original_command || 
                   (props.content as any)?.metadata?.command || 
                   '';
    return isLikelyGMPCommand(command);
  }, [props, isGMPOperation, isLikelyGMPCommand]);

  // GMP hint component
  const GMPHint = () => {
    const hintBg = useColorModeValue('blue.50', 'blue.900');
    const hintColor = useColorModeValue('blue.700', 'blue.200');

    return (
      <Alert status="info" variant="left-accent" bg={hintBg} borderRadius="md" mb={4}>
        <AlertIcon />
        <Text fontSize="sm" color={hintColor}>
          🔗 This looks like a cross-chain operation. SNEL can use Axelar Network for secure execution.
        </Text>
      </Alert>
    );
  };

  return (
    <VStack spacing={4} align="stretch" w="full">
      {/* Show GMP hint for likely cross-chain commands */}
      {showGMPHint && <GMPHint />}

      {/* Show GMP handler for confirmed GMP operations */}
      {isGMPOperation ? (
        <Suspense fallback={
          <Box textAlign="center" py={4}>
            <Spinner size="lg" color="blue.500" />
            <Text mt={2} fontSize="sm" color="gray.600">Loading cross-chain interface...</Text>
          </Box>
        }>
          <GMPCommandHandler
            response={{
              content: typeof props.content === 'object' && props.content !== null ? props.content as any : {} as any,
              message: typeof props.content === 'object' && props.content !== null && 'message' in props.content ? (props.content as any).message || 'Cross-chain operation prepared' : 'Cross-chain operation prepared',
              success: props.status === 'success'
            }}
            onExecute={props.onExecuteTransaction}
            isExecuting={props.isExecuting}
          />
        </Suspense>
      ) : (
        /* Show regular CommandResponse for non-GMP operations */
        <CommandResponse {...props} />
      )}
    </VStack>
  );
});

GMPCompatibleCommandResponse.displayName = 'GMPCompatibleCommandResponse';

export default GMPCompatibleCommandResponse;
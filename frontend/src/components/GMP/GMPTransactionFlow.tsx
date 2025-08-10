/**
 * GMP Transaction Flow Component
 * Handles the UI flow for Axelar General Message Passing transactions
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  Box,
  VStack,
  HStack,
  Text,
  Button,
  Progress,
  Alert,
  AlertIcon,
  AlertTitle,
  AlertDescription,
  Badge,
  Divider,
  Spinner,
  useToast,
  Card,
  CardBody,
  CardHeader,
  Heading,
  List,
  ListItem,
  ListIcon,
  Icon,
  Tooltip
} from '@chakra-ui/react';
import { CheckCircleIcon, TimeIcon, WarningIcon, InfoIcon } from '@chakra-ui/icons';
import { FaEthereum, FaExchangeAlt, FaRocket } from 'react-icons/fa';
import { axelarGMPService, GMPTransactionStatus } from '../../services/axelarGMPService';
import { logger } from '../../utils/logger';

interface GMPTransactionFlowProps {
  transactionData: {
    type: string;
    protocol: string;
    steps: Array<{
      type: string;
      description: string;
      to: string;
      data?: string;
      value?: string;
    }>;
    estimated_gas_fee: string;
    estimated_cost_usd: string;
    gateway_address: string;
    gas_service_address: string;
    source_chain?: string;
    dest_chain?: string;
    payload?: string;
  };
  onExecute: (txData: any) => Promise<{ hash: string; success: boolean; error?: string }>;
  onComplete?: (result: any) => void;
  onError?: (error: string) => void;
}

interface TransactionStep {
  id: string;
  title: string;
  description: string;
  status: 'pending' | 'processing' | 'completed' | 'error';
  txHash?: string;
  estimatedTime?: string;
  error?: string;
}

export const GMPTransactionFlow: React.FC<GMPTransactionFlowProps> = ({
  transactionData,
  onExecute,
  onComplete,
  onError
}) => {
  const [currentStep, setCurrentStep] = useState(0);
  const [steps, setSteps] = useState<TransactionStep[]>([]);
  const [isExecuting, setIsExecuting] = useState(false);
  const [transactionStatus, setTransactionStatus] = useState<GMPTransactionStatus | null>(null);
  const [sourceTxHash, setSourceTxHash] = useState<string>('');
  const toast = useToast();

  // Initialize transaction steps
  useEffect(() => {
    const initialSteps: TransactionStep[] = [
      {
        id: 'gas_payment',
        title: 'Pay Cross-Chain Gas',
        description: `Pay gas fee for execution on ${transactionData.dest_chain || 'destination chain'}`,
        status: 'pending',
        estimatedTime: '1-2 minutes'
      },
      {
        id: 'source_execution',
        title: 'Execute on Source Chain',
        description: `Execute transaction on ${transactionData.source_chain || 'source chain'}`,
        status: 'pending',
        estimatedTime: '2-5 minutes'
      },
      {
        id: 'axelar_processing',
        title: 'Axelar Network Processing',
        description: 'Axelar validators process and approve the cross-chain message',
        status: 'pending',
        estimatedTime: '5-15 minutes'
      },
      {
        id: 'dest_execution',
        title: 'Execute on Destination Chain',
        description: `Complete transaction on ${transactionData.dest_chain || 'destination chain'}`,
        status: 'pending',
        estimatedTime: '1-3 minutes'
      }
    ];

    setSteps(initialSteps);
  }, [transactionData]);

  const updateStepsFromStatus = useCallback((status: GMPTransactionStatus) => {
    setSteps(prevSteps => prevSteps.map(step => {
      switch (step.id) {
        case 'gas_payment':
          return {
            ...step,
            status: status.gasPaid ? 'completed' : step.status,
            txHash: status.gasPaid ? sourceTxHash : undefined
          };
        case 'source_execution':
          return {
            ...step,
            status: status.sourceTxHash ? 'completed' : step.status,
            txHash: status.sourceTxHash
          };
        case 'axelar_processing':
          return {
            ...step,
            status: status.approved ? 'completed' : (status.gasPaid ? 'processing' : step.status)
          };
        case 'dest_execution':
          return {
            ...step,
            status: status.executed ? 'completed' : (status.approved ? 'processing' : step.status),
            txHash: status.destTxHash
          };
        default:
          return step;
      }
    }));

    // Update current step
    if (status.executed) {
      setCurrentStep(4);
      onComplete?.(status);
    } else if (status.approved) {
      setCurrentStep(3);
    } else if (status.gasPaid) {
      setCurrentStep(2);
    }
  }, [onComplete, sourceTxHash]);

  // Track transaction status
  useEffect(() => {
    if (sourceTxHash && transactionData.source_chain && transactionData.dest_chain) {
      const trackTransaction = async () => {
        try {
          const status = await axelarGMPService.trackTransaction(
            sourceTxHash,
            transactionData.source_chain!,
            transactionData.dest_chain!
          );
          
          if (status) {
            setTransactionStatus(status);
            updateStepsFromStatus(status);
          }
        } catch (error) {
          logger.error('Error tracking transaction:', error);
        }
      };

      const interval = setInterval(trackTransaction, 10000); // Check every 10 seconds
      trackTransaction(); // Initial check

      return () => clearInterval(interval);
    }
  }, [sourceTxHash, transactionData.source_chain, transactionData.dest_chain, updateStepsFromStatus]);

  const executeTransaction = async () => {
    setIsExecuting(true);
    
    try {
      // Execute each step sequentially
      for (let i = 0; i < transactionData.steps.length; i++) {
        const step = transactionData.steps[i];
        setCurrentStep(i);
        
        // Update step status to processing
        setSteps(prevSteps => prevSteps.map((s, index) => 
          index === i ? { ...s, status: 'processing' } : s
        ));

        // Execute the transaction step
        const result = await onExecute({
          to: step.to,
          data: step.data || '0x',
          value: step.value || '0'
        });

        if (!result.success) {
          throw new Error(result.error || 'Transaction failed');
        }

        // Update step status to completed
        setSteps(prevSteps => prevSteps.map((s, index) => 
          index === i ? { ...s, status: 'completed', txHash: result.hash } : s
        ));

        // Store source transaction hash for tracking
        if (i === 1) { // Source execution step
          setSourceTxHash(result.hash);
        }

        toast({
          title: 'Step Completed',
          description: `${step.description} completed successfully`,
          status: 'success',
          duration: 3000,
          isClosable: true,
        });
      }

      toast({
        title: 'Transaction Initiated',
        description: 'Cross-chain transaction has been initiated. Tracking progress...',
        status: 'info',
        duration: 5000,
        isClosable: true,
      });

    } catch (error) {
      logger.error('Transaction execution failed:', error);
      
      // Update current step to error
      setSteps(prevSteps => prevSteps.map((s, index) => 
        index === currentStep ? { 
          ...s, 
          status: 'error', 
          error: error instanceof Error ? error.message : 'Unknown error'
        } : s
      ));

      onError?.(error instanceof Error ? error.message : 'Transaction failed');
      
      toast({
        title: 'Transaction Failed',
        description: error instanceof Error ? error.message : 'Unknown error occurred',
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    } finally {
      setIsExecuting(false);
    }
  };

  const getStepIcon = (step: TransactionStep) => {
    switch (step.status) {
      case 'completed':
        return <CheckCircleIcon color="green.500" />;
      case 'processing':
        return <Spinner size="sm" color="blue.500" />;
      case 'error':
        return <WarningIcon color="red.500" />;
      default:
        return <TimeIcon color="gray.400" />;
    }
  };

  const getProgressValue = () => {
    const completedSteps = steps.filter(step => step.status === 'completed').length;
    return (completedSteps / steps.length) * 100;
  };

  return (
    <Box maxW="600px" mx="auto" p={4}>
      <Card>
        <CardHeader>
          <HStack justify="space-between" align="center">
            <VStack align="start" spacing={1}>
              <Heading size="md">Cross-Chain Transaction</Heading>
              <HStack>
                <Badge colorScheme="blue" variant="subtle">
                  <Icon as={FaRocket} mr={1} />
                  Powered by Axelar GMP
                </Badge>
                {transactionData.type === 'cross_chain_swap' && (
                  <Badge colorScheme="green" variant="subtle">
                    <Icon as={FaExchangeAlt} mr={1} />
                    Cross-Chain Swap
                  </Badge>
                )}
              </HStack>
            </VStack>
            <VStack align="end" spacing={1}>
              <Text fontSize="sm" color="gray.600">
                Est. Cost: ${transactionData.estimated_cost_usd}
              </Text>
              <Text fontSize="xs" color="gray.500">
                Gas: {parseFloat(transactionData.estimated_gas_fee).toFixed(6)} ETH
              </Text>
            </VStack>
          </HStack>
        </CardHeader>

        <CardBody>
          <VStack spacing={6} align="stretch">
            {/* Progress Bar */}
            <Box>
              <HStack justify="space-between" mb={2}>
                <Text fontSize="sm" fontWeight="medium">
                  Progress
                </Text>
                <Text fontSize="sm" color="gray.600">
                  {Math.round(getProgressValue())}% Complete
                </Text>
              </HStack>
              <Progress 
                value={getProgressValue()} 
                colorScheme="blue" 
                size="lg" 
                borderRadius="md"
              />
            </Box>

            {/* Transaction Steps */}
            <VStack spacing={4} align="stretch">
              <Text fontSize="md" fontWeight="semibold">
                Transaction Steps
              </Text>
              
              <List spacing={3}>
                {steps.map((step, index) => (
                  <ListItem key={step.id}>
                    <HStack spacing={3} align="start">
                      <ListIcon as={() => getStepIcon(step)} mt={1} />
                      <VStack align="start" spacing={1} flex={1}>
                        <HStack justify="space-between" w="full">
                          <Text fontWeight="medium" fontSize="sm">
                            {step.title}
                          </Text>
                          {step.estimatedTime && step.status === 'pending' && (
                            <Text fontSize="xs" color="gray.500">
                              ~{step.estimatedTime}
                            </Text>
                          )}
                        </HStack>
                        <Text fontSize="xs" color="gray.600">
                          {step.description}
                        </Text>
                        {step.txHash && (
                          <Text fontSize="xs" color="blue.500" fontFamily="mono">
                            Tx: {step.txHash.slice(0, 10)}...{step.txHash.slice(-8)}
                          </Text>
                        )}
                        {step.error && (
                          <Text fontSize="xs" color="red.500">
                            Error: {step.error}
                          </Text>
                        )}
                      </VStack>
                    </HStack>
                  </ListItem>
                ))}
              </List>
            </VStack>

            {/* Transaction Status */}
            {transactionStatus && (
              <Alert status={
                transactionStatus.status === 'executed' ? 'success' :
                transactionStatus.status === 'error' ? 'error' : 'info'
              }>
                <AlertIcon />
                <Box>
                  <AlertTitle>
                    {transactionStatus.status === 'executed' ? 'Transaction Complete!' :
                     transactionStatus.status === 'error' ? 'Transaction Error' :
                     'Transaction Processing'}
                  </AlertTitle>
                  <AlertDescription>
                    {transactionStatus.status === 'executed' 
                      ? 'Your cross-chain transaction has been completed successfully.'
                      : transactionStatus.status === 'error'
                      ? transactionStatus.error || 'An error occurred during processing.'
                      : `Estimated time remaining: ${transactionStatus.estimatedTimeRemaining || '5-10 minutes'}`
                    }
                  </AlertDescription>
                </Box>
              </Alert>
            )}

            {/* Action Buttons */}
            <Divider />
            
            <HStack justify="space-between">
              <VStack align="start" spacing={1}>
                <Text fontSize="xs" color="gray.500">
                  Network: {transactionData.source_chain} → {transactionData.dest_chain}
                </Text>
                <Text fontSize="xs" color="gray.500">
                  Protocol: Axelar General Message Passing
                </Text>
              </VStack>
              
              <Button
                colorScheme="blue"
                onClick={executeTransaction}
                isLoading={isExecuting}
                loadingText="Executing..."
                isDisabled={isExecuting || transactionStatus?.status === 'executed'}
                size="lg"
              >
                {transactionStatus?.status === 'executed' ? 'Completed' : 'Execute Transaction'}
              </Button>
            </HStack>

            {/* Info Alert */}
            <Alert status="info" variant="left-accent">
              <AlertIcon />
              <Box fontSize="sm">
                <Text fontWeight="medium">About Cross-Chain Transactions</Text>
                <Text>
                  This transaction uses Axelar&apos;s secure cross-chain infrastructure. 
                  The process involves multiple steps and may take 5-20 minutes to complete.
                </Text>
              </Box>
            </Alert>
          </VStack>
        </CardBody>
      </Card>
    </Box>
  );
};

export default GMPTransactionFlow;

/**
 * GMP Command Handler Component
 * Intelligent handler for GMP operations in the chat interface
 * Seamlessly integrates with existing chat flow while adding GMP capabilities
 */

import React, { memo, useCallback, useMemo } from 'react';
import {
  Box,
  VStack,
  HStack,
  Text,
  Button,
  Alert,
  AlertIcon,
  AlertTitle,
  AlertDescription,
  Badge,
  Divider,
  useColorModeValue,
  Collapse,
  Icon,
  Tooltip,
  Flex,
  Spacer
} from '@chakra-ui/react';
import {
  FiArrowRight,
  FiZap,
  FiShield,
  FiClock,
  FiDollarSign,
  FiInfo,
  FiChevronDown,
  FiChevronUp
} from 'react-icons/fi';
import { motion } from 'framer-motion';
import { useGMP } from '../../contexts/GMPContext';
import { formatCurrency } from '../../utils/formatters';

// Chain avatar component (inline for now)
const ChainAvatar: React.FC<{ chain: string; size?: string }> = ({ chain, size = 'sm' }) => {
  const chainColors: Record<string, string> = {
    'Ethereum': '#627EEA',
    'Polygon': '#8247E5',
    'Arbitrum': '#28A0F0',
    'Optimism': '#FF0420',
    'Base': '#0052FF',
    'Avalanche': '#E84142'
  };

  return (
    <Box
      w={size === 'sm' ? '24px' : '32px'}
      h={size === 'sm' ? '24px' : '32px'}
      borderRadius="full"
      bg={chainColors[chain] || 'gray.500'}
      color="white"
      fontSize="xs"
      fontWeight="bold"
      display="flex"
      alignItems="center"
      justifyContent="center"
    >
      {chain.slice(0, 2).toUpperCase()}
    </Box>
  );
};

// Motion components
const MotionBox = motion(Box);

interface GMPCommandHandlerProps {
  response: {
    content: {
      transaction_data?: {
        type: string;
        protocol: string;
        steps: Array<{
          type: string;
          description: string;
          to?: string;
          value?: string;
          data?: string;
        }>;
        estimated_gas_fee: string;
        estimated_cost_usd: string;
        gateway_address?: string;
        gas_service_address?: string;
        source_chain?: string;
        dest_chain?: string;
      };
      metadata?: {
        uses_gmp?: boolean;
        axelar_powered?: boolean;
        source_chain?: string;
        dest_chain?: string;
        source_token?: string;
        dest_token?: string;
        amount?: string;
      };
    };
    message: string;
    success: boolean;
  };
  onExecute?: (transactionData: any) => Promise<void>;
  isExecuting?: boolean;
}

// Step preview component
const StepPreview: React.FC<{ 
  steps: Array<{ type: string; description: string }>;
  isExpanded: boolean;
}> = memo(({ steps, isExpanded }) => {
  const stepIcons = {
    approve: FiShield,
    pay_gas: FiDollarSign,
    call_contract: FiZap,
    transfer: FiArrowRight
  };
  const stepBg = useColorModeValue('gray.50', 'gray.700');

  return (
    <Collapse in={isExpanded} animateOpacity>
      <VStack spacing={2} align="stretch" mt={3}>
        {steps.map((step, index) => (
          <HStack
            key={index}
            p={3}
            bg={stepBg}
            borderRadius="md"
            spacing={3}
          >
            <Icon
              as={stepIcons[step.type as keyof typeof stepIcons] || FiInfo}
              color="blue.500"
              size="16px"
            />
            <VStack align="start" spacing={0} flex={1}>
              <Text fontSize="sm" fontWeight="medium">
                Step {index + 1}: {step.type.replace('_', ' ').toUpperCase()}
              </Text>
              <Text fontSize="xs" color="gray.600">
                {step.description}
              </Text>
            </VStack>
            <Badge colorScheme="blue" variant="subtle" size="sm">
              {step.type}
            </Badge>
          </HStack>
        ))}
      </VStack>
    </Collapse>
  );
});
StepPreview.displayName = 'StepPreview';

// Cost breakdown component
const CostBreakdown: React.FC<{
  gasFee: string;
  costUsd: string;
  isExpanded: boolean;
}> = memo(({ gasFee, costUsd, isExpanded }) => {
  const gasFeeNum = parseFloat(gasFee);
  const costUsdNum = parseFloat(costUsd);

  return (
    <Collapse in={isExpanded} animateOpacity>
      <VStack spacing={2} align="stretch" mt={3}>
        <HStack justify="space-between">
          <Text fontSize="sm" color="gray.600">Gas Fee:</Text>
          <Text fontSize="sm" fontWeight="medium" fontFamily="mono">
            {gasFeeNum.toFixed(6)} ETH
          </Text>
        </HStack>
        <HStack justify="space-between">
          <Text fontSize="sm" color="gray.600">USD Equivalent:</Text>
          <Text fontSize="sm" fontWeight="medium">
            ${costUsdNum.toFixed(2)}
          </Text>
        </HStack>
        <Divider />
        <HStack justify="space-between">
          <Text fontSize="sm" fontWeight="semibold">Total Cost:</Text>
          <Text fontSize="sm" fontWeight="bold" color="blue.600">
            ${costUsdNum.toFixed(2)}
          </Text>
        </HStack>
      </VStack>
    </Collapse>
  );
});
CostBreakdown.displayName = 'CostBreakdown';

// Main component
export const GMPCommandHandler: React.FC<GMPCommandHandlerProps> = memo(({
  response,
  onExecute,
  isExecuting = false
}) => {
  const { createTransaction } = useGMP();
  const [showSteps, setShowSteps] = React.useState(false);
  const [showCosts, setShowCosts] = React.useState(false);

  // Extract transaction data
  const transactionData = response.content.transaction_data;
  const metadata = response.content.metadata;
  const isGMPOperation = metadata?.uses_gmp || metadata?.axelar_powered;

  // Theme colors
  const cardBg = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.600');
  const accentColor = useColorModeValue('blue.500', 'blue.300');

  // Memoized values
  const operationType = useMemo(() => {
    if (!transactionData) return 'Unknown';
    return transactionData.type.replace('_', ' ').toUpperCase();
  }, [transactionData]);

  const estimatedTime = useMemo(() => {
    if (!isGMPOperation) return '1-2 minutes';
    return '5-15 minutes'; // Cross-chain operations take longer
  }, [isGMPOperation]);

  // Handle execution
  const handleExecute = useCallback(async () => {
    if (!transactionData || !onExecute) return;

    try {
      // Create transaction in GMP context
      const transactionId = await createTransaction({
        type: transactionData.type,
        source_chain: transactionData.source_chain || metadata?.source_chain,
        dest_chain: transactionData.dest_chain || metadata?.dest_chain,
        steps: transactionData.steps,
        metadata: {
          ...metadata,
          estimated_gas_fee: transactionData.estimated_gas_fee,
          estimated_cost_usd: transactionData.estimated_cost_usd
        }
      });

      // Execute via parent handler
      await onExecute(transactionData);
    } catch (error) {
      console.error('Failed to execute GMP transaction:', error);
    }
  }, [transactionData, metadata, onExecute, createTransaction]);

  // Don't render if not a GMP operation
  if (!isGMPOperation || !transactionData) {
    return null;
  }

  return (
    <MotionBox
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      <Box
        bg={cardBg}
        borderColor={borderColor}
        borderWidth="1px"
        borderRadius="xl"
        p={4}
        shadow="sm"
      >
        <VStack spacing={4} align="stretch">
          {/* Header */}
          <HStack justify="space-between" align="start">
            <VStack align="start" spacing={1}>
              <HStack spacing={2}>
                <Badge colorScheme="blue" variant="solid" px={2} py={1}>
                  <HStack spacing={1}>
                    <Icon as={FiZap} size="12px" />
                    <Text fontSize="xs">GMP</Text>
                  </HStack>
                </Badge>
                <Text fontSize="lg" fontWeight="semibold">
                  {operationType}
                </Text>
              </HStack>
              
              {/* Chain flow */}
              {(transactionData.source_chain || transactionData.dest_chain) && (
                <HStack spacing={2}>
                  <ChainAvatar 
                    chain={transactionData.source_chain || metadata?.source_chain || 'Ethereum'} 
                    size="sm" 
                  />
                  <Icon as={FiArrowRight} color={accentColor} size="16px" />
                  <ChainAvatar 
                    chain={transactionData.dest_chain || metadata?.dest_chain || 'Polygon'} 
                    size="sm" 
                  />
                  <Text fontSize="sm" color="gray.600">
                    Cross-chain operation
                  </Text>
                </HStack>
              )}
            </VStack>

            <VStack align="end" spacing={1}>
              <HStack spacing={1}>
                <Icon as={FiClock} size="14px" color="gray.500" />
                <Text fontSize="sm" color="gray.600">
                  ~{estimatedTime}
                </Text>
              </HStack>
              <Text fontSize="sm" fontWeight="semibold" color="green.600">
                ${parseFloat(transactionData.estimated_cost_usd).toFixed(2)}
              </Text>
            </VStack>
          </HStack>

          {/* Message */}
          <Text fontSize="sm" color="gray.700">
            {response.message}
          </Text>

          {/* Expandable sections */}
          <VStack spacing={2} align="stretch">
            {/* Steps section */}
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowSteps(!showSteps)}
              rightIcon={showSteps ? <FiChevronUp /> : <FiChevronDown />}
              justifyContent="space-between"
              fontWeight="normal"
            >
              <HStack>
                <Text>Transaction Steps</Text>
                <Badge colorScheme="blue" variant="subtle">
                  {transactionData.steps.length}
                </Badge>
              </HStack>
            </Button>
            
            <StepPreview 
              steps={transactionData.steps} 
              isExpanded={showSteps}
            />

            {/* Cost section */}
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowCosts(!showCosts)}
              rightIcon={showCosts ? <FiChevronUp /> : <FiChevronDown />}
              justifyContent="space-between"
              fontWeight="normal"
            >
              <HStack>
                <Text>Cost Breakdown</Text>
                <Badge colorScheme="green" variant="subtle">
                  ${parseFloat(transactionData.estimated_cost_usd).toFixed(2)}
                </Badge>
              </HStack>
            </Button>
            
            <CostBreakdown
              gasFee={transactionData.estimated_gas_fee}
              costUsd={transactionData.estimated_cost_usd}
              isExpanded={showCosts}
            />
          </VStack>

          {/* Security notice */}
          <Alert status="info" variant="left-accent" size="sm">
            <AlertIcon />
            <Box>
              <AlertTitle fontSize="sm">Secured by Axelar Network</AlertTitle>
              <AlertDescription fontSize="xs">
                This cross-chain operation uses Axelar&apos;s decentralized validator network 
                for maximum security and reliability.
              </AlertDescription>
            </Box>
          </Alert>

          {/* Action button */}
          <Divider />
          <Flex>
            <Spacer />
            <Button
              colorScheme="blue"
              size="lg"
              onClick={handleExecute}
              isLoading={isExecuting}
              loadingText="Executing..."
              leftIcon={<FiZap />}
              borderRadius="xl"
              px={8}
            >
              Execute Cross-Chain Transaction
            </Button>
          </Flex>
        </VStack>
      </Box>
    </MotionBox>
  );
});

GMPCommandHandler.displayName = 'GMPCommandHandler';

export default GMPCommandHandler;

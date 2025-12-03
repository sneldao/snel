/**
 * GMP Transaction Card Component
 * Beautiful, performant, and user-delightful transaction display
 * Optimized for clarity, accessibility, and visual appeal
 * 
 * Privacy variant (inline address input) integrated for seamless UX
 */

import React, { memo, useMemo, useState } from 'react';
import {
  Box,
  Card,
  CardBody,
  CardHeader,
  VStack,
  HStack,
  Text,
  Badge,
  Progress,
  Button,
  Icon,
  Tooltip,
  useColorModeValue,
  Skeleton,
  Fade,
  ScaleFade,
  Divider,
  Avatar,
  AvatarGroup,
  Flex,
  Spacer
} from '@chakra-ui/react';
import {
  FiArrowRight,
  FiClock,
  FiCheck,
  FiAlertCircle,
  FiExternalLink,
  FiZap,
  FiShield,
  FiTrendingUp,
  FiLock
} from 'react-icons/fi';
import { motion, AnimatePresence } from 'framer-motion';
import { GMPTransaction, GMPTransactionStep } from '../../contexts/GMPContext';
import { formatDistanceToNow } from 'date-fns';
import { PrivacyAddressInput, validateZcashAddress } from '../Privacy/PrivacyAddressInput';

// Motion components for smooth animations
const MotionBox = motion(Box);
const MotionCard = motion(Card);

interface GMPTransactionCardProps {
  transaction: GMPTransaction;
  onExecute?: () => void;
  onViewDetails?: () => void;
  onCancel?: () => void;
  isExecuting?: boolean;
  compact?: boolean;
  variant?: 'default' | 'privacy';
  privacyLevel?: string;
  zcashAddress?: string;
  onZcashAddressChange?: (address: string) => void;
}

// Step status icon component
const StepStatusIcon: React.FC<{ status: GMPTransactionStep['status'] }> = memo(({ status }) => {
  const iconProps = { size: '16px' };

  switch (status) {
    case 'completed':
      return <Icon as={FiCheck} color="green.500" {...iconProps} />;
    case 'processing':
      return (
        <MotionBox
          animate={{ rotate: 360 }}
          transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
        >
          <Icon as={FiZap} color="blue.500" {...iconProps} />
        </MotionBox>
      );
    case 'error':
      return <Icon as={FiAlertCircle} color="red.500" {...iconProps} />;
    default:
      return <Icon as={FiClock} color="gray.400" {...iconProps} />;
  }
});
StepStatusIcon.displayName = 'StepStatusIcon';

// Chain avatar component
const ChainAvatar: React.FC<{ chain: string; size?: string }> = memo(({ chain, size = 'sm' }) => {
  const chainColors: Record<string, string> = {
    'Ethereum': '#627EEA',
    'Polygon': '#8247E5',
    'Arbitrum': '#28A0F0',
    'Optimism': '#FF0420',
    'Base': '#0052FF',
    'Avalanche': '#E84142'
  };

  return (
    <Avatar
      size={size}
      name={chain}
      bg={chainColors[chain] || 'gray.500'}
      color="white"
      fontSize="xs"
      fontWeight="bold"
    />
  );
});
ChainAvatar.displayName = 'ChainAvatar';

// Progress calculation hook
const useTransactionProgress = (steps: GMPTransactionStep[]) => {
  return useMemo(() => {
    const completedSteps = steps.filter(step => step.status === 'completed').length;
    const totalSteps = steps.length;
    const progress = totalSteps > 0 ? (completedSteps / totalSteps) * 100 : 0;

    return {
      progress,
      completedSteps,
      totalSteps,
      isComplete: progress === 100,
      hasError: steps.some(step => step.status === 'error')
    };
  }, [steps]);
};

// Status badge component
const StatusBadge: React.FC<{ status: GMPTransaction['status'] }> = memo(({ status }) => {
  const statusConfig = {
    pending: { colorScheme: 'gray', label: 'Pending', icon: FiClock },
    processing: { colorScheme: 'blue', label: 'Processing', icon: FiZap },
    completed: { colorScheme: 'green', label: 'Completed', icon: FiCheck },
    error: { colorScheme: 'red', label: 'Failed', icon: FiAlertCircle }
  };

  const config = statusConfig[status];

  return (
    <Badge
      colorScheme={config.colorScheme}
      variant="subtle"
      display="flex"
      alignItems="center"
      gap={1}
      px={2}
      py={1}
      borderRadius="md"
    >
      <Icon as={config.icon} size="12px" />
      {config.label}
    </Badge>
  );
});
StatusBadge.displayName = 'StatusBadge';

// Main component
export const GMPTransactionCard: React.FC<GMPTransactionCardProps> = memo(({
  transaction,
  onExecute,
  onViewDetails,
  onCancel,
  isExecuting = false,
  compact = false,
  variant = 'default',
  privacyLevel,
  zcashAddress = '',
  onZcashAddressChange
}) => {
  // Address validation for privacy variant
  const [addressError, setAddressError] = useState('');
  const isPrivacyAddressValid = zcashAddress ? validateZcashAddress(zcashAddress).isValid : false;
  // Theme colors (privacy variant uses yellow/gold theme)
  const isPrivacy = variant === 'privacy';
  const cardBg = useColorModeValue(
    isPrivacy ? 'yellow.50' : 'white',
    isPrivacy ? 'gray.800' : 'gray.800'
  );
  const borderColor = useColorModeValue(
    isPrivacy ? 'yellow.200' : 'gray.200',
    isPrivacy ? 'yellow.600' : 'gray.600'
  );
  const textColor = useColorModeValue('gray.600', 'gray.300');
  const accentColor = useColorModeValue(
    isPrivacy ? 'yellow.500' : 'blue.500',
    isPrivacy ? 'yellow.300' : 'blue.300'
  );
  const progressBg = useColorModeValue('gray.100', 'gray.700');
  const stepBg = useColorModeValue('gray.50', 'gray.700');
  const axelarBoxBg = useColorModeValue(
    isPrivacy ? 'yellow.50' : 'blue.50',
    isPrivacy ? 'yellow.900' : 'blue.900'
  );

  // Progress calculation
  const { progress, completedSteps, totalSteps, isComplete, hasError } = useTransactionProgress(transaction.steps);

  // Animation variants
  const cardVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: { opacity: 1, y: 0 },
    hover: { y: -2, transition: { duration: 0.2 } }
  };

  // Progress color
  const progressColor = hasError ? 'red' : isComplete ? 'green' : 'blue';

  return (
    <MotionCard
      variants={cardVariants}
      initial="hidden"
      animate="visible"
      whileHover="hover"
      bg={cardBg}
      borderColor={borderColor}
      borderWidth="1px"
      borderRadius="xl"
      overflow="hidden"
      shadow="sm"
      _hover={{ shadow: 'md' }}
      transition="all 0.2s"
    >
      <CardHeader pb={compact ? 2 : 4}>
        <Flex align="center" justify="space-between">
          <HStack spacing={3}>
            {/* Privacy badge for privacy variant */}
            {isPrivacy && (
              <Badge colorScheme="yellow" variant="solid" display="flex" alignItems="center" gap={1}>
                <Icon as={FiLock} boxSize={3} />
                SHIELDED
              </Badge>
            )}

            {/* Chain flow visualization */}
            <HStack spacing={2}>
              <ChainAvatar chain={transaction.sourceChain} />
              <Icon as={FiArrowRight} color={accentColor} size="16px" />
              <ChainAvatar chain={transaction.destChain} />
            </HStack>

            <VStack align="start" spacing={0}>
              <Text fontSize="sm" fontWeight="semibold" color={textColor}>
                {transaction.sourceChain} → {transaction.destChain}
                {isPrivacy && ' (Privacy)'}
              </Text>
              <Text fontSize="xs" color={textColor} opacity={0.8}>
                {transaction.type.replace('_', ' ').toUpperCase()}
              </Text>
            </VStack>
          </HStack>

          <VStack align="end" spacing={1}>
            <StatusBadge status={transaction.status} />
            <Text fontSize="xs" color={textColor} opacity={0.7}>
              {formatDistanceToNow(transaction.createdAt, { addSuffix: true })}
            </Text>
          </VStack>
        </Flex>
      </CardHeader>

      <CardBody pt={0}>
        <VStack spacing={compact ? 3 : 4} align="stretch">
          {/* Progress section */}
          <Box>
            <Flex justify="space-between" align="center" mb={2}>
              <Text fontSize="sm" fontWeight="medium">
                Progress
              </Text>
              <Text fontSize="sm" color={textColor}>
                {completedSteps}/{totalSteps} steps
              </Text>
            </Flex>

            <Progress
              value={progress}
              colorScheme={progressColor}
              size="md"
              borderRadius="full"
              bg={progressBg}
            />
          </Box>

          {/* Steps preview (compact view) */}
          {compact && (
            <HStack spacing={2} justify="center">
              {transaction.steps.map((step, index) => (
                <Tooltip key={step.id} label={step.title} placement="top">
                  <Box
                    w={8}
                    h={8}
                    borderRadius="full"
                    bg={
                      step.status === 'completed' ? 'green.100' :
                        step.status === 'processing' ? 'blue.100' :
                          step.status === 'error' ? 'red.100' : 'gray.100'
                    }
                    display="flex"
                    alignItems="center"
                    justifyContent="center"
                  >
                    <StepStatusIcon status={step.status} />
                  </Box>
                </Tooltip>
              ))}
            </HStack>
          )}

          {/* Detailed steps (full view) */}
          {!compact && (
            <VStack spacing={2} align="stretch">
              <Text fontSize="sm" fontWeight="medium" mb={1}>
                Transaction Steps
              </Text>
              {transaction.steps.map((step, index) => (
                <Fade key={step.id} in={true}>
                  <HStack
                    p={3}
                    bg={stepBg}
                    borderRadius="md"
                    spacing={3}
                  >
                    <StepStatusIcon status={step.status} />
                    <VStack align="start" spacing={0} flex={1}>
                      <Text fontSize="sm" fontWeight="medium">
                        {step.title}
                      </Text>
                      <Text fontSize="xs" color={textColor} opacity={0.8}>
                        {step.description}
                      </Text>
                      {step.txHash && (
                        <HStack spacing={1}>
                          <Text fontSize="xs" color={accentColor} fontFamily="mono">
                            {step.txHash.slice(0, 10)}...{step.txHash.slice(-8)}
                          </Text>
                          <Icon as={FiExternalLink} size="10px" color={accentColor} />
                        </HStack>
                      )}
                    </VStack>
                    {step.estimatedTime && step.status === 'pending' && (
                      <Text fontSize="xs" color={textColor} opacity={0.6}>
                        ~{step.estimatedTime}
                      </Text>
                    )}
                  </HStack>
                </Fade>
              ))}
            </VStack>
          )}

          {/* Privacy level indicator */}
          {isPrivacy && privacyLevel && (
            <HStack justify="space-between" fontSize="sm" p={2} bg={stepBg} borderRadius="md">
              <Text color="gray.500">Privacy Level:</Text>
              <Text fontWeight="bold" color="green.500">
                {privacyLevel}
              </Text>
            </HStack>
          )}

          {/* Zcash Address Input (Privacy variant only) */}
          {isPrivacy && onZcashAddressChange && (
            <>
              <Divider />
              <PrivacyAddressInput
                address={zcashAddress}
                onAddressChange={(newAddress) => {
                  onZcashAddressChange(newAddress);
                  setAddressError('');
                }}
                error={addressError}
                isLoading={isExecuting}
                showWalletLinks={!compact}
                compact={compact}
              />
            </>
          )}

          {/* Action buttons */}
          <Divider />
          <HStack spacing={2} justify="space-between">
            <HStack spacing={2}>
              <Icon as={FiShield} color="green.500" size="14px" />
              <Text fontSize="xs" color={textColor}>
                Secured by Axelar Network
              </Text>
            </HStack>

            <HStack spacing={2}>
              {onCancel && transaction.status === 'pending' && (
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={onCancel}
                  isDisabled={isExecuting}
                >
                  Cancel
                </Button>
              )}

              {onViewDetails && (
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={onViewDetails}
                  leftIcon={<FiTrendingUp />}
                >
                  Details
                </Button>
              )}

              {onExecute && transaction.status === 'pending' && (
                <Button
                  size="sm"
                  colorScheme={isPrivacy ? 'yellow' : 'blue'}
                  onClick={onExecute}
                  isLoading={isExecuting}
                  loadingText={isPrivacy ? 'Bridging...' : 'Executing...'}
                  leftIcon={isPrivacy ? <FiLock /> : <FiZap />}
                  isDisabled={isPrivacy && !isPrivacyAddressValid}
                >
                  {isPrivacy ? 'Bridge to Privacy' : 'Execute'}
                </Button>
              )}
            </HStack>
          </HStack>

          {/* Axelar branding */}
          <Box
            bg={axelarBoxBg}
            p={2}
            borderRadius="md"
            textAlign="center"
          >
            <Text fontSize="xs" color="blue.600" fontWeight="medium">
              ⚡ Powered by Axelar General Message Passing
            </Text>
          </Box>
        </VStack>
      </CardBody>
    </MotionCard>
  );
});

GMPTransactionCard.displayName = 'GMPTransactionCard';

export default GMPTransactionCard;

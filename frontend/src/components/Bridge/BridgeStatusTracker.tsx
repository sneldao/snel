/**
 * BridgeStatusTracker - Real-time bridge transaction progress display
 * 
 * Follows MODULAR, CLEAN, and PERFORMANT principles:
 * - Independent component (no tight coupling)
 * - Clear responsibility (status visualization only)
 * - Reusable across different bridge types
 */

import React, { memo } from 'react';
import {
  Box,
  VStack,
  HStack,
  Progress,
  Text,
  Badge,
  Spinner,
  Icon,
  Tooltip,
  useColorModeValue,
} from '@chakra-ui/react';
import { CheckCircleIcon, WarningIcon, ExternalLinkIcon } from '@chakra-ui/icons';
import { FaClock, FaLink } from 'react-icons/fa';
import type { BridgeStatusContent } from '../../types/responses';

interface BridgeStatusTrackerProps {
  status: BridgeStatusContent;
  isLoading?: boolean;
  collapsible?: boolean;
}

/**
 * Status badge with appropriate color
 */
const StatusBadge = memo(({ status }: { status: string }) => {
  const colorMap: Record<string, string> = {
    initiated: 'blue',
    source_confirmed: 'purple',
    in_transit: 'cyan',
    destination_confirmed: 'blue',
    completed: 'green',
    failed: 'red',
  };

  const labelMap: Record<string, string> = {
    initiated: 'Initiated',
    source_confirmed: 'Source Confirmed',
    in_transit: 'In Transit',
    destination_confirmed: 'Destination Confirmed',
    completed: 'Complete',
    failed: 'Failed',
  };

  return (
    <Badge colorScheme={colorMap[status] || 'gray'} px={3} py={1} fontSize="sm">
      {labelMap[status] || status}
    </Badge>
  );
});

StatusBadge.displayName = 'StatusBadge';

/**
 * Individual step indicator in the bridge flow
 */
const StepIndicator = memo(
  ({
    step,
    isActive,
    isCompleted,
    isFailed,
  }: {
    step: BridgeStatusContent['steps'][0];
    isActive: boolean;
    isCompleted: boolean;
    isFailed: boolean;
  }) => {
    const bgColor = useColorModeValue('gray.50', 'gray.700');
    const borderColor = isActive ? 'blue.500' : isCompleted ? 'green.500' : isFailed ? 'red.500' : 'gray.200';

    return (
      <Box
        p={3}
        borderLeft="4px solid"
        borderColor={borderColor}
        bg={bgColor}
        borderRadius="md"
        transition="all 0.2s"
        _hover={{ shadow: 'sm' }}
      >
        <HStack spacing={2} mb={1}>
          <Text fontWeight="bold" fontSize="sm">
            Step {step.step_number}: {step.name}
          </Text>
          {isCompleted && <CheckCircleIcon color="green.500" w={4} h={4} />}
          {isFailed && <WarningIcon color="red.500" w={4} h={4} />}
          {isActive && !isCompleted && !isFailed && <Spinner size="sm" color="blue.500" />}
        </HStack>

        <Text fontSize="xs" color="gray.600" mb={2}>
          {step.description}
        </Text>

        {step.tx_hash && (
          <HStack spacing={1}>
            <Icon as={FaLink} w={3} h={3} color="blue.500" />
            <Tooltip label="View on Explorer">
              <Text
                as="a"
                href={`https://axelarscan.io/tx/${step.tx_hash}`}
                target="_blank"
                rel="noopener noreferrer"
                fontSize="xs"
                color="blue.500"
                _hover={{ textDecoration: 'underline' }}
              >
                {step.tx_hash.slice(0, 10)}...
                <ExternalLinkIcon ml={1} mb="1px" w={3} h={3} />
              </Text>
            </Tooltip>
          </HStack>
        )}

        {step.confirmed_at && (
          <HStack spacing={1} mt={1}>
            <Icon as={FaClock} w={3} h={3} color="gray.500" />
            <Text fontSize="xs" color="gray.500">
              {new Date(step.confirmed_at).toLocaleTimeString()}
            </Text>
          </HStack>
        )}
      </Box>
    );
  }
);

StepIndicator.displayName = 'StepIndicator';

/**
 * Main bridge status tracker component
 */
export const BridgeStatusTracker = memo(
  ({ status, isLoading = false, collapsible = true }: BridgeStatusTrackerProps) => {
    const bgColor = useColorModeValue('white', 'gray.800');
    const borderColor = useColorModeValue('gray.200', 'gray.600');

    const isComplete = status.status === 'completed';
    const isFailed = status.status === 'failed';

    return (
      <Box
        borderWidth={1}
        borderColor={borderColor}
        borderRadius="lg"
        p={4}
        bg={bgColor}
        shadow="sm"
      >
        {/* Header */}
        <HStack justify="space-between" mb={4}>
          <VStack align="start" spacing={1}>
            <Text fontWeight="bold" fontSize="lg">
              Bridge Status
            </Text>
            <Text fontSize="xs" color="gray.500">
              {status.bridge_id.slice(0, 8)}...
            </Text>
          </VStack>
          <StatusBadge status={status.status} />
        </HStack>

        {/* Progress bar */}
        <Box mb={4}>
          <HStack justify="space-between" mb={2}>
            <Text fontSize="sm" fontWeight="medium">
              Progress
            </Text>
            <Text fontSize="sm" color="gray.600">
              {status.current_step} of {status.total_steps} steps
            </Text>
          </HStack>
          <Progress
            value={(status.current_step / status.total_steps) * 100}
            size="sm"
            colorScheme={isFailed ? 'red' : isComplete ? 'green' : 'blue'}
            borderRadius="full"
          />
        </Box>

        {/* Steps */}
        <VStack spacing={2} mb={4}>
          {status.steps.map((step) => {
            const isCompleted = step.status === 'completed';
            const isActive = step.status === 'in_progress';
            const stepFailed = step.status === 'failed';

            return (
              <React.Fragment key={`step-${step.step_number}`}>
                <StepIndicator
                  step={step}
                  isActive={isActive}
                  isCompleted={isCompleted}
                  isFailed={stepFailed}
                />
              </React.Fragment>
            );
          })}
        </VStack>

        {/* Error state */}
        {isFailed && status.error && (
          <Box
            p={3}
            bg="red.50"
            borderRadius="md"
            borderLeft="4px solid"
            borderColor="red.500"
          >
            <HStack spacing={2}>
              <WarningIcon color="red.500" />
              <Box>
                <Text fontWeight="bold" fontSize="sm" color="red.700">
                  Bridge Failed
                </Text>
                <Text fontSize="xs" color="red.600" mt={1}>
                  {status.error}
                </Text>
              </Box>
            </HStack>
          </Box>
        )}

        {/* Success state */}
        {isComplete && (
          <Box
            p={3}
            bg="green.50"
            borderRadius="md"
            borderLeft="4px solid"
            borderColor="green.500"
          >
            <HStack spacing={2}>
              <CheckCircleIcon color="green.500" w={5} h={5} />
              <Box>
                <Text fontWeight="bold" fontSize="sm" color="green.700">
                  Bridge Complete
                </Text>
                <Text fontSize="xs" color="green.600" mt={1}>
                  Your funds have been transferred successfully
                </Text>
              </Box>
            </HStack>
          </Box>
        )}

        {/* Loading state */}
        {isLoading && (
          <HStack spacing={2} justify="center" py={2}>
            <Spinner size="sm" />
            <Text fontSize="sm" color="gray.500">
              Updating status...
            </Text>
          </HStack>
        )}
      </Box>
    );
  }
);

BridgeStatusTracker.displayName = 'BridgeStatusTracker';

import * as React from "react";
import {
  Box,
  VStack,
  HStack,
  Text,
  Button,
  Progress,
  Badge,
  Icon,
  Spinner,
  Alert,
  AlertIcon,
  AlertTitle,
  AlertDescription,
  Link,
  useColorModeValue,
  Divider,
} from "@chakra-ui/react";
import { CheckCircleIcon, WarningIcon, ExternalLinkIcon } from "@chakra-ui/icons";
import { BLOCK_EXPLORERS } from "../constants/chains";

export interface TransactionStep {
  step: number;
  stepType: "approval" | "swap" | "bridge" | "other";
  status: "pending" | "executing" | "completed" | "failed";
  hash?: string;
  error?: string;
  description?: string;
}

interface TransactionProgressProps {
  steps: TransactionStep[];
  currentStep: number;
  totalSteps: number;
  chainId: number;
  isComplete: boolean;
  error?: string;
  onRetry?: () => void;
  onDone?: () => void;
}

const getStepDescription = (stepType: string, step: number): string => {
  switch (stepType) {
    case "approval":
      return "Approve token spending";
    case "swap":
      return "Execute token swap";
    case "bridge":
      return "Bridge tokens across chains";
    default:
      return `Step ${step}`;
  }
};

const getStepIcon = (status: string) => {
  switch (status) {
    case "completed":
      return <CheckCircleIcon color="green.500" />;
    case "failed":
      return <WarningIcon color="red.500" />;
    case "executing":
      return <Spinner size="sm" color="blue.500" />;
    default:
      return <Box w="16px" h="16px" borderRadius="50%" bg="gray.300" />;
  }
};

const getStatusColor = (status: string): string => {
  switch (status) {
    case "completed":
      return "green";
    case "failed":
      return "red";
    case "executing":
      return "blue";
    default:
      return "gray";
  }
};

export const TransactionProgress: React.FC<TransactionProgressProps> = ({
  steps,
  currentStep,
  totalSteps,
  chainId,
  isComplete,
  error,
  onRetry,
  onDone,
}) => {
  const bgColor = useColorModeValue("white", "gray.800");
  const borderColor = useColorModeValue("gray.200", "gray.600");

  const getBlockExplorerLink = (hash: string): string => {
    return `${BLOCK_EXPLORERS[chainId as keyof typeof BLOCK_EXPLORERS] ||
      BLOCK_EXPLORERS[8453]
      }${hash}`;
  };

  const progressPercentage = (currentStep / totalSteps) * 100;

  return (
    <Box
      bg={bgColor}
      borderWidth="1px"
      borderColor={borderColor}
      borderRadius="lg"
      p={4}
      maxW="500px"
      mx="auto"
    >
      <VStack spacing={4} align="stretch">
        {/* Header */}
        <VStack spacing={2} align="center">
          <Text fontSize="lg" fontWeight="bold">
            Transaction Progress
          </Text>
          <HStack spacing={2}>
            <Badge colorScheme={isComplete ? "green" : error ? "red" : "blue"}>
              {isComplete ? "Complete" : error ? "Failed" : "In Progress"}
            </Badge>
            <Text fontSize="sm" color="gray.600">
              {currentStep} of {totalSteps} steps
            </Text>
          </HStack>
        </VStack>

        {/* Progress Bar */}
        <Box>
          <Progress
            value={progressPercentage}
            colorScheme={error ? "red" : isComplete ? "green" : "blue"}
            size="lg"
            borderRadius="md"
          />
          <Text fontSize="xs" color="gray.500" mt={1} textAlign="center">
            {Math.round(progressPercentage)}% complete
          </Text>
        </Box>

        {/* Steps List */}
        <VStack spacing={3} align="stretch">
          {steps.map((step, index) => (
            <Box key={step.step}>
              <HStack spacing={3} align="center">
                {getStepIcon(step.status)}
                <VStack align="start" spacing={1} flex={1}>
                  <HStack justify="space-between" w="full">
                    <Text fontWeight="semibold" fontSize="sm">
                      {step.description || getStepDescription(step.stepType, step.step)}
                    </Text>
                    <Badge
                      size="sm"
                      colorScheme={getStatusColor(step.status)}
                      variant="subtle"
                    >
                      {step.status}
                    </Badge>
                  </HStack>

                  {step.hash && (
                    <Link
                      href={getBlockExplorerLink(step.hash)}
                      isExternal
                      fontSize="xs"
                      color="blue.500"
                      display="flex"
                      alignItems="center"
                      gap={1}
                    >
                      View transaction <Icon as={ExternalLinkIcon} />
                    </Link>
                  )}

                  {step.error && (
                    <Text fontSize="xs" color="red.500">
                      {step.error}
                    </Text>
                  )}
                </VStack>
              </HStack>

              {index < steps.length - 1 && (
                <Divider mt={2} opacity={0.3} />
              )}
            </Box>
          ))}
        </VStack>

        {/* Success Message */}
        {isComplete && !error && (
          <Alert
            status="success"
            variant="subtle"
            flexDirection="column"
            alignItems="center"
            justifyContent="center"
            textAlign="center"
            borderRadius="md"
            py={6}
          >
            <AlertIcon boxSize="40px" mr={0} />
            <AlertTitle mt={4} mb={1} fontSize="lg">
              Transaction Successful!
            </AlertTitle>
            <AlertDescription maxWidth="sm">
              All steps have been executed successfully. Your assets have been updated.
            </AlertDescription>
            {onDone && (
              <Button
                mt={4}
                colorScheme="green"
                size="sm"
                onClick={onDone}
                width="full"
              >
                Close Progress
              </Button>
            )}
          </Alert>
        )}

        {/* Action Buttons for Failure */}
        {error && (
          <HStack spacing={3} w="full">
            {onRetry && (
              <Button
                colorScheme="red"
                flex={1}
                size="sm"
                onClick={onRetry}
                leftIcon={<WarningIcon />}
              >
                Retry Transaction
              </Button>
            )}
            {onDone && (
              <Button
                variant="outline"
                flex={1}
                size="sm"
                onClick={onDone}
              >
                Close
              </Button>
            )}
          </HStack>
        )}

        {/* Helpful Information */}
        <Box bg="gray.50" p={3} borderRadius="md">
          <Text fontSize="xs" color="gray.600" textAlign="center">
            {currentStep === 1 && steps[0]?.stepType === "approval" && (
              "Step 1: Approving token spending allows the protocol to access your tokens for the swap."
            )}
            {currentStep === 2 && steps[1]?.stepType === "swap" && (
              "Step 2: Executing the actual token swap transaction."
            )}
            {isComplete && (
              "Your transaction has been completed successfully. You can view the details on the block explorer."
            )}
            {error && onRetry && (
              "Something went wrong. You can try again or contact support if the issue persists."
            )}
          </Text>
        </Box>
      </VStack>
    </Box>
  );
};

import React, { useState, useEffect, useCallback, useMemo } from "react";
import {
  Box,
  Flex,
  Text,
  VStack,
  HStack,
  Heading,
  Badge,
  Divider,
  Button,
  Icon,
  Progress,
  Tooltip,
  useColorModeValue,
  Alert,
  AlertIcon,
  AlertTitle,
  AlertDescription,
  Collapse,
  Link,
  Spinner,
  SimpleGrid,
  useDisclosure,
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalFooter,
  ModalCloseButton,
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
} from "@chakra-ui/react";
import { motion, AnimatePresence } from "framer-motion";
import {
  FaCheckCircle,
  FaExclamationTriangle,
  FaArrowRight,
  FaInfoCircle,
  FaSyncAlt,
  FaLink,
  FaExternalLinkAlt,
  FaChartLine,
  FaGasPump,
  FaClock,
  FaExchangeAlt,
  FaNetworkWired,
  FaCoins,
  FaShieldAlt,
} from "react-icons/fa";
import {
  axelarServiceV2,
  TransactionDetailsV2,
  AxelarServiceError,
  FeeBreakdown,
  TransferQuoteV2,
} from "../../services/enhanced/axelarServiceV2";
import { retry } from "../../utils/retry";
import { ChainUtils } from "../../utils/chainUtils";

// ======== TypeScript Interfaces ========

interface CrosschainTransactionTrackerProps {
  txHash: string;
  sourceChain: string | number;
  destinationChain: string | number;
  asset: string;
  amount: string;
  sourceAddress: string;
  destinationAddress: string;
  quote?: TransferQuoteV2;
  onComplete?: (success: boolean) => void;
  onRecoveryNeeded?: (txHash: string) => void;
  showDetailedView?: boolean;
}

interface TransactionStep {
  id: string;
  title: string;
  description: string;
  status: "pending" | "active" | "completed" | "failed";
  timestamp?: number;
  estimatedTime?: string;
  txHash?: string;
  chainId?: number | string;
}

interface RouteNode {
  chainId: number | string;
  name: string;
  icon?: string;
  status: "pending" | "active" | "completed" | "failed";
}

interface RecoveryOption {
  id: string;
  title: string;
  description: string;
  action: () => Promise<void>;
  buttonText: string;
  severity: "low" | "medium" | "high";
}

// ======== Animation Variants ========

const fadeIn = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: { duration: 0.5 } },
};

const slideIn = {
  hidden: { x: -20, opacity: 0 },
  visible: { x: 0, opacity: 1, transition: { duration: 0.4 } },
};

const pulse = {
  initial: { scale: 1 },
  animate: {
    scale: [1, 1.05, 1],
    transition: { duration: 1.5, repeat: Infinity },
  },
};

const progressVariants = {
  initial: { width: "0%" },
  animate: (progress: number) => ({
    width: `${progress}%`,
    transition: { duration: 0.8, ease: "easeInOut" },
  }),
};

// ======== Helper Components ========

const MotionBox = motion(Box);
const MotionFlex = motion(Flex);
const MotionText = motion(Text);
const MotionProgress = motion(Progress);

const StatusIcon: React.FC<{ status: string; size?: number }> = ({
  status,
  size = 5,
}) => {
  switch (status) {
    case "completed":
      return <Icon as={FaCheckCircle} color="green.500" w={size} h={size} />;
    case "active":
      return (
        <MotionBox
          animate={{ rotate: 360 }}
          transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
        >
          <Icon as={FaSyncAlt} color="blue.500" w={size} h={size} />
        </MotionBox>
      );
    case "failed":
      return (
        <Icon as={FaExclamationTriangle} color="red.500" w={size} h={size} />
      );
    default:
      return <Icon as={FaClock} color="gray.400" w={size} h={size} />;
  }
};

const StepProgressBar: React.FC<{
  steps: TransactionStep[];
  currentStep: number;
}> = ({ steps, currentStep }) => {
  const totalSteps = steps.length;
  const completedSteps = steps.filter(
    (step) => step.status === "completed"
  ).length;
  const progress = Math.floor((completedSteps / totalSteps) * 100);
  const activeStep = steps.findIndex((step) => step.status === "active");
  const hasFailedStep = steps.some((step) => step.status === "failed");

  const bgColor = useColorModeValue("gray.100", "gray.700");
  const progressColor = hasFailedStep ? "red.400" : "blue.400";

  return (
    <Box w="100%" mb={4}>
      <Flex justify="space-between" mb={2}>
        <Text fontSize="sm" fontWeight="medium">
          Progress
        </Text>
        <Text fontSize="sm" fontWeight="bold">
          {progress}%
        </Text>
      </Flex>
      <Box
        position="relative"
        h="8px"
        w="100%"
        bg={bgColor}
        borderRadius="full"
        overflow="hidden"
      >
        <MotionProgress
          value={progress}
          size="sm"
          colorScheme={hasFailedStep ? "red" : "blue"}
          borderRadius="full"
          variants={progressVariants}
          initial="initial"
          animate="animate"
          custom={progress}
        />
        {activeStep >= 0 && (
          <MotionBox
            position="absolute"
            top="0"
            left={`${(activeStep / totalSteps) * 100}%`}
            transform="translateX(-50%)"
            animate={{
              opacity: [0.5, 1, 0.5],
            }}
            transition={{
              duration: 1.5,
              repeat: Infinity,
              ease: "easeInOut",
            }}
          >
            <Box
              w="12px"
              h="12px"
              bg="blue.500"
              borderRadius="full"
              mt="-2px"
              boxShadow="0 0 0 4px rgba(66, 153, 225, 0.3)"
            />
          </MotionBox>
        )}
      </Box>
    </Box>
  );
};

const RouteVisualization: React.FC<{
  route: RouteNode[];
  activeNodeIndex: number;
}> = ({ route, activeNodeIndex }) => {
  const bgColor = useColorModeValue("gray.50", "gray.800");
  const borderColor = useColorModeValue("gray.200", "gray.600");

  return (
    <Box
      p={4}
      borderRadius="lg"
      bg={bgColor}
      borderWidth="1px"
      borderColor={borderColor}
      overflow="hidden"
      mb={4}
    >
      <Text fontSize="sm" fontWeight="medium" mb={3}>
        Transaction Route
      </Text>
      <Flex align="center" justify="space-between" position="relative">
        {/* Connection lines */}
        <Box
          position="absolute"
          height="2px"
          bg="gray.300"
          left="10%"
          right="10%"
          top="50%"
          zIndex={1}
        />

        {/* Route nodes */}
        {route.map((node, index) => {
          const isActive = index === activeNodeIndex;
          const isCompleted = index < activeNodeIndex;

          return (
            <React.Fragment key={`node-${index}`}>
              <MotionBox
                position="relative"
                zIndex={2}
                animate={isActive ? pulse.animate : {}}
                initial={pulse.initial}
                whileHover={{ scale: 1.1 }}
              >
                <VStack spacing={1}>
                  <Box
                    w="40px"
                    h="40px"
                    borderRadius="full"
                    bg={
                      isCompleted
                        ? "green.500"
                        : isActive
                        ? "blue.500"
                        : "gray.300"
                    }
                    display="flex"
                    alignItems="center"
                    justifyContent="center"
                    boxShadow={
                      isActive ? "0 0 0 4px rgba(66, 153, 225, 0.3)" : "none"
                    }
                  >
                    {isCompleted ? (
                      <Icon as={FaCheckCircle} color="white" />
                    ) : isActive ? (
                      <Icon as={FaNetworkWired} color="white" />
                    ) : (
                      <Icon as={FaNetworkWired} color="gray.600" />
                    )}
                  </Box>
                  <Text fontSize="xs" fontWeight="medium" textAlign="center">
                    {typeof node.chainId === "number"
                      ? ChainUtils.getChainName(node.chainId)
                      : node.name}
                  </Text>
                </VStack>
              </MotionBox>

              {/* Arrow between nodes */}
              {index < route.length - 1 && (
                <MotionBox
                  animate={
                    index < activeNodeIndex
                      ? { x: [0, 10, 0], opacity: 1 }
                      : { opacity: 0.5 }
                  }
                  transition={
                    index < activeNodeIndex ? { duration: 1.5, repeat: 0 } : {}
                  }
                >
                  <Icon
                    as={FaArrowRight}
                    color={index < activeNodeIndex ? "green.500" : "gray.400"}
                  />
                </MotionBox>
              )}
            </React.Fragment>
          );
        })}
      </Flex>
    </Box>
  );
};

const DetailedSteps: React.FC<{ steps: TransactionStep[] }> = ({ steps }) => {
  const bgColor = useColorModeValue("white", "gray.800");
  const borderColor = useColorModeValue("gray.200", "gray.700");

  return (
    <VStack spacing={3} align="stretch" w="100%">
      <Text fontSize="sm" fontWeight="medium" mb={1}>
        Transaction Steps
      </Text>
      <AnimatePresence>
        {steps.map((step, index) => (
          <MotionBox
            key={step.id}
            variants={slideIn}
            initial="hidden"
            animate="visible"
            exit={{ opacity: 0, height: 0 }}
            custom={index}
            transition={{ delay: index * 0.1 }}
          >
            <Flex
              p={3}
              borderWidth="1px"
              borderRadius="md"
              bg={bgColor}
              borderColor={borderColor}
              mb={2}
              align="center"
              position="relative"
              overflow="hidden"
            >
              {/* Status indicator bar */}
              <Box
                position="absolute"
                left="0"
                top="0"
                bottom="0"
                w="4px"
                bg={
                  step.status === "completed"
                    ? "green.500"
                    : step.status === "active"
                    ? "blue.500"
                    : step.status === "failed"
                    ? "red.500"
                    : "gray.300"
                }
              />

              <StatusIcon status={step.status} />

              <VStack align="start" ml={3} spacing={0} flex={1}>
                <Text fontSize="sm" fontWeight="semibold">
                  {step.title}
                </Text>
                <Text fontSize="xs" color="gray.500">
                  {step.description}
                </Text>

                {step.estimatedTime && step.status !== "completed" && (
                  <HStack mt={1} spacing={1}>
                    <Icon as={FaClock} color="gray.400" fontSize="xs" />
                    <Text fontSize="xs" color="gray.500">
                      Est. {step.estimatedTime}
                    </Text>
                  </HStack>
                )}

                {step.timestamp && step.status === "completed" && (
                  <Text fontSize="xs" color="gray.500" mt={1}>
                    Completed at {new Date(step.timestamp).toLocaleTimeString()}
                  </Text>
                )}
              </VStack>

              {step.txHash && (
                <Tooltip label="View in explorer">
                  <Link
                    href={ChainUtils.getExplorerUrl(
                      typeof step.chainId === "number" ? step.chainId : 1,
                      step.txHash
                    )}
                    isExternal
                  >
                    <Icon
                      as={FaExternalLinkAlt}
                      color="gray.400"
                      _hover={{ color: "blue.500" }}
                    />
                  </Link>
                </Tooltip>
              )}
            </Flex>
          </MotionBox>
        ))}
      </AnimatePresence>
    </VStack>
  );
};

const FeeBreakdownDisplay: React.FC<{
  feeBreakdown: FeeBreakdown;
  asset: string;
  showOptimizationTips?: boolean;
}> = ({ feeBreakdown, asset, showOptimizationTips = true }) => {
  const { isOpen, onToggle } = useDisclosure();
  const bgColor = useColorModeValue("gray.50", "gray.800");
  const borderColor = useColorModeValue("gray.200", "gray.700");
  // Pre-computed color for Collapse background to avoid conditional hook call
  const collapseBg = useColorModeValue("blue.50", "blue.900");

  const totalPercentage =
    parseFloat(feeBreakdown.totalFee) /
    (parseFloat(feeBreakdown.totalFee) + Math.random() * 0.01); // Simulating total transaction value

  const optimizationTips = [
    "Consider transferring during off-peak hours for lower network fees",
    "Larger transfers are more cost-efficient relative to the fee percentage",
    "Some destination chains have lower gas costs than others",
  ];

  return (
    <Box
      p={4}
      borderRadius="lg"
      bg={bgColor}
      borderWidth="1px"
      borderColor={borderColor}
      mb={4}
    >
      <Flex justify="space-between" align="center" mb={3}>
        <Text fontSize="sm" fontWeight="medium">
          Fee Breakdown
        </Text>
        <Badge colorScheme={totalPercentage > 0.05 ? "orange" : "green"}>
          {(totalPercentage * 100).toFixed(2)}% of total
        </Badge>
      </Flex>

      <SimpleGrid columns={1} spacing={2} mb={3}>
        <HStack justify="space-between">
          <HStack>
            <Icon as={FaGasPump} color="gray.500" />
            <Text fontSize="sm">Network Fee</Text>
          </HStack>
          <Text fontSize="sm" fontWeight="medium">
            {feeBreakdown.networkFee} {asset}
          </Text>
        </HStack>

        <HStack justify="space-between">
          <HStack>
            <Icon as={FaExchangeAlt} color="gray.500" />
            <Text fontSize="sm">Bridge Fee</Text>
          </HStack>
          <Text fontSize="sm" fontWeight="medium">
            {feeBreakdown.bridgeFee} {asset}
          </Text>
        </HStack>

        {feeBreakdown.relayerFee && (
          <HStack justify="space-between">
            <HStack>
              <Icon as={FaNetworkWired} color="gray.500" />
              <Text fontSize="sm">Relayer Fee</Text>
            </HStack>
            <Text fontSize="sm" fontWeight="medium">
              {feeBreakdown.relayerFee} {asset}
            </Text>
          </HStack>
        )}

        <Divider my={1} />

        <HStack justify="space-between">
          <HStack>
            <Icon as={FaCoins} color="blue.500" />
            <Text fontSize="sm" fontWeight="bold">
              Total Fee
            </Text>
          </HStack>
          <Text fontSize="sm" fontWeight="bold">
            {feeBreakdown.totalFee} {asset}
            {feeBreakdown.estimatedUsd && (
              <Text as="span" fontSize="xs" color="gray.500" ml={1}>
                (≈${feeBreakdown.estimatedUsd})
              </Text>
            )}
          </Text>
        </HStack>
      </SimpleGrid>

      {showOptimizationTips && (
        <>
          <Button
            size="xs"
            variant="ghost"
            rightIcon={<Icon as={isOpen ? FaArrowRight : FaInfoCircle} />}
            onClick={onToggle}
            colorScheme="blue"
            mb={isOpen ? 3 : 0}
          >
            {isOpen ? "Hide optimization tips" : "Show fee optimization tips"}
          </Button>

          <Collapse in={isOpen} animateOpacity>
            <Box
              p={3}
              bg={collapseBg}
              borderRadius="md"
              borderLeft="4px solid"
              borderColor="blue.400"
            >
              <Text fontSize="xs" fontWeight="medium" mb={2}>
                Optimization Tips
              </Text>
              <VStack align="start" spacing={2}>
                {optimizationTips.map((tip, index) => (
                  <HStack key={index} align="start" spacing={2}>
                    <Icon
                      as={FaInfoCircle}
                      color="blue.500"
                      mt="3px"
                      fontSize="xs"
                    />
                    <Text fontSize="xs">{tip}</Text>
                  </HStack>
                ))}
              </VStack>
            </Box>
          </Collapse>
        </>
      )}
    </Box>
  );
};

const RecoveryOptionsModal: React.FC<{
  isOpen: boolean;
  onClose: () => void;
  options: RecoveryOption[];
  txHash: string;
  isLoading: boolean;
}> = ({ isOpen, onClose, options, txHash, isLoading }) => {
  const [selectedOption, setSelectedOption] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState(false);

  // Theme colors pre-computed to satisfy hook rules
  const optionBg = useColorModeValue("white", "gray.800");
  const optionHoverBg = useColorModeValue("gray.50", "gray.700");

  const handleAction = async (option: RecoveryOption) => {
    setSelectedOption(option.id);
    setActionLoading(true);

    try {
      await option.action();
      // Success handling will be done by the parent component through onComplete callback
    } catch (error) {
      console.error("Recovery action failed:", error);
    } finally {
      setActionLoading(false);
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} isCentered size="lg">
      <ModalOverlay bg="blackAlpha.300" backdropFilter="blur(5px)" />
      <ModalContent>
        <ModalHeader>Transaction Recovery Options</ModalHeader>
        <ModalCloseButton />
        <ModalBody>
          {isLoading ? (
            <VStack py={8}>
              <Spinner size="lg" color="blue.500" />
              <Text mt={4}>Analyzing recovery options...</Text>
            </VStack>
          ) : (
            <>
              <Alert status="warning" mb={4} borderRadius="md">
                <AlertIcon />
                <Box>
                  <AlertTitle>Transaction needs recovery</AlertTitle>
                  <AlertDescription fontSize="sm">
                    Transaction {txHash.substring(0, 6)}...
                    {txHash.substring(txHash.length - 4)} is stuck or failed.
                    Select a recovery option below.
                  </AlertDescription>
                </Box>
              </Alert>

              <VStack spacing={3} align="stretch">
                {options.map((option) => (
                  <Box
                    key={option.id}
                    p={4}
                    borderWidth="1px"
                    borderRadius="md"
                    borderLeftWidth="4px"
                    borderLeftColor={
                      option.severity === "high"
                        ? "red.500"
                        : option.severity === "medium"
                        ? "orange.500"
                        : "yellow.500"
                    }
                    bg={optionBg}
                    cursor="pointer"
                    _hover={{ bg: optionHoverBg }}
                    onClick={() => handleAction(option)}
                  >
                    <Flex justify="space-between" align="center">
                      <VStack align="start" spacing={1}>
                        <Text fontWeight="medium">{option.title}</Text>
                        <Text fontSize="sm" color="gray.500">
                          {option.description}
                        </Text>
                      </VStack>
                      <Button
                        size="sm"
                        colorScheme={
                          option.severity === "high"
                            ? "red"
                            : option.severity === "medium"
                            ? "orange"
                            : "yellow"
                        }
                        isLoading={
                          selectedOption === option.id && actionLoading
                        }
                      >
                        {option.buttonText}
                      </Button>
                    </Flex>
                  </Box>
                ))}
              </VStack>
            </>
          )}
        </ModalBody>
        <ModalFooter>
          <Button variant="ghost" onClick={onClose}>
            Close
          </Button>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
};

const AxelarBranding: React.FC = () => {
  return (
    <MotionBox
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.5, duration: 0.5 }}
    >
      <HStack
        spacing={2}
        p={3}
        bg={useColorModeValue("blue.50", "blue.900")}
        borderRadius="md"
        align="center"
      >
        <Icon as={FaShieldAlt} color="blue.500" boxSize={5} />
        <VStack align="start" spacing={0}>
          <Text fontSize="sm" fontWeight="medium">
            Powered by Axelar Network
          </Text>
          <Text fontSize="xs" color={useColorModeValue("gray.600", "gray.300")}>
            Secure cross-chain infrastructure with proof-of-stake security
          </Text>
        </VStack>
      </HStack>
    </MotionBox>
  );
};

// ======== Main Component ========

export const CrosschainTransactionTracker: React.FC<
  CrosschainTransactionTrackerProps
> = ({
  txHash,
  sourceChain,
  destinationChain,
  asset,
  amount,
  sourceAddress,
  destinationAddress,
  quote,
  onComplete,
  onRecoveryNeeded,
  showDetailedView = true,
}) => {
  // Convert chain IDs to names if needed
  const sourceChainName = useMemo(() => {
    return typeof sourceChain === "number"
      ? ChainUtils.getChainName(sourceChain)
      : sourceChain;
  }, [sourceChain]);

  const destinationChainName = useMemo(() => {
    return typeof destinationChain === "number"
      ? ChainUtils.getChainName(destinationChain)
      : destinationChain;
  }, [destinationChain]);

  // State
  const [txDetails, setTxDetails] = useState<TransactionDetailsV2 | null>(null);
  const [steps, setSteps] = useState<TransactionStep[]>([]);
  const [currentStepIndex, setCurrentStepIndex] = useState(0);
  const [routeNodes, setRouteNodes] = useState<RouteNode[]>([]);
  const [activeRouteNodeIndex, setActiveRouteNodeIndex] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [recoveryOptions, setRecoveryOptions] = useState<RecoveryOption[]>([]);
  const [isPolling, setIsPolling] = useState(true);
  const [loadingRecovery, setLoadingRecovery] = useState(false);

  // Recovery modal state
  const {
    isOpen: isRecoveryModalOpen,
    onOpen: openRecoveryModal,
    onClose: closeRecoveryModal,
  } = useDisclosure();

  // Theme colors
  const bgColor = useColorModeValue("white", "gray.800");
  const borderColor = useColorModeValue("gray.200", "gray.700");

  // Initialize steps
  useEffect(() => {
    const initialSteps: TransactionStep[] = [
      {
        id: "initiate",
        title: "Transaction Initiated",
        description: `Sending ${amount} ${asset} from ${sourceChainName}`,
        status: "completed",
        timestamp: Date.now(),
        txHash,
      },
      {
        id: "source_confirm",
        title: "Source Chain Confirmation",
        description: `Confirming transaction on ${sourceChainName}`,
        status: "active",
        estimatedTime: "1-2 minutes",
        chainId: sourceChain,
      },
      {
        id: "axelar_processing",
        title: "Axelar Network Processing",
        description: "Validating and preparing cross-chain message",
        status: "pending",
        estimatedTime: "3-5 minutes",
      },
      {
        id: "destination_prepare",
        title: "Destination Chain Preparation",
        description: `Preparing to receive on ${destinationChainName}`,
        status: "pending",
        estimatedTime: "2-3 minutes",
        chainId: destinationChain,
      },
      {
        id: "destination_confirm",
        title: "Destination Chain Confirmation",
        description: `Finalizing on ${destinationChainName}`,
        status: "pending",
        estimatedTime: "1-2 minutes",
        chainId: destinationChain,
      },
    ];

    setSteps(initialSteps);
    setCurrentStepIndex(1); // Source chain confirmation is active

    // Initialize route nodes
    setRouteNodes([
      {
        chainId: sourceChain,
        name: sourceChainName,
        status: "completed",
      },
      {
        chainId: "axelar",
        name: "Axelar Network",
        status: "pending",
      },
      {
        chainId: destinationChain,
        name: destinationChainName,
        status: "pending",
      },
    ]);
    setActiveRouteNodeIndex(0);
  }, [
    txHash,
    sourceChain,
    destinationChain,
    sourceChainName,
    destinationChainName,
    asset,
    amount,
  ]);

  // Poll for transaction status
  useEffect(() => {
    if (!isPolling) return;

    let intervalId: NodeJS.Timeout;

    const pollStatus = async () => {
      try {
        // Get transaction status from Axelar
        const status = await axelarServiceV2.getTransactionStatus(
          txHash,
          typeof sourceChain === "number"
            ? ChainUtils.getAxelarChainName(sourceChain) || undefined
            : sourceChain || undefined,
          typeof destinationChain === "number"
            ? ChainUtils.getAxelarChainName(destinationChain) || undefined
            : destinationChain || undefined
        );

        // Get transaction details
        const details = axelarServiceV2.getTransaction(txHash) || {
          txHash,
          sourceChain: sourceChainName,
          destinationChain: destinationChainName,
          sourceAddress,
          destinationAddress,
          asset,
          amount,
          status: status.status,
          timestamp: Date.now(),
        };

        setTxDetails(details);

        // Update steps based on status
        updateStepsFromStatus(status.status, status);
      } catch (error) {
        console.error("Error polling transaction status:", error);
        if (error instanceof AxelarServiceError) {
          setError(error.message);
        } else {
          setError("Failed to get transaction status");
        }
      }
    };

    // Initial poll
    pollStatus();

    // Set up polling interval - more frequent initially, then slower
    intervalId = setInterval(pollStatus, 15000);

    return () => {
      clearInterval(intervalId);
    };
  }, [
    txHash,
    sourceChain,
    destinationChain,
    isPolling,
    sourceChainName,
    destinationChainName,
    sourceAddress,
    destinationAddress,
    asset,
    amount,
  ]);

  // Update steps based on transaction status
  const updateStepsFromStatus = useCallback(
    (status: string, statusDetails: any) => {
      // Clone current steps
      const updatedSteps = [...steps];
      let updatedRouteNodes = [...routeNodes];
      let newCurrentStepIndex = currentStepIndex;
      let newActiveRouteNodeIndex = activeRouteNodeIndex;

      switch (status) {
        case "pending":
          // Transaction is still being confirmed on source chain
          break;

        case "source_confirmed":
          // Transaction confirmed on source chain, now being processed by Axelar
          if (currentStepIndex <= 1) {
            updatedSteps[1].status = "completed";
            updatedSteps[1].timestamp = Date.now();
            updatedSteps[2].status = "active";
            newCurrentStepIndex = 2;

            updatedRouteNodes[0].status = "completed";
            updatedRouteNodes[1].status = "active";
            newActiveRouteNodeIndex = 1;
          }
          break;

        case "axelar_confirmed":
          // Axelar has processed and is preparing destination chain
          if (currentStepIndex <= 2) {
            updatedSteps[2].status = "completed";
            updatedSteps[2].timestamp = Date.now();
            updatedSteps[3].status = "active";
            newCurrentStepIndex = 3;

            updatedRouteNodes[1].status = "completed";
            newActiveRouteNodeIndex = 1;
          }
          break;

        case "destination_executing":
          // Transaction is being executed on destination chain
          if (currentStepIndex <= 3) {
            updatedSteps[3].status = "completed";
            updatedSteps[3].timestamp = Date.now();
            updatedSteps[4].status = "active";
            newCurrentStepIndex = 4;

            updatedRouteNodes[2].status = "active";
            newActiveRouteNodeIndex = 2;
          }
          break;

        case "executed":
        case "completed":
          // Transaction completed successfully
          updatedSteps.forEach((step) => {
            if (step.status !== "completed") {
              step.status = "completed";
              step.timestamp = Date.now();
            }
          });
          newCurrentStepIndex = updatedSteps.length - 1;

          updatedRouteNodes.forEach((node) => {
            node.status = "completed";
          });
          newActiveRouteNodeIndex = updatedRouteNodes.length - 1;

          // Stop polling
          setIsPolling(false);

          // Call onComplete callback
          if (onComplete) {
            onComplete(true);
          }
          break;

        case "error":
        case "failed":
          // Transaction failed
          const failedStepIndex = Math.max(1, currentStepIndex);
          updatedSteps[failedStepIndex].status = "failed";

          // Mark route node as failed
          if (failedStepIndex <= 1) {
            updatedRouteNodes[0].status = "failed";
          } else if (failedStepIndex <= 3) {
            updatedRouteNodes[1].status = "failed";
          } else {
            updatedRouteNodes[2].status = "failed";
          }

          // Stop polling
          setIsPolling(false);

          // Set error message
          setError(statusDetails.message || "Transaction failed");

          // Generate recovery options
          generateRecoveryOptions();

          // Call onRecoveryNeeded callback
          if (onRecoveryNeeded) {
            onRecoveryNeeded(txHash);
          }
          break;

        default:
          // Unknown status
          break;
      }

      setSteps(updatedSteps);
      setRouteNodes(updatedRouteNodes);
      setCurrentStepIndex(newCurrentStepIndex);
      setActiveRouteNodeIndex(newActiveRouteNodeIndex);
    },
    [
      steps,
      currentStepIndex,
      routeNodes,
      activeRouteNodeIndex,
      onComplete,
      onRecoveryNeeded,
      txHash,
    ]
  );

  // Generate recovery options
  const generateRecoveryOptions = useCallback(async () => {
    setLoadingRecovery(true);

    try {
      // In a real implementation, these would come from the Axelar recovery API
      // For now, we'll simulate some options
      await new Promise((resolve) => setTimeout(resolve, 1500));

      const options: RecoveryOption[] = [
        {
          id: "retry",
          title: "Retry Transaction",
          description:
            "Attempt to retry the transaction with the same parameters",
          action: async () => {
            // This would call the Axelar recovery API
            await new Promise((resolve) => setTimeout(resolve, 2000));

            // Simulate success
            // Reset steps and start polling again
            const updatedSteps = steps.map((step) => ({
              ...step,
              status: (step.id === "initiate"
                ? "completed"
                : step.id === "source_confirm"
                ? "active"
                : "pending") as "pending" | "active" | "completed" | "failed",
              timestamp: step.id === "initiate" ? Date.now() : undefined,
            }));

            setSteps(updatedSteps);
            setCurrentStepIndex(1);

            const updatedRouteNodes = routeNodes.map((node, index) => ({
              ...node,
              status: (index === 0 ? "completed" : "pending") as
                | "pending"
                | "active"
                | "completed"
                | "failed",
            }));

            setRouteNodes(updatedRouteNodes);
            setActiveRouteNodeIndex(0);

            setError(null);
            setIsPolling(true);
            closeRecoveryModal();
          },
          buttonText: "Retry",
          severity: "medium",
        },
        {
          id: "accelerate",
          title: "Accelerate with Higher Fee",
          description: "Pay an additional fee to prioritize this transaction",
          action: async () => {
            // This would call the Axelar acceleration API
            await new Promise((resolve) => setTimeout(resolve, 2000));

            // Simulate success
            // Reset steps and start polling again with "accelerated" status
            const updatedSteps = steps.map((step) => ({
              ...step,
              status: (step.id === "initiate"
                ? "completed"
                : step.id === "source_confirm"
                ? "active"
                : "pending") as "pending" | "active" | "completed" | "failed",
              timestamp: step.id === "initiate" ? Date.now() : undefined,
              description:
                step.id === "axelar_processing"
                  ? "Validating and preparing cross-chain message (Accelerated)"
                  : step.description,
            }));

            setSteps(updatedSteps);
            setCurrentStepIndex(1);

            const updatedRouteNodes = routeNodes.map((node, index) => ({
              ...node,
              status: (index === 0 ? "completed" : "pending") as
                | "pending"
                | "active"
                | "completed"
                | "failed",
            }));

            setRouteNodes(updatedRouteNodes);
            setActiveRouteNodeIndex(0);

            setError(null);
            setIsPolling(true);
            closeRecoveryModal();
          },
          buttonText: "Accelerate",
          severity: "low",
        },
        {
          id: "refund",
          title: "Request Refund",
          description: "Attempt to recover your funds back to the source chain",
          action: async () => {
            // This would call the Axelar refund API
            await new Promise((resolve) => setTimeout(resolve, 3000));

            // Simulate success
            // Update steps to show refund
            const updatedSteps = [
              ...steps.slice(0, 2),
              {
                id: "refund",
                title: "Refund Initiated",
                description: `Returning ${amount} ${asset} to ${sourceChainName}`,
                status: "active" as
                  | "pending"
                  | "active"
                  | "completed"
                  | "failed",
                estimatedTime: "5-10 minutes",
                chainId: sourceChain,
              },
            ];

            setSteps(updatedSteps);
            setCurrentStepIndex(2);

            const updatedRouteNodes = [
              {
                chainId: sourceChain,
                name: sourceChainName,
                status: "completed" as
                  | "pending"
                  | "active"
                  | "completed"
                  | "failed",
              },
              {
                chainId: "axelar",
                name: "Axelar Network (Refund)",
                status: "active" as
                  | "pending"
                  | "active"
                  | "completed"
                  | "failed",
              },
              {
                chainId: sourceChain,
                name: `${sourceChainName} (Return)`,
                status: "pending" as
                  | "pending"
                  | "active"
                  | "completed"
                  | "failed",
              },
            ];

            setRouteNodes(updatedRouteNodes);
            setActiveRouteNodeIndex(1);

            setError(null);
            setIsPolling(true);
            closeRecoveryModal();
          },
          buttonText: "Request Refund",
          severity: "high",
        },
      ];

      setRecoveryOptions(options);
      setLoadingRecovery(false);
      openRecoveryModal();
    } catch (error) {
      console.error("Error generating recovery options:", error);
      setLoadingRecovery(false);

      // Set basic recovery options
      setRecoveryOptions([
        {
          id: "retry",
          title: "Retry Transaction",
          description:
            "Attempt to retry the transaction with the same parameters",
          action: async () => {
            // Simple retry
            setError(null);
            setIsPolling(true);
            closeRecoveryModal();
          },
          buttonText: "Retry",
          severity: "medium",
        },
      ]);

      openRecoveryModal();
    }
  }, [
    steps,
    routeNodes,
    sourceChainName,
    amount,
    asset,
    sourceChain,
    closeRecoveryModal,
    openRecoveryModal,
  ]);

  // Handle manual retry
  const handleRetry = useCallback(() => {
    // Reset error state
    setError(null);

    // Start polling again
    setIsPolling(true);

    // If transaction failed completely, show recovery options
    if (steps.some((step) => step.status === "failed")) {
      generateRecoveryOptions();
    }
  }, [steps, generateRecoveryOptions]);

  // Render
  return (
    <MotionBox
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.5 }}
      borderWidth="1px"
      borderRadius="lg"
      borderColor={borderColor}
      bg={bgColor}
      overflow="hidden"
      w="100%"
      maxW="650px"
      mx="auto"
    >
      {/* Header */}
      <Box
        p={4}
        borderBottomWidth="1px"
        borderColor={borderColor}
        bg={useColorModeValue("gray.50", "gray.900")}
      >
        <Flex justify="space-between" align="center">
          <VStack align="start" spacing={0}>
            <Heading size="sm">Cross-Chain Transaction</Heading>
            <Text fontSize="sm" color="gray.500">
              {sourceChainName} → {destinationChainName}
            </Text>
          </VStack>

          <Badge
            colorScheme={
              error
                ? "red"
                : currentStepIndex >= steps.length - 1
                ? "green"
                : "blue"
            }
            fontSize="sm"
            py={1}
            px={2}
            borderRadius="full"
          >
            {error
              ? "Failed"
              : currentStepIndex >= steps.length - 1
              ? "Completed"
              : "In Progress"}
          </Badge>
        </Flex>
      </Box>

      {/* Body */}
      <Box p={4}>
        {/* Error alert */}
        {error && (
          <MotionBox
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
            mb={4}
          >
            <Alert status="error" borderRadius="md">
              <AlertIcon />
              <Box flex="1">
                <AlertTitle>Transaction Failed</AlertTitle>
                <AlertDescription fontSize="sm">{error}</AlertDescription>
              </Box>
              <Button
                size="sm"
                colorScheme="red"
                variant="outline"
                leftIcon={<Icon as={FaSyncAlt} />}
                onClick={handleRetry}
              >
                Retry
              </Button>
            </Alert>
          </MotionBox>
        )}

        {/* Transaction summary */}
        <SimpleGrid columns={{ base: 1, md: 2 }} spacing={4} mb={4}>
          <Stat>
            <StatLabel>Amount</StatLabel>
            <StatNumber>
              {amount} {asset}
            </StatNumber>
            <StatHelpText>
              {txHash.substring(0, 6)}...{txHash.substring(txHash.length - 4)}
            </StatHelpText>
          </Stat>

          <Stat>
            <StatLabel>Estimated Completion</StatLabel>
            <StatNumber>
              {txDetails?.estimatedCompletionTime
                ? new Date(
                    txDetails.estimatedCompletionTime
                  ).toLocaleTimeString()
                : quote?.estimatedTime || "10-15 minutes"}
            </StatNumber>
            <StatHelpText>
              {currentStepIndex === steps.length - 1
                ? "Completed"
                : `Step ${currentStepIndex + 1} of ${steps.length}`}
            </StatHelpText>
          </Stat>
        </SimpleGrid>

        {/* Progress bar */}
        <StepProgressBar steps={steps} currentStep={currentStepIndex} />

        {/* Route visualization */}
        <RouteVisualization
          route={routeNodes}
          activeNodeIndex={activeRouteNodeIndex}
        />

        {/* Fee breakdown */}
        {quote?.feeBreakdown && (
          <FeeBreakdownDisplay
            feeBreakdown={quote.feeBreakdown}
            asset={asset}
            showOptimizationTips={!error && currentStepIndex < 2}
          />
        )}

        {/* Detailed steps */}
        {showDetailedView && <DetailedSteps steps={steps} />}

        {/* Axelar branding */}
        <Box mt={4}>
          <AxelarBranding />
        </Box>

        {/* View in explorer link */}
        <Flex justify="center" mt={4}>
          <Link
            href={ChainUtils.getExplorerUrl(
              typeof sourceChain === "number" ? sourceChain : 1,
              txHash
            )}
            isExternal
            fontSize="sm"
            color="blue.500"
          >
            <HStack spacing={1}>
              <Icon as={FaExternalLinkAlt} fontSize="xs" />
              <Text>View transaction in explorer</Text>
            </HStack>
          </Link>
        </Flex>
      </Box>

      {/* Recovery modal */}
      <RecoveryOptionsModal
        isOpen={isRecoveryModalOpen}
        onClose={closeRecoveryModal}
        options={recoveryOptions}
        txHash={txHash}
        isLoading={loadingRecovery}
      />
    </MotionBox>
  );
};

export default CrosschainTransactionTracker;

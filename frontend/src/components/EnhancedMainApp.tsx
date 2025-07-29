"use client";

import * as React from "react";
import { useState, useEffect, useRef, useCallback } from "react";
import Image from "next/image";
import {
  Box,
  Container,
  Flex,
  VStack,
  Heading,
  Text,
  useToast,
  Alert,
  AlertIcon,
  AlertTitle,
  AlertDescription,
  HStack,
  Icon,
  SimpleGrid,
  useColorModeValue,
  useColorMode,
  IconButton,
  Tooltip,
  Divider,
  Badge,
  Collapse,
  useDisclosure,
  Portal,
  Fade,
  Drawer,
  DrawerBody,
  DrawerHeader,
  DrawerOverlay,
  DrawerContent,
  DrawerCloseButton,
} from "@chakra-ui/react";
import {
  FaExchangeAlt,
  FaLink,
  FaWallet,
  FaCoins,
  FaChartPie,
  FaSearch,
  FaSun,
  FaMoon,
  FaQuestionCircle,
  FaCog,
  FaBell,
  FaUser,
  FaHistory,
  FaArrowRight,
  FaEthereum,
  FaBitcoin,
  FaChevronDown,
  FaChevronUp,
  FaInfoCircle,
  FaExclamationTriangle,
  FaCheckCircle,
  FaTimes,
  FaRedo,
  FaPlus,
  FaMinus,
} from "react-icons/fa";
import {
  useAccount,
  usePublicClient,
  useWalletClient,
  useChainId,
} from "wagmi";
import { motion, AnimatePresence, useAnimation } from "framer-motion";
import { CommandInput } from "./CommandInput";
import { CommandResponse } from "./CommandResponse";
import { WalletButton } from "./WalletButton";
import { ExternalLinkIcon, SettingsIcon, QuestionIcon } from "@chakra-ui/icons";
import { ApiKeyModal } from "./ApiKeyModal";
import { LogoModal } from "./LogoModal";
import { HelpModal } from "./HelpModal";
import { fetchUserProfile } from "../services/profileService";
import { Response } from "../types/responses";
import { SUPPORTED_CHAINS } from "../constants/chains";
import { ApiService } from "../services/apiService";
import { TransactionService } from "../services/transactionService";
import { PortfolioService } from "../services/portfolioService";
import { AdvancedSettings, AdvancedSettingsValues } from "./AdvancedSettings";
import {
  withAsyncRecursionGuard,
  recursionGuard,
} from "../utils/recursionGuard";
import { setupGlobalWalletErrorHandler } from "../utils/walletErrorHandler";

// Import our enhanced components
import EnhancedButton from "./ui/EnhancedButton";
import EnhancedInput from "./ui/EnhancedInput";
import EnhancedCard from "./ui/EnhancedCard";
import EnhancedLoader from "./ui/EnhancedLoader";
import EnhancedModal from "./ui/EnhancedModal";
import InteractiveOnboardingFinal from "./onboarding/InteractiveOnboardingFinal";
import CrosschainTransactionTracker from "./enhanced/CrosschainTransactionTracker";

// Animation variants
const pageTransitionVariants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: { duration: 0.5 } },
  exit: { opacity: 0, transition: { duration: 0.3 } },
};

const cardVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: { 
    opacity: 1, 
    y: 0, 
    transition: { 
      type: "spring", 
      damping: 25, 
      stiffness: 500 
    } 
  },
  exit: { opacity: 0, y: -20, transition: { duration: 0.2 } },
};

const staggerContainerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1,
      delayChildren: 0.2,
    },
  },
};

const featureItemVariants = {
  hidden: { opacity: 0, y: 10 },
  visible: { 
    opacity: 1, 
    y: 0, 
    transition: { 
      type: "spring", 
      damping: 25, 
      stiffness: 500 
    } 
  },
};

interface ResponseContent {
  type?: string;
  confirmation_type?: string;
  pendingCommand?: string;
  transaction?: any;
  [key: string]: any;
}

interface ResponseType {
  content: string | ResponseContent;
  timestamp: string;
  isCommand: boolean;
  status?: "pending" | "processing" | "success" | "error";
  metadata?: any;
  awaitingConfirmation?: boolean;
  agentType?:
    | "default"
    | "swap"
    | "dca"
    | "brian"
    | "bridge"
    | "transfer"
    | "agno"
    | "settings";
  requires_selection?: boolean;
  all_quotes?: any[];
  type?: string;
  confirmation_type?: string;
  pendingCommand?: string;
  transaction?: any;
  summary?: string;
  fullAnalysis?: string;
}

// Enhanced MainApp component
function EnhancedMainApp() {
  // Chakra hooks
  const toast = useToast();
  const { colorMode, toggleColorMode } = useColorMode();
  
  // Wallet hooks
  const { address, isConnected } = useAccount();
  const chainId = useChainId();
  const { data: walletClient } = useWalletClient();
  const publicClient = usePublicClient();

  // Theme colors
  const bgColor = useColorModeValue("gray.50", "gray.900");
  const cardBgColor = useColorModeValue("white", "gray.800");
  const borderColor = useColorModeValue("gray.200", "gray.700");
  const accentColor = useColorModeValue("blue.500", "blue.300");
  const textColor = useColorModeValue("gray.800", "gray.100");
  const subtleTextColor = useColorModeValue("gray.600", "gray.400");
  // Background for settings/portfolio boxes (was inline causing conditional hook warning)
  const settingsBoxBgColor = useColorModeValue("gray.50", "gray.800");

  // Glass effect properties
  const glassBg = useColorModeValue(
    "rgba(255, 255, 255, 0.8)",
    "rgba(26, 32, 44, 0.8)"
  );
  const glassBorder = useColorModeValue(
    "1px solid rgba(255, 255, 255, 0.3)",
    "1px solid rgba(255, 255, 255, 0.1)"
  );
  const glassFilter = "blur(10px)";

  // Initialize services with stable references
  const apiService = React.useMemo(() => new ApiService(), []);
  const portfolioService = React.useMemo(
    () => new PortfolioService(apiService),
    [apiService]
  );
  const transactionService = React.useMemo(
    () =>
      walletClient && publicClient && chainId
        ? new TransactionService(walletClient, publicClient, chainId)
        : null,
    [walletClient, publicClient, chainId]
  );

  // State
  const [responses, setResponses] = useState<ResponseType[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isLogoModalOpen, setIsLogoModalOpen] = useState(false);
  const [isHelpModalOpen, setIsHelpModalOpen] = useState(false);
  const [isApiKeyModalOpen, setIsApiKeyModalOpen] = useState(false);
  const [showOnboarding, setShowOnboarding] = useState(false);
  const [userProfile, setUserProfile] = useState<any>(null);
  const [userId, setUserId] = useState<string>("");
  const [portfolioProcessingId, setPortfolioProcessingId] = useState<
    string | null
  >(null);
  const [isRetryingPortfolio, setIsRetryingPortfolio] =
    useState<boolean>(false);
  const [advancedSettings, setAdvancedSettings] =
    useState<AdvancedSettingsValues>({
      protocol: "auto",
      slippageTolerance: 1.0,
      enableMEVProtection: true,
      preferredRoute: "balanced",
      manualChainSelection: false,
    });
  const [axelarUnavailable, setAxelarUnavailable] = useState<boolean>(false);
  const [portfolioSettings, setPortfolioSettings] = useState(() => ({
    enabled:
      typeof window !== "undefined"
        ? localStorage.getItem("snel_portfolio_enabled") === "true"
        : false,
    cacheEnabled: true,
  }));
  const [isSettingsDrawerOpen, setIsSettingsDrawerOpen] = useState(false);
  const [isFirstVisit, setIsFirstVisit] = useState(false);
  const [activeTransaction, setActiveTransaction] = useState<any>(null);
  const [showAdvancedSettings, setShowAdvancedSettings] = useState(false);

  // Refs
  const responsesEndRef = useRef<HTMLDivElement>(null);
  const commandInputRef = useRef<HTMLInputElement>(null);
  
  // Animation controls
  const controls = useAnimation();

  const isResponseContent = (content: any): content is ResponseContent => {
    return typeof content === "object" && content !== null;
  };

  // Setup global error handlers on mount
  useEffect(() => {
    setupGlobalWalletErrorHandler();
    
    // Check if this is the user's first visit
    const hasVisitedBefore = localStorage.getItem("snel_visited");
    if (!hasVisitedBefore) {
      setIsFirstVisit(true);
      localStorage.setItem("snel_visited", "true");
    }
  }, []);

  // Initialize or update welcome message based on wallet state
  useEffect(() => {
    const welcomeMessage: ResponseType = {
      content: isConnected
        ? chainId && chainId in SUPPORTED_CHAINS
          ? `Welcome to SNEL! How can I help you with crypto today? You're connected to ${
              SUPPORTED_CHAINS[chainId as keyof typeof SUPPORTED_CHAINS]
            }.`
          : "Please switch to a supported network to continue."
        : "Welcome to SNEL! Please connect your wallet to get started.",
      timestamp: new Date().toISOString(),
      isCommand: false,
      status: "success" as const,
    };

    setResponses((prev) =>
      prev.length === 0
        ? [welcomeMessage]
        : prev[0].isCommand
        ? [welcomeMessage, ...prev]
        : prev.map((r, i) => (i === 0 ? welcomeMessage : r))
    );
    
    // Show onboarding for first-time visitors who connect their wallet
    if (isFirstVisit && isConnected) {
      setTimeout(() => {
        setShowOnboarding(true);
      }, 1000);
    }
  }, [isConnected, chainId, isFirstVisit]);

  // Fetch user profile when address changes
  useEffect(() => {
    const fetchProfile = async () => {
      if (address) {
        const profile = await fetchUserProfile(address);
        setUserProfile(profile);
      } else {
        setUserProfile(null);
      }
    };
    fetchProfile();
  }, [address]);

  // Add chain change effect
  useEffect(() => {
    if (chainId) {
      const isSupported = chainId in SUPPORTED_CHAINS;
      if (!isSupported) {
        setResponses((prev) => prev.filter((r) => !r.awaitingConfirmation));
        toast({
          title: "Unsupported Network",
          description: `Please switch to a supported network: ${Object.values(
            SUPPORTED_CHAINS
          ).join(", ")}`,
          status: "warning",
          duration: 5000,
          isClosable: true,
          position: "top",
          render: ({ onClose }) => (
            <EnhancedCard
              variant="glass"
              title="Unsupported Network"
              headerIcon={<Icon as={FaExclamationTriangle} color="orange.500" />}
              footerActions={[
                {
                  label: "Close",
                  onClick: onClose,
                },
              ]}
            >
              <Text>
                Please switch to a supported network: {" "}
                {Object.values(SUPPORTED_CHAINS).join(", ")}
              </Text>
            </EnhancedCard>
          ),
        });
      }
    }
  }, [chainId, toast]);

  // Add extraction of userId from walletAddress
  useEffect(() => {
    if (walletClient && address) {
      setUserId(address);
    } else {
      setUserId("");
    }
  }, [walletClient, address]);

  // Check Axelar availability on component mount
  useEffect(() => {
    const checkAxelar = async () => {
      try {
        const available = await apiService.checkAxelarAvailability();
        setAxelarUnavailable(!available);
      } catch (error) {
        console.warn("Could not check Axelar availability:", error);
        setAxelarUnavailable(true);
      }
    };

    if (isConnected) {
      checkAxelar();
    }
  }, [isConnected, apiService]);

  // Scroll to bottom when responses change
  const scrollToBottom = () => {
    responsesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [responses]);

  // Handle portfolio actions
  const handlePortfolioAction = async (action: any) => {
    if (action.type === "retry") {
      setIsRetryingPortfolio(true);
      try {
        await handleCommand("analyze my portfolio", true);
      } finally {
        setIsRetryingPortfolio(false);
      }
    } else if (action.type === "stablecoin_suggestion") {
      // Add SNEL message suggesting swap command
      const timestamp = new Date().toISOString();
      const suggestionResponse = {
        content: action.message,
        timestamp,
        isCommand: false,
        status: "success" as const,
        agentType: "default" as const,
      };
      setResponses((prev) => [...prev, suggestionResponse]);
    } else if (action.type === "enable_portfolio") {
      // Enable portfolio analysis
      setPortfolioSettings((prev) => ({ ...prev, enabled: true }));
      localStorage.setItem("snel_portfolio_enabled", "true");

      // Add confirmation message
      const timestamp = new Date().toISOString();
      const confirmationResponse = {
        content:
          "✅ Portfolio analysis enabled! You can now get detailed insights about your holdings. Analysis will be cached for 5 minutes to improve performance.",
        timestamp,
        isCommand: false,
        status: "success" as const,
        agentType: "settings" as const,
      };
      setResponses((prev) => [...prev, confirmationResponse]);

      // Auto-trigger portfolio analysis if the last command was a portfolio command
      const lastUserMessage = responses.filter((r) => r.isCommand).pop();
      if (
        lastUserMessage &&
        typeof lastUserMessage.content === "string" &&
        /portfolio|allocation|holdings|assets|analyze/i.test(
          lastUserMessage.content
        )
      ) {
        setTimeout(() => {
          handleCommand(lastUserMessage.content as string, true);
        }, 1000);
      }
    }
  };

  // Handle command submission with recursion guard
  const handleCommand = withAsyncRecursionGuard(
    async (command: string | undefined, isRetry: boolean = false) => {
      if (!command) return;

      // Check if wallet is connected
      if (!isConnected) {
        toast({
          title: "Wallet Not Connected",
          description: "Please connect your wallet to use Snel.",
          status: "warning",
          duration: 5000,
          isClosable: true,
          position: "top",
          render: ({ onClose }) => (
            <EnhancedCard
              variant="glass"
              title="Wallet Not Connected"
              headerIcon={<Icon as={FaWallet} color="orange.500" />}
              footerActions={[
                {
                  label: "Close",
                  onClick: onClose,
                },
              ]}
            >
              <Text>Please connect your wallet to use SNEL.</Text>
            </EnhancedCard>
          ),
        });
        return;
      }

      // Check if chain is supported
      if (!chainId || !(chainId in SUPPORTED_CHAINS)) {
        toast({
          title: "Wrong Network",
          description: "Please connect to a supported network.",
          status: "error",
          duration: 5000,
          isClosable: true,
          position: "top",
          render: ({ onClose }) => (
            <EnhancedCard
              variant="glass"
              title="Wrong Network"
              headerIcon={<Icon as={FaExclamationTriangle} color="red.500" />}
              footerActions={[
                {
                  label: "Close",
                  onClick: onClose,
                },
              ]}
            >
              <Text>Please connect to a supported network.</Text>
            </EnhancedCard>
          ),
        });
        return;
      }

      setIsLoading(true);
      try {
        // Add command to responses immediately to show user input
        const timestamp = new Date().toISOString();
        const commandResponse = {
          content: command,
          timestamp,
          isCommand: true,
          status: "success" as const,
        };
        setResponses((prev) => [...prev, commandResponse]);

        // Check if this is a portfolio analysis command
        const isPortfolioCommand =
          /portfolio|allocation|holdings|assets|analyze/i.test(
            command.toLowerCase()
          );

        if (isPortfolioCommand) {
          // Add processing state immediately for portfolio commands
          const processingResponse = {
            content: { type: "portfolio_progress" },
            timestamp: new Date().toISOString(),
            isCommand: false,
            status: "processing" as const,
            agentType: "agno" as const,
            metadata: { progress: 0, stage: "Starting analysis..." },
          };
          setResponses((prev) => [...prev, processingResponse]);

          // Process portfolio command with progressive updates
          try {
            const response = await apiService.processCommand(
              command,
              address, // Use actual connected wallet address
              chainId, // Use actual connected chain ID
              userProfile?.name,
              (progress, stage) => {
                // Update progress in the UI
                setResponses((prev) =>
                  prev.map((r) =>
                    r.status === "processing" && r.agentType === "agno"
                      ? {
                          ...r,
                          metadata: { progress, stage },
                        }
                      : r
                  )
                );
              },
              walletClient, // Pass signer for potential Axelar operations
              portfolioSettings // Pass portfolio settings
            );

            // Replace processing response with final result
            setResponses((prev) =>
              prev.map((r) =>
                r.status === "processing" && r.agentType === "agno"
                  ? {
                      ...response,
                      agentType: response.agent_type || response.agentType, // Map agent_type to agentType
                      timestamp: new Date().toISOString(),
                      isCommand: false,
                      status: "success" as const,
                    }
                  : r
              )
            );
          } catch (error) {
            console.error("Portfolio analysis failed:", error);
            // Replace processing with error
            setResponses((prev) =>
              prev.map((r) =>
                r.status === "processing" && r.agentType === "agno"
                  ? {
                      content: {
                        error:
                          error instanceof Error
                            ? error.message
                            : "Analysis failed",
                        type: "error",
                      },
                      timestamp: new Date().toISOString(),
                      isCommand: false,
                      status: "error" as const,
                      agentType: "agno" as const,
                    }
                  : r
              )
            );
          }
        } else {
          // Regular command processing for non-portfolio commands
          const response = await apiService.processCommand(
            command,
            address,
            chainId,
            userProfile?.name,
            undefined, // onProgress
            walletClient, // Pass signer for potential Axelar operations
            portfolioSettings // Pass portfolio settings
          );

          // Check for transaction in response
          if (response.transaction) {
            setActiveTransaction(response.transaction);
          }

          // Regular handling for non-portfolio commands
          setResponses((prev) => [
            ...prev,
            {
              ...response,
              agentType: response.agent_type || response.agentType, // Map agent_type to agentType
              timestamp: new Date().toISOString(),
              isCommand: false,
              status: "success",
            },
          ]);
        }
      } catch (error) {
        console.error("Error processing command:", error);
        toast({
          title: "Error",
          description: "Failed to process command. Please try again.",
          status: "error",
          duration: 5000,
          isClosable: true,
          position: "top",
          render: ({ onClose }) => (
            <EnhancedCard
              variant="glass"
              title="Command Processing Error"
              headerIcon={<Icon as={FaTimes} color="red.500" />}
              footerActions={[
                {
                  label: "Close",
                  onClick: onClose,
                },
                {
                  label: "Retry",
                  onClick: () => {
                    onClose();
                    handleCommand(command, true);
                  },
                  icon: <FaRedo />,
                },
              ]}
            >
              <Text>Failed to process command. Please try again.</Text>
            </EnhancedCard>
          ),
        });
      }
      setIsLoading(false);
    },
    "handleCommand"
  );

  // Reset any portfolio processing state when the component unmounts
  useEffect(() => {
    return () => {
      setPortfolioProcessingId(null);
      setIsRetryingPortfolio(false);
    };
  }, []);

  // Handle onboarding completion
  const handleOnboardingComplete = () => {
    setShowOnboarding(false);
    toast({
      title: "Onboarding Complete",
      description: "You're all set to use SNEL!",
      status: "success",
      duration: 3000,
      isClosable: true,
      position: "top",
    });
    // Focus the command input after onboarding
    setTimeout(() => {
      commandInputRef.current?.focus();
    }, 500);
  };

  // Handle transaction updates
  const handleTransactionUpdate = (status: string, hash: string) => {
    if (activeTransaction) {
      setActiveTransaction({
        ...activeTransaction,
        status,
        hash,
      });
    }
  };

  // Render the enhanced main app
  return (
    <motion.div
      initial="hidden"
      animate="visible"
      exit="exit"
      variants={pageTransitionVariants}
    >
      <Box 
        minH="100vh" 
        bg={bgColor}
        backgroundImage={colorMode === "light" 
          ? "radial-gradient(circle at 50% 0%, rgba(255, 255, 255, 0.5), transparent 70%)"
          : "radial-gradient(circle at 50% 0%, rgba(26, 32, 44, 0.5), transparent 70%)"
        }
        backgroundSize="100% 100%"
        backgroundRepeat="no-repeat"
        position="relative"
        overflow="hidden"
      >
        {/* Background gradient elements */}
        <Box
          position="absolute"
          top="-10%"
          left="-10%"
          width="120%"
          height="120%"
          bgGradient={colorMode === "light" 
            ? "radial-gradient(circle at 0% 0%, rgba(66, 153, 225, 0.1), transparent 50%)"
            : "radial-gradient(circle at 0% 0%, rgba(66, 153, 225, 0.05), transparent 50%)"
          }
          zIndex={0}
          pointerEvents="none"
        />
        
        <Box
          position="absolute"
          bottom="-10%"
          right="-10%"
          width="120%"
          height="120%"
          bgGradient={colorMode === "light" 
            ? "radial-gradient(circle at 100% 100%, rgba(159, 122, 234, 0.1), transparent 50%)"
            : "radial-gradient(circle at 100% 100%, rgba(159, 122, 234, 0.05), transparent 50%)"
          }
          zIndex={0}
          pointerEvents="none"
        />

        <Container maxW="container.xl" py={4} position="relative" zIndex={1}>
          <VStack spacing={8} align="stretch">
            {/* Header */}
            <EnhancedCard
              variant="glass"
              glassMorphism={true}
              glassMorphismStrength={10}
              size="full"
              borderRadius="lg"
              boxShadow="md"
            >
              <Flex
                align="center"
                justify="space-between"
                w="100%"
                flexDir={{ base: "column", sm: "row" }}
                gap={{ base: 2, sm: 4 }}
              >
                <Box 
                  cursor="pointer" 
                  onClick={() => setIsLogoModalOpen(true)}
                  transition="transform 0.2s"
                  _hover={{ transform: "scale(1.1)" }}
                >
                  <Image src="/icon.png" alt="Logo" width={40} height={40} />
                </Box>

                <Heading 
                  as="h1" 
                  size="lg" 
                  textAlign="center"
                  bgGradient="linear(to-r, blue.400, purple.500)"
                  bgClip="text"
                  fontWeight="extrabold"
                >
                  SNEL
                </Heading>

                <HStack spacing={4}>
                  <Tooltip label="Toggle theme">
                    <IconButton
                      aria-label="Toggle theme"
                      icon={colorMode === "light" ? <FaMoon /> : <FaSun />}
                      onClick={toggleColorMode}
                      variant="ghost"
                      colorScheme="blue"
                      size="sm"
                    />
                  </Tooltip>
                  <Tooltip label="Help">
                    <IconButton
                      aria-label="Help"
                      icon={<QuestionIcon />}
                      onClick={() => setIsHelpModalOpen(true)}
                      variant="ghost"
                      colorScheme="blue"
                      size="sm"
                    />
                  </Tooltip>
                  <Tooltip label="Settings">
                    <IconButton
                      aria-label="Settings"
                      icon={<SettingsIcon />}
                      onClick={() => setIsSettingsDrawerOpen(true)}
                      variant="ghost"
                      colorScheme="blue"
                      size="sm"
                    />
                  </Tooltip>
                  <WalletButton />
                </HStack>
              </Flex>
            </EnhancedCard>

            {/* Main Content */}
            <Box flex={1}>
              {!isConnected ? (
                <AnimatePresence>
                  <motion.div
                    variants={staggerContainerVariants}
                    initial="hidden"
                    animate="visible"
                  >
                    <EnhancedCard
                      variant="glass"
                      glassMorphism={true}
                      glassMorphismStrength={10}
                      size="full"
                      borderRadius="lg"
                      boxShadow="md"
                    >
                      <VStack spacing={6} align="center" justify="center" py={8}>
                        {/* Logo with animation */}
                        <motion.div
                          animate={{ 
                            scale: [1, 1.05, 1],
                            rotate: [0, 2, 0, -2, 0]
                          }}
                          transition={{ 
                            duration: 4, 
                            repeat: Infinity, 
                            repeatType: "reverse" 
                          }}
                        >
                          <Box position="relative" width="80px" height="80px">
                            <Image
                              src="/icon.png"
                              alt="SNEL Logo"
                              width={80}
                              height={80}
                              priority
                              style={{ objectFit: "contain" }}
                            />
                          </Box>
                        </motion.div>

                        {/* Platform Capabilities */}
                        <VStack spacing={4} align="center">
                          <Heading size="md" mb={2} textAlign="center">
                            Your AI-Powered Crypto Assistant
                          </Heading>
                          
                          <SimpleGrid 
                            columns={{ base: 2, md: 3 }} 
                            spacing={4} 
                            maxW="500px"
                          >
                            <motion.div variants={featureItemVariants}>
                              <EnhancedCard
                                variant="glass"
                                glassMorphism={true}
                                size="sm"
                                isInteractive={true}
                              >
                                <VStack
                                  spacing={2}
                                  align="center"
                                  p={3}
                                >
                                  <Icon as={FaExchangeAlt} color="blue.500" boxSize={5} />
                                  <Text
                                    fontSize="sm"
                                    fontWeight="medium"
                                    textAlign="center"
                                  >
                                    Token Transfers
                                  </Text>
                                </VStack>
                              </EnhancedCard>
                            </motion.div>
                            
                            <motion.div variants={featureItemVariants}>
                              <EnhancedCard
                                variant="glass"
                                glassMorphism={true}
                                size="sm"
                                isInteractive={true}
                              >
                                <VStack
                                  spacing={2}
                                  align="center"
                                  p={3}
                                >
                                  <Icon as={FaLink} color="purple.500" boxSize={5} />
                                  <Text
                                    fontSize="sm"
                                    fontWeight="medium"
                                    textAlign="center"
                                  >
                                    Cross-Chain Bridging
                                  </Text>
                                </VStack>
                              </EnhancedCard>
                            </motion.div>
                            
                            <motion.div variants={featureItemVariants}>
                              <EnhancedCard
                                variant="glass"
                                glassMorphism={true}
                                size="sm"
                                isInteractive={true}
                              >
                                <VStack
                                  spacing={2}
                                  align="center"
                                  p={3}
                                >
                                  <Icon as={FaWallet} color="green.500" boxSize={5} />
                                  <Text
                                    fontSize="sm"
                                    fontWeight="medium"
                                    textAlign="center"
                                  >
                                    Balance Checking
                                  </Text>
                                </VStack>
                              </EnhancedCard>
                            </motion.div>
                            
                            <motion.div variants={featureItemVariants}>
                              <EnhancedCard
                                variant="glass"
                                glassMorphism={true}
                                size="sm"
                                isInteractive={true}
                              >
                                <VStack
                                  spacing={2}
                                  align="center"
                                  p={3}
                                >
                                  <Icon as={FaCoins} color="yellow.500" boxSize={5} />
                                  <Text
                                    fontSize="sm"
                                    fontWeight="medium"
                                    textAlign="center"
                                  >
                                    Token Swaps
                                  </Text>
                                </VStack>
                              </EnhancedCard>
                            </motion.div>
                            
                            <motion.div variants={featureItemVariants}>
                              <EnhancedCard
                                variant="glass"
                                glassMorphism={true}
                                size="sm"
                                isInteractive={true}
                              >
                                <VStack
                                  spacing={2}
                                  align="center"
                                  p={3}
                                >
                                  <Icon as={FaChartPie} color="cyan.500" boxSize={5} />
                                  <Text
                                    fontSize="sm"
                                    fontWeight="medium"
                                    textAlign="center"
                                  >
                                    Portfolio Analysis
                                  </Text>
                                </VStack>
                              </EnhancedCard>
                            </motion.div>
                            
                            <motion.div variants={featureItemVariants}>
                              <EnhancedCard
                                variant="glass"
                                glassMorphism={true}
                                size="sm"
                                isInteractive={true}
                              >
                                <VStack
                                  spacing={2}
                                  align="center"
                                  p={3}
                                >
                                  <Icon as={FaSearch} color="red.500" boxSize={5} />
                                  <Text
                                    fontSize="sm"
                                    fontWeight="medium"
                                    textAlign="center"
                                  >
                                    Protocol Research
                                  </Text>
                                </VStack>
                              </EnhancedCard>
                            </motion.div>
                          </SimpleGrid>

                          {/* Hint about help modal */}
                          <Text fontSize="sm" color={subtleTextColor} textAlign="center" mt={4}>
                            Click ? above for specific commands <br />
                            Click ⚙️ above to configure API keys
                          </Text>
                        </VStack>

                        {/* Connect Wallet Button */}
                        <motion.div
                          whileHover={{ scale: 1.05 }}
                          whileTap={{ scale: 0.95 }}
                        >
                          <EnhancedButton
                            size="lg"
                            variant="primary"
                            leftIcon={<FaWallet />}
                            onClick={() => {
                              // This will trigger the WalletButton component's connect functionality
                              document.getElementById("wallet-connect-button")?.click();
                            }}
                            animate={true}
                            pulseEffect={true}
                          >
                            Connect Wallet
                          </EnhancedButton>
                        </motion.div>
                      </VStack>
                    </EnhancedCard>
                  </motion.div>
                </AnimatePresence>
              ) : (
                <VStack spacing={4} align="stretch">
                  {/* Active Transaction Tracker */}
                  {activeTransaction && (
                    <EnhancedCard
                      variant="glass"
                      glassMorphism={true}
                      glassMorphismStrength={10}
                      size="full"
                      borderRadius="lg"
                      boxShadow="md"
                      title="Transaction Progress"
                      headerIcon={<Icon as={FaExchangeAlt} color={accentColor} />}
                    >
                      <CrosschainTransactionTracker
                        transaction={activeTransaction}
                        onStatusUpdate={handleTransactionUpdate}
                      />
                    </EnhancedCard>
                  )}
                  
                  {/* Chat Messages */}
                  <AnimatePresence>
                    {responses.map((response, index) => (
                      <motion.div
                        key={index}
                        variants={cardVariants}
                        initial="hidden"
                        animate="visible"
                        exit="exit"
                        custom={index}
                      >
                        <EnhancedCard
                          variant={response.isCommand ? "default" : "glass"}
                          glassMorphism={!response.isCommand}
                          glassMorphismStrength={10}
                          size="full"
                          borderRadius="lg"
                          boxShadow="sm"
                          mb={2}
                        >
                          <CommandResponse
                            content={response.content}
                            timestamp={response.timestamp}
                            isCommand={response.isCommand}
                            status={response.status}
                            metadata={response.metadata}
                            agentType={response.agentType}
                            transaction={response.transaction}
                            awaitingConfirmation={response.awaitingConfirmation}
                            onActionClick={handlePortfolioAction}
                          />
                        </EnhancedCard>
                      </motion.div>
                    ))}
                  </AnimatePresence>
                  
                  <div ref={responsesEndRef} />
                  
                  {/* Command Input */}
                  <EnhancedCard
                    variant="glass"
                    glassMorphism={true}
                    glassMorphismStrength={10}
                    size="full"
                    borderRadius="lg"
                    boxShadow="md"
                  >
                    <VStack spacing={4} align="stretch">
                      <Box position="relative">
                        <EnhancedInput
                          name="command"
                          placeholder="Type a command like 'swap $10 for $UNI and send it to vitalik.eth'"
                          inputType="text"
                          size="lg"
                          variant="floating"
                          leftIcon={<Icon as={FaSearch} color="gray.500" />}
                          rightIcon={
                            isLoading ? (
                              <EnhancedLoader
                                variant="spinner"
                                size="sm"
                                color={accentColor}
                              />
                            ) : null
                          }
                          ref={commandInputRef}
                          onKeyPress={(e) => {
                            if (e.key === "Enter" && !isLoading) {
                              const target = e.target as HTMLInputElement;
                              handleCommand(target.value);
                              target.value = "";
                            }
                          }}
                        />
                        
                        <Box position="absolute" right="4" bottom="-10">
                          <EnhancedButton
                            size="sm"
                            variant="text"
                            onClick={() => setShowAdvancedSettings(!showAdvancedSettings)}
                            rightIcon={showAdvancedSettings ? <FaChevronUp /> : <FaChevronDown />}
                          >
                            Advanced Settings
                          </EnhancedButton>
                        </Box>
                      </Box>
                      
                      {/* Advanced Settings */}
                      <Collapse in={showAdvancedSettings} animateOpacity>
                        <Box pt={2}>
                          <AdvancedSettings
                            axelarUnavailable={axelarUnavailable}
                            onSettingsChange={setAdvancedSettings}
                          />
                          
                          {/* Portfolio Settings */}
                          <Box
                            p={3}
                            bg={settingsBoxBgColor}
                            borderRadius="md"
                            border="1px solid"
                            borderColor={borderColor}
                            mt={3}
                          >
                            <HStack justify="space-between">
                              <VStack align="flex-start" spacing={0}>
                                <Text fontSize="sm" fontWeight="medium">
                                  Portfolio Analysis
                                </Text>
                                <Text fontSize="xs" color="gray.500">
                                  {portfolioSettings.enabled
                                    ? "Enabled - Analysis cached for 5min"
                                    : "Disabled for faster performance"}
                                </Text>
                              </VStack>
                              <EnhancedButton
                                variant="switch"
                                isActive={portfolioSettings.enabled}
                                onClick={() => {
                                  const newValue = !portfolioSettings.enabled;
                                  setPortfolioSettings((prev) => ({
                                    ...prev,
                                    enabled: newValue,
                                  }));
                                  localStorage.setItem(
                                    "snel_portfolio_enabled",
                                    newValue.toString()
                                  );
                                }}
                                size="sm"
                              />
                            </HStack>
                          </Box>
                        </Box>
                      </Collapse>
                    </VStack>
                  </EnhancedCard>
                </VStack>
              )}
            </Box>
          </VStack>
        </Container>

        {/* Modals */}
        <EnhancedModal
          isOpen={isLogoModalOpen}
          onClose={() => setIsLogoModalOpen(false)}
          title="About SNEL"
          variant="centered"
          animation="scale"
          size="md"
          glassMorphism={true}
          overlayBlur="8px"
        >
          <VStack spacing={4} align="center">
            <Box position="relative" width="100px" height="100px">
              <Image
                src="/icon.png"
                alt="SNEL Logo"
                width={100}
                height={100}
                priority
                style={{ objectFit: "contain" }}
              />
            </Box>
            <Text textAlign="center">
              SNEL is an AI-powered crypto assistant that helps you navigate the
              world of cryptocurrencies with natural language commands. Swap tokens,
              bridge assets across chains, check balances, and more - all in one place.
            </Text>
            <Text fontSize="sm" color={subtleTextColor} textAlign="center">
              Version 1.0.0
            </Text>
          </VStack>
        </EnhancedModal>

        <EnhancedModal
          isOpen={isHelpModalOpen}
          onClose={() => setIsHelpModalOpen(false)}
          title="Help & Commands"
          variant="centered"
          animation="scale"
          size="lg"
          glassMorphism={true}
          overlayBlur="8px"
        >
          <VStack spacing={6} align="stretch">
            <Box>
              <Heading size="sm" mb={2}>
                Example Commands
              </Heading>
              <SimpleGrid columns={{ base: 1, md: 2 }} spacing={4}>
                <EnhancedCard variant="outlined" size="sm">
                  <Text fontSize="sm" fontWeight="medium">
                    &quot;Swap 0.1 ETH for USDC&quot;
                  </Text>
                </EnhancedCard>
                <EnhancedCard variant="outlined" size="sm">
                  <Text fontSize="sm" fontWeight="medium">
                    &quot;Bridge 100 USDC from Ethereum to Polygon&quot;
                  </Text>
                </EnhancedCard>
                <EnhancedCard variant="outlined" size="sm">
                  <Text fontSize="sm" fontWeight="medium">
                    &quot;Check my ETH balance&quot;
                  </Text>
                </EnhancedCard>
                <EnhancedCard variant="outlined" size="sm">
                  <Text fontSize="sm" fontWeight="medium">
                    &quot;Analyze my portfolio&quot;
                  </Text>
                </EnhancedCard>
                <EnhancedCard variant="outlined" size="sm">
                  <Text fontSize="sm" fontWeight="medium">
                    &quot;Tell me about Uniswap&quot;
                  </Text>
                </EnhancedCard>
                <EnhancedCard variant="outlined" size="sm">
                  <Text fontSize="sm" fontWeight="medium">
                    &quot;Send 0.01 ETH to vitalik.eth&quot;
                  </Text>
                </EnhancedCard>
              </SimpleGrid>
            </Box>

            <Divider />

            <Box>
              <Heading size="sm" mb={2}>
                Supported Features
              </Heading>
              <VStack align="stretch" spacing={2}>
                <HStack>
                  <Icon as={FaCheckCircle} color="green.500" />
                  <Text>Token swaps across multiple DEXs</Text>
                </HStack>
                <HStack>
                  <Icon as={FaCheckCircle} color="green.500" />
                  <Text>Cross-chain bridging via Axelar</Text>
                </HStack>
                <HStack>
                  <Icon as={FaCheckCircle} color="green.500" />
                  <Text>Portfolio analysis and tracking</Text>
                </HStack>
                <HStack>
                  <Icon as={FaCheckCircle} color="green.500" />
                  <Text>Token transfers and balance checking</Text>
                </HStack>
                <HStack>
                  <Icon as={FaCheckCircle} color="green.500" />
                  <Text>Protocol research and information</Text>
                </HStack>
              </VStack>
            </Box>

            <Divider />

            <Box>
              <Heading size="sm" mb={2}>
                Supported Networks
              </Heading>
              <SimpleGrid columns={{ base: 2, md: 3 }} spacing={2}>
                {Object.entries(SUPPORTED_CHAINS).map(([id, name]) => (
                  <HStack key={id}>
                    <Icon as={FaEthereum} color="blue.500" />
                    <Text fontSize="sm">{name}</Text>
                  </HStack>
                ))}
              </SimpleGrid>
            </Box>
          </VStack>
        </EnhancedModal>

        <EnhancedModal
          isOpen={isApiKeyModalOpen}
          onClose={() => setIsApiKeyModalOpen(false)}
          title="API Key Settings"
          variant="centered"
          animation="scale"
          size="md"
          glassMorphism={true}
          overlayBlur="8px"
        >
          <ApiKeyModal
            isOpen={isApiKeyModalOpen}
            onClose={() => setIsApiKeyModalOpen(false)}
          />
        </EnhancedModal>

        {/* Settings Drawer */}
        <EnhancedModal
          isOpen={isSettingsDrawerOpen}
          onClose={() => setIsSettingsDrawerOpen(false)}
          title="Settings"
          variant="drawer"
          placement="right"
          animation="slide"
          size="md"
          glassMorphism={true}
          overlayBlur="8px"
          headerIcon={<Icon as={FaCog} />}
        >
          <VStack spacing={6} align="stretch">
            <Box>
              <Heading size="sm" mb={3}>
                Appearance
              </Heading>
              <HStack justify="space-between">
                <Text>Theme</Text>
                <EnhancedButton
                  variant="outline"
                  size="sm"
                  leftIcon={colorMode === "light" ? <FaSun /> : <FaMoon />}
                  onClick={toggleColorMode}
                >
                  {colorMode === "light" ? "Light" : "Dark"}
                </EnhancedButton>
              </HStack>
            </Box>

            <Divider />

            <Box>
              <Heading size="sm" mb={3}>
                Portfolio Settings
              </Heading>
              <VStack align="stretch" spacing={3}>
                <HStack justify="space-between">
                  <Text>Enable Portfolio Analysis</Text>
                  <EnhancedButton
                    variant="switch"
                    isActive={portfolioSettings.enabled}
                    onClick={() => {
                      const newValue = !portfolioSettings.enabled;
                      setPortfolioSettings((prev) => ({
                        ...prev,
                        enabled: newValue,
                      }));
                      localStorage.setItem(
                        "snel_portfolio_enabled",
                        newValue.toString()
                      );
                    }}
                  />
                </HStack>
                <HStack justify="space-between">
                  <Text>Cache Portfolio Data</Text>
                  <EnhancedButton
                    variant="switch"
                    isActive={portfolioSettings.cacheEnabled}
                    onClick={() => {
                      setPortfolioSettings((prev) => ({
                        ...prev,
                        cacheEnabled: !prev.cacheEnabled,
                      }));
                    }}
                  />
                </HStack>
              </VStack>
            </Box>

            <Divider />

            <Box>
              <Heading size="sm" mb={3}>
                Advanced Settings
              </Heading>
              <AdvancedSettings
                axelarUnavailable={axelarUnavailable}
                onSettingsChange={setAdvancedSettings}
              />
            </Box>

            <Divider />

            <Box>
              <Heading size="sm" mb={3}>
                API Keys
              </Heading>
              <EnhancedButton
                variant="outline"
                size="sm"
                leftIcon={<FaKey />}
                onClick={() => {
                  setIsSettingsDrawerOpen(false);
                  setTimeout(() => setIsApiKeyModalOpen(true), 300);
                }}
                width="100%"
              >
                Configure API Keys
              </EnhancedButton>
            </Box>

            <Box pt={4}>
              <EnhancedButton
                variant="solid"
                colorScheme="blue"
                size="md"
                onClick={() => setIsSettingsDrawerOpen(false)}
                width="100%"
              >
                Save Settings
              </EnhancedButton>
            </Box>
          </VStack>
        </EnhancedModal>

        {/* Interactive Onboarding */}
        {showOnboarding && (
          <Portal>
            <Box
              position="fixed"
              top={0}
              left={0}
              right={0}
              bottom={0}
              bg="rgba(0, 0, 0, 0.7)"
              zIndex={1500}
              backdropFilter="blur(8px)"
            >
              <InteractiveOnboardingFinal
                onComplete={handleOnboardingComplete}
                onSkip={() => setShowOnboarding(false)}
              />
            </Box>
          </Portal>
        )}
      </Box>
    </motion.div>
  );
}

// Missing FaKey icon definition
const FaKey = (props: any) => (
  <Icon viewBox="0 0 512 512" {...props}>
    <path
      fill="currentColor"
      d="M512 176.001C512 273.203 433.202 352 336 352c-11.22 0-22.19-1.062-32.827-3.069l-24.012 27.014A23.999 23.999 0 0 1 261.223 384H224v40c0 13.255-10.745 24-24 24h-40v40c0 13.255-10.745 24-24 24H24c-13.255 0-24-10.745-24-24v-78.059c0-6.365 2.529-12.47 7.029-16.971l161.802-161.802C163.108 213.814 160 195.271 160 176 160 78.798 238.797.001 335.999 0 433.488-.001 512 78.511 512 176.001zM336 128c0 26.51 21.49 48 48 48s48-21.49 48-48-21.49-48-48-48-48 21.49-48 48z"
    ></path>
  </Icon>
);

// ---------------------------------------------------------------------------
// Default export at file end (per instructions)
// ---------------------------------------------------------------------------

export default EnhancedMainApp;

"use client";

import * as React from "react";
import { useState, useEffect, useRef } from "react";
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
  Button,
  Icon,
  SimpleGrid,
  Switch,
} from "@chakra-ui/react";
import {
  FaExchangeAlt,
  FaLink,
  FaWallet,
  FaCoins,
  FaChartPie,
  FaSearch,
  FaShieldAlt,
  FaBolt,
} from "react-icons/fa";
import {
  useAccount,
  usePublicClient,
  useWalletClient,
  useChainId,
} from "wagmi";
import { CommandInput } from "./CommandInput";
import { GMPCompatibleCommandResponse as CommandResponse } from "./GMPCompatibleCommandResponse";
import { WalletButton } from "./WalletButton";
import { ExternalLinkIcon, SettingsIcon, QuestionIcon } from "@chakra-ui/icons";
import { LogoModal } from "./LogoModal";
import { HelpModal } from "./HelpModal";
import { PaymentQuickActions } from "./PaymentQuickActions";
import { fetchUserProfile } from "../services/profileService";
import { SUPPORTED_CHAINS } from "../constants/chains";
import { ApiService } from "../services/apiService";
import { TransactionService } from "../services/transactionService";
import { MultiStepTransactionService } from "../services/multiStepTransactionService";
import { PortfolioService } from "../services/portfolioService";
import { PaymentHistoryService } from "../services/paymentHistoryService";
import { AddRecipientModal } from "./AddRecipientModal";
import { AddPaymentTemplateModal } from "./AddPaymentTemplateModal";
import { AdvancedSettings, AdvancedSettingsValues } from "./AdvancedSettings";
import {
  withAsyncRecursionGuard,
  recursionGuard,
} from "../utils/recursionGuard";
import { setupGlobalWalletErrorHandler } from "../utils/walletErrorHandler";
import { useGMPIntegration } from "../hooks/useGMPIntegration";
import { useWallet } from "../hooks/useWallet";
import {
  analyzeCommandSequence,
  generateBatchingSuggestion,
} from "../utils/commandSequenceAnalyzer";
import { parseCommand } from "../utils/commandParser";

// Import types
import {
  Response,
  ResponseContent,
  ResponseMetadata,
  TransactionData,
  SwapQuote,
} from "../types/responses";

// LINE-specific types
import { Platform } from "../utils/platformDetection";
import { LIFFProfile } from "../providers/LINEProvider";

// Use the imported Response type instead of local interfaces
type ResponseType = Response;

// Define props interface for MainApp to support LINE integration
interface MainAppProps {
  // LINE-specific props
  platform?: Platform;
  lineFeatures?: {
    isAvailable: boolean;
    canLogin: boolean;
    canShare: boolean;
    canConnectWallet: boolean;
    canExecuteTransactions: boolean;
  };
  lineProfile?: LIFFProfile | null;
  isLineLoggedIn?: boolean;

  // LINE-specific callbacks
  onLineLogin?: () => Promise<void>;
  onLineLogout?: () => Promise<void>;
  onLineShare?: (message: string) => Promise<void>;
  onLineClose?: () => void;
  onLineConnectWallet?: () => Promise<void>;
  onLineGetAddress?: () => Promise<string | null>;
  onLineExecuteTransaction?: (txData: any) => Promise<string>;
}

export default function MainApp(props: MainAppProps) {
  const toast = useToast();
  const { address, isConnected } = useAccount();
  const chainId = useChainId();
  const { data: walletClient } = useWalletClient();
  const publicClient = usePublicClient();

  // Destructure LINE props with defaults
  const {
    platform,
    lineFeatures,
    lineProfile,
    isLineLoggedIn,
    onLineLogin,
    onLineLogout,
    onLineShare,
    onLineClose,
    onLineConnectWallet,
    onLineGetAddress,
    onLineExecuteTransaction,
  } = props;

  // GMP Integration
  const { walletClient: gmppWalletClient } = useWallet();
  const { executeGMPTransaction } = useGMPIntegration({
    onTransactionStart: (transactionId) => {
      toast({
        title: "Cross-chain Transaction Started",
        description: `Transaction ${transactionId} is being processed`,
        status: "info",
        duration: 5000,
        isClosable: true,
      });
    },
    onTransactionComplete: (transactionId, result) => {
      toast({
        title: "Cross-chain Transaction Complete",
        description: `Transaction ${transactionId} completed successfully`,
        status: "success",
        duration: 5000,
        isClosable: true,
      });
    },
    onTransactionError: (transactionId, error) => {
      toast({
        title: "Cross-chain Transaction Failed",
        description: `Transaction ${transactionId} failed: ${error}`,
        status: "error",
        duration: 8000,
        isClosable: true,
      });
    },
  });

  // Initialize services with stable references
  const apiService = React.useMemo(() => new ApiService(), []);
  const portfolioService = React.useMemo(
    () => new PortfolioService(apiService),
    [apiService]
  );
  const paymentHistoryService = React.useMemo(
    () => new PaymentHistoryService(apiService),
    [apiService]
  );
  const transactionService = React.useMemo(
    () =>
      walletClient && publicClient && chainId
        ? new TransactionService(walletClient as any, publicClient as any, chainId)
        : null,
    [walletClient, publicClient, chainId]
  );

  const multiStepTransactionService = React.useMemo(
    () =>
      transactionService
        ? new MultiStepTransactionService(transactionService, apiService)
        : null,
    [transactionService, apiService]
  );

  const isResponseContent = (content: any): content is ResponseContent => {
    return typeof content === "object" && content !== null;
  };

  const [responses, setResponses] = useState<ResponseType[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isLogoModalOpen, setIsLogoModalOpen] = useState(false);
  const [isHelpModalOpen, setIsHelpModalOpen] = useState(false);
  const [isAddRecipientModalOpen, setIsAddRecipientModalOpen] = useState(false);
  const [isAddPaymentTemplateModalOpen, setIsAddPaymentTemplateModalOpen] =
    useState(false);
  const [userProfile, setUserProfile] = useState<any>(null);
  const responsesEndRef = useRef<HTMLDivElement>(null);
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
  const [showLandingScreen, setShowLandingScreen] = useState<boolean>(false);

  // Setup global error handlers on mount
  useEffect(() => {
    setupGlobalWalletErrorHandler();
  }, []);

  // Initialize or update welcome message based on wallet state
  useEffect(() => {
    const getWelcomeMessage = () => {
      if (!isConnected) {
        return "Good morning! Please connect your wallet to get started with multichain DeFi.";
      }

      if (!chainId || !(chainId in SUPPORTED_CHAINS)) {
        return "Please switch to a supported network to continue.";
      }

      const chainName = SUPPORTED_CHAINS[chainId as keyof typeof SUPPORTED_CHAINS];
      return `Good morning! How can I help you with DeFi today? You're connected to ${chainName}.`;
    };

    const welcomeMessage: ResponseType = {
      content: getWelcomeMessage(),
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
  }, [isConnected, chainId]);

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

  const scrollToBottom = () => {
    responsesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [responses]);

  const handleResponseAction = async (action: any) => {
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
        agentType: "default" as const,
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
    } else if (action.type === "add_recipient") {
      // Open the add recipient modal
      setIsAddRecipientModalOpen(true);
    } else if (action.type === "add_payment_template") {
      // Open the add payment template modal
      setIsAddPaymentTemplateModalOpen(true);
    } else if (action.type === "select_recipient") {
      // Handle recipient selection by pre-filling a send command
      const recipient = action.recipient;
      const sendCommand = `send [amount] ${recipient.name} (${recipient.address})`;

      // Add the command to the input field
      const timestamp = new Date().toISOString();
      const commandResponse = {
        content: sendCommand,
        timestamp,
        isCommand: true,
        status: "success" as const,
      };
      setResponses((prev) => [...prev, commandResponse]);
    }
  };

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
            content: { type: "portfolio_progress" } as any,
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
              undefined, // onProgress handled separately for portfolio
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
            const errorMessage =
              error instanceof Error ? error.message : "Analysis failed";
            console.log("Creating error response with message:", errorMessage);

            // Replace processing with error
            setResponses((prev) =>
              prev.map((r) =>
                r.status === "processing" && r.agentType === "agno"
                  ? {
                    content: {
                      message: errorMessage,
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
        } else if (
          /payment history|recent transfers|transfer history/i.test(
            command.toLowerCase()
          )
        ) {
          // Handle payment history command
          try {
            if (!address) {
              throw new Error("Wallet not connected");
            }

            const history = await paymentHistoryService.getPaymentHistory(
              address,
              chainId
            );

            const historyResponse: Response = {
              content: {
                message: `Here's your MNEE payment history:`,
                type: "payment_history",
                history: history && history.length > 0
                  ? history
                  : [],
              },
              timestamp: new Date().toISOString(),
              isCommand: false,
              status: "success" as const,
              agentType: "payment" as const,
            };

            setResponses((prev) => [...prev, historyResponse]);
          } catch (error) {
            console.error("Error fetching payment history:", error);
            const errorMessage =
              error instanceof Error
                ? error.message
                : "Failed to fetch payment history";

            const errorResponse: Response = {
              content: {
                message: errorMessage,
                type: "error",
              },
              timestamp: new Date().toISOString(),
              isCommand: false,
              status: "error" as const,
              agentType: "payment" as const,
            };

            setResponses((prev) => [...prev, errorResponse]);
          }
        } else if (
          /spending analytics|spending report/i.test(command.toLowerCase())
        ) {
          // Handle spending analytics command
          try {
            if (!address) {
              throw new Error("Wallet not connected");
            }

            const analytics = await paymentHistoryService.getSpendingAnalytics(
              address,
              chainId
            );

            const analyticsResponse: Response = {
              content: {
                message: `Here's your spending analytics:`,
                type: "spending_analytics",
                analytics: analytics,
              },
              timestamp: new Date().toISOString(),
              isCommand: false,
              status: "success" as const,
              agentType: "payment" as const,
            };

            setResponses((prev) => [...prev, analyticsResponse]);
          } catch (error) {
            console.error("Error fetching spending analytics:", error);
            const errorMessage =
              error instanceof Error
                ? error.message
                : "Failed to fetch spending analytics";

            const errorResponse: Response = {
              content: {
                message: errorMessage,
                type: "error",
              },
              timestamp: new Date().toISOString(),
              isCommand: false,
              status: "error" as const,
              agentType: "payment" as const,
            };

            setResponses((prev) => [...prev, errorResponse]);
          }
        } else if (
          /saved recipients|address book/i.test(command.toLowerCase())
        ) {
          // Handle recipients command
          try {
            if (!address) {
              throw new Error("Wallet not connected");
            }

            const recipients = await paymentHistoryService.getRecipients(
              address
            );

            const recipientsResponse: Response = {
              content: {
                message: `Here are your saved recipients:`,
                type: "recipients",
                recipients: recipients,
              },
              timestamp: new Date().toISOString(),
              isCommand: false,
              status: "success" as const,
              agentType: "payment" as const,
            };

            setResponses((prev) => [...prev, recipientsResponse]);
          } catch (error) {
            console.error("Error fetching recipients:", error);
            const errorMessage =
              error instanceof Error
                ? error.message
                : "Failed to fetch recipients";

            const errorResponse: Response = {
              content: {
                message: errorMessage,
                type: "error",
              },
              timestamp: new Date().toISOString(),
              isCommand: false,
              status: "error" as const,
              agentType: "payment" as const,
            };

            setResponses((prev) => [...prev, errorResponse]);
          }
        } else if (
          /payment templates|scheduled payments/i.test(command.toLowerCase())
        ) {
          // Handle payment templates command
          try {
            if (!address) {
              throw new Error("Wallet not connected");
            }

            const templates = await paymentHistoryService.getPaymentTemplates(
              address
            );

            const templatesResponse: Response = {
              content: {
                message: `Here are your payment templates:`,
                type: "payment_templates",
                templates: templates,
              },
              timestamp: new Date().toISOString(),
              isCommand: false,
              status: "success" as const,
              agentType: "payment" as const,
            };

            setResponses((prev) => [...prev, templatesResponse]);
          } catch (error) {
            console.error("Error fetching payment templates:", error);
            const errorMessage =
              error instanceof Error
                ? error.message
                : "Failed to fetch payment templates";

            const errorResponse: Response = {
              content: {
                message: errorMessage,
                type: "error",
              },
              timestamp: new Date().toISOString(),
              isCommand: false,
              status: "error" as const,
              agentType: "payment" as const,
            };

            setResponses((prev) => [...prev, errorResponse]);
          }
        } else if (
          /setup.*automated.*yield.*farming|yield.*farming|yield.*opportunities/i.test(command.toLowerCase())
        ) {
          // Handle yield farming command
          try {
            // Fetch yield opportunities from the research API
            const queryParams = new URLSearchParams({
              query: 'highest yield farming opportunities defi protocols',
              category: 'yield',
              max_results: '10'
            });
            const yieldResponse = await apiService.get(`/research/discover?${queryParams.toString()}`);

            // Mock yield opportunities structure (replace with actual API response)
            const yieldOpportunities = yieldResponse?.opportunities || [
              {
                protocol: "Aave V3",
                apy: "12.5%",
                tvl: "$2.1B",
                chain: "Ethereum",
                url: "https://aave.com",
                description: "Supply USDC to earn yield"
              },
              {
                protocol: "Compound V3",
                apy: "8.7%",
                tvl: "$1.8B",
                chain: "Base",
                url: "https://compound.finance",
                description: "Lend USDC for competitive rates"
              },
              {
                protocol: "Yearn Finance",
                apy: "15.2%",
                tvl: "$890M",
                chain: "Ethereum",
                url: "https://yearn.fi",
                description: "Automated yield farming vault"
              }
            ];

            const yieldFarmingResponse: Response = {
              content: {
                message: `🌾 Here are the best yield farming opportunities:`,
                type: "yield_opportunities",
                opportunities: yieldOpportunities,
              },
              timestamp: new Date().toISOString(),
              isCommand: false,
              status: "success" as const,
              agentType: "research" as const,
            };

            setResponses((prev) => [...prev, yieldFarmingResponse]);
          } catch (error) {
            console.error("Error fetching yield opportunities:", error);
            const errorMessage =
              error instanceof Error
                ? error.message
                : "Failed to fetch yield opportunities";

            const errorResponse: Response = {
              content: {
                message: errorMessage,
                type: "error",
              },
              timestamp: new Date().toISOString(),
              isCommand: false,
              status: "error" as const,
              agentType: "research" as const,
            };

            setResponses((prev) => [...prev, errorResponse]);
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

          // Ensure proper agentType and awaitingConfirmation mapping
          const mappedAgentType = response.agent_type || response.agentType;
          const mappedAwaitingConfirmation =
            response.awaiting_confirmation ?? response.awaitingConfirmation;

          // Regular handling for non-portfolio commands
          // Check for batching opportunities
          setResponses((prev) => {
            const allResponses = [
              ...prev,
              {
                ...response,
                agentType: mappedAgentType, // Use the mapped value
                awaitingConfirmation: mappedAwaitingConfirmation, // Use the mapped value
                timestamp: new Date().toISOString(),
                isCommand: false,
                status: "success",
              },
            ];

            // Check if we should suggest batching
            const commandResponses = allResponses.filter((r) => r.isCommand);
            if (commandResponses.length >= 2) {
              // Parse the last few commands to check for transfer patterns
              const recentCommands = commandResponses
                .slice(-3)
                .map((r) => parseCommand(r.content as string));
              const analysis = analyzeCommandSequence(recentCommands);
              const suggestion = generateBatchingSuggestion(analysis);

              if (suggestion) {
                // Add a suggestion response
                const suggestionResponse = {
                  content: {
                    message: suggestion,
                    type: "suggestion",
                    suggestionType: "batching",
                  },
                  timestamp: new Date().toISOString(),
                  isCommand: false,
                  status: "success",
                  agentType: "agno",
                };

                return [...allResponses, suggestionResponse];
              }
            }

            return allResponses;
          });
        }
      } catch (error) {
        console.error("Error processing command:", error);
        toast({
          title: "Error",
          description: "Failed to process command. Please try again.",
          status: "error",
          duration: 5000,
          isClosable: true,
        });
      }
      setIsLoading(false);
    },
    "handleCommand"
  );

  // Wrapper function for components that expect (command: string) => Promise<void>
  const handleCommandWrapper = async (command: string) => {
    await handleCommand(command);
  };

  // Reset any portfolio processing state when the component unmounts
  useEffect(() => {
    return () => {
      setPortfolioProcessingId(null);
      setIsRetryingPortfolio(false);
    };
  }, []);

  // GMP Transaction execution handler
  const handleGMPTransaction = async (transactionData: any) => {
    if (!gmppWalletClient || !isConnected) {
      toast({
        title: "Wallet Not Connected",
        description:
          "Please connect your wallet to execute cross-chain transactions",
        status: "warning",
        duration: 5000,
        isClosable: true,
      });
      return;
    }

    try {
      // Extract transaction ID from the response
      const transactionId =
        transactionData?.transactionId ||
        transactionData?.content?.transactionId ||
        transactionData?.id ||
        `gmp_${Date.now()}`;

      await executeGMPTransaction(transactionId, gmppWalletClient);
    } catch (error) {
      console.error("GMP transaction execution failed:", error);
      toast({
        title: "Transaction Failed",
        description:
          error instanceof Error
            ? error.message
            : "Failed to execute cross-chain transaction",
        status: "error",
        duration: 8000,
        isClosable: true,
      });
    }
  };

  return (
    <Box minH="100vh" bg="gray.50">
      <Container maxW="container.xl" py={4}>
        <VStack spacing={8} align="stretch">
          <Box>
            <Flex
              align="center"
              justify="space-between"
              w="100%"
              mb={4}
              flexDir={{ base: "column", sm: "row" }}
              gap={{ base: 2, sm: 4 }}
            >
              <Box cursor="pointer" onClick={() => setIsLogoModalOpen(true)}>
                <Image src="/icon.png" alt="Logo" width={40} height={40} />
              </Box>

              <Heading as="h1" size="lg" textAlign="center">
                SNEL
              </Heading>

              <HStack spacing={4}>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => setIsHelpModalOpen(true)}
                >
                  <Icon as={QuestionIcon} />
                </Button>
                {isConnected && (
                  !showLandingScreen ? (
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => setShowLandingScreen(true)}
                      title="Go to Home"
                    >
                      <Icon as={FaWallet} /> {/* Using wallet icon as a home-like icon */}
                    </Button>
                  ) : (
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => setShowLandingScreen(false)}
                      title="Back to Chat"
                    >
                      <Icon as={FaChartPie} /> {/* Using chart icon to go back to chat */}
                    </Button>
                  )
                )}
                <WalletButton />
              </HStack>
            </Flex>
          </Box>

          <Box flex={1}>
            {(!isConnected || showLandingScreen) ? (
              <VStack spacing={6} align="center" justify="center" py={8}>
                {/* Logo */}
                <Box position="relative" width="60px" height="60px">
                  <Image
                    src="/icon.png"
                    alt="SNEL Logo"
                    width={60}
                    height={60}
                    priority
                    style={{ objectFit: "contain" }}
                  />
                </Box>

                {/* Platform Capabilities */}
                <VStack spacing={4} align="center">
                  <SimpleGrid columns={3} spacing={4} maxW="400px">
                    <VStack
                      spacing={1}
                      align="center"
                      p={3}
                      borderRadius="md"
                      bg="gray.50"
                    >
                      <Icon as={FaExchangeAlt} color="blue.500" boxSize={4} />
                      <Text
                        fontSize="xs"
                        fontWeight="medium"
                        textAlign="center"
                      >
                        Token Transfers
                      </Text>
                    </VStack>
                    <VStack
                      spacing={1}
                      align="center"
                      p={3}
                      borderRadius="md"
                      bg="gray.50"
                    >
                      <Icon as={FaLink} color="blue.500" boxSize={4} />
                      <Text
                        fontSize="xs"
                        fontWeight="medium"
                        textAlign="center"
                      >
                        Cross-Chain Bridging
                      </Text>
                    </VStack>
                    <VStack
                      spacing={1}
                      align="center"
                      p={3}
                      borderRadius="md"
                      bg="gray.50"
                    >
                      <Icon as={FaWallet} color="blue.500" boxSize={4} />
                      <Text
                        fontSize="xs"
                        fontWeight="medium"
                        textAlign="center"
                      >
                        Balance Checking
                      </Text>
                    </VStack>
                    <VStack
                      spacing={1}
                      align="center"
                      p={3}
                      borderRadius="md"
                      bg="gray.50"
                    >
                      <Icon as={FaCoins} color="blue.500" boxSize={4} />
                      <Text
                        fontSize="xs"
                        fontWeight="medium"
                        textAlign="center"
                      >
                        Token Swaps
                      </Text>
                    </VStack>
                    <VStack
                      spacing={1}
                      align="center"
                      p={3}
                      borderRadius="md"
                      bg="gray.50"
                    >
                      <Icon as={FaChartPie} color="blue.500" boxSize={4} />
                      <Text
                        fontSize="xs"
                        fontWeight="medium"
                        textAlign="center"
                      >
                        Portfolio Analysis
                      </Text>
                    </VStack>
                    <VStack
                      spacing={1}
                      align="center"
                      p={3}
                      borderRadius="md"
                      bg="gray.50"
                    >
                      <Icon as={FaSearch} color="blue.500" boxSize={4} />
                      <Text
                        fontSize="xs"
                        fontWeight="medium"
                        textAlign="center"
                      >
                        Protocol Research
                      </Text>
                    </VStack>
                  </SimpleGrid>

                  {/* Premium & Privacy Features */}
                  <SimpleGrid
                    columns={3}
                    spacing={3}
                    maxW="600px"
                    mt={4}
                    pt={4}
                    borderTopWidth="1px"
                    borderTopColor="gray.200"
                    width="100%"
                  >
                    <VStack
                      spacing={1}
                      align="center"
                      p={3}
                      borderRadius="md"
                      bg="linear-gradient(135deg, rgba(244, 183, 40, 0.05) 0%, rgba(244, 183, 40, 0.02) 100%)"
                      border="1px solid"
                      borderColor="rgba(244, 183, 40, 0.2)"
                    >
                      <Icon as={FaCoins} color="yellow.600" boxSize={5} />
                      <Text
                        fontSize="xs"
                        fontWeight="semibold"
                        textAlign="center"
                        color="gray.700"
                      >
                        MNEE Commerce
                      </Text>
                      <Text fontSize="2xs" textAlign="center" color="gray.500">
                        Invoices & Payments
                      </Text>
                    </VStack>

                    <VStack
                      spacing={1}
                      align="center"
                      p={3}
                      borderRadius="md"
                      bg="linear-gradient(135deg, rgba(244, 183, 40, 0.05) 0%, rgba(244, 183, 40, 0.02) 100%)"
                      border="1px solid"
                      borderColor="rgba(244, 183, 40, 0.2)"
                    >
                      <Icon as={FaShieldAlt} color="yellow.600" boxSize={5} />
                      <Text
                        fontSize="xs"
                        fontWeight="semibold"
                        textAlign="center"
                        color="gray.700"
                      >
                        Privacy Bridge
                      </Text>
                      <Text fontSize="2xs" textAlign="center" color="gray.500">
                        Asset Shielding
                      </Text>
                    </VStack>

                    <VStack
                      spacing={1}
                      align="center"
                      p={3}
                      borderRadius="md"
                      bg="linear-gradient(135deg, rgba(138, 43, 226, 0.05) 0%, rgba(138, 43, 226, 0.02) 100%)"
                      border="1px solid"
                      borderColor="rgba(138, 43, 226, 0.2)"
                    >
                      <Icon as={FaBolt} color="purple.600" boxSize={5} />
                      <Text
                        fontSize="xs"
                        fontWeight="semibold"
                        textAlign="center"
                        color="gray.700"
                      >
                        X402 Automation
                      </Text>
                      <Text fontSize="2xs" textAlign="center" color="gray.500">
                        AI-Triggered Payments
                      </Text>
                    </VStack>
                  </SimpleGrid>

                  {/* Multichain Support Highlight */}
                  <VStack spacing={2} mt={4} p={3} bg="blue.50" borderRadius="md" border="1px solid" borderColor="blue.200">
                    <Text fontSize="sm" fontWeight="semibold" color="blue.700" textAlign="center">
                      🌐 Multichain DeFi Assistant
                    </Text>
                    <Text fontSize="xs" color="blue.600" textAlign="center">
                      19+ networks • AI-powered • Cross-chain bridging • X402 automation
                    </Text>
                  </VStack>

                  {/* Hint about help modal */}
                  <Text fontSize="xs" color="gray.500" textAlign="center">
                    Click ? above for specific commands <br />
                    Click ⚙️ above to configure API keys
                  </Text>
                  {/* Features Hint */}
                  <VStack spacing={2} mt={2}>
                    <HStack spacing={4} justify="center">
                      <Text fontSize="2xs" color="gray.500" textAlign="center">
                        💰 Try MNEE: &quot;pay $100 MNEE to merchant...&quot;
                      </Text>
                      <Text fontSize="2xs" color="gray.500" textAlign="center">
                        🛡️ Try Privacy: &quot;bridge 1 ETH to Zcash&quot;
                      </Text>
                    </HStack>
                    <HStack spacing={4} justify="center">
                      <Text fontSize="2xs" color="blue.600" textAlign="center">
                        🤖 Try X402: &quot;setup portfolio rebalancing with 50 USDC&quot;
                      </Text>
                      <Text fontSize="2xs" color="blue.600" textAlign="center">
                        ⚡ Try Swaps: &quot;swap $100 USDC for ETH on Base&quot;
                      </Text>
                    </HStack>
                  </VStack>

                </VStack>
              </VStack>
            ) : (
              <VStack spacing={4} align="stretch">
                {responses.map((response, index) => {
                  // Debug what's being passed to CommandResponse
                  if (
                    response.agentType === "bridge" ||
                    (response.content &&
                      typeof response.content === "object" &&
                      "message" in response.content &&
                      typeof (response.content as any).message === "string" &&
                      (response.content as any).message
                        .toLowerCase()
                        .includes("bridge"))
                  ) {
                    console.log(`Passing to CommandResponse[${index}]:`, {
                      agentType: response.agentType,
                      awaitingConfirmation: response.awaitingConfirmation,
                      hasTransaction: !!response.transaction,
                      contentMessage:
                        typeof response.content === "object" &&
                          "message" in response.content &&
                          typeof response.content.message === "string"
                          ? response.content.message
                          : null,
                    });
                  }

                  return (
                    <CommandResponse
                      key={index}
                      content={response.content}
                      timestamp={response.timestamp}
                      isCommand={response.isCommand}
                      status={response.status}
                      metadata={response.metadata}
                      agentType={response.agentType}
                      transaction={response.transaction}
                      awaitingConfirmation={response.awaitingConfirmation}
                      onActionClick={handleResponseAction}
                      onExecuteTransaction={handleGMPTransaction}
                    />
                  );
                })}
                <div ref={responsesEndRef} />
                <VStack spacing={4} align="stretch">
                  <PaymentQuickActions
                    onCommandSubmit={handleCommand}
                    isVisible={isConnected && chainId !== undefined}
                  />
                  <CommandInput
                    onSubmit={handleCommandWrapper}
                    isLoading={isLoading}
                  />
                  <AdvancedSettings
                    axelarUnavailable={axelarUnavailable}
                    onSettingsChange={setAdvancedSettings}
                  />
                  {/* Portfolio Settings - Simple Toggle */}
                  <Box
                    p={3}
                    bg="gray.50"
                    borderRadius="md"
                    border="1px solid"
                    borderColor="gray.200"
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
                      <Switch
                        isChecked={portfolioSettings.enabled}
                        onChange={(e) => {
                          setPortfolioSettings((prev) => ({
                            ...prev,
                            enabled: e.target.checked,
                          }));
                          localStorage.setItem(
                            "snel_portfolio_enabled",
                            e.target.checked.toString()
                          );
                        }}
                        colorScheme="blue"
                      />
                    </HStack>
                  </Box>
                </VStack>
              </VStack>
            )}
          </Box>
        </VStack>
      </Container>

      <LogoModal
        isOpen={isLogoModalOpen}
        onClose={() => setIsLogoModalOpen(false)}
      />
      <HelpModal
        isOpen={isHelpModalOpen}
        onClose={() => setIsHelpModalOpen(false)}
      />
      <AddRecipientModal
        isOpen={isAddRecipientModalOpen}
        onClose={() => setIsAddRecipientModalOpen(false)}
        onSave={async (recipient) => {
          if (!address) {
            throw new Error("Wallet not connected");
          }
          await paymentHistoryService.saveRecipient(address, recipient);
          // Refresh the recipient list by triggering a new command
          handleCommand("show my saved recipients");
        }}
        chainId={chainId}
      />
      <AddPaymentTemplateModal
        isOpen={isAddPaymentTemplateModalOpen}
        onClose={() => setIsAddPaymentTemplateModalOpen(false)}
        onSave={async (template) => {
          if (!address) {
            throw new Error("Wallet not connected");
          }
          await paymentHistoryService.createPaymentTemplate(address, template);
          // Refresh the template list by triggering a new command
          handleCommand("show my payment templates");
        }}
        chainId={chainId}
      />
    </Box>
  );
}

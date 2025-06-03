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
} from "@chakra-ui/react";
import {
  FaExchangeAlt,
  FaLink,
  FaWallet,
  FaCoins,
  FaChartPie,
  FaSearch,
} from "react-icons/fa";
import {
  useAccount,
  usePublicClient,
  useWalletClient,
  useChainId,
} from "wagmi";
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
    | "agno";
  requires_selection?: boolean;
  all_quotes?: any[];
  type?: string;
  confirmation_type?: string;
  pendingCommand?: string;
  transaction?: any;
  summary?: string;
  fullAnalysis?: string;
}

export default function MainApp() {
  const toast = useToast();
  const { address, isConnected } = useAccount();
  const chainId = useChainId();
  const { data: walletClient } = useWalletClient();
  const publicClient = usePublicClient();

  // Initialize services
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

  const isResponseContent = (content: any): content is ResponseContent => {
    return typeof content === "object" && content !== null;
  };

  const [responses, setResponses] = useState<ResponseType[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isLogoModalOpen, setIsLogoModalOpen] = useState(false);
  const [isHelpModalOpen, setIsHelpModalOpen] = useState(false);
  const [isApiKeyModalOpen, setIsApiKeyModalOpen] = useState(false);
  const [userProfile, setUserProfile] = useState<any>(null);
  const responsesEndRef = useRef<HTMLDivElement>(null);
  const [userId, setUserId] = useState<string>("");
  const [portfolioProcessingId, setPortfolioProcessingId] = useState<
    string | null
  >(null);
  const [isRetryingPortfolio, setIsRetryingPortfolio] =
    useState<boolean>(false);

  // Initialize or update welcome message based on wallet state
  useEffect(() => {
    const welcomeMessage: ResponseType = {
      content: isConnected
        ? chainId && chainId in SUPPORTED_CHAINS
          ? `Good morning! How can I help you with crypto today? You're connected to ${
              SUPPORTED_CHAINS[chainId as keyof typeof SUPPORTED_CHAINS]
            }.`
          : "Please switch to a supported network to continue."
        : "Good morning! Please connect your wallet to get started.",
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

  const scrollToBottom = () => {
    responsesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [responses]);

  const handlePortfolioAction = async (action: any) => {
    if (action.type === "retry") {
      setIsRetryingPortfolio(true);
      try {
        await handleCommand("analyze my portfolio", true);
      } finally {
        setIsRetryingPortfolio(false);
      }
    }
  };

  const handleCommand = async (
    command: string | undefined,
    isRetry: boolean = false
  ) => {
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
            userProfile?.name
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
          userProfile?.name
        );

        // Debug logging for bridge and transfer commands
        if (command.toLowerCase().includes("bridge")) {
          console.log("Bridge command API response:", response);
          console.log("Response agentType:", response.agentType);
          console.log("Response transaction:", response.transaction);
        }

        if (command.toLowerCase().includes("transfer")) {
          console.log("Transfer command API response:", response);
          console.log("Response agent_type:", response.agent_type);
          console.log("Response agentType:", response.agentType);
          console.log("Response transaction:", response.transaction);
          console.log("Response content:", response.content);
          console.log(
            "Response awaiting_confirmation:",
            response.awaiting_confirmation
          );
          console.log(
            "Mapped agentType will be:",
            response.agent_type || response.agentType
          );
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
      });
    }
    setIsLoading(false);
  };

  // Reset any portfolio processing state when the component unmounts
  useEffect(() => {
    return () => {
      setPortfolioProcessingId(null);
      setIsRetryingPortfolio(false);
    };
  }, []);

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
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => setIsApiKeyModalOpen(true)}
                >
                  <Icon as={SettingsIcon} />
                </Button>
                <WalletButton />
              </HStack>
            </Flex>
          </Box>

          <Box flex={1}>
            {!isConnected ? (
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

                  {/* Hint about help modal */}
                  <Text fontSize="xs" color="gray.500" textAlign="center">
                    Click ? above for specific commands <br />
                    Click ⚙️ above to configure API keys
                  </Text>
                </VStack>

                {/* Connect Wallet Button */}
                <WalletButton />
              </VStack>
            ) : (
              <VStack spacing={4} align="stretch">
                {responses.map((response, index) => (
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
                    onActionClick={handlePortfolioAction}
                  />
                ))}
                <div ref={responsesEndRef} />
                <VStack spacing={4} align="stretch">
                  <CommandInput
                    onSubmit={handleCommand}
                    isLoading={isLoading}
                  />
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
      <ApiKeyModal
        isOpen={isApiKeyModalOpen}
        onClose={() => setIsApiKeyModalOpen(false)}
      />
    </Box>
  );
}

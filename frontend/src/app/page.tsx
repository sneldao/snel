"use client";

import * as React from "react";
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
  Link,
  Button,
  Icon,
} from "@chakra-ui/react";
import {
  useAccount,
  usePublicClient,
  useWalletClient,
  useChainId,
} from "wagmi";
import { CommandInput } from "../components/CommandInput";
import { CommandResponse } from "../components/CommandResponse";
import { WalletButton } from "../components/WalletButton";
import { ExternalLinkIcon, SettingsIcon, QuestionIcon } from "@chakra-ui/icons";
import { ApiKeyModal } from "../components/ApiKeyModal";
import { LogoModal } from "../components/LogoModal";
import { HelpModal } from "../components/HelpModal";
import { fetchUserProfile, getDisplayName } from "../services/profileService";
import { useState, useEffect, useRef } from "react";
import { Response } from "../types/responses";
import { SUPPORTED_CHAINS } from "../constants/chains";
import { ApiService } from "../services/apiService";
import { TransactionService } from "../services/transactionService";
import { DCAService } from "../services/dcaService";

export default function Home() {
  const toast = useToast();
  const { address, isConnected } = useAccount();
  const chainId = useChainId();
  const { data: walletClient } = useWalletClient();
  const publicClient = usePublicClient();

  // Initialize services
  const apiService = React.useMemo(() => new ApiService(), []);
  const transactionService = React.useMemo(
    () =>
      walletClient && publicClient && chainId
        ? new TransactionService(walletClient, publicClient, chainId)
        : null,
    [walletClient, publicClient, chainId]
  );
  const dcaService = React.useMemo(
    () => (chainId ? new DCAService(chainId) : null),
    [chainId]
  );

  interface ResponseContent {
    type?: string;
    confirmation_type?: string;
    pendingCommand?: string;
    transaction?: any;
    [key: string]: any;
  }

  interface Response {
    content: string | ResponseContent;
    timestamp: string;
    isCommand: boolean;
    status?: "pending" | "processing" | "success" | "error";
    metadata?: any;
    awaitingConfirmation?: boolean;
    agentType?: "default" | "swap" | "dca" | "brian";
    requires_selection?: boolean;
    all_quotes?: any[];
    type?: string;
    confirmation_type?: string;
    pendingCommand?: string;
    transaction?: any;
  }

  const isResponseContent = (content: any): content is ResponseContent => {
    return typeof content === "object" && content !== null;
  };

  const [responses, setResponses] = useState<Response[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isLogoModalOpen, setIsLogoModalOpen] = useState(false);
  const [isHelpModalOpen, setIsHelpModalOpen] = useState(false);
  const [isApiKeyModalOpen, setIsApiKeyModalOpen] = useState(false);
  const [userProfile, setUserProfile] = useState<any>(null);
  const responsesEndRef = useRef<HTMLDivElement>(null);
  const [userId, setUserId] = useState<string>("");

  // Initialize or update welcome message based on wallet state
  useEffect(() => {
    const welcomeMessage: Response = {
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

  const handleCommand = async (command: string | undefined) => {
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
      setResponses((prev) => [
        ...prev,
        {
          content: command,
          timestamp,
          isCommand: true,
          status: "pending",
        },
      ]);

      // Process command with wallet info
      const response = await apiService.processCommand(
        command,
        address, // Pass wallet address
        chainId, // Pass chain ID
        userProfile?.name // Pass user name if available
      );

      // Add response
      setResponses((prev) => [
        ...prev,
        {
          ...response,
          timestamp: new Date().toISOString(),
          isCommand: false,
          status: "success",
        },
      ]);
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
              <Alert
                status="warning"
                variant="subtle"
                flexDirection="column"
                alignItems="center"
                justifyContent="center"
                textAlign="center"
                height="200px"
              >
                <AlertIcon boxSize="40px" mr={0} />
                <Box mt={4}>
                  <AlertTitle mb={1}>Connect Your Wallet</AlertTitle>
                  <AlertDescription maxWidth="sm">
                    Please connect your wallet to use Snel.
                  </AlertDescription>
                </Box>
              </Alert>
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

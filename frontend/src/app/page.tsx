"use client";

import * as React from "react";
import {
  Box,
  Container,
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
import { ExternalLinkIcon, SettingsIcon } from "@chakra-ui/icons";
import { ApiKeyModal } from "../components/ApiKeyModal";

type Response = {
  content: string;
  timestamp: string;
  isCommand: boolean;
  pendingCommand?: string;
  awaitingConfirmation?: boolean;
  status?: "pending" | "processing" | "success" | "error";
};

type TransactionData = {
  to: string;
  data: string;
  value: string;
  chainId: number;
  method: string;
  gasLimit: string;
  gasPrice?: string;
  maxFeePerGas?: string;
  maxPriorityFeePerGas?: string;
  needs_approval?: boolean;
  token_to_approve?: string;
  spender?: string;
  pending_command?: string;
};

// Add supported chains constant
const SUPPORTED_CHAINS = {
  1: "Ethereum",
  8453: "Base",
  42161: "Arbitrum",
  10: "Optimism",
  137: "Polygon",
  43114: "Avalanche",
  534352: "Scroll",
} as const;

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function Home() {
  const [responses, setResponses] = React.useState<Response[]>([]);
  const [isLoading, setIsLoading] = React.useState(false);
  const { address, isConnected } = useAccount();
  const chainId = useChainId();
  const publicClient = usePublicClient();
  const { data: walletClient } = useWalletClient();
  const toast = useToast();
  const responsesEndRef = React.useRef<HTMLDivElement>(null);
  const [isApiKeyModalOpen, setIsApiKeyModalOpen] = React.useState(false);

  // Add chain change effect
  React.useEffect(() => {
    if (chainId) {
      const isSupported = chainId in SUPPORTED_CHAINS;
      // Only clear pending transactions if switching to an unsupported chain
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

  const scrollToBottom = () => {
    responsesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  React.useEffect(() => {
    scrollToBottom();
  }, [responses]);

  const getBlockExplorerLink = (hash: string) => {
    if (!chainId) return `https://basescan.org/tx/${hash}`;

    const explorers = {
      1: `https://etherscan.io/tx/${hash}`,
      8453: `https://basescan.org/tx/${hash}`,
      42161: `https://arbiscan.io/tx/${hash}`,
      10: `https://optimistic.etherscan.io/tx/${hash}`,
      137: `https://polygonscan.com/tx/${hash}`,
      43114: `https://snowtrace.io/tx/${hash}`,
      534352: `https://scrollscan.com/tx/${hash}`,
    };

    return (
      explorers[chainId as keyof typeof explorers] ||
      `https://basescan.org/tx/${hash}`
    );
  };

  const getApiKeys = () => {
    if (typeof window === "undefined") return {};
    return {
      openaiKey: localStorage.getItem("openai_api_key") || "",
      alchemyKey: localStorage.getItem("alchemy_api_key") || "",
      coingeckoKey: localStorage.getItem("coingecko_api_key") || "",
    };
  };

  const getApiHeaders = () => {
    const { openaiKey, alchemyKey, coingeckoKey } = getApiKeys();
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    };

    if (openaiKey) headers["X-OpenAI-Key"] = openaiKey;
    if (alchemyKey) headers["X-Alchemy-Key"] = alchemyKey;
    if (coingeckoKey) headers["X-CoinGecko-Key"] = coingeckoKey;

    return headers;
  };

  const executeTransaction = async (txData: TransactionData) => {
    if (!walletClient) {
      throw new Error("Wallet not connected");
    }

    try {
      // If approval is needed, handle it first
      if (txData.needs_approval && txData.token_to_approve && txData.spender) {
        setResponses((prev) => [
          ...prev,
          {
            content: "Please approve USDC spending for the swap...",
            timestamp: new Date().toLocaleTimeString(),
            isCommand: false,
            status: "processing",
          },
        ]);

        const approveData = {
          to: txData.token_to_approve as `0x${string}`,
          data: txData.data as `0x${string}`,
          value: BigInt(0),
          chainId: txData.chainId,
          gas: BigInt(100000),
        };

        const approveHash = await walletClient.sendTransaction(approveData);
        const approveReceipt = await publicClient?.waitForTransactionReceipt({
          hash: approveHash,
        });

        if (!approveReceipt?.status) {
          throw new Error("Approval transaction failed");
        }

        setResponses((prev) => [
          ...prev,
          {
            content: "USDC approved successfully! Proceeding with swap...",
            timestamp: new Date().toLocaleTimeString(),
            isCommand: false,
            status: "success",
          },
        ]);

        // Retry the original transaction after approval
        if (txData.pending_command) {
          const response = await fetch(`${API_URL}/api/execute-transaction`, {
            method: "POST",
            headers: getApiHeaders(),
            body: JSON.stringify({
              command: txData.pending_command,
              wallet_address: address,
              chain_id: chainId,
            }),
          });

          if (!response.ok) {
            throw new Error(
              `Failed to execute swap after approval: ${await response.text()}`
            );
          }

          const swapData = await response.json();
          return executeTransaction(swapData); // Execute the swap transaction
        }
      }

      // Execute the main transaction
      const transaction = {
        to: txData.to as `0x${string}`,
        data: txData.data as `0x${string}`,
        value: BigInt(txData.value),
        chainId: txData.chainId,
        gas: BigInt(txData.gasLimit),
      };

      const hash = await walletClient.sendTransaction(transaction);

      setResponses((prev) => [
        ...prev.filter((r) => !r.status?.includes("processing")),
        {
          content: `Transaction submitted!\nView on block explorer:\n${getBlockExplorerLink(
            hash
          )}`,
          timestamp: new Date().toLocaleTimeString(),
          isCommand: false,
          status: "processing",
        },
      ]);

      const receipt = await publicClient?.waitForTransactionReceipt({
        hash,
      });

      if (!receipt) {
        throw new Error("Failed to get transaction receipt");
      }

      const isSuccess = Boolean(receipt.status);

      setResponses((prev) => [
        ...prev.filter((r) => !r.status?.includes("processing")),
        {
          content: isSuccess
            ? `Transaction completed successfully! 🎉\nView on block explorer:\n${getBlockExplorerLink(
                hash
              )}`
            : "Transaction failed. Please try again.",
          timestamp: new Date().toLocaleTimeString(),
          isCommand: false,
          status: isSuccess ? "success" : "error",
        },
      ]);

      return hash;
    } catch (error) {
      console.error("Transaction error:", error);
      let errorMessage = "Transaction failed";

      if (error instanceof Error) {
        if (error.message.includes("user rejected")) {
          errorMessage = "Transaction was cancelled";
        } else if (error.message.includes("insufficient funds")) {
          errorMessage = "Insufficient funds for transaction";
        } else if (error.message.includes("TRANSFER_FROM_FAILED")) {
          errorMessage =
            "Failed to transfer USDC. Please make sure you have enough USDC and have approved the swap.";
        } else {
          errorMessage = error.message;
        }
      }

      setResponses((prev) => [
        ...prev.filter((r) => !r.status?.includes("processing")),
        {
          content: `Transaction failed: ${errorMessage}`,
          timestamp: new Date().toLocaleTimeString(),
          isCommand: false,
          status: "error",
        },
      ]);

      throw error;
    }
  };

  const processCommand = async (command: string) => {
    if (
      !isConnected &&
      !command.toLowerCase().startsWith("what") &&
      !command.toLowerCase().startsWith("how")
    ) {
      toast({
        title: "Wallet not connected",
        description: "Please connect your wallet to execute transactions",
        status: "warning",
        duration: 5000,
      });
      return;
    }

    if (!chainId) {
      toast({
        title: "Chain not detected",
        description:
          "Please make sure your wallet is connected to a supported network",
        status: "warning",
        duration: 5000,
      });
      return;
    }

    const isSwapCommand = command.toLowerCase().includes("swap");
    if (isSwapCommand && !(chainId in SUPPORTED_CHAINS)) {
      toast({
        title: "Unsupported Network",
        description: `Please switch to a supported network: ${Object.values(
          SUPPORTED_CHAINS
        ).join(", ")}`,
        status: "warning",
        duration: 5000,
      });
      return;
    }

    setIsLoading(true);
    try {
      const isConfirmation = /^(yes|confirm|no|cancel)$/i.test(command.trim());

      if (isConfirmation) {
        const pendingResponse = responses.find((r) => r.awaitingConfirmation);
        if (!pendingResponse?.pendingCommand) {
          throw new Error("No pending command found");
        }

        // Add confirmation response
        setResponses((prev) => [
          ...prev,
          {
            content: command,
            timestamp: new Date().toLocaleTimeString(),
            isCommand: true,
            status: "success",
          },
        ]);

        const shouldExecute = /^(yes|confirm)$/i.test(command.trim());
        if (shouldExecute) {
          try {
            const response = await fetch(`${API_URL}/api/execute-transaction`, {
              method: "POST",
              headers: getApiHeaders(),
              body: JSON.stringify({
                command: pendingResponse.pendingCommand,
                wallet_address: address,
                chain_id: chainId,
              }),
            });

            const data = await response.json();
            if (!response.ok) {
              throw new Error(data.detail || "Failed to prepare transaction");
            }

            // Clear the pending command before executing the transaction
            setResponses((prev) =>
              prev.map((r) =>
                r.awaitingConfirmation
                  ? { ...r, awaitingConfirmation: false }
                  : r
              )
            );

            await executeTransaction({
              to: data.to,
              data: data.data,
              value: data.value,
              chainId: chainId,
              method: data.method,
              gasLimit: data.gas_limit,
              gasPrice: data.gas_price,
              maxFeePerGas: data.max_fee_per_gas,
              maxPriorityFeePerGas: data.max_priority_fee_per_gas,
              needs_approval: data.needs_approval,
              token_to_approve: data.token_to_approve,
              spender: data.spender,
              pending_command: data.pending_command,
            });
          } catch (error) {
            console.error("Transaction error:", error);
            setResponses((prev) => [
              ...prev,
              {
                content: `Transaction failed: ${
                  error instanceof Error ? error.message : "Unknown error"
                }`,
                timestamp: new Date().toLocaleTimeString(),
                isCommand: false,
                status: "error",
              },
            ]);
          }
        } else {
          // Handle cancellation
          setResponses((prev) => [
            ...prev.map((r) =>
              r.awaitingConfirmation ? { ...r, awaitingConfirmation: false } : r
            ),
            {
              content: "Transaction cancelled.",
              timestamp: new Date().toLocaleTimeString(),
              isCommand: false,
              status: "error",
            },
          ]);
        }
        return;
      }

      const response = await fetch(`${API_URL}/api/process-command`, {
        method: "POST",
        headers: getApiHeaders(),
        body: JSON.stringify({
          content: command,
          creator_name: "@user",
          creator_id: 1,
          chain_id: chainId,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Failed to process command");
      }

      const isQuestion =
        command.toLowerCase().startsWith("what") ||
        command.toLowerCase().startsWith("how");

      setResponses((prev) => [
        ...prev,
        {
          content: command,
          timestamp: new Date().toLocaleTimeString(),
          isCommand: true,
          status: "success",
        },
        {
          content: data.content,
          timestamp: new Date().toLocaleTimeString(),
          isCommand: !isQuestion,
          pendingCommand: data.pending_command,
          awaitingConfirmation: !isQuestion && data.content !== "None",
          status: !isQuestion ? "pending" : "success",
        },
      ]);
    } catch (error) {
      console.error("Error:", error);
      setResponses((prev) => [
        ...prev,
        {
          content: command,
          timestamp: new Date().toLocaleTimeString(),
          isCommand: true,
          status: "error",
        },
        {
          content:
            error instanceof Error
              ? `Sorry, I encountered an error: ${error.message}. Please make sure the backend server is running at ${API_URL}`
              : "An unknown error occurred. Please try again.",
          timestamp: new Date().toLocaleTimeString(),
          isCommand: false,
          status: "error",
        },
      ]);

      toast({
        title: "Error",
        description:
          error instanceof Error
            ? error.message
            : "Failed to process command. Please try again.",
        status: "error",
        duration: 5000,
        isClosable: true,
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmit = async (command: string) => {
    await processCommand(command);
  };

  return (
    <Box
      minH="100vh"
      bg="gray.50"
      py={{ base: 4, sm: 10 }}
      pb={{ base: 16, sm: 20 }}
    >
      <Container maxW="container.md" px={{ base: 2, sm: 4 }}>
        <VStack spacing={{ base: 4, sm: 8 }}>
          <Box textAlign="center" w="100%">
            <HStack
              justify="space-between"
              w="100%"
              mb={4}
              flexDir={{ base: "column", sm: "row" }}
              spacing={{ base: 2, sm: 4 }}
            >
              <Heading size={{ base: "lg", sm: "xl" }}>Pointless</Heading>
              <HStack spacing={{ base: 2, sm: 4 }}>
                <Button
                  size="sm"
                  variant="outline"
                  colorScheme="gray"
                  onClick={() => setIsApiKeyModalOpen(true)}
                  leftIcon={<Icon as={SettingsIcon} />}
                >
                  API Keys
                </Button>
                <WalletButton />
              </HStack>
            </HStack>
            <Text color="gray.600" fontSize={{ base: "md", sm: "lg" }}>
              Your friendly crypto command interpreter
            </Text>
            <Text color="gray.500" fontSize={{ base: "xs", sm: "sm" }} mt={2}>
              Ask me to swap tokens, send crypto, or answer questions about
              crypto!
            </Text>
          </Box>

          {!isConnected && (
            <Alert
              status="warning"
              borderRadius="md"
              fontSize={{ base: "sm", sm: "md" }}
            >
              <AlertIcon />
              <Box>
                <AlertTitle>Wallet not connected!</AlertTitle>
                <AlertDescription>
                  Please connect your wallet to execute transactions. You can
                  still ask questions without connecting.
                </AlertDescription>
              </Box>
            </Alert>
          )}

          {responses.length === 0 ? (
            <Alert
              status="info"
              borderRadius="md"
              fontSize={{ base: "sm", sm: "md" }}
            >
              <AlertIcon />
              <Box>
                <AlertTitle>Welcome to Pointless!</AlertTitle>
                <AlertDescription>
                  Try asking me to swap some tokens or check crypto prices.
                  Click the help icon above for example commands.
                </AlertDescription>
              </Box>
            </Alert>
          ) : (
            <VStack
              spacing={{ base: 2, sm: 4 }}
              w="100%"
              align="stretch"
              mb={{ base: 4, sm: 8 }}
            >
              {responses.map((response, index) => (
                <CommandResponse
                  key={`response-${index}`}
                  content={response.content}
                  timestamp={response.timestamp}
                  isCommand={response.isCommand}
                  status={response.status}
                  awaitingConfirmation={response.awaitingConfirmation}
                />
              ))}
              <div ref={responsesEndRef} />
            </VStack>
          )}

          <CommandInput onSubmit={handleSubmit} isLoading={isLoading} />

          <ApiKeyModal
            isOpen={isApiKeyModalOpen}
            onClose={() => setIsApiKeyModalOpen(false)}
          />
        </VStack>
      </Container>
    </Box>
  );
}

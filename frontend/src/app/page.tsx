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
} from "@chakra-ui/react";
import { useAccount, usePublicClient, useWalletClient } from "wagmi";
import { CommandInput } from "../components/CommandInput";
import { CommandResponse } from "../components/CommandResponse";
import { WalletButton } from "../components/WalletButton";
import { ExternalLinkIcon } from "@chakra-ui/icons";

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
};

export default function Home() {
  const [responses, setResponses] = React.useState<Response[]>([]);
  const [isLoading, setIsLoading] = React.useState(false);
  const { address, isConnected, chain } = useAccount();
  const publicClient = usePublicClient();
  const { data: walletClient } = useWalletClient();
  const toast = useToast();
  const responsesEndRef = React.useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    responsesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  React.useEffect(() => {
    scrollToBottom();
  }, [responses]);

  const getBlockExplorerLink = (hash: string) => {
    if (!chain) return `https://basescan.org/tx/${hash}`;

    const explorers = {
      1: `https://etherscan.io/tx/${hash}`,
      8453: `https://basescan.org/tx/${hash}`,
      42161: `https://arbiscan.io/tx/${hash}`,
      10: `https://optimistic.etherscan.io/tx/${hash}`,
      137: `https://polygonscan.com/tx/${hash}`,
      43114: `https://snowtrace.io/tx/${hash}`,
    };

    return (
      explorers[chain.id as keyof typeof explorers] ||
      `https://basescan.org/tx/${hash}`
    );
  };

  const executeTransaction = async (txData: TransactionData) => {
    if (!walletClient) {
      throw new Error("Wallet not connected");
    }

    try {
      // Prepare the transaction
      const transaction = {
        to: txData.to as `0x${string}`,
        data: txData.data as `0x${string}`,
        value: BigInt(txData.value),
        chainId: txData.chainId,
        gas: BigInt(txData.gasLimit),
      };

      // Send the transaction
      const hash = await walletClient.sendTransaction(transaction);

      // Only show one processing state
      setResponses((prev) => [
        ...prev.filter((r) => !r.status?.includes("processing")), // Remove any existing processing states
        {
          content: `Transaction submitted!\nView on block explorer:\n${getBlockExplorerLink(
            hash
          )}`,
          timestamp: new Date().toLocaleTimeString(),
          isCommand: false,
          status: "processing",
        },
      ]);

      // Wait for the transaction to be mined
      const receipt = await publicClient?.waitForTransactionReceipt({
        hash,
      });

      if (!receipt) {
        throw new Error("Failed to get transaction receipt");
      }

      // Check if the transaction was successful
      const isSuccess = Boolean(receipt.status);

      setResponses((prev) => [
        ...prev.filter((r) => !r.status?.includes("processing")), // Remove processing state
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
        // Handle specific error types
        if (error.message.includes("user rejected")) {
          errorMessage = "Transaction was rejected by the user";
        } else if (error.message.includes("insufficient funds")) {
          errorMessage = "Insufficient funds for transaction";
        } else {
          errorMessage = error.message;
        }
      }

      setResponses((prev) => [
        ...prev.filter((r) => !r.status?.includes("processing")), // Remove processing state
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

    if (!chain) {
      toast({
        title: "Chain not detected",
        description:
          "Please make sure your wallet is connected to a supported network",
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
        if (!pendingResponse) {
          setResponses((prev) => [
            ...prev,
            {
              content:
                "I don't see any pending commands to confirm. Try sending a new command.",
              timestamp: new Date().toLocaleTimeString(),
              isCommand: false,
              status: "error",
            },
          ]);
          return;
        }

        const shouldExecute = /^(yes|confirm)$/i.test(command.trim());
        if (shouldExecute) {
          setResponses((prev) => [
            ...prev,
            {
              content: command,
              timestamp: new Date().toLocaleTimeString(),
              isCommand: true,
              status: "success",
            },
          ]);

          try {
            // Use the normalized pending command from the response
            const pendingCommand = pendingResponse.pendingCommand;
            if (!pendingCommand) {
              throw new Error("No pending command found");
            }

            const response = await fetch(
              "http://localhost:8000/api/execute-transaction",
              {
                method: "POST",
                headers: {
                  "Content-Type": "application/json",
                },
                body: JSON.stringify({
                  command: pendingCommand,
                  wallet_address: address,
                  chain_id: chain.id,
                }),
              }
            );

            const data = await response.json();

            if (!response.ok) {
              throw new Error(data.detail || "Failed to prepare transaction");
            }

            // Execute the transaction with the wallet
            await executeTransaction({
              to: data.to,
              data: data.data,
              value: data.value,
              chainId: chain.id,
              method: data.method,
              gasLimit: data.gas_limit,
              gasPrice: data.gas_price,
              maxFeePerGas: data.max_fee_per_gas,
              maxPriorityFeePerGas: data.max_priority_fee_per_gas,
            });
          } catch (error) {
            console.error("Transaction error:", error);
            setResponses((prev) => [
              ...prev,
              {
                content: `Transaction failed: ${
                  error instanceof Error ? error.message : "Unknown error"
                }. Make sure your wallet is connected to a supported network.`,
                timestamp: new Date().toLocaleTimeString(),
                isCommand: false,
                status: "error",
              },
            ]);
          }
        } else {
          setResponses((prev) => [
            ...prev,
            {
              content: command,
              timestamp: new Date().toLocaleTimeString(),
              isCommand: true,
              status: "error",
            },
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

      const response = await fetch(
        "http://localhost:8000/api/process-command",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            content: command,
            creator_name: "@user",
            creator_id: 1,
          }),
        }
      );

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
          pendingCommand: data.pending_command, // Use the normalized command from the backend
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
              ? `Sorry, I encountered an error: ${error.message}. Please make sure the backend server is running at http://localhost:8000`
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
    <Box minH="100vh" bg="gray.50">
      <Container maxW="container.md" py={8}>
        <VStack spacing={8}>
          <Box textAlign="center">
            <HStack justify="space-between" w="100%" mb={4}>
              <Heading size="xl">Pointless</Heading>
              <WalletButton />
            </HStack>
            <Text color="gray.600" fontSize="lg">
              Your friendly crypto command interpreter
            </Text>
            <Text color="gray.500" fontSize="sm" mt={2}>
              Ask me to swap tokens, send crypto, or answer questions about
              crypto!
            </Text>
          </Box>

          {!isConnected && (
            <Alert status="warning" borderRadius="md">
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
            <Alert status="info" borderRadius="md">
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
            <VStack spacing={4} w="100%" align="stretch" mb={8}>
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
        </VStack>
      </Container>
    </Box>
  );
}

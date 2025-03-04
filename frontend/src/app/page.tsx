"use client";

import * as React from "react";
import Image from "next/image";
import NextLink from "next/link";
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
  Badge,
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
import { LogoModal } from "../components/LogoModal";
import { formatTokenAmount, smallestUnitsToAmount } from "../utils/tokenUtils";

type Response = {
  content: string | any;
  timestamp: string;
  isCommand: boolean;
  pendingCommand?: string;
  awaitingConfirmation?: boolean;
  confirmation_type?: "token_confirmation" | "quote_selection";
  status?: "pending" | "processing" | "success" | "error";
  agentType?: "default" | "swap";
  metadata?: any;
  requires_selection?: boolean;
  all_quotes?: any[];
  selected_quote?: {
    to: string;
    data: string;
    value: string;
    gas: string;
    buy_amount: string;
    sell_amount: string;
    protocol: string;
    aggregator: string;
  };
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
  error?: string;
  error_code?: string;
  needs_approval?: boolean;
  token_to_approve?: string;
  spender?: string;
  pending_command?: string;
  skip_approval?: boolean;
  metadata?: {
    token_in_address?: string;
    token_in_symbol?: string;
    token_in_name?: string;
    token_in_verified?: boolean;
    token_in_source?: string;
    token_out_address?: string;
    token_out_symbol?: string;
    token_out_name?: string;
    token_out_verified?: boolean;
    token_out_source?: string;
  };
  // Add properties that might come from API responses
  gas_limit?: string;
  gas_price?: string;
  max_fee_per_gas?: string;
  max_priority_fee_per_gas?: string;
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
  const [isLogoModalOpen, setIsLogoModalOpen] = React.useState(false);

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

    // Check if the transaction data contains an error
    if ("error" in txData && txData.error) {
      setResponses((prev) => [
        ...prev,
        {
          content: `Transaction failed: ${txData.error}`,
          timestamp: new Date().toLocaleTimeString(),
          isCommand: false,
          status: "error",
          agentType: "swap",
        },
      ]);
      // Set a flag to indicate this error has been handled
      const handledError = new Error(txData.error);
      (handledError as any).handled = true;
      throw handledError;
    }

    // Validate required transaction fields
    if (!txData.to || !txData.data) {
      const errorMsg = `Invalid transaction data: missing required fields (to: ${txData.to}, data: ${txData.data})`;
      console.error("Invalid transaction data:", txData);
      setResponses((prev) => [
        ...prev,
        {
          content: errorMsg,
          timestamp: new Date().toLocaleTimeString(),
          isCommand: false,
          status: "error",
          agentType: "swap",
        },
      ]);
      throw new Error(errorMsg);
    }

    try {
      // If approval is needed, handle it first
      if (
        txData.needs_approval &&
        txData.token_to_approve &&
        txData.spender &&
        !txData.skip_approval
      ) {
        const tokenSymbol = txData.metadata?.token_in_symbol || "Token";

        setResponses((prev) => [
          ...prev,
          {
            content: `Please approve ${tokenSymbol} spending for the swap...`,
            timestamp: new Date().toLocaleTimeString(),
            isCommand: false,
            status: "processing",
            agentType: "swap",
          },
        ]);

        // Generate proper ERC20 approve function data
        // Function signature: approve(address,uint256)
        const approveSignature = "0x095ea7b3"; // approve(address,uint256) function selector
        // Pad the address to 32 bytes (remove 0x prefix first)
        const paddedSpender = txData.spender.slice(2).padStart(64, "0");
        // Use a very large value to approve (uint256 max value to approve "unlimited")
        const maxUint256 =
          "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff";

        const approveData = `${approveSignature}${paddedSpender}${maxUint256}`;

        const approveParams = {
          to: txData.token_to_approve as `0x${string}`,
          data: approveData as `0x${string}`,
          value: BigInt(0),
          chainId: txData.chainId,
          gas: BigInt(100000),
        };

        const approveHash = await walletClient.sendTransaction(approveParams);
        const approveReceipt = await publicClient?.waitForTransactionReceipt({
          hash: approveHash,
        });

        if (!approveReceipt?.status) {
          throw new Error("Approval transaction failed");
        }

        setResponses((prev) => [
          ...prev,
          {
            content: `${tokenSymbol} approved successfully! Proceeding with swap...`,
            timestamp: new Date().toLocaleTimeString(),
            isCommand: false,
            status: "success",
            agentType: "swap",
          },
        ]);

        // Retry the original transaction after approval
        if (txData.pending_command) {
          try {
            const response = await fetch(`/api/execute-transaction`, {
              method: "POST",
              headers: getApiHeaders(),
              body: JSON.stringify({
                command: txData.pending_command,
                wallet_address: address,
                chain_id: chainId,
                creator_id: address ? address.toLowerCase() : "anonymous",
                skip_approval: txData.pending_command.startsWith("approved:"),
              }),
            });

            if (!response.ok) {
              const errorText = await response.text();
              console.error("API error response:", errorText);
              let errorMessage = "Failed to execute swap after approval";

              try {
                const errorJson = JSON.parse(errorText);
                if (errorJson.detail) {
                  if (typeof errorJson.detail === "object") {
                    errorMessage = JSON.stringify(errorJson.detail);
                  } else {
                    errorMessage = errorJson.detail;
                  }
                }
              } catch (e) {
                errorMessage = errorText;
              }

              throw new Error(errorMessage);
            }

            const swapData = await response.json();
            console.log("Swap data from API after approval:", swapData);

            // Check if the response needs clarification
            if (swapData.status === "needs_clarification") {
              setResponses((prev) => [
                ...prev,
                {
                  content:
                    swapData.clarification_prompt ||
                    "I need more information to process your request.",
                  timestamp: new Date().toLocaleTimeString(),
                  isCommand: false,
                  status: "pending",
                  agentType: "swap",
                  metadata: {
                    missing_info: swapData.missing_info,
                    original_command: txData.pending_command,
                  },
                },
              ]);
              return;
            }

            // Check for errors in the response
            if (swapData.error || swapData.status === "error") {
              const errorMsg = `Transaction failed: ${
                swapData.error || "Unknown error"
              }`;
              setResponses((prev) => [
                ...prev,
                {
                  content: errorMsg,
                  timestamp: new Date().toLocaleTimeString(),
                  isCommand: false,
                  status: "error",
                  agentType: "swap",
                },
              ]);
              throw new Error(errorMsg);
            }

            // Check if we have valid transaction data
            const hasValidData = swapData.to && swapData.data;
            if (!hasValidData) {
              const errorMsg =
                "Invalid transaction data returned from API: missing required fields";
              console.error("Invalid transaction data:", swapData);
              setResponses((prev) => [
                ...prev,
                {
                  content: errorMsg,
                  timestamp: new Date().toLocaleTimeString(),
                  isCommand: false,
                  status: "error",
                  agentType: "swap",
                },
              ]);
              throw new Error(errorMsg);
            }

            // Convert snake_case to camelCase for proper execution
            const mappedData: TransactionData = {
              to: swapData.to,
              data: swapData.data,
              value: swapData.value || "0",
              chainId: chainId,
              method: swapData.method || "unknown",
              gasLimit: swapData.gas_limit || "300000",
              gasPrice: swapData.gas_price,
              maxFeePerGas: swapData.max_fee_per_gas,
              maxPriorityFeePerGas: swapData.max_priority_fee_per_gas,
              error: swapData.error,
              error_code: swapData.error_code,
              needs_approval: false, // Skip approval since we just did it
              token_to_approve: swapData.token_to_approve,
              spender: swapData.spender,
              pending_command: swapData.pending_command,
              skip_approval: true,
              metadata: swapData.metadata || {},
            };
            return executeTransaction(mappedData);
          } catch (error) {
            console.error("Error executing transaction after approval:", error);
            throw error;
          }
        }
      }

      // Execute the main transaction
      const transaction = {
        to: txData.to as `0x${string}`,
        data: txData.data as `0x${string}`,
        value: BigInt(txData.value || "0"),
        chainId: txData.chainId || chainId, // Use current chainId as fallback
        gas: BigInt(txData.gasLimit || txData.gas_limit || "300000"),
      };

      // Ensure the transaction value is properly formatted
      if (transaction.value < BigInt(0)) {
        transaction.value = BigInt(0);
      }

      // Ensure the transaction address is properly formatted
      if (!transaction.to.startsWith("0x")) {
        transaction.to = `0x${transaction.to}` as `0x${string}`;
      }

      // Ensure the transaction data is properly formatted
      if (!transaction.data.startsWith("0x")) {
        transaction.data = `0x${transaction.data}` as `0x${string}`;
      }

      // Log transaction details for debugging
      console.log("Executing transaction:", {
        to: transaction.to,
        value: transaction.value.toString(),
        chainId: transaction.chainId,
        gas: transaction.gas.toString(),
      });

      // Verify that the chain ID matches the current chain
      if (transaction.chainId !== chainId) {
        console.warn(
          `Transaction chain ID (${transaction.chainId}) doesn't match current chain (${chainId}). Updating to current chain.`
        );
        transaction.chainId = chainId;
      }

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
          agentType: "swap",
          metadata: txData.metadata,
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
          agentType: "swap",
          metadata: txData.metadata,
        },
      ]);

      return hash;
    } catch (error) {
      console.error("Transaction error:", error);

      // Skip adding an error message if this error was already handled
      if ((error as any).handled) {
        throw error;
      }

      let errorMessage = "Transaction failed";

      if (error instanceof Error) {
        if (
          error.message.includes("user rejected") ||
          error.message.includes("User rejected")
        ) {
          errorMessage = "Transaction was cancelled by user";
        } else if (error.message.includes("insufficient funds")) {
          errorMessage = "Insufficient funds for transaction";
        } else if (error.message.includes("TRANSFER_FROM_FAILED")) {
          errorMessage =
            "Failed to transfer USDC. Please make sure you have enough USDC and have approved the swap.";
        } else {
          // For other errors, extract a more readable message
          const message = error.message;

          // If the error contains transaction data (which is very long), simplify it
          if (
            message.includes("Request Arguments:") &&
            message.includes("data:")
          ) {
            // Extract just the first part before the technical details
            errorMessage = message.split("Request Arguments:")[0].trim();
          } else {
            // For other errors, use the first line or first 100 characters
            errorMessage = message.split("\n")[0];
            if (errorMessage.length > 100) {
              errorMessage = errorMessage.substring(0, 100) + "...";
            }
          }
        }
      }

      setResponses((prev) => [
        ...prev.filter((r) => !r.status?.includes("processing")),
        {
          content: `Transaction failed: ${errorMessage}`,
          timestamp: new Date().toLocaleTimeString(),
          isCommand: false,
          status: "error",
          agentType: "swap",
        },
      ]);

      throw error;
    }
  };

  const handleQuoteSelection = async (response: Response, quote: any) => {
    try {
      setIsLoading(true);
      const sessionApiKeys = getApiKeys();

      // Call the backend to prepare the transaction with the selected quote
      const result = await fetch("/api/swap/execute", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...getApiHeaders(),
        },
        body: JSON.stringify({
          wallet_address: walletClient?.account?.address,
          chain_id: chainId || 1,
          selected_quote: quote,
        }),
      });

      const txData = await result.json();

      if (txData.error) {
        // Add the error response to the chat
        const errorResponse: Response = {
          content: `Error: ${txData.error}`,
          timestamp: new Date().toISOString(),
          isCommand: false,
          status: "error",
        };
        setResponses((prev) => [...prev, errorResponse]);
        return;
      }

      // Execute the transaction
      if (txData.to && txData.data) {
        await executeTransaction(txData);
      } else {
        // Handle error
        const errorResponse: Response = {
          content: "Invalid transaction data received from API",
          timestamp: new Date().toISOString(),
          isCommand: false,
          status: "error",
        };
        setResponses((prev) => [...prev, errorResponse]);
      }
    } catch (error) {
      console.error("Error during quote selection:", error);
      const errorResponse: Response = {
        content: `Error selecting quote: ${
          error instanceof Error ? error.message : String(error)
        }`,
        timestamp: new Date().toISOString(),
        isCommand: false,
        status: "error",
      };
      setResponses((prev) => [...prev, errorResponse]);
    } finally {
      setIsLoading(false);
    }
  };

  const processCommand = async (command: string) => {
    try {
      setIsLoading(true);

      if (!walletClient || !address) {
        // Handle case where wallet is not connected
        const errorResponse: Response = {
          content: "Please connect your wallet to continue.",
          timestamp: new Date().toISOString(),
          isCommand: false,
          status: "error",
        };
        setResponses((prev) => [...prev, errorResponse]);
        setIsLoading(false);
        return;
      }

      // Add the user command to responses
      const userCommand: Response = {
        content: command,
        timestamp: new Date().toISOString(),
        isCommand: true,
      };
      setResponses((prev) => [...prev, userCommand]);

      // Detect if this is a swap command
      if (command.toLowerCase().startsWith("swap ")) {
        // Process swap command
        await processSwapCommand(command);
        return;
      }

      // For other commands, use the general API
      const response = await fetch("/api/process-command", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...getApiHeaders(),
        },
        body: JSON.stringify({
          content: command,
          wallet_address: address,
          chain_id: chainId || 1,
        }),
      });

      const data = await response.json();

      if (data.error) {
        const errorResponse: Response = {
          content: `Error: ${data.error}`,
          timestamp: new Date().toISOString(),
          isCommand: false,
          status: "error",
        };
        setResponses((prev) => [...prev, errorResponse]);
        return;
      }

      // Process the response
      const botResponse: Response = {
        content: data.content || data,
        timestamp: new Date().toISOString(),
        isCommand: false,
        agentType: data.agent_type || "default",
        metadata: data.metadata,
      };

      // Handle special response types
      if (data.status) {
        botResponse.status = data.status;
      }

      // Add the response
      setResponses((prev) => [...prev, botResponse]);
    } catch (error) {
      console.error("Error processing command:", error);
      const errorResponse: Response = {
        content: `Error: ${
          error instanceof Error ? error.message : String(error)
        }`,
        timestamp: new Date().toISOString(),
        isCommand: false,
        status: "error",
      };
      setResponses((prev) => [...prev, errorResponse]);
    } finally {
      setIsLoading(false);
    }
  };

  const processSwapCommand = async (command: string) => {
    try {
      // Process the initial swap command to get token information
      const response = await fetch("/api/swap/process-command", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...getApiHeaders(),
        },
        body: JSON.stringify({
          command,
          wallet_address: address,
          chain_id: chainId || 1,
        }),
      });

      const data = await response.json();

      if (data.error) {
        const errorResponse: Response = {
          content: `Error: ${data.error}`,
          timestamp: new Date().toISOString(),
          isCommand: false,
          status: "error",
        };
        setResponses((prev) => [...prev, errorResponse]);
        return;
      }

      // Check if we have a swap confirmation
      if (data.content && data.content.type === "swap_confirmation") {
        // Add the swap confirmation to the responses
        const swapConfirmationResponse: Response = {
          content: data.content,
          timestamp: new Date().toISOString(),
          isCommand: false,
          awaitingConfirmation: true,
          confirmation_type: "token_confirmation",
          metadata: data.metadata,
          status: "success",
        };

        setResponses((prev) => [...prev, swapConfirmationResponse]);
      } else {
        // Regular response
        const botResponse: Response = {
          content: data.content || data,
          timestamp: new Date().toISOString(),
          isCommand: false,
          metadata: data.metadata,
          status: "success",
        };

        setResponses((prev) => [...prev, botResponse]);
      }
    } catch (error) {
      console.error("Error processing swap command:", error);
      const errorResponse: Response = {
        content: `Error processing swap: ${
          error instanceof Error ? error.message : String(error)
        }`,
        timestamp: new Date().toISOString(),
        isCommand: false,
        status: "error",
      };
      setResponses((prev) => [...prev, errorResponse]);
    }
  };

  const handleTokenConfirmation = async () => {
    try {
      setIsLoading(true);

      // User has confirmed the tokens, get quotes
      const response = await fetch("/api/swap/get-quotes", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...getApiHeaders(),
        },
        body: JSON.stringify({
          wallet_address: address,
          chain_id: chainId || 1,
        }),
      });

      const data = await response.json();

      if (data.error) {
        const errorResponse: Response = {
          content: `Error: ${data.error}`,
          timestamp: new Date().toISOString(),
          isCommand: false,
          status: "error",
        };
        setResponses((prev) => [...prev, errorResponse]);
        return;
      }

      // Check if we have quotes
      if (data.quotes && data.quotes.length > 0) {
        // Add the quotes to the responses for selection
        const quotesResponse: Response = {
          content: "Here are the available quotes. Please select one:",
          timestamp: new Date().toISOString(),
          isCommand: false,
          status: "success",
          requires_selection: true,
          all_quotes: data.quotes,
        };

        setResponses((prev) => [...prev, quotesResponse]);
      } else {
        // No quotes available
        const errorResponse: Response = {
          content:
            "No quotes available for this swap. Please try a different pair or amount.",
          timestamp: new Date().toISOString(),
          isCommand: false,
          status: "error",
        };

        setResponses((prev) => [...prev, errorResponse]);
      }
    } catch (error) {
      console.error("Error getting quotes:", error);
      const errorResponse: Response = {
        content: `Error getting quotes: ${
          error instanceof Error ? error.message : String(error)
        }`,
        timestamp: new Date().toISOString(),
        isCommand: false,
        status: "error",
      };
      setResponses((prev) => [...prev, errorResponse]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmit = async (command: string) => {
    // Check if we're awaiting a confirmation
    const lastResponse = responses[responses.length - 1];

    if (lastResponse && lastResponse.awaitingConfirmation) {
      // If user confirms with "yes", "confirm", etc.
      if (
        ["yes", "confirm", "proceed", "ok", "go ahead"].includes(
          command.toLowerCase()
        )
      ) {
        // Add the confirmation to the responses
        const userConfirmation: Response = {
          content: command,
          timestamp: new Date().toISOString(),
          isCommand: true,
        };
        setResponses((prev) => [...prev, userConfirmation]);

        // Process based on confirmation type
        if (lastResponse.confirmation_type === "token_confirmation") {
          await handleTokenConfirmation();
        }
        return;
      } else if (["no", "cancel", "stop"].includes(command.toLowerCase())) {
        // User has declined
        const userDecline: Response = {
          content: command,
          timestamp: new Date().toISOString(),
          isCommand: true,
        };

        const botResponse: Response = {
          content: "Swap cancelled. How else can I help you?",
          timestamp: new Date().toISOString(),
          isCommand: false,
          status: "success",
        };

        setResponses((prev) => [...prev, userDecline, botResponse]);
        return;
      }
    }

    // If we're not awaiting confirmation or the user didn't confirm/decline,
    // process as a regular command
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
              <HStack spacing={2} align="center">
                <Box
                  as="button"
                  onClick={() => setIsLogoModalOpen(true)}
                  cursor="pointer"
                  transition="transform 0.2s"
                  _hover={{ transform: "scale(1.1)" }}
                >
                  <Image
                    src="/icon.png"
                    alt="SNEL Logo"
                    width={32}
                    height={32}
                    priority
                    style={{
                      marginRight: "4px",
                      objectFit: "contain",
                    }}
                  />
                </Box>
                <Heading size={{ base: "lg", sm: "xl" }}>SNEL</Heading>
              </HStack>
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
              Super poiNtlEss Lazy agents
            </Text>
            <Text color="gray.500" fontSize={{ base: "xs", sm: "sm" }} mt={2}>
              swap tokens, check balance etc. <br />
              double check all i do please.
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
                <AlertTitle>Welcome! Why are you here?</AlertTitle>
                <AlertDescription>
                  Click the help icon if you need help.
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
                  key={index}
                  content={response.content}
                  timestamp={response.timestamp}
                  isCommand={response.isCommand}
                  status={response.status}
                  awaitingConfirmation={response.awaitingConfirmation}
                  agentType={response.agentType}
                  metadata={response.metadata}
                  requires_selection={response.requires_selection}
                  all_quotes={response.all_quotes}
                  onQuoteSelect={handleQuoteSelection}
                />
              ))}
              <div ref={responsesEndRef} />
            </VStack>
          )}

          <CommandInput onSubmit={handleSubmit} isLoading={isLoading} />

          <LogoModal
            isOpen={isLogoModalOpen}
            onClose={() => setIsLogoModalOpen(false)}
          />
          <ApiKeyModal
            isOpen={isApiKeyModalOpen}
            onClose={() => setIsApiKeyModalOpen(false)}
          />
        </VStack>
      </Container>
    </Box>
  );
}

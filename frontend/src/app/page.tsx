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
import { ExternalLinkIcon, SettingsIcon, QuestionIcon } from "@chakra-ui/icons";
import { ApiKeyModal } from "../components/ApiKeyModal";
import { LogoModal } from "../components/LogoModal";
import { HelpModal } from "../components/HelpModal";
import { formatTokenAmount, smallestUnitsToAmount } from "../utils/tokenUtils";
import { openoceanLimitOrderSdk } from "@openocean.finance/limitorder-sdk";
import { ethers } from "ethers";
import {
  fetchUserProfile,
  ProfileInfo,
  getDisplayName,
} from "../services/profileService";

type Response = {
  content: string | any;
  timestamp: string;
  isCommand: boolean;
  pendingCommand?: string;
  awaitingConfirmation?: boolean;
  confirmation_type?: "token_confirmation" | "quote_selection";
  status?: "pending" | "processing" | "success" | "error";
  agentType?: "default" | "swap" | "dca" | "brian";
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
  transaction?: {
    to: string;
    data: string;
    value?: string;
    chainId?: number;
    gasLimit?: string;
    gas_limit?: string;
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

async function createDCAOrderWithSDK(
  provider: any,
  chainId: number,
  account: string,
  makerToken: {
    address: string;
    decimals: number;
    symbol: string;
  },
  takerToken: {
    address: string;
    decimals: number;
    symbol: string;
  },
  makerAmount: string,
  takerAmount: string,
  frequency: string, // in seconds
  times: number
) {
  try {
    // Validate chain - OpenOcean DCA currently only works on Base (chainId 8453)
    if (chainId !== 8453) {
      return {
        success: false,
        error: "DCA functionality is currently only supported on Base chain",
      };
    }

    // Validate minimum amount - $5 per transaction
    const amountInDecimal = parseFloat(makerAmount) / 10 ** makerToken.decimals;
    const totalAmount = amountInDecimal * times;

    // Assuming USDC/USDT with 6 decimals, minimum $5 per transaction
    const minimumPerDay = 5 * 10 ** (makerToken.decimals - 6); // Adjust for token decimals

    if (amountInDecimal < minimumPerDay) {
      return {
        success: false,
        error: `Minimum amount per transaction is $5 (${minimumPerDay} ${makerToken.symbol})`,
      };
    }

    // Map chain ID to chain key
    const chainKeyMap: Record<number, string> = {
      1: "eth",
      10: "optimism",
      56: "bsc",
      137: "polygon",
      42161: "arbitrum",
      8453: "base",
      534352: "scroll",
      43114: "avalanche",
    };

    const chainKey = chainKeyMap[chainId] || "base"; // Default to base

    // Map frequency to expire option
    const frequencyToExpire: Record<string, string> = {
      "86400": "1D", // 1 day
      "604800": "7D", // 7 days
      "2592000": "30D", // 30 days
    };

    // Calculate total duration in seconds
    const totalDurationSeconds = parseInt(frequency) * times;

    // Choose appropriate expire option
    let expireOption = "30D"; // Default to 30 days
    if (totalDurationSeconds <= 86400) {
      expireOption = "1D";
    } else if (totalDurationSeconds <= 604800) {
      expireOption = "7D";
    } else if (totalDurationSeconds <= 2592000) {
      expireOption = "30D";
    } else {
      expireOption = "1Y";
    }

    console.log("Creating DCA order with SDK:", {
      chainKey,
      chainId,
      account,
      makerToken,
      takerToken,
      makerAmount,
      takerAmount,
      frequency,
      times,
      expireOption,
    });

    // Convert viem provider to ethers provider
    let ethersProvider;
    try {
      // Try to convert the provider to an ethers provider
      if (provider && provider.request) {
        // Create a provider adapter that matches what the SDK expects
        const providerAdapter = {
          request: provider.request,
          send: provider.request,
          sendAsync: provider.request,
          // Add any other required properties
        };
        ethersProvider = new ethers.providers.Web3Provider(
          providerAdapter as any
        );
      } else {
        // Fallback to a window.ethereum provider if available
        if (typeof window !== "undefined" && window.ethereum) {
          ethersProvider = new ethers.providers.Web3Provider(
            window.ethereum as any
          );
        } else {
          // Last resort: create a minimal provider object
          ethersProvider = {
            getSigner: () => ({
              getAddress: async () => account,
              signMessage: async () => "0x",
              _signTypedData: async () => "0x",
            }),
            getNetwork: async () => ({ chainId: chainId }),
          } as any;
        }
      }
      console.log("Ethers provider initialized:", ethersProvider);
    } catch (error) {
      console.error("Error initializing ethers provider:", error);
      return {
        success: false,
        error: "Failed to initialize ethers provider",
      };
    }

    // Create the order using the SDK
    const order = await openoceanLimitOrderSdk.createLimitOrder(
      {
        provider: ethersProvider, // Use ethers provider
        chainKey: chainKey,
        account: account,
        chainId: chainId.toString(), // Convert to string to fix type error
        mode: "Dca", // Important: Use 'Dca' mode for DCA orders
      },
      {
        makerTokenAddress: makerToken.address,
        makerTokenDecimals: makerToken.decimals,
        takerTokenAddress: takerToken.address,
        takerTokenDecimals: takerToken.decimals,
        makerAmount: makerAmount,
        takerAmount: takerAmount,
        gasPrice: 3000000000, // Default gas price as a number
        expire: expireOption,
        receiver: "0x0000000000000000000000000000000000000000", // Default receiver
        receiverInputData: "0x", // Default receiver input data
        mode: "Dca", // Mode for DCA orders
      }
    );

    // Add DCA-specific parameters
    const dcaOrder = {
      ...order,
      expireTime: (parseInt(frequency) * times).toString(),
      time: parseInt(frequency).toString(),
      times: Number(times), // Ensure times is a number
      version: "v2",
      minPrice: "0.9", // 10% price range
      maxPrice: "1.1",
    };

    console.log("DCA order created:", dcaOrder);

    // Submit the order to the OpenOcean API
    const response = await fetch(
      `https://open-api.openocean.finance/v1/${chainId}/dca/swap`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(dcaOrder),
      }
    );

    const result = await response.json();
    console.log("DCA order submission result:", result);

    return {
      success: result.code === 200,
      data: result,
      order: dcaOrder,
    };
  } catch (error) {
    console.error("Error creating DCA order:", error);
    return {
      success: false,
      error: error instanceof Error ? error.message : String(error),
    };
  }
}

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
  const [isHelpModalOpen, setIsHelpModalOpen] = React.useState(false);
  const [commandInput, setCommandInput] = React.useState("");
  const [currentCommand, setCurrentCommand] = React.useState("");
  const [awaitingInput, setAwaitingInput] = React.useState(false);
  const [confirmationCallback, setConfirmationCallback] = React.useState<
    (() => Promise<void>) | null
  >(null);
  const [userProfile, setUserProfile] = React.useState<ProfileInfo | null>(
    null
  );

  // Fetch user profile when address changes
  React.useEffect(() => {
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
        const isScrollChain = chainId === 534352;

        // For Scroll chain, make it clearer that this is a two-step process
        if (isScrollChain) {
          setResponses((prev) => [
            ...prev,
            {
              content: `This swap requires two transactions:\n\n1️⃣ First, approve ${tokenSymbol} spending (current step)\n2️⃣ Then execute the actual swap (next step)\n\nPlease confirm the approval transaction in your wallet...`,
              timestamp: new Date().toLocaleTimeString(),
              isCommand: false,
              status: "processing",
              agentType: "swap",
            },
          ]);
        } else {
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
        }

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

        // For Scroll chain, make it clearer that we're waiting for the approval to complete
        if (isScrollChain) {
          setResponses((prev) => [
            ...prev.filter((r) => !r.status?.includes("processing")),
            {
              content: `✅ Approval transaction submitted!\n\nWaiting for confirmation...\nView on block explorer: ${getBlockExplorerLink(
                approveHash
              )}`,
              timestamp: new Date().toLocaleTimeString(),
              isCommand: false,
              status: "processing",
              agentType: "swap",
            },
          ]);
        }

        const approveReceipt = await publicClient?.waitForTransactionReceipt({
          hash: approveHash,
        });

        if (!approveReceipt?.status) {
          throw new Error("Approval transaction failed");
        }

        // For Scroll chain, make it clearer that we're moving to the second step
        if (isScrollChain) {
          setResponses((prev) => [
            ...prev.filter((r) => !r.status?.includes("processing")),
            {
              content: `✅ ${tokenSymbol} approved successfully!\n\nNow proceeding with the swap transaction (step 2 of 2).\nPlease confirm the swap transaction in your wallet...`,
              timestamp: new Date().toLocaleTimeString(),
              isCommand: false,
              status: "success",
              agentType: "swap",
            },
          ]);
        } else {
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
        }

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

      // Create a user-friendly error message
      let errorMessage = "Transaction failed";
      let isUserRejection = false;

      if (error instanceof Error) {
        // Check for user rejection errors
        if (
          error.message.includes("user rejected") ||
          error.message.includes("User rejected") ||
          error.message.includes("User denied") ||
          error.message.includes("user denied") ||
          error.message.includes("rejected the request") ||
          error.message.includes("transaction signature")
        ) {
          errorMessage = "Transaction cancelled";
          isUserRejection = true;
        }
        // Check for common errors with helpful messages
        else if (error.message.includes("insufficient funds")) {
          errorMessage = "You don't have enough funds for this transaction";
        } else if (error.message.includes("TRANSFER_FROM_FAILED")) {
          errorMessage =
            "Token transfer failed. Please check your balance and token approval.";
        } else if (error.message.includes("gas required exceeds allowance")) {
          errorMessage = "Gas required exceeds your ETH balance";
        } else if (error.message.includes("nonce too low")) {
          errorMessage = "Transaction nonce issue. Please try again.";
        } else if (error.message.includes("execution reverted")) {
          // Extract revert reason if available
          const revertMatch = error.message.match(
            /execution reverted: (.*?)(?:")/
          );
          errorMessage = revertMatch
            ? `Transaction reverted: ${revertMatch[1]}`
            : "Transaction reverted by the contract";
        } else {
          // For other errors, extract a more readable message
          const message = error.message;

          // If the error contains transaction data (which is very long), simplify it
          if (message.includes("Request Arguments:")) {
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

      // Add a user-friendly error message to the chat
      setResponses((prev) => [
        ...prev.filter((r) => !r.status?.includes("processing")),
        {
          content: isUserRejection
            ? "Transaction was cancelled by user"
            : `Transaction failed: ${errorMessage}`,
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
      const isScrollChain = chainId === 534352;

      // For Scroll chain, provide clearer messaging about the two-step process
      if (isScrollChain) {
        setResponses((prev) => [
          ...prev,
          {
            content:
              "Preparing your swap on Scroll...\n\nNote: Scroll swaps typically require two transactions:\n1. First to approve token spending\n2. Then to execute the actual swap",
            timestamp: new Date().toISOString(),
            isCommand: false,
            status: "processing",
            agentType: "swap",
          },
        ]);
      }

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

      // Check if this is a user rejection error
      const errorMessage =
        error instanceof Error ? error.message : String(error);
      const isUserRejection =
        errorMessage.includes("user denied") ||
        errorMessage.includes("User denied") ||
        errorMessage.includes("User rejected") ||
        errorMessage.includes("rejected the request");

      const errorResponse: Response = {
        content: isUserRejection
          ? "Transaction was cancelled by user"
          : `Error selecting quote: ${errorMessage}`,
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

      // Detect if this is a DCA command
      if (
        command.toLowerCase().startsWith("dca ") ||
        command.toLowerCase().startsWith("dollar cost average ")
      ) {
        // Process DCA command
        await processDCACommand(command);
        return;
      }

      // Get the API endpoint
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const endpoint = `${apiUrl}/api/commands`;

      // Get the user's display name
      const userName = getDisplayName(address, userProfile);

      // Prepare the request body
      const requestBody = {
        command,
        wallet_address: address,
        chain_id: chainId,
        user_name: userName, // Add the user's name to the request
      };

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
          user_name: getDisplayName(address, userProfile), // Add user's display name
        }),
      });

      const data = await response.json();

      if (data.error_message) {
        const errorResponse: Response = {
          content: `Error: ${data.error_message}`,
          timestamp: new Date().toISOString(),
          isCommand: false,
          status: "error",
        };
        setResponses((prev) => [...prev, errorResponse]);
        return;
      }

      // Check if we have a transaction to execute
      if (data.transaction) {
        console.log("Transaction data received:", data.transaction);

        // Add a response indicating we're processing the transaction
        const processingResponse: Response = {
          content: {
            type: "message",
            message: `Processing your transaction...`,
          },
          timestamp: new Date().toISOString(),
          isCommand: false,
          status: "processing",
          agentType: data.agent_type || "brian",
        };

        setResponses((prev) => [...prev, processingResponse]);

        // Execute the transaction
        try {
          const txData = {
            to: data.transaction.to,
            data: data.transaction.data,
            value: data.transaction.value || "0",
            chainId: data.transaction.chainId || chainId,
            gasLimit: data.transaction.gasLimit || "300000",
            method: data.transaction.method || "unknown",
          };

          await executeTransaction(txData);
        } catch (error) {
          console.error("Error executing transaction:", error);
          // Error handling is done in executeTransaction
        }

        return;
      }

      // Process the response
      const botResponse: Response = {
        content: data.content || data,
        timestamp: new Date().toISOString(),
        isCommand: false,
        agentType: data.agent_type || "default",
        metadata: data.metadata,
        awaitingConfirmation: data.awaiting_confirmation,
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
        // For Scroll chain, add a note about the two-step process
        const isScrollChain = chainId === 534352;
        let confirmationContent = data.content;

        if (isScrollChain) {
          // Add a note about the two-step process for Scroll
          confirmationContent = {
            ...data.content,
            note: "Note: On Scroll, swaps require two separate transactions: first to approve token spending, then to execute the swap.",
          };
        }

        // Add the swap confirmation to the responses
        const swapConfirmationResponse: Response = {
          content: confirmationContent,
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

  const processDCACommand = async (command: string) => {
    try {
      setIsLoading(true);

      // Call the DCA API
      const response = await fetch("/api/dca/process-command", {
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

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(
          errorData.detail || `Error ${response.status}: ${response.statusText}`
        );
      }

      const data = await response.json();

      // Handle the response
      const botResponse: Response = {
        content: data.content,
        timestamp: new Date().toISOString(),
        isCommand: false,
        agentType: "dca",
        awaitingConfirmation:
          data.content && data.content.type === "dca_confirmation",
        confirmation_type: "token_confirmation",
        pendingCommand: data.pending_command,
        metadata: data.metadata,
        transaction: data.transaction,
      };

      setResponses((prev) => [...prev, botResponse]);

      // If we need confirmation, set up the confirmation state
      if (data.content && data.content.type === "dca_confirmation") {
        setAwaitingInput(true);
        setConfirmationCallback(() => handleDCAConfirmation);
      }

      // If there's transaction data, log it for debugging
      if (data.transaction) {
        console.log("DCA transaction data:", data.transaction);
      }
    } catch (error) {
      console.error("Error processing DCA command:", error);
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

  const handleDCAConfirmation = async () => {
    try {
      // Find the pending command from the responses
      const pendingResponses = responses.filter((r) => r.awaitingConfirmation);
      const lastDCAResponse =
        pendingResponses.length > 0
          ? pendingResponses[pendingResponses.length - 1]
          : null;

      if (!lastDCAResponse) {
        throw new Error("No pending command found");
      }

      // Check if this is actually a swap confirmation that was misidentified
      if (lastDCAResponse.content?.type === "swap_confirmation") {
        console.log("Detected swap confirmation, redirecting to swap handler");
        // Process as a swap instead
        await processCommand("yes");
        return;
      }

      // Check if there's transaction data in the response
      if (lastDCAResponse.transaction) {
        // Execute the transaction
        const txData = lastDCAResponse.transaction;

        // Log transaction details for debugging
        console.log("Executing DCA transaction:", txData);

        // Create transaction parameters
        const transaction = {
          to: txData.to as `0x${string}`,
          data: txData.data as `0x${string}`,
          value: BigInt(txData.value || "0"),
          chainId: txData.chainId || chainId, // Use current chainId as fallback
          gas: BigInt(txData.gas_limit || txData.gasLimit || "300000"),
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

        // Verify that the chain ID matches the current chain
        if (transaction.chainId !== chainId) {
          console.warn(
            `Transaction chain ID (${transaction.chainId}) doesn't match current chain (${chainId}). Updating to current chain.`
          );
          transaction.chainId = chainId;
        }

        // Send the transaction
        if (!walletClient) {
          throw new Error("Wallet client not initialized");
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
            agentType: "dca",
            metadata: lastDCAResponse.metadata,
          },
        ]);

        const receipt = await publicClient?.waitForTransactionReceipt({
          hash,
        });

        if (!receipt) {
          throw new Error("Failed to get transaction receipt");
        }

        const isSuccess = Boolean(receipt.status);

        // If the transaction was successful, create the DCA order using the SDK
        if (isSuccess) {
          // Show processing message
          setResponses((prev) => [
            ...prev,
            {
              content: "Processing DCA order setup...",
              timestamp: new Date().toISOString(),
              isCommand: false,
              status: "processing",
              agentType: "dca",
            },
          ]);

          // Extract metadata from the response
          const metadata = lastDCAResponse.metadata || {};
          const walletAddress = metadata.wallet_address;
          const currentChainId = metadata.chain_id || chainId;

          // Check if user is on Base chain
          if (currentChainId !== 8453) {
            const errorResponse: Response = {
              content: `Error: DCA functionality is currently only supported on Base chain. Please switch your wallet to Base.`,
              timestamp: new Date().toISOString(),
              isCommand: false,
              status: "error",
              agentType: "dca",
            };
            setResponses((prev) => [...prev, errorResponse]);
            return;
          }

          if (!walletAddress) {
            throw new Error("Wallet address not found in metadata");
          }

          // Extract token information
          const makerAsset = metadata.maker_asset;
          const takerAsset = metadata.taker_asset;
          const makerAmount = metadata.maker_amount;
          const takerAmount = metadata.taker_amount || "0";
          const frequencySeconds =
            metadata.frequency_seconds?.toString() || "86400";
          const times = metadata.times || 1;

          // Get token details
          const makerToken = {
            address: makerAsset,
            decimals: metadata.token_in_decimals || 18,
            symbol: metadata.token_in_symbol || "Unknown",
          };

          const takerToken = {
            address: takerAsset,
            decimals: metadata.token_out_decimals || 18,
            symbol: metadata.token_out_symbol || "Unknown",
          };

          // Create the DCA order using the SDK
          const dcaResult = await createDCAOrderWithSDK(
            walletClient.transport,
            currentChainId,
            walletAddress,
            makerToken,
            takerToken,
            makerAmount,
            takerAmount,
            frequencySeconds,
            times
          );

          if (dcaResult.success) {
            // DCA order created successfully
            const successResponse: Response = {
              content: {
                type: "dca_success",
                message:
                  "I've successfully set up your DCA order! You'll be swapping the specified amount on your chosen schedule. You can monitor your DCA positions through your wallet's activity.",
              },
              timestamp: new Date().toISOString(),
              isCommand: false,
              status: "success",
              agentType: "dca",
            };

            setResponses((prev) => [...prev, successResponse]);
          } else {
            // DCA order creation failed
            throw new Error(`Failed to create DCA order: ${dcaResult.error}`);
          }
        } else {
          throw new Error("Approval transaction failed");
        }
      } else {
        // No transaction data, just show a success message
        const successResponse: Response = {
          content: {
            type: "dca_success",
            message:
              "I've initiated your DCA order! You'll be swapping the specified amount on your chosen schedule. You can monitor your DCA positions through your wallet's activity.",
          },
          timestamp: new Date().toISOString(),
          isCommand: false,
          status: "success",
          agentType: "dca",
        };

        setResponses((prev) => [...prev, successResponse]);
      }

      // Clear the awaiting confirmation state
      setAwaitingInput(false);
      setConfirmationCallback(null);
    } catch (error) {
      console.error("Error creating DCA order:", error);
      const errorResponse: Response = {
        content: `Error creating DCA order: ${
          error instanceof Error ? error.message : String(error)
        }`,
        timestamp: new Date().toISOString(),
        isCommand: false,
        status: "error",
        agentType: "dca",
      };
      setResponses((prev) => [...prev, errorResponse]);

      // Clear the awaiting confirmation state
      setAwaitingInput(false);
      setConfirmationCallback(null);
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

        // Check the content type to determine how to handle the confirmation
        if (lastResponse.content?.type === "swap_confirmation") {
          console.log("Processing swap confirmation");

          // For swap confirmations, we need to get quotes and show the aggregator selection UI
          try {
            setIsLoading(true);

            // First, get quotes for the swap
            const quotesResponse = await fetch("/api/swap/get-quotes", {
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

            if (!quotesResponse.ok) {
              throw new Error(
                `Error getting quotes: ${quotesResponse.statusText}`
              );
            }

            const quotesData = await quotesResponse.json();
            console.log("Quotes data:", quotesData);

            if (quotesData.error) {
              throw new Error(quotesData.error);
            }

            // If we have quotes, show the aggregator selection UI
            if (quotesData.quotes && quotesData.quotes.length > 0) {
              // Add a response with the quotes for the user to select from
              const quotesResponse: Response = {
                content: "Please select a provider for your swap:",
                timestamp: new Date().toISOString(),
                isCommand: false,
                status: "success",
                agentType: "swap",
                requires_selection: true,
                all_quotes: quotesData.quotes,
                metadata: {
                  token_out_symbol: quotesData.token_out?.symbol || "tokens",
                  token_out_decimals: quotesData.token_out?.decimals || 18,
                },
              };

              setResponses((prev) => [...prev, quotesResponse]);
            } else {
              throw new Error("No quotes available for this swap");
            }
          } catch (error) {
            console.error("Error processing swap confirmation:", error);
            const errorResponse: Response = {
              content: `Unable to get swap quotes: ${
                error instanceof Error ? error.message : String(error)
              }`,
              timestamp: new Date().toISOString(),
              isCommand: false,
              status: "error",
              agentType: "swap",
            };
            setResponses((prev) => [...prev, errorResponse]);
          } finally {
            setIsLoading(false);
          }
        } else if (
          lastResponse.content?.type === "dca_confirmation" ||
          lastResponse.confirmation_type === "token_confirmation"
        ) {
          console.log("Processing DCA confirmation");
          await handleDCAConfirmation();
        } else {
          // Generic confirmation - just send the command
          await processCommand("yes");
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
          content: "Operation cancelled. How else can I help you?",
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
                  colorScheme="blue"
                  onClick={() => setIsHelpModalOpen(true)}
                  leftIcon={<Icon as={QuestionIcon} />}
                >
                  Help
                </Button>
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
                <AlertTitle>
                  Welcome! I, SNEL, am in beta, kindly go slow.
                </AlertTitle>
                <AlertDescription>
                  By continuing, you agree to my{" "}
                  <Link href="/terms" color="blue.500" isExternal>
                    Terms 🐌
                  </Link>
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
          <HelpModal
            isOpen={isHelpModalOpen}
            onClose={() => setIsHelpModalOpen(false)}
          />
        </VStack>
      </Container>
    </Box>
  );
}

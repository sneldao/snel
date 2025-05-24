import * as React from "react";
import {
  Box,
  HStack,
  VStack,
  Avatar,
  Text,
  Badge,
  Icon,
  List,
  ListItem,
  ListIcon,
  Spinner,
  Link,
  Alert,
  AlertIcon,
  AlertTitle,
  AlertDescription,
  Divider,
  useColorModeValue,
  Button,
  UnorderedList,
  Flex,
  Code,
  useToast,
} from "@chakra-ui/react";
import {
  CheckCircleIcon,
  QuestionIcon,
  WarningIcon,
  TimeIcon,
  ChatIcon,
  InfoIcon,
  ExternalLinkIcon,
} from "@chakra-ui/icons";
import { SwapConfirmation } from "./SwapConfirmation";
import { DCAConfirmation } from "./DCAConfirmation";
import { BrianConfirmation } from "./BrianConfirmation";
import { TransactionProgress } from "./TransactionProgress";
import AggregatorSelection from "./AggregatorSelection";
import { FaExchangeAlt, FaCalendarAlt, FaRobot } from "react-icons/fa";
import { useUserProfile } from "../hooks/useUserProfile";
import { ApiService } from "../services/apiService";
import {
  useAccount,
  useChainId,
  useWalletClient,
  usePublicClient,
} from "wagmi";
import { TransactionService } from "../services/transactionService";
import { executeTransaction } from "../lib/api";

interface CommandResponseProps {
  content: string | any; // Updated to accept structured content
  timestamp: string;
  isCommand: boolean;
  status?: "pending" | "processing" | "success" | "error";
  awaitingConfirmation?: boolean;
  agentType?: "default" | "swap" | "dca" | "brian";
  metadata?: any;
  requires_selection?: boolean;
  all_quotes?: any[];
  onQuoteSelect?: (response: any, quote: any) => void;
  transaction?: any;
}

type TokenInfo = {
  address?: string;
  symbol?: string;
  name?: string;
  verified?: boolean;
  source?: string;
  warning?: string;
};

const LoadingSteps = [
  "Processing your command...",
  "Classifying command type...",
  "Getting token information...",
  "Converting amounts...",
  "Getting best swap route...",
  "Preparing transaction...",
];

const formatSwapResponse = (
  content: string
): { preview: string; success: boolean } => {
  try {
    if (content.includes("SwapArgs")) {
      const match = content.match(/amount_in=(\d+),\s*amount_out=(\d+)/);
      if (match) {
        const amountIn = parseFloat(match[1]) / 1e18;
        const amountOut = parseFloat(match[2]) / 1e18;
        return {
          preview: `I'll swap ${amountIn.toFixed(
            4
          )} ETH for approximately ${amountOut.toFixed(
            4
          )} UNI tokens.\n\nDoes this look good? Reply with 'yes' to confirm or 'no' to cancel.`,
          success: true,
        };
      }
    }
    return { preview: content, success: false };
  } catch (error) {
    return { preview: content, success: false };
  }
};

// Add this function to format detailed error messages
const formatErrorMessage = (errorContent: any): React.ReactNode => {
  // If it's a standard error string
  if (typeof errorContent === "string") {
    if (errorContent.includes("Unable to find a valid swap route")) {
      return (
        <Box>
          <Text mb={2}>
            I couldn&apos;t find a valid swap route for this transaction. I
            tried:
          </Text>
          <UnorderedList pl={4} spacing={1}>
            <ListItem>0x Protocol</ListItem>
            <ListItem>Brian Protocol</ListItem>
          </UnorderedList>
          <Text mt={2}>This could be due to:</Text>
          <UnorderedList pl={4} spacing={1}>
            <ListItem>Insufficient liquidity for this pair</ListItem>
            <ListItem>Minimum amount requirements not met</ListItem>
            <ListItem>Temporary issues with the protocols</ListItem>
          </UnorderedList>
          <Text mt={2}>
            Please try a different token pair, adjust the amount, or try again
            later.
          </Text>
        </Box>
      );
    }

    // Handle other specific error cases
    if (errorContent.includes("Slippage tolerance exceeded")) {
      return (
        <Box>
          <Text mb={2}>The price moved too much during the transaction.</Text>
          <Text>You can try again with:</Text>
          <UnorderedList pl={4} spacing={1}>
            <ListItem>A smaller amount</ListItem>
            <ListItem>A higher slippage tolerance (default is 0.5%)</ListItem>
          </UnorderedList>
        </Box>
      );
    }
  }

  // If it's an object with detailed error information
  if (typeof errorContent === "object" && errorContent !== null) {
    if (errorContent.protocols_tried) {
      return (
        <Box>
          <Text mb={2}>
            I couldn&apos;t complete the swap. I tried these protocols:
          </Text>
          <UnorderedList pl={4} spacing={1}>
            {errorContent.protocols_tried.map(
              (protocol: string, idx: number) => (
                <ListItem key={idx}>{protocol}</ListItem>
              )
            )}
          </UnorderedList>
          {errorContent.reason && (
            <Text mt={2}>Reason: {errorContent.reason}</Text>
          )}
          {errorContent.suggestion && (
            <Text mt={2}>Suggestion: {errorContent.suggestion}</Text>
          )}
        </Box>
      );
    }

    // Fall back to displaying the error message
    if (errorContent.message) {
      return <Text>{errorContent.message}</Text>;
    }
  }

  // Default case: return the original error content
  return <Text>{String(errorContent)}</Text>;
};

export const CommandResponse: React.FC<CommandResponseProps> = ({
  content,
  timestamp,
  isCommand,
  status = "success",
  awaitingConfirmation = false,
  agentType = "default",
  metadata,
  requires_selection = false,
  all_quotes = [],
  onQuoteSelect,
  transaction,
}) => {
  const [currentStep, setCurrentStep] = React.useState(0);
  const [isLoading, setIsLoading] = React.useState(false);
  const [showTokenInfo, setShowTokenInfo] = React.useState(false);
  const [isExecuting, setIsExecuting] = React.useState(false);
  const [txResponse, setTxResponse] = React.useState<any>(null);
  const [multiStepState, setMultiStepState] = React.useState<{
    steps: any[];
    currentStep: number;
    totalSteps: number;
    isComplete: boolean;
    error?: string;
  } | null>(null);
  const toast = useToast();

  // Wallet and chain info
  const { address } = useAccount();
  const chainId = useChainId();
  const { data: walletClient } = useWalletClient();
  const publicClient = usePublicClient();

  // Services
  const apiService = React.useMemo(() => new ApiService(), []);
  const transactionService = React.useMemo(
    () =>
      walletClient && publicClient && chainId
        ? new TransactionService(walletClient, publicClient, chainId)
        : null,
    [walletClient, publicClient, chainId]
  );

  // Multi-step transaction handler
  const handleMultiStepTransaction = React.useCallback(
    async (txData: any) => {
      if (!transactionService || !address || !chainId) {
        toast({
          title: "Error",
          description: "Wallet not properly connected",
          status: "error",
          duration: 5000,
        });
        return;
      }

      // Initialize multi-step state
      const flowInfo = txData.flow_info || {};
      const currentStepNumber = flowInfo.current_step || 1;

      try {
        setIsExecuting(true);
        setMultiStepState({
          steps: [
            {
              step: flowInfo.current_step || 1,
              stepType: flowInfo.step_type || "approval",
              status: "executing",
              description: txData.message || "Executing transaction...",
            },
          ],
          currentStep: flowInfo.current_step || 1,
          totalSteps: flowInfo.total_steps || 1,
          isComplete: false,
        });

        // Execute the transaction
        const result = await transactionService.executeTransaction(
          txData.transaction
        );

        if (result.success) {
          // Update step as completed
          setMultiStepState((prev) =>
            prev
              ? {
                  ...prev,
                  steps: prev.steps.map((step) =>
                    step.step === (flowInfo.current_step || 1)
                      ? { ...step, status: "completed", hash: result.hash }
                      : step
                  ),
                }
              : null
          );

          // Notify backend of completion and get next step
          const nextStepResponse = await apiService.completeTransactionStep(
            address,
            chainId,
            result.hash as string,
            true
          );

          if (nextStepResponse.success && nextStepResponse.has_next_step) {
            // There's a next step - execute it
            const nextTxData = nextStepResponse.content;

            // Add next step to state
            setMultiStepState((prev) =>
              prev
                ? {
                    ...prev,
                    steps: [
                      ...prev.steps,
                      {
                        step: nextTxData.flow_info.current_step,
                        stepType: nextTxData.flow_info.step_type,
                        status: "pending",
                        description: nextTxData.message,
                      },
                    ],
                    currentStep: nextTxData.flow_info.current_step,
                  }
                : null
            );

            // Small delay before next step
            setTimeout(() => {
              handleMultiStepTransaction(nextTxData);
            }, 2000);
          } else {
            // Transaction flow complete
            setMultiStepState((prev) =>
              prev
                ? {
                    ...prev,
                    isComplete: true,
                  }
                : null
            );

            toast({
              title: "Success!",
              description: "All transaction steps completed successfully",
              status: "success",
              duration: 5000,
            });
          }
        } else {
          throw new Error("Transaction failed");
        }
      } catch (error) {
        const errorMessage =
          error instanceof Error ? error.message : String(error);

        // Update step as failed
        setMultiStepState((prev) =>
          prev
            ? {
                ...prev,
                steps: prev.steps.map((step) =>
                  step.step === currentStepNumber
                    ? { ...step, status: "failed", error: errorMessage }
                    : step
                ),
                error: errorMessage,
              }
            : null
        );

        // Notify backend of failure
        if (address && chainId) {
          try {
            await apiService.completeTransactionStep(
              address,
              chainId,
              "",
              false,
              errorMessage
            );
          } catch (e) {
            console.error(
              "Failed to notify backend of transaction failure:",
              e
            );
          }
        }

        toast({
          title: "Transaction Failed",
          description: errorMessage,
          status: "error",
          duration: 5000,
        });
      } finally {
        setIsExecuting(false);
      }
    },
    [transactionService, address, chainId, apiService, toast]
  );

  // Extract transaction data from content if available
  const transactionData =
    transaction ||
    (typeof content === "object" && content?.transaction) ||
    (typeof content === "object" && content?.content?.transaction);

  const isError = status === "error";
  const isSuccess = status === "success";
  const needsConfirmation = awaitingConfirmation;
  const needsSelection =
    requires_selection && all_quotes && all_quotes.length > 0;

  const bgColor = useColorModeValue(
    isCommand ? "blue.50" : "gray.50",
    isCommand ? "blue.900" : "gray.700"
  );
  const borderColor = useColorModeValue(
    isCommand ? "blue.200" : "gray.200",
    isCommand ? "blue.700" : "gray.600"
  );
  const textColor = useColorModeValue("gray.800", "white");

  // Extract token information from metadata
  const tokenInInfo: TokenInfo = metadata
    ? {
        address: metadata.token_in_address,
        symbol: metadata.token_in_symbol,
        name: metadata.token_in_name,
        verified: metadata.token_in_verified,
        source: metadata.token_in_source,
      }
    : {};

  const tokenOutInfo: TokenInfo = metadata
    ? {
        address: metadata.token_out_address,
        symbol: metadata.token_out_symbol,
        name: metadata.token_out_name,
        verified: metadata.token_out_verified,
        source: metadata.token_out_source,
      }
    : {};

  // Simulate progress through steps when loading
  React.useEffect(() => {
    if (isLoading) {
      const interval = setInterval(() => {
        setCurrentStep((prev) =>
          prev < LoadingSteps.length - 1 ? prev + 1 : prev
        );
      }, 1000);
      return () => clearInterval(interval);
    } else {
      setCurrentStep(0);
    }
  }, [isLoading]);

  // Check for various response types
  const isConfirmation =
    typeof content === "object" && content?.type === "confirmation";
  const isSwapConfirmation =
    typeof content === "object" && content?.type === "swap_confirmation";
  const isDCAConfirmation =
    typeof content === "object" && content?.type === "dca_confirmation";
  const isSwapSuccess =
    typeof content === "object" && content?.type === "swap_success";
  const isSwapTransaction =
    typeof content === "object" && content?.type === "swap_transaction";
  const isDCASuccess =
    typeof content === "object" &&
    (content?.type === "dca_success" || content?.type === "dca_order_created");
  const isMultiStepTransaction =
    typeof content === "object" && content?.type === "multi_step_transaction";
  const isBrianTransaction =
    (typeof content === "object" &&
      content?.type === "transaction" &&
      agentType === "brian") ||
    (agentType === "brian" && transactionData);

  // Handle confirmation actions
  const handleConfirm = () => {
    // Find the closest command input (improved approach that doesn't simulate key events)
    const messageForm = document.querySelector("form");
    const inputElement = messageForm?.querySelector(
      'input[placeholder="Type a command..."]'
    ) as HTMLInputElement | null;

    if (inputElement && messageForm) {
      inputElement.value = "yes";

      // Instead of dispatching keyboard events which may have side effects,
      // trigger the form's submit handler programmatically
      const formSubmitEvent = new Event("submit", {
        bubbles: true,
        cancelable: true,
      });
      messageForm.dispatchEvent(formSubmitEvent);
    } else {
      // Fallback to simpler approach if form can't be found
      const event = new CustomEvent("swap-confirmation", {
        detail: { confirmed: true, command: "yes" },
        bubbles: true,
      });
      document.dispatchEvent(event);

      // Also set a value in session storage as another fallback
      sessionStorage.setItem(
        "swap_confirmation",
        JSON.stringify({ confirmed: true, timestamp: Date.now() })
      );
    }
  };

  const handleCancel = () => {
    // Find the closest command input (improved approach that doesn't simulate key events)
    const messageForm = document.querySelector("form");
    const inputElement = messageForm?.querySelector(
      'input[placeholder="Type a command..."]'
    ) as HTMLInputElement | null;

    if (inputElement && messageForm) {
      inputElement.value = "no";

      // Instead of dispatching keyboard events which may have side effects,
      // trigger the form's submit handler programmatically
      const formSubmitEvent = new Event("submit", {
        bubbles: true,
        cancelable: true,
      });
      messageForm.dispatchEvent(formSubmitEvent);
    } else {
      // Fallback to simpler approach if form can't be found
      const event = new CustomEvent("swap-confirmation", {
        detail: { confirmed: false, command: "no" },
        bubbles: true,
      });
      document.dispatchEvent(event);

      // Also set a value in session storage as another fallback
      sessionStorage.setItem(
        "swap_confirmation",
        JSON.stringify({ confirmed: false, timestamp: Date.now() })
      );
    }
  };

  // Handle quote selection
  const handleQuoteSelect = (quote: any) => {
    if (onQuoteSelect) {
      onQuoteSelect(
        {
          content,
          timestamp,
          isCommand,
          status,
          awaitingConfirmation,
          agentType,
          metadata,
          requires_selection,
          all_quotes,
        },
        quote
      );
    }
  };

  const formatContent = (text: string) => {
    return text.split("\n").map((line, i) => (
      <React.Fragment key={i}>
        {line}
        {i < text.split("\n").length - 1 && <br />}
      </React.Fragment>
    ));
  };

  // Format links in content
  const formatLinks = (text: string | undefined | null) => {
    // Early exit if input is not a string or is empty
    if (typeof text !== "string" || !text) return null;

    // Process markdown-style links first - format: [text](url)
    const markdownLinkRegex = /\[([^\]]+)\]\(([^)]+)\)/g;
    let processedText = text;
    let mdMatch: RegExpExecArray | null;

    // Define the type for the replacements
    interface MarkdownReplacement {
      placeholder: string;
      text: string;
      url: string;
    }

    // Initialize with explicit type
    const mdReplacements = [] as MarkdownReplacement[];

    // Replace markdown links with placeholders to avoid conflicts with URL regex
    while ((mdMatch = markdownLinkRegex.exec(text)) !== null) {
      const placeholderText = `__MARKDOWN_LINK_${mdReplacements.length}__`;
      mdReplacements.push({
        placeholder: placeholderText,
        text: mdMatch[1],
        url: mdMatch[2],
      });
      processedText = processedText.replace(mdMatch[0], placeholderText);
    }

    // Now process regular URLs
    const urlRegex = /(https?:\/\/[^\s]+)/g;
    const parts = processedText.split(urlRegex);

    // Map the parts, handling both regular URLs and our markdown link placeholders
    return parts.map((part, i) => {
      // Check if this part is a URL
      if (part.match(urlRegex)) {
        return (
          <Link key={i} href={part} isExternal color="blue.500">
            {part} <Icon as={ExternalLinkIcon} mx="2px" fontSize="xs" />
          </Link>
        );
      }

      // Check if this part contains any of our markdown link placeholders
      let result = part;
      for (const replacement of mdReplacements) {
        if (part.includes(replacement.placeholder)) {
          // Replace the placeholder with the actual link component
          const beforePlaceholder = part.substring(
            0,
            part.indexOf(replacement.placeholder)
          );
          const afterPlaceholder = part.substring(
            part.indexOf(replacement.placeholder) +
              replacement.placeholder.length
          );

          return (
            <React.Fragment key={i}>
              {beforePlaceholder && formatContent(beforePlaceholder)}
              <Link href={replacement.url} isExternal color="blue.500">
                {replacement.text}{" "}
                <Icon as={ExternalLinkIcon} mx="2px" fontSize="xs" />
              </Link>
              {afterPlaceholder && formatContent(afterPlaceholder)}
            </React.Fragment>
          );
        }
      }

      // If no replacements were needed, just format the content normally
      return formatContent(result);
    });
  };

  // Render status icon
  const renderStatusIcon = () => {
    if (status === "pending") {
      return <InfoIcon color="blue.500" />;
    } else if (status === "processing") {
      return <Spinner size="sm" color="blue.500" />;
    } else if (status === "success") {
      return <CheckCircleIcon color="green.500" />;
    } else if (status === "error") {
      return <WarningIcon color="red.500" />;
    }
    return null;
  };

  // Get agent name and avatar based on agent type
  const getAgentInfo = () => {
    switch (agentType) {
      case "swap":
        return {
          name: "Swap Agent",
          handle: "@swap",
          avatarSrc: "/avatars/🕴️.png",
        };
      case "dca":
        return {
          name: "DCA Agent",
          handle: "@dca",
          avatarSrc: "/avatars/📊.png",
        };
      case "brian":
        return {
          name: "Brian Agent",
          handle: "@brian",
          avatarSrc: "/avatars/🤖.png",
        };
      default:
        return {
          name: "SNEL",
          handle: "@snel",
          avatarSrc: "/icon.png",
        };
    }
  };

  const { name, handle, avatarSrc } = getAgentInfo();

  const getAgentIcon = () => {
    switch (agentType) {
      case "swap":
        return <Icon as={FaExchangeAlt} color="blue.500" />;
      case "dca":
        return <Icon as={FaCalendarAlt} color="green.500" />;
      case "brian":
        return <Icon as={FaRobot} color="purple.500" />;
      default:
        return <Icon as={FaRobot} color="gray.500" />;
    }
  };

  // Render token information if available
  const renderTokenInfo = () => {
    if (!metadata || isCommand || !isSuccess) return null;

    // Only show token info for swap transactions
    if (!content.includes("swap") && !content.includes("Swap")) return null;

    return (
      <Box mt={3} fontSize="sm">
        <Divider mb={2} />
        <Text fontWeight="bold" mb={1}>
          Token Information:
        </Text>

        {tokenInInfo.symbol && (
          <Box mb={2}>
            <Text fontWeight="semibold">From: {tokenInInfo.symbol}</Text>
            {tokenInInfo.name && (
              <Text color="gray.600">{tokenInInfo.name}</Text>
            )}
            {tokenInInfo.address && (
              <Text fontSize="xs" color="gray.500" wordBreak="break-all">
                Address: {tokenInInfo.address}
              </Text>
            )}
            {tokenInInfo.verified && (
              <Badge colorScheme="green" fontSize="xs">
                Verified
              </Badge>
            )}
            {tokenInInfo.source && (
              <Text fontSize="xs" color="gray.500">
                Source: {tokenInInfo.source}
              </Text>
            )}
          </Box>
        )}

        {tokenOutInfo.symbol && (
          <Box>
            <Text fontWeight="semibold">To: {tokenOutInfo.symbol}</Text>
            {tokenOutInfo.name && (
              <Text color="gray.600">{tokenOutInfo.name}</Text>
            )}
            {tokenOutInfo.address && (
              <Text fontSize="xs" color="gray.500" wordBreak="break-all">
                Address: {tokenOutInfo.address}
              </Text>
            )}
            {tokenOutInfo.verified ? (
              <Badge colorScheme="green" fontSize="xs">
                Verified
              </Badge>
            ) : (
              <Badge colorScheme="yellow" fontSize="xs">
                Unverified
              </Badge>
            )}
            {tokenOutInfo.source && (
              <Text fontSize="xs" color="gray.500">
                Source: {tokenOutInfo.source}
              </Text>
            )}
          </Box>
        )}

        {(!tokenInInfo.verified || !tokenOutInfo.verified) && (
          <Alert status="warning" mt={2} size="sm" borderRadius="md">
            <AlertIcon />
            <Box>
              <AlertTitle fontSize="xs">Caution</AlertTitle>
              <AlertDescription fontSize="xs">
                One or more tokens in this transaction are unverified. Always
                double-check contract addresses before proceeding.
              </AlertDescription>
            </Box>
          </Alert>
        )}
      </Box>
    );
  };

  const { getUserDisplayName, profile } = useUserProfile();

  // Add a handler to execute transactions
  const handleExecuteTransaction = React.useCallback(async () => {
    if (!transactionData || !walletClient || !publicClient) {
      toast({
        title: "Transaction Error",
        description: "Missing transaction data or wallet connection",
        status: "error",
        duration: 5000,
        isClosable: true,
      });
      return;
    }

    try {
      setIsExecuting(true);

      // Initialize transaction service
      const txService = new TransactionService(
        walletClient,
        publicClient,
        chainId
      );

      // Execute the transaction
      const result = await txService.executeTransaction(transactionData);

      setTxResponse(result);

      toast({
        title: "Transaction Sent",
        description: `Transaction hash: ${result.hash}`,
        status: "success",
        duration: 5000,
        isClosable: true,
      });
    } catch (error) {
      console.error("Failed to execute transaction:", error);
      toast({
        title: "Transaction Failed",
        description: error instanceof Error ? error.message : "Unknown error",
        status: "error",
        duration: 5000,
        isClosable: true,
      });
    } finally {
      setIsExecuting(false);
    }
  }, [transactionData, walletClient, publicClient, chainId, toast]);

  // Execute the transaction automatically when a transaction is displayed
  React.useEffect(() => {
    // Handle multi-step transactions
    if (isMultiStepTransaction && !isExecuting && !multiStepState) {
      const timeoutId = setTimeout(() => {
        handleMultiStepTransaction(content);
      }, 100);
      return () => clearTimeout(timeoutId);
    }

    // Check if we have single-step transaction data that needs to be executed
    const shouldExecuteTransaction =
      (isBrianTransaction ||
        isSwapTransaction ||
        (typeof content === "object" && content?.type === "swap_quotes")) &&
      transactionData &&
      !isExecuting &&
      !txResponse &&
      !isMultiStepTransaction;

    if (shouldExecuteTransaction) {
      // Add a small delay to ensure UI renders first
      const timeoutId = setTimeout(() => {
        handleExecuteTransaction();
      }, 100);

      return () => clearTimeout(timeoutId);
    }
  }, [
    content,
    transactionData,
    isBrianTransaction,
    isSwapTransaction,
    isMultiStepTransaction,
    isExecuting,
    txResponse,
    multiStepState,
    handleExecuteTransaction,
    handleMultiStepTransaction,
  ]);

  return (
    <Box
      p={3}
      borderRadius="md"
      borderWidth="1px"
      borderColor={borderColor}
      bg={bgColor}
      mb={3}
      position="relative"
      maxW="100%"
    >
      <HStack spacing={2} mb={2} alignItems="flex-start">
        <Avatar
          size="sm"
          name={isCommand ? getUserDisplayName() : "SNEL"}
          src={isCommand ? profile?.avatar || undefined : avatarSrc}
          bg={isCommand ? "blue.500" : "gray.500"}
        />
        <VStack spacing={1} align="flex-start" flex={1}>
          <HStack spacing={2} width="100%" justifyContent="space-between">
            <Badge
              colorScheme={isCommand ? "blue" : "gray"}
              fontSize="xs"
              fontWeight="bold"
            >
              {isCommand
                ? `@${getUserDisplayName().toLowerCase().replace(/\s+/g, "_")}`
                : handle}
            </Badge>
            <Text
              fontSize="xs"
              color="gray.500"
              flexShrink={0}
              ml={1}
              noOfLines={1}
            >
              {new Date(timestamp).toLocaleTimeString()}
            </Text>
          </HStack>

          <Box width="100%">
            {isCommand ? (
              <Text
                color={textColor}
                whiteSpace="pre-wrap"
                wordBreak="break-word"
              >
                {content}
              </Text>
            ) : isSwapConfirmation ? (
              <SwapConfirmation
                message={content}
                onConfirm={handleConfirm}
                onCancel={handleCancel}
              />
            ) : isDCAConfirmation ? (
              <DCAConfirmation
                message={content}
                onConfirm={handleConfirm}
                onCancel={handleCancel}
              />
            ) : isMultiStepTransaction ? (
              <Box>
                <Text color={textColor} mb={3}>
                  {typeof content === "object" && content.message
                    ? content.message
                    : "Executing multi-step transaction..."}
                </Text>
                {multiStepState && (
                  <TransactionProgress
                    steps={multiStepState.steps}
                    currentStep={multiStepState.currentStep}
                    totalSteps={multiStepState.totalSteps}
                    chainId={chainId}
                    isComplete={multiStepState.isComplete}
                    error={multiStepState.error}
                  />
                )}
              </Box>
            ) : isSwapTransaction ? (
              <BrianConfirmation
                message={{
                  type: "transaction",
                  message:
                    content.message || "Ready to execute swap transaction",
                  transaction: transactionData,
                }}
                metadata={metadata}
                onConfirm={handleConfirm}
                onCancel={handleCancel}
                onExecute={handleExecuteTransaction}
              />
            ) : isBrianTransaction ? (
              <BrianConfirmation
                message={{
                  type: "transaction",
                  message:
                    typeof content === "object" && content.message
                      ? content.message
                      : "Ready to execute transaction",
                  transaction: transactionData,
                }}
                metadata={metadata}
                onConfirm={handleConfirm}
                onCancel={handleCancel}
                onExecute={handleExecuteTransaction}
              />
            ) : content.type === "brian_confirmation" ? (
              <BrianConfirmation
                message={{
                  type: "transaction",
                  message:
                    content.message || "Ready to execute bridge transaction",
                  transaction: content.data?.tx_steps
                    ? {
                        to: content.data.tx_steps[0]?.to,
                        data: content.data.tx_steps[0]?.data,
                        value: content.data.tx_steps[0]?.value || "0",
                        chainId: content.data.from_chain?.id,
                        gasLimit:
                          content.data.tx_steps[0]?.gasLimit || "500000",
                        method: "bridge",
                      }
                    : undefined,
                }}
                metadata={{
                  token_symbol: content.data?.token,
                  amount: content.data?.amount,
                  from_chain_id: content.data?.from_chain?.id,
                  to_chain_id: content.data?.to_chain?.id,
                  from_chain_name: content.data?.from_chain?.name,
                  to_chain_name: content.data?.to_chain?.name,
                }}
                onConfirm={handleConfirm}
                onCancel={handleCancel}
                onExecute={handleExecuteTransaction}
              />
            ) : isDCASuccess ? (
              <Box mt={2} mb={2}>
                <Alert status="success" rounded="md">
                  <AlertIcon />
                  <AlertTitle>Success!</AlertTitle>
                  <AlertDescription>
                    {content.type === "dca_order_created"
                      ? "DCA order successfully created. You'll be swapping the specified amount on your chosen schedule."
                      : content.message || "DCA order setup complete."}
                    {content?.type === "error" &&
                      content?.content?.includes("minimum") && (
                        <Box mt={2}>
                          <Alert status="warning" rounded="md" size="sm">
                            <AlertIcon />
                            <Box>
                              <AlertTitle fontSize="sm">
                                DCA Requirements:
                              </AlertTitle>
                              <AlertDescription fontSize="xs">
                                <UnorderedList spacing={1} pl={4}>
                                  <ListItem>
                                    Only available on Base chain
                                  </ListItem>
                                  <ListItem>Minimum $5 per swap</ListItem>
                                  <ListItem>Uses WETH instead of ETH</ListItem>
                                </UnorderedList>
                              </AlertDescription>
                            </Box>
                          </Alert>
                        </Box>
                      )}
                    {metadata?.order_id && (
                      <Box mt={1}>
                        <Text>Order ID: {metadata.order_id}</Text>
                      </Box>
                    )}
                    {metadata?.details?.duration && (
                      <Box mt={1}>
                        <Text>
                          Schedule: {metadata.details.frequency} for{" "}
                          {metadata.details.duration} days
                        </Text>
                      </Box>
                    )}
                  </AlertDescription>
                </Alert>
              </Box>
            ) : needsSelection ? (
              <Box mt={2} width="100%">
                <AggregatorSelection
                  quotes={all_quotes}
                  tokenSymbol={metadata?.token_out_symbol || "tokens"}
                  tokenDecimals={metadata?.token_out_decimals || 18}
                  onSelect={handleQuoteSelect}
                />
              </Box>
            ) : (
              <Text
                fontSize="sm"
                color={textColor}
                wordBreak="break-word"
                overflowWrap="break-word"
                whiteSpace="pre-wrap"
              >
                {typeof content === "string"
                  ? formatLinks(
                      content.startsWith('{"response":')
                        ? JSON.parse(content).response
                        : content
                    )
                  : typeof content === "object" &&
                    content !== null &&
                    content.text
                  ? formatLinks(content.text)
                  : typeof content === "object" &&
                    content !== null &&
                    content.message
                  ? formatLinks(content.message)
                  : typeof content === "object" &&
                    content !== null &&
                    content.response
                  ? formatLinks(content.response)
                  : formatLinks(
                      typeof content === "string"
                        ? content
                        : content !== null && content !== undefined
                        ? JSON.stringify(content, null, 2)
                        : ""
                    )}
              </Text>
            )}

            {awaitingConfirmation &&
              false && ( // Disabling this confirmation section as requested
                <HStack spacing={2} mt={2}>
                  <Badge colorScheme="yellow" alignSelf="flex-start">
                    Needs Confirmation
                  </Badge>
                  <Button size="xs" colorScheme="green" onClick={handleConfirm}>
                    Confirm
                  </Button>
                  <Button size="xs" colorScheme="red" onClick={handleCancel}>
                    Cancel
                  </Button>
                </HStack>
              )}

            {status === "processing" && (
              <Badge colorScheme="blue" alignSelf="flex-start" mt={2}>
                Processing
              </Badge>
            )}

            {status === "error" && (
              <Box mt={3}>
                <Alert status="error" variant="left-accent" borderRadius="md">
                  <AlertIcon />
                  <Box>
                    <AlertTitle mb={1}>Transaction Failed</AlertTitle>
                    <AlertDescription>
                      {typeof content === "object" && content?.error
                        ? formatErrorMessage(content.error)
                        : typeof content === "object" && content?.message
                        ? formatErrorMessage(content.message)
                        : typeof content === "string"
                        ? formatErrorMessage(content)
                        : "An error occurred. Please try again."}
                    </AlertDescription>
                  </Box>
                </Alert>
              </Box>
            )}

            {status === "success" &&
              !isCommand &&
              !isSwapConfirmation &&
              !isDCAConfirmation &&
              !isDCASuccess && (
                <Badge colorScheme="green" alignSelf="flex-start" mt={2}>
                  Success
                </Badge>
              )}
          </Box>
        </VStack>
      </HStack>
    </Box>
  );
};

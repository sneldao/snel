import * as React from "react";
import {
  Box,
  HStack,
  VStack,
  Avatar,
  Text,
  Badge,
  Icon,
  ListItem,
  Spinner,
  Alert,
  AlertIcon,
  AlertTitle,
  AlertDescription,
  useColorModeValue,
  Button,
  UnorderedList,
  useToast,
  Progress,
  useDisclosure,
  SimpleGrid,
} from "@chakra-ui/react";
import { CheckCircleIcon } from "@chakra-ui/icons";
import { UnifiedConfirmation } from "./UnifiedConfirmation";
import { TransactionProgress } from "./TransactionProgress";
import AggregatorSelection from "./AggregatorSelection";
import { FaExchangeAlt, FaChartPie } from "react-icons/fa";
import { useUserProfile } from "../hooks/useUserProfile";
import { ApiService } from "../services/apiService";
import {
  useAccount,
  useChainId,
  useWalletClient,
  usePublicClient,
} from "wagmi";
import { TransactionService } from "../services/transactionService";
import { EnhancedPortfolioSummary } from "./EnhancedPortfolioSummary";
import { PortfolioSummary } from "./PortfolioSummary";
import { Chat } from "./Chat";
import { formatErrorMessage } from "../utils/errorFormatting";
import { formatLinks } from "../utils/linkFormatting";
import { useCommandActions } from "../hooks/useCommandActions";
import { getAgentInfo, type AgentType } from "../utils/agentInfo";
import { CrossChainResult } from "./CrossChain/CrossChainResult";
import { BalanceResult } from "./BalanceResult";
import { ProtocolResearchResult } from "./ProtocolResearchResult";
import { TransactionHandler } from "./Transaction/TransactionHandler";
import { MultiStepTransactionDisplay } from "./Transaction/MultiStepTransactionDisplay";
import { PortfolioModal } from "./Portfolio/PortfolioModal";
import { PortfolioEnablePrompt } from "./Portfolio/PortfolioEnablePrompt";
import { StatusBadge } from "./UI/StatusBadge";
import { LoadingState } from "./UI/LoadingState";
// Removed LoadingSteps import - no longer needed

// Removed unused helper functions - now handled by PortfolioSummary component

interface CommandResponseProps {
  content: string | any; // Updated to accept structured content
  timestamp: string;
  isCommand: boolean;
  status?: "pending" | "processing" | "success" | "error";
  awaitingConfirmation?: boolean;
  agentType?: AgentType;
  metadata?: any;
  requires_selection?: boolean;
  all_quotes?: any[];
  onQuoteSelect?: (response: any, quote: any) => void;
  transaction?: any;
  onActionClick?: (action: any) => void;
}

// Removed TokenInfo type - no longer needed

// Removed LoadingSteps - now imported from constants

// Removed formatSwapResponse and formatErrorMessage - now imported from utils

// Removed ProgressStep component - now imported from shared

export const CommandResponse: React.FC<CommandResponseProps> = (props) => {
  const {
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
    onActionClick,
  } = props;
  const [isExecuting, setIsExecuting] = React.useState(false);
  const [txResponse, setTxResponse] = React.useState<any>(null);
  const [multiStepState, setMultiStepState] = React.useState<{
    steps: any[];
    currentStep: number;
    totalSteps: number;
    isComplete: boolean;
    error?: string;
  } | null>(null);
  const [userRejected, setUserRejected] = React.useState(false);
  const toast = useToast();

  // Modal state for portfolio analysis
  const {
    isOpen: isPortfolioModalOpen,
    onOpen: onPortfolioModalOpen,
    onClose: onPortfolioModalClose,
  } = useDisclosure();

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

        // Check if this is a user rejection
        const isUserRejection =
          errorMessage.toLowerCase().includes("cancelled") ||
          errorMessage.toLowerCase().includes("rejected") ||
          errorMessage.toLowerCase().includes("user denied");

        if (isUserRejection) {
          setUserRejected(true);
        }

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
          title: isUserRejection
            ? "Transaction Cancelled"
            : "Transaction Failed",
          description: isUserRejection
            ? "You cancelled the transaction"
            : errorMessage,
          status: isUserRejection ? "warning" : "error",
          duration: 5000,
        });
      } finally {
        setIsExecuting(false);
      }
    },
    [transactionService, address, chainId, apiService, toast, setUserRejected]
  );

  // Extract transaction data from content if available
  const transactionData =
    transaction ||
    (typeof content === "object" && content?.transaction) ||
    (typeof content === "object" && content?.content?.transaction);

  // Check for various response types (moved before useEffect that uses them)
  const isSwapConfirmation =
    typeof content === "object" && content?.type === "swap_confirmation";
  const isDCAConfirmation =
    typeof content === "object" && content?.type === "dca_confirmation";
  const isSwapTransaction =
    (typeof content === "object" && content?.type === "swap_transaction") ||
    (typeof content === "object" &&
      content?.type === "swap_ready" &&
      agentType === "swap") ||
    (agentType === "swap" && transactionData);
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
  const isBridgeTransaction =
    (typeof content === "object" &&
      content?.type === "bridge_ready" &&
      agentType === "bridge") ||
    (typeof content === "object" &&
      content?.type === "bridge_transaction" &&
      agentType === "bridge") ||
    (agentType === "bridge" && transactionData) ||
    (typeof content === "object" &&
      content?.requires_transaction &&
      agentType === "bridge");
  const isTransferTransaction =
    (typeof content === "object" &&
      content?.type === "transfer_confirmation" &&
      agentType === "transfer") ||
    (typeof content === "object" &&
      content?.type === "transfer_ready" &&
      agentType === "transfer") ||
    (agentType === "transfer" && transactionData);
  const isBalanceResult =
    typeof content === "object" &&
    content?.type === "balance_result" &&
    agentType === "balance";
  const isProtocolResearch =
    typeof content === "object" &&
    content?.type === "protocol_research_result" &&
    agentType === "protocol_research";

  const isCrossChainSuccess =
    typeof content === "object" && 
    content?.type === "cross_chain_success" &&
    content?.axelar_powered === true;

  const isPortfolioDisabled =
    typeof content === "object" && content?.type === "portfolio_disabled";

  // Debug logging for bridge and transfer transactions
  React.useEffect(() => {
    if (
      agentType === "bridge" ||
      agentType === "transfer" ||
      (typeof content === "object" && content?.type === "bridge_ready") ||
      (typeof content === "object" && content?.type === "transfer_confirmation")
    ) {
      console.log("Transaction debug:", {
        agentType,
        content,
        transaction,
        transactionData,
        isBridgeTransaction,
        isTransferTransaction,
        contentType: typeof content === "object" ? content?.type : "string",
        shouldExecuteTransaction:
          (isBrianTransaction ||
            isBridgeTransaction ||
            isTransferTransaction ||
            isSwapTransaction ||
            (typeof content === "object" && content?.type === "swap_quotes")) &&
          transactionData &&
          !isExecuting &&
          !txResponse &&
          !isMultiStepTransaction,
      });
    }
  }, [
    agentType,
    content,
    transaction,
    transactionData,
    isBridgeTransaction,
    isTransferTransaction,
    isBrianTransaction,
    isSwapTransaction,
    isExecuting,
    txResponse,
    isMultiStepTransaction,
  ]);

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

  // Removed token info extraction - no longer needed

  // Removed loading progress effect - no longer needed

  // Using imported command actions hook
  const { handleConfirm, handleCancel, handlePredefinedQuery } =
    useCommandActions();

  // Handle quote selection (local implementation needed for specific signature)
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

  // Removed formatContent - no longer needed

  // Using imported getAgentInfo function
  const { handle, avatarSrc } = getAgentInfo(agentType);

  // Using imported getAgentIcon function

  // Removed renderTokenInfo - now using imported TokenInfo component

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

    // Don't execute if user already rejected
    if (userRejected) {
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

      // Check if this is a user rejection
      const errorMessage =
        error instanceof Error ? error.message : "Unknown error";
      const isUserRejection =
        errorMessage.toLowerCase().includes("cancelled") ||
        errorMessage.toLowerCase().includes("rejected") ||
        errorMessage.toLowerCase().includes("user denied");

      if (isUserRejection) {
        setUserRejected(true);
        toast({
          title: "Transaction Cancelled",
          description: "You cancelled the transaction",
          status: "warning",
          duration: 3000,
          isClosable: true,
        });
      } else {
        toast({
          title: "Transaction Failed",
          description: errorMessage,
          status: "error",
          duration: 5000,
          isClosable: true,
        });
      }
    } finally {
      setIsExecuting(false);
    }
  }, [
    transactionData,
    walletClient,
    publicClient,
    chainId,
    toast,
    userRejected,
  ]);

  // Don't reset user rejection state automatically - let user manually retry if needed

  // Execute the transaction automatically when a transaction is displayed
  React.useEffect(() => {
    // Don't auto-execute if user has rejected
    if (userRejected) {
      return;
    }

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
        isBridgeTransaction ||
        isTransferTransaction ||
        isSwapTransaction ||
        (typeof content === "object" && content?.type === "swap_quotes")) &&
      transactionData &&
      !isExecuting &&
      !txResponse &&
      !isMultiStepTransaction &&
      !userRejected;

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
    isBridgeTransaction,
    isTransferTransaction,
    isSwapTransaction,
    isMultiStepTransaction,
    isExecuting,
    txResponse,
    multiStepState,
    userRejected,
    handleExecuteTransaction,
    handleMultiStepTransaction,
  ]);

  // Extract portfolio analysis data for modal
  const portfolioAnalysis =
    typeof content === "object" && content.analysis ? content.analysis : null;

  // Function to handle portfolio action clicks
  const handleActionClick = (action: any) => {
    // Handle stablecoin diversification action
    if (action.id === "diversify_into_stablecoins") {
      // Close the deep dive modal
      onPortfolioModalClose();

      // Add SNEL message suggesting swap command
      if (onActionClick) {
        onActionClick({
          type: "stablecoin_suggestion",
          message:
            "To diversify into stablecoins, you can write: **'swap 1 ETH to USDC'** (or any amount you prefer). This will help reduce your portfolio risk and provide stability.",
        });
      }
      return;
    }

    // Handle other actions normally
    if (onActionClick) {
      onActionClick(action);
    }
  };

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
              <UnifiedConfirmation
                agentType="swap"
                content={{
                  message:
                    typeof content === "object" && content.message
                      ? content.message
                      : "Ready to swap tokens",
                  type: "swap_confirmation",
                  details: typeof content === "object" ? content : {},
                }}
                transaction={transactionData}
                metadata={metadata}
                onExecute={handleExecuteTransaction}
                onCancel={handleCancel}
                isLoading={isExecuting}
              />
            ) : isDCAConfirmation ? (
              <UnifiedConfirmation
                agentType="swap"
                content={{
                  message:
                    typeof content === "object" && content.message
                      ? content.message
                      : "Ready to set up DCA",
                  type: "dca_confirmation",
                  details: typeof content === "object" ? content : {},
                }}
                transaction={transactionData}
                metadata={metadata}
                onExecute={handleExecuteTransaction}
                onCancel={handleCancel}
                isLoading={isExecuting}
              />
            ) : isMultiStepTransaction ? (
              <MultiStepTransactionDisplay
                content={content}
                multiStepState={multiStepState}
                chainId={chainId}
                textColor={textColor}
              />
            ) : isSwapTransaction ? (
              <TransactionHandler
                agentType="swap"
                content={content}
                transactionData={transactionData}
                metadata={metadata}
                isExecuting={isExecuting}
                onExecute={handleExecuteTransaction}
                onCancel={handleCancel}
              />
            ) : isBrianTransaction ? (
              <TransactionHandler
                agentType="brian"
                content={content}
                transactionData={transactionData}
                metadata={metadata}
                isExecuting={isExecuting}
                onExecute={handleExecuteTransaction}
                onCancel={handleCancel}
              />
            ) : isBridgeTransaction ? (
              <TransactionHandler
                agentType="bridge"
                content={content}
                transactionData={transactionData}
                metadata={metadata}
                isExecuting={isExecuting}
                onExecute={handleExecuteTransaction}
                onCancel={handleCancel}
              />
            ) : isTransferTransaction ? (
              <TransactionHandler
                agentType="transfer"
                content={content}
                transactionData={transactionData}
                metadata={metadata}
                isExecuting={isExecuting}
                onExecute={handleExecuteTransaction}
                onCancel={handleCancel}
              />
            ) : content.type === "brian_confirmation" ? (
              <UnifiedConfirmation
                agentType="bridge"
                content={{
                  message:
                    content.message || "Ready to execute bridge transaction",
                  type: "brian_confirmation",
                  details: {
                    token: content.data?.token,
                    amount: content.data?.amount,
                    source_chain: content.data?.from_chain?.name,
                    destination_chain: content.data?.to_chain?.name,
                  },
                }}
                transaction={
                  content.data?.tx_steps
                    ? {
                        to: content.data.tx_steps[0]?.to,
                        data: content.data.tx_steps[0]?.data,
                        value: content.data.tx_steps[0]?.value || "0",
                        chain_id: content.data.from_chain?.id,
                        gas_limit:
                          content.data.tx_steps[0]?.gasLimit || "500000",
                      }
                    : undefined
                }
                metadata={{
                  token_symbol: content.data?.token,
                  amount: content.data?.amount,
                  from_chain_id: content.data?.from_chain?.id,
                  to_chain_id: content.data?.to_chain?.id,
                  from_chain_name: content.data?.from_chain?.name,
                  to_chain_name: content.data?.to_chain?.name,
                }}
                onExecute={handleExecuteTransaction}
                onCancel={handleCancel}
                isLoading={isExecuting}
              />
            ) : isBalanceResult ? (
              <BalanceResult content={content} />
            ) : isProtocolResearch ? (
              <ProtocolResearchResult content={content} />
            ) : isPortfolioDisabled ? (
              <PortfolioEnablePrompt
                suggestion={typeof content === "object" ? content.suggestion : {
                  title: "Enable Portfolio Analysis",
                  description: "Get detailed insights about your holdings",
                  features: ["Holdings analysis", "Risk assessment", "Optimization tips"],
                  warning: "Analysis takes 10-30 seconds"
                }}
                onEnable={() => {
                  // This will be handled by MainApp
                  if (onActionClick) {
                    onActionClick({
                      type: "enable_portfolio",
                      message: "Portfolio analysis enabled"
                    });
                  }
                }}
              />
            ) : isCrossChainSuccess ? (
              <CrossChainResult 
                content={typeof content === "object" ? content : { type: "cross_chain_success" }}
                metadata={metadata}
              />
            ) : agentType === "agno" || agentType === "portfolio" ? (
              <VStack spacing={4} align="stretch" w="100%">
                {/* Enhanced Portfolio Summary */}
                <EnhancedPortfolioSummary
                  response={{
                    analysis:
                      typeof content === "object"
                        ? content.analysis
                        : undefined,
                    summary:
                      typeof content === "object"
                        ? content.analysis?.summary
                        : content,
                    fullAnalysis:
                      typeof content === "object"
                        ? content.analysis?.fullAnalysis
                        : undefined,
                    content:
                      typeof content === "object"
                        ? content.analysis?.summary
                        : content,
                    status: status,
                    metadata: metadata,
                  }}
                  onActionClick={handleActionClick}
                  isLoading={status === "processing"}
                />

                {/* Action Buttons - Only show when analysis is complete */}
                {status === "success" && (
                  <HStack spacing={4} justify="center" mt={4}>
                    <Button
                      colorScheme="blue"
                      size="md"
                      onClick={onPortfolioModalOpen}
                      leftIcon={<Icon as={FaChartPie} />}
                    >
                      Deep Dive Analysis
                    </Button>
                    <Button
                      colorScheme="teal"
                      size="md"
                      onClick={() => {
                        // Trigger the same stablecoin suggestion as rebalance
                        handleActionClick({
                          type: "stablecoin_suggestion",
                          message:
                            "To optimize your portfolio, consider diversifying into stablecoins. You can write: **'swap 1 ETH to USDC'** (or any amount you prefer). This will help reduce risk and provide stability.",
                        });
                      }}
                      leftIcon={<Icon as={FaExchangeAlt} />}
                    >
                      Optimize Portfolio
                    </Button>
                  </HStack>
                )}
              </VStack>
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

            {status === "processing" &&
              agentType !== "agno" &&
              agentType !== "portfolio" && (
                <StatusBadge status="processing" animated={true} />
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
                <StatusBadge status="success" />
              )}
          </Box>
        </VStack>
      </HStack>

      {/* Portfolio Analysis Modal - Detailed Analysis with Actions */}
      <PortfolioModal
        isOpen={isPortfolioModalOpen}
        onClose={onPortfolioModalClose}
        portfolioAnalysis={portfolioAnalysis}
        metadata={metadata}
        onActionClick={handleActionClick}
      />
    </Box>
  );
};

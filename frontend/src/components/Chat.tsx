import React, { useState, useEffect, useRef } from "react";
import {
  VStack,
  Box,
  Input,
  Button,
  Text,
  useToast,
  Flex,
  Divider,
  Badge,
  Progress,
  Collapse,
  IconButton,
  HStack,
  SimpleGrid,
  Wrap,
  WrapItem,
  useColorModeValue,
} from "@chakra-ui/react";
import { ChevronDownIcon, ChevronUpIcon } from "@chakra-ui/icons";
import { useAccount, useChainId, useSignTypedData } from "wagmi";
import {
  PortfolioService,
  PortfolioAnalysis,
  AnalysisProgress,
} from "../services/portfolioService";
import { ApiService } from "../services/apiService";
import { TerminalProgress } from "./shared/TerminalProgress";
import { PortfolioSummary } from "./PortfolioSummary";
import { UnifiedConfirmation } from "./UnifiedConfirmation";

interface Message {
  id: string;
  type: "user" | "assistant" | "system" | "progress";
  content: string;
  timestamp: Date;
  metadata?: {
    stage?: string;
    progress?: number;
    agent?: string;
    reasoning?: string[];
    steps?: AnalysisProgress[];
  };
}

interface WorkflowStage {
  id: "portfolio" | "market" | "strategy";
  name: string;
  status: "pending" | "active" | "completed" | "error";
  agent: string;
  progress: number;
  output?: any;
}

interface ProgressStep {
  stage: string;
  type: "progress" | "error" | "thought" | "action";
  completion?: number;
  details?: string;
}

interface ProgressUpdate {
  type: "progress" | "thought" | "action" | "error";
  message: string;
  agent?: string;
  stage?: string;
  reasoning?: string[];
}

interface ChatProps {
  portfolioMode?: boolean;
  initialAnalysis?: PortfolioAnalysis;
}

export const Chat: React.FC<ChatProps> = ({
  portfolioMode = false,
  initialAnalysis,
}): React.ReactNode => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [currentWorkflow, setCurrentWorkflow] = useState<WorkflowStage[]>([
    {
      id: "portfolio",
      name: "Portfolio Analysis",
      status: "pending",
      agent: "ChainScope-X",
      progress: 0,
    },
    {
      id: "market",
      name: "Market Context",
      status: "pending",
      agent: "TrendSage-X",
      progress: 0,
    },
    {
      id: "strategy",
      name: "Strategy Optimization",
      status: "pending",
      agent: "AlphaQuest-X",
      progress: 0,
    },
  ]);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const toast = useToast();
  const { address } = useAccount();
  const chainId = useChainId();
  const { signTypedData } = useSignTypedData();
  const apiService = new ApiService();
  const portfolioService = new PortfolioService(apiService);
  const [currentAnalysis, setCurrentAnalysis] =
    useState<PortfolioAnalysis | null>(initialAnalysis || null);
  const [progressSteps, setProgressSteps] = useState<AnalysisProgress[]>([]);
  const [pendingPayment, setPendingPayment] = useState<any>(null);
  const [isExecutingPayment, setIsExecutingPayment] = useState(false);
  const [paymentSuccess, setPaymentSuccess] = useState(false);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Initialize with welcome message and analysis if in portfolio mode
  useEffect(() => {
    if (portfolioMode && initialAnalysis && messages.length === 0) {
      const welcomeMessage: Message = {
        id: `system-${Date.now()}`,
        type: "system",
        content:
          "Welcome to Portfolio Deep Dive! Ask me anything about your portfolio analysis.",
        timestamp: new Date(),
      };

      const analysisMessage: Message = {
        id: `assistant-${Date.now()}`,
        type: "assistant",
        content: initialAnalysis.summary,
        timestamp: new Date(),
        metadata: {
          reasoning: initialAnalysis.keyInsights,
        },
      };

      setMessages([welcomeMessage, analysisMessage]);
    }
  }, [portfolioMode, initialAnalysis, messages.length]);

  const handleProgress = (progress: AnalysisProgress) => {
    console.log("Progress update:", progress);

    // Add to progress steps for display
    setProgressSteps((prev) => [...prev, progress]);

    // Update workflow stages based on progress
    setCurrentWorkflow((stages) =>
      stages.map((stage) => {
        if (
          progress.stage.toLowerCase().includes(stage.name.toLowerCase()) ||
          (progress.stage.toLowerCase().includes("portfolio") &&
            stage.name.toLowerCase().includes("portfolio")) ||
          (progress.stage.toLowerCase().includes("analyzing") &&
            stage.name.toLowerCase().includes("analysis"))
        ) {
          return {
            ...stage,
            status: progress.type === "error" ? "error" : "active",
            progress: progress.completion || 0,
          };
        }
        return stage;
      })
    );

    // Update the existing progress message with the latest stage and all collected steps
    setMessages((msgs) => {
      // Find the progress message in the current messages
      const progressIndex = msgs.findIndex((msg) => msg.type === "progress");

      if (progressIndex >= 0) {
        // Update the existing progress message
        const updatedMsgs = [...msgs];
        const currentSteps = updatedMsgs[progressIndex].metadata?.steps || [];

        updatedMsgs[progressIndex] = {
          ...updatedMsgs[progressIndex],
          content: progress.stage,
          metadata: {
            stage: progress.stage,
            progress: progress.completion,
            reasoning: progress.details ? [progress.details] : undefined,
            steps: [...currentSteps, progress],
          },
        };

        return updatedMsgs;
      } else {
        // Create a new progress message if none exists
        const progressMessage: Message = {
          id: `progress-${Date.now()}-${Math.random()
            .toString(36)
            .substr(2, 9)}`,
          type: "progress",
          content: progress.stage,
          timestamp: new Date(),
          metadata: {
            stage: progress.stage,
            progress: progress.completion,
            reasoning: progress.details ? [progress.details] : undefined,
            steps: [progress],
          },
        };
        return [...msgs, progressMessage];
      }
    });
  };

  const handlePaymentExecution = async (paymentData: any) => {
    if (!address) {
      toast({
        title: "Wallet not connected",
        description: "Please connect your wallet first",
        status: "error",
        isClosable: true,
      });
      return;
    }

    try {
      setIsExecutingPayment(true);

      const apiUrl =
        process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

      // Step 1: Prepare payment (get EIP-712 payload)
      const prepareResponse = await fetch(
        `${apiUrl}/api/v1/x402/prepare-payment`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            user_address: address,
            recipient_address: paymentData.recipient,
            amount_usdc: paymentData.amount,
            network: paymentData.network || "cronos-testnet",
          }),
        }
      );

      if (!prepareResponse.ok) {
        throw new Error("Failed to prepare payment");
      }

      const payload = await prepareResponse.json();

      // Step 2: Sign with Wagmi
      if (!signTypedData) {
        throw new Error("Signing not available");
      }

      const signature = await signTypedData({
        domain: payload.domain,
        types: payload.types,
        primaryType: payload.primaryType,
        message: {
          ...payload.message,
          from: address,
        },
        account: address as `0x${string}`,
      });

      // Step 3: Submit signed payment
      const submitResponse = await fetch(
        `${apiUrl}/api/v1/x402/submit-payment`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            signature,
            user_address: address,
            message: payload.message,
            metadata: payload.metadata,
          }),
        }
      );

      if (!submitResponse.ok) {
        throw new Error("Failed to submit payment");
      }

      const result = await submitResponse.json();

      // Step 4: Show success
      toast({
        title: "Payment Successful",
        description: `Transaction: ${result.txHash}`,
        status: "success",
        isClosable: true,
        duration: 5000,
      });

      // Add to chat history
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now().toString(),
          type: "system",
          content: `✅ Payment confirmed. TX: ${result.txHash}`,
          timestamp: new Date(),
        },
      ]);


      setPaymentSuccess(true);

      // Auto-clear success after 3 seconds
      setTimeout(() => {
        setPendingPayment(null);
        setPaymentSuccess(false);
      }, 3000);
    } catch (error) {
      const errorMsg =
        error instanceof Error ? error.message : "Unknown error";
      console.error("Payment execution failed:", error);

      toast({
        title: "Payment Failed",
        description: errorMsg,
        status: "error",
        isClosable: true,
        duration: 5000,
      });
    } finally {
      setIsExecutingPayment(false);
    }
  };

  const handleSubmit = async () => {
    if (!input.trim()) return;

    const userMessage: Message = {
      id: `user-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      type: "user",
      content: input,
      timestamp: new Date(),
    };

    setMessages((msgs) => [...msgs, userMessage]);
    const command = input;
    setInput("");
    setIsAnalyzing(true);

    // Proactive Zero-State Check: No Wallet
    if (!address) {
      setMessages((msgs) => [...msgs, {
        id: `assistant-${Date.now()}`,
        type: "assistant",
        content: "I've noticed your wallet isn't connected yet. To execute payments, swaps, or portfolio analysis, I'll need a connection. Would you like to connect using MetaMask or WalletConnect?",
        timestamp: new Date(),
        metadata: {
          stage: "onboarding",
          reasoning: ["Wallet connection required for transactions"]
        }
      }]);
      setIsAnalyzing(false);
      return;
    }

    try {
      // Check for portfolio commands first
      if (
        /portfolio|allocation|holdings|assets|analyze/i.test(command.toLowerCase())
      ) {
        await handlePortfolioAnalysis(command);
      } else {
        // Process regular commands via API
        const response = await apiService.processCommand(
          command,
          address,
          chainId
        );

        // Handle payment responses
        if (response.agent_type === "payment" || response.content?.type === "payment") {
          setPendingPayment({
            ...response.content?.details,
            message: response.content?.message || "Confirm payment",
          });

          // Add response message to chat
          const paymentMessage: Message = {
            id: `assistant-${Date.now()}`,
            type: "assistant",
            content: response.content?.message || "Ready for payment confirmation",
            timestamp: new Date(),
            metadata: {
              stage: "payment_confirmation",
              progress: 0,
              reasoning: ["Payment confirmation required"],
            },
          };
          setMessages((msgs) => [...msgs, paymentMessage]);
        } else {
          // Add other responses to chat
          const responseMessage: Message = {
            id: `assistant-${Date.now()}`,
            type: "assistant",
            content: response.content?.message || JSON.stringify(response.content),
            timestamp: new Date(),
            metadata: {
              stage: response.content?.type || "response",
              progress: 100,
            },
          };
          setMessages((msgs) => [...msgs, responseMessage]);
        }
      }
    } catch (error) {
      const errorMsg =
        error instanceof Error ? error.message : "Failed to process command";
      console.error("Command processing error:", error);


      // Agentic Error Guidance
      let guidance = errorMsg;
      if (errorMsg.includes("insufficient funds") || errorMsg.includes("low balance")) {
        guidance = `It looks like you have insufficient funds for this transaction. If you're on Cronos Testnet, you can get free TCRO and USDC from the Official Faucets: https://cronos.org/faucet and https://faucet.cronos.org`;
      } else if (errorMsg.includes("user rejected")) {
        guidance = "Transaction was cancelled. No worries! If you're ready to try again, just let me know.";
      }

      setMessages((msgs) => [
        ...msgs,
        {
          id: `error-${Date.now()}`,
          type: "assistant", // Use assistant for guidance
          content: guidance,
          timestamp: new Date(),
          metadata: {
            stage: "error_guidance",
            reasoning: [errorMsg]
          }
        },
      ]);
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handlePortfolioAnalysis = async (input: string) => {
    setIsAnalyzing(true);

    // Clear previous progress
    setProgressSteps([]);

    // Initialize a single progress message
    const initialProgressMessage: Message = {
      id: `progress-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      type: "progress",
      content: "Starting portfolio analysis...",
      timestamp: new Date(),
      metadata: {
        stage: "Starting portfolio analysis...",
        progress: 0,
        steps: [],
      },
    };
    setMessages((msgs) => [...msgs, initialProgressMessage]);

    setCurrentWorkflow((stages) =>
      stages.map((stage) => ({
        ...stage,
        status: "pending" as const,
        progress: 0,
        output: undefined,
      }))
    );

    try {
      // Use actual connected wallet address and chain
      if (!address) {
        throw new Error("Wallet not connected");
      }

      const analysis = await portfolioService.analyzePortfolio(
        input,
        address, // Use actual connected wallet address
        chainId, // Use actual connected chain ID
        handleProgress
      );

      // Store the analysis for the component
      setCurrentAnalysis(analysis);

      // Mark the analysis as complete
      setCurrentWorkflow((stages) =>
        stages.map((stage) => ({
          ...stage,
          status: "completed" as const,
          progress: 100,
        }))
      );

      // Replace the progress message with the result
      setMessages((msgs) => {
        // Find and remove the progress message
        const filteredMsgs = msgs.filter((msg) => msg.type !== "progress");

        // Add the assistant message with the analysis result
        const assistantMessage: Message = {
          id: `assistant-${Date.now()}-${Math.random()
            .toString(36)
            .substr(2, 9)}`,
          type: "assistant",
          content: analysis.summary,
          timestamp: new Date(),
          metadata: {
            reasoning: analysis.keyInsights,
          },
        };

        return [...filteredMsgs, assistantMessage];
      });
    } catch (error) {
      console.error("Analysis failed:", error);
      // Add a more helpful error message
      const errorMessage =
        error instanceof Error
          ? error.message
          : "Failed to analyze portfolio. Please try again.";

      // Add a system message showing the error
      setMessages((prev) => [
        ...prev,
        {
          id: `error-${Date.now()}`,
          type: "system",
          content: `Error: ${errorMessage}`,
          timestamp: new Date(),
          metadata: {
            stage: "Error",
            progress: 0,
          },
        },
      ]);

      toast({
        title: "Analysis Failed",
        description: errorMessage,
        status: "error",
        duration: 5000,
        isClosable: true,
      });

      setCurrentWorkflow((stages) =>
        stages.map((stage) => ({
          ...stage,
          status: stage.status === "active" ? ("error" as const) : stage.status,
        }))
      );
    } finally {
      setIsAnalyzing(false);
    }
  };

  const renderWorkflowProgress = () => (
    <Box w="100%" bg="whiteAlpha.50" p={4} borderRadius="xl" mb={4}>
      <Text fontSize="lg" fontWeight="medium" mb={4}>
        Analysis Workflow
      </Text>
      <VStack spacing={4} align="stretch">
        {currentWorkflow.map((stage) => (
          <Box key={stage.id}>
            <HStack justify="space-between" mb={2}>
              <HStack>
                <Badge
                  colorScheme={
                    stage.status === "completed"
                      ? "green"
                      : stage.status === "error"
                        ? "red"
                        : stage.status === "active"
                          ? "blue"
                          : "gray"
                  }
                >
                  {stage.agent}
                </Badge>
                <Text>{stage.name}</Text>
              </HStack>
              <Text fontSize="sm" color="whiteAlpha.700">
                {stage.progress}%
              </Text>
            </HStack>
            <Progress
              value={stage.progress}
              size="sm"
              colorScheme={
                stage.status === "completed"
                  ? "green"
                  : stage.status === "error"
                    ? "red"
                    : "blue"
              }
              borderRadius="full"
            />
          </Box>
        ))}
      </VStack>
    </Box>
  );

  // Move color mode values to component level
  const suggestionsBgColor = useColorModeValue("gray.50", "whiteAlpha.50");
  const suggestionsBorderColor = useColorModeValue(
    "gray.200",
    "whiteAlpha.200"
  );

  const renderSuggestedCommands = () => {
    const suggestions = [
      { text: "analyze my portfolio", category: "Portfolio" },
      { text: "swap 1 ETH for USDC", category: "Trading" },
      { text: "tell me about Aave", category: "Research" },
      { text: "bridge 0.1 ETH to Base", category: "Bridge" },
      { text: "what's my USDC balance?", category: "Balance" },
      { text: "show me my risk assessment", category: "Portfolio" },
      { text: "research Compound protocol", category: "Research" },
      { text: "setup portfolio rebalancing with 50 USDC", category: "X402" },
      { text: "pay 20 USDC when ETH drops below $3000", category: "X402" },
    ];

    return (
      <Box
        w="100%"
        bg={suggestionsBgColor}
        p={{ base: 3, md: 4 }}
        borderRadius="xl"
        borderWidth="1px"
        borderColor={suggestionsBorderColor}
        mb={4}
        overflowX="auto"
      >
        <Text fontSize="sm" fontWeight="medium" mb={3} color="gray.600">
          Try asking me something like:
        </Text>
        <Wrap spacing={{ base: 1, md: 2 }}>
          {suggestions.map((suggestion, index) => (
            <WrapItem key={index}>
              <Button
                size="sm"
                variant="outline"
                colorScheme="blue"
                fontSize={{ base: "2xs", sm: "xs" }}
                py={{ base: 1, md: 2 }}
                px={{ base: 2, md: 3 }}
                onClick={() => setInput(suggestion.text)}
                _hover={{ bg: "blue.50" }}
                whiteSpace="normal"
                height="auto"
                textAlign="left"
              >
                {suggestion.text}
              </Button>
            </WrapItem>
          ))}
        </Wrap>
      </Box>
    );
  };

  // Removed old renderAnalysisView - now using PortfolioSummary directly

  const renderMessage = (message: Message) => {
    switch (message.type) {
      case "user":
        return (
          <Box
            alignSelf="flex-end"
            bg="blue.500"
            color="white"
            px={{ base: 3, md: 4 }}
            py={{ base: 1.5, md: 2 }}
            borderRadius="2xl"
            maxW={{ base: "85%", md: "70%" }}
            wordBreak="break-word"
          >
            <Text fontSize={{ base: "sm", md: "md" }}>{message.content}</Text>
          </Box>
        );
      case "system":
        return (
          <Box
            bg="whiteAlpha.100"
            p={{ base: 2, md: 3 }}
            borderRadius="lg"
            borderWidth="1px"
            borderColor="whiteAlpha.200"
            textAlign="center"
            w="100%"
          >
            <Text fontSize={{ base: "xs", md: "sm" }} color="whiteAlpha.700">
              {message.content}
            </Text>
          </Box>
        );
      case "assistant":
        return (
          <VStack align="stretch" maxW="100%" spacing={4}>
            {message.metadata?.stage === "payment_confirmation" && pendingPayment ? (
              <UnifiedConfirmation
                agentType="payment"
                content={{
                  message: pendingPayment.message || message.content,
                  type: "payment",
                  details: {
                    recipient: pendingPayment.recipient,
                    amount: pendingPayment.amount,
                    token: pendingPayment.token || "USDC",
                    network: pendingPayment.network || "cronos-testnet",
                  },
                }}
                onExecute={() => handlePaymentExecution(pendingPayment)}
                onCancel={() => setPendingPayment(null)}
                isLoading={isExecutingPayment}
                isSuccess={paymentSuccess}
              />
            ) : currentAnalysis ? (
              <PortfolioSummary
                response={{
                  analysis: currentAnalysis,
                  summary: currentAnalysis.summary,
                  fullAnalysis: currentAnalysis.fullAnalysis,
                  content: currentAnalysis.summary,
                }}
                onActionClick={(action) => {
                  if (action.type === "retry") {
                    // Retry the analysis
                    handlePortfolioAnalysis("analyze my portfolio");
                  } else if (action.type === "stablecoin_suggestion") {
                    // Add SNEL message suggesting swap command
                    const actionMessage: Message = {
                      id: Date.now().toString(),
                      content:
                        (action as any).message ||
                        "Consider diversifying into stablecoins for better portfolio stability.",
                      type: "assistant",
                      timestamp: new Date(),
                      metadata: {
                        agent: "snel",
                      },
                    };
                    setMessages((prev) => [...prev, actionMessage]);
                  } else if (action.id === "diversify_into_stablecoins") {
                    // Legacy handler - trigger stablecoin diversification swap
                    const swapCommand = "swap 0.1 eth for usdc";
                    setInput(swapCommand);
                    // Add a message to explain the action
                    const actionMessage: Message = {
                      id: Date.now().toString(),
                      content: `Initiating stablecoin diversification. How much ETH would you like to swap to USDC?`,
                      type: "assistant",
                      timestamp: new Date(),
                      metadata: {
                        agent: "swap",
                      },
                    };
                    setMessages((prev) => [...prev, actionMessage]);
                  }
                }}
              />
            ) : (
              <Box
                bg="whiteAlpha.50"
                p={{ base: 3, md: 4 }}
                borderRadius="xl"
                borderWidth="1px"
                borderColor="whiteAlpha.200"
                w="100%"
              >
                <Text
                  fontSize={{ base: "sm", md: "md" }}
                  wordBreak="break-word"
                >
                  {message.content}
                </Text>
              </Box>
            )}
          </VStack>
        );
      case "progress":
        return (
          <Box maxW="100%" mb={2} w="100%">
            <Box
              bg="whiteAlpha.50"
              p={{ base: 3, md: 4 }}
              borderRadius="lg"
              borderWidth="1px"
              borderColor="whiteAlpha.200"
            >
              <VStack spacing={3} align="stretch">
                <Flex
                  direction={{ base: "column", sm: "row" }}
                  justify="space-between"
                  align={{ base: "flex-start", sm: "center" }}
                  gap={{ base: 2, sm: 0 }}
                >
                  <VStack align="start" spacing={1}>
                    <Text
                      fontSize={{ base: "xs", md: "sm" }}
                      fontWeight="medium"
                      color="white"
                    >
                      {message.content}
                    </Text>
                    {message.metadata?.reasoning?.[0] && (
                      <Text
                        fontSize={{ base: "2xs", md: "xs" }}
                        color="whiteAlpha.600"
                      >
                        {message.metadata.reasoning[0]}
                      </Text>
                    )}
                  </VStack>
                  <Text
                    fontSize="xs"
                    color="whiteAlpha.700"
                    fontWeight="bold"
                    flexShrink={0}
                  >
                    {message.metadata?.progress || 0}%
                  </Text>
                </Flex>
                <Progress
                  value={message.metadata?.progress || 0}
                  size="md"
                  colorScheme="blue"
                  borderRadius="full"
                  bg="whiteAlpha.200"
                  hasStripe
                  isAnimated={message.metadata?.progress !== 100}
                />
                {isAnalyzing &&
                  message.metadata?.steps &&
                  message.metadata.steps.length > 0 && (
                    <TerminalProgress
                      steps={message.metadata.steps.map((step) => ({
                        stage: step.stage,
                        type: step.type,
                        completion: step.completion,
                        details: step.details,
                      }))}
                      isComplete={!isAnalyzing}
                    />
                  )}
              </VStack>
            </Box>
          </Box>
        );
      default:
        return null;
    }
  };

  return (
    <VStack h={{ base: "calc(100vh - 60px)", md: "100vh" }} spacing={0}>
      <Box flex={1} w="100%" overflowY="auto" p={{ base: 2, md: 4 }}>
        <VStack spacing={6} align="stretch">
          {/* Show suggested commands when chat is empty and not in portfolio mode */}
          {messages.length === 0 && !portfolioMode && renderSuggestedCommands()}

          {messages.map((msg) => (
            <Box
              key={msg.id}
              alignSelf={msg.type === "user" ? "flex-end" : "flex-start"}
              w={msg.type === "assistant" ? "100%" : "auto"}
              maxW="100%"
            >
              {renderMessage(msg)}
            </Box>
          ))}
          <div ref={messagesEndRef} />
        </VStack>
      </Box>
      <Box
        w="100%"
        p={{ base: 2, md: 4 }}
        borderTop="1px"
        borderColor="whiteAlpha.200"
        position="sticky"
        bottom={0}
        bg="inherit"
        zIndex={1}
      >
        <Flex
          direction={{ base: "column", sm: "row" }}
          gap={{ base: 2, sm: 0 }}
        >
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={
              portfolioMode
                ? "Ask me more about your portfolio..."
                : "Ask about your portfolio..."
            }
            mr={{ base: 0, sm: 2 }}
            mb={{ base: 2, sm: 0 }}
            disabled={isAnalyzing}
            onKeyPress={(e) => e.key === "Enter" && handleSubmit()}
          />
          <Button
            onClick={handleSubmit}
            colorScheme="blue"
            isLoading={isAnalyzing}
            flexShrink={0}
            width={{ base: "full", sm: "auto" }}
          >
            Send
          </Button>
        </Flex>
      </Box>
    </VStack>
  );
};

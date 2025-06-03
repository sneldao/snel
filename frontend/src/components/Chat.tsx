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
import { useAccount, useChainId } from "wagmi";
import {
  PortfolioService,
  PortfolioAnalysis,
  AnalysisProgress,
} from "../services/portfolioService";
import { ApiService } from "../services/apiService";
import { TerminalProgress } from "./shared/TerminalProgress";
import { PortfolioSummary } from "./PortfolioSummary";

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
  const apiService = new ApiService();
  const portfolioService = new PortfolioService(apiService);
  const [currentAnalysis, setCurrentAnalysis] =
    useState<PortfolioAnalysis | null>(initialAnalysis || null);
  const [progressSteps, setProgressSteps] = useState<AnalysisProgress[]>([]);

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

  const handleSubmit = async () => {
    if (!input.trim()) return;

    const userMessage: Message = {
      id: `user-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      type: "user",
      content: input,
      timestamp: new Date(),
    };

    setMessages((msgs) => [...msgs, userMessage]);
    setInput("");
    setIsAnalyzing(true);
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
    ];

    return (
      <Box
        w="100%"
        bg={suggestionsBgColor}
        p={4}
        borderRadius="xl"
        borderWidth="1px"
        borderColor={suggestionsBorderColor}
        mb={4}
      >
        <Text fontSize="sm" fontWeight="medium" mb={3} color="gray.600">
          Try asking me something like:
        </Text>
        <Wrap spacing={2}>
          {suggestions.map((suggestion, index) => (
            <WrapItem key={index}>
              <Button
                size="sm"
                variant="outline"
                colorScheme="blue"
                fontSize="xs"
                onClick={() => setInput(suggestion.text)}
                _hover={{ bg: "blue.50" }}
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
            px={4}
            py={2}
            borderRadius="2xl"
            maxW="70%"
          >
            <Text>{message.content}</Text>
          </Box>
        );
      case "system":
        return (
          <Box
            bg="whiteAlpha.100"
            p={3}
            borderRadius="lg"
            borderWidth="1px"
            borderColor="whiteAlpha.200"
            textAlign="center"
          >
            <Text fontSize="sm" color="whiteAlpha.700">
              {message.content}
            </Text>
          </Box>
        );
      case "assistant":
        return (
          <VStack align="stretch" maxW="100%" spacing={4}>
            {currentAnalysis ? (
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
                  }
                }}
              />
            ) : (
              <Box
                bg="whiteAlpha.50"
                p={4}
                borderRadius="xl"
                borderWidth="1px"
                borderColor="whiteAlpha.200"
              >
                <Text>{message.content}</Text>
              </Box>
            )}
          </VStack>
        );
      case "progress":
        return (
          <Box maxW="100%" mb={2}>
            <Box
              bg="whiteAlpha.50"
              p={4}
              borderRadius="lg"
              borderWidth="1px"
              borderColor="whiteAlpha.200"
            >
              <VStack spacing={3} align="stretch">
                <HStack justify="space-between">
                  <VStack align="start" spacing={1}>
                    <Text fontSize="sm" fontWeight="medium" color="white">
                      {message.content}
                    </Text>
                    {message.metadata?.reasoning?.[0] && (
                      <Text fontSize="xs" color="whiteAlpha.600">
                        {message.metadata.reasoning[0]}
                      </Text>
                    )}
                  </VStack>
                  <Text fontSize="xs" color="whiteAlpha.700" fontWeight="bold">
                    {message.metadata?.progress || 0}%
                  </Text>
                </HStack>
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
    <VStack h="100vh" spacing={0}>
      <Box flex={1} w="100%" overflowY="auto" p={4}>
        <VStack spacing={6} align="stretch">
          {/* Show suggested commands when chat is empty and not in portfolio mode */}
          {messages.length === 0 && !portfolioMode && renderSuggestedCommands()}

          {messages.map((msg) => (
            <Box
              key={msg.id}
              alignSelf={msg.type === "user" ? "flex-end" : "flex-start"}
              w={msg.type === "assistant" ? "100%" : "auto"}
            >
              {renderMessage(msg)}
            </Box>
          ))}
          <div ref={messagesEndRef} />
        </VStack>
      </Box>
      <Box w="100%" p={4} borderTop="1px" borderColor="whiteAlpha.200">
        <Flex>
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={
              portfolioMode
                ? "Ask me more about your portfolio..."
                : "Ask about your portfolio..."
            }
            mr={2}
            disabled={isAnalyzing}
            onKeyPress={(e) => e.key === "Enter" && handleSubmit()}
          />
          <Button
            onClick={handleSubmit}
            colorScheme="blue"
            isLoading={isAnalyzing}
          >
            Send
          </Button>
        </Flex>
      </Box>
    </VStack>
  );
};

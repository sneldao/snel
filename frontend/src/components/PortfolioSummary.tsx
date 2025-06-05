import React, { useState, useEffect } from "react";
import {
  Box,
  VStack,
  HStack,
  Text,
  SimpleGrid,
  Badge,
  Icon,
  useDisclosure,
  Button,
  Progress,
  Spinner,
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
  StatArrow,
  Tooltip,
  Divider,
  Flex,
  Circle,
  Tag,
  TagLabel,
  TagLeftIcon,
  Accordion,
  AccordionItem,
  AccordionButton,
  AccordionPanel,
  AccordionIcon,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  TableContainer,
} from "@chakra-ui/react";
import { ChevronDownIcon, ChevronUpIcon } from "@chakra-ui/icons";
import {
  FaChartPie,
  FaExchangeAlt,
  FaChartLine,
  FaInfoCircle,
  FaLightbulb,
  FaExclamationTriangle,
  FaRocket,
  FaSync,
  FaCoins,
  FaLink,
  FaShieldAlt,
  FaPercentage,
  FaEye,
  FaFire,
  FaSearch,
  FaWallet,
  FaLayerGroup,
} from "react-icons/fa";
import {
  PortfolioAnalysis,
  PortfolioMetric,
  PortfolioAction,
  AnalysisProgress,
} from "../services/portfolioService";
import { TerminalProgress } from "./shared/TerminalProgress";
import ReactMarkdown from "react-markdown";
import { Chat } from "./Chat";

export interface PortfolioSummaryProps {
  response: {
    analysis?: PortfolioAnalysis;
    summary?: string;
    fullAnalysis?: string;
    content?: string;
    status?: "pending" | "processing" | "success" | "error";
    metadata?: any;
    error?: string;
  };
  onActionClick?: (action: PortfolioAction) => void;
  isLoading?: boolean;
  progressSteps?: AnalysisProgress[];
}

// PortfolioMetric imported from portfolioService.ts

const GradientBox = ({
  children,
  ...props
}: { children: React.ReactNode } & any) => (
  <Box
    position="relative"
    p={6}
    borderRadius="xl"
    bg="white"
    borderWidth="1px"
    borderColor="gray.200"
    boxShadow="sm"
    {...props}
  >
    {children}
  </Box>
);

const AssetCard = ({
  asset,
}: {
  asset: {
    name: string;
    value: number;
    amount: string | number;
    change?: number;
  };
}) => (
  <Box
    p={{ base: 3, md: 4 }}
    bg="gray.50"
    borderRadius="lg"
    borderWidth="1px"
    borderColor="gray.200"
    _hover={{
      transform: "translateY(-2px)",
      boxShadow: "md",
      borderColor: "gray.300",
    }}
    transition="all 0.3s"
    position="relative"
    overflow="hidden"
    width="100%"
  >
    <Box
      position="absolute"
      top={0}
      left={0}
      right={0}
      h="3px"
      bg={asset.change && asset.change > 0 ? "green.400" : "red.400"}
      opacity={asset.change ? 1 : 0}
    />
    <VStack align="stretch" spacing={2}>
      <Flex justify="space-between" align="center" wrap="wrap" gap={1}>
        <Text
          fontSize={{ base: "xs", md: "sm" }}
          color="gray.600"
          fontWeight="medium"
          noOfLines={1}
        >
          {asset.name}
        </Text>
        {asset.change && (
          <Badge
            variant="subtle"
            colorScheme={asset.change > 0 ? "green" : "red"}
            px={2}
            py={1}
            borderRadius="full"
            fontSize={{ base: "2xs", md: "xs" }}
            flexShrink={0}
          >
            {asset.change > 0 ? "+" : ""}
            {asset.change}%
          </Badge>
        )}
      </Flex>
      <Text
        fontSize={{ base: "lg", md: "xl" }}
        fontWeight="bold"
        letterSpacing="tight"
        color="gray.800"
      >
        ${asset.value.toLocaleString()}
      </Text>
      <Text fontSize={{ base: "xs", md: "sm" }} color="gray.500">
        {asset.amount}
      </Text>
    </VStack>
  </Box>
);

export const PortfolioSummary: React.FC<PortfolioSummaryProps> = ({
  response,
  onActionClick,
  isLoading = false,
  progressSteps = [],
}) => {
  // Track local loading state
  const [currentProgress, setCurrentProgress] = useState<number>(0);
  const [currentStage, setCurrentStage] = useState<string>("");

  // Extract real data from analysis for the clean UI
  const analysis = response.analysis;
  const analysisContent =
    analysis?.fullAnalysis ||
    analysis?.summary ||
    response.summary ||
    response.content;

  // Get progress steps from metadata if available
  const metadataSteps = response.metadata?.steps || [];
  const allProgressSteps =
    metadataSteps.length > 0 ? metadataSteps : progressSteps;

  // Calculate unavailable services for better UI handling
  const unavailableServices: string[] = [];
  if (analysis?.services_status) {
    if (analysis.services_status.portfolio === false)
      unavailableServices.push("Blockchain Data");
    if (analysis.services_status.exa === false)
      unavailableServices.push("Protocol Discovery");
    if (analysis.services_status.firecrawl === false)
      unavailableServices.push("Protocol Details");
  }

  // Update progress based on steps
  useEffect(() => {
    if (allProgressSteps.length > 0) {
      const latestStep = allProgressSteps[allProgressSteps.length - 1];
      setCurrentProgress(latestStep.completion || 0);
      setCurrentStage(latestStep.stage || "Processing...");
    }
  }, [allProgressSteps]);

  // Parse real portfolio data from the analysis
  const extractPortfolioValue = (content: string): number | null => {
    // First try to get value from structured data if available
    if (analysis?.portfolio_data?.portfolio_value) {
      return analysis.portfolio_data.portfolio_value;
    }

    if (analysis?.metrics) {
      const totalValueMetric = analysis.metrics.find(
        (m) =>
          m.label?.toLowerCase().includes("total") &&
          m.label?.toLowerCase().includes("value")
      );
      if (totalValueMetric && typeof totalValueMetric.value === "number") {
        return totalValueMetric.value;
      }
    }

    // Look for portfolio value in the analysis text
    const valueMatch = content?.match(/portfolio value[:\s]*\$?([0-9,]+)/i);
    if (valueMatch) {
      return parseInt(valueMatch[1].replace(/,/g, ""));
    }

    // Look for USD amounts in the text
    const usdMatch = content?.match(/\$([0-9,]+)/);
    if (usdMatch) {
      return parseInt(usdMatch[1].replace(/,/g, ""));
    }

    // Return null instead of 0 to indicate no data is available yet
    return null;
  };

  const portfolioValue = extractPortfolioValue(analysisContent || "");
  const riskScore = analysis?.riskScore || null;

  // Create succinct summary from the full analysis
  const createSummary = (content: string): string => {
    if (!content)
      return "Portfolio analysis completed with real blockchain data.";

    // Extract key points for summary
    const sentences = content
      .split(/[.!?]+/)
      .filter((s) => s.trim().length > 20);
    const keyPoints = sentences.slice(0, 3).join(". ") + ".";

    return keyPoints.length > 200
      ? keyPoints.substring(0, 200) + "..."
      : keyPoints;
  };

  const summary = createSummary(analysisContent || "");

  // Function to clean markdown and make text user-friendly
  const cleanAnalysisText = (content: string): string => {
    if (!content) return "No analysis available";

    // Remove markdown formatting
    let cleaned = content
      .replace(/#{1,6}\s+/g, "") // Remove headers
      .replace(/\*\*(.*?)\*\*/g, "$1") // Remove bold
      .replace(/\*(.*?)\*/g, "$1") // Remove italic
      .replace(/`(.*?)`/g, "$1") // Remove code blocks
      .replace(/\[(.*?)\]\(.*?\)/g, "$1") // Remove links, keep text
      .replace(/^\s*[-*+]\s+/gm, "• ") // Convert list items to bullets
      .replace(/^\s*\d+\.\s+/gm, "• ") // Convert numbered lists to bullets
      .replace(/\n{3,}/g, "\n\n") // Reduce multiple newlines
      .trim();

    // Extract first meaningful paragraph (not just wallet address)
    const paragraphs = cleaned
      .split("\n\n")
      .filter(
        (p) =>
          p.trim().length > 50 &&
          !p.includes("0x") &&
          !p.includes("###") &&
          !p.includes("**")
      );

    return (
      paragraphs[0] || "Portfolio analysis completed with real blockchain data."
    );
  };

  // Helper functions for extracting real data insights
  const extractChainCount = (content: string): number => {
    const chainMentions = [
      "ethereum",
      "base",
      "arbitrum",
      "optimism",
      "polygon",
      "avalanche",
      "bsc",
      "linea",
      "scroll",
      "zksync",
    ];
    const foundChains = chainMentions.filter((chain) =>
      content.toLowerCase().includes(chain)
    );
    return Math.max(foundChains.length, 1);
  };

  const extractProtocolCount = (content: string): number => {
    const protocolMentions = [
      "aave",
      "compound",
      "uniswap",
      "curve",
      "lido",
      "maker",
      "yearn",
      "convex",
      "balancer",
      "sushiswap",
    ];
    const foundProtocols = protocolMentions.filter((protocol) =>
      content.toLowerCase().includes(protocol)
    );
    return foundProtocols.length;
  };

  const extractYieldOpportunities = (content: string): number => {
    const yieldMatches = content.match(/(\d+\.?\d*)\s*%/g) || [];
    return Math.min(yieldMatches.length, 12); // Cap at 12 opportunities
  };

  const extractTokenCount = (content: string): number => {
    // Look for token count mentions or estimate from content
    const tokenMatch = content.match(/(\d+)\s+(?:different\s+)?tokens?/i);
    if (tokenMatch) return parseInt(tokenMatch[1]);

    // Fallback: count unique token symbols mentioned
    const tokenSymbols = content.match(/\b[A-Z]{3,5}\b/g) || [];
    const uniqueTokens = new Set(
      tokenSymbols.filter(
        (token) =>
          ![
            "THE",
            "AND",
            "FOR",
            "YOU",
            "ARE",
            "NOT",
            "CAN",
            "ALL",
            "NEW",
            "GET",
            "USE",
            "NOW",
            "TOP",
            "HOW",
            "WHY",
            "WHO",
            "API",
            "FAQ",
            "USD",
            "EUR",
            "GBP",
          ].includes(token)
      )
    );
    return Math.max(uniqueTokens.size, 1);
  };

  const extractBestAPY = (content: string): string => {
    const apyMatches = content.match(/(\d+\.?\d*)\s*%/g) || [];
    const apyNumbers = apyMatches
      .map((match) => parseFloat(match.replace("%", "")))
      .filter((num) => num < 100);
    return apyNumbers.length > 0 ? Math.max(...apyNumbers).toFixed(1) : "0.0";
  };

  const extractTVLData = (content: string): string => {
    const tvlMatch = content.match(/\$?([0-9,.]+[BMK]?)\s*(?:TVL|locked)/i);
    return tvlMatch ? tvlMatch[1] : "N/A";
  };

  const extractSecurityInfo = (content: string): string => {
    const hasAudit = content.toLowerCase().includes("audit");
    const hasInsurance = content.toLowerCase().includes("insurance");
    if (hasAudit && hasInsurance) return "Audited + Insured";
    if (hasAudit) return "Audited";
    if (hasInsurance) return "Insured";
    return "Unverified";
  };

  const extractLiveRates = (content: string): string => {
    const rateMatches = content.match(/(\d+\.?\d*)\s*%\s*(?:APY|APR)/gi) || [];
    return rateMatches.length > 0 ? `${rateMatches.length} rates` : "No rates";
  };

  const extractKeyInsights = (content: string): string[] => {
    const insights: string[] = [];

    // Extract sentences that contain key DeFi terms
    const sentences = content
      .split(/[.!?]+/)
      .filter((s) => s.trim().length > 30);

    const keyTerms = [
      "apy",
      "yield",
      "staking",
      "liquidity",
      "tvl",
      "protocol",
      "defi",
    ];

    sentences.forEach((sentence) => {
      const lowerSentence = sentence.toLowerCase();
      if (
        keyTerms.some((term) => lowerSentence.includes(term)) &&
        insights.length < 4
      ) {
        insights.push(sentence.trim());
      }
    });

    // Fallback insights if none found
    if (insights.length === 0) {
      insights.push(
        "Portfolio analysis completed using real blockchain data",
        "Multiple DeFi protocols discovered for yield optimization",
        "Cross-chain opportunities identified for better diversification"
      );
    }

    return insights.slice(0, 4); // Limit to 4 insights
  };

  // Concise loading state
  if (isLoading || response.status === "processing") {
    return (
      <Box
        w="100%"
        bg="white"
        borderRadius="xl"
        p={6}
        boxShadow="sm"
        textAlign="center"
      >
        <VStack spacing={3}>
          <Spinner size="lg" color="blue.500" />
          <Text fontSize="lg" fontWeight="medium" color="gray.700">
            Analyzing Portfolio...
          </Text>
        </VStack>
      </Box>
    );
  }

  // Show the analysis UI when data is available
  return (
    <Box w="100%" maxW="1200px" mx="auto" py={{ base: 4, md: 8 }}>
      <VStack spacing={{ base: 4, md: 8 }} align="stretch">
        <GradientBox>
          <Flex
            mb={{ base: 3, md: 6 }}
            justify="space-between"
            align="start"
            direction={{ base: "column", md: "row" }}
            gap={{ base: 3, md: 0 }}
          >
            <VStack align="start" spacing={2}>
              <HStack spacing={{ base: 2, md: 3 }} flexWrap="wrap">
                <Icon as={FaChartPie} boxSize={6} color="blue.500" />
                <Text fontSize="xl" fontWeight="bold" color="gray.800">
                  Portfolio Overview
                </Text>
                <Badge
                  colorScheme={
                    analysis?.services_status?.portfolio ? "green" : "yellow"
                  }
                  variant="subtle"
                >
                  {analysis?.services_status?.portfolio
                    ? "Real Data"
                    : "Limited Data"}
                </Badge>
              </HStack>
              <Text color="gray.600" fontSize="sm">
                Last updated {new Date().toLocaleString()}
              </Text>
            </VStack>
            <HStack spacing={{ base: 3, md: 6 }}>
              {/* View Full Analysis button removed - now handled by parent component */}
              <Box
                textAlign={{ base: "left", md: "right" }}
                borderLeft={{ base: "none", md: "1px" }}
                borderTop={{ base: "1px", md: "none" }}
                borderColor="gray.200"
                pl={{ base: 0, md: 6 }}
                pt={{ base: 3, md: 0 }}
                w={{ base: "full", md: "auto" }}
              >
                <Text color="gray.600" mb={1} fontSize="sm">
                  Total Portfolio Value
                </Text>
                <Text
                  fontSize="2xl"
                  fontWeight="bold"
                  letterSpacing="tight"
                  color="gray.800"
                >
                  {portfolioValue !== null ? (
                    `$${portfolioValue.toLocaleString()}`
                  ) : analysis?.services_status?.portfolio === false ? (
                    <Text as="span" color="orange.400">
                      Unavailable
                    </Text>
                  ) : (
                    <Text as="span" color="gray.400">
                      Loading...
                    </Text>
                  )}
                </Text>
                {/* Only show risk if we have meaningful data */}
                {(riskScore !== null && riskScore > 0) ||
                (analysis?.portfolio_data?.risk_level &&
                  analysis.portfolio_data.risk_level !== "N/A" &&
                  analysis.portfolio_data.risk_level !== "Loading...") ? (
                  <HStack justify="flex-end" color="green.500" mt={1}>
                    <Text fontSize="sm">📊</Text>
                    <Text fontSize="sm">
                      Risk:{" "}
                      {riskScore !== null && riskScore > 0
                        ? `${riskScore.toFixed(1)}/5`
                        : analysis?.portfolio_data?.risk_level}
                    </Text>
                  </HStack>
                ) : null}
              </Box>
            </HStack>
          </Flex>

          {/* Sectioned Data Display */}
          <VStack spacing={{ base: 3, md: 4 }} align="stretch">
            {/* Alchemy Blockchain Data Section */}
            <Box
              p={4}
              bg={
                analysis?.services_status?.portfolio === false
                  ? "linear-gradient(135deg, #FFF5F5 0%, #FED7D7 100%)"
                  : "linear-gradient(135deg, #EBF8FF 0%, #E0F2FE 100%)"
              }
              borderRadius="lg"
              borderWidth="1px"
              borderColor={
                analysis?.services_status?.portfolio === false
                  ? "red.200"
                  : "blue.200"
              }
              opacity={analysis?.services_status?.portfolio === false ? 0.8 : 1}
              position="relative"
            >
              {analysis?.services_status?.portfolio === false && (
                <Box
                  position="absolute"
                  top={2}
                  right={2}
                  px={2}
                  py={1}
                  bg="red.100"
                  color="red.800"
                  fontSize="xs"
                  fontWeight="medium"
                  borderRadius="md"
                >
                  Service Unavailable
                </Box>
              )}
              <Flex
                mb={3}
                justify="space-between"
                direction={{ base: "column", sm: "row" }}
                gap={{ base: 1, sm: 0 }}
              >
                <HStack>
                  <Text
                    fontSize="sm"
                    color={
                      analysis?.services_status?.portfolio === false
                        ? "red.700"
                        : "blue.700"
                    }
                    fontWeight="bold"
                  >
                    🔗 ALCHEMY BLOCKCHAIN DATA
                  </Text>
                </HStack>
                <Badge
                  colorScheme={
                    analysis?.services_status?.portfolio === false
                      ? "red"
                      : "blue"
                  }
                  variant="subtle"
                  fontSize="xs"
                >
                  {analysis?.services_status?.portfolio === false
                    ? "Service Unavailable"
                    : `${
                        analysis?.portfolio_data?.api_calls_made ||
                        analysis?.tool_calls_summary?.total_calls ||
                        "0"
                      } API calls`}
                </Badge>
              </Flex>
              <SimpleGrid
                columns={{ base: 2, md: 4 }}
                spacing={{ base: 2, md: 4 }}
              >
                <Box>
                  <Text fontSize="xs" color="blue.600">
                    Portfolio Value
                  </Text>
                  <Text fontSize="lg" fontWeight="bold" color="blue.800">
                    {analysis?.portfolio_data?.portfolio_value ||
                    portfolioValue !== null ? (
                      `$${(
                        analysis?.portfolio_data?.portfolio_value ||
                        portfolioValue ||
                        0
                      ).toLocaleString()}`
                    ) : (
                      <Text as="span" color="gray.400">
                        Loading...
                      </Text>
                    )}
                  </Text>
                </Box>
                <Box>
                  <Text fontSize="xs" color="blue.600">
                    Active Chains
                  </Text>
                  <Text fontSize="lg" fontWeight="bold" color="blue.800">
                    {analysis?.portfolio_data?.active_chains ||
                      extractChainCount(analysisContent || "")}
                  </Text>
                </Box>
                <Box>
                  <Text fontSize="xs" color="blue.600">
                    Token Count
                  </Text>
                  <Text fontSize="lg" fontWeight="bold" color="blue.800">
                    {analysis?.portfolio_data?.token_count ||
                      extractTokenCount(analysisContent || "")}
                  </Text>
                </Box>
                {/* Only show risk level if we have actual data (not Loading...) */}
                {(analysis?.portfolio_data?.risk_level &&
                  analysis.portfolio_data.risk_level !== "Loading..." &&
                  analysis.portfolio_data.risk_level !== "N/A") ||
                (riskScore !== null && riskScore > 0) ? (
                  <Box>
                    <Text fontSize="xs" color="blue.600">
                      Risk Level
                    </Text>
                    <Text fontSize="lg" fontWeight="bold" color="blue.800">
                      {analysis?.portfolio_data?.risk_level ||
                        (riskScore !== null
                          ? `${riskScore.toFixed(1)}/5`
                          : "N/A")}
                    </Text>
                  </Box>
                ) : null}
              </SimpleGrid>
            </Box>

            {/* Exa Protocol Discovery Section */}
            <Box
              p={4}
              bg={
                analysis?.services_status?.exa === false
                  ? "linear-gradient(135deg, #FFF5F5 0%, #FED7D7 100%)"
                  : "linear-gradient(135deg, #FAF5FF 0%, #F3E8FF 100%)"
              }
              borderRadius="lg"
              borderWidth="1px"
              borderColor={
                analysis?.services_status?.exa === false
                  ? "red.200"
                  : "purple.200"
              }
              opacity={analysis?.services_status?.exa === false ? 0.8 : 1}
              position="relative"
            >
              {analysis?.services_status?.exa === false && (
                <Box
                  position="absolute"
                  top={2}
                  right={2}
                  px={2}
                  py={1}
                  bg="red.100"
                  color="red.800"
                  fontSize="xs"
                  fontWeight="medium"
                  borderRadius="md"
                >
                  Service Unavailable
                </Box>
              )}
              <Flex
                mb={3}
                justify="space-between"
                direction={{ base: "column", sm: "row" }}
                gap={{ base: 1, sm: 0 }}
              >
                <HStack flexWrap="wrap">
                  <Text
                    fontSize="sm"
                    color={
                      analysis?.services_status?.exa === false
                        ? "red.700"
                        : "purple.700"
                    }
                    fontWeight="bold"
                  >
                    🔍 EXA PROTOCOL DISCOVERY
                  </Text>
                </HStack>
                <Badge
                  colorScheme={
                    analysis?.services_status?.exa === false
                      ? "red"
                      : analysis?.exa_data?.search_success
                      ? "purple"
                      : "gray"
                  }
                  variant="subtle"
                  fontSize="xs"
                >
                  {analysis?.services_status?.exa === false
                    ? "Service Unavailable"
                    : analysis?.exa_data?.search_success
                    ? "Neural Search"
                    : "Search Failed"}
                </Badge>
              </Flex>
              <SimpleGrid
                columns={{ base: 2, md: 3 }}
                spacing={{ base: 2, md: 4 }}
              >
                <Box>
                  <Text fontSize="xs" color="purple.600">
                    Protocols Found
                  </Text>
                  <Text fontSize="lg" fontWeight="bold" color="purple.800">
                    {analysis?.exa_data?.protocols_found || 0}
                  </Text>
                </Box>
                {/* Only show yield opportunities if they exist and are > 0 */}
                {analysis?.exa_data?.yield_opportunities &&
                  analysis.exa_data.yield_opportunities > 0 && (
                    <Box>
                      <Text fontSize="xs" color="purple.600">
                        Yield Opportunities
                      </Text>
                      <Text fontSize="lg" fontWeight="bold" color="purple.800">
                        {analysis.exa_data.yield_opportunities}
                      </Text>
                    </Box>
                  )}
                {/* Only show APY if it exists and is not 0.0% */}
                {analysis?.exa_data?.best_apy_found &&
                  analysis.exa_data.best_apy_found !== "0.0%" &&
                  analysis.exa_data.best_apy_found !== "N/A" && (
                    <Box>
                      <Text fontSize="xs" color="purple.600">
                        Best APY Found
                      </Text>
                      <Text fontSize="lg" fontWeight="bold" color="purple.800">
                        {analysis.exa_data.best_apy_found}
                      </Text>
                    </Box>
                  )}
              </SimpleGrid>
            </Box>

            {/* Portfolio AI Analysis Section */}
            <Box
              p={4}
              bg="linear-gradient(135deg, #F0FDF4 0%, #DCFCE7 100%)"
              borderRadius="lg"
              borderWidth="1px"
              borderColor="green.200"
            >
              <HStack mb={3}>
                <Text fontSize="sm" color="green.700" fontWeight="bold">
                  🧠 AI PORTFOLIO ANALYSIS
                </Text>
              </HStack>
              <Text color="green.800" fontSize="sm" lineHeight="1.6">
                {cleanAnalysisText(analysisContent || "")}
              </Text>
            </Box>
          </VStack>

          {/* Action Recommendations Section */}
          {analysis?.actions && analysis.actions.length > 0 && (
            <Box
              mt={{ base: 4, md: 6 }}
              p={{ base: 3, md: 4 }}
              bg="linear-gradient(135deg, #FCFCFC 0%, #F9F9F9 100%)"
              borderRadius="lg"
              borderWidth="1px"
              borderColor="blue.100"
            >
              <HStack mb={3}>
                <Icon as={FaExchangeAlt} color="blue.500" />
                <Text fontSize="md" fontWeight="semibold" color="gray.700">
                  Recommended Actions
                </Text>
              </HStack>
              <SimpleGrid
                columns={{ base: 1, md: 2 }}
                spacing={{ base: 2, md: 3 }}
              >
                {analysis.actions.slice(0, 4).map((action, idx) => (
                  <Box
                    key={idx}
                    p={3}
                    bg="white"
                    borderRadius="md"
                    borderWidth="1px"
                    borderColor={
                      action.type === "optimize"
                        ? "green.200"
                        : action.type === "rebalance"
                        ? "blue.200"
                        : action.type === "exit"
                        ? "red.200"
                        : action.type === "enter"
                        ? "purple.200"
                        : action.type === "retry"
                        ? "orange.200"
                        : "gray.200"
                    }
                    _hover={{ transform: "translateY(-2px)", boxShadow: "sm" }}
                    transition="all 0.2s"
                  >
                    <Text
                      fontSize={{ base: "xs", md: "sm" }}
                      fontWeight="medium"
                      mb={2}
                    >
                      {action.description}
                    </Text>
                    <Button
                      size="sm"
                      colorScheme={
                        action.id === "diversify_into_stablecoins"
                          ? "green"
                          : action.type === "optimize"
                          ? "green"
                          : action.type === "rebalance"
                          ? "blue"
                          : action.type === "exit"
                          ? "red"
                          : action.type === "enter"
                          ? "purple"
                          : action.type === "retry" || action.type === "connect"
                          ? "orange"
                          : "gray"
                      }
                      isDisabled={
                        action.id !== "diversify_into_stablecoins" &&
                        action.type !== "retry" &&
                        action.type !== "connect"
                      }
                      opacity={
                        action.id === "diversify_into_stablecoins" ||
                        action.type === "retry" ||
                        action.type === "connect"
                          ? 1
                          : 0.5
                      }
                      onClick={() => onActionClick && onActionClick(action)}
                    >
                      {action.type === "retry"
                        ? "Retry Analysis"
                        : action.type === "connect"
                        ? "Connect Wallet"
                        : action.id === "diversify_into_stablecoins"
                        ? "Rebalance"
                        : action.type === "optimize"
                        ? "Optimize"
                        : action.type === "rebalance"
                        ? "Rebalance"
                        : action.type === "exit"
                        ? "Exit Position"
                        : action.type === "enter"
                        ? "Enter Position"
                        : "Execute"}
                    </Button>
                  </Box>
                ))}
              </SimpleGrid>
            </Box>
          )}

          {/* Service Status Summary */}
          <Box
            mt={{ base: 4, md: 6 }}
            p={{ base: 3, md: 4 }}
            bg={unavailableServices.length > 0 ? "red.50" : "gray.50"}
            borderRadius="lg"
            borderWidth="1px"
            borderColor={
              unavailableServices.length > 0 ? "red.200" : "gray.200"
            }
          >
            <Flex
              mb={3}
              justify="space-between"
              direction={{ base: "column", sm: "row" }}
              gap={{ base: 1, sm: 0 }}
            >
              <HStack>
                <Icon
                  as={FaInfoCircle}
                  color={
                    unavailableServices.length > 0 ? "red.500" : "blue.500"
                  }
                />
                <Text
                  fontSize="md"
                  fontWeight="semibold"
                  color={
                    unavailableServices.length > 0 ? "red.700" : "gray.700"
                  }
                >
                  Service Status
                </Text>
              </HStack>
              {unavailableServices.length > 0 && (
                <Badge colorScheme="red" variant="subtle">
                  {unavailableServices.length} service
                  {unavailableServices.length > 1 ? "s" : ""} unavailable
                </Badge>
              )}
            </Flex>
            <SimpleGrid columns={{ base: 1, md: 2 }} spacing={3}>
              <HStack>
                <Box
                  w="8px"
                  h="8px"
                  bg={
                    analysis?.services_status?.portfolio
                      ? "green.400"
                      : "red.400"
                  }
                  borderRadius="full"
                />
                <Text
                  fontSize="sm"
                  color={
                    analysis?.services_status?.portfolio
                      ? "gray.600"
                      : "red.600"
                  }
                  fontWeight={
                    analysis?.services_status?.portfolio ? "normal" : "medium"
                  }
                >
                  Blockchain Data:{" "}
                  {analysis?.services_status?.portfolio
                    ? "Available"
                    : "Unavailable"}
                </Text>
              </HStack>
              <HStack>
                <Box
                  w="8px"
                  h="8px"
                  bg={analysis?.services_status?.exa ? "green.400" : "red.400"}
                  borderRadius="full"
                />
                <Text
                  fontSize="sm"
                  color={
                    analysis?.services_status?.exa ? "gray.600" : "red.600"
                  }
                  fontWeight={
                    analysis?.services_status?.exa ? "normal" : "medium"
                  }
                >
                  Protocol Discovery:{" "}
                  {analysis?.services_status?.exa ? "Available" : "Unavailable"}
                </Text>
              </HStack>
            </SimpleGrid>
            {unavailableServices.length > 0 && (
              <Box
                mt={3}
                p={2}
                bg="red.50"
                borderRadius="md"
                borderWidth="1px"
                borderColor="red.200"
              >
                <Text fontSize="sm" color="red.700">
                  Some services are currently unavailable. The analysis is based
                  on limited data and may not be complete.
                </Text>
              </Box>
            )}
          </Box>

          {analysisContent && (
            <Box
              mt={{ base: 4, md: 6 }}
              p={{ base: 3, md: 4 }}
              bg="gray.50"
              borderRadius="lg"
              borderWidth="1px"
              borderColor="gray.200"
              overflowX="auto"
            >
              <HStack mb={3}>
                <Icon as={FaLightbulb} color="yellow.500" />
                <Text fontSize="md" fontWeight="semibold" color="gray.700">
                  Key Insights
                  {analysis?.services_status?.portfolio
                    ? " from Real Data"
                    : ""}
                </Text>
              </HStack>
              <VStack align="stretch" spacing={2}>
                {extractKeyInsights(analysisContent).map((insight, idx) => (
                  <Flex key={idx} align="flex-start" gap={2}>
                    <Box
                      w="4px"
                      h="4px"
                      bg="blue.400"
                      borderRadius="full"
                      mt={2}
                      flexShrink={0}
                    />
                    <Text
                      fontSize={{ base: "xs", md: "sm" }}
                      color="gray.600"
                      wordBreak="break-word"
                    >
                      {cleanAnalysisText(insight)}
                    </Text>
                  </Flex>
                ))}
              </VStack>

              {/* If services are unavailable, show retry button */}
              {(!analysis?.services_status?.portfolio ||
                !analysis?.services_status?.exa) && (
                <Box mt={4} textAlign="center">
                  <Button
                    size="sm"
                    colorScheme="red"
                    leftIcon={<Icon as={FaSync} />}
                    onClick={() =>
                      onActionClick &&
                      onActionClick({
                        id: "retry_analysis",
                        description: "Retry analysis with all services",
                        type: "retry",
                        impact: {},
                      })
                    }
                    isLoading={isLoading}
                    loadingText="Retrying..."
                  >
                    Retry Analysis
                  </Button>
                  <Text fontSize="xs" color="red.600" mt={1}>
                    {unavailableServices.length === 1
                      ? `${unavailableServices[0]} service is currently unavailable.`
                      : `${unavailableServices.length} services are currently unavailable.`}
                    Retry to attempt reconnection.
                  </Text>
                </Box>
              )}
            </Box>
          )}
        </GradientBox>
      </VStack>

      {/* Modal functionality removed - now handled by parent component with Chat interface */}
    </Box>
  );

  // Concise loading state
  if (isLoading) {
    return (
      <Box
        w="100%"
        p={6}
        bg="white"
        borderRadius="lg"
        borderWidth="1px"
        borderColor="gray.200"
        textAlign="center"
      >
        <VStack spacing={3}>
          <Spinner size="lg" color="blue.500" />
          <Text fontSize="lg" fontWeight="medium" color="gray.700">
            Analyzing Portfolio...
          </Text>
        </VStack>
      </Box>
    );
  }

  // Error state
  if (response.error) {
    return (
      <Box
        w="100%"
        p={6}
        bg="white"
        borderRadius="lg"
        borderWidth="1px"
        borderColor="red.200"
        textAlign="center"
      >
        <VStack spacing={3}>
          <Text color="red.500" fontSize="lg" fontWeight="medium">
            Analysis Failed
          </Text>
          <Text color="gray.600" fontSize="sm">
            {response.error}
          </Text>
          {onActionClick && (
            <Button
              size="sm"
              colorScheme="red"
              leftIcon={<Icon as={FaSync} />}
              onClick={() =>
                onActionClick &&
                onActionClick({
                  id: "retry_analysis",
                  description: "Retry portfolio analysis",
                  type: "retry",
                  impact: {},
                })
              }
            >
              Retry Analysis
            </Button>
          )}
        </VStack>
      </Box>
    );
  }

  // No data state
  return (
    <Box
      w="100%"
      p={6}
      bg="white"
      borderRadius="lg"
      borderWidth="1px"
      borderColor="gray.200"
      textAlign="center"
    >
      <VStack spacing={3}>
        <Icon as={FaChartPie} boxSize={8} color="gray.400" />
        <Text color="gray.600">No portfolio data available</Text>
        {onActionClick && (
          <Button
            size="sm"
            colorScheme="blue"
            leftIcon={<Icon as={FaChartPie} />}
            onClick={() =>
              onActionClick &&
              onActionClick({
                id: "start_analysis",
                description: "Start portfolio analysis",
                type: "retry",
                impact: {},
              })
            }
          >
            Analyze Portfolio
          </Button>
        )}
      </VStack>
    </Box>
  );
};

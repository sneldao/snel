import React, { useState } from "react";
import {
  Box,
  VStack,
  HStack,
  Text,
  SimpleGrid,
  Badge,
  Icon,
  Button,
  Progress,
  Spinner,
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
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
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalCloseButton,
  ModalBody,
  useDisclosure,
  UnorderedList,
  ListItem,
  Collapse,
} from "@chakra-ui/react";
import { ChevronDownIcon, ChevronUpIcon } from "@chakra-ui/icons";
import {
  FaChartPie,
  FaExchangeAlt,
  FaInfoCircle,
  FaLightbulb,
  FaCoins,
  FaLink,
  FaShieldAlt,
  FaPercentage,
  FaEye,
  FaFire,
  FaSearch,
  FaWallet,
  FaLayerGroup,
  FaChartLine,
  FaExternalLinkAlt,
} from "react-icons/fa";
import {
  PortfolioAnalysis,
  PortfolioAction,
} from "../services/portfolioService";

// Utility function to render markdown-like text properly
const renderFormattedText = (text: string) => {
  if (!text) return null;

  // Split text into lines and process each line
  const lines = text.split("\n");
  const elements: React.ReactNode[] = [];

  lines.forEach((line, index) => {
    const trimmedLine = line.trim();

    if (!trimmedLine) {
      // Empty line - add spacing
      elements.push(<Box key={index} h={2} />);
    } else if (trimmedLine.startsWith("###")) {
      // Header
      const headerText = trimmedLine.replace(/^###\s*/, "");
      elements.push(
        <Text
          key={index}
          fontSize="lg"
          fontWeight="bold"
          color="blue.600"
          mt={4}
          mb={2}
        >
          {headerText}
        </Text>
      );
    } else if (trimmedLine.startsWith("**") && trimmedLine.endsWith("**")) {
      // Bold text
      const boldText = trimmedLine.replace(/^\*\*|\*\*$/g, "");
      elements.push(
        <Text key={index} fontWeight="bold" mb={2}>
          {boldText}
        </Text>
      );
    } else if (trimmedLine.startsWith("- ")) {
      // Bullet point
      const bulletText = trimmedLine.replace(/^-\s*/, "");
      elements.push(
        <HStack key={index} align="start" mb={1}>
          <Text color="blue.500" fontWeight="bold">
            •
          </Text>
          <Text fontSize="sm" color="gray.700">
            {bulletText}
          </Text>
        </HStack>
      );
    } else {
      // Regular text
      elements.push(
        <Text
          key={index}
          fontSize="sm"
          color="gray.700"
          mb={2}
          lineHeight="1.6"
        >
          {trimmedLine}
        </Text>
      );
    }
  });

  return (
    <VStack align="start" spacing={1}>
      {elements}
    </VStack>
  );
};

export interface EnhancedPortfolioSummaryProps {
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
}

// Enhanced Portfolio Overview Card
const PortfolioOverviewCard = ({
  analysis,
}: {
  analysis?: PortfolioAnalysis;
}) => {
  // Get data from the correct structure - handle both old and new response formats
  const portfolioData = analysis?.portfolio_data;

  // Debug logging to understand the data structure
  console.log("Portfolio Analysis Debug:", {
    analysis,
    portfolioData,
  });

  // Try multiple paths to get portfolio value
  const portfolioValue =
    portfolioData?.portfolio_value ||
    // Parse from summary if available
    (analysis?.summary &&
      parseFloat(
        analysis.summary
          .match(/\$([0-9,]+\.?[0-9]*)/)?.[1]
          ?.replace(/,/g, "") || "0"
      )) ||
    0;

  // Try multiple paths to get token count
  const tokenCount =
    portfolioData?.token_count ||
    // Parse from summary if available
    (analysis?.summary &&
      parseInt(analysis.summary.match(/(\d+) different tokens/)?.[1] || "0")) ||
    0;

  // Try multiple paths to get active chains
  const activeChains =
    portfolioData?.active_chains ||
    // Parse from summary if available
    (analysis?.summary &&
      parseInt(analysis.summary.match(/across (\d+) chains/)?.[1] || "0")) ||
    1; // Default to 1 if we have any data

  // Try multiple paths to get risk level
  const riskLevel = portfolioData?.risk_level || "Medium";

  return (
    <Box
      p={6}
      bg="linear-gradient(135deg, #667eea 0%, #764ba2 100%)"
      borderRadius="xl"
      color="white"
      position="relative"
      overflow="hidden"
    >
      <Box position="absolute" top={0} right={0} opacity={0.1}>
        <Icon as={FaChartPie} boxSize={20} />
      </Box>

      <VStack align="start" spacing={4} position="relative" zIndex={1}>
        <HStack justify="space-between" w="100%">
          <VStack align="start" spacing={1}>
            <Text fontSize="sm" opacity={0.8}>
              Total Portfolio Value
            </Text>
            <Text fontSize="3xl" fontWeight="bold" letterSpacing="tight">
              ${portfolioValue.toLocaleString()}
            </Text>
          </VStack>
          <Badge colorScheme="whiteAlpha" variant="solid" px={3} py={1}>
            Live Data
          </Badge>
        </HStack>

        <SimpleGrid columns={3} spacing={6} w="100%">
          <Stat>
            <StatLabel fontSize="xs" opacity={0.8}>
              Assets
            </StatLabel>
            <StatNumber fontSize="xl">{tokenCount}</StatNumber>
          </Stat>
          <Stat>
            <StatLabel fontSize="xs" opacity={0.8}>
              Chains
            </StatLabel>
            <StatNumber fontSize="xl">{activeChains}</StatNumber>
          </Stat>
          <Stat>
            <StatLabel fontSize="xs" opacity={0.8}>
              Risk Level
            </StatLabel>
            <StatNumber fontSize="xl">{riskLevel}</StatNumber>
          </Stat>
        </SimpleGrid>
      </VStack>
    </Box>
  );
};

// Service Status Card with Enhanced Visuals
const ServiceStatusCard = ({ analysis }: { analysis?: PortfolioAnalysis }) => {
  const services = [
    {
      name: "Blockchain Data",
      status: analysis?.services_status?.portfolio,
      icon: FaWallet,
      color: "blue",
      description: "Real-time portfolio data from Alchemy API",
    },
    {
      name: "Protocol Discovery",
      status: analysis?.services_status?.exa,
      icon: FaSearch,
      color: "purple",
      description: "AI-powered DeFi protocol search via Exa",
    },
  ];

  return (
    <Box
      p={6}
      bg="white"
      borderRadius="xl"
      borderWidth="1px"
      borderColor="gray.200"
    >
      <HStack mb={4}>
        <Icon as={FaLayerGroup} color="gray.600" />
        <Text fontSize="lg" fontWeight="semibold">
          Service Status
        </Text>
      </HStack>

      <VStack spacing={4}>
        {services.map((service, idx) => (
          <HStack
            key={idx}
            justify="space-between"
            w="100%"
            p={3}
            bg={service.status ? "green.50" : "red.50"}
            borderRadius="lg"
            borderWidth="1px"
            borderColor={service.status ? "green.200" : "red.200"}
          >
            <HStack>
              <Circle size="8" bg={service.status ? "green.100" : "red.100"}>
                <Icon
                  as={service.icon}
                  color={service.status ? "green.600" : "red.600"}
                />
              </Circle>
              <VStack align="start" spacing={0}>
                <Text fontSize="sm" fontWeight="medium">
                  {service.name}
                </Text>
                <Text fontSize="xs" color="gray.600">
                  {service.description}
                </Text>
              </VStack>
            </HStack>
            <Badge
              colorScheme={service.status ? "green" : "red"}
              variant="subtle"
            >
              {service.status ? "Active" : "Offline"}
            </Badge>
          </HStack>
        ))}
      </VStack>
    </Box>
  );
};

// Token Holdings Table Component
const TokenHoldingsTable = ({ analysis }: { analysis?: PortfolioAnalysis }) => {
  // Extract real token data from the analysis
  const extractTokenData = () => {
    const portfolioData = analysis?.portfolio_data;
    const tokens: any[] = [];

    console.log("Token extraction debug:", {
      portfolioData,
      rawData: analysis?.raw_data,
    });

    // Extract tokens from the raw_data which contains the actual token_balances
    if (analysis?.raw_data?.token_balances) {
      const tokenBalances = analysis.raw_data.token_balances;

      // Iterate through each chain's token data
      Object.entries(tokenBalances).forEach(
        ([chainName, chainData]: [string, any]) => {
          if (chainData?.tokens && chainData?.metadata) {
            const chainTokens = chainData.tokens;
            const metadata = chainData.metadata;

            chainTokens.forEach((token: any) => {
              const contractAddress = token.contractAddress;
              const tokenMeta = metadata[contractAddress];

              if (tokenMeta && token.tokenBalance) {
                const balanceHex = token.tokenBalance;
                const balanceInt = parseInt(balanceHex, 16);
                const decimals = tokenMeta.decimals || 18;
                const balance = balanceInt / Math.pow(10, decimals);

                // Only show tokens with meaningful balances
                if (balance > 0.001) {
                  tokens.push({
                    symbol: tokenMeta.symbol || "UNKNOWN",
                    name: tokenMeta.name || "Unknown Token",
                    balance: balance.toFixed(4),
                    value: `$${(balance * 1).toFixed(2)}`, // Placeholder value
                    change: "+0.00%", // Placeholder change
                    chain: chainName,
                    contractAddress,
                  });
                }
              }
            });
          }
        }
      );
    }

    console.log("Extracted tokens:", tokens);
    return tokens;
  };

  const tokens = extractTokenData();

  return (
    <Box
      p={6}
      bg="white"
      borderRadius="xl"
      borderWidth="1px"
      borderColor="gray.200"
    >
      <HStack mb={4}>
        <Icon as={FaCoins} color="yellow.500" />
        <Text fontSize="lg" fontWeight="semibold">
          Token Holdings
        </Text>
        <Badge colorScheme="blue" variant="subtle">
          {analysis?.portfolio_data?.token_count || 0} tokens
        </Badge>
      </HStack>

      {tokens.length > 0 ? (
        <TableContainer>
          <Table variant="simple" size="sm">
            <Thead>
              <Tr>
                <Th>Token</Th>
                <Th>Chain</Th>
                <Th isNumeric>Balance</Th>
                <Th isNumeric>Est. Value</Th>
              </Tr>
            </Thead>
            <Tbody>
              {tokens.map((token, idx) => (
                <Tr key={idx}>
                  <Td>
                    <VStack align="start" spacing={0}>
                      <Text fontWeight="medium">{token.symbol}</Text>
                      <Text fontSize="xs" color="gray.500" noOfLines={1}>
                        {token.name}
                      </Text>
                    </VStack>
                  </Td>
                  <Td>
                    <Badge colorScheme="blue" variant="subtle" size="sm">
                      {token.chain}
                    </Badge>
                  </Td>
                  <Td isNumeric>
                    <Text fontWeight="medium">{token.balance}</Text>
                  </Td>
                  <Td isNumeric>
                    <Text fontWeight="medium" color="gray.600">
                      {token.value}
                    </Text>
                  </Td>
                </Tr>
              ))}
            </Tbody>
          </Table>
        </TableContainer>
      ) : (
        <Box p={8} textAlign="center" bg="gray.50" borderRadius="lg">
          <Text color="gray.500" fontSize="sm">
            No token data available in the current analysis.
            <br />
            Portfolio data may be loading or unavailable.
          </Text>
        </Box>
      )}
    </Box>
  );
};

// Enhanced Data Insights Card
const DataInsightsCard = ({ analysis }: { analysis?: PortfolioAnalysis }) => {
  const { isOpen, onOpen, onClose } = useDisclosure();

  // Only show insights that are actually working and have meaningful data
  const insights = [
    {
      title: "Protocol Discovery",
      value: analysis?.exa_data?.protocols_found || 0,
      subtitle: "DeFi protocols found",
      icon: FaSearch,
      color: "purple",
    },
  ].filter(
    (insight) =>
      // Only show if we have actual data (not 0 or default values)
      insight.value && insight.value !== 0
  );

  // Don't render the card if there are no meaningful insights
  if (insights.length === 0) {
    return null;
  }

  return (
    <>
      <Box
        p={6}
        bg="white"
        borderRadius="xl"
        borderWidth="1px"
        borderColor="gray.200"
      >
        <HStack justify="space-between" mb={4}>
          <HStack>
            <Icon as={FaLightbulb} color="yellow.500" />
            <Text fontSize="lg" fontWeight="semibold">
              AI Insights
            </Text>
          </HStack>
          <Button
            size="sm"
            colorScheme="blue"
            variant="outline"
            onClick={onOpen}
          >
            View Details
          </Button>
        </HStack>

        <SimpleGrid columns={insights.length} spacing={4}>
          {insights.map((insight, idx) => (
            <VStack key={idx} p={4} bg="gray.50" borderRadius="lg" spacing={2}>
              <Circle size="10" bg={`${insight.color}.100`}>
                <Icon as={insight.icon} color={`${insight.color}.600`} />
              </Circle>
              <Text
                fontSize="xl"
                fontWeight="bold"
                color={`${insight.color}.600`}
              >
                {insight.value}
              </Text>
              <Text fontSize="xs" color="gray.600" textAlign="center">
                {insight.subtitle}
              </Text>
            </VStack>
          ))}
        </SimpleGrid>
      </Box>

      {/* Detailed Analysis Modal */}
      <Modal isOpen={isOpen} onClose={onClose} size="4xl">
        <ModalOverlay />
        <ModalContent>
          <ModalHeader>Detailed Portfolio Analysis</ModalHeader>
          <ModalCloseButton />
          <ModalBody pb={6}>
            <VStack spacing={6} align="stretch">
              <Accordion allowToggle>
                <AccordionItem>
                  <AccordionButton>
                    <Box flex="1" textAlign="left">
                      <HStack>
                        <Icon as={FaSearch} color="purple.500" />
                        <Text fontWeight="medium">DeFi Protocol Discovery</Text>
                      </HStack>
                    </Box>
                    <AccordionIcon />
                  </AccordionButton>
                  <AccordionPanel pb={4}>
                    <Text fontSize="sm" color="gray.600">
                      Found {analysis?.exa_data?.protocols_found || 0} DeFi
                      protocols including Uniswap, Curve, and Aave. Best APY
                      discovered: {analysis?.exa_data?.best_apy_found || "N/A"}
                    </Text>
                  </AccordionPanel>
                </AccordionItem>
              </Accordion>
            </VStack>
          </ModalBody>
        </ModalContent>
      </Modal>
    </>
  );
};

// Portfolio Analysis Summary Card - Simple and concise
const AIAnalysisSummaryCard = ({
  analysis,
}: {
  analysis?: PortfolioAnalysis;
}) => {
  const summary = analysis?.summary;

  if (!summary) {
    return null;
  }

  // Extract concise summary (first sentence or up to 150 characters)
  const getConciseSummary = (fullSummary?: string) => {
    if (!fullSummary) return "No analysis available";

    // Remove service unavailability notes for concise view
    const cleanSummary = fullSummary
      .replace(/Note: The following services.*?incomplete\./g, "")
      .trim();

    // Get first sentence or first 150 characters
    const firstSentence = cleanSummary.split(".")[0] + ".";
    return firstSentence.length > 150
      ? cleanSummary.substring(0, 150) + "..."
      : firstSentence;
  };

  const conciseSummary = getConciseSummary(summary);

  return (
    <Box
      p={6}
      bg="white"
      borderRadius="xl"
      borderWidth="1px"
      borderColor="gray.200"
    >
      <HStack mb={4}>
        <Icon as={FaLightbulb} color="yellow.500" />
        <Text fontSize="lg" fontWeight="semibold">
          Portfolio Analysis Summary
        </Text>
      </HStack>

      <Box>{renderFormattedText(conciseSummary)}</Box>
    </Box>
  );
};

export const EnhancedPortfolioSummary: React.FC<
  EnhancedPortfolioSummaryProps
> = ({ response, onActionClick, isLoading = false }) => {
  const analysis = response.analysis;

  // Debug logging to understand data structure
  React.useEffect(() => {
    if (analysis) {
      console.log("Portfolio Analysis Data:", analysis);
      console.log("Portfolio Data:", analysis.portfolio_data);
    }
  }, [analysis]);

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

  return (
    <Box w="100%" maxW="1200px" mx="auto">
      <VStack spacing={6} align="stretch">
        {/* Enhanced Portfolio Overview */}
        <PortfolioOverviewCard analysis={analysis} />

        {/* AI Analysis Summary - Concise by default */}
        <AIAnalysisSummaryCard analysis={analysis} />
      </VStack>
    </Box>
  );
};

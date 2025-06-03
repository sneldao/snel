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
} from "@chakra-ui/react";
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
    });

    // For now, return empty array since PortfolioData interface doesn't include token details
    // This will be populated when the backend provides token-level data

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
                <Th isNumeric>Balance</Th>
                <Th isNumeric>Value</Th>
                <Th isNumeric>24h Change</Th>
              </Tr>
            </Thead>
            <Tbody>
              {tokens.map((token, idx) => (
                <Tr key={idx}>
                  <Td>
                    <VStack align="start" spacing={0}>
                      <Text fontWeight="medium">{token.symbol}</Text>
                      <Text fontSize="xs" color="gray.500">
                        {token.name}
                      </Text>
                    </VStack>
                  </Td>
                  <Td isNumeric>{token.balance}</Td>
                  <Td isNumeric fontWeight="medium">
                    {token.value}
                  </Td>
                  <Td isNumeric>
                    <Text
                      color={
                        token.change.startsWith("+") ? "green.500" : "red.500"
                      }
                    >
                      {token.change}
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

  const insights = [
    {
      title: "Protocol Discovery",
      value: analysis?.exa_data?.protocols_found || 0,
      subtitle: "DeFi protocols found",
      icon: FaSearch,
      color: "purple",
    },
    {
      title: "Yield Opportunities",
      value: analysis?.exa_data?.yield_opportunities || 0,
      subtitle: "Available strategies",
      icon: FaPercentage,
      color: "green",
    },
    {
      title: "Security Analysis",
      value: analysis?.firecrawl_data?.security_audits || "N/A",
      subtitle: "Audit status",
      icon: FaShieldAlt,
      color: "blue",
    },
  ];

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

        <SimpleGrid columns={3} spacing={4}>
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
                        <Text fontWeight="medium">Exa Protocol Discovery</Text>
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

// AI Analysis Summary Card
const AIAnalysisSummaryCard = ({
  analysis,
}: {
  analysis?: PortfolioAnalysis;
}) => {
  const summary = analysis?.summary;
  const interpretation = analysis?.fullAnalysis;

  if (!summary && !interpretation) {
    return null;
  }

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
          AI Analysis Summary
        </Text>
      </HStack>

      <VStack spacing={4} align="stretch">
        {summary && (
          <Box>
            <Text fontSize="md" fontWeight="medium" color="blue.600" mb={2}>
              Summary
            </Text>
            {renderFormattedText(summary)}
          </Box>
        )}

        {interpretation && (
          <Box>
            <Text fontSize="md" fontWeight="medium" color="green.600" mb={2}>
              AI Interpretation
            </Text>
            {renderFormattedText(interpretation)}
          </Box>
        )}
      </VStack>
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
      <Box w="100%" bg="white" borderRadius="xl" p={6} boxShadow="sm">
        <VStack spacing={4}>
          <Spinner size="lg" color="blue.500" />
          <Text fontSize="lg" fontWeight="semibold">
            Analyzing portfolio...
          </Text>
          <Progress
            size="sm"
            isIndeterminate
            colorScheme="blue"
            w="100%"
            borderRadius="full"
          />
        </VStack>
      </Box>
    );
  }

  return (
    <Box w="100%" maxW="1200px" mx="auto">
      <VStack spacing={6} align="stretch">
        {/* Enhanced Portfolio Overview */}
        <PortfolioOverviewCard analysis={analysis} />

        {/* AI Analysis Summary */}
        <AIAnalysisSummaryCard analysis={analysis} />

        {/* Service Status and Data Insights */}
        <SimpleGrid columns={[1, 2]} spacing={6}>
          <ServiceStatusCard analysis={analysis} />
          <DataInsightsCard analysis={analysis} />
        </SimpleGrid>

        {/* Token Holdings Table */}
        <TokenHoldingsTable analysis={analysis} />

        {/* Action Recommendations */}
        {analysis?.actions && analysis.actions.length > 0 && (
          <Box
            p={6}
            bg="white"
            borderRadius="xl"
            borderWidth="1px"
            borderColor="gray.200"
          >
            <HStack mb={4}>
              <Icon as={FaExchangeAlt} color="blue.500" />
              <Text fontSize="lg" fontWeight="semibold">
                Recommended Actions
              </Text>
            </HStack>
            <SimpleGrid columns={[1, 2]} spacing={4}>
              {analysis.actions.slice(0, 4).map((action, idx) => (
                <Box
                  key={idx}
                  p={4}
                  bg="gray.50"
                  borderRadius="lg"
                  _hover={{ bg: "gray.100" }}
                  transition="all 0.2s"
                >
                  <Text fontSize="sm" fontWeight="medium" mb={2}>
                    {action.description}
                  </Text>
                  <Box position="relative">
                    <Button
                      size="sm"
                      colorScheme="blue"
                      isDisabled
                      opacity={0.5}
                      onClick={() => onActionClick && onActionClick(action)}
                    >
                      Execute
                    </Button>
                    <Badge
                      position="absolute"
                      top="-8px"
                      right="-8px"
                      colorScheme="orange"
                      fontSize="xs"
                      px={2}
                      py={1}
                      borderRadius="md"
                    >
                      Coming Soon
                    </Badge>
                  </Box>
                </Box>
              ))}
            </SimpleGrid>
          </Box>
        )}
      </VStack>
    </Box>
  );
};

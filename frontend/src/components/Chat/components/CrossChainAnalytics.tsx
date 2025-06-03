import React from "react";
import {
  Box,
  VStack,
  HStack,
  Text,
  Progress,
  Badge,
  SimpleGrid,
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
  StatArrow,
  Icon,
  Divider,
} from "@chakra-ui/react";
import {
  FaArrowRight,
  FaGasPump,
  FaExchangeAlt,
  FaChartLine,
} from "react-icons/fa";
import { AgentWorkflow } from "../../../services/agentService";

interface CrossChainAnalyticsProps {
  selectedChains: string[];
  workflow: AgentWorkflow | null;
}

export const CrossChainAnalytics: React.FC<CrossChainAnalyticsProps> = ({
  selectedChains,
  workflow,
}) => {
  if (!workflow?.stages.length) {
    return (
      <Box p={4}>
        <Text>No analytics data available</Text>
      </Box>
    );
  }

  const alphaQuestStage = workflow.stages.find(
    (stage) => stage.id === "alphaquest"
  );
  const crossChainData = alphaQuestStage?.output?.crossChainAnalytics;

  return (
    <VStack spacing={6} align="stretch" p={4}>
      <HStack spacing={2} justify="center">
        <Badge colorScheme="blue">{selectedChains[0]}</Badge>
        <Icon as={FaArrowRight} />
        <Badge colorScheme="green">{selectedChains[1]}</Badge>
      </HStack>

      <SimpleGrid columns={{ base: 1, md: 2 }} spacing={4}>
        <Stat>
          <StatLabel>Bridging Efficiency</StatLabel>
          <StatNumber>
            {crossChainData?.bridging_efficiency?.current?.toFixed(2) || "0"}%
          </StatNumber>
          <StatHelpText>
            <StatArrow
              type={
                (crossChainData?.bridging_efficiency?.potential || 0) >
                (crossChainData?.bridging_efficiency?.current || 0)
                  ? "increase"
                  : "decrease"
              }
            />
            Potential:{" "}
            {crossChainData?.bridging_efficiency?.potential?.toFixed(2) || "0"}%
          </StatHelpText>
        </Stat>

        <Stat>
          <StatLabel>Gas Optimization</StatLabel>
          <StatNumber>
            {crossChainData?.gas_optimization.estimated_savings.toFixed(2)}%
          </StatNumber>
          <StatHelpText>Potential savings through optimization</StatHelpText>
        </Stat>
      </SimpleGrid>

      <Divider />

      <Box>
        <Text fontWeight="medium" mb={4}>
          Cross-Chain Opportunities
        </Text>
        <VStack spacing={4} align="stretch">
          {crossChainData?.opportunities.map((opportunity, idx) => (
            <Box
              key={idx}
              p={4}
              borderRadius="lg"
              borderWidth="1px"
              borderColor="whiteAlpha.200"
            >
              <HStack justify="space-between" mb={2}>
                <Text fontSize="sm" fontWeight="medium">
                  {opportunity.description}
                </Text>
                <Badge
                  colorScheme={
                    opportunity.confidence > 0.7 ? "green" : "yellow"
                  }
                >
                  {(opportunity.confidence * 100).toFixed(0)}% confident
                </Badge>
              </HStack>
              <HStack spacing={4} mt={2}>
                <HStack>
                  <Icon as={FaChartLine} />
                  <Text fontSize="sm">
                    Gain: {opportunity.potential_gain.toFixed(2)}%
                  </Text>
                </HStack>
                <HStack>
                  <Icon as={FaGasPump} />
                  <Text fontSize="sm">Risk: {opportunity.risk_level}</Text>
                </HStack>
              </HStack>
            </Box>
          ))}
        </VStack>
      </Box>

      {crossChainData?.bridging_efficiency.recommendations && (
        <Box>
          <Text fontWeight="medium" mb={2}>
            Recommendations
          </Text>
          <VStack align="stretch" spacing={2}>
            {crossChainData.bridging_efficiency.recommendations.map(
              (recommendation, idx) => (
                <HStack key={idx} spacing={2}>
                  <Icon as={FaExchangeAlt} color="blue.400" />
                  <Text fontSize="sm">{recommendation}</Text>
                </HStack>
              )
            )}
          </VStack>
        </Box>
      )}
    </VStack>
  );
};

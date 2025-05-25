import React from "react";
import {
  Box,
  VStack,
  HStack,
  Text,
  Heading,
  Progress,
  List,
  ListItem,
  ListIcon,
  Divider,
  SimpleGrid,
  Card,
  CardHeader,
  CardBody,
  Stat,
  StatLabel,
  StatNumber,
} from "@chakra-ui/react";
import {
  CheckCircleIcon,
  WarningIcon,
  InfoIcon,
  StarIcon,
} from "@chakra-ui/icons";
import { AgnoResponse } from "../services/agnoService";

interface PortfolioAnalysisProps {
  response: AgnoResponse;
  isLoading?: boolean;
}

export const PortfolioAnalysis: React.FC<PortfolioAnalysisProps> = ({
  response,
  isLoading,
}) => {
  if (!response.analysis) {
    return null;
  }

  const { composition, keyInsights, risks, opportunities, recommendations } =
    response.analysis;

  return (
    <VStack spacing={6} align="stretch" w="full">
      {/* Portfolio Value */}
      <Card>
        <CardHeader>
          <Heading size="md">Portfolio Overview</Heading>
        </CardHeader>
        <CardBody>
          <Stat>
            <StatLabel>Total Portfolio Value</StatLabel>
            <StatNumber>${composition.totalValue.toLocaleString()}</StatNumber>
          </Stat>
        </CardBody>
      </Card>

      {/* Asset Allocation */}
      <Card>
        <CardHeader>
          <Heading size="md">Asset Allocation</Heading>
        </CardHeader>
        <CardBody>
          <VStack spacing={4} align="stretch">
            {Object.entries(composition.assetAllocation).map(
              ([asset, percentage]) => (
                <Box key={asset}>
                  <HStack justify="space-between">
                    <Text>
                      {asset.charAt(0).toUpperCase() + asset.slice(1)}
                    </Text>
                    <Text>{percentage}%</Text>
                  </HStack>
                  <Progress
                    value={percentage}
                    colorScheme={
                      asset === "tokens"
                        ? "blue"
                        : asset === "lps"
                        ? "green"
                        : "purple"
                    }
                  />
                </Box>
              )
            )}
          </VStack>
        </CardBody>
      </Card>

      {/* Chain Distribution */}
      <Card>
        <CardHeader>
          <Heading size="md">Chain Distribution</Heading>
        </CardHeader>
        <CardBody>
          <SimpleGrid columns={[1, 2, 3]} spacing={4}>
            {Object.entries(composition.chainDistribution).map(
              ([chain, percentage]) => (
                <Box key={chain} p={4} borderWidth={1} borderRadius="md">
                  <Text fontWeight="bold">{chain}</Text>
                  <Text fontSize="2xl">{percentage}%</Text>
                  <Progress
                    value={percentage}
                    colorScheme="teal"
                    size="sm"
                    mt={2}
                  />
                </Box>
              )
            )}
          </SimpleGrid>
        </CardBody>
      </Card>

      {/* Analysis Sections */}
      {[
        {
          title: "Key Insights",
          data: keyInsights,
          icon: InfoIcon,
          color: "blue",
        },
        { title: "Risks", data: risks, icon: WarningIcon, color: "red" },
        {
          title: "Opportunities",
          data: opportunities,
          icon: StarIcon,
          color: "yellow",
        },
        {
          title: "Recommendations",
          data: recommendations,
          icon: CheckCircleIcon,
          color: "green",
        },
      ].map((section) => (
        <Card key={section.title}>
          <CardHeader>
            <Heading size="md">{section.title}</Heading>
          </CardHeader>
          <CardBody>
            <List spacing={3}>
              {section.data.map((item, index) => (
                <ListItem key={index} display="flex" alignItems="flex-start">
                  <ListIcon
                    as={section.icon}
                    color={`${section.color}.500`}
                    mt={1}
                  />
                  <Text>{item}</Text>
                </ListItem>
              ))}
            </List>
          </CardBody>
        </Card>
      ))}

      {/* Reasoning Steps */}
      {response.reasoningSteps && response.reasoningSteps.length > 0 && (
        <Card>
          <CardHeader>
            <Heading size="md">Analysis Steps</Heading>
          </CardHeader>
          <CardBody>
            <List spacing={4}>
              {response.reasoningSteps.map((step, index) => (
                <ListItem key={index}>
                  <Text fontWeight="bold" color="blue.600">
                    {step.title}
                  </Text>
                  <Text mt={1} color="gray.600">
                    {step.content}
                  </Text>
                  {index < response.reasoningSteps!.length - 1 && (
                    <Divider my={4} />
                  )}
                </ListItem>
              ))}
            </List>
          </CardBody>
        </Card>
      )}
    </VStack>
  );
};

import React from "react";
import {
  Box,
  VStack,
  HStack,
  Text,
  Progress,
  Badge,
  Circle,
  SlideFade,
} from "@chakra-ui/react";
import {
  PortfolioMetric,
  AnalysisProgress,
} from "../../services/portfolioService";

// Shared Progress Feedback Component
export const ProgressFeedback: React.FC<{ steps: AnalysisProgress[] }> = ({
  steps,
}) => (
  <VStack
    spacing={2}
    align="stretch"
    p={4}
    bg="whiteAlpha.50"
    borderRadius="xl"
    borderWidth="1px"
    borderColor="whiteAlpha.200"
    maxH="200px"
    overflowY="auto"
    className="progress-feedback"
    sx={{
      "&::-webkit-scrollbar": { width: "4px" },
      "&::-webkit-scrollbar-track": { background: "whiteAlpha.100" },
      "&::-webkit-scrollbar-thumb": {
        background: "whiteAlpha.300",
        borderRadius: "full",
      },
    }}
  >
    {steps.map((step, idx) => (
      <SlideFade key={idx} in={true} offsetY="10px">
        <HStack spacing={3} opacity={idx === steps.length - 1 ? 1 : 0.6}>
          <Circle
            size="2"
            bg={
              step.type === "error"
                ? "red.400"
                : step.type === "thought"
                ? "purple.400"
                : step.type === "action"
                ? "green.400"
                : "blue.400"
            }
          />
          <Text
            fontSize="sm"
            color={step.type === "error" ? "red.300" : "gray.300"}
            fontFamily={step.type === "thought" ? "mono" : "body"}
          >
            {step.stage}
          </Text>
        </HStack>
      </SlideFade>
    ))}
  </VStack>
);

// Shared Metric Card Component
export const MetricCard: React.FC<{ metric: PortfolioMetric }> = ({
  metric,
}) => {
  const getChangeColor = (change?: number) => {
    if (!change) return "gray.400";
    return change > 0 ? "green.400" : "red.400";
  };

  return (
    <Box
      p={4}
      bg="whiteAlpha.50"
      borderRadius="xl"
      borderWidth="1px"
      borderColor="whiteAlpha.200"
    >
      <Text fontSize="sm" color="gray.400" mb={1}>
        {metric.label}
      </Text>
      <HStack justify="space-between">
        <Text fontSize="lg" fontWeight="medium">
          {typeof metric.value === "number"
            ? metric.type === "percentage"
              ? `${metric.value}%`
              : metric.type === "currency"
              ? `$${metric.value.toLocaleString()}`
              : metric.value.toLocaleString()
            : metric.value}
        </Text>
        {metric.change && (
          <Text fontSize="sm" color={getChangeColor(metric.change)}>
            {metric.change > 0 ? "+" : ""}
            {metric.change}%
          </Text>
        )}
      </HStack>
    </Box>
  );
};

// Shared Confidence Indicator Component
export const ConfidenceIndicator: React.FC<{ score: number }> = ({ score }) => {
  const getColor = (score: number) => {
    if (score >= 0.8) return "green";
    if (score >= 0.6) return "blue";
    if (score >= 0.4) return "yellow";
    return "red";
  };

  return (
    <Box>
      <Progress
        value={score * 100}
        size="sm"
        colorScheme={getColor(score)}
        borderRadius="full"
        width="100px"
      />
      <Text fontSize="xs" color="gray.400" mt={1} textAlign="center">
        {Math.round(score * 100)}% Confidence
      </Text>
    </Box>
  );
};

// Shared Risk Badge Component
export const RiskBadge: React.FC<{ risk: string }> = ({ risk }) => (
  <Badge
    colorScheme="red"
    variant="subtle"
    px={3}
    py={1}
    borderRadius="full"
    fontSize="sm"
  >
    {risk}
  </Badge>
);

// Shared Action Badge Component
export const ActionBadge: React.FC<{ action: string }> = ({ action }) => (
  <Badge
    colorScheme="blue"
    variant="subtle"
    px={3}
    py={1}
    borderRadius="full"
    fontSize="sm"
  >
    {action}
  </Badge>
);

import React from "react";
import {
  Box,
  VStack,
  HStack,
  Text,
  Progress,
  Badge,
  Icon,
  Tooltip,
} from "@chakra-ui/react";
import {
  FaCheckCircle,
  FaExclamationCircle,
  FaSpinner,
  FaClock,
} from "react-icons/fa";
import { AgentWorkflow } from "../../../services/agentService";

interface WorkflowProgressProps {
  workflow: AgentWorkflow;
}

export const WorkflowProgress: React.FC<WorkflowProgressProps> = ({
  workflow,
}) => {
  const getStageIcon = (status: string) => {
    switch (status) {
      case "completed":
        return FaCheckCircle;
      case "error":
        return FaExclamationCircle;
      case "active":
        return FaSpinner;
      default:
        return FaClock;
    }
  };

  const getStageColor = (status: string) => {
    switch (status) {
      case "completed":
        return "green";
      case "error":
        return "red";
      case "active":
        return "blue";
      default:
        return "gray";
    }
  };

  return (
    <Box
      borderWidth="1px"
      borderRadius="lg"
      p={4}
      bg="whiteAlpha.50"
      borderColor="whiteAlpha.200"
    >
      <VStack spacing={4} align="stretch">
        <Text fontWeight="medium" fontSize="sm">
          Analysis Progress
        </Text>
        {workflow.stages.map((stage) => (
          <Box key={stage.id}>
            <HStack justify="space-between" mb={1}>
              <HStack>
                <Icon
                  as={getStageIcon(stage.status)}
                  color={`${getStageColor(stage.status)}.400`}
                />
                <Text fontSize="sm">{stage.name}</Text>
              </HStack>
              <Tooltip label={stage.agent.description} placement="top" hasArrow>
                <Badge
                  colorScheme={getStageColor(stage.status)}
                  variant="subtle"
                >
                  {stage.status}
                </Badge>
              </Tooltip>
            </HStack>
            <Progress
              value={stage.progress}
              size="sm"
              colorScheme={getStageColor(stage.status)}
              borderRadius="full"
              bg="whiteAlpha.100"
            />
            {stage.output && (
              <VStack align="start" mt={2} spacing={1}>
                {stage.output.metrics.map((metric, idx) => (
                  <HStack key={idx} spacing={2}>
                    <Text fontSize="xs" color="gray.400">
                      {metric.label}:
                    </Text>
                    <Text fontSize="xs" fontWeight="medium">
                      {metric.value}
                      {metric.change && (
                        <Text
                          as="span"
                          color={metric.change > 0 ? "green.400" : "red.400"}
                          ml={1}
                        >
                          ({metric.change > 0 ? "+" : ""}
                          {metric.change}%)
                        </Text>
                      )}
                    </Text>
                  </HStack>
                ))}
              </VStack>
            )}
          </Box>
        ))}
      </VStack>
    </Box>
  );
};

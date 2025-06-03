import React from "react";
import {
  Box,
  VStack,
  HStack,
  Text,
  Progress,
  Badge,
  SimpleGrid,
  Icon,
} from "@chakra-ui/react";
import {
  FaCheckCircle,
  FaExclamationTriangle,
  FaSpinner,
} from "react-icons/fa";
import { AgentWorkflow } from "../../services/agentService";

interface WorkflowProgressProps {
  workflow: AgentWorkflow;
}

export const WorkflowProgress: React.FC<WorkflowProgressProps> = ({
  workflow,
}) => {
  const getStatusIcon = (
    status: "pending" | "active" | "completed" | "error"
  ) => {
    switch (status) {
      case "completed":
        return <Icon as={FaCheckCircle} color="green.400" />;
      case "error":
        return <Icon as={FaExclamationTriangle} color="red.400" />;
      case "active":
        return <Icon as={FaSpinner} color="blue.400" className="spin" />;
      default:
        return null;
    }
  };

  const getStatusColor = (
    status: "pending" | "active" | "completed" | "error"
  ) => {
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
      w="100%"
      bg="whiteAlpha.50"
      p={4}
      borderRadius="xl"
      borderWidth="1px"
      borderColor="whiteAlpha.200"
    >
      <VStack spacing={4} align="stretch">
        <Text fontSize="sm" fontWeight="medium">
          Analysis Progress
        </Text>

        <SimpleGrid columns={{ base: 1, md: 3 }} spacing={4}>
          {workflow.stages.map((stage) => (
            <Box key={stage.id}>
              <HStack justify="space-between" mb={2}>
                <HStack>
                  {getStatusIcon(stage.status)}
                  <Text fontSize="sm">{stage.name}</Text>
                </HStack>
                <Badge colorScheme={getStatusColor(stage.status)}>
                  {stage.status}
                </Badge>
              </HStack>
              <Progress
                value={stage.progress}
                size="sm"
                colorScheme={getStatusColor(stage.status)}
                borderRadius="full"
              />
              {stage.agent && (
                <Text fontSize="xs" color="whiteAlpha.600" mt={1}>
                  Agent: {stage.agent.name}
                </Text>
              )}
            </Box>
          ))}
        </SimpleGrid>
      </VStack>
    </Box>
  );
};

import React from "react";
import {
  Box,
  VStack,
  HStack,
  Spinner,
  Text,
  Progress,
  Circle,
  useColorModeValue,
} from "@chakra-ui/react";

interface LoadingStateProps {
  message?: string;
  progress?: number;
  steps?: Array<{
    label: string;
    completed: boolean;
  }>;
  variant?: "spinner" | "progress" | "steps";
}

export const LoadingState: React.FC<LoadingStateProps> = ({
  message = "Loading...",
  progress,
  steps = [],
  variant = "spinner",
}) => {
  const accentColor = useColorModeValue("blue.500", "blue.300");
  const bgColor = useColorModeValue("gray.100", "gray.700");

  if (variant === "steps" && steps.length > 0) {
    return (
      <VStack spacing={4} align="stretch">
        <Text fontSize="sm" fontWeight="medium" color="gray.600">
          {message}
        </Text>
        <VStack spacing={3} align="stretch">
          {steps.map((step, index) => (
            <HStack key={index} spacing={3}>
              <Circle
                size={6}
                bg={step.completed ? accentColor : bgColor}
                color={step.completed ? "white" : "gray.500"}
                fontSize="xs"
                fontWeight="bold"
              >
                {step.completed ? "✓" : index + 1}
              </Circle>
              <Text
                fontSize="sm"
                color={step.completed ? "green.600" : "gray.600"}
                fontWeight={step.completed ? "medium" : "normal"}
              >
                {step.label}
              </Text>
            </HStack>
          ))}
        </VStack>
      </VStack>
    );
  }

  if (variant === "progress" && progress !== undefined) {
    return (
      <VStack spacing={3} align="stretch">
        <HStack justify="space-between">
          <Text fontSize="sm" fontWeight="medium">
            {message}
          </Text>
          <Text fontSize="xs" color="gray.500">
            {Math.round(progress)}%
          </Text>
        </HStack>
        <Progress
          value={progress}
          colorScheme="blue"
          size="sm"
          borderRadius="full"
          bg={bgColor}
        />
      </VStack>
    );
  }

  return (
    <HStack spacing={3} justify="center" py={4}>
      <Spinner size="sm" color={accentColor} />
      <Text fontSize="sm" color="gray.600">
        {message}
      </Text>
    </HStack>
  );
};
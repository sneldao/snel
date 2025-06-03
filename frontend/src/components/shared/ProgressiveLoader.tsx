import React, { useState, useEffect } from "react";
import {
  Box,
  VStack,
  HStack,
  Text,
  Progress,
  Spinner,
  Badge,
} from "@chakra-ui/react";
import { AnalysisProgress } from "../../services/portfolioService";
import { TerminalProgress } from "./TerminalProgress";

interface ProgressiveLoaderProps {
  isLoading: boolean;
  progressSteps: AnalysisProgress[];
  onComplete?: (result: any) => void;
  onError?: (error: string) => void;
}

export const ProgressiveLoader: React.FC<ProgressiveLoaderProps> = ({
  isLoading,
  progressSteps,
  onComplete,
  onError,
}) => {
  const [currentProgress, setCurrentProgress] = useState(0);
  const [currentStage, setCurrentStage] = useState("Starting analysis...");

  useEffect(() => {
    if (progressSteps.length > 0) {
      const latestStep = progressSteps[progressSteps.length - 1];
      setCurrentProgress(latestStep.completion || 0);
      setCurrentStage(latestStep.stage);
      
      if (latestStep.type === "error" && onError) {
        onError(latestStep.details || "Analysis failed");
      }
    }
  }, [progressSteps, onError]);

  if (!isLoading && progressSteps.length === 0) {
    return null;
  }

  return (
    <Box
      w="100%"
      bg="white"
      borderRadius="xl"
      p={6}
      boxShadow="sm"
      borderWidth="1px"
      borderColor="gray.200"
    >
      <VStack spacing={4} align="stretch">
        <HStack spacing={3}>
          <Spinner size="md" color="blue.500" />
          <Text fontSize="lg" fontWeight="semibold" color="gray.700">
            {currentStage}
          </Text>
          <Badge colorScheme="blue">{currentProgress}%</Badge>
        </HStack>

        <Progress
          value={currentProgress}
          size="sm"
          colorScheme="blue"
          hasStripe
          isAnimated
          borderRadius="full"
          mb={3}
        />

        {progressSteps.length > 0 && (
          <TerminalProgress
            steps={progressSteps.map((step) => ({
              stage: step.stage,
              type: step.type,
              completion: step.completion,
              details: step.details,
            }))}
            isComplete={!isLoading}
          />
        )}

        <Text fontSize="sm" color="gray.500" textAlign="center">
          This may take 30-60 seconds for complete analysis
        </Text>
      </VStack>
    </Box>
  );
};

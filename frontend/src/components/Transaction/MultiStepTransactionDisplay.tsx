import React from "react";
import { Box, Text } from "@chakra-ui/react";
import { TransactionProgress } from "../TransactionProgress";

interface MultiStepTransactionDisplayProps {
  content: any;
  multiStepState: {
    steps: any[];
    currentStep: number;
    totalSteps: number;
    isComplete: boolean;
    error?: string;
  } | null;
  chainId: number;
  textColor: string;
  onDone?: () => void;
  onRetry?: () => void;
}

export const MultiStepTransactionDisplay: React.FC<MultiStepTransactionDisplayProps> = ({
  content,
  multiStepState,
  chainId,
  textColor,
  onDone,
  onRetry,
}) => {
  // Determine the display message: current step's description, or original content message
  const displayMessage = React.useMemo(() => {
    if (multiStepState && multiStepState.steps && multiStepState.steps.length > 0) {
      // Find the currently executing or pending step to show its description
      const currentStepObj = multiStepState.steps.find(s => s.step === multiStepState.currentStep) ||
        multiStepState.steps[multiStepState.steps.length - 1];
      if (currentStepObj && currentStepObj.description) {
        return currentStepObj.description;
      }
    }

    return typeof content === "object" && content.message
      ? content.message
      : "Executing multi-step transaction...";
  }, [multiStepState, content]);

  return (
    <Box>
      <Text color={textColor} mb={3} fontWeight="medium">
        {displayMessage}
      </Text>
      {multiStepState && (
        <TransactionProgress
          steps={multiStepState.steps}
          currentStep={multiStepState.currentStep}
          totalSteps={multiStepState.totalSteps}
          chainId={chainId}
          isComplete={multiStepState.isComplete}
          error={multiStepState.error}
          onDone={onDone}
          onRetry={onRetry}
        />
      )}
    </Box>
  );
};
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
}

export const MultiStepTransactionDisplay: React.FC<MultiStepTransactionDisplayProps> = ({
  content,
  multiStepState,
  chainId,
  textColor,
}) => {
  return (
    <Box>
      <Text color={textColor} mb={3}>
        {typeof content === "object" && content.message
          ? content.message
          : "Executing multi-step transaction..."}
      </Text>
      {multiStepState && (
        <TransactionProgress
          steps={multiStepState.steps}
          currentStep={multiStepState.currentStep}
          totalSteps={multiStepState.totalSteps}
          chainId={chainId}
          isComplete={multiStepState.isComplete}
          error={multiStepState.error}
        />
      )}
    </Box>
  );
};
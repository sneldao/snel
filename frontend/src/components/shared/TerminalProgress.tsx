import React, { useEffect, useRef } from "react";
import { Box, VStack, Text, useColorModeValue, Flex } from "@chakra-ui/react";
import { motion } from "framer-motion";

const blinkAnimation = `
  @keyframes blink {
    0% { opacity: 1; }
    50% { opacity: 0; }
    100% { opacity: 1; }
  }
`;

interface TerminalProgressProps {
  steps: {
    stage: string;
    type: "progress" | "thought" | "action" | "error";
    completion?: number;
    details?: string;
  }[];
  isComplete?: boolean;
}

export const TerminalProgress: React.FC<TerminalProgressProps> = ({
  steps,
  isComplete,
}) => {
  // Only show the last 5 steps to keep the UI compact
  const limitedSteps = steps.length > 5 ? steps.slice(-5) : steps;
  const terminalRef = useRef<HTMLDivElement>(null);
  const bgColor = useColorModeValue("gray.900", "gray.900");
  const textColor = useColorModeValue("green.400", "green.400");
  const promptColor = useColorModeValue("blue.400", "blue.400");
  const errorColor = useColorModeValue("red.400", "red.400");
  const thoughtColor = useColorModeValue("purple.400", "purple.400");

  useEffect(() => {
    if (terminalRef.current) {
      terminalRef.current.scrollTop = terminalRef.current.scrollHeight;
    }
  }, [steps]);

  const getStepColor = (type: string) => {
    switch (type) {
      case "error":
        return errorColor;
      case "thought":
        return thoughtColor;
      case "action":
        return promptColor;
      default:
        return textColor;
    }
  };

  const getPromptSymbol = (type: string) => {
    switch (type) {
      case "error":
        return "✖";
      case "thought":
        return "💭";
      case "action":
        return "→";
      default:
        return ">";
    }
  };

  return (
    <>
      <style>{blinkAnimation}</style>
      <Box
        bg={bgColor}
        borderRadius="md"
        p={3}
        fontFamily="mono"
        fontSize="xs"
        color={textColor}
        maxH="200px"
        overflowY="auto"
        ref={terminalRef}
        sx={{
          "&::-webkit-scrollbar": {
            width: "6px",
          },
          "&::-webkit-scrollbar-track": {
            bg: "whiteAlpha.100",
          },
          "&::-webkit-scrollbar-thumb": {
            bg: "whiteAlpha.300",
            borderRadius: "full",
          },
        }}
      >
        <VStack align="stretch" spacing={1}>
          {limitedSteps.map((step, idx) => (
            <motion.div
              key={idx}
              initial={{ opacity: 0, y: 5 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.15 }}
            >
              <Flex gap={1}>
                <Text color={getStepColor(step.type)} flexShrink={0} fontSize="xs">
                  {getPromptSymbol(step.type)}
                </Text>
                <VStack align="stretch" spacing={0} flex={1}>
                  <Text color={getStepColor(step.type)} fontSize="xs">{step.stage}</Text>
                  {step.details && (
                    <Text color="gray.500" fontSize="9px">
                      {step.details}
                    </Text>
                  )}
                  {step.completion !== undefined && step.completion < 100 && (
                    <Box
                      h="1px"
                      bg="whiteAlpha.100"
                      borderRadius="full"
                      overflow="hidden"
                      mt={0.5}
                    >
                      <Box
                        h="100%"
                        w={`${step.completion}%`}
                        bg={getStepColor(step.type)}
                        transition="width 0.2s ease-in-out"
                      />
                    </Box>
                  )}
                </VStack>
              </Flex>
            </motion.div>
          ))}
          {!isComplete && (
            <Text
              as="span"
              color={textColor}
              sx={{ animation: "blink 1s infinite" }}
              ml={1}
              fontSize="xs"
            >
              _
            </Text>
          )}
        </VStack>
      </Box>
    </>
  );
};

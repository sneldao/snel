import * as React from "react";
import {
  Box,
  HStack,
  VStack,
  Avatar,
  Text,
  Badge,
  Icon,
  Button,
} from "@chakra-ui/react";
import { CheckCircleIcon, QuestionIcon, WarningIcon } from "@chakra-ui/icons";

type CommandResponseProps = {
  content: string;
  timestamp: string;
  isCommand: boolean;
  onConfirm?: () => Promise<void>;
};

const formatSwapResponse = (
  content: string
): { preview: string; success: boolean } => {
  try {
    if (content.includes("SwapArgs")) {
      const match = content.match(/amount_in=(\d+),\s*amount_out=(\d+)/);
      if (match) {
        const amountIn = parseFloat(match[1]) / 1e18;
        const amountOut = parseFloat(match[2]) / 1e18;
        return {
          preview: `I'll swap ${amountIn.toFixed(
            4
          )} ETH for approximately ${amountOut.toFixed(4)} UNI tokens.`,
          success: true,
        };
      }
    }
    return { preview: content, success: false };
  } catch (error) {
    return { preview: content, success: false };
  }
};

export const CommandResponse = ({
  content,
  timestamp,
  isCommand,
  onConfirm,
}: CommandResponseProps) => {
  const [isConfirming, setIsConfirming] = React.useState(false);
  const isError =
    content.toLowerCase().includes("error") ||
    content.toLowerCase().includes("sorry");
  const needsConfirmation = isCommand && !content.includes("None") && !isError;

  const handleConfirm = async () => {
    if (!onConfirm) return;
    setIsConfirming(true);
    try {
      await onConfirm();
    } finally {
      setIsConfirming(false);
    }
  };

  // Format the content to be more conversational
  const formatContent = (content: string) => {
    if (isError) {
      return content;
    }

    if (content === "None") {
      return "I'm processing your request...";
    }

    if (isCommand) {
      const { preview, success } = formatSwapResponse(content);
      if (success) {
        return preview;
      }
      return content;
    } else {
      return content;
    }
  };

  const getBadgeProps = () => {
    if (isError) {
      return {
        colorScheme: "red",
        icon: WarningIcon,
        text: "Error",
      };
    }
    if (needsConfirmation) {
      return {
        colorScheme: "orange",
        icon: WarningIcon,
        text: "Needs Confirmation",
      };
    }
    return {
      colorScheme: isCommand ? "green" : "blue",
      icon: isCommand ? CheckCircleIcon : QuestionIcon,
      text: isCommand ? "Command" : "Question",
    };
  };

  const badge = getBadgeProps();
  const formattedContent = formatContent(content);

  return (
    <Box
      borderWidth="1px"
      borderRadius="lg"
      p={4}
      bg="white"
      shadow="sm"
      borderColor={
        isError ? "red.200" : needsConfirmation ? "orange.200" : undefined
      }
    >
      <HStack align="start" spacing={3}>
        <Avatar
          size="sm"
          name="Pointless"
          bg={
            isError
              ? "red.500"
              : needsConfirmation
              ? "orange.500"
              : "twitter.500"
          }
          color="white"
        />
        <VStack align="stretch" flex={1} spacing={2}>
          <HStack>
            <Text fontWeight="bold">Pointless</Text>
            <Text color="gray.500" fontSize="sm">
              @pointless_agent
            </Text>
            <Text color="gray.500" fontSize="sm">
              ·
            </Text>
            <Text color="gray.500" fontSize="sm">
              {timestamp}
            </Text>
            <Badge
              colorScheme={badge.colorScheme}
              ml="auto"
              display="flex"
              alignItems="center"
              gap={1}
            >
              <Icon as={badge.icon} />
              {badge.text}
            </Badge>
          </HStack>
          <Text whiteSpace="pre-wrap" color={isError ? "red.600" : "gray.700"}>
            {formattedContent}
          </Text>
          {needsConfirmation && (
            <VStack align="start" spacing={2} mt={2}>
              <Text fontSize="sm" color="orange.600">
                ⚠️ This action will execute a blockchain transaction that cannot
                be undone.
              </Text>
              <HStack>
                <Button
                  size="sm"
                  colorScheme="twitter"
                  onClick={handleConfirm}
                  isLoading={isConfirming}
                >
                  Confirm Transaction
                </Button>
                <Button size="sm" variant="ghost">
                  Cancel
                </Button>
              </HStack>
            </VStack>
          )}
          {content === "None" && (
            <Text fontSize="sm" color="gray.500" mt={2}>
              Please wait while I process your request...
            </Text>
          )}
          {!isError && !needsConfirmation && content !== "None" && (
            <Text fontSize="sm" color="gray.500" mt={2}>
              {isCommand
                ? "Transaction details will appear here once processed."
                : "Let me know if you have any other questions!"}
            </Text>
          )}
        </VStack>
      </HStack>
    </Box>
  );
};

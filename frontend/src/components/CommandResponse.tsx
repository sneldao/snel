import * as React from "react";
import {
  Box,
  HStack,
  VStack,
  Avatar,
  Text,
  Badge,
  Icon,
  List,
  ListItem,
  ListIcon,
  Spinner,
} from "@chakra-ui/react";
import {
  CheckCircleIcon,
  QuestionIcon,
  WarningIcon,
  TimeIcon,
  ChatIcon,
} from "@chakra-ui/icons";

type CommandResponseProps = {
  content: string;
  timestamp: string;
  isCommand: boolean;
  status?: "pending" | "processing" | "success" | "error";
  awaitingConfirmation?: boolean;
};

const LoadingSteps = [
  "Processing your command...",
  "Classifying command type...",
  "Getting token information...",
  "Converting amounts...",
  "Getting best swap route...",
  "Preparing transaction...",
];

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
          )} ETH for approximately ${amountOut.toFixed(
            4
          )} UNI tokens.\n\nDoes this look good? Reply with 'yes' to confirm or 'no' to cancel.`,
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
  status = "pending",
  awaitingConfirmation,
}: CommandResponseProps) => {
  const [currentStep, setCurrentStep] = React.useState(0);
  const isError = status === "error";
  const isLoading = status === "processing";
  const isSuccess = status === "success";
  const needsConfirmation = awaitingConfirmation;

  // Simulate progress through steps when loading
  React.useEffect(() => {
    if (isLoading) {
      const interval = setInterval(() => {
        setCurrentStep((prev) =>
          prev < LoadingSteps.length - 1 ? prev + 1 : prev
        );
      }, 1000);
      return () => clearInterval(interval);
    } else {
      setCurrentStep(0);
    }
  }, [isLoading]);

  const formatContent = (content: string) => {
    if (isError) {
      return content;
    }

    if (isLoading) {
      return LoadingSteps[currentStep];
    }

    if (isCommand && !isSuccess) {
      const { preview, success } = formatSwapResponse(content);
      if (success) {
        return preview;
      }
    }

    return content;
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
    if (isLoading) {
      return {
        colorScheme: "blue",
        icon: TimeIcon,
        text: "Processing",
      };
    }
    if (isSuccess) {
      return {
        colorScheme: "green",
        icon: CheckCircleIcon,
        text: "Success",
      };
    }
    return {
      colorScheme: isCommand ? "purple" : "blue",
      icon: isCommand ? ChatIcon : QuestionIcon,
      text: isCommand ? "User" : "Question",
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
        isError
          ? "red.200"
          : needsConfirmation
          ? "orange.200"
          : isSuccess
          ? "green.200"
          : undefined
      }
    >
      <HStack align="start" spacing={3}>
        <Avatar
          size="sm"
          name={isCommand && !isSuccess ? "You" : "Pointless"}
          bg={
            isError
              ? "red.500"
              : needsConfirmation
              ? "orange.500"
              : isSuccess
              ? "green.500"
              : isCommand
              ? "purple.500"
              : "twitter.500"
          }
          color="white"
        />
        <VStack align="stretch" flex={1} spacing={2}>
          <HStack>
            <Text fontWeight="bold">
              {isCommand && !isSuccess ? "You" : "Pointless"}
            </Text>
            <Text color="gray.500" fontSize="sm">
              {isCommand && !isSuccess ? "@user" : "@pointless_agent"}
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
              {isLoading && <Spinner size="xs" mr={1} />}
              <Icon as={badge.icon} />
              {badge.text}
            </Badge>
          </HStack>
          <Text whiteSpace="pre-wrap" color={isError ? "red.600" : "gray.700"}>
            {formattedContent}
          </Text>
          {isLoading && (
            <List spacing={1} mt={2}>
              {LoadingSteps.map((step, index) => (
                <ListItem
                  key={index}
                  color={index <= currentStep ? "blue.500" : "gray.400"}
                  fontSize="sm"
                  display="flex"
                  alignItems="center"
                >
                  {index < currentStep ? (
                    <ListIcon as={CheckCircleIcon} color="green.500" />
                  ) : index === currentStep ? (
                    <Spinner size="xs" mr={2} />
                  ) : (
                    <ListIcon as={TimeIcon} />
                  )}
                  {step}
                </ListItem>
              ))}
            </List>
          )}
          {needsConfirmation && (
            <Text fontSize="sm" color="orange.600" mt={2}>
              ⚠️ This action will execute a blockchain transaction that cannot
              be undone.
            </Text>
          )}
        </VStack>
      </HStack>
    </Box>
  );
};

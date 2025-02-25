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
  Link,
  Alert,
  AlertIcon,
  AlertTitle,
  AlertDescription,
  Divider,
} from "@chakra-ui/react";
import {
  CheckCircleIcon,
  QuestionIcon,
  WarningIcon,
  TimeIcon,
  ChatIcon,
  InfoIcon,
} from "@chakra-ui/icons";

type TokenInfo = {
  address?: string;
  symbol?: string;
  name?: string;
  verified?: boolean;
  source?: string;
  warning?: string;
};

type CommandResponseProps = {
  content: string;
  timestamp: string;
  isCommand: boolean;
  status?: "pending" | "processing" | "success" | "error";
  awaitingConfirmation?: boolean;
  agentType?: "default" | "swap";
  metadata?: {
    token_in_address?: string;
    token_in_symbol?: string;
    token_in_name?: string;
    token_in_verified?: boolean;
    token_in_source?: string;
    token_out_address?: string;
    token_out_symbol?: string;
    token_out_name?: string;
    token_out_verified?: boolean;
    token_out_source?: string;
  };
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
  agentType = "default",
  metadata,
}: CommandResponseProps) => {
  const [currentStep, setCurrentStep] = React.useState(0);
  const isError = status === "error";
  const isLoading = status === "processing";
  const isSuccess = status === "success";
  const needsConfirmation = awaitingConfirmation;

  // Extract token information from metadata
  const tokenInInfo: TokenInfo = metadata
    ? {
        address: metadata.token_in_address,
        symbol: metadata.token_in_symbol,
        name: metadata.token_in_name,
        verified: metadata.token_in_verified,
        source: metadata.token_in_source,
      }
    : {};

  const tokenOutInfo: TokenInfo = metadata
    ? {
        address: metadata.token_out_address,
        symbol: metadata.token_out_symbol,
        name: metadata.token_out_name,
        verified: metadata.token_out_verified,
        source: metadata.token_out_source,
      }
    : {};

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
      // Handle specific error cases
      if (content.includes("User rejected the request")) {
        return "Transaction cancelled by user.";
      }
      if (content.includes("No valid swap route found")) {
        return "No valid swap route found. Try a different amount or token pair.";
      }
      if (content.includes("Not enough liquidity")) {
        return "Not enough liquidity for this swap. Try a smaller amount.";
      }
      if (content.includes("Failed to execute swap")) {
        return "Failed to execute the swap. Please try again.";
      }
      // Handle token not found errors
      if (content.includes("Could not find contract address for token")) {
        return (
          <Box>
            <Text>{content}</Text>
            {content.includes("NURI") && (
              <Alert status="info" mt={2} borderRadius="md">
                <AlertIcon />
                <AlertDescription>
                  NURI token swaps are not supported through our service. Please
                  use SyncSwap or ScrollSwap directly.
                </AlertDescription>
              </Alert>
            )}
          </Box>
        );
      }
      // For other errors, clean up and return a user-friendly message
      if (content.includes("Transaction failed:")) {
        const cleanedError = content
          .replace(/Transaction failed: /g, "")
          .replace(/Request Arguments:[\s\S]*$/, "")
          .trim();
        return cleanedError;
      }
      // Return the original error if none of the above match
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

    // Format block explorer links
    if (content.includes("block explorer")) {
      return content.split("\n").map((line, i) => {
        if (line.startsWith("http")) {
          return (
            <Link
              key={i}
              href={line}
              isExternal
              color="blue.500"
              wordBreak="break-all"
              display="inline-block"
            >
              {line}
            </Link>
          );
        }
        return <Text key={i}>{line}</Text>;
      });
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

  // Get agent name and avatar based on agent type
  const getAgentInfo = () => {
    if (agentType === "swap") {
      return {
        name: "Wheeler-Dealer",
        handle: "@wheeler_dealer",
        avatarSrc: "/avatars/🕴️.png",
      };
    }
    return {
      name: "SNEL",
      handle: "@snel_agent",
      avatarSrc: "/avatars/🐌.png",
    };
  };

  const { name, handle, avatarSrc } = getAgentInfo();

  // Render token information if available
  const renderTokenInfo = () => {
    if (!metadata || isCommand || !isSuccess) return null;

    // Only show token info for swap transactions
    if (!content.includes("swap") && !content.includes("Swap")) return null;

    return (
      <Box mt={3} fontSize="sm">
        <Divider mb={2} />
        <Text fontWeight="bold" mb={1}>
          Token Information:
        </Text>

        {tokenInInfo.symbol && (
          <Box mb={2}>
            <Text fontWeight="semibold">From: {tokenInInfo.symbol}</Text>
            {tokenInInfo.name && (
              <Text color="gray.600">{tokenInInfo.name}</Text>
            )}
            {tokenInInfo.address && (
              <Text fontSize="xs" color="gray.500" wordBreak="break-all">
                Address: {tokenInInfo.address}
              </Text>
            )}
            {tokenInInfo.verified && (
              <Badge colorScheme="green" fontSize="xs">
                Verified
              </Badge>
            )}
            {tokenInInfo.source && (
              <Text fontSize="xs" color="gray.500">
                Source: {tokenInInfo.source}
              </Text>
            )}
          </Box>
        )}

        {tokenOutInfo.symbol && (
          <Box>
            <Text fontWeight="semibold">To: {tokenOutInfo.symbol}</Text>
            {tokenOutInfo.name && (
              <Text color="gray.600">{tokenOutInfo.name}</Text>
            )}
            {tokenOutInfo.address && (
              <Text fontSize="xs" color="gray.500" wordBreak="break-all">
                Address: {tokenOutInfo.address}
              </Text>
            )}
            {tokenOutInfo.verified ? (
              <Badge colorScheme="green" fontSize="xs">
                Verified
              </Badge>
            ) : (
              <Badge colorScheme="yellow" fontSize="xs">
                Unverified
              </Badge>
            )}
            {tokenOutInfo.source && (
              <Text fontSize="xs" color="gray.500">
                Source: {tokenOutInfo.source}
              </Text>
            )}
          </Box>
        )}

        {(!tokenInInfo.verified || !tokenOutInfo.verified) && (
          <Alert status="warning" mt={2} size="sm" borderRadius="md">
            <AlertIcon />
            <Box>
              <AlertTitle fontSize="xs">Caution</AlertTitle>
              <AlertDescription fontSize="xs">
                One or more tokens in this transaction are unverified. Always
                double-check contract addresses before proceeding.
              </AlertDescription>
            </Box>
          </Alert>
        )}
      </Box>
    );
  };

  const badge = getBadgeProps();
  const formattedContent = formatContent(content);

  return (
    <Box
      w="full"
      bg={isCommand ? "gray.50" : "white"}
      borderRadius="lg"
      p={{ base: 2, sm: 4 }}
      position="relative"
    >
      <HStack align="start" spacing={4} w="full">
        <Avatar
          size={{ base: "xs", sm: "sm" }}
          name={isCommand ? "You" : name}
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
          src={!isCommand ? avatarSrc : undefined}
        />
        <VStack align="stretch" flex={1} spacing={{ base: 1, sm: 2 }}>
          <HStack spacing={2} fontSize={{ base: "xs", sm: "sm" }}>
            <Text fontWeight="bold">{isCommand ? "You" : name}</Text>
            <Text color="gray.500">{isCommand ? "@user" : handle}</Text>
            <Text color="gray.500">·</Text>
            <Text color="gray.500">{timestamp}</Text>
            <Badge
              colorScheme={badge.colorScheme}
              ml={{ base: 0, sm: "auto" }}
              display="flex"
              alignItems="center"
              gap={1}
              fontSize={{ base: "2xs", sm: "xs" }}
            >
              {isLoading && <Spinner size="xs" mr={1} />}
              <Icon as={badge.icon} />
              {badge.text}
            </Badge>
          </HStack>
          <Box
            fontSize={{ base: "sm", sm: "md" }}
            whiteSpace="pre-wrap"
            wordBreak="break-word"
          >
            {formattedContent}
          </Box>
          {renderTokenInfo()}
          {isLoading && (
            <List spacing={1} mt={2} fontSize={{ base: "xs", sm: "sm" }}>
              {LoadingSteps.map((step, index) => (
                <ListItem
                  key={index}
                  color={index <= currentStep ? "blue.500" : "gray.400"}
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
            <Text fontSize={{ base: "xs", sm: "sm" }} color="orange.600" mt={2}>
              ⚠️ This action will execute a blockchain transaction that cannot
              be undone.
            </Text>
          )}
        </VStack>
      </HStack>
    </Box>
  );
};

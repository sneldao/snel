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
  useColorModeValue,
  Button,
  UnorderedList,
} from "@chakra-ui/react";
import {
  CheckCircleIcon,
  QuestionIcon,
  WarningIcon,
  TimeIcon,
  ChatIcon,
  InfoIcon,
} from "@chakra-ui/icons";
import { SwapConfirmation } from "./SwapConfirmation";
import { DCAConfirmation } from "./DCAConfirmation";
import AggregatorSelection from "./AggregatorSelection";

interface CommandResponseProps {
  content: string | any; // Updated to accept structured content
  timestamp: string;
  isCommand: boolean;
  status?: "pending" | "processing" | "success" | "error";
  awaitingConfirmation?: boolean;
  agentType?: "default" | "swap" | "dca";
  metadata?: any;
  requires_selection?: boolean;
  all_quotes?: any[];
  onQuoteSelect?: (response: any, quote: any) => void;
}

type TokenInfo = {
  address?: string;
  symbol?: string;
  name?: string;
  verified?: boolean;
  source?: string;
  warning?: string;
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

export const CommandResponse: React.FC<CommandResponseProps> = ({
  content,
  timestamp,
  isCommand,
  status = "success",
  awaitingConfirmation = false,
  agentType = "default",
  metadata,
  requires_selection = false,
  all_quotes = [],
  onQuoteSelect,
}) => {
  const [currentStep, setCurrentStep] = React.useState(0);
  const [isLoading, setIsLoading] = React.useState(false);
  const [showTokenInfo, setShowTokenInfo] = React.useState(false);

  const isError = status === "error";
  const isSuccess = status === "success";
  const needsConfirmation = awaitingConfirmation;
  const needsSelection =
    requires_selection && all_quotes && all_quotes.length > 0;

  const bgColor = useColorModeValue(
    isCommand ? "blue.50" : "gray.50",
    isCommand ? "blue.900" : "gray.700"
  );
  const borderColor = useColorModeValue(
    isCommand ? "blue.200" : "gray.200",
    isCommand ? "blue.700" : "gray.600"
  );
  const textColor = useColorModeValue("gray.800", "white");

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

  // Check for various response types
  const isConfirmation =
    typeof content === "object" && content?.type === "confirmation";
  const isSwapConfirmation =
    typeof content === "object" && content?.type === "swap_confirmation";
  const isDCAConfirmation =
    typeof content === "object" && content?.type === "dca_confirmation";
  const isSwapSuccess =
    typeof content === "object" && content?.type === "swap_success";
  const isDCASuccess =
    typeof content === "object" &&
    (content?.type === "dca_success" || content?.type === "dca_order_created");

  // Handle confirmation actions
  const handleConfirm = () => {
    // Simulate typing "yes" in the command input
    const inputElement = document.querySelector(
      'input[placeholder="Type a command..."]'
    ) as HTMLInputElement;
    if (inputElement) {
      inputElement.value = "yes";
      inputElement.focus();
      // Trigger the Enter key press
      const enterEvent = new KeyboardEvent("keydown", {
        key: "Enter",
        code: "Enter",
        keyCode: 13,
        which: 13,
        bubbles: true,
      });
      inputElement.dispatchEvent(enterEvent);
    }
  };

  const handleCancel = () => {
    // Simulate typing "no" in the command input
    const inputElement = document.querySelector(
      'input[placeholder="Type a command..."]'
    ) as HTMLInputElement;
    if (inputElement) {
      inputElement.value = "no";
      inputElement.focus();
      // Trigger the Enter key press
      const enterEvent = new KeyboardEvent("keydown", {
        key: "Enter",
        code: "Enter",
        keyCode: 13,
        which: 13,
        bubbles: true,
      });
      inputElement.dispatchEvent(enterEvent);
    }
  };

  // Handle quote selection
  const handleQuoteSelect = (quote: any) => {
    if (onQuoteSelect) {
      onQuoteSelect(
        {
          content,
          timestamp,
          isCommand,
          status,
          awaitingConfirmation,
          agentType,
          metadata,
          requires_selection,
          all_quotes,
        },
        quote
      );
    }
  };

  const formatContent = (text: string) => {
    return text.split("\n").map((line, i) => (
      <React.Fragment key={i}>
        {line}
        {i < text.split("\n").length - 1 && <br />}
      </React.Fragment>
    ));
  };

  // Format links in content
  const formatLinks = (text: string) => {
    // Regex to match URLs
    const urlRegex = /(https?:\/\/[^\s]+)/g;
    const parts = text.split(urlRegex);

    return parts.map((part, i) => {
      if (part.match(urlRegex)) {
        return (
          <Link key={i} href={part} isExternal color="blue.500">
            {part}
          </Link>
        );
      }
      return formatContent(part);
    });
  };

  // Render status icon
  const renderStatusIcon = () => {
    if (status === "pending") {
      return <InfoIcon color="blue.500" />;
    } else if (status === "processing") {
      return <Spinner size="sm" color="blue.500" />;
    } else if (status === "success") {
      return <CheckCircleIcon color="green.500" />;
    } else if (status === "error") {
      return <WarningIcon color="red.500" />;
    }
    return null;
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
    if (agentType === "dca") {
      return {
        name: "DCA Planner",
        handle: "@dca_planner",
        avatarSrc: "/avatars/📊.png",
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

  return (
    <Box
      p={3}
      borderRadius="md"
      borderWidth="1px"
      borderColor={borderColor}
      bg={bgColor}
      mb={3}
      position="relative"
      maxW="100%"
    >
      <HStack spacing={2} mb={2} alignItems="flex-start">
        <Avatar
          size="sm"
          name={
            isCommand
              ? "User"
              : agentType === "swap"
              ? "Wheeler-Dealer"
              : "SNEL"
          }
          src={isCommand ? undefined : avatarSrc}
          bg={isCommand ? "blue.500" : "gray.500"}
        />
        <VStack spacing={1} align="flex-start" flex={1}>
          <HStack spacing={2} width="100%" justifyContent="space-between">
            <Badge
              colorScheme={isCommand ? "blue" : "gray"}
              fontSize="xs"
              fontWeight="bold"
            >
              {isCommand
                ? "@user"
                : agentType === "swap"
                ? "@wheeler_dealer"
                : "@snel"}
            </Badge>
            <Text
              fontSize="xs"
              color="gray.500"
              flexShrink={0}
              ml={1}
              noOfLines={1}
            >
              {timestamp}
            </Text>
          </HStack>

          {isSwapConfirmation ? (
            <SwapConfirmation
              message={content}
              onConfirm={handleConfirm}
              onCancel={handleCancel}
            />
          ) : isDCAConfirmation ? (
            <DCAConfirmation
              message={content}
              onConfirm={handleConfirm}
              onCancel={handleCancel}
            />
          ) : isDCASuccess ? (
            <Box mt={2} mb={2}>
              <Alert status="success" rounded="md">
                <AlertIcon />
                <AlertTitle>Success!</AlertTitle>
                <AlertDescription>
                  {content.type === "dca_order_created"
                    ? "DCA order successfully created. You'll be swapping the specified amount on your chosen schedule."
                    : content.message || "DCA order setup complete."}
                  {content?.type === "error" &&
                    content?.content?.includes("minimum") && (
                      <Box mt={2}>
                        <Alert status="warning" rounded="md" size="sm">
                          <AlertIcon />
                          <Box>
                            <AlertTitle fontSize="sm">
                              DCA Requirements:
                            </AlertTitle>
                            <AlertDescription fontSize="xs">
                              <UnorderedList spacing={1} pl={4}>
                                <ListItem>
                                  Only available on Base chain
                                </ListItem>
                                <ListItem>Minimum $5 per swap</ListItem>
                                <ListItem>Uses WETH instead of ETH</ListItem>
                              </UnorderedList>
                            </AlertDescription>
                          </Box>
                        </Alert>
                      </Box>
                    )}
                  {metadata?.order_id && (
                    <Box mt={1}>
                      <Text>Order ID: {metadata.order_id}</Text>
                    </Box>
                  )}
                  {metadata?.details?.duration && (
                    <Box mt={1}>
                      <Text>
                        Schedule: {metadata.details.frequency} for{" "}
                        {metadata.details.duration} days
                      </Text>
                    </Box>
                  )}
                </AlertDescription>
              </Alert>
            </Box>
          ) : needsSelection ? (
            <Box mt={2} width="100%">
              <AggregatorSelection
                quotes={all_quotes}
                tokenSymbol={metadata?.token_out_symbol || "tokens"}
                tokenDecimals={metadata?.token_out_decimals || 18}
                onSelect={handleQuoteSelect}
              />
            </Box>
          ) : (
            <Text
              fontSize="sm"
              color={textColor}
              wordBreak="break-word"
              overflowWrap="break-word"
              whiteSpace="pre-wrap"
            >
              {typeof content === "string"
                ? formatLinks(
                    content.startsWith('{"response":')
                      ? JSON.parse(content).response
                      : content
                  )
                : typeof content === "object" &&
                  content !== null &&
                  content.text
                ? formatLinks(content.text)
                : typeof content === "object" &&
                  content !== null &&
                  content.message
                ? formatLinks(content.message)
                : typeof content === "object" &&
                  content !== null &&
                  content.response
                ? formatLinks(content.response)
                : formatLinks(
                    typeof content === "string"
                      ? content
                      : JSON.stringify(content, null, 2)
                  )}
            </Text>
          )}

          {awaitingConfirmation &&
            false && ( // Disabling this confirmation section as requested
              <HStack spacing={2} mt={2}>
                <Badge colorScheme="yellow" alignSelf="flex-start">
                  Needs Confirmation
                </Badge>
                <Button size="xs" colorScheme="green" onClick={handleConfirm}>
                  Confirm
                </Button>
                <Button size="xs" colorScheme="red" onClick={handleCancel}>
                  Cancel
                </Button>
              </HStack>
            )}

          {status === "processing" && (
            <Badge colorScheme="blue" alignSelf="flex-start" mt={2}>
              Processing
            </Badge>
          )}

          {status === "error" && (
            <Badge colorScheme="red" alignSelf="flex-start" mt={2}>
              Error
            </Badge>
          )}

          {status === "success" &&
            !isCommand &&
            !isSwapConfirmation &&
            !isDCAConfirmation &&
            !isDCASuccess && (
              <Badge colorScheme="green" alignSelf="flex-start" mt={2}>
                Success
              </Badge>
            )}
        </VStack>
      </HStack>
    </Box>
  );
};

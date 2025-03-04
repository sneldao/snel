import React from "react";
import {
  Box,
  Text,
  VStack,
  HStack,
  Badge,
  Icon,
  Tooltip,
  useColorModeValue,
} from "@chakra-ui/react";
import { InfoIcon, WarningIcon, CheckIcon } from "@chakra-ui/icons";

interface TokenInfo {
  address?: string;
  symbol?: string;
  name?: string;
  verified?: boolean;
  source?: string;
  warning?: string;
}

interface DCAConfirmationProps {
  message: {
    type?: "dca_confirmation";
    message?: string;
    amount?: number;
    from_token?: TokenInfo;
    to_token?: TokenInfo;
    token_in?: TokenInfo; // For backward compatibility
    token_out?: TokenInfo; // For backward compatibility
    frequency?: string;
    duration?: number;
    end_date?: string;
    warning?: string;
  };
  onConfirm: () => void;
  onCancel: () => void;
}

export const DCAConfirmation: React.FC<DCAConfirmationProps> = ({
  message,
  onConfirm,
  onCancel,
}) => {
  // Support both old and new formats
  const fromToken = message.from_token || message.token_in || {};
  const toToken = message.to_token || message.token_out || {};
  const amount = message.amount || 0;
  const frequency = message.frequency || "daily";
  const duration = message.duration || 30;

  const getFrequencyText = (freq: string) => {
    switch (freq) {
      case "daily":
        return "every day";
      case "weekly":
        return "every week";
      case "monthly":
        return "every month";
      default:
        return freq;
    }
  };

  const warningBgColor = useColorModeValue("yellow.50", "yellow.900");
  const warningBorderColor = useColorModeValue("yellow.200", "yellow.700");
  const warningTextColor = useColorModeValue("yellow.800", "yellow.200");

  const infoBgColor = useColorModeValue("blue.50", "blue.900");
  const infoBorderColor = useColorModeValue("blue.200", "blue.700");
  const infoTextColor = useColorModeValue("blue.800", "blue.200");

  const renderTokenInfo = (token: TokenInfo, label: string) => (
    <Box>
      <Text fontWeight="semibold">
        {label}: {token.symbol || "Unknown"}
      </Text>
      {token.name && <Text fontSize="sm">{token.name}</Text>}
      <HStack spacing={2} mt={1}>
        {token.verified ? (
          <Badge colorScheme="green" fontSize="xs">
            Verified
          </Badge>
        ) : (
          <Badge colorScheme="yellow" fontSize="xs">
            Unverified
          </Badge>
        )}
        {token.source && (
          <Text fontSize="xs" color="gray.500">
            Source: {token.source}
          </Text>
        )}
      </HStack>
      {token.address && (
        <Text fontSize="xs" color="gray.500" wordBreak="break-all">
          {token.address}
        </Text>
      )}
    </Box>
  );

  // Use the message text directly if available
  if (message.message) {
    return (
      <VStack spacing={4} align="stretch">
        <Text>{message.message}</Text>

        <VStack align="stretch" spacing={3} pl={4}>
          {fromToken.symbol && renderTokenInfo(fromToken, "From")}
          {toToken.symbol && renderTokenInfo(toToken, "To")}
        </VStack>

        {/* Warning box */}
        {message.warning && (
          <Box
            bg="yellow.50"
            p={3}
            borderRadius="md"
            borderWidth="1px"
            borderColor="yellow.300"
          >
            <HStack spacing={2} align="flex-start">
              <Box>⚠️</Box>
              <Text fontSize="sm">{message.warning}</Text>
            </HStack>
          </Box>
        )}

        <Text mt={2}>
          Would you like to proceed with setting up this DCA? Type 'yes' to
          continue or 'no' to cancel.
        </Text>
      </VStack>
    );
  }

  // Fallback to original format
  const endDate = message.end_date
    ? new Date(message.end_date)
    : new Date(Date.now() + duration * 24 * 60 * 60 * 1000);

  const formattedEndDate = endDate.toLocaleDateString(undefined, {
    year: "numeric",
    month: "long",
    day: "numeric",
  });

  return (
    <VStack spacing={4} align="stretch">
      <Text>
        I'll set up a Dollar Cost Average (DCA) order to swap{" "}
        <Text as="span" fontWeight="bold">
          {amount} {fromToken.symbol || "tokens"}
        </Text>{" "}
        for{" "}
        <Text as="span" fontWeight="bold">
          {toToken.symbol || "tokens"}
        </Text>{" "}
        {getFrequencyText(frequency)} for {duration} days.
      </Text>

      <Box
        bg={infoBgColor}
        p={3}
        borderRadius="md"
        borderWidth="1px"
        borderColor={infoBorderColor}
      >
        <HStack spacing={2} align="flex-start">
          <InfoIcon color="blue.500" mt={1} />
          <VStack align="stretch" spacing={1}>
            <Text fontSize="sm" color={infoTextColor}>
              <Text as="span" fontWeight="bold">
                DCA (Dollar Cost Averaging)
              </Text>{" "}
              helps reduce the impact of volatility by spreading out your
              purchases over time.
            </Text>
            <Text fontSize="sm" color={infoTextColor}>
              Your order will run until {formattedEndDate}.
            </Text>
          </VStack>
        </HStack>
      </Box>

      <VStack align="stretch" spacing={3} pl={4}>
        {fromToken.symbol && renderTokenInfo(fromToken, "From")}
        {toToken.symbol && renderTokenInfo(toToken, "To")}
      </VStack>

      {/* Warning for unverified tokens */}
      {(!fromToken.verified || !toToken.verified) && (
        <Box
          bg={warningBgColor}
          p={3}
          borderRadius="md"
          borderWidth="1px"
          borderColor={warningBorderColor}
        >
          <HStack spacing={2} align="flex-start">
            <WarningIcon color="yellow.500" mt={1} />
            <VStack align="stretch" spacing={1}>
              <Text fontSize="sm" fontWeight="bold" color={warningTextColor}>
                Warning: Unverified Tokens Detected
              </Text>
              <Text fontSize="sm" color={warningTextColor}>
                Please verify tokens before proceeding with DCA. Unverified
                tokens may pose risks.
              </Text>
            </VStack>
          </HStack>
        </Box>
      )}

      <Box
        bg="yellow.50"
        p={3}
        borderRadius="md"
        borderWidth="1px"
        borderColor="yellow.300"
      >
        <HStack spacing={2} align="flex-start">
          <Box>⚠️</Box>
          <Text fontSize="sm">
            <strong>Important:</strong> Please note that the OpenOcean DCA API
            is in beta. Always monitor your DCA orders regularly.
          </Text>
        </HStack>
      </Box>

      <Text mt={2}>
        Would you like to proceed with setting up this DCA? Type 'yes' to
        continue or 'no' to cancel.
      </Text>
    </VStack>
  );
};

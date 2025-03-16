import React from "react";
import {
  Box,
  Text,
  Button,
  VStack,
  HStack,
  Icon,
  Tooltip,
  Badge,
  Alert,
  AlertIcon,
  Divider,
} from "@chakra-ui/react";
import { InfoIcon, WarningIcon, CheckIcon } from "@chakra-ui/icons";
import { FaExchangeAlt, FaWallet, FaLink } from "react-icons/fa";

interface BrianConfirmationProps {
  message: {
    type: string;
    message: string;
    transaction?: {
      to: string;
      data: string;
      value: string;
      chainId: number;
      gasLimit: string;
      method: string;
    };
  };
  metadata?: {
    token_symbol?: string;
    token_name?: string;
    token_address?: string;
    amount?: number;
    recipient?: string;
    chain_id?: number;
    chain_name?: string;
    from_chain_id?: number;
    to_chain_id?: number;
    from_chain_name?: string;
    to_chain_name?: string;
    needs_approval?: boolean;
  };
  onConfirm: () => void;
  onCancel: () => void;
}

export const BrianConfirmation: React.FC<BrianConfirmationProps> = ({
  message,
  metadata,
  onConfirm,
  onCancel,
}) => {
  const isTransfer = message.transaction?.method === "transfer";
  const isBridge = message.transaction?.method === "bridge";

  const renderIcon = () => {
    if (isTransfer) {
      return <Icon as={FaWallet} color="blue.500" boxSize={5} />;
    } else if (isBridge) {
      return <Icon as={FaExchangeAlt} color="purple.500" boxSize={5} />;
    } else {
      return <Icon as={InfoIcon} color="gray.500" boxSize={5} />;
    }
  };

  const renderTitle = () => {
    if (isTransfer) {
      return "Token Transfer";
    } else if (isBridge) {
      return "Cross-Chain Bridge";
    } else {
      return "Transaction";
    }
  };

  const truncateAddress = (address: string) => {
    if (!address) return "";
    return `${address.substring(0, 6)}...${address.substring(
      address.length - 4
    )}`;
  };

  return (
    <Box
      borderWidth="1px"
      borderRadius="lg"
      p={4}
      mt={2}
      mb={2}
      width="100%"
      borderColor="gray.200"
      bg="white"
    >
      <VStack spacing={4} align="stretch">
        <HStack>
          {renderIcon()}
          <Text fontWeight="bold" fontSize="lg">
            {renderTitle()}
          </Text>
          <Badge
            colorScheme={isTransfer ? "blue" : isBridge ? "purple" : "gray"}
          >
            {metadata?.chain_name ||
              `Chain ID: ${message.transaction?.chainId}`}
          </Badge>
        </HStack>

        <Divider />

        <Text>{message.message}</Text>

        {metadata && (
          <Box bg="gray.50" p={3} borderRadius="md">
            <VStack align="stretch" spacing={2}>
              {metadata.token_symbol && (
                <HStack justify="space-between">
                  <Text fontWeight="semibold">Token:</Text>
                  <Text>
                    {metadata.token_symbol}
                    {metadata.token_name && ` (${metadata.token_name})`}
                  </Text>
                </HStack>
              )}

              {metadata.amount && (
                <HStack justify="space-between">
                  <Text fontWeight="semibold">Amount:</Text>
                  <Text>
                    {metadata.amount} {metadata.token_symbol}
                  </Text>
                </HStack>
              )}

              {metadata.recipient && (
                <HStack justify="space-between">
                  <Text fontWeight="semibold">Recipient:</Text>
                  <Text>{truncateAddress(metadata.recipient)}</Text>
                </HStack>
              )}

              {metadata.from_chain_name && metadata.to_chain_name && (
                <HStack justify="space-between">
                  <Text fontWeight="semibold">Route:</Text>
                  <Text>
                    {metadata.from_chain_name} → {metadata.to_chain_name}
                  </Text>
                </HStack>
              )}

              {metadata.needs_approval && (
                <Alert status="info" size="sm" borderRadius="md">
                  <AlertIcon />
                  <Text fontSize="sm">
                    This transaction requires token approval first
                  </Text>
                </Alert>
              )}
            </VStack>
          </Box>
        )}

        {/* Display note for Scroll chain transactions */}
        {message.transaction?.chainId === 534352 && (
          <Alert status="info" size="sm">
            <AlertIcon />
            <Text fontSize="sm">
              Transactions on Scroll may take longer to confirm
            </Text>
          </Alert>
        )}

        <HStack spacing={4} justify="flex-end">
          <Button size="sm" onClick={onCancel} variant="outline">
            Cancel
          </Button>
          <Button size="sm" colorScheme="blue" onClick={onConfirm}>
            Confirm
          </Button>
        </HStack>
      </VStack>
    </Box>
  );
};

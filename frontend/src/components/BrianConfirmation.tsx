import React from "react";
import {
  Box,
  Text,
  VStack,
  HStack,
  Icon,
  Badge,
  Alert,
  AlertIcon,
  Divider,
  Button,
  Flex,
  useToast,
} from "@chakra-ui/react";
import { InfoIcon } from "@chakra-ui/icons";
import { FaExchangeAlt, FaWallet, FaArrowRight } from "react-icons/fa";

interface BrianConfirmationProps {
  message: {
    type: string;
    message: string;
    bridge_id?: string;
    data?: any;
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
    dollar_amount?: number;
  };
  onConfirm: () => void;
  onCancel: () => void;
  onExecute?: (transaction: any) => void;
}

export const BrianConfirmation: React.FC<BrianConfirmationProps> = ({
  message,
  metadata,
  onConfirm,
  onCancel,
  onExecute,
}) => {
  const toast = useToast();
  const [isExecuting, setIsExecuting] = React.useState(false);

  const handleExecute = () => {
    if (message.transaction && onExecute) {
      setIsExecuting(true);
      try {
        onExecute(message.transaction);
      } catch (error) {
        console.error("Failed to execute transaction:", error);
        toast({
          title: "Transaction Failed",
          description: error instanceof Error ? error.message : "Unknown error",
          status: "error",
          duration: 5000,
          isClosable: true,
        });
      } finally {
        setIsExecuting(false);
      }
    }
  };

  const isTransfer = message.transaction?.method === "transfer";
  const isBridge =
    message.transaction?.method === "bridge" ||
    message.type === "brian_confirmation";

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

  // Extract chain names for bridge display
  let fromChainName = metadata?.from_chain_name;
  let toChainName = metadata?.to_chain_name;

  // If metadata doesn't have chain names but message data does (in case of brian_confirmation type)
  if (isBridge && message.data) {
    if (!fromChainName && message.data.from_chain) {
      fromChainName = message.data.from_chain.name;
    }
    if (!toChainName && message.data.to_chain) {
      toChainName = message.data.to_chain.name;
    }
  }

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
                    {metadata.dollar_amount && ` ($${metadata.dollar_amount})`}
                  </Text>
                </HStack>
              )}

              {metadata.recipient && (
                <HStack justify="space-between">
                  <Text fontWeight="semibold">Recipient:</Text>
                  <Text>{truncateAddress(metadata.recipient)}</Text>
                </HStack>
              )}

              {fromChainName && toChainName && (
                <HStack justify="space-between">
                  <Text fontWeight="semibold">Route:</Text>
                  <Text>
                    {fromChainName} → {toChainName}
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
        {(message.transaction?.chainId === 534352 ||
          metadata?.to_chain_id === 534352) && (
          <Alert status="info" size="sm">
            <AlertIcon />
            <Text fontSize="sm">
              Transactions on Scroll may take longer to confirm
            </Text>
          </Alert>
        )}

        {/* Add button to manually execute transaction */}
        {message.transaction && onExecute && (
          <Flex justify="center" mt={2} mb={2}>
            <Button
              leftIcon={<FaArrowRight />}
              colorScheme="blue"
              onClick={handleExecute}
              isLoading={isExecuting}
              loadingText="Sending"
            >
              Send to Wallet
            </Button>
          </Flex>
        )}
      </VStack>
    </Box>
  );
};

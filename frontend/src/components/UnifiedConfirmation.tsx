import React from "react";
import {
  Box,
  Text,
  Button,
  VStack,
  HStack,
  Badge,
  Divider,
} from "@chakra-ui/react";

interface TokenInfo {
  symbol: string;
  address?: string;
  decimals?: number;
  name?: string;
  logo_uri?: string;
  price_usd?: number;
  verified?: boolean;
  metadata?: Record<string, any>;
}

interface TransactionData {
  to: string;
  data?: string;
  value: string;
  gas_limit?: string;
  gas_price?: string;
  chain_id: number;
  from_address?: string;
}

interface UnifiedConfirmationProps {
  agentType: "transfer" | "bridge" | "swap" | "balance" | "portfolio";
  content: {
    message: string;
    type: string;
    details?: {
      amount?: string | number;
      token?: string;
      token_in?: string;
      token_out?: string;
      destination?: string;
      resolved_address?: string;
      chain?: string;
      source_chain?: string;
      destination_chain?: string;
      from_chain?: string;
      to_chain?: string;
      protocol?: string;
      route?: string;
    };
  };
  transaction?: TransactionData;
  metadata?: {
    token_in?: TokenInfo;
    token_out?: TokenInfo;
    protocol?: string;
    quote?: any;
    [key: string]: any;
  };
  onExecute: () => void;
  onCancel?: () => void;
  isLoading?: boolean;
}

export const UnifiedConfirmation: React.FC<UnifiedConfirmationProps> = ({
  agentType,
  content,
  transaction,
  metadata,
  onExecute,
  onCancel,
  isLoading = false,
}) => {
  const getTitle = () => {
    switch (agentType) {
      case "transfer":
        return "Token Transfer";
      case "bridge":
        return "Cross-Chain Bridge";
      case "swap":
        return "Token Swap";
      case "balance":
        return "Balance Check";
      case "portfolio":
        return "Portfolio Analysis";
      default:
        return "Transaction";
    }
  };

  const getActionColor = () => {
    switch (agentType) {
      case "transfer":
        return "blue";
      case "bridge":
        return "purple";
      case "swap":
        return "green";
      case "balance":
        return "orange";
      case "portfolio":
        return "teal";
      default:
        return "gray";
    }
  };

  const renderTransferDetails = () => {
    const amount = content.details?.amount || "0";
    const token = content.details?.token || "ETH";

    return (
      <VStack spacing={3} align="stretch">
        <HStack justify="space-between">
          <Text color="gray.600">Token:</Text>
          <Text fontWeight="bold">{token}</Text>
        </HStack>
        <HStack justify="space-between">
          <Text color="gray.600">Amount:</Text>
          <Text fontWeight="bold">
            {amount} {token}
          </Text>
        </HStack>
        <HStack justify="space-between">
          <Text color="gray.600">Recipient:</Text>
          <Text fontWeight="bold" fontSize="sm">
            {content.details?.resolved_address
              ? `${
                  content.details.destination
                } (${content.details.resolved_address.slice(
                  0,
                  6
                )}...${content.details.resolved_address.slice(-4)})`
              : content.details?.destination}
          </Text>
        </HStack>
        {/* Gas Optimization Hint */}
        {(content as any)?.gas_optimization_hint && (
          <Alert status="info" borderRadius="md" mt={2}>
            <AlertIcon />
            <Box flex="1">
              <AlertTitle fontSize="sm">Gas Optimization Tip</AlertTitle>
              <AlertDescription display="block" fontSize="xs">
                {(content as any)?.gas_optimization_hint}
              </AlertDescription>
            </Box>
          </Alert>
        )}
      </VStack>
    );
  };

  const renderBridgeDetails = () => {
    const amount = content.details?.amount || "0";
    const token = content.details?.token || "ETH";
    const sourceChain =
      content.details?.source_chain || content.details?.from_chain || "Base";
    const destChain =
      content.details?.destination_chain ||
      content.details?.to_chain ||
      content.details?.chain ||
      "Unknown";
    const route = content.details?.route || `${sourceChain} → ${destChain}`;

    return (
      <VStack spacing={3} align="stretch">
        <HStack justify="space-between">
          <Text color="gray.600">Token:</Text>
          <Text fontWeight="bold">{token}</Text>
        </HStack>
        <HStack justify="space-between">
          <Text color="gray.600">Amount:</Text>
          <Text fontWeight="bold">
            {amount} {token}
          </Text>
        </HStack>
        <HStack justify="space-between">
          <Text color="gray.600">Route:</Text>
          <Text fontWeight="bold">{route}</Text>
        </HStack>
        {content.details?.protocol && (
          <HStack justify="space-between">
            <Text color="gray.600">Protocol:</Text>
            <Badge colorScheme="purple">{content.details.protocol}</Badge>
          </HStack>
        )}
      </VStack>
    );
  };

  const renderSwapDetails = () => {
    // Extract values from content object (directly from backend) or fallback to details
    const amount = (content as any)?.amount || content.details?.amount || "0";
    const tokenIn =
      (content as any)?.token_in || content.details?.token_in || content.details?.token || "ETH";
    const tokenOut = (content as any)?.token_out || content.details?.token_out || "USDC";

    // Format amount to avoid scientific notation
    const formatAmount = (amt: string | number) => {
      if (typeof amt === "number") {
        return amt < 1 ? amt.toFixed(8).replace(/\.?0+$/, "") : amt.toString();
      }
      return amt;
    };

    return (
      <VStack spacing={3} align="stretch">
        <HStack justify="space-between">
          <Text color="gray.600">From:</Text>
          <Text fontWeight="bold">{tokenIn}</Text>
        </HStack>
        <HStack justify="space-between">
          <Text color="gray.600">Amount:</Text>
          <Text fontWeight="bold">
            {formatAmount(amount)} {tokenIn}
          </Text>
        </HStack>
        <HStack justify="space-between">
          <Text color="gray.600">To:</Text>
          <Text fontWeight="bold">{tokenOut}</Text>
        </HStack>
        {content.details?.chain && (
          <HStack justify="space-between">
            <Text color="gray.600">Network:</Text>
            <Text fontWeight="bold">{content.details.chain}</Text>
          </HStack>
        )}
        {(content as any)?.protocol && (
          <HStack justify="space-between">
            <Text color="gray.600">Protocol:</Text>
            <Badge colorScheme="green">{(content as any)?.protocol}</Badge>
          </HStack>
        )}
        {content.details?.protocol && (
          <HStack justify="space-between">
            <Text color="gray.600">Protocol:</Text>
            <Badge colorScheme="green">{content.details.protocol}</Badge>
          </HStack>
        )}
      </VStack>
    );
  };

  const renderDetails = () => {
    switch (agentType) {
      case "transfer":
        return renderTransferDetails();
      case "bridge":
        return renderBridgeDetails();
      case "swap":
        return renderSwapDetails();
      default:
        return (
          <Text color="gray.600" fontSize="sm">
            {content.message}
          </Text>
        );
    }
  };

  const renderTokenWarnings = () => {
    const tokenIn = metadata?.token_in;
    const tokenOut = metadata?.token_out;

    if (!tokenIn && !tokenOut) return null;

    const hasUnverifiedTokens =
      (tokenIn && !tokenIn.verified) || (tokenOut && !tokenOut.verified);

    if (!hasUnverifiedTokens) return null;

    return (
      <Box
        mt={2}
        mb={4}
        p={3}
        bg="orange.50"
        border="1px solid"
        borderColor="orange.200"
        borderRadius="md"
      >
        <Text fontSize="sm" color="orange.800" fontWeight="medium">
          ⚠️ Unverified Token Warning
        </Text>
        <Text fontSize="xs" color="orange.700" mt={1}>
          One or more tokens in this transaction are not verified. Please
          double-check the token addresses before proceeding.
        </Text>
      </Box>
    );
  };

  return (
    <Box
      bg="white"
      border="1px solid"
      borderColor="gray.200"
      borderRadius="lg"
      p={6}
      shadow="sm"
      maxW="md"
      mx="auto"
    >
      <VStack spacing={4} align="stretch">
        {/* Header */}
        <VStack spacing={2}>
          <Badge colorScheme={getActionColor()} size="lg" px={3} py={1}>
            {getTitle()}
          </Badge>
          <Text fontSize="sm" color="gray.600" textAlign="center">
            {content.message}
          </Text>
        </VStack>

        <Divider />

        {/* Details */}
        {renderDetails()}

        {/* Token Warnings */}
        {renderTokenWarnings()}

        {/* Transaction Info */}
        {transaction && (
          <Box fontSize="xs" color="gray.500">
            <Text>Chain ID: {transaction.chain_id}</Text>
            <Text>
              To: {transaction.to.slice(0, 6)}...{transaction.to.slice(-4)}
            </Text>
            {transaction.value !== "0" && (
              <Text>Value: {transaction.value} wei</Text>
            )}
          </Box>
        )}

        {/* Action Buttons */}
        <HStack spacing={3} pt={2}>
          {onCancel && (
            <Button
              variant="outline"
              colorScheme="gray"
              flex={1}
              onClick={onCancel}
              isDisabled={isLoading}
            >
              Cancel
            </Button>
          )}
          <Button
            colorScheme={getActionColor()}
            flex={1}
            onClick={onExecute}
            isLoading={isLoading}
            loadingText="Sending..."
          >
            Send to Wallet
          </Button>
        </HStack>
      </VStack>
    </Box>
  );
};

export default UnifiedConfirmation;
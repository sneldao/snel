import React from "react";
import {
  Box,
  Text,
  Button,
  VStack,
  HStack,
  Badge,
  Divider,
  Alert,
  AlertIcon,
  AlertTitle,
  AlertDescription,
  Circle,
  Icon,
  useColorModeValue,
} from "@chakra-ui/react";
import { motion, AnimatePresence } from "framer-motion";
import { CheckIcon } from "@chakra-ui/icons";

const MotionBox = motion(Box);
const MotionVStack = motion(VStack);

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
  agentType: "transfer" | "bridge" | "swap" | "balance" | "portfolio" | "payment";
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
      recipient?: string; // Add recipient for payment
      fee_mnee?: string; // Add fee for payment
      network?: string; // Add network for payment
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
  isSuccess?: boolean;
}

export const UnifiedConfirmation: React.FC<UnifiedConfirmationProps> = ({
  agentType,
  content,
  transaction,
  metadata,
  onExecute,
  onCancel,
  isLoading = false,
  isSuccess = false,
}) => {
  const cardBg = useColorModeValue("white", "gray.800");
  const borderColor = useColorModeValue("gray.200", "gray.700");
  const glassBg = useColorModeValue("rgba(255, 255, 255, 0.8)", "rgba(26, 32, 44, 0.8)");

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
      case "payment":
        return "Payment Action";
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
      case "payment":
        return "cyan";
      default:
        return "gray";
    }
  };

  const renderPaymentDetails = () => {
    const amount = content.details?.amount || "0";
    const token = content.details?.token || "MNEE";
    const recipient = content.details?.recipient || "Unknown";
    const fee = content.details?.fee_mnee || "Unknown";
    const network = content.details?.network || "cronos-testnet";
    const networkName = network === "cronos-testnet" ? "Cronos Testnet" :
      network === "cronos-mainnet" ? "Cronos Mainnet" :
        "Ethereum Mainnet";

    return (
      <VStack spacing={3} align="stretch">
        <HStack justify="space-between">
          <Text color="gray.600">Network:</Text>
          <Badge colorScheme={network.includes("testnet") ? "yellow" : "blue"}>
            {networkName}
          </Badge>
        </HStack>
        <HStack justify="space-between">
          <Text color="gray.600">Payment To:</Text>
          <Text fontFamily="monospace" fontSize="sm" fontWeight="bold">{recipient.slice(0, 10)}...{recipient.slice(-8)}</Text>
        </HStack>
        <HStack justify="space-between">
          <Text color="gray.600">Amount:</Text>
          <Text fontWeight="bold">
            {amount} {token}
          </Text>
        </HStack>
        {fee !== "Unknown" && (
          <HStack justify="space-between">
            <Text color="gray.600">Estimated Fee:</Text>
            <Text fontWeight="bold">{fee} MNEE</Text>
          </HStack>
        )}
        <Alert status="info" borderRadius="md" mt={2}>
          <AlertIcon />
          <Box flex="1">
            <AlertTitle fontSize="sm">Action Required</AlertTitle>
            <AlertDescription display="block" fontSize="xs">
              Please sign the transaction in your wallet to complete the payment.
            </AlertDescription>
          </Box>
        </Alert>
      </VStack>
    );
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
              ? `${content.details.destination
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
    const amount = (content as any)?.amount || (content as any)?.details?.amount || "0";
    const tokenIn =
      (content as any)?.token_in ||
      (content as any)?.details?.token_in ||
      (content as any)?.details?.token ||
      "ETH";
    const tokenOut =
      (content as any)?.token_out || (content as any)?.details?.token_out || "USDC";

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
    if (isSuccess) {
      return (
        <MotionVStack
          spacing={4}
          py={8}
          initial={{ scale: 0.8, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ type: "spring", damping: 12 }}
        >
          <Circle
            size="60px"
            bg="green.500"
            color="white"
            shadow="0 0 20px rgba(72, 187, 120, 0.4)"
          >
            <Icon as={CheckIcon} w={8} h={8} />
          </Circle>
          <VStack spacing={1}>
            <Text fontWeight="bold" fontSize="lg">
              Action Successful!
            </Text>
            <Text fontSize="sm" color="gray.500" textAlign="center">
              Your transaction has been submitted and is being processed.
            </Text>
          </VStack>
        </MotionVStack>
      );
    }

    switch (agentType) {
      case "transfer":
        return renderTransferDetails();
      case "bridge":
        return renderBridgeDetails();
      case "swap":
        return renderSwapDetails();
      case "payment":
        return renderPaymentDetails();
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
    <AnimatePresence>
      <MotionBox
        initial={{ y: 20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        exit={{ y: -20, opacity: 0 }}
        transition={{ duration: 0.3, ease: "easeOut" }}
        bg={cardBg}
        border="1px solid"
        borderColor={borderColor}
        borderRadius="2xl"
        p={{ base: 4, md: 6 }}
        shadow="xl"
        maxW="md"
        w="full"
        mx="auto"
        backdropFilter="blur(10px)"
        backgroundColor={glassBg}
      >
        <VStack spacing={4} align="stretch">
          {/* Header - Hidden on success */}
          {!isSuccess && (
            <>
              <VStack spacing={2}>
                <Badge
                  colorScheme={getActionColor()}
                  size="lg"
                  px={4}
                  py={1.5}
                  borderRadius="full"
                  textTransform="uppercase"
                  letterSpacing="wider"
                >
                  {getTitle()}
                </Badge>
                <Text fontSize="sm" color="gray.500" fontWeight="medium" textAlign="center">
                  Action Verification
                </Text>
              </VStack>
              <Divider />
            </>
          )}

          {/* Details */}
          {renderDetails()}

          {/* Token Warnings */}
          {!isSuccess && renderTokenWarnings()}

          {/* Transaction Info */}
          {!isSuccess && transaction && (
            <Box
              fontSize="2xs"
              color="gray.400"
              bg="gray.50"
              p={2}
              borderRadius="md"
              fontFamily="monospace"
            >
              <Text>Chain: {transaction.chain_id}</Text>
              <Text>
                To: {transaction.to.slice(0, 10)}...{transaction.to.slice(-8)}
              </Text>
              {transaction.value !== "0" && (
                <Text>Value: {transaction.value} wei</Text>
              )}
            </Box>
          )}

          {/* Action Buttons */}
          {!isSuccess && (
            <HStack spacing={4} pt={2}>
              {onCancel && (
                <Button
                  variant="ghost"
                  colorScheme="gray"
                  flex={1}
                  onClick={onCancel}
                  isDisabled={isLoading}
                  borderRadius="xl"
                  _hover={{ bg: "gray.100" }}
                >
                  Cancel
                </Button>
              )}
              <Button
                colorScheme={getActionColor()}
                flex={2}
                onClick={onExecute}
                isLoading={isLoading}
                loadingText={agentType === "payment" ? "Signing..." : "Sending..."}
                borderRadius="xl"
                size="lg"
                shadow="md"
                _hover={{ transform: "translateY(-2px)", shadow: "lg" }}
                _active={{ transform: "translateY(0)" }}
                transition="all 0.2s"
              >
                {agentType === "payment" ? "Authorize Payment" : "Execute Action"}
              </Button>
            </HStack>
          )}
        </VStack>
      </MotionBox>
    </AnimatePresence>
  );
};

export default UnifiedConfirmation;

import React, { useState } from "react";
import {
  Box,
  Text,
  Button,
  Link,
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalCloseButton,
  useDisclosure,
  VStack,
  HStack,
  Icon,
  Tooltip,
} from "@chakra-ui/react";
import {
  ExternalLinkIcon,
  InfoIcon,
  WarningIcon,
  CheckIcon,
} from "@chakra-ui/icons";

interface TokenInfo {
  address: string;
  symbol: string;
  name: string;
  metadata: {
    verified: boolean;
    source: string;
    warning?: string;
    decimals?: number;
    links?: VerificationLinks;
  };
}

interface VerificationLinks {
  explorer?: string;
  coingecko?: string;
  dexscreener?: string;
}

interface SwapConfirmationProps {
  message: {
    type: "swap_confirmation";
    amount: number;
    token_in: TokenInfo;
    token_out: TokenInfo;
    is_target_amount: boolean;
    amount_is_usd: boolean;
    note?: string;
    metadata?: {
      route_summary?: string;
      price_impact?: string;
      minimum_received?: string;
      estimated_gas_usd?: string;
      requires_contract?: boolean;
      token_symbol?: string;
      chain_id?: number;
      chain_name?: string;
      aggregator_info?: {
        supported_aggregators: string[];
        requires_api_key: {
          [key: string]: boolean;
        };
      };
      missing_key?: string;
      fallback_options?: string[];
    };
  };
  onConfirm: () => void;
  onCancel: () => void;
}

interface TokenDetailsModalProps {
  isOpen: boolean;
  onClose: () => void;
  token: TokenInfo;
}

const TokenDetailsModal: React.FC<TokenDetailsModalProps> = ({
  isOpen,
  onClose,
  token,
}) => {
  return (
    <Modal isOpen={isOpen} onClose={onClose} isCentered size="md">
      <ModalOverlay />
      <ModalContent>
        <ModalHeader>Token Details</ModalHeader>
        <ModalCloseButton />
        <ModalBody pb={6}>
          <VStack align="stretch" spacing={4}>
            {token.name && (
              <Box>
                <Text fontWeight="bold">Name</Text>
                <Text>{token.name}</Text>
              </Box>
            )}
            {token.symbol && (
              <Box>
                <Text fontWeight="bold">Symbol</Text>
                <Text>{token.symbol}</Text>
              </Box>
            )}
            {token.address && (
              <Box>
                <Text fontWeight="bold">Contract Address</Text>
                <Text fontSize="sm" wordBreak="break-all">
                  {token.address}
                </Text>
              </Box>
            )}
            {token.metadata.decimals !== undefined && (
              <Box>
                <Text fontWeight="bold">Decimals</Text>
                <Text>{token.metadata.decimals}</Text>
              </Box>
            )}
            {token.metadata.verified !== undefined && (
              <Box>
                <Text fontWeight="bold">Verification Status</Text>
                <HStack spacing={2}>
                  <Text>
                    {token.metadata.verified ? "Verified" : "Unverified"}
                  </Text>
                  {token.metadata.verified ? (
                    <Icon as={CheckIcon} color="green.500" />
                  ) : (
                    <Icon as={WarningIcon} color="yellow.500" />
                  )}
                </HStack>
              </Box>
            )}
            {token.metadata.links && (
              <Box>
                <Text fontWeight="bold" mb={2}>
                  Verification Links
                </Text>
                <VStack align="stretch" spacing={2}>
                  {token.metadata.links.dexscreener && (
                    <Link
                      href={token.metadata.links.dexscreener}
                      isExternal
                      color="blue.500"
                      display="flex"
                      alignItems="center"
                    >
                      <Icon as={ExternalLinkIcon} mr={2} />
                      View on DexScreener
                    </Link>
                  )}
                  {token.metadata.links.coingecko && (
                    <Link
                      href={token.metadata.links.coingecko}
                      isExternal
                      color="blue.500"
                      display="flex"
                      alignItems="center"
                    >
                      <Icon as={ExternalLinkIcon} mr={2} />
                      View on CoinGecko
                    </Link>
                  )}
                  {token.metadata.links.explorer && (
                    <Link
                      href={token.metadata.links.explorer}
                      isExternal
                      color="blue.500"
                      display="flex"
                      alignItems="center"
                    >
                      <Icon as={ExternalLinkIcon} mr={2} />
                      View on Block Explorer
                    </Link>
                  )}
                </VStack>
              </Box>
            )}
            {token.metadata.warning && (
              <Box
                bg="yellow.50"
                p={3}
                borderRadius="md"
                borderWidth="1px"
                borderColor="yellow.200"
              >
                <HStack spacing={2}>
                  <WarningIcon color="yellow.400" />
                  <Text color="yellow.800">{token.metadata.warning}</Text>
                </HStack>
              </Box>
            )}
          </VStack>
        </ModalBody>
      </ModalContent>
    </Modal>
  );
};

const TokenDisplay: React.FC<{
  token: TokenInfo;
  showInfoButton?: boolean;
}> = ({ token, showInfoButton = true }) => {
  const { isOpen, onOpen, onClose } = useDisclosure();

  return (
    <React.Fragment>
      <Text as="span" display="inline">
        {token.symbol}
      </Text>
      {showInfoButton && (
        <Box as="span" display="inline-block" ml={1} verticalAlign="middle">
          <Tooltip label="View token details">
            <InfoIcon
              cursor="pointer"
              color="blue.500"
              onClick={onOpen}
              _hover={{ color: "blue.600" }}
            />
          </Tooltip>
        </Box>
      )}
      <TokenDetailsModal isOpen={isOpen} onClose={onClose} token={token} />
    </React.Fragment>
  );
};

const AggregatorInfo: React.FC<{
  aggregatorInfo: {
    supported_aggregators: string[];
    requires_api_key: { [key: string]: boolean };
  };
  missingKey?: string;
  fallbackOptions?: string[];
}> = ({ aggregatorInfo, missingKey, fallbackOptions }) => {
  if (!aggregatorInfo) return null;

  return (
    <Box mt={4}>
      <Text fontWeight="medium" mb={2}>
        Available Aggregators:
      </Text>
      <VStack align="stretch" spacing={2}>
        {aggregatorInfo.supported_aggregators.map((agg) => (
          <HStack key={agg} spacing={2}>
            <Icon
              as={agg === missingKey ? WarningIcon : CheckIcon}
              color={agg === missingKey ? "yellow.500" : "green.500"}
            />
            <Text>
              {agg.toUpperCase()}{" "}
              {aggregatorInfo.requires_api_key[agg] && "(Requires API Key)"}
            </Text>
          </HStack>
        ))}
      </VStack>
      {missingKey && fallbackOptions && (
        <Box
          mt={2}
          p={3}
          bg="yellow.50"
          borderRadius="md"
          borderWidth="1px"
          borderColor="yellow.200"
        >
          <HStack spacing={2}>
            <WarningIcon color="yellow.400" />
            <Box>
              <Text color="yellow.800" fontWeight="medium">
                {missingKey.toUpperCase()} API key not configured
              </Text>
              <Text color="yellow.700" fontSize="sm">
                Falling back to: {fallbackOptions.join(", ").toUpperCase()}
              </Text>
            </Box>
          </HStack>
        </Box>
      )}
    </Box>
  );
};

export const SwapConfirmation: React.FC<SwapConfirmationProps> = ({
  message,
  onConfirm,
  onCancel,
}) => {
  const formatAmount = (amount: number, isUsd: boolean) => {
    if (isUsd) {
      return `$${amount.toFixed(2)}`;
    }
    return amount.toString();
  };

  const renderTokenInfo = (token: TokenInfo) => {
    const { isOpen, onOpen, onClose } = useDisclosure();

    return (
      <HStack spacing={2}>
        <Text>
          {token.symbol} ({token.name}) {token.metadata.verified ? "✓" : "⚠️"}
        </Text>
        {token.metadata.links && (
          <HStack spacing={2} ml={2}>
            {token.metadata.links.dexscreener && (
              <Link
                href={token.metadata.links.dexscreener}
                isExternal
                color="blue.500"
                fontSize="sm"
              >
                Chart <ExternalLinkIcon mx="1px" />
              </Link>
            )}
            {token.metadata.links.coingecko && (
              <Link
                href={token.metadata.links.coingecko}
                isExternal
                color="blue.500"
                fontSize="sm"
              >
                CoinGecko <ExternalLinkIcon mx="1px" />
              </Link>
            )}
            {token.metadata.links.explorer && (
              <Link
                href={token.metadata.links.explorer}
                isExternal
                color="blue.500"
                fontSize="sm"
              >
                Contract <ExternalLinkIcon mx="1px" />
              </Link>
            )}
          </HStack>
        )}
        <InfoIcon cursor="pointer" color="blue.500" onClick={onOpen} />
        <TokenDetailsModal isOpen={isOpen} onClose={onClose} token={token} />
      </HStack>
    );
  };

  const renderSwapMessage = () => {
    const { amount, token_in, token_out, is_target_amount, amount_is_usd } =
      message;
    const formattedAmount = formatAmount(amount, amount_is_usd);

    return (
      <Box>
        <Text fontSize="md" mb={4}>
          I'll help you swap {formattedAmount} of{" "}
          <TokenDisplay token={token_in} /> for{" "}
          <TokenDisplay token={token_out} />.
        </Text>

        {/* Display note for Scroll chain transactions */}
        {message.note && (
          <Box
            mt={2}
            mb={4}
            p={3}
            borderRadius="md"
            borderWidth="1px"
            borderColor="blue.200"
            bg="blue.50"
          >
            <Text fontSize="sm" color="blue.700">
              {message.note}
            </Text>
          </Box>
        )}

        {/* Display token verification warnings */}
        {(!token_in.metadata.verified || !token_out.metadata.verified) && (
          <Box
            mt={2}
            mb={4}
            p={3}
            borderRadius="md"
            borderWidth="1px"
            borderColor="yellow.200"
            bg="yellow.50"
          >
            <HStack spacing={2} alignItems="flex-start">
              <WarningIcon color="yellow.500" mt={1} />
              <Box>
                <Text fontSize="sm" fontWeight="medium" color="yellow.700">
                  Token Verification Warning
                </Text>
                <Text fontSize="sm" color="yellow.700">
                  {!token_in.metadata.verified &&
                    !token_out.metadata.verified &&
                    "Both tokens in this swap are unverified. Please verify the token addresses before proceeding."}
                  {token_in.metadata.verified &&
                    !token_out.metadata.verified &&
                    `${token_out.symbol} is unverified. Please verify the token address before proceeding.`}
                  {!token_in.metadata.verified &&
                    token_out.metadata.verified &&
                    `${token_in.symbol} is unverified. Please verify the token address before proceeding.`}
                </Text>
              </Box>
            </HStack>
          </Box>
        )}

        {/* Check if we need a contract address for any token */}
        {message.metadata?.requires_contract &&
          message.metadata.token_symbol && (
            <Box
              mt={4}
              p={4}
              borderRadius="md"
              borderWidth="1px"
              borderColor="blue.200"
              bg="blue.50"
            >
              <VStack align="stretch" spacing={3}>
                <HStack>
                  <InfoIcon color="blue.500" />
                  <Text color="blue.800" fontWeight="medium">
                    Contract Address Required
                  </Text>
                </HStack>
                <Text color="blue.800">
                  To proceed with this swap, please provide the contract address
                  for {message.metadata.token_symbol} on{" "}
                  {message.metadata.chain_name ?? "the selected chain"}.
                </Text>
                <Text fontSize="sm" color="blue.600">
                  You can try again with:
                  <br />
                  swap {formattedAmount} {message.token_in.symbol} for{" "}
                  {message.token_out.symbol} at{" "}
                  {message.metadata.chain_id ?? ""} [contract_address]
                </Text>
              </VStack>
            </Box>
          )}

        {/* Regular swap confirmation */}
        <VStack spacing={3} align="stretch" fontSize="md">
          {/* Token Information */}
          <VStack align="stretch" spacing={2} pl={4}>
            {renderTokenInfo(message.token_in)}
            {renderTokenInfo(message.token_out)}
          </VStack>

          {/* Swap Details */}
          {message.metadata && (
            <VStack align="stretch" spacing={2} pl={4} fontSize="sm">
              {message.metadata.route_summary && (
                <Text>{message.metadata.route_summary}</Text>
              )}
              {message.metadata.minimum_received && (
                <Text>
                  Minimum received: {message.metadata.minimum_received}
                </Text>
              )}
              {message.metadata.price_impact && (
                <Text>Price impact: {message.metadata.price_impact}</Text>
              )}
              {message.metadata.estimated_gas_usd && (
                <Text>
                  Estimated gas: ${message.metadata.estimated_gas_usd}
                </Text>
              )}
            </VStack>
          )}

          {/* Aggregator Information */}
          {message.metadata?.aggregator_info && (
            <AggregatorInfo
              aggregatorInfo={message.metadata.aggregator_info}
              missingKey={message.metadata.missing_key}
              fallbackOptions={message.metadata.fallback_options}
            />
          )}
        </VStack>

        {/* Confirmation Request */}
        <Text mt={2}>
          Would you like me to proceed with the swap? Type 'yes' to continue or
          'no' to cancel.
        </Text>
      </Box>
    );
  };

  return <Box>{renderSwapMessage()}</Box>;
};

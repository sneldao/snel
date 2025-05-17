import React, { useState } from "react";
import {
  Box,
  Text,
  VStack,
  HStack,
  Badge,
  Icon,
  Tooltip,
  useColorModeValue,
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalCloseButton,
  useDisclosure,
  Link,
  Button,
  Flex,
  Divider,
} from "@chakra-ui/react";
import {
  InfoIcon,
  WarningIcon,
  CheckIcon,
  ExternalLinkIcon,
} from "@chakra-ui/icons";

interface TokenInfo {
  address?: string;
  symbol?: string;
  name?: string;
  verified?: boolean;
  source?: string;
  warning?: string;
  decimals?: number;
  links?: {
    explorer?: string;
    coingecko?: string;
    dexscreener?: string;
  };
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
    amount_is_usd?: boolean;
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
            {token.decimals !== undefined && (
              <Box>
                <Text fontWeight="bold">Decimals</Text>
                <Text>{token.decimals}</Text>
              </Box>
            )}
            {token.verified !== undefined && (
              <Box>
                <Text fontWeight="bold">Verification Status</Text>
                <HStack spacing={2}>
                  <Text>{token.verified ? "Verified" : "Unverified"}</Text>
                  {token.verified ? (
                    <Icon as={CheckIcon} color="green.500" />
                  ) : (
                    <Icon as={WarningIcon} color="yellow.500" />
                  )}
                </HStack>
              </Box>
            )}
            {token.links && (
              <Box>
                <Text fontWeight="bold" mb={2}>
                  Verification Links
                </Text>
                <VStack align="stretch" spacing={2}>
                  {token.links.dexscreener && (
                    <Link
                      href={token.links.dexscreener}
                      isExternal
                      color="blue.500"
                      display="flex"
                      alignItems="center"
                    >
                      <Icon as={ExternalLinkIcon} mr={2} />
                      View on DexScreener
                    </Link>
                  )}
                  {token.links.coingecko && (
                    <Link
                      href={token.links.coingecko}
                      isExternal
                      color="blue.500"
                      display="flex"
                      alignItems="center"
                    >
                      <Icon as={ExternalLinkIcon} mr={2} />
                      View on CoinGecko
                    </Link>
                  )}
                  {token.links.explorer && (
                    <Link
                      href={token.links.explorer}
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
            {token.warning && (
              <Box
                bg="yellow.50"
                p={3}
                borderRadius="md"
                borderWidth="1px"
                borderColor="yellow.200"
              >
                <HStack spacing={2}>
                  <WarningIcon color="yellow.400" />
                  <Text color="yellow.800">{token.warning}</Text>
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
    <>
      <HStack spacing={2} align="center">
        <Box>
          <Text fontWeight="semibold">{token.symbol || "Unknown"}</Text>
          <Text fontSize="xs" color="gray.500">
            {token.name || "Unknown Token"}
          </Text>
        </Box>
        {token.verified ? (
          <Badge colorScheme="green" fontSize="xs">
            Verified
          </Badge>
        ) : (
          <Badge colorScheme="yellow" fontSize="xs">
            Unverified
          </Badge>
        )}
        {showInfoButton && (
          <Button
            size="xs"
            variant="ghost"
            onClick={onOpen}
            aria-label="Token details"
          >
            <InfoIcon />
          </Button>
        )}
      </HStack>
      <TokenDetailsModal isOpen={isOpen} onClose={onClose} token={token} />
    </>
  );
};

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
  const amountIsUsd = message.amount_is_usd || false;

  // Add useDisclosure hooks for both modals
  const {
    isOpen: isFromTokenModalOpen,
    onOpen: onFromTokenModalOpen,
    onClose: onFromTokenModalClose,
  } = useDisclosure();
  const {
    isOpen: isToTokenModalOpen,
    onOpen: onToTokenModalOpen,
    onClose: onToTokenModalClose,
  } = useDisclosure();

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

  // Calculate end date
  const endDate = message.end_date
    ? new Date(message.end_date)
    : new Date(Date.now() + duration * 24 * 60 * 60 * 1000);

  const formattedEndDate = endDate.toLocaleDateString(undefined, {
    year: "numeric",
    month: "long",
    day: "numeric",
  });

  // Format amount with currency symbol if needed
  const formattedAmount = amountIsUsd
    ? `$${amount}`
    : `${amount} ${fromToken.symbol || "tokens"}`;

  // Generate explorer links
  const getExplorerLink = (address: string) => {
    // Base chain explorer by default
    return `https://basescan.org/token/${address}`;
  };

  const getDexScreenerLink = (address: string) => {
    // Base chain DexScreener by default
    return `https://dexscreener.com/base/${address}`;
  };

  return (
    <VStack spacing={3} align="stretch">
      <Text fontSize="md" fontWeight="medium">
        I&apos;ll set up a Dollar Cost Average (DCA) order to swap{" "}
        <Text as="span" fontWeight="bold">
          {formattedAmount}
        </Text>{" "}
        for{" "}
        <Text as="span" fontWeight="bold">
          {toToken.symbol || "tokens"}
        </Text>{" "}
        {getFrequencyText(frequency)} for {duration} days.
      </Text>

      {/* Token information in a compact box */}
      <Box borderWidth="1px" borderRadius="md" overflow="hidden">
        <Box bg={useColorModeValue("gray.50", "gray.700")} px={4} py={2}>
          <Text fontWeight="bold" fontSize="sm">
            DCA Details
          </Text>
        </Box>

        <VStack spacing={0} divider={<Divider />} align="stretch">
          {/* Combined From/To Token Display */}
          <Box p={3}>
            <Flex justify="space-between" align="center">
              <HStack spacing={4}>
                <HStack>
                  <Text fontSize="sm" fontWeight="medium">
                    From:
                  </Text>
                  <Text fontWeight="semibold">
                    {fromToken.symbol || "Unknown"}
                  </Text>
                  {fromToken.verified ? (
                    <Badge colorScheme="green" fontSize="xs">
                      Verified
                    </Badge>
                  ) : (
                    <Badge colorScheme="yellow" fontSize="xs">
                      Unverified
                    </Badge>
                  )}
                  <Button
                    size="xs"
                    variant="ghost"
                    onClick={onFromTokenModalOpen}
                    aria-label="From token details"
                  >
                    <InfoIcon />
                  </Button>
                </HStack>
                <Text color="gray.500">→</Text>
                <HStack>
                  <Text fontSize="sm" fontWeight="medium">
                    To:
                  </Text>
                  <Text fontWeight="semibold">
                    {toToken.symbol || "Unknown"}
                  </Text>
                  {toToken.verified ? (
                    <Badge colorScheme="green" fontSize="xs">
                      Verified
                    </Badge>
                  ) : (
                    <Badge colorScheme="yellow" fontSize="xs">
                      Unverified
                    </Badge>
                  )}
                  <Button
                    size="xs"
                    variant="ghost"
                    onClick={onToTokenModalOpen}
                    aria-label="To token details"
                  >
                    <InfoIcon />
                  </Button>
                </HStack>
              </HStack>
            </Flex>
          </Box>

          {/* End Date */}
          <Box p={3}>
            <HStack justify="space-between">
              <Text fontSize="sm" fontWeight="medium">
                End Date:
              </Text>
              <Text fontSize="sm">{formattedEndDate}</Text>
            </HStack>
          </Box>
        </VStack>
      </Box>

      {/* From Token Modal */}
      <Modal
        isOpen={isFromTokenModalOpen}
        onClose={onFromTokenModalClose}
        isCentered
        size="md"
      >
        <ModalOverlay />
        <ModalContent>
          <ModalHeader>Token Details - {fromToken.symbol}</ModalHeader>
          <ModalCloseButton />
          <ModalBody pb={6}>
            <VStack align="stretch" spacing={4}>
              {fromToken.name && (
                <Box>
                  <Text fontWeight="bold">Name</Text>
                  <Text>{fromToken.name}</Text>
                </Box>
              )}
              {fromToken.symbol && (
                <Box>
                  <Text fontWeight="bold">Symbol</Text>
                  <Text>{fromToken.symbol}</Text>
                </Box>
              )}
              {fromToken.address && (
                <Box>
                  <Text fontWeight="bold">Contract Address</Text>
                  <Text fontSize="sm" wordBreak="break-all">
                    {fromToken.address}
                  </Text>
                </Box>
              )}
              {fromToken.decimals !== undefined && (
                <Box>
                  <Text fontWeight="bold">Decimals</Text>
                  <Text>{fromToken.decimals}</Text>
                </Box>
              )}
              {fromToken.verified !== undefined && (
                <Box>
                  <Text fontWeight="bold">Verification Status</Text>
                  <HStack spacing={2}>
                    <Text>
                      {fromToken.verified ? "Verified" : "Unverified"}
                    </Text>
                    {fromToken.verified ? (
                      <Icon as={CheckIcon} color="green.500" />
                    ) : (
                      <Icon as={WarningIcon} color="yellow.500" />
                    )}
                  </HStack>
                </Box>
              )}
              {fromToken.address && (
                <Box>
                  <Text fontWeight="bold" mb={2}>
                    Verification Links
                  </Text>
                  <VStack align="stretch" spacing={2}>
                    <Link
                      href={getExplorerLink(fromToken.address)}
                      isExternal
                      color="blue.500"
                    >
                      <HStack>
                        <ExternalLinkIcon />
                        <Text>View Contract on Basescan</Text>
                      </HStack>
                    </Link>
                    <Link
                      href={getDexScreenerLink(fromToken.address)}
                      isExternal
                      color="blue.500"
                    >
                      <HStack>
                        <ExternalLinkIcon />
                        <Text>View on DexScreener</Text>
                      </HStack>
                    </Link>
                  </VStack>
                </Box>
              )}
            </VStack>
          </ModalBody>
        </ModalContent>
      </Modal>

      {/* To Token Modal */}
      <Modal
        isOpen={isToTokenModalOpen}
        onClose={onToTokenModalClose}
        isCentered
        size="md"
      >
        <ModalOverlay />
        <ModalContent>
          <ModalHeader>Token Details - {toToken.symbol}</ModalHeader>
          <ModalCloseButton />
          <ModalBody pb={6}>
            <VStack align="stretch" spacing={4}>
              {toToken.name && (
                <Box>
                  <Text fontWeight="bold">Name</Text>
                  <Text>{toToken.name}</Text>
                </Box>
              )}
              {toToken.symbol && (
                <Box>
                  <Text fontWeight="bold">Symbol</Text>
                  <Text>{toToken.symbol}</Text>
                </Box>
              )}
              {toToken.address && (
                <Box>
                  <Text fontWeight="bold">Contract Address</Text>
                  <Text fontSize="sm" wordBreak="break-all">
                    {toToken.address}
                  </Text>
                </Box>
              )}
              {toToken.decimals !== undefined && (
                <Box>
                  <Text fontWeight="bold">Decimals</Text>
                  <Text>{toToken.decimals}</Text>
                </Box>
              )}
              {toToken.verified !== undefined && (
                <Box>
                  <Text fontWeight="bold">Verification Status</Text>
                  <HStack spacing={2}>
                    <Text>{toToken.verified ? "Verified" : "Unverified"}</Text>
                    {toToken.verified ? (
                      <Icon as={CheckIcon} color="green.500" />
                    ) : (
                      <Icon as={WarningIcon} color="yellow.500" />
                    )}
                  </HStack>
                </Box>
              )}
              {toToken.address && (
                <Box>
                  <Text fontWeight="bold" mb={2}>
                    Verification Links
                  </Text>
                  <VStack align="stretch" spacing={2}>
                    <Link
                      href={getExplorerLink(toToken.address)}
                      isExternal
                      color="blue.500"
                    >
                      <HStack>
                        <ExternalLinkIcon />
                        <Text>View Contract on Basescan</Text>
                      </HStack>
                    </Link>
                    <Link
                      href={getDexScreenerLink(toToken.address)}
                      isExternal
                      color="blue.500"
                    >
                      <HStack>
                        <ExternalLinkIcon />
                        <Text>View on DexScreener</Text>
                      </HStack>
                    </Link>
                  </VStack>
                </Box>
              )}
            </VStack>
          </ModalBody>
        </ModalContent>
      </Modal>

      {/* Combined info and warning box */}
      <Box
        bg={infoBgColor}
        p={3}
        borderRadius="md"
        borderWidth="1px"
        borderColor={infoBorderColor}
      >
        <VStack spacing={2} align="stretch">
          <HStack spacing={2} align="flex-start">
            <InfoIcon color="blue.500" mt={1} />
            <Text fontSize="sm" color={infoTextColor}>
              <Text as="span" fontWeight="bold">
                DCA
              </Text>{" "}
              helps reduce the impact of volatility by spreading out purchases
              over time.
            </Text>
          </HStack>

          <HStack spacing={2} align="flex-start">
            <WarningIcon color="yellow.500" mt={1} />
            <Text fontSize="sm" color={warningTextColor}>
              <Text as="span" fontWeight="bold">
                Important:
              </Text>{" "}
              DCA orders are executed automatically. Always monitor your orders
              and ensure you have sufficient balance.
            </Text>
          </HStack>
        </VStack>
      </Box>

      {/* Warning for unverified tokens - only show if needed */}
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
            <Text fontSize="sm" color={warningTextColor}>
              <Text as="span" fontWeight="bold">
                Warning:
              </Text>{" "}
              Unverified tokens detected. Please verify tokens before
              proceeding.
            </Text>
          </HStack>
        </Box>
      )}

      <Text fontSize="sm" mt={1}>
        Would you like to proceed with setting up this DCA? Type &apos;yes&apos;
        to continue or &apos;no&apos; to cancel.
      </Text>
    </VStack>
  );
};

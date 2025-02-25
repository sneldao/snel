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
import { ExternalLinkIcon, InfoIcon, WarningIcon } from "@chakra-ui/icons";

interface TokenInfo {
  symbol?: string;
  name?: string;
  address?: string;
  display: string;
  amount?: number;
  usd_value?: number;
}

interface VerificationLinks {
  explorer?: string;
  coingecko?: string;
  dexscreener?: string;
}

interface SwapConfirmationProps {
  message: {
    type: "swap_confirmation";
    text: string;
    subtext?: string;
    tokens: {
      in: TokenInfo;
      out: TokenInfo;
    };
    verification_links: {
      in: VerificationLinks;
      out: VerificationLinks;
    };
    warning?: string;
    confirmation_prompt: string;
  };
  onConfirm: () => void;
  onCancel: () => void;
}

interface TokenDetailsModalProps {
  isOpen: boolean;
  onClose: () => void;
  token: TokenInfo;
  links: VerificationLinks;
}

const TokenDetailsModal: React.FC<TokenDetailsModalProps> = ({
  isOpen,
  onClose,
  token,
  links,
}) => {
  const hasLinks = Object.keys(links).length > 0;
  const isUnverified = !hasLinks || (!links.explorer && !links.coingecko);

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

            {token.amount && (
              <Box>
                <Text fontWeight="bold">Amount</Text>
                <Text>{token.amount}</Text>
              </Box>
            )}

            {token.usd_value && (
              <Box>
                <Text fontWeight="bold">USD Value</Text>
                <Text>${token.usd_value.toFixed(2)}</Text>
              </Box>
            )}

            <Box>
              <Text fontWeight="bold" mb={2}>
                Verify On
              </Text>
              {hasLinks ? (
                <HStack spacing={4} wrap="wrap">
                  {links.explorer && (
                    <Link href={links.explorer} isExternal color="blue.500">
                      Explorer <ExternalLinkIcon mx="2px" />
                    </Link>
                  )}
                  {links.coingecko && (
                    <Link href={links.coingecko} isExternal color="blue.500">
                      CoinGecko <ExternalLinkIcon mx="2px" />
                    </Link>
                  )}
                  {links.dexscreener && (
                    <Link href={links.dexscreener} isExternal color="blue.500">
                      DexScreener <ExternalLinkIcon mx="2px" />
                    </Link>
                  )}
                </HStack>
              ) : (
                <Text fontSize="sm" color="gray.500">
                  No verification links available for this token.
                </Text>
              )}
            </Box>

            {isUnverified && (
              <Box
                bg="yellow.50"
                p={3}
                borderRadius="md"
                borderWidth="1px"
                borderColor="yellow.200"
                mt={2}
              >
                <HStack spacing={2} align="flex-start">
                  <WarningIcon color="yellow.400" mt={1} />
                  <Box>
                    <Text fontSize="sm" fontWeight="bold" color="yellow.800">
                      Caution: Unverified Token
                    </Text>
                    <Text fontSize="sm" color="yellow.800">
                      This token has limited or no verification information.
                      Anyone can create a token with any name or symbol. Always
                      verify the contract address before proceeding with a swap.
                    </Text>
                  </Box>
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
  links: VerificationLinks;
  showInfoButton?: boolean;
}> = ({ token, links, showInfoButton = true }) => {
  const { isOpen, onOpen, onClose } = useDisclosure();
  const hasLinks = Object.keys(links).length > 0;

  return (
    <>
      <HStack spacing={1} display="inline-flex" alignItems="center">
        <Text as="span">{token.display}</Text>
        {showInfoButton && (
          <Tooltip label="View token details">
            <InfoIcon
              cursor="pointer"
              color="blue.500"
              onClick={onOpen}
              _hover={{ color: "blue.600" }}
            />
          </Tooltip>
        )}
      </HStack>
      <TokenDetailsModal
        isOpen={isOpen}
        onClose={onClose}
        token={token}
        links={links}
      />
    </>
  );
};

export const SwapConfirmation: React.FC<SwapConfirmationProps> = ({
  message,
  onConfirm,
  onCancel,
}) => {
  // Create separate disclosures for token info modals
  const {
    isOpen: isTokenInModalOpen,
    onOpen: onTokenInModalOpen,
    onClose: onTokenInModalClose,
  } = useDisclosure();

  const {
    isOpen: isTokenOutModalOpen,
    onOpen: onTokenOutModalOpen,
    onClose: onTokenOutModalClose,
  } = useDisclosure();

  // Replace token displays in the message with interactive components
  const renderMessage = () => {
    const parts = message.text.split(
      /(ETH|USDC|\$[A-Za-z]+|0x[a-fA-F0-9]{40})/g
    );
    return parts.map((part, index) => {
      // Check if this part matches the input token display
      if (
        part === message.tokens.in.display ||
        (message.tokens.in.symbol && part === message.tokens.in.symbol) ||
        (message.tokens.in.address && part === message.tokens.in.address)
      ) {
        return (
          <TokenDisplay
            key={index}
            token={message.tokens.in}
            links={message.verification_links.in}
          />
        );
      }
      // Check if this part matches the output token display
      if (
        part === message.tokens.out.display ||
        (message.tokens.out.symbol && part === message.tokens.out.symbol) ||
        (message.tokens.out.address && part === message.tokens.out.address)
      ) {
        return (
          <TokenDisplay
            key={index}
            token={message.tokens.out}
            links={message.verification_links.out}
          />
        );
      }
      return part;
    });
  };

  return (
    <Box borderWidth="1px" borderRadius="lg" p={4}>
      <VStack align="stretch" spacing={4}>
        <Text fontSize="md">{renderMessage()}</Text>

        {message.subtext && (
          <Text fontSize="sm" color="gray.600">
            {message.subtext}
          </Text>
        )}

        {/* Token Information Section */}
        <Box
          borderWidth="1px"
          borderRadius="md"
          p={3}
          bg="gray.50"
          _dark={{ bg: "gray.700" }}
        >
          <Text fontSize="sm" fontWeight="medium" mb={2}>
            Token Information:
          </Text>

          <HStack spacing={4} justify="space-between" flexWrap="wrap">
            {/* Input Token Info */}
            <Box flex="1" minW="150px">
              <HStack>
                <Text fontSize="sm" fontWeight="bold">
                  From:
                </Text>
                <Text fontSize="sm">{message.tokens.in.display}</Text>
                <Tooltip label="View token details">
                  <InfoIcon
                    cursor="pointer"
                    color="blue.500"
                    onClick={onTokenInModalOpen}
                    _hover={{ color: "blue.600" }}
                    boxSize={3}
                  />
                </Tooltip>
              </HStack>
              {message.tokens.in.address && (
                <Text fontSize="xs" color="gray.500" noOfLines={1}>
                  {message.tokens.in.address.substring(0, 10)}...
                  {message.tokens.in.address.substring(
                    message.tokens.in.address.length - 8
                  )}
                </Text>
              )}
            </Box>

            {/* Output Token Info */}
            <Box flex="1" minW="150px">
              <HStack>
                <Text fontSize="sm" fontWeight="bold">
                  To:
                </Text>
                <Text fontSize="sm">{message.tokens.out.display}</Text>
                <Tooltip label="View token details">
                  <InfoIcon
                    cursor="pointer"
                    color="blue.500"
                    onClick={onTokenOutModalOpen}
                    _hover={{ color: "blue.600" }}
                    boxSize={3}
                  />
                </Tooltip>
              </HStack>
              {message.tokens.out.address && (
                <Text fontSize="xs" color="gray.500" noOfLines={1}>
                  {message.tokens.out.address.substring(0, 10)}...
                  {message.tokens.out.address.substring(
                    message.tokens.out.address.length - 8
                  )}
                </Text>
              )}
            </Box>
          </HStack>
        </Box>

        {message.warning && (
          <HStack
            bg="yellow.50"
            p={3}
            borderRadius="md"
            borderWidth="1px"
            borderColor="yellow.200"
          >
            <WarningIcon color="yellow.400" />
            <Text fontSize="sm" color="yellow.800">
              {message.warning}
            </Text>
          </HStack>
        )}

        <Text fontSize="md" fontWeight="medium">
          {message.confirmation_prompt}
        </Text>

        {/* Buttons removed as users should respond in chat */}
      </VStack>

      {/* Token Modals */}
      <TokenDetailsModal
        isOpen={isTokenInModalOpen}
        onClose={onTokenInModalClose}
        token={message.tokens.in}
        links={message.verification_links.in}
      />

      <TokenDetailsModal
        isOpen={isTokenOutModalOpen}
        onClose={onTokenOutModalClose}
        token={message.tokens.out}
        links={message.verification_links.out}
      />
    </Box>
  );
};

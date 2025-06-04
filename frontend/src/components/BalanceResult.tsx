"use client";

import React, { useState } from "react";
import {
  Box,
  VStack,
  HStack,
  Text,
  Badge,
  Button,
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalCloseButton,
  useColorModeValue,
  Divider,
  SimpleGrid,
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
  Icon,
  Flex,
} from "@chakra-ui/react";
import { FaWallet, FaCoins, FaExternalLinkAlt } from "react-icons/fa";

interface BalanceResultProps {
  content: any;
}

export const BalanceResult: React.FC<BalanceResultProps> = ({ content }) => {
  const [isModalOpen, setIsModalOpen] = useState(false);

  const bgColor = useColorModeValue("white", "gray.800");
  const borderColor = useColorModeValue("gray.200", "gray.600");
  const textColor = useColorModeValue("gray.800", "white");
  const mutedColor = useColorModeValue("gray.600", "gray.400");
  const modalBgColor = useColorModeValue("gray.50", "gray.700");
  const blueBgColor = useColorModeValue("blue.50", "blue.900");

  if (!content || typeof content !== "object") {
    return <Text color="red.500">Invalid balance data received</Text>;
  }

  const { message, chain, address, token, balance_data } = content;

  // Format balance data for display
  const formatBalanceData = (data: any) => {
    if (!data) return "No balance data available";

    // If it's a string, return as is
    if (typeof data === "string") {
      return data;
    }

    // If it's an object, try to extract meaningful information
    if (typeof data === "object") {
      // Look for common balance fields
      if (data.balance) return data.balance;
      if (data.amount) return data.amount;
      if (data.value) return data.value;

      // If it has multiple tokens, show count
      if (Array.isArray(data)) {
        return `${data.length} tokens found`;
      }

      // Otherwise show as JSON
      return JSON.stringify(data, null, 2);
    }

    return String(data);
  };

  const balanceDisplay = formatBalanceData(balance_data);

  return (
    <>
      <Box
        p={4}
        borderRadius="lg"
        borderWidth="1px"
        borderColor={borderColor}
        bg={bgColor}
      >
        <VStack spacing={3} align="stretch">
          {/* Header */}
          <HStack justify="space-between" align="center">
            <HStack spacing={2}>
              <Icon as={FaWallet} color="blue.500" />
              <Text fontWeight="bold" color={textColor}>
                Balance Check
              </Text>
            </HStack>
            <Badge colorScheme="green" variant="subtle">
              {chain}
            </Badge>
          </HStack>

          <Divider />

          {/* Summary */}
          <SimpleGrid columns={1} spacing={3}>
            <Stat>
              <StatLabel color={mutedColor}>
                {token === "All tokens" ? "Wallet Balance" : `${token} Balance`}
              </StatLabel>
              <StatNumber fontSize="lg" color={textColor}>
                {balanceDisplay}
              </StatNumber>
              <StatHelpText color={mutedColor}>
                {address?.slice(0, 6)}...{address?.slice(-4)} on {chain}
              </StatHelpText>
            </Stat>
          </SimpleGrid>

          {/* Actions */}
          <HStack spacing={2} justify="flex-end">
            <Button
              size="sm"
              variant="outline"
              colorScheme="blue"
              onClick={() => setIsModalOpen(true)}
              leftIcon={<Icon as={FaCoins} />}
            >
              View Details
            </Button>
          </HStack>
        </VStack>
      </Box>

      {/* Detailed Modal */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        size="lg"
      >
        <ModalOverlay backdropFilter="blur(4px)" />
        <ModalContent
          borderRadius="xl"
          boxShadow="xl"
          bg={bgColor}
          border="1px solid"
          borderColor={borderColor}
          mx={4}
        >
          <ModalHeader>
            <Flex align="center" gap={3}>
              <Icon as={FaWallet} color="blue.500" boxSize={5} />
              <Text>Balance Details</Text>
            </Flex>
          </ModalHeader>
          <ModalCloseButton />

          <ModalBody pb={6}>
            <VStack spacing={4} align="stretch">
              {/* Chain and Address Info */}
              <Box p={3} borderRadius="md" bg={modalBgColor}>
                <VStack spacing={2} align="stretch">
                  <HStack justify="space-between">
                    <Text fontSize="sm" color={mutedColor}>
                      Chain:
                    </Text>
                    <Badge colorScheme="blue">{chain}</Badge>
                  </HStack>
                  <HStack justify="space-between">
                    <Text fontSize="sm" color={mutedColor}>
                      Address:
                    </Text>
                    <Text fontSize="sm" fontFamily="mono" color={textColor}>
                      {address}
                    </Text>
                  </HStack>
                  <HStack justify="space-between">
                    <Text fontSize="sm" color={mutedColor}>
                      Token Filter:
                    </Text>
                    <Text fontSize="sm" color={textColor}>
                      {token}
                    </Text>
                  </HStack>
                </VStack>
              </Box>

              {/* Balance Data */}
              <Box>
                <Text fontSize="sm" color={mutedColor} mb={2}>
                  Balance Data:
                </Text>
                <Box
                  p={3}
                  borderRadius="md"
                  bg={modalBgColor}
                  maxH="300px"
                  overflowY="auto"
                >
                  <Text
                    fontSize="sm"
                    fontFamily="mono"
                    whiteSpace="pre-wrap"
                    color={textColor}
                  >
                    {balanceDisplay}
                  </Text>
                </Box>
              </Box>

              {/* Message */}
              {message && (
                <Box p={3} borderRadius="md" bg={blueBgColor}>
                  <Text fontSize="sm" color={textColor}>
                    {message}
                  </Text>
                </Box>
              )}
            </VStack>
          </ModalBody>
        </ModalContent>
      </Modal>
    </>
  );
};

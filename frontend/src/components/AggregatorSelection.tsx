import React, { useState, useEffect } from "react";
import {
  Box,
  Text,
  VStack,
  HStack,
  Button,
  Divider,
  Badge,
  useColorModeValue,
  Tooltip,
  Alert,
  AlertIcon,
} from "@chakra-ui/react";
import { formatTokenAmount, smallestUnitsToAmount } from "../utils/tokenUtils";
import { formatAmountForDisplay, validateGasUsd } from "../utils/formatUtils";

import { SwapQuote } from "../types/responses";

interface AggregatorSelectionProps {
  quotes: SwapQuote[];
  tokenSymbol: string;
  tokenDecimals: number;
  onSelect: (quote: SwapQuote) => void;
  chainId?: number;
  scrollNote?: string;
  isLoading?: boolean;
}

const AggregatorSelection: React.FC<AggregatorSelectionProps> = ({
  quotes,
  tokenSymbol,
  tokenDecimals,
  onSelect,
  chainId,
  scrollNote,
  isLoading,
}) => {
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null);
  const bgColor = useColorModeValue("white", "gray.800");
  const borderColor = useColorModeValue("gray.200", "gray.700");
  const hoverBgColor = useColorModeValue("gray.50", "gray.700");
  const selectedBgColor = useColorModeValue("blue.50", "blue.900");

  // Check if we're on Scroll chain
  const isScrollChain = chainId === 534352;

  // Sort quotes by buyAmount (descending), but prioritize Brian API for Scroll
  const sortedQuotes = [...quotes].sort((a, b) => {
    // If we're on Scroll and one is Brian API, prioritize it
    if (isScrollChain) {
      if (a.aggregator === "brian" && b.aggregator !== "brian") return -1;
      if (a.aggregator !== "brian" && b.aggregator === "brian") return 1;
    }

    // Otherwise sort by buyAmount
    try {
      const amountA = BigInt(a.buyAmount || "0");
      const amountB = BigInt(b.buyAmount || "0");
      return amountB > amountA ? 1 : amountB < amountA ? -1 : 0;
    } catch (e) {
      // Handle case where buyAmount might not be a valid BigInt
      return 0;
    }
  });

  // Auto-select the best quote (highest buy_amount or Brian API on Scroll) but DON'T execute it
  useEffect(() => {
    if (sortedQuotes.length > 0 && selectedIndex === null) {
      // If on Scroll, prefer Brian API
      if (isScrollChain) {
        const brianIndex = sortedQuotes.findIndex(
          (q) => q.aggregator === "brian"
        );
        if (brianIndex >= 0) {
          setSelectedIndex(brianIndex);
          // Removed the onSelect call here to prevent automatic execution
          return;
        }
      }

      // Otherwise select the first (best) quote visually
      setSelectedIndex(0);
      // Removed the onSelect call here to prevent automatic execution
    }
  }, [sortedQuotes, selectedIndex, isScrollChain]); // Removed onSelect from dependencies

  const handleSelect = (index: number) => {
    setSelectedIndex(index);
    onSelect(sortedQuotes[index]);
  };

  const formatAmount = (amount: string) => {
    if (!amount || amount === "0") {
      return "calculating...";
    }

    try {
      // First try our new formatting function
      return formatAmountForDisplay(amount, tokenDecimals);
    } catch (error) {
      // Fall back to the original method if there's an error
      return formatTokenAmount(
        smallestUnitsToAmount(amount, tokenDecimals),
        tokenDecimals
      );
    }
  };

  if (quotes.length === 0) {
    return (
      <Box p={4} borderRadius="md" borderWidth="1px" borderColor={borderColor}>
        <Text>No quotes available</Text>
      </Box>
    );
  }

  return (
    <VStack spacing={4} align="stretch" w="100%" opacity={isLoading ? 0.6 : 1} pointerEvents={isLoading ? "none" : "auto"}>
      <Text fontWeight="medium" fontSize="sm">
        Select a provider for your swap:
      </Text>

      {isScrollChain && scrollNote && (
        <Alert status="info" borderRadius="md">
          <AlertIcon />
          <Text fontSize="sm">{scrollNote}</Text>
        </Alert>
      )}

      {sortedQuotes.map((quote, index) => {
        const isBrianApi = quote.aggregator === "brian";

        return (
          <Box
            key={index}
            p={3}
            borderRadius="md"
            borderWidth="1px"
            borderColor={
              selectedIndex === index
                ? "blue.500"
                : isBrianApi && isScrollChain
                  ? "purple.300"
                  : borderColor
            }
            bg={selectedIndex === index ? selectedBgColor : bgColor}
            cursor="pointer"
            _hover={{
              bg: selectedIndex === index ? selectedBgColor : hoverBgColor,
            }}
            onClick={() => handleSelect(index)}
            position="relative"
          >
            <HStack justifyContent="space-between" mb={2}>
              <HStack>
                <Text fontWeight="bold">{quote.protocol}</Text>
                {index === 0 && !isBrianApi && (
                  <Badge colorScheme="green" fontSize="xs">
                    Best Rate
                  </Badge>
                )}
                {isBrianApi && isScrollChain && (
                  <Badge colorScheme="purple" fontSize="xs">
                    Recommended for Scroll
                  </Badge>
                )}
              </HStack>
              <Text
                fontWeight="semibold"
                color={selectedIndex === index ? "blue.500" : undefined}
              >
                {formatAmount(quote.buyAmount)} {tokenSymbol}
              </Text>
            </HStack>

            <HStack
              justifyContent="space-between"
              fontSize="xs"
              color="gray.500"
            >
              <Text>
                Price Impact: {quote.priceImpact || "0"}%
              </Text>
              {/* Gas estimate removed - users will see actual gas in their wallet */}
            </HStack>

            {selectedIndex === index && (
              <Box position="absolute" top={2} right={2}>
                <Badge colorScheme="blue">Selected</Badge>
              </Box>
            )}
          </Box>
        );
      })}

      <Box
        p={3}
        borderRadius="md"
        borderWidth="1px"
        bg="yellow.50"
        borderColor="yellow.300"
      >
        <HStack spacing={2} align="flex-start">
          <Box>⚠️</Box>
          <Text fontSize="sm">
            <strong>Important:</strong> Please carefully review the transaction
            details in your wallet before confirming. Verify the token amounts
            match your expectations.
          </Text>
        </HStack>
      </Box>
    </VStack>
  );
};

export default AggregatorSelection;

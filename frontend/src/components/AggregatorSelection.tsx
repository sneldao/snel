import React, { useState } from "react";
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
} from "@chakra-ui/react";
import { formatTokenAmount, smallestUnitsToAmount } from "../utils/tokenUtils";

interface Quote {
  aggregator: string;
  protocol: string;
  buy_amount: string;
  minimum_received: string;
  gas_usd: string;
  gas: string;
  to: string;
  data: string;
  value: string;
}

interface AggregatorSelectionProps {
  quotes: Quote[];
  tokenSymbol: string;
  tokenDecimals: number;
  onSelect: (quote: Quote) => void;
}

const AggregatorSelection: React.FC<AggregatorSelectionProps> = ({
  quotes,
  tokenSymbol,
  tokenDecimals,
  onSelect,
}) => {
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null);
  const bgColor = useColorModeValue("white", "gray.800");
  const borderColor = useColorModeValue("gray.200", "gray.700");
  const hoverBgColor = useColorModeValue("gray.50", "gray.700");
  const selectedBgColor = useColorModeValue("blue.50", "blue.900");

  // Sort quotes by buy_amount (descending)
  const sortedQuotes = [...quotes].sort((a, b) => {
    const amountA = BigInt(a.buy_amount);
    const amountB = BigInt(b.buy_amount);
    return amountB > amountA ? 1 : amountB < amountA ? -1 : 0;
  });

  // Auto-select the best quote (highest buy_amount)
  React.useEffect(() => {
    if (sortedQuotes.length > 0 && selectedIndex === null) {
      setSelectedIndex(0);
    }
  }, [sortedQuotes, selectedIndex]);

  const handleSelect = (index: number) => {
    setSelectedIndex(index);
    onSelect(sortedQuotes[index]);
  };

  const formatAmount = (amount: string) => {
    return formatTokenAmount(
      smallestUnitsToAmount(amount, tokenDecimals),
      tokenDecimals
    );
  };

  if (quotes.length === 0) {
    return (
      <Box p={4} borderRadius="md" borderWidth="1px" borderColor={borderColor}>
        <Text>No quotes available</Text>
      </Box>
    );
  }

  return (
    <VStack spacing={4} align="stretch" w="100%">
      <Text fontWeight="medium" fontSize="sm">
        Select a provider for your swap:
      </Text>

      {sortedQuotes.map((quote, index) => (
        <Box
          key={index}
          p={3}
          borderRadius="md"
          borderWidth="1px"
          borderColor={selectedIndex === index ? "blue.500" : borderColor}
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
              {index === 0 && (
                <Badge colorScheme="green" fontSize="xs">
                  Best Rate
                </Badge>
              )}
            </HStack>
            <Text
              fontWeight="semibold"
              color={selectedIndex === index ? "blue.500" : undefined}
            >
              {formatAmount(quote.buy_amount)} {tokenSymbol}
            </Text>
          </HStack>

          <HStack justifyContent="space-between" fontSize="xs" color="gray.500">
            <Text>
              Min. received: {formatAmount(quote.minimum_received)}{" "}
              {tokenSymbol}
            </Text>
            <Tooltip label="Estimated gas cost in USD">
              <Text>Gas: ${parseFloat(quote.gas_usd).toFixed(2)}</Text>
            </Tooltip>
          </HStack>

          {selectedIndex === index && (
            <Box position="absolute" top={2} right={2}>
              <Badge colorScheme="blue">Selected</Badge>
            </Box>
          )}
        </Box>
      ))}

      <Button
        colorScheme="blue"
        isDisabled={selectedIndex === null}
        onClick={() =>
          selectedIndex !== null && onSelect(sortedQuotes[selectedIndex])
        }
      >
        Confirm Selection
      </Button>
    </VStack>
  );
};

export default AggregatorSelection;

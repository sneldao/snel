"use client";
import React from "react";
import {
  Box,
  Button,
  VStack,
  Text,
  HStack,
  Icon,
  Badge,
  useColorModeValue,
  Spinner,
} from "@chakra-ui/react";
import { FaShieldAlt, FaUnlockAlt, FaExchangeAlt, FaEthereum } from "react-icons/fa";
import { useStarknetIntegration } from "../../hooks/useStarknetIntegration";

interface StarknetCommandHandlerProps {
  response: {
    content: any;
    message: string;
    success: boolean;
  };
  onExecute?: () => void;
  isExecuting?: boolean;
}

export function StarknetCommandHandler({ response, onExecute, isExecuting }: StarknetCommandHandlerProps) {
  const { content } = response;
  const metadata = content?.metadata || {};
  const starknetTx = content?.metadata?.starknet_tx;
  
  const { executeStarknetCall, isConnected } = useStarknetIntegration();
  const [isPending, setIsPending] = React.useState(false);
  const [txHash, setTxHash] = React.useState<string | null>(null);

  const bgColor = useColorModeValue("orange.50", "orange.900");
  const borderColor = useColorModeValue("orange.200", "orange.700");

  const handleExecute = async () => {
    if (!starknetTx) return;
    
    setIsPending(true);
    try {
      const result = await executeStarknetCall(
        starknetTx.contractAddress,
        starknetTx.entrypoint,
        starknetTx.calldata
      );
      if (result?.transaction_hash) {
        setTxHash(result.transaction_hash);
        onExecute?.();
      }
    } catch (error) {
      console.error("Starknet execution error:", error);
    } finally {
      setIsPending(false);
    }
  };

  const getActionIcon = () => {
    switch (starknetTx?.metadata?.action) {
      case "shield": return FaShieldAlt;
      case "unshield": return FaUnlockAlt;
      default: return FaExchangeAlt;
    }
  };

  return (
    <Box
      p={4}
      bg={bgColor}
      border="1px solid"
      borderColor={borderColor}
      borderRadius="lg"
      w="full"
    >
      <VStack align="start" spacing={3}>
        <HStack w="full" justify="space-between">
          <HStack>
            <Icon as={FaEthereum} color="orange.400" w={5} h={5} />
            <Text fontWeight="bold" fontSize="sm">Starknet Privacy Operation</Text>
          </HStack>
          <Badge colorScheme="orange">ZK-Powered</Badge>
        </HStack>

        <Text fontSize="sm">{response.message}</Text>

        {starknetTx && !txHash && (
          <Box w="full" p={3} bg="whiteAlpha.400" borderRadius="md" border="1px dashed" borderColor="orange.300">
            <VStack align="start" spacing={1}>
              <HStack>
                <Icon as={getActionIcon()} color="orange.500" />
                <Text fontSize="xs" fontWeight="bold">
                  {starknetTx.metadata?.action?.toUpperCase() || "TRANSACTION"} DETAILS
                </Text>
              </HStack>
              <Text fontSize="2xs" color="gray.600">Contract: {starknetTx.contractAddress.slice(0, 10)}...</Text>
              <Text fontSize="2xs" color="gray.600">Entrypoint: {starknetTx.entrypoint}</Text>
            </VStack>
          </Box>
        )}

        {txHash ? (
          <Box w="full" p={3} bg="green.50" color="green.700" borderRadius="md">
            <VStack align="start" spacing={1}>
              <Text fontSize="xs" fontWeight="bold">Transaction Sent!</Text>
              <Text fontSize="2xs" isTruncated w="full">Hash: {txHash}</Text>
              <Button 
                size="xs" 
                variant="link" 
                colorScheme="green"
                as="a"
                href={`https://starkscan.co/tx/${txHash}`}
                target="_blank"
              >
                View on Starkscan
              </Button>
            </VStack>
          </Box>
        ) : (
          <Button
            size="sm"
            colorScheme="orange"
            w="full"
            onClick={handleExecute}
            isLoading={isPending || isExecuting}
            isDisabled={!isConnected}
            leftIcon={<Icon as={FaEthereum} />}
          >
            {isConnected ? "Confirm & Execute on Starknet" : "Connect Starknet Wallet to Proceed"}
          </Button>
        )}
        
        {!isConnected && (
          <Text fontSize="xs" color="orange.600" fontStyle="italic">
            Note: You need Argent X or Braavos wallet connected.
          </Text>
        )}
      </VStack>
    </Box>
  );
}

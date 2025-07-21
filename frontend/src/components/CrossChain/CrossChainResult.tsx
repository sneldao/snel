import React from "react";
import {
  VStack,
  HStack,
  Text,
  Alert,
  AlertIcon,
  AlertTitle,
  AlertDescription,
  Box,
  Icon,
} from "@chakra-ui/react";
import { FaCheckCircle, FaClock, FaLink } from "react-icons/fa";

interface CrossChainResultProps {
  content: {
    type: string;
    message?: string;
    transaction?: { hash?: string };
    steps?: Array<{
      description: string;
      status: 'completed' | 'in_progress' | 'pending';
      txHash?: string;
    }>;
    axelar_powered?: boolean;
  };
  metadata?: {
    estimatedTime?: string;
  };
}

export const CrossChainResult: React.FC<CrossChainResultProps> = ({
  content,
  metadata,
}) => {
  return (
    <VStack spacing={4} align="stretch">
      <Alert status="success" borderRadius="md">
        <AlertIcon as={FaCheckCircle} />
        <Box>
          <AlertTitle>Cross-Chain Operation Successful!</AlertTitle>
          <AlertDescription>
            {content.message || 
             "Your cross-chain transaction has been initiated via Axelar Network."}
          </AlertDescription>
        </Box>
      </Alert>

      {content.transaction?.hash && (
        <Box p={4} bg="gray.50" borderRadius="md">
          <Text fontSize="sm" fontWeight="medium" mb={2}>
            Transaction Hash:
          </Text>
          <Text 
            fontSize="xs" 
            fontFamily="mono" 
            wordBreak="break-all"
            color="blue.600"
          >
            {content.transaction.hash}
          </Text>
        </Box>
      )}

      {Array.isArray(content.steps) && (
        <VStack spacing={3} align="stretch">
          <Text fontSize="sm" fontWeight="medium">Progress:</Text>
          {content.steps.map((step, index) => (
            <HStack key={index} spacing={3}>
              <Icon 
                as={step.status === 'completed' ? FaCheckCircle : FaClock} 
                color={step.status === 'completed' ? 'green.500' : 
                       step.status === 'in_progress' ? 'blue.500' : 'gray.400'}
              />
              <Text fontSize="sm">{step.description}</Text>
              {step.txHash && (
                <Icon as={FaLink} color="blue.400" />
              )}
            </HStack>
          ))}
        </VStack>
      )}

      <Box p={3} bg="blue.50" borderRadius="md">
        <HStack spacing={2}>
          <Icon as={FaLink} color="blue.500" />
          <VStack align="start" spacing={1}>
            <Text fontSize="sm" fontWeight="medium">
              Powered by Axelar Network
            </Text>
            <Text fontSize="xs" color="gray.600">
              Secure cross-chain infrastructure with proof-of-stake security
            </Text>
          </VStack>
        </HStack>
      </Box>

      {metadata?.estimatedTime && (
        <Alert status="info" size="sm">
          <AlertIcon as={FaClock} />
          <Text fontSize="sm">
            Estimated completion time: {metadata.estimatedTime}
          </Text>
        </Alert>
      )}
    </VStack>
  );
};
import * as React from "react";
import {
  Box,
  Text,
  Badge,
  Divider,
  Alert,
  AlertIcon,
  AlertTitle,
  AlertDescription,
} from "@chakra-ui/react";

interface TokenInfoProps {
  metadata?: any;
  isCommand: boolean;
  isSuccess: boolean;
  content: any;
}

type TokenInfo = {
  address?: string;
  symbol?: string;
  name?: string;
  verified?: boolean;
  source?: string;
  warning?: string;
};

export const TokenInfo: React.FC<TokenInfoProps> = ({
  metadata,
  isCommand,
  isSuccess,
  content,
}) => {
  if (!metadata || isCommand || !isSuccess) return null;

  // Only show token info for swap transactions
  if (!content.includes("swap") && !content.includes("Swap")) return null;

  // Extract token information from metadata
  const tokenInInfo: TokenInfo = metadata
    ? {
        address: metadata.token_in_address,
        symbol: metadata.token_in_symbol,
        name: metadata.token_in_name,
        verified: metadata.token_in_verified,
        source: metadata.token_in_source,
      }
    : {};

  const tokenOutInfo: TokenInfo = metadata
    ? {
        address: metadata.token_out_address,
        symbol: metadata.token_out_symbol,
        name: metadata.token_out_name,
        verified: metadata.token_out_verified,
        source: metadata.token_out_source,
      }
    : {};

  return (
    <Box mt={3} fontSize="sm">
      <Divider mb={2} />
      <Text fontWeight="bold" mb={1}>
        Token Information:
      </Text>

      {tokenInInfo.symbol && (
        <Box mb={2}>
          <Text fontWeight="semibold">From: {tokenInInfo.symbol}</Text>
          {tokenInInfo.name && (
            <Text color="gray.600">{tokenInInfo.name}</Text>
          )}
          {tokenInInfo.address && (
            <Text fontSize="xs" color="gray.500" wordBreak="break-all">
              Address: {tokenInInfo.address}
            </Text>
          )}
          {tokenInInfo.verified && (
            <Badge colorScheme="green" fontSize="xs">
              Verified
            </Badge>
          )}
          {tokenInInfo.source && (
            <Text fontSize="xs" color="gray.500">
              Source: {tokenInInfo.source}
            </Text>
          )}
        </Box>
      )}

      {tokenOutInfo.symbol && (
        <Box>
          <Text fontWeight="semibold">To: {tokenOutInfo.symbol}</Text>
          {tokenOutInfo.name && (
            <Text color="gray.600">{tokenOutInfo.name}</Text>
          )}
          {tokenOutInfo.address && (
            <Text fontSize="xs" color="gray.500" wordBreak="break-all">
              Address: {tokenOutInfo.address}
            </Text>
          )}
          {tokenOutInfo.verified ? (
            <Badge colorScheme="green" fontSize="xs">
              Verified
            </Badge>
          ) : (
            <Badge colorScheme="yellow" fontSize="xs">
              Unverified
            </Badge>
          )}
          {tokenOutInfo.source && (
            <Text fontSize="xs" color="gray.500">
              Source: {tokenOutInfo.source}
            </Text>
          )}
        </Box>
      )}

      {(!tokenInInfo.verified || !tokenOutInfo.verified) && (
        <Alert status="warning" mt={2} size="sm" borderRadius="md">
          <AlertIcon />
          <Box>
            <AlertTitle fontSize="xs">Caution</AlertTitle>
            <AlertDescription fontSize="xs">
              One or more tokens in this transaction are unverified. Always
              double-check contract addresses before proceeding.
            </AlertDescription>
          </Box>
        </Alert>
      )}
    </Box>
  );
};

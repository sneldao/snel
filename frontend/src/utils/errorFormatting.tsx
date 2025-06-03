import * as React from "react";
import { Box, Text, UnorderedList, ListItem } from "@chakra-ui/react";

export const formatSwapResponse = (
  content: string
): { preview: string; success: boolean } => {
  try {
    if (content.includes("SwapArgs")) {
      const match = content.match(/amount_in=(\d+),\s*amount_out=(\d+)/);
      if (match) {
        const amountIn = parseFloat(match[1]) / 1e18;
        const amountOut = parseFloat(match[2]) / 1e18;
        return {
          preview: `I'll swap ${amountIn.toFixed(
            4
          )} ETH for approximately ${amountOut.toFixed(
            4
          )} UNI tokens.\n\nDoes this look good? Reply with 'yes' to confirm or 'no' to cancel.`,
          success: true,
        };
      }
    }
    return { preview: content, success: false };
  } catch (error) {
    return { preview: content, success: false };
  }
};

export const formatErrorMessage = (errorContent: any): React.ReactNode => {
  // If it's a standard error string
  if (typeof errorContent === "string") {
    if (errorContent.includes("Unable to find a valid swap route")) {
      return (
        <Box>
          <Text mb={2}>
            I couldn&apos;t find a valid swap route for this transaction. I
            tried:
          </Text>
          <UnorderedList pl={4} spacing={1}>
            <ListItem>0x Protocol</ListItem>
            <ListItem>Brian Protocol</ListItem>
          </UnorderedList>
          <Text mt={2}>This could be due to:</Text>
          <UnorderedList pl={4} spacing={1}>
            <ListItem>Insufficient liquidity for this pair</ListItem>
            <ListItem>Minimum amount requirements not met</ListItem>
            <ListItem>Temporary issues with the protocols</ListItem>
          </UnorderedList>
          <Text mt={2}>
            Please try a different token pair, adjust the amount, or try again
            later.
          </Text>
        </Box>
      );
    }

    // Handle other specific error cases
    if (errorContent.includes("Slippage tolerance exceeded")) {
      return (
        <Box>
          <Text mb={2}>The price moved too much during the transaction.</Text>
          <Text>You can try again with:</Text>
          <UnorderedList pl={4} spacing={1}>
            <ListItem>A smaller amount</ListItem>
            <ListItem>A higher slippage tolerance (default is 0.5%)</ListItem>
          </UnorderedList>
        </Box>
      );
    }
  }

  // If it's an object with detailed error information
  if (typeof errorContent === "object" && errorContent !== null) {
    if (errorContent.protocols_tried) {
      return (
        <Box>
          <Text mb={2}>
            I couldn&apos;t complete the swap. I tried these protocols:
          </Text>
          <UnorderedList pl={4} spacing={1}>
            {errorContent.protocols_tried.map(
              (protocol: string, idx: number) => (
                <ListItem key={idx}>{protocol}</ListItem>
              )
            )}
          </UnorderedList>
          {errorContent.reason && (
            <Text mt={2}>Reason: {errorContent.reason}</Text>
          )}
          {errorContent.suggestion && (
            <Text mt={2}>Suggestion: {errorContent.suggestion}</Text>
          )}
        </Box>
      );
    }

    // Fall back to displaying the error message
    if (errorContent.message) {
      return <Text>{errorContent.message}</Text>;
    }
  }

  // Default case: return the original error content
  return <Text>{String(errorContent)}</Text>;
};

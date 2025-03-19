"use client";

import React from "react";
import { Box, Container } from "@chakra-ui/react";
import WalletBridge from "../../components/WalletBridge";

// This page is specifically for handling wallet connections from external sources
export default function WalletBridgePage() {
  return (
    <Container maxW="container.lg" py={8}>
      <Box p={4} borderRadius="lg">
        <WalletBridge />
      </Box>
    </Container>
  );
}

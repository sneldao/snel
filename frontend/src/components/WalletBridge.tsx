"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useAccount, useConnect, useSignMessage } from "wagmi";
import {
  Box,
  Button,
  Card,
  CardBody,
  CardHeader,
  Flex,
  Heading,
  Spinner,
  Text,
  VStack,
  useToast,
} from "@chakra-ui/react";

export default function WalletBridge() {
  const [isLoading, setIsLoading] = useState(true);
  const [connectionError, setConnectionError] = useState<string | null>(null);
  const [connectionStatus, setConnectionStatus] =
    useState<string>("initializing");
  const [connectionData, setConnectionData] = useState<any>(null);

  const searchParams = useSearchParams();
  const router = useRouter();
  const toast = useToast();

  // Extract params from URL
  const uid = searchParams.get("uid");
  const action = searchParams.get("action");
  const source = searchParams.get("source");
  const callback = searchParams.get("callback");
  const botName = searchParams.get("botName");

  // Wagmi hooks
  const { address, isConnected } = useAccount();
  const { connect, connectors } = useConnect();
  const { signMessageAsync } = useSignMessage();

  // Check if we have all required parameters
  const hasRequiredParams =
    uid && (action === "connect" || action === "transaction") && callback;

  // Function to fetch connection status
  const fetchConnectionStatus = async () => {
    if (!source || !uid) return null;

    try {
      const apiUrl = source.startsWith("/")
        ? `${window.location.origin}${source}`
        : source;

      const response = await fetch(apiUrl);
      if (!response.ok) throw new Error("Failed to fetch connection status");

      const data = await response.json();
      return data;
    } catch (error) {
      console.error("Error fetching connection status:", error);
      return null;
    }
  };

  // Function to complete the connection
  const completeConnection = async () => {
    if (!address || !uid || !callback) {
      setConnectionError("Missing required information to complete connection");
      return;
    }

    try {
      setConnectionStatus("signing");

      // Create a message to sign
      const message = `Connect wallet to ${
        botName || "Pointless"
      } Bot\nConnection ID: ${uid}\nAddress: ${address}\nTime: ${new Date().toISOString()}`;

      // Sign the message
      const signature = await signMessageAsync({ message });

      // Send the signed message to the callback
      const callbackUrl = callback.startsWith("/")
        ? `${window.location.origin}${callback}`
        : callback;

      const response = await fetch(callbackUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          connection_id: uid,
          uid: uid,
          wallet_address: address,
          address: address,
          signature: signature,
          message: message,
        }),
      });

      const result = await response.json();

      if (result.success) {
        setConnectionStatus("success");
        toast({
          title: "Wallet Connected",
          description: "Your wallet has been successfully connected.",
          status: "success",
          duration: 5000,
          isClosable: true,
        });
      } else {
        setConnectionStatus("error");
        setConnectionError(result.error || "Unknown error occurred");
        toast({
          title: "Connection Failed",
          description: result.error || "Failed to connect wallet.",
          status: "error",
          duration: 5000,
          isClosable: true,
        });
      }
    } catch (error: any) {
      setConnectionStatus("error");
      setConnectionError(error.message || "Failed to complete connection");
      toast({
        title: "Connection Error",
        description:
          error.message || "An error occurred during wallet connection.",
        status: "error",
        duration: 5000,
        isClosable: true,
      });
    }
  };

  // Return to the bot
  const returnToBot = () => {
    if (botName) {
      window.location.href = `https://t.me/${botName}`;
    }
  };

  // Handle initial setup
  useEffect(() => {
    const setup = async () => {
      if (!hasRequiredParams) {
        setConnectionError("Missing required parameters");
        setIsLoading(false);
        return;
      }

      // Check connection status
      const status = await fetchConnectionStatus();
      setConnectionData(status);

      if (status && status.is_completed) {
        setConnectionStatus("success");
      } else if (status && !status.success) {
        setConnectionError(status.error || "Connection not found or expired");
        setConnectionStatus("error");
      } else {
        setConnectionStatus("ready");
      }

      setIsLoading(false);
    };

    setup();
  }, [hasRequiredParams, uid, source]);

  // If user is already connected, offer to complete the connection
  useEffect(() => {
    if (isConnected && connectionStatus === "ready" && address) {
      // Automatically proceed to signing if wallet is already connected
      setConnectionStatus("connected");
    }
  }, [isConnected, connectionStatus, address]);

  if (isLoading) {
    return (
      <Box
        maxW="md"
        mx="auto"
        mt={10}
        p={6}
        borderWidth={1}
        borderRadius="lg"
        boxShadow="lg"
      >
        <VStack spacing={4}>
          <Heading size="md">Initializing Wallet Connection</Heading>
          <Spinner size="xl" />
          <Text>Loading connection details...</Text>
        </VStack>
      </Box>
    );
  }

  if (connectionError) {
    return (
      <Box
        maxW="md"
        mx="auto"
        mt={10}
        p={6}
        borderWidth={1}
        borderRadius="lg"
        boxShadow="lg"
        bg="red.50"
      >
        <VStack spacing={4}>
          <Heading size="md" color="red.500">
            Connection Error
          </Heading>
          <Text>{connectionError}</Text>
          <Button colorScheme="blue" onClick={returnToBot}>
            Return to Bot
          </Button>
        </VStack>
      </Box>
    );
  }

  if (connectionStatus === "success") {
    return (
      <Box
        maxW="md"
        mx="auto"
        mt={10}
        p={6}
        borderWidth={1}
        borderRadius="lg"
        boxShadow="lg"
        bg="green.50"
      >
        <VStack spacing={4}>
          <Heading size="md" color="green.500">
            Wallet Connected Successfully
          </Heading>
          <Text>Your wallet has been connected to the bot.</Text>
          <Text fontWeight="bold">Address: {address}</Text>
          <Button colorScheme="blue" onClick={returnToBot}>
            Return to Bot
          </Button>
        </VStack>
      </Box>
    );
  }

  if (connectionStatus === "signing") {
    return (
      <Box
        maxW="md"
        mx="auto"
        mt={10}
        p={6}
        borderWidth={1}
        borderRadius="lg"
        boxShadow="lg"
      >
        <VStack spacing={4}>
          <Heading size="md">Completing Connection</Heading>
          <Spinner size="xl" />
          <Text>Please confirm the signature request in your wallet...</Text>
        </VStack>
      </Box>
    );
  }

  if (connectionStatus === "connected") {
    return (
      <Box
        maxW="md"
        mx="auto"
        mt={10}
        p={6}
        borderWidth={1}
        borderRadius="lg"
        boxShadow="lg"
      >
        <VStack spacing={4}>
          <Heading size="md">Wallet Connected</Heading>
          <Text>Your wallet is connected with address:</Text>
          <Text fontWeight="bold" fontSize="sm" wordBreak="break-all">
            {address}
          </Text>
          <Button colorScheme="green" onClick={completeConnection}>
            Complete Connection
          </Button>
          <Button variant="outline" onClick={returnToBot}>
            Cancel
          </Button>
        </VStack>
      </Box>
    );
  }

  // Default view - ready to connect
  return (
    <Box
      maxW="md"
      mx="auto"
      mt={10}
      p={6}
      borderWidth={1}
      borderRadius="lg"
      boxShadow="lg"
    >
      <VStack spacing={6}>
        <Heading size="md">
          Connect Wallet to {botName || "Pointless"} Bot
        </Heading>
        <Text>Connect your Ethereum wallet to use with the bot.</Text>

        {connectors.map((connector) => (
          <Button
            key={connector.id}
            colorScheme="blue"
            width="full"
            isDisabled={!connector.ready}
            onClick={() => connect({ connector })}
          >
            Connect with {connector.name}
          </Button>
        ))}

        <Button variant="outline" onClick={returnToBot}>
          Cancel
        </Button>
      </VStack>
    </Box>
  );
}

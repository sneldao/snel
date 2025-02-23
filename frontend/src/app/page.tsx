"use client";

import * as React from "react";
import {
  Box,
  Container,
  VStack,
  Heading,
  Text,
  useToast,
  Alert,
  AlertIcon,
  AlertTitle,
  AlertDescription,
} from "@chakra-ui/react";
import { CommandInput } from "../components/CommandInput";
import { CommandResponse } from "../components/CommandResponse";

type Response = {
  content: string;
  timestamp: string;
  isCommand: boolean;
  needsConfirmation?: boolean;
  pendingCommand?: string;
};

export default function Home() {
  const [responses, setResponses] = React.useState<Response[]>([]);
  const [isLoading, setIsLoading] = React.useState(false);
  const toast = useToast();
  const responsesEndRef = React.useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    responsesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  React.useEffect(() => {
    scrollToBottom();
  }, [responses]);

  const processCommand = async (command: string) => {
    setIsLoading(true);
    try {
      const response = await fetch(
        "http://localhost:8000/api/process-command",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            content: command,
            creator_name: "@user",
            creator_id: 1,
          }),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Failed to process command");
      }

      if (!data.content) {
        throw new Error("No response from the agent");
      }

      const isQuestion =
        command.toLowerCase().startsWith("what") ||
        command.toLowerCase().startsWith("how");
      const needsConfirmation = !isQuestion && data.content !== "None";

      setResponses((prev) => [
        {
          content: data.content,
          timestamp: new Date().toLocaleTimeString(),
          isCommand: !isQuestion,
          needsConfirmation,
          pendingCommand: needsConfirmation ? command : undefined,
        },
        ...prev,
      ]);
    } catch (error) {
      console.error("Error:", error);

      setResponses((prev) => [
        {
          content:
            error instanceof Error
              ? `Sorry, I encountered an error: ${error.message}. Please make sure the backend server is running at http://localhost:8000`
              : "An unknown error occurred. Please try again.",
          timestamp: new Date().toLocaleTimeString(),
          isCommand: false,
        },
        ...prev,
      ]);

      toast({
        title: "Error",
        description:
          error instanceof Error
            ? error.message
            : "Failed to process command. Please try again.",
        status: "error",
        duration: 5000,
        isClosable: true,
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmit = async (command: string) => {
    await processCommand(command);
  };

  const handleConfirm = async (index: number) => {
    const response = responses[index];
    if (!response.pendingCommand) return;

    // Remove the confirmation UI
    setResponses((prev) => {
      const updated = [...prev];
      updated[index] = {
        ...updated[index],
        needsConfirmation: false,
        content: "Processing transaction...",
      };
      return updated;
    });

    // Process the actual command
    await processCommand(response.pendingCommand);
  };

  return (
    <Box minH="100vh" bg="gray.50">
      <Container maxW="container.md" py={8}>
        <VStack spacing={8}>
          <Box textAlign="center">
            <Heading size="xl" mb={2}>
              Pointless
            </Heading>
            <Text color="gray.600" fontSize="lg">
              Your friendly crypto command interpreter
            </Text>
            <Text color="gray.500" fontSize="sm" mt={2}>
              Ask me to swap tokens, send crypto, or answer questions about
              crypto!
            </Text>
          </Box>

          <CommandInput onSubmit={handleSubmit} isLoading={isLoading} />

          {responses.length === 0 ? (
            <Alert status="info" borderRadius="md">
              <AlertIcon />
              <Box>
                <AlertTitle>Welcome to Pointless!</AlertTitle>
                <AlertDescription>
                  Try asking me to swap some tokens or check crypto prices.
                  Click the help icon above for example commands.
                </AlertDescription>
              </Box>
            </Alert>
          ) : (
            <VStack spacing={4} w="100%" align="stretch">
              {responses.map((response, index) => (
                <CommandResponse
                  key={`response-${index}`}
                  content={response.content}
                  timestamp={response.timestamp}
                  isCommand={response.isCommand}
                  onConfirm={
                    response.needsConfirmation
                      ? () => handleConfirm(index)
                      : undefined
                  }
                />
              ))}
              <div ref={responsesEndRef} />
            </VStack>
          )}
        </VStack>
      </Container>
    </Box>
  );
}

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
  pendingCommand?: string;
  awaitingConfirmation?: boolean;
  status?: "pending" | "processing" | "success" | "error";
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
      const isConfirmation = /^(yes|confirm|no|cancel)$/i.test(command.trim());

      // Handle confirmation responses without making API calls
      if (isConfirmation) {
        const confirmationIndex = responses.findIndex(
          (r) => r.awaitingConfirmation
        );
        if (confirmationIndex === -1) {
          setResponses((prev) => [
            ...prev,
            {
              content:
                "I don't see any pending commands to confirm. Try sending a new command.",
              timestamp: new Date().toLocaleTimeString(),
              isCommand: false,
              status: "error",
            },
          ]);
          return;
        }

        const shouldExecute = /^(yes|confirm)$/i.test(command.trim());
        if (shouldExecute) {
          // Add user's confirmation message
          setResponses((prev) => [
            ...prev,
            {
              content: command,
              timestamp: new Date().toLocaleTimeString(),
              isCommand: true,
              status: "success",
            },
          ]);

          // Add processing message
          const processingTimestamp = new Date().toLocaleTimeString();
          setResponses((prev) => [
            ...prev,
            {
              content: "Processing your transaction...",
              timestamp: processingTimestamp,
              isCommand: false,
              status: "processing",
            },
          ]);

          // Add success message after a short delay and remove the processing message
          setTimeout(() => {
            setResponses((prev) =>
              prev
                .filter((r) => r.timestamp !== processingTimestamp)
                .concat({
                  content: "Transaction completed successfully! 🎉",
                  timestamp: new Date().toLocaleTimeString(),
                  isCommand: false,
                  status: "success",
                })
            );
          }, 2000);
        } else {
          // Add user's cancellation message
          setResponses((prev) => [
            ...prev,
            {
              content: command,
              timestamp: new Date().toLocaleTimeString(),
              isCommand: true,
              status: "error",
            },
          ]);

          // Add cancellation confirmation
          setResponses((prev) => [
            ...prev,
            {
              content: "Transaction cancelled.",
              timestamp: new Date().toLocaleTimeString(),
              isCommand: false,
              status: "error",
            },
          ]);
        }
        return;
      }

      // For non-confirmation commands, make the API call
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

      // Handle None response or missing content
      if (!data.content || data.content === "None") {
        // Add user's command with error status
        setResponses((prev) => [
          ...prev,
          {
            content: command,
            timestamp: new Date().toLocaleTimeString(),
            isCommand: true,
            status: "error",
          },
        ]);

        setResponses((prev) => [
          ...prev,
          {
            content:
              "Sorry, I encountered an error processing your command. Please try again.",
            timestamp: new Date().toLocaleTimeString(),
            isCommand: false,
            status: "error",
          },
        ]);
        return;
      }

      const isQuestion =
        command.toLowerCase().startsWith("what") ||
        command.toLowerCase().startsWith("how");

      // Add user's command with success status
      setResponses((prev) => [
        ...prev,
        {
          content: command,
          timestamp: new Date().toLocaleTimeString(),
          isCommand: true,
          status: "success",
        },
      ]);

      // Add agent's response
      setResponses((prev) => [
        ...prev,
        {
          content: data.content,
          timestamp: new Date().toLocaleTimeString(),
          isCommand: !isQuestion,
          pendingCommand: !isQuestion ? command : undefined,
          awaitingConfirmation: !isQuestion && data.content !== "None",
          status: !isQuestion ? "pending" : "success",
        },
      ]);
    } catch (error) {
      console.error("Error:", error);

      // Add user's command with error status
      setResponses((prev) => [
        ...prev,
        {
          content: command,
          timestamp: new Date().toLocaleTimeString(),
          isCommand: true,
          status: "error",
        },
      ]);

      // Add error message
      setResponses((prev) => [
        ...prev,
        {
          content:
            error instanceof Error
              ? `Sorry, I encountered an error: ${error.message}. Please make sure the backend server is running at http://localhost:8000`
              : "An unknown error occurred. Please try again.",
          timestamp: new Date().toLocaleTimeString(),
          isCommand: false,
          status: "error",
        },
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
            <VStack spacing={4} w="100%" align="stretch" mb={8}>
              {responses.map((response, index) => (
                <CommandResponse
                  key={`response-${index}`}
                  content={response.content}
                  timestamp={response.timestamp}
                  isCommand={response.isCommand}
                  status={response.status}
                  awaitingConfirmation={response.awaitingConfirmation}
                />
              ))}
              <div ref={responsesEndRef} />
            </VStack>
          )}

          <CommandInput onSubmit={handleSubmit} isLoading={isLoading} />
        </VStack>
      </Container>
    </Box>
  );
}

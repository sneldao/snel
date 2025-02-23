import React, { useState } from "react";
import {
  ChakraProvider,
  Box,
  VStack,
  Heading,
  Text,
  Input,
  Button,
  useToast,
  Container,
  Card,
  CardBody,
  Badge,
} from "@chakra-ui/react";
import axios from "axios";

function App() {
  const [command, setCommand] = useState("");
  const [result, setResult] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const toast = useToast();

  const handleSubmit = async () => {
    if (!command.trim()) {
      toast({
        title: "Error",
        description: "Please enter a command",
        status: "error",
        duration: 3000,
        isClosable: true,
      });
      return;
    }

    setIsLoading(true);
    try {
      const response = await axios.post(
        "http://localhost:8000/api/process-command",
        {
          command: command,
        }
      );
      setResult(response.data);
    } catch (error) {
      toast({
        title: "Error",
        description:
          error.response?.data?.detail || "Failed to process command",
        status: "error",
        duration: 5000,
        isClosable: true,
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === "Enter") {
      handleSubmit();
    }
  };

  return (
    <ChakraProvider>
      <Box minH="100vh" bg="gray.50" py={10}>
        <Container maxW="container.md">
          <VStack spacing={8}>
            <Heading>Dowse Command Processor</Heading>
            <Text color="gray.600" textAlign="center">
              Enter a command like "swap $300 for $UNI and then send half of it
              to @vitalikbuterin"
            </Text>

            <Card w="100%" variant="outline">
              <CardBody>
                <VStack spacing={4}>
                  <Input
                    placeholder="Enter your command..."
                    value={command}
                    onChange={(e) => setCommand(e.target.value)}
                    onKeyPress={handleKeyPress}
                    size="lg"
                  />
                  <Button
                    colorScheme="blue"
                    onClick={handleSubmit}
                    isLoading={isLoading}
                    w="full"
                  >
                    Process Command
                  </Button>
                </VStack>
              </CardBody>
            </Card>

            {result && (
              <Card w="100%" variant="outline">
                <CardBody>
                  <VStack align="start" spacing={4}>
                    <Box>
                      <Text fontWeight="bold" mb={2}>
                        Classification:
                      </Text>
                      <Badge
                        colorScheme={
                          result.classification === "commands"
                            ? "green"
                            : "blue"
                        }
                      >
                        {result.classification}
                      </Badge>
                    </Box>
                    <Box>
                      <Text fontWeight="bold" mb={2}>
                        Result:
                      </Text>
                      <Text whiteSpace="pre-wrap">{result.result}</Text>
                    </Box>
                  </VStack>
                </CardBody>
              </Card>
            )}
          </VStack>
        </Container>
      </Box>
    </ChakraProvider>
  );
}

export default App;

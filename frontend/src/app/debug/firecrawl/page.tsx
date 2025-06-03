"use client";

import React, { useState } from "react";
import {
  Box,
  Container,
  VStack,
  Heading,
  Text,
  Input,
  Button,
  FormControl,
  FormLabel,
  Stack,
  Code,
  useToast,
  Spinner,
  Divider,
  Badge,
  HStack,
  Accordion,
  AccordionItem,
  AccordionButton,
  AccordionPanel,
  AccordionIcon,
} from "@chakra-ui/react";

export default function FirecrawlDebugPage() {
  const [protocol, setProtocol] = useState("Uniswap");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [directApiResult, setDirectApiResult] = useState<any>(null);
  const [apiErrorInfo, setApiErrorInfo] = useState<any>(null);
  const toast = useToast();

  const testFirecrawl = async () => {
    if (!protocol.trim()) {
      toast({
        title: "Error",
        description: "Please enter a protocol name",
        status: "error",
        duration: 3000,
        isClosable: true,
      });
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await fetch("/debug/firecrawl", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          protocol,
          debug: true,
        }),
      });

      // First try to get the response as text
      const responseText = await response.text();
      let data;
      
      // Try to parse as JSON
      try {
        data = JSON.parse(responseText);
      } catch (jsonError) {
        // If we can't parse as JSON, show the raw response
        throw new Error(`Failed to parse response as JSON. Raw response: ${responseText.substring(0, 500)}...`);
      }

      if (!response.ok) {
        throw new Error(data.detail || `Error ${response.status}: ${JSON.stringify(data)}`);
      }

      setResult(data.result);
      
      // Also save the direct API result and error info if available
      if (data.direct_api_result) {
        setDirectApiResult(data.direct_api_result);
      }
      
      if (data.error_info) {
        setApiErrorInfo(data.error_info);
        toast({
          title: "API Warning",
          description: `Direct API call had issues: ${data.error_info.error}`,
          status: "warning",
          duration: 5000,
          isClosable: true,
        });
      } else {
        toast({
          title: "Success",
          description: `Successfully retrieved data for ${protocol}`,
          status: "success",
          duration: 3000,
          isClosable: true,
        });
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
      toast({
        title: "Error",
        description: err instanceof Error ? err.message : "Failed to test Firecrawl",
        status: "error",
        duration: 5000,
        isClosable: true,
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <Container maxW="container.xl" py={8}>
      <VStack spacing={8} align="stretch">
        <Heading as="h1" size="xl">
          Firecrawl API Debug Tool
        </Heading>
        
        <Text>
        Use this tool to test the Firecrawl API integration directly. Enter a protocol name 
        to see the raw data returned from the API and how it&apos;s processed by our system.
      </Text>

        <Box p={6} borderWidth={1} borderRadius="lg" bg="white">
          <VStack spacing={4} align="stretch">
            <FormControl>
              <FormLabel>Protocol Name</FormLabel>
              <Stack direction={["column", "row"]}>
                <Input
                  value={protocol}
                  onChange={(e) => setProtocol(e.target.value)}
                  placeholder="e.g., Uniswap, Aave, Compound"
                  disabled={loading}
                  flex={1}
                />
                <Button
                  colorScheme="blue"
                  onClick={testFirecrawl}
                  isLoading={loading}
                  loadingText="Testing..."
                  width={["100%", "auto"]}
                >
                  Test Firecrawl
                </Button>
              </Stack>
            </FormControl>
          </VStack>
        </Box>

        {loading && (
          <Box textAlign="center" py={10}>
            <Spinner size="xl" />
            <Text mt={4}>Testing Firecrawl API...</Text>
          </Box>
        )}

        {error && (
          <Box p={6} borderWidth={1} borderRadius="lg" bg="red.50">
            <Heading as="h3" size="md" color="red.500" mb={2}>
              Error
            </Heading>
            <Text color="red.700" whiteSpace="pre-wrap">{error}</Text>
          </Box>
        )}
        
        {apiErrorInfo && (
          <Box p={6} borderWidth={1} borderRadius="lg" bg="orange.50" mt={4}>
            <Heading as="h3" size="md" color="orange.500" mb={2}>
              API Diagnostics
            </Heading>
            <VStack align="stretch" spacing={2}>
              <Text fontWeight="bold">Error Type: {apiErrorInfo.error}</Text>
              {apiErrorInfo.details && <Text>Details: {apiErrorInfo.details}</Text>}
              {apiErrorInfo.response_text && (
                <Box mt={2}>
                  <Text fontWeight="bold">Response Preview:</Text>
                  <Box 
                    p={3} 
                    bg="gray.100" 
                    borderRadius="md" 
                    mt={1} 
                    fontSize="sm"
                    overflowX="auto"
                    maxH="200px"
                    overflowY="auto"
                  >
                    <pre>{apiErrorInfo.response_text}</pre>
                  </Box>
                </Box>
              )}
            </VStack>
          </Box>
        )}

        {result && (
          <VStack spacing={6} align="stretch">
            <Heading as="h2" size="lg">
              Firecrawl Results for {protocol}
            </Heading>

            <Box p={6} borderWidth={1} borderRadius="lg" bg="white">
              <VStack align="stretch" spacing={4}>
                <HStack>
                  <Badge colorScheme={result.scraping_success ? "green" : "red"} fontSize="md" p={2}>
                    {result.scraping_success ? "Success" : "Failed"}
                  </Badge>
                  <Text fontWeight="bold">Protocol: {result.protocol_name}</Text>
                </HStack>

                <Divider />

                <HStack>
                  <Text fontWeight="bold" minW="150px">TVL:</Text>
                  <Text>{result.tvl_analyzed}</Text>
                </HStack>

                <HStack>
                  <Text fontWeight="bold" minW="150px">Security Audits:</Text>
                  <Text>{result.security_audits}</Text>
                </HStack>

                <HStack>
                  <Text fontWeight="bold" minW="150px">Live Rates:</Text>
                  <Text>{result.live_rates}</Text>
                </HStack>

                {result.rates && result.rates.length > 0 && (
                  <Box>
                    <Text fontWeight="bold" mb={2}>Rates Found:</Text>
                    <Stack direction="row" flexWrap="wrap">
                      {result.rates.map((rate: string, index: number) => (
                        <Badge key={index} colorScheme="green" mr={2} mb={2}>
                          {rate}
                        </Badge>
                      ))}
                    </Stack>
                  </Box>
                )}

                {result.features && result.features.length > 0 && (
                  <Box>
                    <Text fontWeight="bold" mb={2}>Features:</Text>
                    <VStack align="stretch">
                      {result.features.map((feature: string, index: number) => (
                        <Text key={index} fontSize="sm">• {feature}</Text>
                      ))}
                    </VStack>
                  </Box>
                )}

                <Divider />

                <Accordion allowToggle>
                  <AccordionItem>
                    <h2>
                      <AccordionButton>
                        <Box flex="1" textAlign="left" fontWeight="bold">
                          Content Preview
                        </Box>
                        <AccordionIcon />
                      </AccordionButton>
                    </h2>
                    <AccordionPanel pb={4}>
                      <Text whiteSpace="pre-wrap">{result.content_preview}</Text>
                    </AccordionPanel>
                  </AccordionItem>

                  <AccordionItem>
                    <h2>
                      <AccordionButton>
                        <Box flex="1" textAlign="left" fontWeight="bold">
                          Full Content
                        </Box>
                        <AccordionIcon />
                      </AccordionButton>
                    </h2>
                    <AccordionPanel pb={4} maxH="300px" overflowY="auto">
                      <Text whiteSpace="pre-wrap">{result.full_content}</Text>
                    </AccordionPanel>
                  </AccordionItem>

                  <AccordionItem>
                    <h2>
                      <AccordionButton>
                        <Box flex="1" textAlign="left" fontWeight="bold">
                          Raw JSON Response
                        </Box>
                        <AccordionIcon />
                      </AccordionButton>
                    </h2>
                    <AccordionPanel pb={4} maxH="500px" overflowY="auto">
                      <Code p={4} borderRadius="md" display="block" whiteSpace="pre-wrap">
                        {JSON.stringify(result, null, 2)}
                      </Code>
                    </AccordionPanel>
                  </AccordionItem>
                  
                  {directApiResult && (
                    <AccordionItem>
                      <h2>
                        <AccordionButton>
                          <Box flex="1" textAlign="left" fontWeight="bold">
                            Direct API Response
                          </Box>
                          <AccordionIcon />
                        </AccordionButton>
                      </h2>
                      <AccordionPanel pb={4} maxH="500px" overflowY="auto">
                        <Code p={4} borderRadius="md" display="block" whiteSpace="pre-wrap">
                          {JSON.stringify(directApiResult, null, 2)}
                        </Code>
                      </AccordionPanel>
                    </AccordionItem>
                  )}
                </Accordion>
              </VStack>
            </Box>
          </VStack>
        )}
      </VStack>
    </Container>
  );
}
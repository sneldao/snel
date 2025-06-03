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
  Select,
  Textarea,
  Switch,
  FormHelperText,
  Tabs, 
  TabList, 
  TabPanels, 
  Tab, 
  TabPanel,
} from "@chakra-ui/react";

export default function RawApiDebugPage() {
  const [url, setUrl] = useState("https://api.firecrawl.dev/search");
  const [method, setMethod] = useState("GET");
  const [params, setParams] = useState("q=Uniswap+defi+protocol");
  const [headers, setHeaders] = useState("Content-Type: application/json");
  const [body, setBody] = useState("{}");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [addAuthHeader, setAddAuthHeader] = useState(true);
  const toast = useToast();

  const parseParams = (paramsStr: string) => {
    const paramsObj: Record<string, string> = {};
    paramsStr.split('&').forEach(pair => {
      const [key, value] = pair.split('=');
      if (key && value) {
        paramsObj[key.trim()] = value.trim();
      }
    });
    return paramsObj;
  };

  const parseHeaders = (headersStr: string) => {
    const headersObj: Record<string, string> = {};
    headersStr.split('\n').forEach(line => {
      const [key, value] = line.split(':');
      if (key && value) {
        headersObj[key.trim()] = value.trim();
      }
    });
    return headersObj;
  };

  const parseBody = (bodyStr: string) => {
    try {
      return JSON.parse(bodyStr);
    } catch (e) {
      return bodyStr;
    }
  };

  const sendApiRequest = async () => {
    if (!url.trim()) {
      toast({
        title: "Error",
        description: "Please enter a valid URL",
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
      const parsedParams = parseParams(params);
      const parsedHeaders = parseHeaders(headers);
      const parsedBody = method !== "GET" ? parseBody(body) : {};

      const response = await fetch("/debug/raw-firecrawl", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          url,
          method,
          headers: parsedHeaders,
          params: parsedParams,
          body: parsedBody,
          addAuthHeader,
        }),
      });

      // First try to get the response as text
      const responseText = await response.text();
      let data;
      
      // Try to parse as JSON
      try {
        data = JSON.parse(responseText);
      } catch (jsonError) {
        throw new Error(`Failed to parse response as JSON. Raw response: ${responseText.substring(0, 500)}...`);
      }

      if (!response.ok) {
        throw new Error(data.detail || `Error ${response.status}: ${JSON.stringify(data)}`);
      }

      setResult(data);
      
      toast({
        title: "Success",
        description: `API request completed with status ${data.status_code}`,
        status: "success",
        duration: 3000,
        isClosable: true,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
      toast({
        title: "Error",
        description: err instanceof Error ? err.message : "Failed to make API request",
        status: "error",
        duration: 5000,
        isClosable: true,
      });
    } finally {
      setLoading(false);
    }
  };

  const presetQueries = [
    { 
      name: "Search Uniswap", 
      url: "https://api.firecrawl.dev/search", 
      method: "GET", 
      params: "q=Uniswap+defi+protocol" 
    },
    { 
      name: "Search Aave", 
      url: "https://api.firecrawl.dev/search", 
      method: "GET", 
      params: "q=Aave+lending+protocol" 
    },
    {
      name: "Search DeFi Protocols",
      url: "https://api.firecrawl.dev/search",
      method: "GET",
      params: "q=top+defi+protocols+by+TVL"
    }
  ];

  const applyPreset = (preset: any) => {
    setUrl(preset.url);
    setMethod(preset.method);
    setParams(preset.params);
    setBody(preset.body || "{}");
  };

  return (
    <Container maxW="container.xl" py={8}>
      <VStack spacing={8} align="stretch">
        <Heading as="h1" size="xl">
          Raw API Debug Tool
        </Heading>
        
        <Text>
          Use this tool to make direct API requests to Firecrawl or other services, bypassing any application-specific logic.
        </Text>

        <Box p={6} borderWidth={1} borderRadius="lg" bg="white">
          <VStack spacing={6} align="stretch">
            <Heading as="h3" size="md">API Request</Heading>
            
            <HStack>
              <Text fontWeight="bold">Presets:</Text>
              {presetQueries.map((preset, index) => (
                <Button 
                  key={index} 
                  size="sm" 
                  colorScheme="blue" 
                  variant="outline"
                  onClick={() => applyPreset(preset)}
                >
                  {preset.name}
                </Button>
              ))}
            </HStack>
            
            <FormControl>
              <FormLabel>URL</FormLabel>
              <Input
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="https://api.example.com/endpoint"
                disabled={loading}
              />
            </FormControl>
            
            <HStack>
              <FormControl width="200px">
                <FormLabel>Method</FormLabel>
                <Select 
                  value={method} 
                  onChange={(e) => setMethod(e.target.value)}
                  disabled={loading}
                >
                  <option value="GET">GET</option>
                  <option value="POST">POST</option>
                </Select>
              </FormControl>
              
              <FormControl>
                <FormLabel>Add Auth Header</FormLabel>
                <Switch 
                  isChecked={addAuthHeader} 
                  onChange={(e) => setAddAuthHeader(e.target.checked)}
                  disabled={loading}
                />
                <FormHelperText>
                  Automatically add the Firecrawl API key as a Bearer token
                </FormHelperText>
              </FormControl>
            </HStack>
            
            <Tabs variant="enclosed">
              <TabList>
                <Tab>Query Parameters</Tab>
                <Tab>Headers</Tab>
                {method !== "GET" && <Tab>Body</Tab>}
              </TabList>
              
              <TabPanels>
                <TabPanel>
                  <FormControl>
                    <FormLabel>Query Parameters (key=value&key2=value2)</FormLabel>
                    <Textarea
                      value={params}
                      onChange={(e) => setParams(e.target.value)}
                      placeholder="param1=value1&param2=value2"
                      disabled={loading}
                      height="100px"
                    />
                  </FormControl>
                </TabPanel>
                
                <TabPanel>
                  <FormControl>
                    <FormLabel>Headers (one per line, Key: Value)</FormLabel>
                    <Textarea
                      value={headers}
                      onChange={(e) => setHeaders(e.target.value)}
                      placeholder="Content-Type: application/json"
                      disabled={loading}
                      height="100px"
                    />
                  </FormControl>
                </TabPanel>
                
                {method !== "GET" && (
                  <TabPanel>
                    <FormControl>
                      <FormLabel>Body (JSON)</FormLabel>
                      <Textarea
                        value={body}
                        onChange={(e) => setBody(e.target.value)}
                        placeholder="{}"
                        disabled={loading}
                        height="150px"
                        fontFamily="monospace"
                      />
                    </FormControl>
                  </TabPanel>
                )}
              </TabPanels>
            </Tabs>
            
            <Button
              colorScheme="blue"
              onClick={sendApiRequest}
              isLoading={loading}
              loadingText="Sending..."
              width="100%"
            >
              Send Request
            </Button>
          </VStack>
        </Box>

        {loading && (
          <Box textAlign="center" py={10}>
            <Spinner size="xl" />
            <Text mt={4}>Sending API request...</Text>
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

        {result && (
          <VStack spacing={6} align="stretch">
            <Heading as="h2" size="lg">
              API Response
            </Heading>

            <Box p={6} borderWidth={1} borderRadius="lg" bg="white">
              <VStack align="stretch" spacing={4}>
                <HStack>
                  <Badge 
                    colorScheme={result.status_code < 400 ? "green" : "red"} 
                    fontSize="md" 
                    p={2}
                  >
                    Status: {result.status_code}
                  </Badge>
                  <Badge 
                    colorScheme={result.is_json ? "blue" : "orange"} 
                    fontSize="md" 
                    p={2}
                  >
                    {result.is_json ? "JSON Response" : "Text Response"}
                  </Badge>
                </HStack>

                <Divider />

                <Accordion allowToggle defaultIndex={[0]}>
                  <AccordionItem>
                    <h2>
                      <AccordionButton>
                        <Box flex="1" textAlign="left" fontWeight="bold">
                          Response Headers
                        </Box>
                        <AccordionIcon />
                      </AccordionButton>
                    </h2>
                    <AccordionPanel pb={4}>
                      <Code p={4} borderRadius="md" display="block" whiteSpace="pre-wrap">
                        {JSON.stringify(result.headers, null, 2)}
                      </Code>
                    </AccordionPanel>
                  </AccordionItem>

                  <AccordionItem>
                    <h2>
                      <AccordionButton>
                        <Box flex="1" textAlign="left" fontWeight="bold">
                          {result.is_json ? "JSON Response" : "Text Response"}
                        </Box>
                        <AccordionIcon />
                      </AccordionButton>
                    </h2>
                    <AccordionPanel pb={4} maxH="500px" overflowY="auto">
                      <Code p={4} borderRadius="md" display="block" whiteSpace="pre-wrap">
                        {result.is_json 
                          ? JSON.stringify(result.json_response, null, 2)
                          : result.text_response
                        }
                      </Code>
                    </AccordionPanel>
                  </AccordionItem>

                  <AccordionItem>
                    <h2>
                      <AccordionButton>
                        <Box flex="1" textAlign="left" fontWeight="bold">
                          Full Response Object
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
                </Accordion>
              </VStack>
            </Box>
          </VStack>
        )}
      </VStack>
    </Container>
  );
}
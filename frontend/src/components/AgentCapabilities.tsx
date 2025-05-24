import * as React from "react";
import {
  Box,
  VStack,
  HStack,
  Text,
  Badge,
  Accordion,
  AccordionItem,
  AccordionButton,
  AccordionPanel,
  AccordionIcon,
  List,
  ListItem,
  ListIcon,
  useColorModeValue,
  Spinner,
  Alert,
  AlertIcon,
} from "@chakra-ui/react";
import { CheckCircleIcon, InfoIcon } from "@chakra-ui/icons";
import { useQuery } from "@tanstack/react-query";

interface AgentCapability {
  description: string;
  supported_chains: number;
  examples: string[];
}

interface AgentInfo {
  agent_name: string;
  version: string;
  capabilities: Record<string, AgentCapability>;
  supported_chains: Record<string, string>;
  protocols: string[];
  response_modes: string[];
  status: string;
}

const fetchAgentInfo = async (): Promise<AgentInfo> => {
  const response = await fetch("/api/v1/chat/agent-info");
  if (!response.ok) {
    throw new Error("Failed to fetch agent info");
  }
  return response.json();
};

export const AgentCapabilities: React.FC = () => {
  const bgColor = useColorModeValue("white", "gray.800");
  const borderColor = useColorModeValue("gray.200", "gray.600");

  const { data: agentInfo, isLoading, error } = useQuery({
    queryKey: ["agent-info"],
    queryFn: fetchAgentInfo,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  if (isLoading) {
    return (
      <Box p={4} textAlign="center">
        <Spinner size="lg" />
        <Text mt={2}>Loading agent capabilities...</Text>
      </Box>
    );
  }

  if (error) {
    return (
      <Alert status="error">
        <AlertIcon />
        Failed to load agent capabilities
      </Alert>
    );
  }

  if (!agentInfo) return null;

  return (
    <Box
      bg={bgColor}
      borderWidth="1px"
      borderColor={borderColor}
      borderRadius="lg"
      p={4}
      maxW="600px"
      mx="auto"
    >
      <VStack spacing={4} align="stretch">
        {/* Header */}
        <HStack justify="space-between" align="center">
          <VStack align="start" spacing={1}>
            <Text fontSize="xl" fontWeight="bold">
              {agentInfo.agent_name} Agent
            </Text>
            <HStack>
              <Badge colorScheme="blue" variant="subtle">
                v{agentInfo.version}
              </Badge>
              <Badge
                colorScheme={agentInfo.status === "operational" ? "green" : "red"}
                variant="subtle"
              >
                {agentInfo.status}
              </Badge>
            </HStack>
          </VStack>
          <InfoIcon color="blue.500" />
        </HStack>

        {/* Quick Stats */}
        <HStack spacing={4} justify="center">
          <VStack spacing={1}>
            <Text fontSize="2xl" fontWeight="bold" color="blue.500">
              {Object.keys(agentInfo.capabilities).length}
            </Text>
            <Text fontSize="sm" color="gray.600">
              Capabilities
            </Text>
          </VStack>
          <VStack spacing={1}>
            <Text fontSize="2xl" fontWeight="bold" color="green.500">
              {Object.keys(agentInfo.supported_chains).length}
            </Text>
            <Text fontSize="sm" color="gray.600">
              Chains
            </Text>
          </VStack>
          <VStack spacing={1}>
            <Text fontSize="2xl" fontWeight="bold" color="purple.500">
              {agentInfo.protocols.length}
            </Text>
            <Text fontSize="sm" color="gray.600">
              Protocols
            </Text>
          </VStack>
        </HStack>

        {/* Capabilities Accordion */}
        <Accordion allowToggle>
          <AccordionItem>
            <AccordionButton>
              <Box flex="1" textAlign="left">
                <Text fontWeight="semibold">Core Capabilities</Text>
              </Box>
              <AccordionIcon />
            </AccordionButton>
            <AccordionPanel pb={4}>
              <VStack spacing={3} align="stretch">
                {Object.entries(agentInfo.capabilities).map(([name, capability]) => (
                  <Box key={name} p={3} bg="gray.50" borderRadius="md">
                    <VStack align="start" spacing={2}>
                      <HStack justify="space-between" w="full">
                        <Text fontWeight="semibold" textTransform="capitalize">
                          {name.replace(/_/g, " ")}
                        </Text>
                        <Badge colorScheme="blue" size="sm">
                          {capability.supported_chains} chains
                        </Badge>
                      </HStack>
                      <Text fontSize="sm" color="gray.600">
                        {capability.description}
                      </Text>
                      <Box>
                        <Text fontSize="xs" fontWeight="semibold" mb={1}>
                          Examples:
                        </Text>
                        <List spacing={1}>
                          {capability.examples.map((example, idx) => (
                            <ListItem key={idx} fontSize="xs">
                              <ListIcon as={CheckCircleIcon} color="green.500" />
                              <Text as="span" fontFamily="mono" bg="gray.100" px={1} borderRadius="sm">
                                {example}
                              </Text>
                            </ListItem>
                          ))}
                        </List>
                      </Box>
                    </VStack>
                  </Box>
                ))}
              </VStack>
            </AccordionPanel>
          </AccordionItem>

          <AccordionItem>
            <AccordionButton>
              <Box flex="1" textAlign="left">
                <Text fontWeight="semibold">Supported Networks</Text>
              </Box>
              <AccordionIcon />
            </AccordionButton>
            <AccordionPanel pb={4}>
              <Box display="grid" gridTemplateColumns="repeat(auto-fit, minmax(150px, 1fr))" gap={2}>
                {Object.entries(agentInfo.supported_chains).map(([chainId, name]) => (
                  <Badge key={chainId} colorScheme="gray" variant="outline" p={2} textAlign="center">
                    {name} ({chainId})
                  </Badge>
                ))}
              </Box>
            </AccordionPanel>
          </AccordionItem>

          <AccordionItem>
            <AccordionButton>
              <Box flex="1" textAlign="left">
                <Text fontWeight="semibold">Integrated Protocols</Text>
              </Box>
              <AccordionIcon />
            </AccordionButton>
            <AccordionPanel pb={4}>
              <HStack spacing={2} flexWrap="wrap">
                {agentInfo.protocols.map((protocol) => (
                  <Badge key={protocol} colorScheme="purple" variant="solid">
                    {protocol}
                  </Badge>
                ))}
              </HStack>
            </AccordionPanel>
          </AccordionItem>
        </Accordion>

        {/* Footer */}
        <Text fontSize="xs" color="gray.500" textAlign="center">
          Agent capabilities are dynamically determined based on your current network and available protocols.
        </Text>
      </VStack>
    </Box>
  );
};

import React, { useState, useEffect } from 'react';
import {
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalCloseButton,
  VStack,
  HStack,
  Text,
  Badge,
  Button,
  Box,
  Spinner,
  useColorModeValue,
  Link,
  Divider,
} from '@chakra-ui/react';
import { FaLeaf, FaExternalLinkAlt, FaChartLine } from 'react-icons/fa';

interface YieldOpportunity {
  protocol: string;
  apy: string;
  tvl?: string;
  chain: string;
  url?: string;
  description?: string;
}

interface YieldFarmingDashboardProps {
  isOpen: boolean;
  onClose: () => void;
}

export const YieldFarmingDashboard: React.FC<YieldFarmingDashboardProps> = ({
  isOpen,
  onClose,
}) => {
  const [opportunities, setOpportunities] = useState<YieldOpportunity[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const bg = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.600');

  useEffect(() => {
    if (isOpen) {
      fetchYieldOpportunities();
    }
  }, [isOpen]);

  const fetchYieldOpportunities = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch('/api/v1/research/discover?query=highest yield farming opportunities DeFi&category=yield&max_results=10');
      const data = await response.json();
      
      if (data.protocols && data.protocols.length > 0) {
        const formattedOpportunities = data.protocols.map((protocol: any) => ({
          protocol: protocol.name || protocol.title || 'Unknown Protocol',
          apy: protocol.apy || protocol.yield || 'N/A',
          tvl: protocol.tvl,
          chain: protocol.chain || protocol.network || 'Multi-chain',
          url: protocol.url,
          description: protocol.description || protocol.summary,
        }));
        setOpportunities(formattedOpportunities);
      } else {
        setOpportunities([]);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load yield opportunities');
    } finally {
      setLoading(false);
    }
  };

  const getAPYColor = (apy: string) => {
    const numericAPY = parseFloat(apy.replace('%', ''));
    if (numericAPY >= 20) return 'green';
    if (numericAPY >= 10) return 'blue';
    if (numericAPY >= 5) return 'orange';
    return 'gray';
  };

  const handleSetupYield = (protocol: string, apy: string) => {
    onClose();
    // This would trigger the chat with a specific yield farming command
    const command = `setup yield farming on ${protocol} with ${apy} APY`;
    // You could emit this to the parent component or use a global state
    console.log('Setup yield farming:', command);
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="xl">
      <ModalOverlay />
      <ModalContent bg={bg}>
        <ModalHeader>
          <HStack>
            <FaLeaf />
            <Text>Yield Farming Opportunities</Text>
          </HStack>
        </ModalHeader>
        <ModalCloseButton />
        <ModalBody pb={6}>
          {loading ? (
            <Box textAlign="center" py={8}>
              <Spinner size="lg" />
              <Text mt={4} color="gray.500">Finding best yields...</Text>
            </Box>
          ) : error ? (
            <Box textAlign="center" py={8}>
              <Text color="red.500">{error}</Text>
              <Button mt={4} onClick={fetchYieldOpportunities}>Retry</Button>
            </Box>
          ) : opportunities.length === 0 ? (
            <Box textAlign="center" py={8}>
              <Text color="gray.500">No yield opportunities found</Text>
              <Text fontSize="sm" color="gray.400" mt={2}>
                Try "find yield opportunities on Base" in chat
              </Text>
            </Box>
          ) : (
            <VStack spacing={4} align="stretch">
              {opportunities.map((opportunity, index) => (
                <Box
                  key={index}
                  p={4}
                  border="1px solid"
                  borderColor={borderColor}
                  borderRadius="lg"
                  bg={bg}
                >
                  <HStack justify="space-between" mb={2}>
                    <VStack align="start" spacing={1}>
                      <HStack>
                        <Text fontWeight="bold">{opportunity.protocol}</Text>
                        {opportunity.url && (
                          <Link href={opportunity.url} isExternal>
                            <FaExternalLinkAlt size={12} />
                          </Link>
                        )}
                      </HStack>
                      <HStack spacing={2}>
                        <Badge colorScheme={getAPYColor(opportunity.apy)}>
                          {opportunity.apy} APY
                        </Badge>
                        <Text fontSize="sm" color="gray.500">
                          {opportunity.chain}
                        </Text>
                        {opportunity.tvl && (
                          <>
                            <Text fontSize="sm" color="gray.500">•</Text>
                            <Text fontSize="sm" color="gray.500">
                              {opportunity.tvl} TVL
                            </Text>
                          </>
                        )}
                      </HStack>
                    </VStack>
                    <Button
                      size="sm"
                      colorScheme="green"
                      leftIcon={<FaChartLine />}
                      onClick={() => handleSetupYield(opportunity.protocol, opportunity.apy)}
                    >
                      Setup
                    </Button>
                  </HStack>
                  
                  {opportunity.description && (
                    <Text fontSize="sm" color="gray.600" mt={2}>
                      {opportunity.description.slice(0, 150)}
                      {opportunity.description.length > 150 ? '...' : ''}
                    </Text>
                  )}
                </Box>
              ))}
              
              <Divider />
              
              <Box textAlign="center" py={2}>
                <Text fontSize="sm" color="gray.500">
                  💡 Try: "setup weekly 100 USDC for yield farming when APY &gt; 15%"
                </Text>
              </Box>
            </VStack>
          )}
        </ModalBody>
      </ModalContent>
    </Modal>
  );
};

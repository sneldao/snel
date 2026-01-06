import React, { useState, useEffect, useMemo } from 'react';
import {
  Box,
  VStack,
  HStack,
  Text,
  Select,
  Button,
  useColorModeValue,
  Divider,
  Icon,
  Tooltip
} from '@chakra-ui/react';
import { FaShieldAlt, FaGlobe, FaBalanceScale, FaInfoCircle } from 'react-icons/fa';
import { useWallet } from '../../hooks/useWallet';

/**
 * PrivacySettings - Component for managing privacy preferences
 * Supports chain-specific privacy settings with x402/GMP fallback
 */

const PrivacySettings = () => {
  const { chainId, chainName, address: walletAddress } = useWallet();
  
  // Privacy options based on chain capabilities
  const [privacyOptions, setPrivacyOptions] = useState([]);
  const [defaultPrivacy, setDefaultPrivacy] = useState('public');
  const [isLoading, setIsLoading] = useState(true);
  
  // Mock chain privacy capabilities (in production, fetch from backend)
  const chainCapabilities = useMemo(() => ({
    1: { // Ethereum
      x402: true,
      gmp: true,
      compliance: true
    },
    8453: { // Base
      x402: true,
      gmp: true,
      compliance: true
    },
    137: { // Polygon
      x402: true,
      gmp: true,
      compliance: true
    },
    534352: { // Scroll
      x402: false,
      gmp: true,
      compliance: false
    }
  }), []);
  
  // Generate privacy options based on current chain
  useEffect(() => {
    if (!chainId) return;
    
    const capabilities = chainCapabilities[chainId] || { x402: false, gmp: false, compliance: false };
    
    const options = [
      { value: 'public', label: 'Public Transactions', icon: FaGlobe, description: 'Standard transactions on public blockchain' }
    ];
    
    if (capabilities.x402) {
      options.push(
        { value: 'private', label: 'Private via x402', icon: FaShieldAlt, description: 'Fast privacy using x402 programmatic payments' },
        { value: 'compliance', label: 'Private with Compliance', icon: FaBalanceScale, description: 'Private transaction with regulatory records' }
      );
    } else if (capabilities.gmp) {
      options.push(
        { value: 'private', label: 'Private via GMP', icon: FaShieldAlt, description: 'Privacy using GMP bridge (slower)' }
      );
    }
    
    setPrivacyOptions(options);
    setIsLoading(false);
    
  }, [chainId]);
  
  const handleSetDefault = (level) => {
    setDefaultPrivacy(level);
    // In production, this would call backend API to save preference
    console.log(`Setting default privacy to: ${level}`);
  };
  
  const bgColor = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.700');
  const textColor = useColorModeValue('gray.800', 'white');
  const mutedColor = useColorModeValue('gray.600', 'gray.400');
  
  if (isLoading) {
    return (
      <Box p={4} borderWidth={1} borderRadius="lg" borderColor={borderColor} bg={bgColor}>
        <Text>Loading privacy settings...</Text>
      </Box>
    );
  }
  
  const currentOption = privacyOptions.find(opt => opt.value === defaultPrivacy);
  
  return (
    <Box
      p={4}
      borderWidth={1}
      borderRadius="lg"
      borderColor={borderColor}
      bg={bgColor}
      width="100%"
    >
      <VStack spacing={4} align="stretch">
        {/* Header */}
        <HStack justifyContent="space-between">
          <HStack>
            <Icon as={FaShieldAlt} color="yellow.500" />
            <Text fontWeight="semibold" fontSize="lg">Privacy Settings</Text>
          </HStack>
          {chainName && (
            <Text fontSize="sm" color={mutedColor}>{chainName}</Text>
          )}
        </HStack>
        
        <Divider />
        
        {/* Current Setting */}
        <Box>
          <Text fontSize="sm" color={mutedColor} mb={2}>Current Default</Text>
          {currentOption && (
            <HStack>
              <Icon as={currentOption.icon} color={currentOption.value === 'public' ? 'gray.500' : 'yellow.500'} />
              <Text fontWeight="medium">{currentOption.label}</Text>
              <Tooltip label={currentOption.description}>
                <Icon as={FaInfoCircle} color={mutedColor} ml={1} />
              </Tooltip>
            </HStack>
          )}
        </Box>
        
        {/* Privacy Options */}
        <Box>
          <Text fontSize="sm" color={mutedColor} mb={2}>Available Options</Text>
          <VStack spacing={2}>
            {privacyOptions.map((option) => (
              <HStack
                key={option.value}
                p={2}
                borderWidth={1}
                borderRadius="md"
                borderColor={option.value === defaultPrivacy ? 'yellow.500' : borderColor}
                bg={option.value === defaultPrivacy ? 'yellow.50' : 'transparent'}
                cursor="pointer"
                _hover={{ bg: option.value === defaultPrivacy ? 'yellow.100' : 'gray.50' }}
                onClick={() => handleSetDefault(option.value)}
              >
                <Icon as={option.icon} color={option.value === 'public' ? 'gray.500' : 'yellow.500'} />
                <Text ml={2} flex={1}>{option.label}</Text>
                {option.value === defaultPrivacy && (
                  <Text fontSize="xs" color="yellow.600" fontWeight="medium">DEFAULT</Text>
                )}
              </HStack>
            ))}
          </VStack>
        </Box>
        
        {/* Chain Capabilities */}
        <Box>
          <Text fontSize="sm" color={mutedColor} mb={2}>Chain Capabilities</Text>
          {chainId && chainCapabilities[chainId] && (
            <VStack spacing={1} align="start">
              <HStack>
                <Icon as={FaShieldAlt} color={chainCapabilities[chainId].x402 ? 'yellow.500' : 'gray.400'} />
                <Text fontSize="sm">x402 Privacy: {chainCapabilities[chainId].x402 ? '✅ Supported' : '❌ Not available'}</Text>
              </HStack>
              <HStack>
                <Icon as={FaGlobe} color={chainCapabilities[chainId].gmp ? 'green.500' : 'gray.400'} />
                <Text fontSize="sm">GMP Privacy: {chainCapabilities[chainId].gmp ? '✅ Supported' : '❌ Not available'}</Text>
              </HStack>
              <HStack>
                <Icon as={FaBalanceScale} color={chainCapabilities[chainId].compliance ? 'blue.500' : 'gray.400'} />
                <Text fontSize="sm">Compliance: {chainCapabilities[chainId].compliance ? '✅ Supported' : '❌ Not available'}</Text>
              </HStack>
            </VStack>
          )}
        </Box>
        
        {/* Quick Actions */}
        <Box>
          <Text fontSize="sm" color={mutedColor} mb={2}>Quick Actions</Text>
          <Button
            size="sm"
            colorScheme="yellow"
            leftIcon={<FaShieldAlt />}
            onClick={() => handleSetDefault('private')}
          >
            Make All Transactions Private
          </Button>
        </Box>
      </VStack>
    </Box>
  );
};

export default PrivacySettings;
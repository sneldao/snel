/**
 * PrivacyAddressInput - Reusable Zcash address input component
 * Extracted from ZcashAddressModal - used by GMPTransactionCard
 * Single source of truth for address validation and education
 */

import React, { useState } from 'react';
import {
  VStack,
  HStack,
  Input,
  Box,
  Text,
  FormControl,
  FormLabel,
  FormErrorMessage,
  Button,
  Link,
  Icon,
  useColorModeValue,
  Divider,
} from '@chakra-ui/react';
import { FaExternalLinkAlt, FaInfo, FaShieldAlt } from 'react-icons/fa';

interface PrivacyAddressInputProps {
  address: string;
  onAddressChange: (address: string) => void;
  onConfirm?: (address: string) => void;
  error?: string;
  isLoading?: boolean;
  showWalletLinks?: boolean;
  compact?: boolean;
}

const ZCASH_ADDRESS_REGEX = /^(t1|t3|u)[a-zA-Z0-9]{33,}$/;

export const validateZcashAddress = (address: string): { isValid: boolean; error?: string } => {
  if (!address.trim()) {
    return { isValid: false, error: 'Please enter a Zcash address' };
  }
  
  if (!ZCASH_ADDRESS_REGEX.test(address)) {
    return { isValid: false, error: 'Invalid Zcash address format. Should start with u, t1, or t3' };
  }
  
  return { isValid: true };
};

export const PrivacyAddressInput: React.FC<PrivacyAddressInputProps> = ({
  address,
  onAddressChange,
  onConfirm,
  error: externalError,
  isLoading = false,
  showWalletLinks = true,
  compact = false,
}) => {
  const [localError, setLocalError] = useState('');
  const error = externalError || localError;

  const bgColor = useColorModeValue('gray.50', 'gray.700');
  const textColor = useColorModeValue('gray.800', 'white');
  const mutedColor = useColorModeValue('gray.600', 'gray.400');
  const borderColor = useColorModeValue('gray.200', 'gray.600');
  const infoBg = useColorModeValue('yellow.50', 'yellow.900');
  const infoBorder = useColorModeValue('yellow.200', 'yellow.700');

  const isValidAddress = ZCASH_ADDRESS_REGEX.test(address);

  const handleConfirm = () => {
    const validation = validateZcashAddress(address);
    
    if (!validation.isValid) {
      setLocalError(validation.error || '');
      return;
    }

    setLocalError('');
    onConfirm?.(address);
  };

  const handleAddressChange = (newAddress: string) => {
    onAddressChange(newAddress);
    setLocalError('');
  };

  return (
    <VStack spacing={compact ? 3 : 4} align="stretch">
      {/* Info Box */}
      {!compact && (
        <Box 
          p={3} 
          bg={infoBg}
          borderRadius="md" 
          borderWidth="1px" 
          borderColor={infoBorder}
          borderLeft="3px solid"
          borderLeftColor="yellow.500"
        >
          <HStack spacing={2} mb={1} align="start">
            <Icon as={FaInfo} color="yellow.600" mt={0.5} flexShrink={0} />
            <Text fontWeight="semibold" fontSize="sm" color={textColor}>
              Unified addresses (u...) provide maximum privacy
            </Text>
          </HStack>
          <Text fontSize="xs" color={mutedColor} lineHeight="1.5" ml={6}>
            Your funds will arrive in a shielded address where transaction details remain hidden.
          </Text>
        </Box>
      )}

      {/* Wallet Links */}
      {showWalletLinks && !compact && (
        <>
          <VStack spacing={2} align="stretch">
            <Text fontWeight="semibold" fontSize="sm" color={textColor}>
              Need a Zcash wallet?
            </Text>
            <HStack spacing={2}>
              <Button
                as={Link}
                href="https://zashi.app/"
                isExternal
                colorScheme="yellow"
                variant="outline"
                size="sm"
                fontSize="xs"
                rightIcon={<FaExternalLinkAlt />}
                textDecoration="none"
                _hover={{ textDecoration: 'none' }}
                flex={1}
              >
                Zashi (Mobile)
              </Button>
              <Button
                as={Link}
                href="https://nighthawkwallet.com/"
                isExternal
                colorScheme="gray"
                variant="outline"
                size="sm"
                fontSize="xs"
                rightIcon={<FaExternalLinkAlt />}
                textDecoration="none"
                _hover={{ textDecoration: 'none' }}
                flex={1}
              >
                Nighthawk (Desktop)
              </Button>
            </HStack>
          </VStack>
          <Divider />
        </>
      )}

      {/* Address Input */}
      <FormControl isInvalid={!!error}>
        <FormLabel fontSize="sm" fontWeight="semibold">
          Zcash Address
        </FormLabel>
        <Input
          placeholder="u1... or t1... or t3..."
          value={address}
          onChange={(e) => handleAddressChange(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && handleConfirm()}
          disabled={isLoading}
          size="md"
          borderColor={borderColor}
          _focus={{
            borderColor: 'blue.500',
            boxShadow: '0 0 0 1px var(--chakra-colors-blue-500)',
          }}
          fontFamily="mono"
          fontSize="sm"
        />
        <FormErrorMessage fontSize="sm">
          {error}
        </FormErrorMessage>
        <Text fontSize="xs" color={mutedColor} mt={1}>
          Unified (u...) and Shielded (z...) addresses provide maximum privacy
        </Text>
      </FormControl>

      {/* Address Format Help (only in non-compact mode) */}
      {!compact && (
        <Box 
          p={3} 
          bg={bgColor}
          borderRadius="md" 
          borderWidth="1px" 
          borderColor={borderColor}
        >
          <Text fontSize="xs" fontWeight="semibold" mb={2} color={textColor}>
            Address Formats
          </Text>
          <VStack align="start" spacing={1}>
            <Text fontSize="xs" color={mutedColor}>
              <strong>u...</strong> Unified Address (recommended)
            </Text>
            <Text fontSize="xs" color={mutedColor}>
              <strong>z...</strong> Shielded Address
            </Text>
            <Text fontSize="xs" color={mutedColor}>
              <strong>t1/t3...</strong> Transparent Address (less privacy)
            </Text>
          </VStack>
        </Box>
      )}

      {/* Confirm Button (only when onConfirm provided) */}
      {onConfirm && (
        <Button
          colorScheme="yellow"
          onClick={handleConfirm}
          isLoading={isLoading}
          isDisabled={!address.trim()}
          width="full"
          size="sm"
        >
          Confirm Address
        </Button>
      )}
    </VStack>
  );
};

export default PrivacyAddressInput;

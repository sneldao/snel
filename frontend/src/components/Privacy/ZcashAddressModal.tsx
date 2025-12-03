/**
 * ZcashAddressModal - Collects Zcash receiving address for privacy bridge
 * Required before executing bridge to Zcash
 */

import React, { useState } from 'react';
import {
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalCloseButton,
  VStack,
  HStack,
  Input,
  Button,
  Text,
  Box,
  useColorModeValue,
  FormControl,
  FormLabel,
  FormErrorMessage,
  Link,
  Icon,
  Badge,
  Divider,
} from '@chakra-ui/react';
import { FaExternalLinkAlt, FaCheckCircle } from 'react-icons/fa';

interface ZcashAddressModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: (address: string) => void;
  isLoading?: boolean;
}

const ZCASH_ADDRESS_REGEX = /^(t1|t3|u)[a-zA-Z0-9]{33,}$/;

export const ZcashAddressModal: React.FC<ZcashAddressModalProps> = ({
  isOpen,
  onClose,
  onConfirm,
  isLoading = false,
}) => {
  const [address, setAddress] = useState('');
  const [error, setError] = useState('');
  
  const bgColor = useColorModeValue('white', 'gray.800');
  const textColor = useColorModeValue('gray.800', 'white');
  const mutedColor = useColorModeValue('gray.600', 'gray.400');
  const borderColor = useColorModeValue('gray.200', 'gray.600');

  const isValidAddress = ZCASH_ADDRESS_REGEX.test(address);

  const handleConfirm = () => {
    if (!address.trim()) {
      setError('Please enter a Zcash address');
      return;
    }
    
    if (!isValidAddress) {
      setError('Invalid Zcash address format. Should start with u, t1, or t3');
      return;
    }

    setError('');
    onConfirm(address);
    setAddress('');
  };

  const handleClose = () => {
    setAddress('');
    setError('');
    onClose();
  };

  return (
    <Modal isOpen={isOpen} onClose={handleClose} size="lg" isCentered>
      <ModalOverlay backdropFilter="blur(4px)" />
      <ModalContent bg={bgColor} borderRadius="xl" boxShadow="xl">
        <ModalHeader>
          <VStack align="start" spacing={2}>
            <Text fontSize="lg" fontWeight="bold">
              Zcash Receiving Address
            </Text>
            <Text fontSize="sm" color={mutedColor}>
              Where should your funds arrive?
            </Text>
          </VStack>
        </ModalHeader>
        <ModalCloseButton isDisabled={isLoading} />

        <ModalBody pb={6}>
          <VStack spacing={6} align="stretch">
            {/* Info Box */}
            <Box p={4} bg={useColorModeValue('blue.50', 'blue.900')} borderRadius="md" borderWidth="1px" borderColor="blue.200">
              <VStack spacing={2} align="start">
                <HStack>
                  <Icon as={FaCheckCircle} color="blue.500" />
                  <Text fontWeight="semibold" fontSize="sm" color={textColor}>
                    What's a Zcash Address?
                  </Text>
                </HStack>
                <Text fontSize="sm" color={mutedColor} lineHeight="1.6">
                  A Zcash address is where your private funds will be received. Use a <strong>unified address (starts with 'u')</strong> for full privacy. Shielded addresses hide transaction details.
                </Text>
              </VStack>
            </Box>

            <Divider />

            {/* Get Wallet Section */}
            <Box>
              <Text fontWeight="semibold" fontSize="sm" mb={3}>
                Don't have a Zcash wallet yet?
              </Text>
              <VStack spacing={2} align="stretch">
                <Button
                  as={Link}
                  href="https://zashi.app/"
                  isExternal
                  colorScheme="purple"
                  variant="outline"
                  size="sm"
                  rightIcon={<FaExternalLinkAlt />}
                  textDecoration="none"
                  _hover={{ textDecoration: 'none' }}
                >
                  Download Zashi (Mobile)
                </Button>
                <Button
                  as={Link}
                  href="https://nighthawkwallet.com/"
                  isExternal
                  colorScheme="blue"
                  variant="outline"
                  size="sm"
                  rightIcon={<FaExternalLinkAlt />}
                  textDecoration="none"
                  _hover={{ textDecoration: 'none' }}
                >
                  Download Nighthawk (Desktop)
                </Button>
                <Text fontSize="xs" color={mutedColor} mt={2}>
                  Both wallets are <Badge colorScheme="green" fontSize="xs">shielded by default</Badge>
                </Text>
              </VStack>
            </Box>

            <Divider />

            {/* Address Input */}
            <FormControl isInvalid={!!error}>
              <FormLabel fontSize="sm" fontWeight="semibold">
                Zcash Address
              </FormLabel>
              <Input
                placeholder="u1... or t1... or t3..."
                value={address}
                onChange={(e) => {
                  setAddress(e.target.value);
                  setError('');
                }}
                onKeyPress={(e) => e.key === 'Enter' && handleConfirm()}
                disabled={isLoading}
                size="md"
                borderColor={borderColor}
                _focus={{
                  borderColor: 'blue.500',
                  boxShadow: '0 0 0 1px var(--chakra-colors-blue-500)',
                }}
                fontFamily="mono"
              />
              <FormErrorMessage fontSize="sm">
                {error}
              </FormErrorMessage>
              <Text fontSize="xs" color={mutedColor} mt={1}>
                Unified addresses (u...) provide maximum privacy
              </Text>
            </FormControl>

            {/* Address Format Help */}
            <Box p={3} bg={useColorModeValue('gray.50', 'gray.700')} borderRadius="md" borderWidth="1px" borderColor={borderColor}>
              <Text fontSize="xs" fontWeight="semibold" mb={2} color={textColor}>
                Valid Address Formats:
              </Text>
              <VStack spacing={1} align="start">
                <Text fontSize="xs" color={mutedColor}>
                  🛡️ <strong>u...</strong> (Unified - recommended for privacy)
                </Text>
                <Text fontSize="xs" color={mutedColor}>
                  🔒 <strong>z...</strong> (Shielded transparent address)
                </Text>
                <Text fontSize="xs" color={mutedColor}>
                  👁️ <strong>t1/t3...</strong> (Transparent - not private)
                </Text>
              </VStack>
            </Box>

            {/* Action Buttons */}
            <HStack spacing={3} pt={4}>
              <Button
                variant="outline"
                onClick={handleClose}
                isDisabled={isLoading}
                flex={1}
              >
                Cancel
              </Button>
              <Button
                colorScheme="purple"
                onClick={handleConfirm}
                isLoading={isLoading}
                isDisabled={!address.trim()}
                flex={1}
              >
                Confirm Address
              </Button>
            </HStack>
          </VStack>
        </ModalBody>
      </ModalContent>
    </Modal>
  );
};

export default ZcashAddressModal;

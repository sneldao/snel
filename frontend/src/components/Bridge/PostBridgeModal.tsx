/**
 * PostBridgeModal - Success state and next steps after bridge completion
 * 
 * Displays when bridge transaction completes successfully.
 * Shows receiving address, actions (Receive/Spend/Learn), and merchant directory.
 * 
 * Follows MODULAR and ENHANCEMENT principles - reuses existing components.
 */

import React, { memo, useState } from 'react';
import { MERCHANT_DIRECTORY } from '../../constants/privacy';
import {
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalCloseButton,
  ModalBody,
  ModalFooter,
  VStack,
  HStack,
  Box,
  Button,
  Text,
  Badge,
  Grid,
  GridItem,
  useClipboard,
  Icon,
  Tooltip,
  useColorModeValue,
} from '@chakra-ui/react';
import { CheckCircleIcon, CopyIcon, ExternalLinkIcon } from '@chakra-ui/icons';
import { FaWallet, FaShoppingCart, FaBookOpen } from 'react-icons/fa';
import type { PostBridgeSuccessContent } from '../../types/responses';

interface PostBridgeModalProps {
  isOpen: boolean;
  content: PostBridgeSuccessContent;
  onClose: () => void;
}

/**
 * Action card component - displays single action option
 */
const ActionCard = memo(
  ({
    action,
    onActionClick,
  }: {
    action: PostBridgeSuccessContent['actions'][0];
    onActionClick: (action: PostBridgeSuccessContent['actions'][0]) => void;
  }) => {
    const bgColor = useColorModeValue('gray.50', 'gray.700');
    const borderColor = useColorModeValue('gray.200', 'gray.600');
    const hoverBg = useColorModeValue('gray.100', 'gray.600');

    const iconMap: Record<string, React.ReactNode> = {
      receive: <Icon as={FaWallet} w={6} h={6} color="blue.500" />,
      spend: <Icon as={FaShoppingCart} w={6} h={6} color="green.500" />,
      learn: <Icon as={FaBookOpen} w={6} h={6} color="purple.500" />,
    };

    return (
      <Box
        p={4}
        borderWidth={1}
        borderColor={borderColor}
        borderRadius="lg"
        bg={bgColor}
        cursor="pointer"
        transition="all 0.2s"
        _hover={{ bg: hoverBg, shadow: 'md', borderColor: 'blue.400' }}
        onClick={() => onActionClick(action)}
      >
        <VStack align="start" spacing={2}>
          <HStack spacing={2}>
            {iconMap[action.id]}
            <Text fontWeight="bold" fontSize="md">
              {action.title}
            </Text>
          </HStack>
          <Text fontSize="sm" color="gray.600">
            {action.description}
          </Text>
          <Button
            size="sm"
            colorScheme="blue"
            variant="outline"
            rightIcon={<ExternalLinkIcon />}
            mt={2}
          >
            {action.cta_text}
          </Button>
        </VStack>
      </Box>
    );
  }
);

ActionCard.displayName = 'ActionCard';

/**
 * Address display and copy component
 */
const AddressDisplay = memo(({ address }: { address: string }) => {
  const { onCopy, hasCopied } = useClipboard(address);
  const bgColor = useColorModeValue('blue.50', 'blue.900');
  const borderColor = useColorModeValue('blue.200', 'blue.700');

  return (
    <Box
      p={3}
      borderWidth={1}
      borderColor={borderColor}
      bg={bgColor}
      borderRadius="md"
      mb={4}
    >
      <Text fontSize="xs" color="gray.600" mb={2} fontWeight="medium">
        Your Zcash Receiving Address
      </Text>
      <HStack spacing={2} justify="space-between">
        <Text
          fontSize="sm"
          fontFamily="mono"
          color="blue.600"
          wordBreak="break-all"
          flex={1}
        >
          {address}
        </Text>
        <Tooltip label={hasCopied ? 'Copied!' : 'Copy address'}>
          <Button
            size="sm"
            variant="ghost"
            onClick={onCopy}
            colorScheme={hasCopied ? 'green' : 'blue'}
          >
            <CopyIcon />
          </Button>
        </Tooltip>
      </HStack>
    </Box>
  );
});

AddressDisplay.displayName = 'AddressDisplay';

/**
 * Main post-bridge modal component
 */
export const PostBridgeModal = memo(
  ({ isOpen, content, onClose }: PostBridgeModalProps) => {
    const borderBgColor = useColorModeValue('gray.200', 'gray.600');
    const blueBg = useColorModeValue('blue.50', 'blue.900');
    const grayBg = useColorModeValue('gray.100', 'gray.700');
    const grayBgHover = useColorModeValue('gray.200', 'gray.600');
    const yellowBg = useColorModeValue('yellow.50', 'yellow.900');
    
    const handleActionClick = (action: PostBridgeSuccessContent['actions'][0]) => {
      if (action.cta_url) {
        window.open(action.cta_url, '_blank');
      }
    };

    return (
      <Modal isOpen={isOpen} onClose={onClose} size="xl" isCentered>
        <ModalOverlay backdropFilter="blur(4px)" />
        <ModalContent>
          {/* Header with success badge */}
          <ModalHeader pb={2}>
            <HStack spacing={2}>
              <CheckCircleIcon color="green.500" w={6} h={6} />
              <VStack align="start" spacing={0}>
                <Text fontSize="lg" fontWeight="bold">
                  Bridge Complete
                </Text>
                <Text fontSize="sm" color="gray.500">
                  Your funds are on their way
                </Text>
              </VStack>
            </HStack>
          </ModalHeader>
          <ModalCloseButton />

          <ModalBody>
            <VStack spacing={4} align="stretch">
              {/* Transaction summary */}
              <Box
                p={3}
                borderRadius="md"
                bg={useColorModeValue('gray.50', 'gray.700')}
              >
                <Grid templateColumns="1fr 1fr" gap={4}>
                  <GridItem>
                    <Text fontSize="xs" color="gray.600" fontWeight="medium">
                      Amount
                    </Text>
                    <Text fontSize="md" fontWeight="bold">
                      {content.amount} {content.token}
                    </Text>
                  </GridItem>
                  <GridItem>
                    <Text fontSize="xs" color="gray.600" fontWeight="medium">
                      From
                    </Text>
                    <Text fontSize="md" fontWeight="bold">
                      {content.from_chain}
                    </Text>
                  </GridItem>
                  <GridItem>
                    <Text fontSize="xs" color="gray.600" fontWeight="medium">
                      To
                    </Text>
                    <Badge colorScheme="purple">{content.to_chain}</Badge>
                  </GridItem>
                  <GridItem>
                    <Text fontSize="xs" color="gray.600" fontWeight="medium">
                      Status
                    </Text>
                    <Badge colorScheme="green">Completed</Badge>
                  </GridItem>
                </Grid>
              </Box>

              {/* Receiving address */}
              <AddressDisplay address={content.receiving_address} />

              {/* Action cards */}
              <Box>
                <Text fontWeight="bold" fontSize="sm" mb={3}>
                  What&apos;s Next?
                </Text>
                <Grid templateColumns="repeat(auto-fit, minmax(150px, 1fr))" gap={3}>
                  {content.actions.map((action) => (
                    <GridItem key={action.id}>
                      <ActionCard
                        action={action}
                        onActionClick={handleActionClick}
                      />
                    </GridItem>
                  ))}
                </Grid>
              </Box>

              {/* Next steps if provided */}
              {content.next_steps && content.next_steps.length > 0 && (
                <Box borderTop="1px solid" borderColor={borderBgColor} pt={3}>
                  <Text fontWeight="bold" fontSize="sm" mb={2}>
                    Quick Steps
                  </Text>
                  <VStack align="start" spacing={2}>
                    {content.next_steps.map((step, idx) => (
                      <HStack key={idx} spacing={2}>
                        <Badge colorScheme="blue" fontSize="xs">
                          {idx + 1}
                        </Badge>
                        <Text fontSize="sm">{step}</Text>
                      </HStack>
                    ))}
                  </VStack>
                </Box>
              )}

              {/* Merchant Directory */}
              <Box borderTop="1px solid" borderColor={borderBgColor} pt={3}>
                <Text fontWeight="bold" fontSize="sm" mb={3}>
                  Where to Spend Your Zcash
                </Text>
                <VStack spacing={3}>
                  {/* Primary Directory */}
                  <Box
                    p={3}
                    borderRadius="md"
                    bg={blueBg}
                    borderWidth={1}
                    borderColor="blue.200"
                    width="100%"
                    cursor="pointer"
                    transition="all 0.2s"
                    _hover={{ shadow: 'md' }}
                    onClick={() => window.open(MERCHANT_DIRECTORY.primary.url, '_blank')}
                  >
                    <HStack justify="space-between" mb={1}>
                      <Text fontWeight="bold" fontSize="sm">
                        {MERCHANT_DIRECTORY.primary.name}
                      </Text>
                      <Badge colorScheme="blue" fontSize="xs">
                        {MERCHANT_DIRECTORY.primary.badge}
                      </Badge>
                    </HStack>
                    <Text fontSize="xs" color="gray.600" mb={2}>
                      {MERCHANT_DIRECTORY.primary.description}
                    </Text>
                    <HStack spacing={1} flexWrap="wrap">
                      {MERCHANT_DIRECTORY.primary.categories.map((cat) => (
                        <Badge key={cat} colorScheme="purple" fontSize="xs">
                          {cat}
                        </Badge>
                      ))}
                    </HStack>
                  </Box>

                  {/* Secondary Resources */}
                  <Box fontSize="xs">
                    <Text fontWeight="bold" mb={2} fontSize="xs">
                      Also Try
                    </Text>
                    <VStack spacing={1} align="start">
                      {MERCHANT_DIRECTORY.secondaryResources.map((resource) => (
                        <HStack
                          key={resource.name}
                          spacing={2}
                          p={2}
                          borderRadius="md"
                          bg={grayBg}
                          cursor="pointer"
                          transition="all 0.2s"
                          _hover={{ bg: grayBgHover }}
                          width="100%"
                          onClick={() => window.open(resource.url, '_blank')}
                        >
                          <Box flex={1}>
                            <Text fontSize="xs" fontWeight="bold">
                              {resource.name}
                            </Text>
                            <Text fontSize="xs" color="gray.500">
                              {resource.description}
                            </Text>
                          </Box>
                          <Badge colorScheme="gray" fontSize="xs">
                            {resource.category}
                          </Badge>
                        </HStack>
                      ))}
                    </VStack>
                  </Box>

                  {/* Tips */}
                  <Box
                    p={2}
                    borderRadius="md"
                    bg={yellowBg}
                    borderLeft="3px solid"
                    borderColor="yellow.500"
                    width="100%"
                  >
                    <Text fontWeight="bold" fontSize="xs" mb={1}>
                      💡 Pro Tips
                    </Text>
                    <VStack align="start" spacing={1}>
                      {MERCHANT_DIRECTORY.tips.map((tip, idx) => (
                        <Text key={idx} fontSize="xs" color="gray.600">
                          • {tip}
                        </Text>
                      ))}
                    </VStack>
                  </Box>
                </VStack>
              </Box>
            </VStack>
          </ModalBody>

          <ModalFooter>
            <Button colorScheme="blue" onClick={onClose}>
              Got It
            </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>
    );
  }
);

PostBridgeModal.displayName = 'PostBridgeModal';

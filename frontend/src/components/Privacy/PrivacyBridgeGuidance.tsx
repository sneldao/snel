/**
 * PrivacyBridgeGuidance - Reusable privacy bridge guidance component
 * Follows MODULAR and DRY principles for wallet recommendations and post-bridge steps
 */

import React, { memo, useState } from 'react';
import {
  Box,
  VStack,
  HStack,
  Text,
  Badge,
  Link,
  Icon,
  Divider,
  Heading,
  Button,
  Collapse,
  useDisclosure,
  useColorModeValue,
  Tabs,
  TabList,
  Tab,
  TabPanels,
  TabPanel,
} from '@chakra-ui/react';
import { FaExternalLinkAlt, FaChevronDown, FaCheckCircle, FaLock, FaDownload, FaBook, FaFlask } from 'react-icons/fa';
import { BridgePrivacyReadyContent } from '../../types/responses';
import { ZCASH_WALLETS, ZCASH_EDUCATION_LINKS } from '../../constants/privacy';

interface PrivacyBridgeGuidanceProps {
  content: BridgePrivacyReadyContent;
  isCompact?: boolean;
  disclosureLevel?: 'simple' | 'detailed' | 'technical'; // Progressive disclosure (Tier 2.3)
}

/**
 * Wallet recommendation card
 * Shows wallet info with download and learn more links
 */
type WalletType = typeof ZCASH_WALLETS[number];
const WalletCard = memo(({ wallet, isCompact = false }: { wallet: WalletType; isCompact?: boolean }) => {
  const bgColor = useColorModeValue('gray.50', 'gray.700');
  const borderColor = useColorModeValue('yellow.200', 'yellow.600');
  const textColor = useColorModeValue('gray.600', 'gray.300');

  if (isCompact) {
    return (
      <HStack
        p={2}
        borderRadius="md"
        bg={bgColor}
        borderLeft="3px solid"
        borderColor="yellow.500"
        spacing={2}
        justify="space-between"
      >
        <VStack align="start" spacing={0} flex={1}>
          <HStack spacing={1}>
            <Text fontSize="sm" fontWeight="semibold">
              {wallet.name}
            </Text>
            {wallet.badge && (
              <Badge colorScheme="green" fontSize="xs">
                {wallet.badge}
              </Badge>
            )}
          </HStack>
          <Text fontSize="xs" color={textColor}>
            {wallet.type}
          </Text>
        </VStack>
        <Link href={wallet.url} isExternal>
          <Button size="xs" colorScheme="yellow" variant="outline">
            Get <Icon as={FaDownload} ml={1} boxSize={3} />
          </Button>
        </Link>
      </HStack>
    );
  }

  return (
    <Box
      p={3}
      borderRadius="md"
      bg={bgColor}
      borderLeft="4px solid"
      borderColor="yellow.500"
      borderTop="1px solid"
      borderTopColor={borderColor}
    >
      <HStack justify="space-between" mb={2}>
        <VStack align="start" spacing={1}>
          <HStack spacing={2}>
            <Heading size="sm">{wallet.name}</Heading>
            {wallet.badge && (
              <Badge colorScheme="green" fontSize="xs">
                {wallet.badge}
              </Badge>
            )}
          </HStack>
          <Badge colorScheme="blue" fontSize="xs">
            {wallet.type}
          </Badge>
        </VStack>
      </HStack>

      <Text fontSize="sm" color={textColor} mb={3}>
        {wallet.description}
      </Text>

      <HStack spacing={2} flexWrap="wrap">
        {wallet.platforms.map((platform) => (
          <Badge key={platform} variant="outline" fontSize="xs">
            {platform}
          </Badge>
        ))}
      </HStack>

      <HStack mt={3} spacing={2}>
        <Link href={wallet.url} isExternal>
          <Button size="sm" colorScheme="yellow">
            Download <Icon as={FaDownload} ml={2} boxSize={3} />
          </Button>
        </Link>
        <Link href="https://z.cash/learn/whats-the-best-zcash-wallet/" isExternal>
          <Button size="sm" variant="outline">
            Learn More <Icon as={FaExternalLinkAlt} ml={2} boxSize={3} />
          </Button>
        </Link>
      </HStack>
    </Box>
  );
});
WalletCard.displayName = 'WalletCard';

/**
 * Post-bridge instruction step
 */
const InstructionStep = memo(
  ({ step, title, description }: { step: number; title: string; description: string }) => {
    const textColor = useColorModeValue('gray.600', 'gray.300');

    return (
      <HStack spacing={3} align="start">
        <Badge colorScheme="blue" borderRadius="full" boxSize={6} display="flex" alignItems="center" justifyContent="center">
          {step}
        </Badge>
        <VStack align="start" spacing={0} flex={1}>
          <Text fontWeight="semibold" fontSize="sm">
            {title}
          </Text>
          <Text fontSize="xs" color={textColor}>
            {description}
          </Text>
        </VStack>
      </HStack>
    );
  }
);
InstructionStep.displayName = 'InstructionStep';

/**
 * Main Privacy Bridge Guidance Component
 * Supports progressive disclosure: simple → detailed → technical (Tier 2.3)
 */
export const PrivacyBridgeGuidance = memo(
  ({ content, isCompact = false, disclosureLevel = 'detailed' }: PrivacyBridgeGuidanceProps) => {
    const { isOpen, onToggle } = useDisclosure({ defaultIsOpen: !isCompact });
    const textColor = useColorModeValue('gray.600', 'gray.300');
    const bgColor = useColorModeValue('yellow.50', 'gray.800');
    const borderColor = useColorModeValue('yellow.200', 'yellow.600');
    const conceptBgColor = useColorModeValue('gray.100', 'gray.700');
    const hoverBgColor = useColorModeValue('gray.200', 'gray.600');

  const guidance = content.post_bridge_guidance;
  if (!guidance) return null;

  // SIMPLE disclosure level (Tier 2.3)
  if (disclosureLevel === 'simple') {
    return (
      <Box
        p={3}
        borderRadius="md"
        bg={bgColor}
        border="1px solid"
        borderColor={borderColor}
        width="100%"
      >
        <HStack spacing={2} mb={2}>
          <Icon as={FaLock} color="yellow.600" boxSize={4} />
          <Text fontWeight="semibold" fontSize="sm">
            Your assets will be private
          </Text>
        </HStack>
        <Text fontSize="sm" color={textColor} mb={3}>
          Your transaction details stay hidden. After bridging, you&apos;ll need a Zcash wallet to receive your funds.
        </Text>
        <Link href={ZCASH_EDUCATION_LINKS[0].url} isExternal>
          <Button size="sm" variant="outline" rightIcon={<Icon as={FaExternalLinkAlt} boxSize={3} />}>
            Learn more about privacy
          </Button>
        </Link>
      </Box>
    );
  }

  if (isCompact) {
    return (
      <VStack spacing={2} align="stretch">
        <Button
          onClick={onToggle}
          variant="ghost"
          size="sm"
          justifyContent="flex-start"
          rightIcon={<FaChevronDown transform={isOpen ? 'rotate(180deg)' : ''} />}
        >
          <Icon as={FaLock} mr={2} color="yellow.500" />
          After Bridging
        </Button>

        <Collapse in={isOpen} animateOpacity>
          <VStack spacing={3} align="stretch" p={3} borderRadius="md" bg={bgColor} border="1px solid" borderColor={borderColor}>
            {/* Wallets */}
            <Box>
              <Heading size="xs" mb={2}>
                Get a Zcash Wallet
              </Heading>
              <VStack spacing={2}>
                {guidance.recommended_wallets.map((wallet) => {
                  const walletData = ZCASH_WALLETS.find((w) => w.url === wallet.url) || null;
                  return walletData ? <WalletCard key={wallet.name} wallet={walletData} isCompact /> : null;
                })}
              </VStack>
            </Box>

            {/* Quick Tips */}
            {guidance.security_tips.length > 0 && (
              <>
                <Divider />
                <Box>
                  <Heading size="xs" mb={2}>
                    Security Tips
                  </Heading>
                  <VStack spacing={1} align="start">
                    {guidance.security_tips.map((tip, idx) => (
                      <HStack key={idx} spacing={1} fontSize="xs">
                        <Icon as={FaCheckCircle} color="green.500" boxSize={3} />
                        <Text color={textColor}>{tip}</Text>
                      </HStack>
                    ))}
                  </VStack>
                </Box>
              </>
            )}
          </VStack>
        </Collapse>
      </VStack>
    );
  }

  // Full/Detailed view with tabs (Tier 2.3 - progressive disclosure with education)
  return (
    <Box
      p={4}
      borderRadius="lg"
      bg={bgColor}
      border="2px solid"
      borderColor={borderColor}
      width="100%"
    >
      <VStack spacing={4} align="stretch">
        {/* Header */}
        <HStack spacing={2}>
          <Icon as={FaLock} color="yellow.600" boxSize={5} />
          <Heading size="md">{guidance.title}</Heading>
        </HStack>

        <Divider />

        {/* Tabs for Detailed + Education (Tier 2.3) */}
        <Tabs variant="enclosed" defaultIndex={0}>
          <TabList mb="1em">
            <Tab>Steps</Tab>
            <Tab>Wallets</Tab>
            <Tab display="flex" alignItems="center" gap={2}>
              <Icon as={FaBook} boxSize={4} />
              Learn More
            </Tab>
            {disclosureLevel === 'technical' && (
              <Tab display="flex" alignItems="center" gap={2}>
                <Icon as={FaFlask} boxSize={4} />
                Technical
              </Tab>
            )}
          </TabList>

          <TabPanels>
            {/* Steps Tab */}
            <TabPanel>
              <VStack spacing={3}>
                {guidance.instructions.map((instruction) => (
                  <InstructionStep
                    key={instruction.step}
                    step={instruction.step}
                    title={instruction.title}
                    description={instruction.description}
                  />
                ))}
              </VStack>
            </TabPanel>

            {/* Wallets Tab */}
            <TabPanel>
              <VStack spacing={3}>
                {guidance.recommended_wallets.map((wallet) => {
                  const walletData = ZCASH_WALLETS.find((w) => w.url === wallet.url) || null;
                  return walletData ? <WalletCard key={wallet.name} wallet={walletData} /> : null;
                })}
                {/* Security Tips in Wallets tab */}
                {guidance.security_tips.length > 0 && (
                  <>
                    <Divider my={3} />
                    <Box width="100%">
                      <Heading size="sm" mb={3}>
                        Security Tips
                      </Heading>
                      <VStack spacing={2} align="start">
                        {guidance.security_tips.map((tip, idx) => (
                          <HStack key={idx} spacing={2}>
                            <Icon as={FaCheckCircle} color="green.500" boxSize={4} />
                            <Text fontSize="sm" color={textColor}>{tip}</Text>
                          </HStack>
                        ))}
                      </VStack>
                    </Box>
                  </>
                )}
              </VStack>
            </TabPanel>

            {/* Education Tab - Tier 2.1 Education Links */}
            <TabPanel>
              <VStack spacing={3} align="stretch">
                <Text fontSize="sm" color={textColor}>
                  Understand the concepts behind private transactions with these official Zcash guides.
                </Text>
                {ZCASH_EDUCATION_LINKS.map((link, idx) => (
                  <Link key={idx} href={link.url} isExternal _hover={{ textDecoration: 'none' }}>
                    <Box
                      p={3}
                      borderRadius="md"
                      bg={conceptBgColor}
                      _hover={{ bg: hoverBgColor }}
                      cursor="pointer"
                      transition="all 0.2s"
                    >
                      <HStack justify="space-between" align="start">
                        <VStack align="start" spacing={1} flex={1}>
                          <Text fontWeight="semibold" fontSize="sm">
                            {link.title}
                          </Text>
                          <Text fontSize="xs" color={textColor}>
                            {link.description}
                          </Text>
                        </VStack>
                        <Icon as={FaExternalLinkAlt} color="blue.500" boxSize={4} flexShrink={0} />
                      </HStack>
                    </Box>
                  </Link>
                ))}
              </VStack>
            </TabPanel>

            {/* Technical Tab - Tier 2.3 Advanced details */}
            {disclosureLevel === 'technical' && (
              <TabPanel>
                <VStack spacing={3} align="stretch" fontSize="sm">
                  <Box p={3} borderRadius="md" bg={conceptBgColor}>
                    <Heading size="xs" mb={2}>Protocol Details</Heading>
                    <Text color={textColor}>
                      Bridge Protocol: Axelar General Message Passing (GMP)
                    </Text>
                    <Text color={textColor} fontSize="xs" mt={1}>
                      Uses zero-knowledge proofs to ensure transaction security and privacy across chains.
                    </Text>
                  </Box>
                  <Box p={3} borderRadius="md" bg={conceptBgColor}>
                    <Heading size="xs" mb={2}>Estimated Timing</Heading>
                    <Text color={textColor}>
                      Typical confirmation: 5-10 minutes depending on network congestion
                    </Text>
                  </Box>
                  <Box p={3} borderRadius="md" bg={conceptBgColor}>
                    <Heading size="xs" mb={2}>Advanced Resources</Heading>
                    <Link href="https://z.cash/learn/" isExternal color="blue.500" fontSize="xs">
                      Zcash Protocol Documentation <Icon as={FaExternalLinkAlt} ml={1} boxSize={3} />
                    </Link>
                  </Box>
                </VStack>
              </TabPanel>
            )}
          </TabPanels>
        </Tabs>
      </VStack>
    </Box>
  );
  }
);
PrivacyBridgeGuidance.displayName = 'PrivacyBridgeGuidance';

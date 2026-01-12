import React, { useState } from "react";
import {
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalFooter,
  ModalBody,
  ModalCloseButton,
  Button,
  Text,
  VStack,
  Box,
  Heading,
  Divider,
  useColorModeValue,
  Flex,
  Icon,
  List,
  ListItem,
  SimpleGrid,
  Tabs,
  TabList,
  TabPanels,
  Tab,
  TabPanel,
  Badge,
  Link,
  UnorderedList,
  HStack,
} from "@chakra-ui/react";
import {
  FaExchangeAlt,
  FaWallet,
  FaCoins,
  FaArrowRight,
  FaBalanceScale,
  FaChartLine,
  FaSearch,
  FaShieldAlt,
  FaExternalLinkAlt,
  FaClock,
  FaBolt,
} from "react-icons/fa";
import { BsArrowLeftRight } from "react-icons/bs";
import Image from "next/image";
import { PRIVACY_BRIDGE_GUIDANCE, ZCASH_WALLETS, PRIVACY_FAQ, PRIVACY_RESOURCES, ZCASH_EDUCATION_LINKS, PRIVACY_CONCEPTS, MERCHANT_DIRECTORY } from "../constants/privacy";
import { PrivacyTermTooltip } from "./Privacy/PrivacyTermTooltip";

interface HelpModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const HelpModal: React.FC<HelpModalProps> = ({ isOpen, onClose }) => {
  const bgColor = useColorModeValue("white", "gray.800");
  const borderColor = useColorModeValue("gray.200", "gray.700");
  const headingColor = useColorModeValue("gray.700", "white");
  const textColor = useColorModeValue("gray.600", "gray.300");
  const exampleBoxBg = useColorModeValue("gray.50", "gray.700");
  const hoverBg = useColorModeValue("gray.100", "gray.600");
  const conceptBg = useColorModeValue("gray.100", "gray.700");
  const [selectedTab, setSelectedTab] = useState(0);

  const basicCommands = [
    {
      category: "Token Transfers",
      icon: FaArrowRight,
      examples: [
        "send 10 USDC to 0x123...",
        "transfer 0.1 ETH to papajams.eth",
      ],
    },
    {
      category: "Cross-Chain Bridging",
      icon: BsArrowLeftRight,
      examples: [
        "bridge 0.1 ETH from Scroll to Base",
        "bridge 50 USDC from Ethereum to Arbitrum",
      ],
    },
    {
      category: "Balance Checking",
      icon: FaBalanceScale,
      examples: ["check my USDC balance on Scroll", "what's my ETH balance"],
    },
    {
      category: "Token Swaps",
      icon: FaExchangeAlt,
      examples: ["swap 1 ETH for USDC", "swap $100 worth of USDC for ETH"],
    },
  ];

  const portfolioAnalysis = [
    {
      category: "Portfolio Analysis",
      icon: FaChartLine,
      examples: [
        "analyze my portfolio",
        "what's my portfolio allocation?",
        "show me my risk assessment",
      ],
    },
    {
      category: "Protocol Research",
      icon: FaSearch,
      examples: [
        "tell me about Aave",
        "what is Uniswap?",
        "research Compound protocol",
        "how does Curve work?",
      ],
    },
  ];

  const paymentAutomation = [
    {
      category: "X402 Automation",
      icon: FaBolt,
      examples: [
        "setup portfolio rebalancing with 50 USDC",
        "pay 20 USDC when ETH drops below $3000",
        "setup weekly 100 USDC for yield farming",
        "create automated bridge 200 USDC monthly",
      ],
    },
  ];

  const privacyFeatures = [
    {
      category: "Privacy Bridging",
      icon: FaShieldAlt,
      examples: [
        "bridge 1 ETH to Zcash",
        "make my 100 USDC private",
        "what about privacy?",
        "can I do stuff in private?",
      ],
    },
  ];

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="lg" isCentered>
      <ModalOverlay backdropFilter="blur(4px)" />
      <ModalContent
        borderRadius="xl"
        boxShadow="xl"
        bg={bgColor}
        border="1px solid"
        borderColor={borderColor}
        mx={4}
        maxW="600px"
      >
        <ModalHeader
          display="flex"
          alignItems="center"
          justifyContent="center"
          pt={4}
          pb={2}
        >
          <Flex align="center" justify="center" direction="row" gap={3}>
            <Box position="relative" width="40px" height="40px">
              <Image
                src="/icon.png"
                alt="SNEL Logo"
                width={40}
                height={40}
                priority
                style={{ objectFit: "contain" }}
              />
            </Box>
            <Heading size="md" color={headingColor}>
              What can SNEL do?
            </Heading>
          </Flex>
        </ModalHeader>
        <ModalCloseButton />

        <ModalBody pb={4} px={4}>
          <Tabs onChange={setSelectedTab} variant="enclosed">
            <TabList mb="1em">
              <Tab>Commands</Tab>
              <Tab>Payments & Automation</Tab>
              <Tab>Portfolio & Analysis</Tab>
              <Tab>Privacy Guide</Tab>
            </TabList>

            <TabPanels>
              {/* Commands Tab - Basic Operations */}
              <TabPanel>
                <SimpleGrid columns={1} spacing={3} alignItems="stretch">
                  {basicCommands.map((category, idx) => (
                    <Box key={idx} p={2} borderRadius="md" bg={exampleBoxBg}>
                      <Flex align="center" mb={1}>
                        <Icon
                          as={category.icon}
                          mr={2}
                          color="blue.500"
                          boxSize={4}
                        />
                        <Heading size="xs" color={headingColor}>
                          {category.category}
                        </Heading>
                      </Flex>
                      <List spacing={1} pl={6} fontSize="xs">
                        {category.examples.map((example, exIdx) => (
                          <ListItem key={exIdx} color={textColor}>
                            <Text as="span" fontFamily="mono" fontWeight="medium">
                              &quot;{example}&quot;
                            </Text>
                          </ListItem>
                        ))}
                      </List>
                    </Box>
                  ))}
                </SimpleGrid>
              </TabPanel>

              {/* Payment Actions Tab */}
              <TabPanel>
                <VStack spacing={4} align="stretch">
                  {/* X402 Automation Section */}
                  <Box>
                    <Heading size="sm" mb={3} color={headingColor}>
                      DeFi Automation (X402)
                    </Heading>
                    <SimpleGrid columns={1} spacing={3} alignItems="stretch">
                      {paymentAutomation.map((category, idx) => (
                        <Box key={idx} p={3} borderRadius="md" bg="purple.50" border="1px solid" borderColor="purple.200">
                          <Flex align="center" mb={2}>
                            <Icon
                              as={category.icon}
                              mr={2}
                              color="purple.600"
                              boxSize={4}
                            />
                            <Heading size="xs" color="purple.700">
                              {category.category}
                            </Heading>
                          </Flex>
                          <Text fontSize="xs" color="purple.600" mb={2}>
                            AI-powered automation on Cronos EVM with real x402 protocol integration
                          </Text>
                          <List spacing={1} pl={6} fontSize="xs">
                            {category.examples.map((example, exIdx) => (
                              <ListItem key={exIdx} color="purple.700">
                                <Text as="span" fontFamily="mono" fontWeight="medium">
                                  &quot;{example}&quot;
                                </Text>
                              </ListItem>
                            ))}
                          </List>
                        </Box>
                      ))}
                    </SimpleGrid>
                  </Box>

                  <Divider />

                  {/* Traditional Payment Actions */}
                  <Box>
                    <Heading size="sm" mb={2} color={headingColor}>
                      Payment Actions
                    </Heading>
                    <Text fontSize="sm" color={textColor} mb={3}>
                      Create reusable payment shortcuts and automate recurring payments.
                    </Text>

                    <VStack spacing={2} align="stretch">
                      <Box p={2} borderRadius="md" bg={exampleBoxBg}>
                        <Flex align="start" mb={1}>
                          <Icon as={FaWallet} mr={2} color="blue.500" boxSize={4} mt="2px" />
                          <VStack align="start" spacing={0}>
                            <Text fontSize="xs" fontWeight="semibold" color={headingColor}>
                              Quick Actions
                            </Text>
                            <Text fontSize="xs" color={textColor}>
                              Pin frequent payments as buttons for instant access.
                            </Text>
                          </VStack>
                        </Flex>
                      </Box>
                      <Box p={2} borderRadius="md" bg={exampleBoxBg}>
                        <Flex align="start">
                          <Icon as={FaClock} mr={2} color="green.500" boxSize={4} mt="2px" />
                          <VStack align="start" spacing={0}>
                            <Text fontSize="xs" fontWeight="semibold" color={headingColor}>
                              Example Commands
                            </Text>
                            <Text fontSize="xs" color={textColor}>
                              "create payment action" • "use action rent" • "show my actions"
                            </Text>
                          </VStack>
                        </Flex>
                      </Box>
                    </VStack>
                  </Box>
                </VStack>
              </TabPanel>

              {/* Portfolio & Analysis Tab */}
              <TabPanel>
                <SimpleGrid columns={1} spacing={3} alignItems="stretch">
                  {portfolioAnalysis.map((category, idx) => (
                    <Box key={idx} p={2} borderRadius="md" bg={exampleBoxBg}>
                      <Flex align="center" mb={1}>
                        <Icon
                          as={category.icon}
                          mr={2}
                          color="blue.500"
                          boxSize={4}
                        />
                        <Heading size="xs" color={headingColor}>
                          {category.category}
                        </Heading>
                      </Flex>
                      <List spacing={1} pl={6} fontSize="xs">
                        {category.examples.map((example, exIdx) => (
                          <ListItem key={exIdx} color={textColor}>
                            <Text as="span" fontFamily="mono" fontWeight="medium">
                              &quot;{example}&quot;
                            </Text>
                          </ListItem>
                        ))}
                      </List>
                    </Box>
                  ))}
                </SimpleGrid>
              </TabPanel>

              {/* Privacy Guide Tab */}
              <TabPanel>
                <VStack spacing={4} align="stretch">
                  {/* Privacy Commands */}
                  <Box>
                    <Heading size="sm" mb={3} color={headingColor}>
                      Privacy Commands
                    </Heading>
                    <SimpleGrid columns={1} spacing={3} alignItems="stretch">
                      {privacyFeatures.map((category, idx) => (
                        <Box key={idx} p={3} borderRadius="md" bg="yellow.50" border="1px solid" borderColor="yellow.200">
                          <Flex align="center" mb={2}>
                            <Icon
                              as={category.icon}
                              mr={2}
                              color="yellow.600"
                              boxSize={4}
                            />
                            <Heading size="xs" color="yellow.700">
                              {category.category}
                            </Heading>
                          </Flex>
                          <List spacing={1} pl={6} fontSize="xs">
                            {category.examples.map((example, exIdx) => (
                              <ListItem key={exIdx} color="yellow.700">
                                <Text as="span" fontFamily="mono" fontWeight="medium">
                                  &quot;{example}&quot;
                                </Text>
                              </ListItem>
                            ))}
                          </List>
                        </Box>
                      ))}
                    </SimpleGrid>
                  </Box>

                  <Divider />

                  {/* What is Private Bridging */}
                  <Box>
                    <Heading size="sm" mb={2} color={headingColor}>
                      What is Private Bridging?
                    </Heading>
                    <Text fontSize="sm" color={textColor}>
                      {PRIVACY_BRIDGE_GUIDANCE.SIMPLE}
                    </Text>
                  </Box>

                  <Divider />

                  {/* Wallet Recommendations */}
                  <Box>
                    <Heading size="sm" mb={2} color={headingColor}>
                      Recommended Wallets
                    </Heading>
                    <VStack spacing={2} align="stretch">
                      {ZCASH_WALLETS.slice(0, 2).map((wallet) => (
                        <Box key={wallet.id} p={2} borderRadius="md" bg={exampleBoxBg} borderLeft="3px solid" borderColor="yellow.600">
                          <Flex justify="space-between" align="start" mb={1}>
                            <VStack align="start" spacing={0}>
                              <Heading size="xs" color={headingColor}>
                                {wallet.name}
                              </Heading>
                              {wallet.badge && (
                                <Badge colorScheme="green" fontSize="xs">
                                  {wallet.badge}
                                </Badge>
                              )}
                            </VStack>
                            <Badge colorScheme="blue">{wallet.type}</Badge>
                          </Flex>
                          <Text fontSize="xs" color={textColor} mb={2}>
                            {wallet.description}
                          </Text>
                          <Flex gap={1} flexWrap="wrap">
                            {wallet.platforms.map((p) => (
                              <Badge key={p} size="sm" colorScheme="gray">
                                {p}
                              </Badge>
                            ))}
                          </Flex>
                        </Box>
                      ))}
                    </VStack>
                  </Box>

                  <Divider />

                  {/* Quick FAQ */}
                  <Box>
                    <Heading size="sm" mb={2} color={headingColor}>
                      Common Questions
                    </Heading>
                    <VStack spacing={2} align="stretch">
                      {PRIVACY_FAQ.slice(0, 3).map((faq, idx) => (
                        <Box key={idx} p={2} borderRadius="md" bg={exampleBoxBg}>
                          <Text fontSize="xs" fontWeight="semibold" color={headingColor} mb={1}>
                            Q: {faq.question}
                          </Text>
                          <Text fontSize="xs" color={textColor}>
                            A: {faq.answer}
                          </Text>
                        </Box>
                      ))}
                    </VStack>
                  </Box>

                  <Divider />

                  <Divider />

                  {/* Learn More Links - Tier 2.1 Enhanced */}
                  <Box>
                    <Heading size="sm" mb={2} color={headingColor}>
                      Educational Resources
                    </Heading>
                    <VStack spacing={2} align="stretch">
                      {ZCASH_EDUCATION_LINKS.map((link, idx) => (
                        <Link
                          key={idx}
                          href={link.url}
                          isExternal
                          _hover={{ textDecoration: 'none' }}
                        >
                          <Box
                            p={2}
                            borderRadius="md"
                            bg={exampleBoxBg}
                            _hover={{ bg: hoverBg }}
                            cursor="pointer"
                            transition="all 0.2s"
                          >
                            <Text fontSize="sm" fontWeight="semibold" color={headingColor}>
                              {link.title}
                            </Text>
                            <Text fontSize="xs" color={textColor}>
                              {link.description}
                            </Text>
                          </Box>
                        </Link>
                      ))}
                    </VStack>
                  </Box>

                  <Divider />

                  {/* Privacy Concepts Explained - Tier 2.2 */}
                  <Box>
                    <Heading size="sm" mb={2} color={headingColor}>
                      Privacy Concepts
                    </Heading>
                    <VStack spacing={2} align="stretch">
                      <Box p={2} borderRadius="md" bg={exampleBoxBg}>
                        <HStack spacing={1} mb={1}>
                          <Text fontWeight="semibold" fontSize="xs" color={headingColor}>
                            {PRIVACY_CONCEPTS.SHIELDED.title}
                          </Text>
                        </HStack>
                        <Text fontSize="xs" color={textColor}>
                          {PRIVACY_CONCEPTS.SHIELDED.tooltip}
                          {' '}
                          <Link
                            href={PRIVACY_CONCEPTS.SHIELDED.learnUrl}
                            isExternal
                            color="blue.500"
                            fontSize="xs"
                          >
                            Learn more <Icon as={FaExternalLinkAlt} mx="1px" boxSize={2} />
                          </Link>
                        </Text>
                      </Box>
                      <Box p={2} borderRadius="md" bg={exampleBoxBg}>
                        <HStack spacing={1} mb={1}>
                          <Text fontWeight="semibold" fontSize="xs" color={headingColor}>
                            {PRIVACY_CONCEPTS.UNIFIED_ADDRESS.title}
                          </Text>
                        </HStack>
                        <Text fontSize="xs" color={textColor}>
                          {PRIVACY_CONCEPTS.UNIFIED_ADDRESS.tooltip}
                          {' '}
                          <Link
                            href={PRIVACY_CONCEPTS.UNIFIED_ADDRESS.learnUrl}
                            isExternal
                            color="blue.500"
                            fontSize="xs"
                          >
                            Learn more <Icon as={FaExternalLinkAlt} mx="1px" boxSize={2} />
                          </Link>
                        </Text>
                      </Box>
                    </VStack>
                  </Box>

                  <Divider />

                  {/* Merchant Directory - Tier 3.3 */}
                  <Box>
                    <Heading size="sm" mb={2} color={headingColor}>
                      Where to Spend Zcash
                    </Heading>
                    <VStack spacing={2} align="stretch">
                      {/* Primary Directory */}
                      <Link href={MERCHANT_DIRECTORY.primary.url} isExternal _hover={{ textDecoration: 'none' }}>
                        <Box p={2} borderRadius="md" bg={exampleBoxBg} _hover={{ bg: hoverBg }} cursor="pointer" borderLeft="3px solid" borderColor="blue.500">
                          <Flex justify="space-between" align="start" mb={1}>
                            <Text fontWeight="bold" fontSize="sm" color={headingColor}>
                              {MERCHANT_DIRECTORY.primary.name}
                            </Text>
                            <Badge colorScheme="blue" fontSize="xs">
                              {MERCHANT_DIRECTORY.primary.badge}
                            </Badge>
                          </Flex>
                          <Text fontSize="xs" color={textColor} mb={2}>
                            {MERCHANT_DIRECTORY.primary.description}
                          </Text>
                          <Flex gap={1} flexWrap="wrap">
                            {MERCHANT_DIRECTORY.primary.categories.map((cat) => (
                              <Badge key={cat} size="sm" colorScheme="purple">
                                {cat}
                              </Badge>
                            ))}
                          </Flex>
                        </Box>
                      </Link>

                      {/* Secondary Resources */}
                      {MERCHANT_DIRECTORY.secondaryResources.slice(0, 2).map((resource) => (
                        <Link key={resource.name} href={resource.url} isExternal _hover={{ textDecoration: 'none' }}>
                          <Box p={2} borderRadius="md" bg={exampleBoxBg} _hover={{ bg: hoverBg }} cursor="pointer">
                            <Flex justify="space-between" align="start" mb={1}>
                              <VStack align="start" spacing={0}>
                                <Text fontWeight="semibold" fontSize="xs" color={headingColor}>
                                  {resource.name}
                                </Text>
                                <Text fontSize="xs" color={textColor}>
                                  {resource.description}
                                </Text>
                              </VStack>
                              <Badge colorScheme="gray" fontSize="xs">
                                {resource.category}
                              </Badge>
                            </Flex>
                          </Box>
                        </Link>
                      ))}
                    </VStack>
                  </Box>
                </VStack>
              </TabPanel>
            </TabPanels>
          </Tabs>
        </ModalBody>

        <ModalFooter justifyContent="center" pt={2} pb={3}>
          <Button colorScheme="blue" onClick={onClose} size="sm" width="120px">
            Got it!
          </Button>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
};

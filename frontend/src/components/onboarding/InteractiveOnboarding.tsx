import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Box,
  Button,
  Container,
  Flex,
  Heading,
  Text,
  VStack,
  HStack,
  Icon,
  Image,
  Progress,
  Badge,
  useDisclosure,
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalFooter,
  ModalCloseButton,
  Tooltip,
  Drawer,
  DrawerBody,
  DrawerHeader,
  DrawerOverlay,
  DrawerContent,
  DrawerCloseButton,
  Tabs,
  TabList,
  TabPanels,
  Tab,
  TabPanel,
  Radio,
  RadioGroup,
  Checkbox,
  SimpleGrid,
  useColorModeValue,
  useToast,
  IconButton,
  Collapse,
  Divider,
  Kbd,
  Tag,
  Popover,
  PopoverTrigger,
  PopoverContent,
  PopoverHeader,
  PopoverBody,
  PopoverArrow,
  PopoverCloseButton,
  Slider,
  SliderTrack,
  SliderFilledTrack,
  SliderThumb,
  Select,
  Skeleton,
  Input,
  FormControl,
  FormLabel,
  Alert,
  AlertIcon,
  AlertTitle,
  AlertDescription,
  Wrap,
  WrapItem,
  Spinner,
  OrderedList,
  ListItem,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
} from '@chakra-ui/react';
import { motion, AnimatePresence, useAnimation } from 'framer-motion';
import {
  FaArrowRight,
  FaArrowLeft,
  FaTimes,
  FaCheck,
  FaCog,
  FaGraduationCap,
  FaLightbulb,
  FaRocket,
  FaStar,
  FaTrophy,
  FaInfoCircle,
  FaExchangeAlt,
  FaLink,
  FaWallet,
  FaCoins,
  FaChartPie,
  FaNetworkWired,
  FaShieldAlt,
  FaGlobe,
  FaUserGraduate,
  FaRegLightbulb,
  FaRegCheckCircle,
  FaRegClock,
  FaRegStar,
  FaRegBookmark,
  FaRegQuestionCircle,
  FaRegThumbsUp,
  FaPlay,
  FaPause,
  FaCheckCircle,
  FaGasPump,
  FaQuestion,
} from 'react-icons/fa';
import { ChainUtils } from '../../utils/chainUtils';
import { axelarServiceV2 } from '../../services/enhanced/axelarServiceV2';
import { useLocalStorage } from '../../hooks/useLocalStorage';

// ======== TypeScript Interfaces ========

export interface OnboardingStep {
  id: string;
  title: string;
  description: string;
  content: React.ReactNode;
  icon: React.ElementType;
  completionCriteria?: () => boolean;
  requiredInteraction?: boolean;
  experienceLevel: 'beginner' | 'intermediate' | 'advanced';
  category: 'intro' | 'crosschain' | 'axelar' | 'defi' | 'portfolio' | 'commands';
  estimatedTime: number; // in seconds
  reward?: {
    type: 'achievement' | 'feature' | 'tip';
    title: string;
    description: string;
    icon: React.ElementType;
  };
}

export interface OnboardingPath {
  id: string;
  title: string;
  description: string;
  icon: React.ElementType;
  stepIds: string[];
  experienceLevel: 'beginner' | 'intermediate' | 'advanced';
  estimatedTime: number; // in minutes
}

export interface OnboardingPreferences {
  experienceLevel: 'beginner' | 'intermediate' | 'advanced';
  interests: string[];
  completedSteps: string[];
  currentPath?: string;
  currentStep?: string;
  achievements: string[];
  lastActiveDate?: string;
  dismissedUntil?: string;
}

export interface OnboardingAchievement {
  id: string;
  title: string;
  description: string;
  icon: React.ElementType;
  unlockedAt?: string;
  criteria: (preferences: OnboardingPreferences) => boolean;
}

export interface InteractiveOnboardingProps {
  isOpen?: boolean;
  onClose?: () => void;
  initialStep?: string;
  initialPath?: string;
  onComplete?: (preferences: OnboardingPreferences) => void;
  onStepComplete?: (stepId: string) => void;
  showFloatingButton?: boolean;
}

// ======== Animation Variants ========

const fadeIn = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: { duration: 0.5 } }
};

const slideUp = {
  hidden: { y: 20, opacity: 0 },
  visible: { y: 0, opacity: 1, transition: { duration: 0.5 } }
};

const slideRight = {
  hidden: { x: -20, opacity: 0 },
  visible: { x: 0, opacity: 1, transition: { duration: 0.4 } }
};

const pulse = {
  initial: { scale: 1 },
  animate: { 
    scale: [1, 1.05, 1],
    transition: { duration: 1.5, repeat: Infinity }
  }
};

const staggerChildren = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1
    }
  }
};

// ======== Helper Components ========

const MotionBox = motion(Box);
const MotionFlex = motion(Flex);
const MotionText = motion(Text);
const MotionHeading = motion(Heading);
const MotionButton = motion(Button);
const MotionIcon = motion(Icon);

const StepProgressBar: React.FC<{ 
  currentStepIndex: number; 
  totalSteps: number;
  completedSteps: number;
}> = ({ currentStepIndex, totalSteps, completedSteps }) => {
  const progress = (completedSteps / totalSteps) * 100;
  
  return (
    <Box w="100%" mb={4}>
      <Flex justify="space-between" mb={2}>
        <Text fontSize="sm" fontWeight="medium">Progress</Text>
        <HStack spacing={2}>
          <Badge colorScheme="green">{completedSteps}/{totalSteps} completed</Badge>
          <Text fontSize="sm" fontWeight="bold">{Math.round(progress)}%</Text>
        </HStack>
      </Flex>
      <Box position="relative" h="8px" w="100%" bg="gray.100" borderRadius="full" overflow="hidden">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${progress}%` }}
          transition={{ duration: 0.5 }}
          style={{
            height: '100%',
            background: 'var(--chakra-colors-blue-500)',
            borderRadius: 'var(--chakra-radii-full)'
          }}
        />
        <Box
          position="absolute"
          top="0"
          left={`${(currentStepIndex / totalSteps) * 100}%`}
          transform="translateX(-50%)"
          w="16px"
          h="16px"
          bg="blue.500"
          borderRadius="full"
          mt="-4px"
          border="2px solid white"
        />
      </Box>
    </Box>
  );
};

const AchievementBadge: React.FC<{ 
  achievement: OnboardingAchievement;
  isUnlocked: boolean;
  onClick?: () => void;
}> = ({ achievement, isUnlocked, onClick }) => {
  const bgColor = useColorModeValue(
    isUnlocked ? 'yellow.100' : 'gray.100',
    isUnlocked ? 'yellow.900' : 'gray.700'
  );
  
  const iconColor = useColorModeValue(
    isUnlocked ? 'yellow.500' : 'gray.400',
    isUnlocked ? 'yellow.300' : 'gray.500'
  );
  
  return (
    <MotionBox
      p={3}
      borderRadius="lg"
      bg={bgColor}
      cursor={onClick ? "pointer" : "default"}
      onClick={onClick}
      whileHover={{ scale: 1.05 }}
      whileTap={{ scale: 0.98 }}
      position="relative"
      overflow="hidden"
    >
      {isUnlocked && (
        <Badge 
          position="absolute" 
          top={2} 
          right={2} 
          colorScheme="green"
          fontSize="xs"
        >
          Unlocked
        </Badge>
      )}
      
      <VStack spacing={2} align="center">
        <Icon 
          as={achievement.icon} 
          boxSize={8} 
          color={iconColor} 
        />
        <Text fontWeight="medium" textAlign="center">{achievement.title}</Text>
        {isUnlocked && achievement.unlockedAt && (
          <Text fontSize="xs" color="gray.500">
            Unlocked on {new Date(achievement.unlockedAt).toLocaleDateString()}
          </Text>
        )}
      </VStack>
    </MotionBox>
  );
};

const InteractiveDemoCard: React.FC<{
  title: string;
  description: string;
  icon: React.ElementType;
  children: React.ReactNode;
  isCompleted: boolean;
  onComplete?: () => void;
}> = ({ title, description, icon, children, isCompleted, onComplete }) => {
  const bgColor = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.700');
  
  return (
    <Box
      p={5}
      borderWidth="1px"
      borderRadius="lg"
      borderColor={borderColor}
      bg={bgColor}
      boxShadow="sm"
      position="relative"
      overflow="hidden"
    >
      {isCompleted && (
        <Box
          position="absolute"
          top={0}
          right={0}
          bg="green.500"
          color="white"
          px={2}
          py={1}
          borderBottomLeftRadius="md"
        >
          <HStack spacing={1}>
            <Icon as={FaCheck} boxSize={3} />
            <Text fontSize="xs" fontWeight="bold">Completed</Text>
          </HStack>
        </Box>
      )}
      
      <VStack spacing={4} align="stretch">
        <HStack spacing={3}>
          <Icon as={icon} boxSize={6} color="blue.500" />
          <VStack spacing={0} align="start">
            <Heading size="md">{title}</Heading>
            <Text color="gray.500">{description}</Text>
          </VStack>
        </HStack>
        
        <Box>{children}</Box>
        
        {onComplete && !isCompleted && (
          <Button 
            rightIcon={<Icon as={FaCheck} />} 
            colorScheme="blue" 
            onClick={onComplete}
            alignSelf="flex-end"
          >
            Mark as Complete
          </Button>
        )}
      </VStack>
    </Box>
  );
};

const ConceptCard: React.FC<{
  title: string;
  description: string;
  icon: React.ElementType;
  imageUrl?: string;
  learnMoreUrl?: string;
}> = ({ title, description, icon, imageUrl, learnMoreUrl }) => {
  return (
    <MotionBox
      p={5}
      borderWidth="1px"
      borderRadius="lg"
      borderColor="gray.200"
      bg="white"
      boxShadow="sm"
      whileHover={{ y: -5, boxShadow: '0 10px 20px rgba(0,0,0,0.1)' }}
      transition={{ duration: 0.3 }}
    >
      <VStack spacing={4} align="start">
        <HStack spacing={3}>
          <Icon as={icon} boxSize={6} color="blue.500" />
          <Heading size="md">{title}</Heading>
        </HStack>
        
        {imageUrl && (
          <Image 
            src={imageUrl} 
            alt={title} 
            borderRadius="md" 
            w="100%" 
            maxH="150px" 
            objectFit="cover" 
          />
        )}
        
        <Text>{description}</Text>
        
        {learnMoreUrl && (
          <Button 
            as="a" 
            href={learnMoreUrl} 
            target="_blank" 
            variant="link" 
            colorScheme="blue" 
            rightIcon={<Icon as={FaArrowRight} />}
          >
            Learn more
          </Button>
        )}
      </VStack>
    </MotionBox>
  );
};

// ======== Onboarding Content ========

// Define onboarding steps
const onboardingSteps: OnboardingStep[] = [
  // Introduction Steps
  {
    id: 'welcome',
    title: 'Welcome to SNEL',
    description: 'Your AI-powered cross-chain DeFi assistant',
    icon: FaRocket,
    experienceLevel: 'beginner',
    category: 'intro',
    estimatedTime: 60,
    content: (
      <VStack spacing={6} align="stretch">
        <MotionBox
          variants={fadeIn}
          initial="hidden"
          animate="visible"
          textAlign="center"
          py={8}
        >
          <Heading size="xl" mb={4}>Welcome to SNEL</Heading>
          <Text fontSize="lg" color="gray.600" maxW="600px" mx="auto">
            Your AI-powered assistant for seamless DeFi operations across 16+ blockchain networks.
          </Text>
        </MotionBox>
        
        <MotionBox variants={slideUp} initial="hidden" animate="visible">
          <SimpleGrid columns={{ base: 1, md: 2 }} spacing={5}>
            <Box p={5} borderWidth="1px" borderRadius="lg" bg="white">
              <VStack spacing={3} align="start">
                <Icon as={FaLightbulb} color="yellow.500" boxSize={8} />
                <Heading size="md">Smart & Natural</Heading>
                <Text>
                  Use natural language commands like "swap 1 ETH for USDC on Base" instead of navigating complex interfaces.
                </Text>
              </VStack>
            </Box>
            
            <Box p={5} borderWidth="1px" borderRadius="lg" bg="white">
              <VStack spacing={3} align="start">
                <Icon as={FaLink} color="purple.500" boxSize={8} />
                <Heading size="md">Cross-Chain Capable</Heading>
                <Text>
                  Seamlessly bridge assets between 16+ networks with Axelar's secure cross-chain infrastructure.
                </Text>
              </VStack>
            </Box>
            
            <Box p={5} borderWidth="1px" borderRadius="lg" bg="white">
              <VStack spacing={3} align="start">
                <Icon as={FaWallet} color="green.500" boxSize={8} />
                <Heading size="md">Portfolio Management</Heading>
                <Text>
                  Track and analyze your assets across multiple chains in one unified interface.
                </Text>
              </VStack>
            </Box>
            
            <Box p={5} borderWidth="1px" borderRadius="lg" bg="white">
              <VStack spacing={3} align="start">
                <Icon as={FaShieldAlt} color="blue.500" boxSize={8} />
                <Heading size="md">Secure & Non-custodial</Heading>
                <Text>
                  SNEL never holds your assets. All transactions are executed directly from your connected wallet.
                </Text>
              </VStack>
            </Box>
          </SimpleGrid>
        </MotionBox>
      </VStack>
    )
  },
  {
    id: 'experience-level',
    title: 'Set Your Experience Level',
    description: 'Customize your onboarding experience',
    icon: FaUserGraduate,
    experienceLevel: 'beginner',
    category: 'intro',
    estimatedTime: 30,
    content: ({ onPreferenceChange, preferences }: any) => (
      <VStack spacing={8} align="stretch" py={4}>
        <Heading size="md">What's your experience level with DeFi?</Heading>
        
        <RadioGroup 
          onChange={(val) => onPreferenceChange('experienceLevel', val)} 
          value={preferences.experienceLevel}
        >
          <VStack spacing={4} align="stretch">
            <Box 
              p={4} 
              borderWidth="1px" 
              borderRadius="md" 
              borderColor={preferences.experienceLevel === 'beginner' ? 'blue.500' : 'gray.200'}
              bg={preferences.experienceLevel === 'beginner' ? 'blue.50' : 'white'}
            >
              <Radio value="beginner" colorScheme="blue">
                <VStack align="start" spacing={1}>
                  <Heading size="sm">Beginner</Heading>
                  <Text fontSize="sm">I'm new to DeFi and cross-chain operations</Text>
                </VStack>
              </Radio>
            </Box>
            
            <Box 
              p={4} 
              borderWidth="1px" 
              borderRadius="md" 
              borderColor={preferences.experienceLevel === 'intermediate' ? 'blue.500' : 'gray.200'}
              bg={preferences.experienceLevel === 'intermediate' ? 'blue.50' : 'white'}
            >
              <Radio value="intermediate" colorScheme="blue">
                <VStack align="start" spacing={1}>
                  <Heading size="sm">Intermediate</Heading>
                  <Text fontSize="sm">I've used DeFi protocols but am new to cross-chain operations</Text>
                </VStack>
              </Radio>
            </Box>
            
            <Box 
              p={4} 
              borderWidth="1px" 
              borderRadius="md" 
              borderColor={preferences.experienceLevel === 'advanced' ? 'blue.500' : 'gray.200'}
              bg={preferences.experienceLevel === 'advanced' ? 'blue.50' : 'white'}
            >
              <Radio value="advanced" colorScheme="blue">
                <VStack align="start" spacing={1}>
                  <Heading size="sm">Advanced</Heading>
                  <Text fontSize="sm">I'm experienced with DeFi and cross-chain operations</Text>
                </VStack>
              </Radio>
            </Box>
          </VStack>
        </RadioGroup>
        
        <Box>
          <Heading size="md" mb={4}>What are you most interested in?</Heading>
          <SimpleGrid columns={{ base: 1, md: 2 }} spacing={3}>
            {[
              { id: 'swaps', label: 'Token Swaps', icon: FaExchangeAlt },
              { id: 'bridges', label: 'Cross-Chain Bridges', icon: FaLink },
              { id: 'portfolio', label: 'Portfolio Management', icon: FaChartPie },
              { id: 'yields', label: 'Yield Opportunities', icon: FaCoins },
              { id: 'security', label: 'Security Best Practices', icon: FaShieldAlt },
              { id: 'automation', label: 'Automated Strategies', icon: FaRocket }
            ].map(interest => (
              <Checkbox
                key={interest.id}
                isChecked={preferences.interests?.includes(interest.id)}
                onChange={(e) => {
                  const newInterests = e.target.checked
                    ? [...(preferences.interests || []), interest.id]
                    : (preferences.interests || []).filter(i => i !== interest.id);
                  onPreferenceChange('interests', newInterests);
                }}
                colorScheme="blue"
              >
                <HStack>
                  <Icon as={interest.icon} color="blue.500" />
                  <Text>{interest.label}</Text>
                </HStack>
              </Checkbox>
            ))}
          </SimpleGrid>
        </Box>
      </VStack>
    ),
    requiredInteraction: true
  },
  {
    id: 'natural-language',
    title: 'Natural Language Commands',
    description: 'Learn how to interact with SNEL using simple text commands',
    icon: FaRegLightbulb,
    experienceLevel: 'beginner',
    category: 'commands',
    estimatedTime: 120,
    content: (
      <VStack spacing={6} align="stretch">
        <Text>
          SNEL understands natural language commands, making complex DeFi operations as simple as typing a sentence.
          Here are some examples of commands you can use:
        </Text>
        
        <SimpleGrid columns={{ base: 1, md: 2 }} spacing={4}>
          {[
            {
              command: "swap 1 ETH for USDC on Base",
              description: "Exchange ETH for USDC on the Base network",
              category: "Swaps"
            },
            {
              command: "bridge 100 USDC from Ethereum to Arbitrum",
              description: "Transfer USDC from Ethereum to Arbitrum",
              category: "Cross-Chain"
            },
            {
              command: "show my portfolio",
              description: "Display your portfolio across all chains",
              category: "Portfolio"
            },
            {
              command: "what's the best yield for USDC?",
              description: "Find the highest yield opportunities for USDC",
              category: "Yields"
            },
            {
              command: "swap 0.5 ETH for WBTC on Optimism",
              description: "Exchange ETH for WBTC on Optimism",
              category: "Swaps"
            },
            {
              command: "bridge 50 USDT from Polygon to Avalanche",
              description: "Transfer USDT from Polygon to Avalanche",
              category: "Cross-Chain"
            }
          ].map((example, index) => (
            <MotionBox
              key={index}
              p={4}
              borderWidth="1px"
              borderRadius="md"
              bg="white"
              variants={slideRight}
              initial="hidden"
              animate="visible"
              custom={index}
              whileHover={{ y: -2, boxShadow: 'md' }}
            >
              <Badge colorScheme="purple" mb={2}>{example.category}</Badge>
              <Text fontWeight="bold" fontFamily="mono" mb={2}>
                "{example.command}"
              </Text>
              <Text fontSize="sm" color="gray.600">{example.description}</Text>
            </MotionBox>
          ))}
        </SimpleGrid>
        
        <InteractiveDemoCard
          title="Try It Yourself"
          description="Practice writing natural language commands"
          icon={FaPlay}
          isCompleted={false}
          onComplete={() => {}}
        >
          <Box borderWidth="1px" borderRadius="md" p={4} bg="gray.50" mb={4}>
            <Text mb={2} fontWeight="medium">Write a command to:</Text>
            <Text color="blue.600">Swap 0.1 ETH for DAI on Arbitrum</Text>
            
            <Input
              placeholder="Type your command here..."
              mt={4}
              variant="filled"
              onChange={(e) => {
                const input = e.target.value.toLowerCase();
                const expected = "swap 0.1 eth for dai on arbitrum";
                // Simple fuzzy matching
                if (input.includes("swap") && 
                    input.includes("0.1") && 
                    input.includes("eth") && 
                    input.includes("dai") && 
                    input.includes("arbitrum")) {
                  // Success logic would go here
                }
              }}
            />
          </Box>
        </InteractiveDemoCard>
        
        <Box p={4} bg="blue.50" borderRadius="md">
          <HStack spacing={3}>
            <Icon as={FaInfoCircle} color="blue.500" boxSize={5} />
            <Text fontWeight="medium">Pro Tip</Text>
          </HStack>
          <Text mt={2}>
            You can also ask SNEL questions like "What is the price of ETH?" or "Explain impermanent loss" to get information without executing transactions.
          </Text>
        </Box>
      </VStack>
    ),
    reward: {
      type: 'achievement',
      title: 'Command Master',
      description: 'Learned how to use natural language commands',
      icon: FaRegLightbulb
    }
  },
  
  // Cross-chain Concepts
  {
    id: 'cross-chain-intro',
    title: 'Cross-Chain 101',
    description: 'Understanding the basics of cross-chain operations',
    icon: FaLink,
    experienceLevel: 'beginner',
    category: 'crosschain',
    estimatedTime: 180,
    content: (
      <VStack spacing={6} align="stretch">
        <MotionBox variants={fadeIn} initial="hidden" animate="visible">
          <Heading size="md" mb={4}>What are Cross-Chain Operations?</Heading>
          <Text mb={4}>
            Cross-chain operations allow you to move assets and data between different blockchain networks that would otherwise be isolated from each other.
          </Text>
          
          <SimpleGrid columns={{ base: 1, md: 3 }} spacing={6} mb={8}>
            <ConceptCard
              title="Blockchain Isolation"
              description="Each blockchain network operates independently with its own validators, tokens, and rules."
              icon={FaNetworkWired}
            />
            <ConceptCard
              title="Bridging"
              description="Bridges connect blockchains, allowing assets to move between them securely."
              icon={FaLink}
            />
            <ConceptCard
              title="Interoperability"
              description="The ability of different blockchain systems to exchange and make use of information."
              icon={FaExchangeAlt}
            />
          </SimpleGrid>
        </MotionBox>
        
        <Divider my={4} />
        
        <MotionBox variants={slideUp} initial="hidden" animate="visible">
          <Heading size="md" mb={4}>Why Use Cross-Chain Operations?</Heading>
          
          <SimpleGrid columns={{ base: 1, md: 2 }} spacing={6} mb={8}>
            <Box p={4} borderWidth="1px" borderRadius="md" bg="white">
              <Heading size="sm" mb={3}>Access to Different Ecosystems</Heading>
              <Text>
                Each blockchain has unique DeFi protocols, NFT marketplaces, and applications. Cross-chain operations let you access all of them without selling your assets.
              </Text>
            </Box>
            
            <Box p={4} borderWidth="1px" borderRadius="md" bg="white">
              <Heading size="sm" mb={3}>Lower Fees</Heading>
              <Text>
                Move from high-fee networks like Ethereum to lower-fee alternatives like Polygon or Arbitrum for cheaper transactions.
              </Text>
            </Box>
            
            <Box p={4} borderWidth="1px" borderRadius="md" bg="white">
              <Heading size="sm" mb={3}>Better Yields</Heading>
              <Text>
                Find the best yield opportunities across all chains instead of being limited to a single ecosystem.
              </Text>
            </Box>
            
            <Box p={4} borderWidth="1px" borderRadius="md" bg="white">
              <Heading size="sm" mb={3}>Risk Diversification</Heading>
              <Text>
                Spread your assets across multiple chains to reduce exposure to chain-specific risks.
              </Text>
            </Box>
          </SimpleGrid>
        </MotionBox>
        
        <Divider my={4} />
        
        <MotionBox variants={slideUp} initial="hidden" animate="visible" delay={0.2}>
          <Heading size="md" mb={4}>How Cross-Chain Operations Work</Heading>
          
          <Box 
            p={5} 
            borderWidth="1px" 
            borderRadius="lg" 
            bg="white"
            mb={6}
          >
            <VStack spacing={4} align="stretch">
              <HStack spacing={4}>
                <Box 
                  w="50px" 
                  h="50px" 
                  borderRadius="full" 
                  bg="blue.100" 
                  display="flex" 
                  alignItems="center" 
                  justifyContent="center"
                >
                  <Text fontWeight="bold">1</Text>
                </Box>
                <VStack align="start" spacing={1}>
                  <Heading size="sm">Lock or Burn</Heading>
                  <Text>Assets are locked in a smart contract on the source chain or burned (destroyed).</Text>
                </VStack>
              </HStack>
              
              <Icon as={FaArrowDown} alignSelf="center" color="gray.400" />
              
              <HStack spacing={4}>
                <Box 
                  w="50px" 
                  h="50px" 
                  borderRadius="full" 
                  bg="purple.100" 
                  display="flex" 
                  alignItems="center" 
                  justifyContent="center"
                >
                  <Text fontWeight="bold">2</Text>
                </Box>
                <VStack align="start" spacing={1}>
                  <Heading size="sm">Verification</Heading>
                  <Text>The bridge protocol verifies the transaction on the source chain.</Text>
                </VStack>
              </HStack>
              
              <Icon as={FaArrowDown} alignSelf="center" color="gray.400" />
              
              <HStack spacing={4}>
                <Box 
                  w="50px" 
                  h="50px" 
                  borderRadius="full" 
                  bg="green.100" 
                  display="flex" 
                  alignItems="center" 
                  justifyContent="center"
                >
                  <Text fontWeight="bold">3</Text>
                </Box>
                <VStack align="start" spacing={1}>
                  <Heading size="sm">Mint or Release</Heading>
                  <Text>Equivalent assets are minted or released from a smart contract on the destination chain.</Text>
                </VStack>
              </HStack>
            </VStack>
          </Box>
          
          <Alert status="info" borderRadius="md">
            <AlertIcon />
            <Box>
              <AlertTitle>Important to Know</AlertTitle>
              <AlertDescription>
                Cross-chain operations typically take longer than regular transactions (5-20 minutes) because they require confirmations on both chains and processing by the bridge protocol.
              </AlertDescription>
            </Box>
          </Alert>
        </MotionBox>
      </VStack>
    ),
    reward: {
      type: 'achievement',
      title: 'Chain Explorer',
      description: 'Learned the basics of cross-chain operations',
      icon: FaLink
    }
  },
  {
    id: 'axelar-benefits',
    title: 'Axelar Network Benefits',
    description: 'Why SNEL uses Axelar for secure cross-chain operations',
    icon: FaShieldAlt,
    experienceLevel: 'beginner',
    category: 'axelar',
    estimatedTime: 180,
    content: (
      <VStack spacing={8} align="stretch">
        <MotionBox variants={fadeIn} initial="hidden" animate="visible">
          <HStack spacing={4} mb={4}>
            <Icon as={FaShieldAlt} boxSize={8} color="blue.500" />
            <Heading size="lg">Axelar Network</Heading>
          </HStack>
          
          <Text mb={6}>
            SNEL uses Axelar Network as its primary cross-chain infrastructure provider. Axelar is a secure and decentralized cross-chain communication network that enables seamless asset transfers and message passing between blockchains.
          </Text>
          
          <SimpleGrid columns={{ base: 1, md: 2 }} spacing={6}>
            <Box p={5} borderWidth="1px" borderRadius="lg" bg="white" boxShadow="sm">
              <VStack spacing={3} align="start">
                <Icon as={FaShieldAlt} color="blue.500" boxSize={6} />
                <Heading size="md">Proof-of-Stake Security</Heading>
                <Text>
                  Axelar is secured by a decentralized network of validators using Proof-of-Stake consensus, providing robust security for cross-chain operations.
                </Text>
              </VStack>
            </Box>
            
            <Box p={5} borderWidth="1px" borderRadius="lg" bg="white" boxShadow="sm">
              <VStack spacing={3} align="start">
                <Icon as={FaGlobe} color="blue.500" boxSize={6} />
                <Heading size="md">Wide Chain Support</Heading>
                <Text>
                  Supports 16+ major blockchain networks including Ethereum, Polygon, Avalanche, Arbitrum, Optimism, Base, and more.
                </Text>
              </VStack>
            </Box>
            
            <Box p={5} borderWidth="1px" borderRadius="lg" bg="white" boxShadow="sm">
              <VStack spacing={3} align="start">
                <Icon as={FaExchangeAlt} color="blue.500" boxSize={6} />
                <Heading size="md">General Message Passing</Heading>
                <Text>
                  Enables not just token transfers but also cross-chain smart contract calls and message passing for advanced use cases.
                </Text>
              </VStack>
            </Box>
            
            <Box p={5} borderWidth="1px" borderRadius="lg" bg="white" boxShadow="sm">
              <VStack spacing={3} align="start">
                <Icon as={FaRegCheckCircle} color="blue.500" boxSize={6} />
                <Heading size="md">Transaction Recovery</Heading>
                <Text>
                  Built-in mechanisms to recover failed transactions, ensuring your assets don't get stuck during cross-chain transfers.
                </Text>
              </VStack>
            </Box>
          </SimpleGrid>
        </MotionBox>
        
        <Divider my={4} />
        
        <MotionBox variants={slideUp} initial="hidden" animate="visible">
          <Heading size="md" mb={4}>How Axelar Compares to Other Bridges</Heading>
          
          <Box overflowX="auto">
            <Table variant="simple" mb={6}>
              <Thead>
                <Tr>
                  <Th>Feature</Th>
                  <Th>Axelar</Th>
                  <Th>Typical Bridges</Th>
                </Tr>
              </Thead>
              <Tbody>
                <Tr>
                  <Td>Security Model</Td>
                  <Td>Proof-of-Stake with 30+ validators</Td>
                  <Td>Often centralized or with few validators</Td>
                </Tr>
                <Tr>
                  <Td>Chain Support</Td>
                  <Td>16+ major networks</Td>
                  <Td>Usually limited to 2-5 chains</Td>
                </Tr>
                <Tr>
                  <Td>Transaction Recovery</Td>
                  <Td>Built-in recovery mechanisms</Td>
                  <Td>Limited or no recovery options</Td>
                </Tr>
                <Tr>
                  <Td>Message Passing</Td>
                  <Td>Full General Message Passing (GMP)</Td>
                  <Td>Often limited to token transfers only</Td>
                </Tr>
                <Tr>
                  <Td>Developer Ecosystem</Td>
                  <Td>Extensive SDK and developer tools</Td>
                  <Td>Varies, often limited</Td>
                </Tr>
              </Tbody>
            </Table>
          </Box>
        </MotionBox>
        
        <Divider my={4} />
        
        <MotionBox variants={slideUp} initial="hidden" animate="visible" delay={0.2}>
          <Heading size="md" mb={4}>How SNEL Leverages Axelar</Heading>
          
          <SimpleGrid columns={{ base: 1, md: 2 }} spacing={6} mb={6}>
            <Box p={4} borderWidth="1px" borderRadius="md" bg="white">
              <VStack align="start" spacing={3}>
                <Icon as={FaExchangeAlt} color="blue.500" boxSize={5} />
                <Heading size="sm">Seamless Cross-Chain Swaps</Heading>
                <Text fontSize="sm">
                  SNEL combines Axelar's cross-chain capabilities with DEX aggregators to enable one-command cross-chain swaps.
                </Text>
              </VStack>
            </Box>
            
            <Box p={4} borderWidth="1px" borderRadius="md" bg="white">
              <VStack align="start" spacing={3}>
                <Icon as={FaChartPie} color="blue.500" boxSize={5} />
                <Heading size="sm">Portfolio Rebalancing</Heading>
                <Text fontSize="sm">
                  Automatically rebalance your portfolio across chains based on your investment strategy.
                </Text>
              </VStack>
            </Box>
            
            <Box p={4} borderWidth="1px" borderRadius="md" bg="white">
              <VStack align="start" spacing={3}>
                <Icon as={FaRegClock} color="blue.500" boxSize={5} />
                <Heading size="sm">Real-time Transaction Tracking</Heading>
                <Text fontSize="sm">
                  Monitor the status of your cross-chain transactions with detailed progress updates.
                </Text>
              </VStack>
            </Box>
            
            <Box p={4} borderWidth="1px" borderRadius="md" bg="white">
              <VStack align="start" spacing={3}>
                <Icon as={FaCoins} color="blue.500" boxSize={5} />
                <Heading size="sm">Cross-Chain Yield Strategies</Heading>
                <Text fontSize="sm">
                  Find and execute yield strategies across multiple chains from a single interface.
                </Text>
              </VStack>
            </Box>
          </SimpleGrid>
          
          <InteractiveDemoCard
            title="Explore Supported Chains"
            description="See which chains are supported by Axelar and SNEL"
            icon={FaGlobe}
            isCompleted={false}
            onComplete={() => {}}
          >
            <SimpleGrid columns={{ base: 2, md: 4 }} spacing={4}>
              {[
                { name: 'Ethereum', id: 1, icon: '🔷' },
                { name: 'Polygon', id: 137, icon: '🟣' },
                { name: 'Arbitrum', id: 42161, icon: '🔵' },
                { name: 'Optimism', id: 10, icon: '🔴' },
                { name: 'Avalanche', id: 43114, icon: '🔺' },
                { name: 'Base', id: 8453, icon: '🔷' },
                { name: 'Binance', id: 56, icon: '🟡' },
                { name: 'Linea', id: 59144, icon: '⚪' }
              ].map(chain => (
                <Box 
                  key={chain.id}
                  p={3}
                  borderWidth="1px"
                  borderRadius="md"
                  bg="white"
                  textAlign="center"
                >
                  <Text fontSize="2xl" mb={1}>{chain.icon}</Text>
                  <Text fontWeight="medium">{chain.name}</Text>
                  <Text fontSize="xs" color="gray.500">Chain ID: {chain.id}</Text>
                </Box>
              ))}
            </SimpleGrid>
          </InteractiveDemoCard>
        </MotionBox>
      </VStack>
    ),
    reward: {
      type: 'achievement',
      title: 'Axelar Expert',
      description: 'Learned about Axelar Network and its benefits',
      icon: FaShieldAlt
    }
  },
  
  // Interactive demos
  {
    id: 'cross-chain-demo',
    title: 'Cross-Chain Transfer Demo',
    description: 'See how cross-chain transfers work in practice',
    icon: FaExchangeAlt,
    experienceLevel: 'intermediate',
    category: 'crosschain',
    estimatedTime: 300,
    content: ({ onStepComplete }: any) => {
      const [sourceChain, setSourceChain] = useState('ethereum');
      const [destChain, setDestChain] = useState('arbitrum');
      const [asset, setAsset] = useState('USDC');
      const [amount, setAmount] = useState('100');
      const [showDemo, setShowDemo] = useState(false);
      const [demoTxHash, setDemoTxHash] = useState('0x123...abc');
      
      const startDemo = () => {
        setShowDemo(true);
        // In a real implementation, this would trigger the demo
        setTimeout(() => {
          if (onStepComplete) {
            onStepComplete('cross-chain-demo');
          }
        }, 5000);
      };
      
      return (
        <VStack spacing={6} align="stretch">
          <Text>
            This interactive demo shows you how cross-chain transfers work using Axelar Network.
            Configure your transfer parameters below and start the demo to see the process in action.
          </Text>
          
          {!showDemo ? (
            <Box p={6} borderWidth="1px" borderRadius="lg" bg="white">
              <VStack spacing={5} align="stretch">
                <FormControl>
                  <FormLabel>Source Chain</FormLabel>
                  <Select 
                    value={sourceChain} 
                    onChange={(e) => setSourceChain(e.target.value)}
                  >
                    <option value="ethereum">Ethereum</option>
                    <option value="polygon">Polygon</option>
                    <option value="avalanche">Avalanche</option>
                    <option value="base">Base</option>
                  </Select>
                </FormControl>
                
                <FormControl>
                  <FormLabel>Destination Chain</FormLabel>
                  <Select 
                    value={destChain} 
                    onChange={(e) => setDestChain(e.target.value)}
                  >
                    <option value="arbitrum">Arbitrum</option>
                    <option value="optimism">Optimism</option>
                    <option value="base">Base</option>
                    <option value="polygon">Polygon</option>
                  </Select>
                </FormControl>
                
                <FormControl>
                  <FormLabel>Asset</FormLabel>
                  <Select 
                    value={asset} 
                    onChange={(e) => setAsset(e.target.value)}
                  >
                    <option value="USDC">USDC</option>
                    <option value="USDT">USDT</option>
                    <option value="ETH">ETH</option>
                    <option value="WETH">WETH</option>
                  </Select>
                </FormControl>
                
                <FormControl>
                  <FormLabel>Amount</FormLabel>
                  <Input 
                    type="number" 
                    value={amount} 
                    onChange={(e) => setAmount(e.target.value)}
                  />
                </FormControl>
                
                <Button 
                  colorScheme="blue" 
                  size="lg" 
                  rightIcon={<Icon as={FaPlay} />}
                  onClick={startDemo}
                >
                  Start Demo
                </Button>
              </VStack>
            </Box>
          ) : (
            <Box>
              <Alert status="info" mb={4}>
                <AlertIcon />
                <AlertTitle>Demo Mode</AlertTitle>
                <AlertDescription>
                  This is a simulated demo. No actual transaction is being executed.
                </AlertDescription>
              </Alert>
              
              {/* This would be replaced with the actual CrosschainTransactionTracker component */}
              <Box 
                p={6} 
                borderWidth="1px" 
                borderRadius="lg" 
                bg="white"
              >
                <VStack spacing={4} align="stretch">
                  <Heading size="md">Cross-Chain Transfer Demo</Heading>
                  <Text>
                    Transferring {amount} {asset} from {sourceChain} to {destChain}
                  </Text>
                  
                  <Box py={4}>
                    <Progress size="sm" isIndeterminate colorScheme="blue" />
                  </Box>
                  
                  <VStack align="stretch" spacing={3}>
                    <HStack>
                      <Icon as={FaCheckCircle} color="green.500" />
                      <Text>Transaction initiated on {sourceChain}</Text>
                    </HStack>
                    <HStack>
                      <Spinner size="sm" color="blue.500" />
                      <Text>Confirming on source chain...</Text>
                    </HStack>
                    <HStack opacity={0.5}>
                      <Icon as={FaRegClock} color="gray.500" />
                      <Text>Axelar Network processing</Text>
                    </HStack>
                    <HStack opacity={0.5}>
                      <Icon as={FaRegClock} color="gray.500" />
                      <Text>Finalizing on {destChain}</Text>
                    </HStack>
                  </VStack>
                  
                  <Divider my={2} />
                  
                  <HStack justify="space-between">
                    <Text fontSize="sm">Estimated completion time:</Text>
                    <Text fontSize="sm" fontWeight="bold">5-10 minutes</Text>
                  </HStack>
                </VStack>
              </Box>
            </Box>
          )}
          
          <Box p={4} bg="blue.50" borderRadius="md">
            <Heading size="sm" mb={2}>What's happening behind the scenes?</Heading>
            <OrderedList spacing={2} pl={4}>
              <ListItem>Your assets are locked in a smart contract on the source chain</ListItem>
              <ListItem>Axelar validators confirm the transaction on the source chain</ListItem>
              <ListItem>Axelar network prepares the cross-chain message</ListItem>
              <ListItem>The message is delivered to the destination chain</ListItem>
              <ListItem>Equivalent assets are minted or released on the destination chain</ListItem>
            </OrderedList>
          </Box>
        </VStack>
      );
    },
    requiredInteraction: true
  },
  
  // Portfolio Management
  {
    id: 'portfolio-management',
    title: 'Cross-Chain Portfolio Management',
    description: 'Learn how to track and optimize your assets across chains',
    icon: FaChartPie,
    experienceLevel: 'intermediate',
    category: 'portfolio',
    estimatedTime: 240,
    content: (
      <VStack spacing={6} align="stretch">
        <Text>
          One of SNEL's most powerful features is its ability to track and manage your portfolio across multiple blockchains.
          This gives you a unified view of all your assets and helps you make informed decisions about cross-chain strategies.
        </Text>
        
        <SimpleGrid columns={{ base: 1, md: 2 }} spacing={6} mb={4}>
          <Box p={5} borderWidth="1px" borderRadius="lg" bg="white">
            <VStack spacing={3} align="start">
              <Icon as={FaChartPie} color="blue.500" boxSize={6} />
              <Heading size="md">Unified Portfolio View</Heading>
              <Text>
                See all your assets across multiple chains in one place, with USD values and allocation percentages.
              </Text>
            </VStack>
          </Box>
          
          <Box p={5} borderWidth="1px" borderRadius="lg" bg="white">
            <VStack spacing={3} align="start">
              <Icon as={FaExchangeAlt} color="blue.500" boxSize={6} />
              <Heading size="md">Cross-Chain Rebalancing</Heading>
              <Text>
                Easily move assets between chains to maintain your desired portfolio allocation.
              </Text>
            </VStack>
          </Box>
          
          <Box p={5} borderWidth="1px" borderRadius="lg" bg="white">
            <VStack spacing={3} align="start">
              <Icon as={FaCoins} color="blue.500" boxSize={6} />
              <Heading size="md">Yield Opportunities</Heading>
              <Text>
                Discover the best yield opportunities for your assets across all supported chains.
              </Text>
            </VStack>
          </Box>
          
          <Box p={5} borderWidth="1px" borderRadius="lg" bg="white">
            <VStack spacing={3} align="start">
              <Icon as={FaRegLightbulb} color="blue.500" boxSize={6} />
              <Heading size="md">AI-Powered Insights</Heading>
              <Text>
                Get personalized recommendations for optimizing your portfolio based on your goals.
              </Text>
            </VStack>
          </Box>
        </SimpleGrid>
        
        <InteractiveDemoCard
          title="Portfolio Commands"
          description="Learn how to use SNEL's portfolio features"
          icon={FaChartPie}
          isCompleted={false}
          onComplete={() => {}}
        >
          <SimpleGrid columns={{ base: 1, md: 2 }} spacing={4}>
            {[
              {
                command: "show my portfolio",
                description: "Display your portfolio across all chains"
              },
              {
                command: "analyze my portfolio",
                description: "Get detailed analysis and recommendations"
              },
              {
                command: "show my assets on Arbitrum",
                description: "View assets on a specific chain"
              },
              {
                command: "find yield opportunities for USDC",
                description: "Discover yield strategies for a specific token"
              }
            ].map((example, index) => (
              <Box
                key={index}
                p={3}
                borderWidth="1px"
                borderRadius="md"
                bg="gray.50"
              >
                <Text fontWeight="bold" fontFamily="mono" mb={1}>
                  "{example.command}"
                </Text>
                <Text fontSize="sm">{example.description}</Text>
              </Box>
            ))}
          </SimpleGrid>
        </InteractiveDemoCard>
        
        <Box 
          p={5} 
          borderWidth="1px" 
          borderRadius="lg" 
          bg="white"
          boxShadow="sm"
        >
          <Heading size="md" mb={4}>Cross-Chain Portfolio Optimization</Heading>
          
          <Text mb={4}>
            SNEL helps you optimize your portfolio across chains by considering:
          </Text>
          
          <SimpleGrid columns={{ base: 1, md: 2 }} spacing={4}>
            <HStack align="start" spacing={3}>
              <Icon as={FaCoins} color="green.500" mt={1} />
              <Text>Yield differences between chains</Text>
            </HStack>
            
            <HStack align="start" spacing={3}>
              <Icon as={FaGasPump} color="orange.500" mt={1} />
              <Text>Gas costs for transactions</Text>
            </HStack>
            
            <HStack align="start" spacing={3}>
              <Icon as={FaRegClock} color="blue.500" mt={1} />
              <Text>Bridge transfer times</Text>
            </HStack>
            
            <HStack align="start" spacing={3}>
              <Icon as={FaShieldAlt} color="purple.500" mt={1} />
              <Text>Security considerations</Text>
            </HStack>
          </SimpleGrid>
          
          <Divider my={4} />
          
          <Text fontWeight="medium" mb={2}>Example optimization scenario:</Text>
          <Text fontSize="sm">
            If you have USDC on Ethereum earning 2% APY, but Arbitrum offers 5% APY for the same asset,
            SNEL can help you bridge your USDC to Arbitrum if the yield difference outweighs the bridge fees.
          </Text>
        </Box>
      </VStack>
    ),
    reward: {
      type: 'achievement',
      title: 'Portfolio Manager',
      description: 'Learned how to manage a cross-chain portfolio',
      icon: FaChartPie
    }
  },
  
  // Advanced topics
  {
    id: 'advanced-cross-chain',
    title: 'Advanced Cross-Chain Strategies',
    description: 'Learn sophisticated cross-chain techniques',
    icon: FaRocket,
    experienceLevel: 'advanced',
    category: 'crosschain',
    estimatedTime: 300,
    content: (
      <VStack spacing={6} align="stretch">
        <Text>
          For experienced users, SNEL enables advanced cross-chain strategies that can help you maximize returns,
          minimize costs, and optimize your DeFi operations across the entire blockchain ecosystem.
        </Text>
        
        <SimpleGrid columns={{ base: 1, md: 1 }} spacing={6} mb={4}>
          <Box p={5} borderWidth="1px" borderRadius="lg" bg="white" boxShadow="sm">
            <VStack spacing={3} align="start">
              <HStack>
                <Icon as={FaRocket} color="purple.500" boxSize={6} />
                <Heading size="md">Cross-Chain Yield Farming</Heading>
              </HStack>
              <Text>
                Automatically move assets to the chain with the highest yield for a particular token,
                and rebalance when yield opportunities change.
              </Text>
              <Box p={4} bg="gray.50" borderRadius="md" w="100%">
                <Text fontWeight="medium" mb={2}>Example Strategy:</Text>
                <OrderedList spacing={2} pl={4}>
                  <ListItem>Monitor USDC yield across Ethereum, Arbitrum, Optimism, and Polygon</ListItem>
                  <ListItem>When a significantly better yield appears (accounting for bridge fees), move assets</ListItem>
                  <ListItem>Set up automated monitoring to alert when yields change</ListItem>
                  <ListItem>Consider gas costs and bridge fees in yield calculations</ListItem>
                </OrderedList>
              </Box>
            </VStack>
          </Box>
          
          <Box p={5} borderWidth="1px" borderRadius="lg" bg="white" boxShadow="sm">
            <VStack spacing={3} align="start">
              <HStack>
                <Icon as={FaExchangeAlt} color="blue.500" boxSize={6} />
                <Heading size="md">Cross-Chain Arbitrage</Heading>
              </HStack>
              <Text>
                Take advantage of price differences for the same asset across different chains,
                accounting for bridge fees and transfer times.
              </Text>
              <Box p={4} bg="gray.50" borderRadius="md" w="100%">
                <Text fontWeight="medium" mb={2}>Example Strategy:</Text>
                <OrderedList spacing={2} pl={4}>
                  <ListItem>Monitor ETH/USDC price on Ethereum, Arbitrum, and Optimism</ListItem>
                  <ListItem>When price difference exceeds bridge costs + buffer, execute arbitrage</ListItem>
                  <ListItem>Buy on the lower-priced chain, bridge, and sell on the higher-priced chain</ListItem>
                  <ListItem>Consider slippage, execution risk, and bridge time in calculations</ListItem>
                </OrderedList>
              </Box>
            </VStack>
          </Box>
          
          <Box p={5} borderWidth="1px" borderRadius="lg" bg="white" boxShadow="sm">
            <VStack spacing={3} align="start">
              <HStack>
                <Icon as={FaShieldAlt} color="green.500" boxSize={6} />
                <Heading size="md">Cross-Chain Risk Hedging</Heading>
              </HStack>
              <Text>
                Spread assets across multiple chains to reduce exposure to chain-specific risks,
                such as bridge exploits, chain outages, or governance issues.
              </Text>
              <Box p={4} bg="gray.50" borderRadius="md" w="100%">
                <Text fontWeight="medium" mb={2}>Example Strategy:</Text>
                <OrderedList spacing={2} pl={4}>
                  <ListItem>Distribute stablecoins across 3-5 different chains</ListItem>
                  <ListItem>Use different bridge protocols for transfers to diversify bridge risk</ListItem>
                  <ListItem>Monitor TVL and security status of bridges and protocols</ListItem>
                  <ListItem>Maintain liquidity on at least two major chains for quick access</ListItem>
                </OrderedList>
              </Box>
            </VStack>
          </Box>
        </SimpleGrid>
        
        <Alert status="warning" borderRadius="md">
          <AlertIcon />
          <Box>
            <AlertTitle>Advanced Strategies Involve Risk</AlertTitle>
            <AlertDescription>
              These strategies involve multiple transactions, bridge operations, and timing considerations.
              Always start with small amounts and understand the risks involved.
            </AlertDescription>
          </Box>
        </Alert>
        
        <InteractiveDemoCard
          title="Cross-Chain Strategy Builder"
          description="Design your own cross-chain strategy"
          icon={FaCog}
          isCompleted={false}
          onComplete={() => {}}
        >
          <VStack spacing={4} align="stretch">
            <FormControl>
              <FormLabel>Strategy Type</FormLabel>
              <Select defaultValue="yield">
                <option value="yield">Yield Optimization</option>
                <option value="arbitrage">Price Arbitrage</option>
                <option value="hedging">Risk Hedging</option>
              </Select>
            </FormControl>
            
            <FormControl>
              <FormLabel>Primary Asset</FormLabel>
              <Select defaultValue="usdc">
                <option value="usdc">USDC</option>
                <option value="eth">ETH</option>
                <option value="wbtc">WBTC</option>
                <option value="dai">DAI</option>
              </Select>
            </FormControl>
            
            <FormControl>
              <FormLabel>Chains to Include</FormLabel>
              <SimpleGrid columns={2} spacing={2}>
                <Checkbox defaultChecked>Ethereum</Checkbox>
                <Checkbox defaultChecked>Arbitrum</Checkbox>
                <Checkbox defaultChecked>Optimism</Checkbox>
                <Checkbox>Polygon</Checkbox>
                <Checkbox>Avalanche</Checkbox>
                <Checkbox>Base</Checkbox>
              </SimpleGrid>
            </FormControl>
            
            <FormControl>
              <FormLabel>Risk Tolerance</FormLabel>
              <Slider defaultValue={50} min={0} max={100}>
                <SliderTrack>
                  <SliderFilledTrack />
                </SliderTrack>
                <SliderThumb />
              </Slider>
              <Flex justify="space-between" mt={1}>
                <Text fontSize="xs">Conservative</Text>
                <Text fontSize="xs">Aggressive</Text>
              </Flex>
            </FormControl>
            
            <Button colorScheme="blue">Generate Strategy</Button>
          </VStack>
        </InteractiveDemoCard>
      </VStack>
    ),
    reward: {
      type: 'achievement',
      title: 'Cross-Chain Strategist',
      description: 'Mastered advanced cross-chain strategies',
      icon: FaRocket
    }
  },
  
  // Final step
  {
    id: 'completion',
    title: 'Onboarding Complete',
    description: 'You're ready to use SNEL',
    icon: FaRegCheckCircle,
    experienceLevel: 'beginner',
    category: 'intro',
    estimatedTime: 60,
    content: ({ preferences, achievements }: any) => (
      <VStack spacing={8} align="stretch">
        <MotionBox
          variants={fadeIn}
          initial="hidden"
          animate="visible"
          textAlign="center"
          py={6}
        >
          <Icon as={FaTrophy} boxSize={16} color="yellow.400" mb={4} />
          <Heading size="xl" mb={2}>Congratulations!</Heading>
          <Text fontSize="lg" color="gray.600">
            You've completed the SNEL onboarding experience.
            You're now ready to use SNEL for seamless cross-chain DeFi operations.
          </Text>
        </MotionBox>
        
        <SimpleGrid columns={{ base: 1, md: 2 }} spacing={6}>
          <Box p={5} borderWidth="1px" borderRadius="lg" bg="white" boxShadow="sm">
            <Heading size="md" mb={4}>Your Achievements</Heading>
            <SimpleGrid columns={2} spacing={4}>
              {achievements?.map((achievement: any) => (
                <AchievementBadge
                  key={achievement.id}
                  achievement={achievement}
                  isUnlocked={true}
                />
              ))}
            </SimpleGrid>
          </Box>
          
          <Box p={5} borderWidth="1px" borderRadius="lg" bg="white" boxShadow="sm">
            <Heading size="md" mb={4}>Your Profile</Heading>
            <VStack align="start" spacing={3}>
              <HStack>
                <Text fontWeight="bold">Experience Level:</Text>
                <Badge colorScheme={
                  preferences?.experienceLevel === 'beginner' ? 'green' :
                  preferences?.experienceLevel === 'intermediate' ? 'blue' : 'purple'
                }>
                  {preferences?.experienceLevel || 'Beginner'}
                </Badge>
              </HStack>
              
              <Box>
                <Text fontWeight="bold" mb={1}>Interests:</Text>
                <Wrap>
                  {preferences?.interests?.map((interest: string) => (
                    <WrapItem key={interest}>
                      <Tag colorScheme="blue" size="sm">{interest}</Tag>
                    </WrapItem>
                  ))}
                </Wrap>
              </Box>
              
              <HStack>
                <Text fontWeight="bold">Steps Completed:</Text>
                <Text>{preferences?.completedSteps?.length || 0}</Text>
              </HStack>
            </VStack>
          </Box>
        </SimpleGrid>
        
        <Box p={5} borderWidth="1px" borderRadius="lg" bg="white" boxShadow="sm">
          <Heading size="md" mb={4}>What's Next?</Heading>
          <SimpleGrid columns={{ base: 1, md: 3 }} spacing={5}>
            <VStack align="start" spacing={3}>
              <Icon as={FaExchangeAlt} color="blue.500" boxSize={6} />
              <Heading size="sm">Try Your First Swap</Heading>
              <Text fontSize="sm">
                Start with a simple token swap to get familiar with SNEL's interface.
              </Text>
              <Button size="sm" colorScheme="blue" variant="outline">
                Try Now
              </Button>
            </VStack>
            
            <VStack align="start" spacing={3}>
              <Icon as={FaLink} color="purple.500" boxSize={6} />
              <Heading size="sm">Bridge Some Assets</Heading>
              <Text fontSize="sm">
                Experience the power of cross-chain operations by bridging assets between networks.
              </Text>
              <Button size="sm" colorScheme="purple" variant="outline">
                Try Now
              </Button>
            </VStack>
            
            <VStack align="start" spacing={3}>
              <Icon as={FaChartPie} color="green.500" boxSize={6} />
              <Heading size="sm">View Your Portfolio</Heading>
              <Text fontSize="sm">
                Get a unified view of your assets across all supported chains.
              </Text>
              <Button size="sm" colorScheme="green" variant="outline">
                Try Now
              </Button>
            </VStack>
          </SimpleGrid>
        </Box>
        
        <Alert status="info" borderRadius="md">
          <AlertIcon />
          <Box>
            <AlertTitle>Help is Always Available</AlertTitle>
            <AlertDescription>
              You can revisit this onboarding experience anytime from the settings menu.
              If you have questions, just ask SNEL directly in the chat interface.
            </AlertDescription>
          </Box>
        </Alert>
      </VStack>
    )
  }
];

// Define onboarding paths
const onboardingPaths: OnboardingPath[] = [
  {
    id: 'beginner',
    title: 'Beginner Path',
    description: 'Perfect for those new to DeFi and cross-chain operations',
    icon: FaRegLightbulb,
    stepIds: ['welcome', 'experience-level', 'natural-language', 'cross-chain-intro', 'axelar-benefits', 'completion'],
    experienceLevel: 'beginner',
    estimatedTime: 15
  },
  {
    id: 'intermediate',
    title: 'Intermediate Path',
    description: 'For users familiar with DeFi but new to cross-chain',
    icon: FaLink,
    stepIds: ['welcome', 'experience-level', 'cross-chain-intro', 'axelar-benefits', 'cross-chain-demo', 'portfolio-management', 'completion'],
    experienceLevel: 'intermediate',
    estimatedTime: 25
  },
  {
    id: 'advanced',
    title: 'Advanced Path',
    description: 'For experienced DeFi users looking to master cross-chain strategies',
    icon: FaRocket,
    stepIds: ['welcome', 'experience-level', 'axelar-benefits', 'cross-chain-demo', 'portfolio-management', 'advanced-cross-chain', 'completion'],
    experienceLevel: 'advanced',
    estimatedTime: 30
  },
  {
    id: 'axelar-focus',
    title: 'Axelar Deep Dive',
    description: 'Focus on understanding Axelar and cross-chain operations',
    icon: FaShieldAlt,
    stepIds: ['welcome', 'experience-level', 'cross-chain-intro', 'axelar-benefits', 'cross-chain-demo', 'advanced-cross-chain', 'completion'],
    experienceLevel: 'intermediate',
    estimatedTime: 25
  }
];

// Define achievements
const onboardingAchievements: OnboardingAchievement[] = [
  {
    id: 'first-steps',
    title: 'First Steps',
    description: 'Completed your first onboarding step',
    icon: FaRegCheckCircle,
    criteria: (prefs) => prefs.completedSteps.length >= 1
  },
  {
    id: 'halfway-there',
    title: 'Halfway There',
    description: 'Completed half of your onboarding path',
    icon: FaRegClock,
    criteria: (prefs) => {
      const path = onboardingPaths.find(p => p.id === prefs.currentPath);
      return path ? prefs.completedSteps.length >= Math.floor(path.stepIds.length / 2) : false;
    }
  },
  {
    id: 'cross-chain-explorer',
    title: 'Cross-Chain Explorer',
    description: 'Learned about cross-chain operations',
    icon: FaLink,
    criteria: (prefs) => prefs.completedSteps.includes('cross-chain-intro')
  },
  {
    id: 'axelar-expert',
    title: 'Axelar Expert',
    description: 'Mastered Axelar Network concepts',
    icon: FaShieldAlt,
    criteria: (prefs) => prefs.completedSteps.includes('axelar-benefits')
  },
  {
    id: 'command-master',
    title: 'Command Master',
    description: 'Learned how to use natural language commands',
    icon: FaRegLightbulb,
    criteria: (prefs) => prefs.completedSteps.includes('natural-language')
  },
  {
    id: 'portfolio-pro',
    title: 'Portfolio Pro',
    description: 'Mastered cross-chain portfolio management',
    icon: FaChartPie,
    criteria: (prefs) => prefs.completedSteps.includes('portfolio-management')
  },
  {
    id: 'advanced-strategist',
    title: 'Advanced Strategist',
    description: 'Learned advanced cross-chain strategies',
    icon: FaRocket,
    criteria: (prefs) => prefs.completedSteps.includes('advanced-cross-chain')
  },
  {
    id: 'completion',
    title: 'Onboarding Complete',
    description: 'Completed the entire onboarding process',
    icon: FaTrophy,
    criteria: (prefs) => prefs.completedSteps.includes('completion')
  }
];

// Default preferences
const defaultPreferences: OnboardingPreferences = {
  experienceLevel: 'beginner',
  interests: [],
  completedSteps: [],
  achievements: [],
  currentPath: 'beginner'
};

// FloatingHelpButton Component
const FloatingHelpButton: React.FC<{ onClick: () => void }> = ({ onClick }) => {
  const bgColor = useColorModeValue('blue.500', 'blue.300');
  const controls = useAnimation();
  
  useEffect(() => {
    // Animate the button to draw attention
    const animate = async () => {
      await controls.start({
        scale: [1, 1.1, 1],
        transition: { duration: 1.5 }
      });
      setTimeout(animate, 5000);
    };
    
    animate();
  }, [controls]);
  
  return (
    <motion.div
      animate={controls}
      style={{
        position: 'fixed',
        bottom: '20px',
        right: '20px',
        zIndex: 100
      }}
    >
      <Tooltip label="Open SNEL Onboarding" placement="left">
        <IconButton
          aria-label="Open onboarding"
          icon={<Icon as={FaRegQuestionCircle} boxSize={5} />}
          onClick={onClick}
          colorScheme="blue"
          size="lg"
          borderRadius="full"
          boxShadow="lg"
        />
      </Tooltip>
    </motion.div>
  );
};

// ======== Main Component ========

export const InteractiveOnboarding: React.FC<InteractiveOnboardingProps> = ({
  isOpen = false,
  onClose,
  initialStep,
  initialPath = 'beginner',
  onComplete,
  onStepComplete,
  showFloatingButton = true
}) => {
  // State
  const [isDrawerOpen, setIsDrawerOpen] = useState(isOpen);
  const [currentPathId, setCurrentPathId] = useState(initialPath);
  const [currentStepId, setCurrentStepId] = useState(initialStep || '');
  const [preferences, setPreferences] = useLocalStorage<OnboardingPreferences>(
    'snel-onboarding-preferences',
    defaultPreferences
  );
  const [unlockedAchievements, setUnlockedAchievements] = useState<OnboardingAchievement[]>([]);
  const [showAchievementModal, setShowAchievementModal] = useState(false);
  const [newAchievement, setNewAchievement] = useState<OnboardingAchievement | null>(null);
  
  const toast = useToast();
  const controls = useAnimation();
  
  // Derived state
  const currentPath = onboardingPaths.find(path => path.id === currentPathId) || onboardingPaths[0];
  const stepIds = currentPath.stepIds;
  const currentStepIndex = currentStepId ? stepIds.indexOf(currentStepId) : 0;
  const currentStep = onboardingSteps.find(step => step.id === (currentStepId || stepIds[0]));
  
  // Effects
  
  // Initialize
  useEffect(() => {
    if (isOpen) {
      setIsDrawerOpen(true);
      
      // If no current step is set, use the first step of the path
      if (!currentStepId && stepIds.length > 0) {
        setCurrentStepId(stepIds[0]);
      }
      
      // Update preferences with current path
      if (currentPathId !== preferences.currentPath) {
        setPreferences({
          ...preferences,
          currentPath: currentPathId
        });
      }
    }
  }, [isOpen, currentPathId, currentStepId, stepIds, preferences, setPreferences]);
  
  // Check for achievements
  useEffect(() => {
    // Find achievements that are newly unlocked
    const newlyUnlocked = onboardingAchievements.filter(achievement => {
      // Check if achievement is already unlocked
      const isAlreadyUnlocked = preferences.achievements.includes(achievement.id);
      
      // Check if achievement criteria is now met
      const isCriteriaMet = achievement.criteria(preferences);
      
      return !isAlreadyUnlocked && isCriteriaMet;
    });
    
    if (newlyUnlocked.length > 0) {
      // Update preferences with new achievements
      const updatedAchievements = [
        ...preferences.achievements,
        ...newlyUnlocked.map(a => a.id)
      ];
      
      setPreferences({
        ...preferences,
        achievements: updatedAchievements
      });
      
      // Show achievement modal for the first new achievement
      setNewAchievement({
        ...newlyUnlocked[0],
        unlockedAt: new Date().toISOString()
      });
      setShowAchievementModal(true);
      
      // Update unlocked achievements list
      setUnlockedAchievements(prev => [
        ...prev,
        ...newlyUnlocked.map(a => ({
          ...a,
          unlockedAt: new Date().toISOString()
        }))
      ]);
    }
  }, [preferences, setPreferences]);
  
  // Loa
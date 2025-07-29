import React, { useState, useEffect } from 'react';
import {
  Box,
  Button,
  Flex,
  Heading,
  Text,
  VStack,
  HStack,
  Icon,
  Image,
  Progress,
  Badge,
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
  Radio,
  RadioGroup,
  Checkbox,
  SimpleGrid,
  useColorModeValue,
  useToast,
  IconButton,
  Divider,
  Alert,
  AlertIcon,
  AlertTitle,
  AlertDescription,
  Wrap,
  WrapItem,
  Tag,
  Select,
} from '@chakra-ui/react';
import { motion, AnimatePresence, useAnimation } from 'framer-motion';
import {
  FaArrowRight,
  FaArrowLeft,
  FaCheck,
  FaLightbulb,
  FaRocket,
  FaTrophy,
  FaInfoCircle,
  FaExchangeAlt,
  FaLink,
  FaWallet,
  FaChartPie,
  FaShieldAlt,
  FaUserGraduate,
  FaRegLightbulb,
  FaRegCheckCircle,
  FaRegClock,
  FaRegQuestionCircle,
} from 'react-icons/fa';
import { useLocalStorage } from '../../hooks/useLocalStorage';

// ======== TypeScript Interfaces ========

export interface OnboardingStep {
  id: string;
  title: string;
  description: string;
  content: React.ReactNode;
  icon: React.ElementType;
  experienceLevel: 'beginner' | 'intermediate' | 'advanced';
  category: 'intro' | 'crosschain' | 'axelar' | 'portfolio' | 'commands';
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

// ======== Helper Components ========

const MotionBox = motion(Box);

const FloatingHelpButton: React.FC<{ onClick: () => void }> = ({ onClick }) => {
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

const ConceptCard: React.FC<{
  title: string;
  description: string;
  icon: React.ElementType;
}> = ({ title, description, icon }) => {
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
        
        <Text>{description}</Text>
      </VStack>
    </MotionBox>
  );
};

// ======== Onboarding Content ========

// Define onboarding steps - simplified to 5 key steps
const onboardingSteps: OnboardingStep[] = [
  // Step 1: Welcome
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
  
  // Step 2: Experience Level
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
              { id: 'yields', label: 'Yield Opportunities', icon: FaRocket }
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
    )
  },
  
  // Step 3: Cross-Chain Basics
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
              icon={FaExchangeAlt}
            />
            <ConceptCard
              title="Bridging"
              description="Bridges connect blockchains, allowing assets to move between them securely."
              icon={FaLink}
            />
            <ConceptCard
              title="Interoperability"
              description="The ability of different blockchain systems to exchange and make use of information."
              icon={FaRocket}
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
        
        <Alert status="info" borderRadius="md">
          <AlertIcon />
          <Box>
            <AlertTitle>Important to Know</AlertTitle>
            <AlertDescription>
              Cross-chain operations typically take longer than regular transactions (5-20 minutes) because they require confirmations on both chains and processing by the bridge protocol.
            </AlertDescription>
          </Box>
        </Alert>
      </VStack>
    ),
    reward: {
      type: 'achievement',
      title: 'Chain Explorer',
      description: 'Learned the basics of cross-chain operations',
      icon: FaLink
    }
  },
  
  // Step 4: Axelar Benefits
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
                <Icon as={FaLink} color="blue.500" boxSize={6} />
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
      </VStack>
    ),
    reward: {
      type: 'achievement',
      title: 'Axelar Expert',
      description: 'Learned about Axelar Network and its benefits',
      icon: FaShieldAlt
    }
  },
  
  // Step 5: Completion
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
    stepIds: ['welcome', 'experience-level', 'cross-chain-intro', 'axelar-benefits', 'completion'],
    experienceLevel: 'beginner',
    estimatedTime: 15
  },
  {
    id: 'intermediate',
    title: 'Intermediate Path',
    description: 'For users familiar with DeFi but new to cross-chain',
    icon: FaLink,
    stepIds: ['welcome', 'experience-level', 'cross-chain-intro', 'axelar-benefits', 'completion'],
    experienceLevel: 'intermediate',
    estimatedTime: 20
  },
  {
    id: 'advanced',
    title: 'Advanced Path',
    description: 'For experienced DeFi users looking to master cross-chain strategies',
    icon: FaRocket,
    stepIds: ['welcome', 'cross-chain-intro', 'axelar-benefits', 'completion'],
    experienceLevel: 'advanced',
    estimatedTime: 15
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
    title: 'Chain Explorer',
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

// ======== Main Component ========

export const InteractiveOnboardingFinal: React.FC<InteractiveOnboardingProps> = ({
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
  
  // Load unlocked achievements on mount
  useEffect(() => {
    const loadedAchievements = onboardingAchievements
      .filter(achievement => preferences.achievements.includes(achievement.id))
      .map(achievement => ({
        ...achievement,
        unlockedAt: new Date().toISOString() // We don't have the actual unlock date
      }));
    
    setUnlockedAchievements(loadedAchievements);
  }, [preferences.achievements]);
  
  // Update last active date
  useEffect(() => {
    if (isDrawerOpen) {
      setPreferences({
        ...preferences,
        lastActiveDate: new Date().toISOString()
      });
    }
  }, [isDrawerOpen, setPreferences, preferences]);
  
  // Handler Functions
  const handleStepComplete = (stepId: string) => {
    // Add step to completed steps if not already there
    if (!preferences.completedSteps.includes(stepId)) {
      const updatedCompletedSteps = [...preferences.completedSteps, stepId];
      
      setPreferences({
        ...preferences,
        completedSteps: updatedCompletedSteps,
        currentStep: stepId
      });
      
      // Call onStepComplete callback
      if (onStepComplete) {
        onStepComplete(stepId);
      }
      
      // If this was the last step, call onComplete
      if (stepId === 'completion' && onComplete) {
        onComplete(preferences);
      }
      
      // Show toast
      toast({
        title: "Step completed!",
        description: `You've completed the "${currentStep?.title}" step.`,
        status: "success",
        duration: 3000,
        isClosable: true,
        position: "bottom-right"
      });
    }
  };
  
  const handleNextStep = () => {
    // Complete current step if not already completed
    if (currentStep && !preferences.completedSteps.includes(currentStep.id)) {
      handleStepComplete(currentStep.id);
    }
    
    // Move to next step
    const nextIndex = currentStepIndex + 1;
    if (nextIndex < stepIds.length) {
      const nextStepId = stepIds[nextIndex];
      setCurrentStepId(nextStepId);
      
      // Update preferences
      setPreferences({
        ...preferences,
        currentStep: nextStepId
      });
      
      // Animate transition
      controls.start({
        opacity: [0, 1],
        y: [20, 0],
        transition: { duration: 0.3 }
      });
    }
  };
  
  const handlePrevStep = () => {
    // Move to previous step
    const prevIndex = currentStepIndex - 1;
    if (prevIndex >= 0) {
      const prevStepId = stepIds[prevIndex];
      setCurrentStepId(prevStepId);
      
      // Update preferences
      setPreferences({
        ...preferences,
        currentStep: prevStepId
      });
      
      // Animate transition
      controls.start({
        opacity: [0, 1],
        y: [20, 0],
        transition: { duration: 0.3 }
      });
    }
  };
  
  const handleSkipStep = () => {
    // Skip to next step without marking current as complete
    const nextIndex = currentStepIndex + 1;
    if (nextIndex < stepIds.length) {
      const nextStepId = stepIds[nextIndex];
      setCurrentStepId(nextStepId);
      
      // Update preferences
      setPreferences({
        ...preferences,
        currentStep: nextStepId
      });
      
      toast({
        title: "Step skipped",
        description: "You can always come back to this step later.",
        status: "info",
        duration: 3000,
        isClosable: true,
        position: "bottom-right"
      });
    }
  };
  
  const handlePathChange = (pathId: string) => {
    setCurrentPathId(pathId);
    
    // Reset to first step of the new path
    const newPath = onboardingPaths.find(p => p.id === pathId);
    if (newPath && newPath.stepIds.length > 0) {
      setCurrentStepId(newPath.stepIds[0]);
    }
    
    // Update preferences
    setPreferences({
      ...preferences,
      currentPath: pathId
    });
    
    toast({
      title: "Path changed",
      description: `Now following the "${newPath?.title}" path.`,
      status: "info",
      duration: 3000,
      isClosable: true,
      position: "bottom-right"
    });
  };
  
  const handlePreferenceChange = (key: keyof OnboardingPreferences, value: any) => {
    setPreferences({
      ...preferences,
      [key]: value
    });
  };
  
  const handleDrawerClose = () => {
    setIsDrawerOpen(false);
    if (onClose) {
      onClose();
    }
  };
  
  const handleShowOnboarding = () => {
    setIsDrawerOpen(true);
  };
  
  // Helper functions
  const isStepCompleted = (stepId: string) => {
    return preferences.completedSteps.includes(stepId);
  };
  
  const getStepProgress = () => {
    return {
      completed: preferences.completedSteps.filter(id => stepIds.includes(id)).length,
      total: stepIds.length
    };
  };
  
  const isLastStep = () => {
    return currentStepIndex === stepIds.length - 1;
  };
  
  const isFirstStep = () => {
    return currentStepIndex === 0;
  };
  
  const getStepContent = () => {
    if (!currentStep) return null;
    
    // If the content is a function, call it with context
    if (typeof currentStep.content === 'function') {
      return currentStep.content({
        preferences,
        onPreferenceChange: handlePreferenceChange,
        onStepComplete: handleStepComplete,
        achievements: unlockedAchievements,
        isCompleted: isStepCompleted(currentStep.id)
      });
    }
    
    // Otherwise, render the content directly
    return currentStep.content;
  };
  
  // Main Render
  return (
    <>
      {/* Floating Help Button */}
      {showFloatingButton && !isDrawerOpen && (
        <FloatingHelpButton onClick={handleShowOnboarding} />
      )}
      
      {/* Main Drawer */}
      <Drawer
        isOpen={isDrawerOpen}
        placement="right"
        onClose={handleDrawerClose}
        size="lg"
      >
        <DrawerOverlay />
        <DrawerContent>
          <DrawerCloseButton />
          <DrawerHeader borderBottomWidth="1px">
            <HStack spacing={3}>
              <Icon as={currentStep?.icon || FaRocket} color="blue.500" />
              <Text>SNEL Onboarding</Text>
            </HStack>
          </DrawerHeader>
          
          <DrawerBody p={0}>
            <Flex h="100%" direction="column">
              {/* Path Selection */}
              <Box p={4} bg="gray.50" borderBottomWidth="1px">
                <Select
                  value={currentPathId}
                  onChange={(e) => handlePathChange(e.target.value)}
                  size="sm"
                  maxW="400px"
                >
                  {onboardingPaths.map(path => (
                    <option key={path.id} value={path.id}>
                      {path.title} - {path.estimatedTime} min
                    </option>
                  ))}
                </Select>
              </Box>
              
              {/* Progress Bar */}
              <Box px={4} py={3} bg="white" borderBottomWidth="1px">
                <StepProgressBar
                  currentStepIndex={currentStepIndex}
                  totalSteps={stepIds.length}
                  completedSteps={getStepProgress().completed}
                />
              </Box>
              
              {/* Step Content */}
              <Box flex="1" p={6} overflowY="auto">
                <motion.div
                  animate={controls}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.3 }}
                >
                  {currentStep && (
                    <>
                      <HStack spacing={3} mb={6}>
                        <Icon as={currentStep.icon} color="blue.500" boxSize={8} />
                        <VStack spacing={0} align="start">
                          <Heading size="lg">{currentStep.title}</Heading>
                          <Text color="gray.600">{currentStep.description}</Text>
                        </VStack>
                      </HStack>
                      
                      <Box mb={8}>
                        {getStepContent()}
                      </Box>
                    </>
                  )}
                </motion.div>
              </Box>
              
              {/* Navigation Footer */}
              <Box p={4} borderTopWidth="1px" bg="gray.50">
                <Flex justify="space-between">
                  <Button
                    leftIcon={<Icon as={FaArrowLeft} />}
                    onClick={handlePrevStep}
                    isDisabled={isFirstStep()}
                    variant="outline"
                  >
                    Previous
                  </Button>
                  
                  <HStack spacing={3}>
                    {!isLastStep() && (
                      <Button
                        variant="ghost"
                        onClick={handleSkipStep}
                      >
                        Skip
                      </Button>
                    )}
                    
                    {isLastStep() ? (
                      <Button
                        rightIcon={<Icon as={FaCheck} />}
                        colorScheme="green"
                        onClick={() => handleStepComplete(currentStep?.id || '')}
                        isDisabled={!currentStep || isStepCompleted(currentStep.id)}
                      >
                        Complete
                      </Button>
                    ) : (
                      <Button
                        rightIcon={<Icon as={FaArrowRight} />}
                        colorScheme="blue"
                        onClick={handleNextStep}
                      >
                        {currentStep && isStepCompleted(currentStep.id) ? 'Next' : 'Complete & Next'}
                      </Button>
                    )}
                  </HStack>
                </Flex>
              </Box>
            </Flex>
          </DrawerBody>
        </DrawerContent>
      </Drawer>
      
      {/* Achievement Modal */}
      <Modal
        isOpen={showAchievementModal}
        onClose={() => setShowAchievementModal(false)}
        isCentered
      >
        <ModalOverlay />
        <ModalContent>
          <ModalHeader>Achievement Unlocked!</ModalHeader>
          <ModalCloseButton />
          <ModalBody>
            {newAchievement && (
              <VStack spacing={4} py={4}>
                <Icon
                  as={newAchievement.icon}
                  boxSize={16}
                  color="yellow.400"
                />
                <Heading size="md" textAlign="center">
                  {newAchievement.title}
                </Heading>
                <Text textAlign="center">
                  {newAchievement.description}
                </Text>
              </VStack>
            )}
          </ModalBody>
          <ModalFooter>
            <Button
              colorScheme="blue"
              onClick={() => setShowAchievementModal(false)}
            >
              Awesome!
            </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>
    </>
  );
};

export default InteractiveOnboardingFinal;

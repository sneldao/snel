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

// Types and interfaces
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

// Helper Components
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

// Main Component Implementation
export const InteractiveOnboardingPart2: React.FC<InteractiveOnboardingProps> = ({
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
    {
      experienceLevel: 'beginner',
      interests: [],
      completedSteps: [],
      achievements: [],
      currentPath: 'beginner'
    }
  );
  const [unlockedAchievements, setUnlockedAchievements] = useState<OnboardingAchievement[]>([]);
  const [showAchievementModal, setShowAchievementModal] = useState(false);
  const [newAchievement, setNewAchievement] = useState<OnboardingAchievement | null>(null);
  
  const toast = useToast();
  const controls = useAnimation();
  
  // Define onboarding steps and paths (these would be imported from the first file)
  // For this example, we'll use placeholders
  const onboardingSteps: OnboardingStep[] = [];
  const onboardingPaths: OnboardingPath[] = [];
  const onboardingAchievements: OnboardingAchievement[] = [];
  
  // Derived state
  const currentPath = onboardingPaths.find(path => path.id === currentPathId) || onboardingPaths[0];
  const stepIds = currentPath?.stepIds || [];
  const currentStepIndex = currentStepId ? stepIds.indexOf(currentStepId) : 0;
  const currentStep = onboardingSteps.find(step => step.id === (currentStepId || stepIds[0]));
  
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
  }, [preferences, setPreferences, onboardingAchievements]);
  
  // Load unlocked achievements on mount
  useEffect(() => {
    const loadedAchievements = onboardingAchievements
      .filter(achievement => preferences.achievements.includes(achievement.id))
      .map(achievement => ({
        ...achievement,
        unlockedAt: new Date().toISOString() // We don't have the actual unlock date
      }));
    
    setUnlockedAchievements(loadedAchievements);
  }, [preferences.achievements, onboardingAchievements]);
  
  // Update last active date
  useEffect(() => {
    if (isDrawerOpen) {
      setPreferences({
        ...preferences,
        lastActiveDate: new Date().toISOString()
      });
    }
  }, [isDrawerOpen, setPreferences, preferences]);
  
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

// Helper component for progress bar
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

// Export the component
export default InteractiveOnboardingPart2;

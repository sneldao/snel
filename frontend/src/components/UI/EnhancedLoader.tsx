import React, { useState, useEffect, useRef } from 'react';
import {
  Box,
  Flex,
  Text,
  Heading,
  Stack,
  HStack,
  VStack,
  Spinner,
  Progress,
  CircularProgress,
  CircularProgressLabel,
  Skeleton,
  SkeletonText,
  SkeletonCircle,
  useColorModeValue,
  useTheme,
  keyframes,
  Portal,
  IconButton,
  Button,
  Badge,
  Tooltip,
  VisuallyHidden,
  chakra,
  ThemingProps,
  SystemProps,
  ResponsiveValue,
} from '@chakra-ui/react';
import { motion, AnimatePresence, useAnimation, Variants, MotionProps } from 'framer-motion';
import {
  FaEthereum,
  FaBitcoin,
  FaSpinner,
  FaRedo,
  FaExclamationTriangle,
  FaCheckCircle,
  FaTimesCircle,
  FaArrowRight,
  FaWallet,
  FaExchangeAlt,
  FaNetworkWired,
  FaLink,
  FaChartLine,
  FaCoins,
  FaLock,
  FaUnlock,
} from 'react-icons/fa';
import { transparentize, darken, lighten } from '@chakra-ui/theme-tools';

// ========== Types & Interfaces ==========

export type LoaderVariant = 
  | 'spinner'
  | 'pulse'
  | 'dots'
  | 'bars'
  | 'waves'
  | 'skeleton'
  | 'circular'
  | 'progress'
  | 'shimmer';

export type LoaderSize = 'xs' | 'sm' | 'md' | 'lg' | 'xl';

export type LoaderState = 
  | 'loading'
  | 'success'
  | 'error'
  | 'warning'
  | 'idle';

export type LoaderSpeed = 'slow' | 'normal' | 'fast';

export type ChainType = 
  | 'ethereum'
  | 'bitcoin'
  | 'binance'
  | 'polygon'
  | 'arbitrum'
  | 'optimism'
  | 'avalanche'
  | 'solana'
  | 'cosmos'
  | 'generic';

export interface TransactionStep {
  id: string | number;
  label: string;
  description?: string;
  status: 'pending' | 'active' | 'completed' | 'error';
  icon?: React.ReactNode;
  percentage?: number;
}

export interface RetryConfig {
  enabled: boolean;
  maxAttempts?: number;
  onRetry?: () => void;
  delayMs?: number;
  showButton?: boolean;
}

export interface EnhancedLoaderProps {
  // Base props
  variant?: LoaderVariant;
  size?: LoaderSize;
  state?: LoaderState;
  speed?: LoaderSpeed;
  
  // Content props
  message?: string;
  description?: string;
  showMessage?: boolean;
  
  // Visual props
  color?: string;
  secondaryColor?: string;
  thickness?: number;
  isIndeterminate?: boolean;
  value?: number;
  min?: number;
  max?: number;
  
  // Chain specific props
  chainType?: ChainType;
  showChainIcon?: boolean;
  
  // Transaction loader props
  steps?: TransactionStep[];
  currentStep?: number;
  
  // Overlay props
  isOverlay?: boolean;
  overlayColor?: string;
  overlayOpacity?: number;
  blockInteraction?: boolean;
  
  // Portfolio loader props
  portfolioItemCount?: number;
  
  // Button loader props
  buttonText?: string;
  buttonVariant?: string;
  buttonSize?: string;
  isDisabled?: boolean;
  
  // Progressive loading props
  stageCount?: number;
  stageDelay?: number;
  
  // Animation props
  animate?: boolean;
  animationDuration?: number;
  
  // Retry mechanism props
  retry?: RetryConfig;
  
  // Accessibility props
  ariaLabel?: string;
  ariaLive?: 'polite' | 'assertive' | 'off';
  
  // Misc props
  onComplete?: () => void;
  className?: string;
  
  // Additional props
  [key: string]: any;
}

// ========== Animation Variants ==========

const pulseKeyframes = keyframes`
  0% { transform: scale(1); opacity: 1; }
  50% { transform: scale(1.1); opacity: 0.7; }
  100% { transform: scale(1); opacity: 1; }
`;

const shimmerKeyframes = keyframes`
  0% { background-position: -200% 0; }
  100% { background-position: 200% 0; }
`;

const waveKeyframes = keyframes`
  0% { transform: translateY(0); }
  50% { transform: translateY(-10px); }
  100% { transform: translateY(0); }
`;

const bouncingDotsVariants: Variants = {
  animate: {
    transition: {
      staggerChildren: 0.2,
    },
  },
};

const dotVariants: Variants = {
  initial: { y: 0 },
  animate: {
    y: [0, -10, 0],
    transition: {
      repeat: Infinity,
      duration: 0.8,
    },
  },
};

const barVariants: Variants = {
  initial: { scaleY: 0.5, opacity: 0.5 },
  animate: (custom) => ({
    scaleY: [0.5, 1, 0.5],
    opacity: [0.5, 1, 0.5],
    transition: {
      repeat: Infinity,
      duration: 1,
      delay: custom * 0.1,
    },
  }),
};

const progressStepVariants: Variants = {
  pending: { opacity: 0.5, scale: 0.95 },
  active: { 
    opacity: 1, 
    scale: 1,
    transition: { duration: 0.3 }
  },
  completed: { 
    opacity: 1, 
    scale: 1,
    transition: { duration: 0.3 }
  },
  error: { 
    opacity: 1, 
    scale: 1,
    transition: { duration: 0.3 }
  },
};

const progressLineVariants: Variants = {
  pending: { width: 0 },
  active: { 
    width: '50%',
    transition: { duration: 0.5 }
  },
  completed: { 
    width: '100%',
    transition: { duration: 0.5 }
  },
  error: { 
    width: '100%',
    transition: { duration: 0.5 }
  },
};

const overlayVariants: Variants = {
  hidden: { opacity: 0 },
  visible: { 
    opacity: 1,
    transition: { duration: 0.3 }
  },
  exit: { 
    opacity: 0,
    transition: { duration: 0.2 }
  },
};

const staggeredContentVariants: Variants = {
  hidden: { opacity: 0 },
  visible: (custom) => ({
    opacity: 1,
    transition: { 
      delay: custom * 0.1,
      duration: 0.3
    }
  }),
};

// ========== Helper Components ==========

const MotionBox = motion(Box);
const MotionFlex = motion(Flex);
const MotionText = motion(Text);
const MotionProgress = motion(Progress);
const MotionCircularProgress = motion(CircularProgress);

// Basic Spinner Loader
const SpinnerLoader: React.FC<{ 
  size: LoaderSize; 
  color?: string;
  speed: LoaderSpeed;
  thickness?: number;
}> = ({ 
  size, 
  color,
  speed,
  thickness = 4
}) => {
  const spinnerColor = color || useColorModeValue('blue.500', 'blue.300');
  
  const getSpinnerSize = () => {
    switch (size) {
      case 'xs': return 'sm';
      case 'sm': return 'md';
      case 'md': return 'md';
      case 'lg': return 'lg';
      case 'xl': return 'xl';
      default: return 'md';
    }
  };
  
  const getSpeedMultiplier = () => {
    switch (speed) {
      case 'slow': return 1.5;
      case 'fast': return 0.7;
      default: return 1;
    }
  };
  
  return (
    <Spinner 
      size={getSpinnerSize()} 
      color={spinnerColor} 
      thickness={`${thickness}px`}
      speed={`${0.8 * getSpeedMultiplier()}s`}
    />
  );
};

// Pulse Loader
const PulseLoader: React.FC<{ 
  size: LoaderSize; 
  color?: string;
  speed: LoaderSpeed;
}> = ({ 
  size, 
  color,
  speed
}) => {
  const pulseColor = color || useColorModeValue('blue.500', 'blue.300');
  
  const getSize = () => {
    switch (size) {
      case 'xs': return '16px';
      case 'sm': return '24px';
      case 'md': return '40px';
      case 'lg': return '60px';
      case 'xl': return '80px';
      default: return '40px';
    }
  };
  
  const getSpeedMultiplier = () => {
    switch (speed) {
      case 'slow': return 1.5;
      case 'fast': return 0.7;
      default: return 1;
    }
  };
  
  const pulseDuration = `${1.2 * getSpeedMultiplier()}s`;
  
  return (
    <Box
      width={getSize()}
      height={getSize()}
      borderRadius="full"
      bg={pulseColor}
      animation={`${pulseKeyframes} ${pulseDuration} infinite ease-in-out`}
    />
  );
};

// Dots Loader
const DotsLoader: React.FC<{ 
  size: LoaderSize; 
  color?: string;
  speed: LoaderSpeed;
}> = ({ 
  size, 
  color,
  speed
}) => {
  const dotsColor = color || useColorModeValue('blue.500', 'blue.300');
  
  const getDotSize = () => {
    switch (size) {
      case 'xs': return '6px';
      case 'sm': return '8px';
      case 'md': return '10px';
      case 'lg': return '12px';
      case 'xl': return '16px';
      default: return '10px';
    }
  };
  
  const getSpeedMultiplier = () => {
    switch (speed) {
      case 'slow': return 1.3;
      case 'fast': return 0.7;
      default: return 1;
    }
  };
  
  return (
    <MotionFlex
      variants={bouncingDotsVariants}
      initial="initial"
      animate="animate"
      custom={getSpeedMultiplier()}
    >
      {[0, 1, 2].map((index) => (
        <MotionBox
          key={index}
          width={getDotSize()}
          height={getDotSize()}
          borderRadius="full"
          bg={dotsColor}
          mx="2px"
          variants={dotVariants}
          custom={index * getSpeedMultiplier()}
        />
      ))}
    </MotionFlex>
  );
};

// Bars Loader
const BarsLoader: React.FC<{ 
  size: LoaderSize; 
  color?: string;
  speed: LoaderSpeed;
}> = ({ 
  size, 
  color,
  speed
}) => {
  const barsColor = color || useColorModeValue('blue.500', 'blue.300');
  
  const getBarSize = () => {
    switch (size) {
      case 'xs': return { width: '3px', height: '12px' };
      case 'sm': return { width: '4px', height: '16px' };
      case 'md': return { width: '5px', height: '24px' };
      case 'lg': return { width: '6px', height: '32px' };
      case 'xl': return { width: '8px', height: '40px' };
      default: return { width: '5px', height: '24px' };
    }
  };
  
  const getSpeedMultiplier = () => {
    switch (speed) {
      case 'slow': return 1.5;
      case 'fast': return 0.7;
      default: return 1;
    }
  };
  
  const { width, height } = getBarSize();
  
  return (
    <HStack spacing="3px">
      {[0, 1, 2, 3, 4].map((index) => (
        <MotionBox
          key={index}
          width={width}
          height={height}
          bg={barsColor}
          borderRadius="sm"
          variants={barVariants}
          initial="initial"
          animate="animate"
          custom={index * getSpeedMultiplier()}
          style={{ originY: 1 }}
        />
      ))}
    </HStack>
  );
};

// Waves Loader
const WavesLoader: React.FC<{ 
  size: LoaderSize; 
  color?: string;
  speed: LoaderSpeed;
}> = ({ 
  size, 
  color,
  speed
}) => {
  const wavesColor = color || useColorModeValue('blue.500', 'blue.300');
  
  const getWaveSize = () => {
    switch (size) {
      case 'xs': return { width: '4px', height: '12px', spacing: '2px' };
      case 'sm': return { width: '6px', height: '16px', spacing: '3px' };
      case 'md': return { width: '8px', height: '24px', spacing: '4px' };
      case 'lg': return { width: '10px', height: '32px', spacing: '5px' };
      case 'xl': return { width: '12px', height: '40px', spacing: '6px' };
      default: return { width: '8px', height: '24px', spacing: '4px' };
    }
  };
  
  const getSpeedMultiplier = () => {
    switch (speed) {
      case 'slow': return 1.5;
      case 'fast': return 0.7;
      default: return 1;
    }
  };
  
  const { width, height, spacing } = getWaveSize();
  const waveDuration = `${1 * getSpeedMultiplier()}s`;
  
  return (
    <HStack spacing={spacing}>
      {[0, 1, 2, 3, 4].map((index) => (
        <Box
          key={index}
          width={width}
          height={height}
          bg={wavesColor}
          borderRadius="full"
          animation={`${waveKeyframes} ${waveDuration} infinite ease-in-out ${index * 0.1}s`}
        />
      ))}
    </HStack>
  );
};

// Skeleton Loader
const SkeletonLoader: React.FC<{ 
  size: LoaderSize; 
  variant?: 'text' | 'circle' | 'rect';
  speed: LoaderSpeed;
}> = ({ 
  size, 
  variant = 'rect',
  speed
}) => {
  const getSkeletonSize = () => {
    switch (size) {
      case 'xs': return { width: '100px', height: '40px', circle: '24px', lines: 1 };
      case 'sm': return { width: '150px', height: '60px', circle: '36px', lines: 2 };
      case 'md': return { width: '200px', height: '80px', circle: '48px', lines: 3 };
      case 'lg': return { width: '300px', height: '100px', circle: '64px', lines: 4 };
      case 'xl': return { width: '400px', height: '120px', circle: '80px', lines: 5 };
      default: return { width: '200px', height: '80px', circle: '48px', lines: 3 };
    }
  };
  
  const getSpeedMultiplier = () => {
    switch (speed) {
      case 'slow': return 1.5;
      case 'fast': return 0.7;
      default: return 1;
    }
  };
  
  const { width, height, circle, lines } = getSkeletonSize();
  const speedMultiplier = getSpeedMultiplier();
  
  if (variant === 'circle') {
    return <SkeletonCircle size={circle} speed={`${1.5 * speedMultiplier}s`} />;
  }
  
  if (variant === 'text') {
    return <SkeletonText noOfLines={lines} spacing="4" speed={`${1.5 * speedMultiplier}s`} width={width} />;
  }
  
  return <Skeleton height={height} width={width} speed={`${1.5 * speedMultiplier}s`} />;
};

// Circular Progress Loader
const CircularLoader: React.FC<{ 
  size: LoaderSize; 
  color?: string;
  value?: number;
  isIndeterminate?: boolean;
  thickness?: number;
  showValue?: boolean;
  speed: LoaderSpeed;
}> = ({ 
  size, 
  color,
  value = 0,
  isIndeterminate = false,
  thickness = 8,
  showValue = true,
  speed
}) => {
  const circleColor = color || useColorModeValue('blue.500', 'blue.300');
  
  const getCircleSize = () => {
    switch (size) {
      case 'xs': return '32px';
      case 'sm': return '48px';
      case 'md': return '80px';
      case 'lg': return '120px';
      case 'xl': return '160px';
      default: return '80px';
    }
  };
  
  const getSpeedMultiplier = () => {
    switch (speed) {
      case 'slow': return 1.5;
      case 'fast': return 0.7;
      default: return 1;
    }
  };
  
  const trackColor = useColorModeValue('gray.100', 'gray.700');
  
  return (
    <CircularProgress
      value={value}
      size={getCircleSize()}
      thickness={thickness}
      color={circleColor}
      trackColor={trackColor}
      isIndeterminate={isIndeterminate}
      capIsRound
    >
      {showValue && !isIndeterminate && (
        <CircularProgressLabel>{Math.round(value)}%</CircularProgressLabel>
      )}
    </CircularProgress>
  );
};

// Progress Bar Loader
const ProgressLoader: React.FC<{ 
  size: LoaderSize; 
  color?: string;
  value?: number;
  isIndeterminate?: boolean;
  min?: number;
  max?: number;
  hasStripe?: boolean;
  speed: LoaderSpeed;
}> = ({ 
  size, 
  color,
  value = 0,
  isIndeterminate = false,
  min = 0,
  max = 100,
  hasStripe = false,
  speed
}) => {
  const progressColor = color || useColorModeValue('blue.500', 'blue.300');
  
  const getProgressHeight = () => {
    switch (size) {
      case 'xs': return '4px';
      case 'sm': return '6px';
      case 'md': return '8px';
      case 'lg': return '12px';
      case 'xl': return '16px';
      default: return '8px';
    }
  };
  
  const getSpeedMultiplier = () => {
    switch (speed) {
      case 'slow': return 1.5;
      case 'fast': return 0.7;
      default: return 1;
    }
  };
  
  return (
    <Progress
      value={value}
      min={min}
      max={max}
      height={getProgressHeight()}
      colorScheme={progressColor.split('.')[0]}
      isIndeterminate={isIndeterminate}
      hasStripe={hasStripe}
      isAnimated={hasStripe}
      borderRadius="full"
      sx={isIndeterminate ? {
        '& > div': {
          transitionDuration: `${0.8 * getSpeedMultiplier()}s`
        }
      } : {}}
    />
  );
};

// Shimmer Loader
const ShimmerLoader: React.FC<{ 
  size: LoaderSize; 
  primaryColor?: string;
  secondaryColor?: string;
  speed: LoaderSpeed;
}> = ({ 
  size, 
  primaryColor,
  secondaryColor,
  speed
}) => {
  const bgColor = primaryColor || useColorModeValue('gray.100', 'gray.700');
  const shimmerColor = secondaryColor || useColorModeValue('gray.300', 'gray.600');
  
  const getShimmerSize = () => {
    switch (size) {
      case 'xs': return { width: '100px', height: '40px' };
      case 'sm': return { width: '150px', height: '60px' };
      case 'md': return { width: '200px', height: '80px' };
      case 'lg': return { width: '300px', height: '100px' };
      case 'xl': return { width: '400px', height: '120px' };
      default: return { width: '200px', height: '80px' };
    }
  };
  
  const getSpeedMultiplier = () => {
    switch (speed) {
      case 'slow': return 2;
      case 'fast': return 0.7;
      default: return 1.2;
    }
  };
  
  const { width, height } = getShimmerSize();
  const shimmerDuration = `${2 * getSpeedMultiplier()}s`;
  
  return (
    <Box
      width={width}
      height={height}
      borderRadius="md"
      background={`linear-gradient(90deg, ${bgColor}, ${shimmerColor}, ${bgColor})`}
      backgroundSize="200% 100%"
      animation={`${shimmerKeyframes} ${shimmerDuration} infinite linear`}
    />
  );
};

// Chain Icon Loader
const ChainIconLoader: React.FC<{ 
  chainType: ChainType; 
  size: LoaderSize;
  speed: LoaderSpeed;
}> = ({ 
  chainType, 
  size,
  speed
}) => {
  const getIconSize = () => {
    switch (size) {
      case 'xs': return { box: '24px', icon: '14px' };
      case 'sm': return { box: '32px', icon: '18px' };
      case 'md': return { box: '48px', icon: '24px' };
      case 'lg': return { box: '64px', icon: '32px' };
      case 'xl': return { box: '80px', icon: '40px' };
      default: return { box: '48px', icon: '24px' };
    }
  };
  
  const getChainIcon = () => {
    switch (chainType) {
      case 'ethereum': return FaEthereum;
      case 'bitcoin': return FaBitcoin;
      case 'binance': return FaCoins;
      case 'polygon': return FaNetworkWired;
      case 'arbitrum': return FaLink;
      case 'optimism': return FaArrowRight;
      case 'avalanche': return FaChartLine;
      case 'solana': return FaCoins;
      case 'cosmos': return FaLink;
      default: return FaSpinner;
    }
  };
  
  const getChainColor = () => {
    switch (chainType) {
      case 'ethereum': return useColorModeValue('blue.500', 'blue.300');
      case 'bitcoin': return useColorModeValue('orange.500', 'orange.300');
      case 'binance': return useColorModeValue('yellow.500', 'yellow.300');
      case 'polygon': return useColorModeValue('purple.500', 'purple.300');
      case 'arbitrum': return useColorModeValue('blue.700', 'blue.500');
      case 'optimism': return useColorModeValue('red.500', 'red.300');
      case 'avalanche': return useColorModeValue('red.600', 'red.400');
      case 'solana': return useColorModeValue('purple.600', 'purple.400');
      case 'cosmos': return useColorModeValue('teal.500', 'teal.300');
      default: return useColorModeValue('gray.500', 'gray.300');
    }
  };
  
  const getSpeedMultiplier = () => {
    switch (speed) {
      case 'slow': return 1.5;
      case 'fast': return 0.7;
      default: return 1;
    }
  };
  
  const { box, icon } = getIconSize();
  const ChainIcon = getChainIcon();
  const chainColor = getChainColor();
  const spinDuration = `${3 * getSpeedMultiplier()}s`;
  
  return (
    <Box
      width={box}
      height={box}
      borderRadius="full"
      bg={useColorModeValue('gray.100', 'gray.700')}
      display="flex"
      alignItems="center"
      justifyContent="center"
      position="relative"
      overflow="hidden"
    >
      <Box
        as={ChainIcon}
        color={chainColor}
        fontSize={icon}
        animation={`${pulseKeyframes} ${spinDuration} infinite ease-in-out`}
      />
    </Box>
  );
};

// Transaction Progress Loader
const TransactionProgressLoader: React.FC<{ 
  steps: TransactionStep[]; 
  currentStep: number;
  size: LoaderSize;
  color?: string;
  speed: LoaderSpeed;
}> = ({ 
  steps, 
  currentStep,
  size,
  color,
  speed
}) => {
  const progressColor = color || useColorModeValue('blue.500', 'blue.300');
  const completedColor = useColorModeValue('green.500', 'green.300');
  const errorColor = useColorModeValue('red.500', 'red.300');
  const pendingColor = useColorModeValue('gray.300', 'gray.600');
  
  const getStepSize = () => {
    switch (size) {
      case 'xs': return { icon: '16px', line: '2px', spacing: '20px' };
      case 'sm': return { icon: '24px', line: '3px', spacing: '30px' };
      case 'md': return { icon: '32px', line: '4px', spacing: '40px' };
      case 'lg': return { icon: '40px', line: '5px', spacing: '60px' };
      case 'xl': return { icon: '48px', line: '6px', spacing: '80px' };
      default: return { icon: '32px', line: '4px', spacing: '40px' };
    }
  };
  
  const getSpeedMultiplier = () => {
    switch (speed) {
      case 'slow': return 1.5;
      case 'fast': return 0.7;
      default: return 1;
    }
  };
  
  const { icon, line, spacing } = getStepSize();
  
  const getStepColor = (status: string) => {
    switch (status) {
      case 'completed': return completedColor;
      case 'active': return progressColor;
      case 'error': return errorColor;
      default: return pendingColor;
    }
  };
  
  const getStepIcon = (step: TransactionStep) => {
    if (step.icon) return step.icon;
    
    switch (step.status) {
      case 'completed': return <FaCheckCircle />;
      case 'active': return <FaSpinner />;
      case 'error': return <FaTimesCircle />;
      default: return <FaSpinner opacity={0.5} />;
    }
  };
  
  return (
    <Box width="100%">
      <Flex justifyContent="space-between" alignItems="center" position="relative">
        {/* Progress Line */}
        <Box
          position="absolute"
          height={line}
          bg={pendingColor}
          left="0"
          right="0"
          top="50%"
          transform="translateY(-50%)"
          zIndex={0}
        />
        
        {/* Completed Line */}
        <MotionBox
          position="absolute"
          height={line}
          bg={progressColor}
          left="0"
          top="50%"
          transform="translateY(-50%)"
          zIndex={1}
          width={`${(currentStep / (steps.length - 1)) * 100}%`}
          initial={{ width: 0 }}
          animate={{ width: `${(currentStep / (steps.length - 1)) * 100}%` }}
          transition={{ duration: 0.5 * getSpeedMultiplier() }}
        />
        
        {/* Steps */}
        {steps.map((step, index) => (
          <MotionFlex
            key={step.id}
            direction="column"
            alignItems="center"
            zIndex={2}
            variants={progressStepVariants}
            initial="pending"
            animate={step.status}
            transition={{ duration: 0.3 }}
          >
            <MotionBox
              width={icon}
              height={icon}
              borderRadius="full"
              bg={useColorModeValue('white', 'gray.800')}
              border="2px solid"
              borderColor={getStepColor(step.status)}
              display="flex"
              alignItems="center"
              justifyContent="center"
              color={getStepColor(step.status)}
              position="relative"
              {...(step.status === 'active' && {
                animation: `${pulseKeyframes} ${1.2 * getSpeedMultiplier()}s infinite ease-in-out`
              })}
            >
              {getStepIcon(step)}
              
              {step.percentage !== undefined && step.status === 'active' && (
                <CircularProgress
                  value={step.percentage}
                  size={icon}
                  thickness="8px"
                  color={progressColor}
                  position="absolute"
                  top="0"
                  left="0"
                  zIndex={-1}
                />
              )}
            </MotionBox>
            
            <Text
              fontSize={size === 'xs' || size === 'sm' ? 'xs' : 'sm'}
              fontWeight={step.status === 'active' ? 'bold' : 'normal'}
              color={step.status === 'active' ? getStepColor(step.status) : 'gray.500'}
              mt={2}
              textAlign="center"
              maxWidth={spacing}
            >
              {step.label}
            </Text>
            
            {step.description && (
              <Text
                fontSize="xs"
                color="gray.500"
                mt={1}
                textAlign="center"
                maxWidth={spacing}
              >
                {step.description}
              </Text>
            )}
          </MotionFlex>
        ))}
      </Flex>
    </Box>
  );
};

// Portfolio Shimmer Loader
const PortfolioShimmerLoader: React.FC<{ 
  itemCount: number;
  size: LoaderSize;
  speed: LoaderSpeed;
}> = ({ 
  itemCount = 3,
  size,
  speed
}) => {
  const bgColor = useColorModeValue('gray.100', 'gray.700');
  const shimmerColor = useColorModeValue('gray.300', 'gray.600');
  
  const getItemSize = () => {
    switch (size) {
      case 'xs': return { height: '40px', iconSize: '20px', spacing: '10px' };
      case 'sm': return { height: '50px', iconSize: '24px', spacing: '12px' };
      case 'md': return { height: '60px', iconSize: '30px', spacing: '16px' };
      case 'lg': return { height: '70px', iconSize: '36px', spacing: '20px' };
      case 'xl': return { height: '80px', iconSize: '40px', spacing: '24px' };
      default: return { height: '60px', iconSize: '30px', spacing: '16px' };
    }
  };
  
  const getSpeedMultiplier = () => {
    switch (speed) {
      case 'slow': return 2;
      case 'fast': return 0.7;
      default: return 1.2;
    }
  };
  
  const { height, iconSize, spacing } = getItemSize();
  const shimmerDuration = `${2 * getSpeedMultiplier()}s`;
  
  return (
    <VStack spacing={spacing} align="stretch" width="100%">
      {Array.from({ length: itemCount }).map((_, index) => (
        <Flex
          key={index}
          height={height}
          borderRadius="md"
          overflow="hidden"
          align="center"
          p={3}
        >
          {/* Token Icon */}
          <Box
            width={iconSize}
            height={iconSize}
            borderRadius="full"
            background={`linear-gradient(90deg, ${bgColor}, ${shimmerColor}, ${bgColor})`}
            backgroundSize="200% 100%"
            animation={`${shimmerKeyframes} ${shimmerDuration} infinite linear`}
            mr={3}
          />
          
          {/* Token Name and Balance */}
          <Box flex="1">
            <Box
              width="80px"
              height="16px"
              borderRadius="sm"
              background={`linear-gradient(90deg, ${bgColor}, ${shimmerColor}, ${bgColor})`}
              backgroundSize="200% 100%"
              animation={`${shimmerKeyframes} ${shimmerDuration} infinite linear`}
              mb={2}
            />
            <Box
              width="120px"
              height="12px"
              borderRadius="sm"
              background={`linear-gradient(90deg, ${bgColor}, ${shimmerColor}, ${bgColor})`}
              backgroundSize="200% 100%"
              animation={`${shimmerKeyframes} ${shimmerDuration} infinite linear ${index * 0.1}s`}
            />
          </Box>
          
          {/* Token Value */}
          <Box>
            <Box
              width="60px"
              height="16px"
              borderRadius="sm"
              background={`linear-gradient(90deg, ${bgColor}, ${shimmerColor}, ${bgColor})`}
              backgroundSize="200% 100%"
              animation={`${shimmerKeyframes} ${shimmerDuration} infinite linear ${index * 0.15}s`}
              mb={2}
            />
            <Box
              width="40px"
              height="12px"
              borderRadius="sm"
              background={`linear-gradient(90deg, ${bgColor}, ${shimmerColor}, ${bgColor})`}
              backgroundSize="200% 100%"
              animation={`${shimmerKeyframes} ${shimmerDuration} infinite linear ${index * 0.2}s`}
            />
          </Box>
        </Flex>
      ))}
    </VStack>
  );
};

// Page Loading Overlay
const PageLoadingOverlay: React.FC<{ 
  message?: string;
  description?: string;
  color?: string;
  overlayColor?: string;
  overlayOpacity?: number;
  variant?: LoaderVariant;
  size: LoaderSize;
  speed: LoaderSpeed;
  blockInteraction?: boolean;
}> = ({ 
  message,
  description,
  color,
  overlayColor,
  overlayOpacity = 0.7,
  variant = 'spinner',
  size,
  speed,
  blockInteraction = true
}) => {
  const bgColor = overlayColor || useColorModeValue('white', 'gray.800');
  const loaderColor = color || useColorModeValue('blue.500', 'blue.300');
  
  return (
    <Portal>
      <MotionBox
        position="fixed"
        top="0"
        left="0"
        right="0"
        bottom="0"
        bg={bgColor}
        opacity={overlayOpacity}
        zIndex={blockInteraction ? 9999 : 50}
        display="flex"
        flexDirection="column"
        alignItems="center"
        justifyContent="center"
        variants={overlayVariants}
        initial="hidden"
        animate="visible"
        exit="exit"
      >
        <Box mb={4}>
          {variant === 'spinner' && <SpinnerLoader size={size} color={loaderColor} speed={speed} />}
          {variant === 'pulse' && <PulseLoader size={size} color={loaderColor} speed={speed} />}
          {variant === 'dots' && <DotsLoader size={size} color={loaderColor} speed={speed} />}
          {variant === 'bars' && <BarsLoader size={size} color={loaderColor} speed={speed} />}
          {variant === 'waves' && <WavesLoader size={size} color={loaderColor} speed={speed} />}
          {variant === 'circular' && <CircularLoader size={size} color={loaderColor} isIndeterminate speed={speed} />}
        </Box>
        
        {message && (
          <Heading size="md" textAlign="center" mb={description ? 2 : 0}>
            {message}
          </Heading>
        )}
        
        {description && (
          <Text textAlign="center" color="gray.500" maxWidth="400px">
            {description}
          </Text>
        )}
      </MotionBox>
    </Portal>
  );
};

// Button Loading State
const ButtonLoader: React.FC<{ 
  text: string;
  isLoading: boolean;
  variant?: string;
  size?: string;
  color?: string;
  isDisabled?: boolean;
  onClick?: () => void;
  speed: LoaderSpeed;
}> = ({ 
  text,
  isLoading,
  variant = 'solid',
  size = 'md',
  color,
  isDisabled = false,
  onClick,
  speed
}) => {
  return (
    <Button
      variant={variant}
      size={size}
      colorScheme={color?.split('.')[0] || 'blue'}
      isLoading={isLoading}
      loadingText={text}
      spinnerPlacement="start"
      isDisabled={isDisabled || isLoading}
      onClick={onClick}
      sx={isLoading ? {
        '& .chakra-spinner': {
          transitionDuration: speed === 'slow' ? '1.2s' : speed === 'fast' ? '0.6s' : '0.8s'
        }
      } : {}}
    >
      {text}
    </Button>
  );
};

// Progressive Content Loader
const ProgressiveLoader: React.FC<{ 
  stageCount: number;
  stageDelay: number;
  children: React.ReactNode;
  isLoading: boolean;
}> = ({ 
  stageCount,
  stageDelay,
  children,
  isLoading
}) => {
  const childrenArray = React.Children.toArray(children);
  const stages = Math.min(stageCount, childrenArray.length);
  
  if (isLoading) {
    return (
      <VStack spacing={4} align="stretch">
        {Array.from({ length: stages }).map((_, index) => (
          <SkeletonLoader 
            key={index} 
            size="md" 
            variant={index % 2 === 0 ? 'rect' : 'text'} 
            speed="normal"
          />
        ))}
      </VStack>
    );
  }
  
  return (
    <>
      {childrenArray.map((child, index) => (
        <MotionBox
          key={index}
          variants={staggeredContentVariants}
          initial="hidden"
          animate="visible"
          custom={index}
          transition={{ delay: index * (stageDelay / 1000) }}
        >
          {child}
        </MotionBox>
      ))}
    </>
  );
};

// Retry Mechanism
const RetryLoader: React.FC<{ 
  isError: boolean;
  errorMessage?: string;
  retryConfig: RetryConfig;
  children: React.ReactNode;
  size: LoaderSize;
  speed: LoaderSpeed;
}> = ({ 
  isError,
  errorMessage = 'Something went wrong',
  retryConfig,
  children,
  size,
  speed
}) => {
  const [retryCount, setRetryCount] = useState(0);
  const [isRetrying, setIsRetrying] = useState(false);
  const maxAttempts = retryConfig.maxAttempts || 3;
  
  const handleRetry = () => {
    if (retryCount < maxAttempts) {
      setIsRetrying(true);
      setRetryCount(prev => prev + 1);
      
      setTimeout(() => {
        setIsRetrying(false);
        if (retryConfig.onRetry) {
          retryConfig.onRetry();
        }
      }, retryConfig.delayMs || 1500);
    }
  };
  
  if (isError) {
    return (
      <Box textAlign="center" py={6}>
        <Icon as={FaExclamationTriangle} color="red.500" boxSize={size === 'xs' ? 6 : size === 'sm' ? 8 : 10} mb={4} />
        <Heading size={size === 'xs' || size === 'sm' ? 'sm' : 'md'} mb={2}>
          {errorMessage}
        </Heading>
        <Text color="gray.500" mb={4}>
          {retryCount >= maxAttempts 
            ? `Maximum retry attempts (${maxAttempts}) reached.` 
            : `Retry attempt ${retryCount} of ${maxAttempts}`}
        </Text>
        
        {retryConfig.showButton && retryCount < maxAttempts && (
          <Button
            leftIcon={<FaRedo />}
            onClick={handleRetry}
            isLoading={isRetrying}
            loadingText="Retrying"
            variant="outline"
            colorScheme="blue"
            size={size === 'xs' ? 'xs' : size === 'sm' ? 'sm' : 'md'}
          >
            Retry
          </Button>
        )}
      </Box>
    );
  }
  
  if (isRetrying) {
    return (
      <Box textAlign="center" py={4}>
        <SpinnerLoader size={size} speed={speed} />
        <Text mt={2}>Retrying...</Text>
      </Box>
    );
  }
  
  return <>{children}</>;
};

// ========== Main Component ==========

export const EnhancedLoader: React.FC<EnhancedLoaderProps> = ({
  // Base props
  variant = 'spinner',
  size = 'md',
  state = 'loading',
  speed = 'normal',
  
  // Content props
  message,
  description,
  showMessage = true,
  
  // Visual props
  color,
  secondaryColor,
  thickness,
  isIndeterminate = true,
  value = 0,
  min = 0,
  max = 100,
  
  // Chain specific props
  chainType = 'generic',
  showChainIcon = false,
  
  // Transaction loader props
  steps = [],
  currentStep = 0,
  
  // Overlay props
  isOverlay = false,
  overlayColor,
  overlayOpacity = 0.7,
  blockInteraction = true,
  
  // Portfolio loader props
  portfolioItemCount = 3,
  
  // Button loader props
  buttonText = 'Loading',
  buttonVariant = 'solid',
  buttonSize = 'md',
  isDisabled = false,
  
  // Progressive loading props
  stageCount = 3,
  stageDelay = 300,
  
  // Animation props
  animate = true,
  animationDuration = 300,
  
  // Retry mechanism props
  retry,
  
  // Accessibility props
  ariaLabel,
  ariaLive = 'polite',
  
  // Misc props
  onComplete,
  className,
  
  // Children
  children,
  
  // Additional props
  ...rest
}) => {
  // State
  const [isVisible, setIsVisible] = useState(true);
  const [retryAttempts, setRetryAttempts] = useState(0);
  const [isRetrying, setIsRetrying] = useState(false);
  
  // Refs
  const loadingTimeRef = useRef<number | null>(null);
  
  // Effects
  
  // Handle completion
  useEffect(() => {
    if (state === 'success' && onComplete) {
      onComplete();
    }
  }, [state, onComplete]);
  
  // Track loading time for performance metrics
  useEffect(() => {
    if (state === 'loading' && !loadingTimeRef.current) {
      loadingTimeRef.current = Date.now();
    } else if (state !== 'loading' && loadingTimeRef.current) {
      const loadingTime = Date.now() - loadingTimeRef.current;
      console.debug(`Loading completed in ${loadingTime}ms`);
      loadingTimeRef.current = null;
    }
  }, [state]);
  
  // Automatic retry logic
  useEffect(() => {
    if (state === 'error' && retry?.enabled && retryAttempts < (retry.maxAttempts || 3) && !isRetrying) {
      setIsRetrying(true);
      
      const retryTimer = setTimeout(() => {
        setRetryAttempts(prev => prev + 1);
        setIsRetrying(false);
        if (retry.onRetry) {
          retry.onRetry();
        }
      }, retry.delayMs || 2000);
      
      return () => clearTimeout(retryTimer);
    }
  }, [state, retry, retryAttempts, isRetrying]);
  
  // Render overlay loader
  if (isOverlay) {
    return (
      <PageLoadingOverlay
        message={message}
        description={description}
        color={color}
        overlayColor={overlayColor}
        overlayOpacity={overlayOpacity}
        variant={variant}
        size={size}
        speed={speed}
        blockInteraction={blockInteraction}
      />
    );
  }
  
  // Render chain-specific loader
  if (showChainIcon) {
    return (
      <Flex direction="column" align="center" justify="center" className={className} {...rest}>
        <ChainIconLoader 
          chainType={chainType} 
          size={size}
          speed={speed}
        />
        
        {showMessage && message && (
          <Text mt={3} textAlign="center" fontWeight="medium">
            {message}
          </Text>
        )}
        
        {description && (
          <Text mt={1} textAlign="center" color="gray.500" fontSize="sm">
            {description}
          </Text>
        )}
        
        {/* Screen reader announcement */}
        <VisuallyHidden>
          <div aria-live={ariaLive}>
            {state === 'loading' ? `Loading ${message || ''}` : 
             state === 'success' ? `Completed ${message || ''}` : 
             state === 'error' ? `Error loading ${message || ''}` : ''}
          </div>
        </VisuallyHidden>
      </Flex>
    );
  }
  
  // Render transaction progress
  if (steps.length > 0) {
    return (
      <Box width="100%" className={className} {...rest}>
        <TransactionProgressLoader
          steps={steps}
          currentStep={currentStep}
          size={size}
          color={color}
          speed={speed}
        />
        
        {/* Screen reader announcement */}
        <VisuallyHidden>
          <div aria-live={ariaLive}>
            {`Step ${currentStep + 1} of ${steps.length}: ${steps[currentStep]?.label || ''}`}
          </div>
        </VisuallyHidden>
      </Box>
    );
  }
  
  // Render portfolio loader
  if (variant === 'shimmer' && portfolioItemCount > 0) {
    return (
      <PortfolioShimmerLoader
        itemCount={portfolioItemCount}
        size={size}
        speed={speed}
      />
    );
  }
  
  // Render button loader
  if (buttonText) {
    return (
      <ButtonLoader
        text={buttonText}
        isLoading={state === 'loading'}
        variant={buttonVariant}
        size={buttonSize}
        color={color}
        isDisabled={isDisabled}
        speed={speed}
        onClick={rest.onClick}
      />
    );
  }
  
  // Render progressive loader
  if (children && animate) {
    return (
      <ProgressiveLoader
        stageCount={stageCount}
        stageDelay={stageDelay}
        isLoading={state === 'loading'}
      >
        {children}
      </ProgressiveLoader>
    );
  }
  
  // Render retry mechanism
  if (retry?.enabled) {
    return (
      <RetryLoader
        isError={state === 'error'}
        errorMessage={message}
        retryConfig={retry}
        size={size}
        speed={speed}
      >
        {renderLoader()}
      </RetryLoader>
    );
  }
  
  // Render standard loader
  return renderLoader();
  
  // Helper function to render the appropriate loader
  function renderLoader() {
    return (
      <Flex 
        direction="column" 
        align="center" 
        justify="center"
        className={className}
        aria-label={ariaLabel || `${state} ${message || ''}`}
        {...rest}
      >
        {/* Loader */}
        <Box>
          {variant === 'spinner' && <SpinnerLoader size={size} color={color} speed={speed} thickness={thickness} />}
          {variant === 'pulse' && <PulseLoader size={size} color={color} speed={speed} />}
          {variant === 'dots' && <DotsLoader size={size} color={color} speed={speed} />}
          {variant === 'bars' && <BarsLoader size={size} color={color} speed={speed} />}
          {variant === 'waves' && <WavesLoader size={size} color={color} speed={speed} />}
          {variant === 'skeleton' && <SkeletonLoader size={size} speed={speed} />}
          {variant === 'circular' && (
            <CircularLoader 
              size={size} 
              color={color} 
              value={value} 
              isIndeterminate={isIndeterminate}
              thickness={thickness}
              speed={speed}
            />
          )}
          {variant === 'progress' && (
            <ProgressLoader
              size={size}
              color={color}
              value={value}
              isIndeterminate={isIndeterminate}
              min={min}
              max={max}
              hasStripe={true}
              speed={speed}
            />
          )}
          {variant === 'shimmer' && (
            <ShimmerLoader 
              size={size} 
              primaryColor={color} 
              secondaryColor={secondaryColor}
              speed={speed}
            />
          )}
        </Box>
        
        {/* Message */}
        {showMessage && message && (
          <Text mt={3} textAlign="center" fontWeight="medium">
            {message}
          </Text>
        )}
        
        {/* Description */}
        {description && (
          <Text mt={1} textAlign="center" color="gray.500" fontSize="sm">
            {description}
          </Text>
        )}
        
        {/* Status indicators */}
        {state === 'error' && (
          <Flex align="center" mt={3} color="red.500">
            <Icon as={FaExclamationTriangle} mr={2} />
            <Text fontWeight="medium">Error occurred</Text>
          </Flex>
        )}
        
        {state === 'success' && (
          <Flex align="center" mt={3} color="green.500">
            <Icon as={FaCheckCircle} mr={2} />
            <Text fontWeight="medium">Completed successfully</Text>
          </Flex>
        )}
        
        {/* Screen reader announcement */}
        <VisuallyHidden>
          <div aria-live={ariaLive}>
            {state === 'loading' ? `Loading ${message || ''}` : 
             state === 'success' ? `Completed ${message || ''}` : 
             state === 'error' ? `Error loading ${message || ''}` : ''}
          </div>
        </VisuallyHidden>
      </Flex>
    );
  }
};

export default EnhancedLoader;
